"""Endpoints superadmin para tenants silenciosos (Sprint 3.3).

GET    /api/superadmin/silent-tenants/                  — lista alertas OPEN
POST   /api/superadmin/silent-tenants/{id}/acknowledge   — reconhece
POST   /api/superadmin/silent-tenants/{id}/resolve       — resolve
POST   /api/superadmin/silent-tenants/run-detector       — força execução manual
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.access_control import require_superadmin
from backend.core.database import engine, get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/superadmin/silent-tenants",
    tags=["superadmin-silent-tenants"],
)


# ── Listagem ─────────────────────────────────────────────────────────────

@router.get("/")
async def list_silent_tenants(
    severity: str | None = Query(None, description="info|warning|critical"),
    alert_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    """Lista alertas OPEN com filtros opcionais."""
    where = ["ta.status = 'open'"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if severity:
        where.append("ta.severity = :severity")
        params["severity"] = severity
    if alert_type:
        where.append("ta.alert_type = :alert_type")
        params["alert_type"] = alert_type

    sql = f"""
        SELECT
          ta.id, ta.tenant_id, ta.alert_type, ta.severity,
          ta.detail, ta.criado_em, ta.atualizado_em,
          u.email, u.nome, u.plano, u.status_plano
        FROM tenant_alerts ta
        LEFT JOIN users u ON u.id = ta.tenant_id
        WHERE {' AND '.join(where)}
        ORDER BY ta.criado_em DESC
        LIMIT :limit OFFSET :offset
    """
    try:
        rows = db.execute(text(sql), params).fetchall()
    except Exception as exc:
        logger.exception("list_silent_tenants falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    alerts = [
        {
            "id": r[0],
            "tenant_id": r[1],
            "alert_type": r[2],
            "severity": r[3],
            "detail": r[4] if isinstance(r[4], dict) else {},
            "criado_em": str(r[5]) if r[5] else None,
            "atualizado_em": str(r[6]) if r[6] else None,
            "tenant_email": r[7],
            "tenant_nome": r[8],
            "tenant_plano": r[9],
            "tenant_status": r[10],
        }
        for r in rows
    ]
    return {"ok": True, "total": len(alerts), "alerts": alerts}


# ── Aggregate para widget ────────────────────────────────────────────────

@router.get("/summary")
async def summary_silent_tenants(
    db: Session = Depends(get_db),
    _: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    """Contadores agregados por severity + top 5 recentes (para widget)."""
    try:
        by_severity = dict(
            db.execute(
                text(
                    """
                    SELECT severity, COUNT(*)
                    FROM tenant_alerts
                    WHERE status = 'open'
                    GROUP BY severity
                    """
                )
            ).fetchall()
        )
        top5 = db.execute(
            text(
                """
                SELECT ta.id, ta.tenant_id, ta.alert_type, ta.severity,
                       ta.criado_em, u.email
                FROM tenant_alerts ta
                LEFT JOIN users u ON u.id = ta.tenant_id
                WHERE ta.status = 'open'
                ORDER BY ta.criado_em DESC
                LIMIT 5
                """
            )
        ).fetchall()
        top5_list = [
            {
                "id": r[0],
                "tenant_id": r[1],
                "alert_type": r[2],
                "severity": r[3],
                "criado_em": str(r[4]) if r[4] else None,
                "tenant_email": r[5],
            }
            for r in top5
        ]
        return {
            "ok": True,
            "counts": {
                "info": by_severity.get("info", 0),
                "warning": by_severity.get("warning", 0),
                "critical": by_severity.get("critical", 0),
                "total": sum(by_severity.values()),
            },
            "top5": top5_list,
        }
    except Exception as exc:
        logger.exception("summary_silent_tenants falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc


# ── Acknowledge ──────────────────────────────────────────────────────────

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    """Marca alerta como acknowledged."""
    actor_id = (user or {}).get("user_id") or (user or {}).get("id")
    try:
        result = db.execute(
            text(
                """
                UPDATE tenant_alerts
                SET status = 'acknowledged',
                    acknowledged_by = :actor,
                    acknowledged_at = NOW(),
                    atualizado_em = NOW()
                WHERE id = :alert_id AND status = 'open'
                """
            ),
            {"alert_id": alert_id, "actor": actor_id},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("acknowledge_alert falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    if (result.rowcount or 0) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Alerta {alert_id} nao encontrado ou nao esta OPEN",
        )
    return {"status": "ok", "alert_id": alert_id, "new_status": "acknowledged"}


# ── Resolve ──────────────────────────────────────────────────────────────

@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    """Marca alerta como resolved (encerrado)."""
    try:
        result = db.execute(
            text(
                """
                UPDATE tenant_alerts
                SET status = 'resolved',
                    resolved_at = NOW(),
                    atualizado_em = NOW()
                WHERE id = :alert_id
                """
            ),
            {"alert_id": alert_id},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("resolve_alert falhou")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    if (result.rowcount or 0) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Alerta {alert_id} nao encontrado",
        )
    return {"status": "ok", "alert_id": alert_id, "new_status": "resolved"}


# ── Run detector manualmente ─────────────────────────────────────────────

@router.post("/run-detector")
async def run_detector_now(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    """Forca execução do detector (util para o superadmin testar / corrigir)."""
    # Import local para evitar import circular com backend.jobs
    from backend.jobs import detect_silent_tenants

    try:
        results = detect_silent_tenants.detect_all(engine)
    except Exception as exc:
        logger.exception("run_detector_now falhou")
        raise HTTPException(status_code=500, detail=f"detector error: {exc}") from exc

    # Bonus: grava audit_events se a tabela existir (Sprint 2.2).
    try:
        actor_id = (user or {}).get("user_id") or (user or {}).get("id")
        db.execute(
            text(
                """
                INSERT INTO audit_events
                    (event_type, actor_id, payload, criado_em)
                VALUES
                    ('cron.detect_silent_tenants', :actor,
                     CAST(:payload AS jsonb), NOW())
                """
            ),
            {
                "actor": actor_id,
                "payload": (
                    '{"count":' + str(len(results)) + ', "trigger":"manual"}'
                ),
            },
        )
        db.commit()
    except Exception:
        # Se tabela nao existir, ignora silenciosamente (logger ja em DEBUG).
        db.rollback()
        logger.debug(
            "audit_events nao disponivel - run_detector manual nao auditado",
        )

    return {
        "status": "ok",
        "detected": len(results),
        "results": results,
    }
