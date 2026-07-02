"""Audit endpoints — Sprint 2.2.

GET /api/superadmin/audit — lista paginada de eventos (somente superadmin).
Filtros: tenant_id, actor_id, action, entity_type, since, until, limit.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.audit.recorder import query_events
from backend.core.database import engine
from backend.core.auth import get_current_user
from backend.core.config import is_superadmin

router = APIRouter(prefix="/api/superadmin", tags=["audit"])


@router.get("/audit")
async def list_audit_events(
    request: Request,
    tenant_id: Optional[int] = Query(None),
    actor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    since: Optional[str] = Query(None, description="ISO timestamp (e.g. 2026-01-01T00:00:00)"),
    until: Optional[str] = Query(None, description="ISO timestamp (e.g. 2026-12-31T23:59:59)"),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    """Lista eventos de auditoria. Restrito a superadmin."""
    email = ""
    if isinstance(current_user, dict):
        email = str(current_user.get("email") or "")
    else:
        email = str(getattr(current_user, "email", "") or "")
    if not is_superadmin(email):
        raise HTTPException(status_code=403, detail="Acesso restrito a superadmin")
    try:
        rows = query_events(
            engine,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            since=since,
            until=until,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar auditoria: {e}")
    return {"items": rows, "count": len(rows), "limit": limit}
