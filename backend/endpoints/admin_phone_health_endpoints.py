"""Endpoints admin (escopados por tenant) para phone-health.

Cada tenant vê apenas o próprio estado de saúde do número WhatsApp.
Não requer role=superadmin — basta estar autenticado.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from backend.core.auth import get_current_user
from backend.core.database import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/phone-health", tags=["admin-phone-health"])


def _resolve_user_id(usuario: dict) -> int:
    """Extrai user_id do token. Assume que sempre existe para usuário autenticado."""
    uid = (usuario or {}).get("user_id") or (usuario or {}).get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="user_id ausente no token")
    return int(uid)


@router.get("")
async def get_my_health(
    limit_events: int = Query(20, ge=1, le=100),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Retorna saúde atual do número WhatsApp do tenant autenticado."""
    user_id = _resolve_user_id(usuario)

    try:
        with engine.connect() as conn:
            score_row = conn.execute(
                text(
                    """
                    SELECT score, status, signals, ultima_restricao_em,
                           pause_franz_until, atualizado_em
                    FROM phone_health_score
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).fetchone()

            events_rows = conn.execute(
                text(
                    """
                    SELECT id, severity, event_type, criado_em
                    FROM phone_health_events
                    WHERE user_id = :user_id
                    ORDER BY criado_em DESC
                    LIMIT :limit
                    """
                ),
                {"user_id": user_id, "limit": limit_events},
            ).fetchall()
    except Exception as exc:
        logger.exception("get_my_health falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    if score_row is None:
        return {
            "user_id": user_id,
            "score": 100,
            "status": "healthy",
            "signals": {},
            "ultima_restricao_em": None,
            "pause_franz_until": None,
            "atualizado_em": None,
            "events": [],
            "recommendation": "Sem dados ainda — execute /cron/compute-phone-health-score.",
        }

    signals = score_row[2] if isinstance(score_row[2], dict) else {}
    score = int(score_row[0])
    status = score_row[1]
    events = [
        {
            "id": int(r[0]),
            "severity": r[1],
            "event_type": r[2],
            "criado_em": r[3].isoformat() if r[3] else None,
        }
        for r in events_rows
    ]

    return {
        "user_id": user_id,
        "score": score,
        "status": status,
        "signals": {
            "events_24h": signals.get("events_24h", 0),
            "dlq_24h": signals.get("dlq_24h", 0),
            "optouts_24h": signals.get("optouts_24h", 0),
        },
        "ultima_restricao_em": score_row[3].isoformat() if score_row[3] else None,
        "pause_franz_until": score_row[4].isoformat() if score_row[4] else None,
        "atualizado_em": score_row[5].isoformat() if score_row[5] else None,
        "events": events,
        "recommendation": _recommendation(score, status, signals),
    }


@router.post("/pause")
async def pause_my_franz(
    hours: int = Query(24, ge=1, le=168),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Pausa o Franz do próprio tenant por N horas.

    Efeito real é aplicado em até 30s (cache do listener). Para efeito
    imediato, reiniciar o serviço fralib-wpp-listener.
    """
    user_id = _resolve_user_id(usuario)

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE phone_health_score
                    SET pause_franz_until = NOW() + (:hours || ' hours')::INTERVAL,
                        atualizado_em = NOW()
                    WHERE user_id = :user_id
                    RETURNING pause_franz_until
                    """
                ),
                {"user_id": user_id, "hours": hours},
            ).fetchone()
            if result is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO phone_health_score
                          (user_id, score, status, pause_franz_until)
                        VALUES
                          (:user_id, 100, 'healthy', NOW() + (:hours || ' hours')::INTERVAL)
                        """
                    ),
                    {"user_id": user_id, "hours": hours},
                )
    except Exception as exc:
        logger.exception("pause_my_franz falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    return {
        "status": "ok",
        "user_id": user_id,
        "paused_hours": hours,
        "note": "Efeito aplicado em até 30s (cache do listener)",
    }


# ── Recomendação textual para o tenant ─────────────────────────────────

def _recommendation(score: int, status: str, signals: dict) -> str:
    """Gera recomendação automática em PT-BR baseada no estado atual."""
    events_24h = signals.get("events_24h", 0)
    dlq_24h = signals.get("dlq_24h", 0)
    optouts_24h = signals.get("optouts_24h", 0)

    if status == "banned":
        return (
            "Número provavelmente banido pelo WhatsApp. "
            "Pare todos os envios imediatamente e contate o suporte Fralib."
        )
    if status == "restricted":
        return (
            f"Score crítico ({score}/100). Recomendamos reduzir volume em 50% "
            "nas próximas 24h e revisar templates do Franz."
        )
    if status == "degraded":
        if dlq_24h > 5:
            return (
                f"Score degradado ({score}/100) com {dlq_24h} mensagens na DLQ. "
                "Recomendamos pausar campanhas outbound por 24h."
            )
        if events_24h > 10:
            return (
                f"Score degradado ({score}/100) com {events_24h} eventos de erro. "
                "Verifique se o número WhatsApp está conectado."
            )
        return f"Score abaixo do ideal ({score}/100). Monitore nas próximas horas."
    return f"Número saudável ({score}/100). Operação normal."