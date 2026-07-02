"""Audit data models."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event payload (Sprint 2.2)."""

    tenant_id: Optional[int]
    actor_id: Optional[int]
    actor_email: Optional[str]
    actor_role: str
    action: str
    entity_type: str
    entity_id: Optional[int]
    diff: dict
    ip: Optional[str]
    user_agent: Optional[str]
    metadata: dict