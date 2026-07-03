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


def _parse_iso_ts(value: Optional[str], field_name: str) -> Optional[datetime]:
    """Valida e parseia ISO timestamp. Retorna 422 se inválido."""
    if value is None or value == "":
        return None
    try:
        # Aceita tanto "2026-01-01T00:00:00" quanto "2026-01-01 00:00:00"
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} invalido (esperado ISO 8601, ex: '2026-01-01T00:00:00'): {exc}",
        )


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
    # Bug #6 fix: rejeita email vazio/None explicitamente (era bypass)
    if not email or not is_superadmin(email):
        raise HTTPException(status_code=403, detail="Acesso restrito a superadmin")
    # Bug #5 fix: valida ISO timestamps antes de mandar pro SQL
    since_dt = _parse_iso_ts(since, "since")
    until_dt = _parse_iso_ts(until, "until")
    since_iso = since_dt.isoformat() if since_dt else None
    until_iso = until_dt.isoformat() if until_dt else None
    try:
        rows = query_events(
            engine,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            since=since_iso,
            until=until_iso,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar auditoria: {e}")
    return {"items": rows, "count": len(rows), "limit": limit}
