"""Audit recorder — writes to audit_events table."""

import json
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import text

from backend.audit.models import AuditEvent

logger = logging.getLogger("fralib.audit.recorder")


def record_event(engine, event: AuditEvent) -> None:
    """Insert one audit event. Fail-safe: never raises (logs warning on DB error).

    Uses ``engine.begin()`` so the INSERT is wrapped in an explicit
    transaction that auto-commits on success and auto-rollbacks on error,
    preventing zombie transactions on transient failures.
    """
    try:
        diff_json = json.dumps(event.diff or {})
        metadata_json = json.dumps(event.metadata or {})
        sql = text(
            """
            INSERT INTO audit_events (
                tenant_id, actor_id, actor_email, actor_role, action,
                entity_type, entity_id, diff_json, ip, user_agent, metadata
            ) VALUES (
                :tenant_id, :actor_id, :actor_email, :actor_role, :action,
                :entity_type, :entity_id, :diff_json, :ip, :user_agent, :metadata
            )
            """
        )
        with engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "tenant_id": event.tenant_id,
                    "actor_id": event.actor_id,
                    "actor_email": event.actor_email,
                    "actor_role": event.actor_role,
                    "action": event.action,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "diff_json": diff_json,
                    "ip": event.ip,
                    "user_agent": event.user_agent,
                    "metadata": metadata_json,
                },
            )
    except Exception as e:  # pragma: no cover - fail-safe
        logger.warning(f"Audit DB error (action={event.action}): {e}")


def query_events(
    engine,
    *,
    tenant_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query audit_events with optional filters. Returns list of dicts."""
    where_clauses = []
    params: Dict[str, Any] = {"limit": limit}
    if tenant_id is not None:
        where_clauses.append("tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id
    if actor_id is not None:
        where_clauses.append("actor_id = :actor_id")
        params["actor_id"] = actor_id
    if action is not None:
        where_clauses.append("action = :action")
        params["action"] = action
    if entity_type is not None:
        where_clauses.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    if since is not None:
        where_clauses.append("criado_em >= :since")
        params["since"] = since
    if until is not None:
        where_clauses.append("criado_em <= :until")
        params["until"] = until

    sql = "SELECT * FROM audit_events"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY criado_em DESC LIMIT :limit"

    with engine.connect() as conn:
        result = conn.execute(text(sql), params).fetchall()
        # convert rows to dicts
        return [dict(row._mapping) for row in result]


def record_login(
    engine,
    *,
    user_id: Optional[int],
    email: Optional[str],
    ip: Optional[str],
    user_agent: Optional[str],
    action: str = "auth.login",
) -> None:
    """Shortcut for auth.login / auth.logout."""
    record_event(
        engine,
        AuditEvent(
            tenant_id=None,
            actor_id=user_id,
            actor_email=email,
            actor_role="user",
            action=action,
            entity_type="user",
            entity_id=user_id,
            diff={},
            ip=ip,
            user_agent=user_agent,
            metadata={},
        ),
    )


def record_tenant_change(
    engine,
    *,
    actor_id: int,
    tenant_id: int,
    before: dict,
    after: dict,
    ip: Optional[str],
) -> None:
    """Shortcut for tenant settings change — emits diff of {key: [before, after]}."""
    diff = {k: [before.get(k), after.get(k)] for k in set((before or {}) | (after or {}))}
    record_event(
        engine,
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=None,
            actor_role="admin",
            action="tenant.update_settings",
            entity_type="tenant_settings",
            entity_id=tenant_id,
            diff=diff,
            ip=ip,
            user_agent=None,
            metadata={},
        ),
    )


def record_lead_change(
    engine,
    *,
    actor_id: int,
    tenant_id: int,
    lead_id: int,
    action: str,
    diff: dict,
    ip: Optional[str],
) -> None:
    """Shortcut for lead create/update/delete."""
    record_event(
        engine,
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=None,
            actor_role="admin",
            action=action,
            entity_type="lead",
            entity_id=lead_id,
            diff=diff or {},
            ip=ip,
            user_agent=None,
            metadata={},
        ),
    )