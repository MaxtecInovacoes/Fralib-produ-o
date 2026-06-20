"""Lead Provider Facade — factory and unified interface for all lead providers."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.services.hunter_provider import HunterProvider
from backend.services.maps_provider import MapsProvider
from backend.services.manual_provider import ManualProvider

if TYPE_CHECKING:
    pass


# ---- known provider names ----
AVAILABLE_PROVIDERS = ("hunter", "maps", "manual")
DEFAULT_PROVIDER = "hunter"


class LeadProviderFacade:
    """Unified entry point for all lead supply strategies.

    Selects the appropriate provider based on the tenant config's `provider`
    field and exposes a consistent interface:

        facade = LeadProviderFacade(db, tenant_id, config)
        candidates = await facade.search(...)
        stored = facade.store_candidates(candidates, ...)
    """

    def __init__(self, db: Session, tenant_id: int, config: dict[str, Any]):
        self.db = db
        self.tenant_id = tenant_id
        self.config = config
        self._provider = self._resolve_provider(config)

    # ---- provider factory ----

    def _resolve_provider(self, config: dict[str, Any]) -> HunterProvider | MapsProvider | ManualProvider:
        name = str(config.get("provider") or DEFAULT_PROVIDER).lower()
        if name == "maps":
            return MapsProvider(self.db, self.tenant_id, config)
        if name == "manual":
            return ManualProvider(self.db, self.tenant_id, config)
        # Default: hunter
        return HunterProvider(self.db, self.tenant_id, config)

    @property
    def provider_name(self) -> str:
        """The name of the active provider ('hunter', 'maps', or 'manual')."""
        return self._provider.name

    # ---- unified search API ----

    async def search(
        self,
        segmentos: list[str],
        cidades: list[str],
        *,
        force: bool = False,
        force_fresh: bool = False,
        batch_limit: int | None = None,
        score_minimo: int | None = None,
        existing_names: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for leads using the configured provider.

        Delegates to the provider's async `search` method.
        """
        effective_limit = batch_limit
        if effective_limit is None:
            effective_limit = max(
                1,
                min(
                    int(os.getenv("LEAD_SUPPLY_HUNTER_BATCH", "8")),
                    20,
                ),
            )
        effective_score = score_minimo
        if effective_score is None:
            effective_score = int(self.config.get("score_minimo", 45))

        return await self._provider.search(
            segmentos=segmentos,
            cidades=cidades,
            force=force,
            force_fresh=force_fresh,
            batch_limit=effective_limit,
            score_minimo=effective_score,
            existing_names=existing_names,
        )

    # ---- unified store API ----

    def store_candidates(
        self,
        candidates: list[dict[str, Any]],
        segmento: str | None = None,
        cidade: str | None = None,
    ) -> list[tuple[str, bool]]:
        """Store candidate leads using the configured provider.

        Delegates to the provider's `store_candidates` method.
        """
        return self._provider.store_candidates(candidates, segmento, cidade)

    # ---- manual-only helpers (noop for other providers) ----

    def parse_csv(
        self,
        csv_content: str | bytes,
        delimiter: str = ";",
        encoding: str = "utf-8",
    ) -> list[dict[str, Any]]:
        """Parse CSV into lead dicts (manual provider only)."""
        if not isinstance(self._provider, ManualProvider):
            return []
        return self._provider.parse_csv(csv_content, delimiter=delimiter, encoding=encoding)

    def validate_candidate(self, candidate: dict[str, Any]) -> tuple[bool, str]:
        """Validate a single candidate (manual provider only)."""
        if not isinstance(self._provider, ManualProvider):
            return True, ""
        return self._provider.validate_candidate(candidate)


# ---- module-level helpers (used by lead_supply_engine) ----

def create_facade(db: Session, tenant_id: int, config: dict[str, Any]) -> LeadProviderFacade:
    """Factory: build a LeadProviderFacade for the given tenant."""
    return LeadProviderFacade(db, tenant_id, config)


async def run_provider_search(
    db: Session,
    tenant_id: int,
    config: dict[str, Any],
    *,
    segmentos: list[str],
    cidades: list[str],
    force: bool = False,
    force_fresh: bool = False,
    batch_limit: int | None = None,
    score_minimo: int | None = None,
    existing_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Convenience: run a provider search in one call."""
    facade = LeadProviderFacade(db, tenant_id, config)
    return await facade.search(
        segmentos=segmentos,
        cidades=cidades,
        force=force,
        force_fresh=force_fresh,
        batch_limit=batch_limit,
        score_minimo=score_minimo,
        existing_names=existing_names,
    )
