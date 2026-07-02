"""Guards operacionais do atendimento WhatsApp/SDR.

Estado de anti-abuse agora persiste em Postgres (tabela rate_limit_counters)
via whatsapp.persistence. Mantém cache in-memory como fallback caso o DB
esteja indisponível — degradação graciosa, nunca derruba o atendimento.

API pública preservada 100% compatível com whatsapp_listener.py e
response_executor.py (callers não precisam mudar).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Callable, Optional

from sqlalchemy.engine import Engine

from whatsapp.persistence import (
    delete_counter,
    lead_key_user_id,
    read_counter,
    upsert_counter,
)

logger = logging.getLogger(__name__)


# Pesos por severity de evento (espelha phone_health_events).
EVENT_WEIGHTS: dict[str, int] = {
    "info": 0,
    "warn": 5,
    "error": 15,
    "critical": 40,
}

# Thresholds de status a partir do score.
STATUS_THRESHOLDS: list[tuple[int, str]] = [
    (80, "healthy"),
    (50, "degraded"),
    (20, "restricted"),
    (0, "banned"),
]


def score_to_status(score: int) -> str:
    """Converte score 0-100 em status textual."""
    score = max(0, min(100, score))
    for threshold, status in STATUS_THRESHOLDS:
        if score >= threshold:
            return status
    return "banned"


class AntiAbuseGuards:
    """Anti-abuse state com persistência em Postgres + cache in-memory.

    O cache in-memory (dicts abaixo) é write-through:
      - leituras: cache → DB → cache (fallback)
      - escritas: cache + DB em paralelo
    Se DB falhar, operação ainda funciona via cache (degradação graciosa).
    """

    def __init__(
        self,
        *,
        engine: Engine | None = None,
        flood_threshold: int,
        flood_window: float,
        flood_silence: float,
        daily_limit_for_key: Callable[[str], int],
        cooldown_seconds_for_key: Callable[[str], float],
        human_pause_seconds_for_key: Callable[[str], float],
        now_func: Callable[[], float] = time.time,
        today_func: Callable[[], date] = date.today,
    ):
        self.engine = engine
        self.flood_threshold = flood_threshold
        self.flood_window = flood_window
        self.flood_silence = flood_silence
        self.daily_limit_for_key = daily_limit_for_key
        self.cooldown_seconds_for_key = cooldown_seconds_for_key
        self.human_pause_seconds_for_key = human_pause_seconds_for_key
        self.now_func = now_func
        self.today_func = today_func

        # Cache in-memory (fallback + hot path)
        self.flood_tracker: dict[str, list[float]] = {}
        self.flood_silenced: dict[str, float] = {}
        self.daily_count: dict[str, int] = {}
        self.daily_date = ""
        self.lead_last_reply: dict[str, float] = {}
        self.human_pause: dict[str, float] = {}

    # ── Daily reset ────────────────────────────────────────────────────

    def reset_daily_if_needed(self) -> None:
        today = self.today_func().isoformat()
        if self.daily_date != today:
            self.daily_count = {}
            self.daily_date = today

    # ── Flood ──────────────────────────────────────────────────────────

    def check_flood(self, lead_key: str) -> bool:
        """Retorna True se lead está em flood (deve ser silenciado)."""
        now = self.now_func()

        # Checar silêncio ativo (cache in-memory primeiro)
        if lead_key in self.flood_silenced:
            if now - self.flood_silenced[lead_key] < self.flood_silence:
                return True
            del self.flood_silenced[lead_key]

        # Hidratar do DB se cache vazio (cold start / restart)
        if lead_key not in self.flood_tracker and self.engine is not None:
            self._hydrate_flood_from_db(lead_key)

        # Append + janela deslizante
        self.flood_tracker.setdefault(lead_key, []).append(now)
        self.flood_tracker[lead_key] = [
            item for item in self.flood_tracker[lead_key]
            if now - item < self.flood_window
        ]

        if len(self.flood_tracker[lead_key]) > self.flood_threshold:
            self.flood_silenced[lead_key] = now
            self._persist_flood(lead_key)
            return True
        return False

    def _hydrate_flood_from_db(self, lead_key: str) -> None:
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        row = read_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="flood",
        )
        if row is None:
            return
        timestamps = row["payload"].get("timestamps", [])
        self.flood_tracker[lead_key] = [float(t) for t in timestamps]
        silenced_until = row["payload"].get("silenced_until")
        if silenced_until is not None and float(silenced_until) > self.now_func():
            self.flood_silenced[lead_key] = float(silenced_until)

    def _persist_flood(self, lead_key: str) -> None:
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        payload = {
            "timestamps": self.flood_tracker.get(lead_key, []),
            "silenced_until": self.flood_silenced.get(lead_key),
        }
        upsert_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="flood",
            value=len(self.flood_tracker.get(lead_key, [])),
            payload=payload,
        )

    # ── Daily limit ────────────────────────────────────────────────────

    def check_daily_limit(self, lead_key: str) -> bool:
        self.reset_daily_if_needed()
        if lead_key not in self.daily_count and self.engine is not None:
            self._hydrate_daily_from_db(lead_key)
        return self.daily_count.get(lead_key, 0) >= self.daily_limit_for_key(lead_key)

    def _hydrate_daily_from_db(self, lead_key: str) -> None:
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        row = read_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="daily",
        )
        if row is not None:
            self.daily_count[lead_key] = int(row["value"])

    def increment_daily(self, lead_key: str) -> None:
        self.reset_daily_if_needed()
        self.daily_count[lead_key] = self.daily_count.get(lead_key, 0) + 1
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        upsert_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="daily",
            value=self.daily_count[lead_key],
            payload={"date": self.daily_date},
        )

    # ── Cooldown ───────────────────────────────────────────────────────

    def check_cooldown(self, lead_key: str) -> bool:
        if lead_key not in self.lead_last_reply and self.engine is not None:
            self._hydrate_cooldown_from_db(lead_key)
        last = self.lead_last_reply.get(lead_key, 0)
        return (self.now_func() - last) < self.cooldown_seconds_for_key(lead_key)

    def cooldown_remaining(self, lead_key: str) -> float:
        if lead_key not in self.lead_last_reply and self.engine is None:
            return 0.0
        last = self.lead_last_reply.get(lead_key, 0)
        remaining = self.cooldown_seconds_for_key(lead_key) - (self.now_func() - last)
        return max(0.0, remaining)

    def set_cooldown(self, lead_key: str) -> None:
        self.lead_last_reply[lead_key] = self.now_func()
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        upsert_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="cooldown",
            value=int(self.now_func()),
            payload={"set_at": self.now_func()},
        )

    def _hydrate_cooldown_from_db(self, lead_key: str) -> None:
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        row = read_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="cooldown",
        )
        if row is not None:
            self.lead_last_reply[lead_key] = float(row["value"])

    # ── Human pause ────────────────────────────────────────────────────

    def activate_human_pause(self, lead_key: str) -> float:
        self.human_pause[lead_key] = self.now_func()
        uid = lead_key_user_id(lead_key)
        if uid is not None and self.engine is not None:
            upsert_counter(
                self.engine,
                user_id=uid,
                lead_key=lead_key,
                kind="human_pause",
                value=int(self.now_func()),
                payload={"activated_at": self.now_func()},
            )
        return self.human_pause_seconds_for_key(lead_key)

    def is_human_paused(self, lead_key: str) -> bool:
        if lead_key not in self.human_pause and self.engine is not None:
            self._hydrate_human_pause_from_db(lead_key)
        if lead_key not in self.human_pause:
            return False
        elapsed = self.now_func() - self.human_pause[lead_key]
        if elapsed >= self.human_pause_seconds_for_key(lead_key):
            del self.human_pause[lead_key]
            return False
        return True

    def _hydrate_human_pause_from_db(self, lead_key: str) -> None:
        uid = lead_key_user_id(lead_key)
        if uid is None or self.engine is None:
            return
        row = read_counter(
            self.engine,
            user_id=uid,
            lead_key=lead_key,
            kind="human_pause",
        )
        if row is not None:
            self.human_pause[lead_key] = float(row["value"])


class SavedContactsRegistry:
    """Cache em memoria dos contatos salvos por tenant."""

    def __init__(self) -> None:
        self.contacts_by_tenant: dict[str, set[str]] = {}

    def handle_upsert(self, tenant_id: str, contacts: list[dict]) -> int:
        bucket = self.contacts_by_tenant.setdefault(tenant_id, set())
        for contact in contacts:
            jid = contact.get("jid", "")
            if jid and "@s.whatsapp.net" in jid:
                bucket.add(jid)
        return len(bucket)

    def is_saved_contact(self, tenant_id: str, jid: str) -> bool:
        return jid in self.contacts_by_tenant.get(tenant_id, set())