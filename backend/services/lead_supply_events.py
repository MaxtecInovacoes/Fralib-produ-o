"""Lead supply events module - event logging utilities."""

from __future__ import annotations

import json
from typing import Any

from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
def _event(db: Session, tenant_id: int, source: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
    """Log an event to the lead supply events table."""
    from backend.services.lead_supply_storage import ensure_schema

    ensure_schema(db)
    db.execute(
        text(
            """
            INSERT INTO lead_supply_events (tenant_id, source, level, message, payload)
            VALUES (:uid, :source, :level, :message, CAST(:payload AS jsonb))
            """
        ),
        {
            "uid": tenant_id,
            "source": source[:40],
            "level": level[:20],
            "message": message[:1000],
            "payload": json.dumps(payload or {}, ensure_ascii=False),
        },
    )
    db.commit()
    try:
        from sse_endpoints import adicionar_log

        adicionar_log(f"[{source}] {message}", level if level in {"info", "warning", "error", "success"} else "info", user_id=tenant_id)
    except Exception:
        pass


__all__ = ["_event"]