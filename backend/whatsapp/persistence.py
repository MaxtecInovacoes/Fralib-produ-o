"""Persistência Postgres para os contadores de anti-abuse.

Substitui dicts in-memory do AntiAbuseGuards por UPSERT/SELECT em
rate_limit_counters. API exposta como funções puras — sem estado
interno — para que múltiplos workers do whatsapp_listener compartilhem
o mesmo estado via DB.

Toda função é tolerante a falha de DB: em caso de exception, faz
fallback para o caller (que mantém cache in-memory como fallback).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ── TTLs por tipo de contador ───────────────────────────────────────────
# Mantém tabela enxuta sem precisar de cron de GC agressivo.

TTL_FLOOD_SECONDS = 600          # 10 min — janela do flood
TTL_DAILY_SECONDS = 60 * 60 * 26 # 26 h — cobre virada de dia com folga
TTL_COOLDOWN_SECONDS = 600       # 10 min — janela máx de cooldown
TTL_HUMAN_PAUSE_SECONDS = 60 * 60  # 1 h — limite humano


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at(kind: str, base: datetime | None = None) -> datetime:
    base = base or _now_utc()
    return {
        "flood": base + timedelta(seconds=TTL_FLOOD_SECONDS),
        "daily": base + timedelta(seconds=TTL_DAILY_SECONDS),
        "cooldown": base + timedelta(seconds=TTL_COOLDOWN_SECONDS),
        "human_pause": base + timedelta(seconds=TTL_HUMAN_PAUSE_SECONDS),
    }[kind]


# ── CRUD ────────────────────────────────────────────────────────────────

def upsert_counter(
    engine: Engine,
    *,
    user_id: int,
    lead_key: str,
    kind: str,
    value: int,
    payload: dict[str, Any] | None = None,
) -> None:
    """UPSERT em rate_limit_counters. Idempotente."""
    try:
        payload_json = json.dumps(payload or {})
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO rate_limit_counters
                      (user_id, lead_key, counter_kind, counter_value, payload, expires_at)
                    VALUES
                      (:user_id, :lead_key, :kind, :value, CAST(:payload AS JSONB), :expires_at)
                    ON CONFLICT (user_id, lead_key, counter_kind) DO UPDATE
                      SET counter_value = EXCLUDED.counter_value,
                          payload       = EXCLUDED.payload,
                          expires_at    = EXCLUDED.expires_at,
                          atualizado_em = NOW()
                    """
                ),
                {
                    "user_id": user_id,
                    "lead_key": lead_key,
                    "kind": kind,
                    "value": value,
                    "payload": payload_json,
                    "expires_at": _expires_at(kind),
                },
            )
    except Exception as exc:
        logger.warning(
            "[rate_limit_counters] upsert falhou (user=%s lead=%s kind=%s): %s",
            user_id, lead_key, kind, exc,
        )


def read_counter(
    engine: Engine,
    *,
    user_id: int,
    lead_key: str,
    kind: str,
) -> dict[str, Any] | None:
    """Lê 1 contador. Retorna None se não existe ou expirou."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT counter_value, payload, expires_at
                    FROM rate_limit_counters
                    WHERE user_id = :user_id
                      AND lead_key = :lead_key
                      AND counter_kind = :kind
                      AND expires_at > NOW()
                    """
                ),
                {"user_id": user_id, "lead_key": lead_key, "kind": kind},
            ).fetchone()
        if row is None:
            return None
        payload = row[1]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return {
            "value": int(row[0]),
            "payload": payload or {},
            "expires_at": row[2],
        }
    except Exception as exc:
        logger.warning(
            "[rate_limit_counters] read falhou (user=%s lead=%s kind=%s): %s",
            user_id, lead_key, kind, exc,
        )
        return None


def delete_counter(
    engine: Engine,
    *,
    user_id: int,
    lead_key: str,
    kind: str,
) -> None:
    """Remove 1 contador (cleanup explícito)."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM rate_limit_counters
                    WHERE user_id = :user_id
                      AND lead_key = :lead_key
                      AND counter_kind = :kind
                    """
                ),
                {"user_id": user_id, "lead_key": lead_key, "kind": kind},
            )
    except Exception as exc:
        logger.warning(
            "[rate_limit_counters] delete falhou (user=%s lead=%s kind=%s): %s",
            user_id, lead_key, kind, exc,
        )


# ── Helpers de parsing do lead_key ─────────────────────────────────────

def lead_key_user_id(lead_key: str) -> int | None:
    """Extrai user_id do formato '{user_id}:{telefone}'."""
    try:
        return int(str(lead_key).split(":", 1)[0])
    except Exception:
        return None