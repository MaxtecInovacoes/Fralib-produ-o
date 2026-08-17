"""Lead supply providers package."""


PIPELINE_TYPES = ("pipeline_lead", "pipeline_multiplos", "pipeline_main")
SUPPLY_HUNTER_JOB = "lead_supply_hunter"
SUPPLY_CAIO_JOB = "lead_supply_caio"
PRODUCTION_TICK_JOB = "lead_production_tick"

PLAN_DAILY_CAPS = {
    "trial": 1,
    "free": 1,
    "starter": 6,
    "pro": 12,
    "beta": 12,
    "agency": 50,
    "ilimitado": 50,
    "admin": 50,
}

__all__ = [
    "PIPELINE_TYPES",
    "SUPPLY_HUNTER_JOB",
    "SUPPLY_CAIO_JOB",
    "PRODUCTION_TICK_JOB",
    "PLAN_DAILY_CAPS",
    "run_hunter_job",
]