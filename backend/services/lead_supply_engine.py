"""Lead inventory engine: thin wrapper re-exporting all modules.

This module maintains backward compatibility by re-exporting everything
from the modularized components:
- lead_supply_providers: Hunter, Caio, and Production tick jobs
- lead_supply_filters: Normalization and deduplication utilities
- lead_supply_storage: Schema and config management
- lead_supply_inventory: Status, candidates, locks and job handling
"""


import sys

# Re-export providers

# Re-export filters

# Re-export storage (schema and config)

# Re-export inventory operations

# Re-export _event helper (from storage, used by inventory)

# Re-export _row_to_config (from storage, used by inventory)

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


def log_pipeline_error(
    db,
    lead_id: str,
    tenant_id: int,
    step: str = None,
    exception_type: str = None,
    message: str = "",
    traceback_str: str = None,
) -> None:
    """Persiste erro de pipeline no banco (best-effort, falha nao quebra pipeline).

    Usado pelo worker (worker.py) que ja possui uma sessao SQLAlchemy aberta.
    """
    try:
        from sqlalchemy import text
        lid = str(lead_id)
        tid = int(tenant_id)
        sn = step or "UNKNOWN"
        et = exception_type or "UNKNOWN"
        msg = (message or "")[:2000]
        tb = (traceback_str or "")[:8000]

        db.execute(text("""
            INSERT INTO pipeline_error_log
                (lead_id, tenant_id, step, exception_type, message, traceback)
            VALUES (:lid, :tid, :sn, :et, :msg, :tb)
        """), {"lid": lid, "tid": tid, "sn": sn, "et": et, "msg": msg, "tb": tb})
        db.commit()
    except Exception as log_err:
        print(f"[lead_supply_engine][WARN] Falha ao registrar pipeline_error: {log_err}")

