"""Cálculo do phone_health_score por tenant.

Lógica pura (sem dependência de FastAPI) — chamada pelo endpoint cron
e pelos testes unitários.

Fontes de sinal (últimas 24h):
  - phone_health_events: peso por severity (info=0, warn=5, error=15, critical=40)
  - outbound_queue em DLQ: peso 10 por item
  - opt-outs (sdr_stage='opt_out'): peso 8 por item

Score = max(0, 100 - soma). Thresholds em whatsapp.guards.STATUS_THRESHOLDS.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from whatsapp.guards import EVENT_WEIGHTS, score_to_status

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantHealthSnapshot:
    """Resultado do cálculo para 1 tenant."""
    user_id: int
    score: int
    status: str
    events_weight: int
    dlq_weight: int
    optout_weight: int
    total_weight: int
    events_24h: int
    dlq_24h: int
    optouts_24h: int


def compute_health_score(engine: Engine, user_id: int) -> TenantHealthSnapshot:
    """Calcula score de 1 tenant."""
    events_weight, events_24h = _sum_events_weight(engine, user_id)
    dlq_weight, dlq_24h = _count_dlq(engine, user_id)
    optout_weight, optouts_24h = _count_optouts(engine, user_id)
    total_weight = events_weight + dlq_weight + optout_weight
    score = max(0, 100 - total_weight)
    status = score_to_status(score)
    return TenantHealthSnapshot(
        user_id=user_id,
        score=score,
        status=status,
        events_weight=events_weight,
        dlq_weight=dlq_weight,
        optout_weight=optout_weight,
        total_weight=total_weight,
        events_24h=events_24h,
        dlq_24h=dlq_24h,
        optouts_24h=optouts_24h,
    )


def persist_health_score(engine: Engine, snap: TenantHealthSnapshot) -> None:
    """UPSERT em phone_health_score. Auto-pausa Franz se score=0 (banned).

    Auto-pause é freio de emergência: quando o número provavelmente foi banido,
    o cron pausa automaticamente o Franz por 24h. O superadmin pode desfazer
    via /api/superadmin/phone-health/{id}/pause?hours=0.
    """
    signals = {
        "events_24h": snap.events_24h,
        "dlq_24h": snap.dlq_24h,
        "optouts_24h": snap.optouts_24h,
        "events_weight": snap.events_weight,
        "dlq_weight": snap.dlq_weight,
        "optout_weight": snap.optout_weight,
        "total_weight": snap.total_weight,
    }

    auto_pause_until = None
    if snap.status == "banned":
        # Auto-pausa: 24h. Não sobrescreve pause manual já existente que
        # seja mais longo (cap superior).
        auto_pause_until = "GREATEST(COALESCE(pause_franz_until, NOW() - INTERVAL '1 second'), NOW() + INTERVAL '24 hours')"

    with engine.begin() as conn:
        if auto_pause_until is not None:
            conn.execute(
                text(
                    f"""
                    INSERT INTO phone_health_score
                      (user_id, score, status, signals, pause_franz_until, atualizado_em)
                    VALUES
                      (:user_id, :score, :status, CAST(:signals AS JSONB), NOW() + INTERVAL '24 hours', NOW())
                    ON CONFLICT (user_id) DO UPDATE
                      SET score             = EXCLUDED.score,
                          status            = EXCLUDED.status,
                          signals           = EXCLUDED.signals,
                          pause_franz_until = {auto_pause_until},
                          atualizado_em     = NOW()
                    """
                ),
                {
                    "user_id": snap.user_id,
                    "score": snap.score,
                    "status": snap.status,
                    "signals": json.dumps(signals),
                },
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO phone_health_score
                      (user_id, score, status, signals, atualizado_em)
                    VALUES
                      (:user_id, :score, :status, CAST(:signals AS JSONB), NOW())
                    ON CONFLICT (user_id) DO UPDATE
                      SET score         = EXCLUDED.score,
                          status        = EXCLUDED.status,
                          signals       = EXCLUDED.signals,
                          atualizado_em = NOW()
                    """
                ),
                {
                    "user_id": snap.user_id,
                    "score": snap.score,
                    "status": snap.status,
                    "signals": json.dumps(signals),
                },
            )

        # Log do auto-pause (event append-only)
        if snap.status == "banned":
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO phone_health_events
                          (user_id, severity, event_type, detail)
                        VALUES
                          (:user_id, 'critical', 'auto_paused',
                           CAST(:detail AS JSONB))
                        """
                    ),
                    {
                        "user_id": snap.user_id,
                        "detail": json.dumps({
                            "reason": "score=0",
                            "score": snap.score,
                            "auto_pause_hours": 24,
                        }),
                    },
                )
            except Exception as exc:
                logger.warning(
                    "[phone_health] insert auto_paused event falhou (user=%s): %s",
                    snap.user_id, exc,
                )


def compute_all_tenants(engine: Engine) -> list[TenantHealthSnapshot]:
    """Calcula score para todos os tenants ativos. Idempotente."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id FROM users WHERE status = 'active'")
        ).fetchall()
    snapshots: list[TenantHealthSnapshot] = []
    for row in rows:
        uid = int(row[0])
        snap = compute_health_score(engine, uid)
        persist_health_score(engine, snap)
        snapshots.append(snap)
    return snapshots


# ── Helpers internos ───────────────────────────────────────────────────

def _sum_events_weight(engine: Engine, user_id: int) -> tuple[int, int]:
    """Soma pesos de phone_health_events últimas 24h. Retorna (peso, count)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT severity, COUNT(*) AS n
                FROM phone_health_events
                WHERE user_id = :user_id
                  AND criado_em > NOW() - INTERVAL '24 hours'
                GROUP BY severity
                """
            ),
            {"user_id": user_id},
        ).fetchall()
    weight = 0
    count = 0
    for row in rows:
        sev = str(row[0])
        n = int(row[1])
        weight += EVENT_WEIGHTS.get(sev, 0) * n
        count += n
    return weight, count


def _count_dlq(engine: Engine, user_id: int) -> tuple[int, int]:
    """Conta outbound_queue em DLQ últimas 24h. Retorna (peso, count)."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM outbound_queue
                    WHERE user_id = :user_id
                      AND status = 'dlq'
                      AND atualizado_em > NOW() - INTERVAL '24 hours'
                    """
                ),
                {"user_id": user_id},
            ).fetchone()
        n = int(row[0]) if row else 0
        return n * 10, n
    except Exception as exc:
        logger.warning("[phone_health] _count_dlq falhou (user=%s): %s", user_id, exc)
        return 0, 0


def _count_optouts(engine: Engine, user_id: int) -> tuple[int, int]:
    """Conta leads com sdr_stage='opt_out' criadas últimas 24h."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM leads
                    WHERE user_id = :user_id
                      AND sdr_stage = 'opt_out'
                      AND criado_em > NOW() - INTERVAL '24 hours'
                    """
                ),
                {"user_id": user_id},
            ).fetchone()
        n = int(row[0]) if row else 0
        return n * 8, n
    except Exception as exc:
        logger.warning("[phone_health] _count_optouts falhou (user=%s): %s", user_id, exc)
        return 0, 0