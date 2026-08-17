"""Hunter agent — delegates to lead_supply_providers.hunter.run_hunter_job."""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session


def get_agent(*args, **kwargs):
    """Return a Hunter agent whose .run() delegates to run_hunter_job."""
    from backend.services.lead_supply_providers.hunter import run_hunter_job

    class _HunterAgent:
        def __init__(self, db: Session, payload: Dict[str, Any], tenant_id: int):
            self._db = db
            self._payload = payload
            self._tenant_id = tenant_id

        async def run(self, *args, **kwargs) -> Dict[str, Any]:
            return await run_hunter_job(self._db, self._payload, self._tenant_id)

    return _HunterAgent(*args, **kwargs)
