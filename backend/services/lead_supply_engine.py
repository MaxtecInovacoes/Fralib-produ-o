"""Lead inventory engine: thin wrapper re-exporting all modules.

This module maintains backward compatibility by re-exporting everything
from the modularized components:
- lead_supply_providers: Hunter, Caio, and Production tick jobs
- lead_supply_filters: Normalization and deduplication utilities
- lead_supply_storage: Schema and config management
- lead_supply_inventory: Status, candidates, locks and job handling
"""

from __future__ import annotations

import sys

# Re-export providers
from backend.services.lead_supply_providers import (
    PIPELINE_TYPES,
    PLAN_DAILY_CAPS,
    PRODUCTION_TICK_JOB,
    SUPPLY_CAIO_JOB,
    SUPPLY_HUNTER_JOB,
    run_hunter_job,
)
from backend.services.lead_supply_providers.caio import run_caio_job
from backend.services.lead_supply_providers.maps import run_production_tick

# Re-export filters
from backend.services.lead_supply_filters import (
    _slug,
    dedupe_key,
    default_targets,
    normalize_list,
)

# Re-export storage (schema and config)
from backend.services.lead_supply_storage import (
    ensure_schema,
    get_or_create_config,
    save_config,
    get_user_plan,
    set_pause,
)

# Re-export inventory operations
from backend.services.lead_supply_inventory import (
    status,
    sync_supply,
    _store_candidate,
    _enqueue_caio,
    _existing_names,
    _reserve_next,
    _ensure_lead_row,
    _lead_to_dict,
    _compute_live_status,
    handle_pipeline_job_finished,
    reap_stale_inventory_locks,
    enqueue_hunter,
    enqueue_production_tick,
)

# Re-export _event helper (from storage, used by inventory)
from backend.services.lead_supply_storage import _event

# Re-export _row_to_config (from storage, used by inventory)
from backend.services.lead_supply_storage import _row_to_config

__all__ = [
    # Constants
    "PIPELINE_TYPES",
    "SUPPLY_HUNTER_JOB",
    "SUPPLY_CAIO_JOB",
    "PRODUCTION_TICK_JOB",
    "PLAN_DAILY_CAPS",
    # Providers
    "run_hunter_job",
    "run_caio_job",
    "run_production_tick",
    # Filters
    "normalize_list",
    "default_targets",
    "dedupe_key",
    "_slug",
    # Storage
    "ensure_schema",
    "get_or_create_config",
    "save_config",
    "get_user_plan",
    "set_pause",
    "status",
    "sync_supply",
    "_store_candidate",
    "_enqueue_caio",
    "_existing_names",
    "_reserve_next",
    "_ensure_lead_row",
    "_lead_to_dict",
    "_compute_live_status",
    "handle_pipeline_job_finished",
    "reap_stale_inventory_locks",
    "enqueue_hunter",
    "enqueue_production_tick",
    "_event",
    "_row_to_config",
]

# Backward compatibility alias (used by lead_supply_endpoints)
lead_supply_engine = sys.modules[__name__]

