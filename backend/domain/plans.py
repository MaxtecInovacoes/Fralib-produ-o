"""Canonical FraLib plan and credit contract.

Keep product limits, cooldowns and paid-plan semantics in one place so billing,
superadmin actions and pipeline gates cannot drift independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast


PlanId = Literal[
    "trial",
    "starter",
    "pro",
    "agency",
    "beta",
    "ilimitado",
    "admin",
    "free",
]


@dataclass(frozen=True, slots=True)
class PlanSpec:
    id: PlanId
    label: str
    monthly_brl: int | None
    monthly_credits: int
    cooldown_seconds: int
    has_sdr: bool
    is_paid: bool
    is_unlimited: bool = False


PLAN_SPECS: dict[PlanId, PlanSpec] = {
    "trial": PlanSpec("trial", "Trial", None, 1, 0, True, False),
    "starter": PlanSpec("starter", "Starter", 97, 180, 3600, False, True),
    "pro": PlanSpec("pro", "Pro", 197, 360, 1800, True, True),
    "agency": PlanSpec("agency", "Agency", 497, 99999, 0, True, True, True),
    "beta": PlanSpec("beta", "Beta", None, 360, 1800, True, True),
    "ilimitado": PlanSpec("ilimitado", "Ilimitado", None, 99999, 0, True, True, True),
    "admin": PlanSpec("admin", "Admin", None, 99999, 0, True, True, True),
    "free": PlanSpec("free", "Free", None, 1, 0, True, False),
}

SUBSCRIPTION_PLAN_IDS: tuple[PlanId, ...] = ("starter", "pro", "agency")
TRIAL_PLAN_IDS: frozenset[PlanId] = frozenset({"trial", "free"})
UNLIMITED_PLAN_IDS: frozenset[PlanId] = frozenset(
    plan_id for plan_id, spec in PLAN_SPECS.items() if spec.is_unlimited
)
SDR_PLAN_IDS: frozenset[PlanId] = frozenset(
    plan_id for plan_id, spec in PLAN_SPECS.items() if spec.has_sdr
)
PAID_PLAN_IDS: frozenset[PlanId] = frozenset(
    plan_id for plan_id, spec in PLAN_SPECS.items() if spec.is_paid
)

PLAN_LIMITS: dict[str, int] = {
    plan_id: spec.monthly_credits for plan_id, spec in PLAN_SPECS.items()
}
LIMITES_DIARIOS = PLAN_LIMITS
COOLDOWNS: dict[str, int] = {
    plan_id: spec.cooldown_seconds for plan_id, spec in PLAN_SPECS.items()
}
PLAN_CREDITOS_PADRAO = PLAN_LIMITS
PLANOS_ILIMITADOS = set(UNLIMITED_PLAN_IDS)
PLANOS_COM_SDR = set(SDR_PLAN_IDS)
PLANOS_TRIAL = set(TRIAL_PLAN_IDS)


def normalize_plan_id(value: str | None, *, default: PlanId = "free") -> PlanId:
    candidate = (value or default).strip().lower()
    if candidate in PLAN_SPECS:
        return cast(PlanId, candidate)
    return default


def get_plan_spec(value: str | None) -> PlanSpec:
    return PLAN_SPECS[normalize_plan_id(value)]


def is_paid_plan(value: str | None) -> bool:
    return get_plan_spec(value).is_paid
