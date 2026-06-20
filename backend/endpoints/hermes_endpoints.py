"""Superadmin Hermes watchdog endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.core.access_control import require_superadmin
from backend.core.config import is_superadmin
from backend.services.hermes_watchdog import (
    collect_snapshot,
    guard_check,
    list_incidents,
    record_blocked_action,
    run_scan,
)


router = APIRouter(prefix="/api/superadmin/hermes", tags=["superadmin-hermes"])


@router.get("/snapshot")
async def hermes_snapshot(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Read-only operational snapshot. Does not mutate queue/runtime."""
    return collect_snapshot(db)


@router.post("/scan")
async def hermes_scan(
    auto_remediate: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Collect read-only snapshot and append diagnostic incidents."""
    return run_scan(db, actor_id=int(user.get("id") or 0), auto_remediate=auto_remediate)


@router.post("/remediate")
async def hermes_remediate(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Run snapshot, record diagnostics and execute allowlisted playbooks only."""
    return run_scan(db, actor_id=int(user.get("id") or 0), auto_remediate=True)


@router.get("/incidents")
async def hermes_incidents(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    return {"ok": True, "incidents": list_incidents(db, limit=limit)}


@router.post("/guard/check")
async def hermes_guard_check(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    body = await request.json()
    action = body.get("action")
    command = body.get("command")
    record = bool(body.get("record"))
    if record:
        return record_blocked_action(
            db,
            action=action,
            command=command,
            actor_id=int(user.get("id") or 0),
        )
    return guard_check(action=action, command=command)


@router.get("/access-check")
async def hermes_access_check(user: dict = Depends(get_current_user)):
    email = user.get("email", "")
    return {"ok": is_superadmin(email), "email": email}
