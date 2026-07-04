"""Endpoints superadmin para phone-health (visão de toda a frota).

Permite ao superadmin ver a saúde do número WhatsApp de todos os tenants
e intervir manualmente quando necessário (freio de emergência).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.auth import get_current_user
from backend.core.database import engine, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/superadmin/phone-health", tags=["superadmin-phone-health"])


def require_superadmin(usuario: dict) -> None:
    """Verifica que o requester é superadmin."""
    if not usuario:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    role = (usuario or {}).get("role", "")
    is_su = (usuario or {}).get("is_superadmin", False)
    if role != "superadmin" and not is_su:
        raise HTTPException(status_code=403, detail="Acesso restrito a superadmin")


@router.get("")
async def list_tenant_health(
    status: str | None = Query(None, description="Filtra por status: healthy|degraded|restricted|banned"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Lista todos os tenants com score atual. Top 5 em risco no topo."""
    require_superadmin(usuario)

    params: dict[str, Any] = {"limit": limit}
    where = "1=1"
    if status:
        where = "phs.status = :status"
        params["status"] = status

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT
                      u.id AS user_id,
                      u.email,
                      COALESCE(phs.score, 100) AS score,
                      COALESCE(phs.status, 'healthy') AS status,
                      phs.ultima_restricao_em,
                      phs.pause_franz_until,
                      phs.atualizado_em,
                      COALESCE(phs.signals, '{{}}'::jsonb) AS signals
                    FROM users u
                    LEFT JOIN phone_health_score phs ON phs.user_id = u.id
                    WHERE u.status = 'active' AND {where}
                    ORDER BY phs.score ASC NULLS FIRST
                    LIMIT :limit
                    """
                ),
                params,
            ).fetchall()
    except Exception as exc:
        logger.exception("list_tenant_health falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    tenants = []
    for row in rows:
        signals = row[7] if isinstance(row[7], dict) else {}
        tenants.append(
            {
                "user_id": int(row[0]),
                "email": row[1],
                "score": int(row[2]),
                "status": row[3],
                "ultima_restricao_em": row[4].isoformat() if row[4] else None,
                "pause_franz_until": row[5].isoformat() if row[5] else None,
                "atualizado_em": row[6].isoformat() if row[6] else None,
                "events_24h": signals.get("events_24h", 0),
                "dlq_24h": signals.get("dlq_24h", 0),
                "optouts_24h": signals.get("optouts_24h", 0),
            }
        )

    return {
        "tenants": tenants,
        "total": len(tenants),
        "top_5_risk": tenants[:5],
    }


@router.get("/{tenant_id}/events")
async def get_tenant_events(
    tenant_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Últimos eventos de saúde do tenant."""
    require_superadmin(usuario)

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, severity, event_type, detail, criado_em
                    FROM phone_health_events
                    WHERE user_id = :user_id
                    ORDER BY criado_em DESC
                    LIMIT :limit
                    """
                ),
                {"user_id": tenant_id, "limit": limit},
            ).fetchall()
    except Exception as exc:
        logger.exception("get_tenant_events falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    events = []
    for row in rows:
        detail = row[3] if isinstance(row[3], dict) else {}
        events.append(
            {
                "id": int(row[0]),
                "severity": row[1],
                "event_type": row[2],
                "detail": detail,
                "criado_em": row[4].isoformat() if row[4] else None,
            }
        )
    return {"user_id": tenant_id, "events": events}


@router.post("/{tenant_id}/pause")
async def pause_tenant_franz(
    tenant_id: int,
    hours: int = Query(24, ge=1, le=168, description="Horas de pausa (1-168)"),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Pausa o Franz de um tenant por N horas. Freio de emergência.

    Insere em phone_health_score.pause_franz_until. O whatsapp_listener
    deve checar essa coluna antes de enviar (a ser integrado no Passo B
    ou em sprint posterior).
    """
    require_superadmin(usuario)

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
                {"user_id": tenant_id, "hours": hours},
            ).fetchone()
            if result is None:
                # Sem score ainda — cria linha default
                conn.execute(
                    text(
                        """
                        INSERT INTO phone_health_score
                          (user_id, score, status, pause_franz_until)
                        VALUES
                          (:user_id, 100, 'healthy', NOW() + (:hours || ' hours')::INTERVAL)
                        ON CONFLICT (user_id) DO UPDATE
                          SET pause_franz_until = EXCLUDED.pause_franz_until
                        """
                    ),
                    {"user_id": tenant_id, "hours": hours},
                )
    except Exception as exc:
        logger.exception("pause_tenant_franz falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    return {
        "status": "ok",
        "user_id": tenant_id,
        "paused_hours": hours,
        "pause_until": (result[0].isoformat() if result else None),
    }