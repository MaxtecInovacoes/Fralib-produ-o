"""Audit decorator for FastAPI endpoints.

Sprint 2.2 — Aplica @audit_log em endpoints para gravar AuditEvent automatico.
Decorado simples: extrai request, user, IP do contexto FastAPI e chama record_event.
"""

import logging
from functools import wraps
from typing import Callable, Optional

from fastapi import Request

from backend.audit.models import AuditEvent
from backend.audit.recorder import record_event

logger = logging.getLogger("fralib.audit.decorators")


def _resolve_ip(request: Optional[Request]) -> Optional[str]:
    if request is None or request.client is None:
        return None
    return request.client.host


def audit_log(action: str, entity_type: str) -> Callable:
    """Decorator: registra AuditEvent apos execucao bem-sucedida do endpoint.

    Usage:
        @router.post("/api/foo")
        @audit_log("foo.create", "foo")
        async def create_foo(request: Request, current_user: User = Depends(...)):
            ...

    O decorator NAO quebra a request se a auditoria falhar (record_event e fail-safe).
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            try:
                request: Optional[Request] = kwargs.get("request")
                if request is None:
                    for a in args:
                        if isinstance(a, Request):
                            request = a
                            break
                user = kwargs.get("current_user") or kwargs.get("user")
                if isinstance(user, dict):
                    actor_id = user.get("user_id") or user.get("id")
                    actor_email = user.get("email")
                    actor_role = user.get("role") or "user"
                    tenant_id = user.get("tenant_id") or user.get("user_id") or user.get("id")
                    entity_id = user.get("id") or user.get("user_id")
                else:
                    actor_id = getattr(user, "id", None) if user is not None else None
                    actor_email = getattr(user, "email", None) if user is not None else None
                    actor_role = getattr(user, "role", None) if user is not None else "user"
                    tenant_id = getattr(user, "tenant_id", None) if user is not None else None
                    entity_id = getattr(user, "id", None) if user is not None else None
                ip = _resolve_ip(request)
                user_agent = (
                    request.headers.get("user-agent") if request is not None else None
                )
                engine = (
                    request.app.state.engine
                    if request is not None and hasattr(request.app.state, "engine")
                    else None
                )
                if engine is None:
                    logger.warning("audit_log skipped: request.app.state.engine ausente")
                    return result
                record_event(
                    engine,
                    AuditEvent(
                        tenant_id=tenant_id,
                        actor_id=actor_id,
                        actor_email=actor_email,
                        actor_role=actor_role,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        diff={},
                        ip=ip,
                        user_agent=user_agent[:255] if user_agent else None,
                        metadata={},
                    ),
                )
            except Exception as e:  # pragma: no cover - fail-safe
                logger.warning(f"audit_log decorator failed: {e}")
            return result

        return wrapper

    return decorator
