"""Manual/manual provider for lead supply engine."""

from __future__ import annotations

from typing import Any

from backend.core.db_imports import Session  # noqa: F401  — B3 DRY


def run_manual_job(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    """Manual provider - placeholder for manual lead insertion."""
    from backend.services.lead_supply_storage import _event

    _event(db, tenant_id, "manual", "info", "Provider manual não suportado ainda")
    return {"ok": False, "error": "manual_provider_not_supported"}