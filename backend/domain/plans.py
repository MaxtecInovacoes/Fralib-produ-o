"""
Planos de assinatura — specs reais (NAO stub).

Cakto e o unico payment provider. Valores em BRL (R$).
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SubscriptionPlanSpec:
    """Especificacao completa de um plano de assinatura."""
    id: str
    label: str
    monthly_brl: float
    monthly_credits: int
    trial_days: int
    max_retries: int
    retry_interval_days: int
    sdr_allowed: bool
    sdr_cooldown_min: int
    features: list = field(default_factory=list)


SUBSCRIPTION_PLAN_IDS = ["free", "starter", "pro", "agency"]

PLAN_SPECS: dict[str, SubscriptionPlanSpec] = {
    "free": SubscriptionPlanSpec(
        id="free",
        label="Free",
        monthly_brl=0.0,
        monthly_credits=3,
        trial_days=0,
        max_retries=0,
        retry_interval_days=0,
        sdr_allowed=False,
        sdr_cooldown_min=0,
        features=["site_unico"],
    ),
    "starter": SubscriptionPlanSpec(
        id="starter",
        label="Starter",
        monthly_brl=97.0,
        monthly_credits=3,
        trial_days=7,
        max_retries=3,
        retry_interval_days=3,
        sdr_allowed=True,
        sdr_cooldown_min=10,
        features=["site_unico", "sdr_whatsapp"],
    ),
    "pro": SubscriptionPlanSpec(
        id="pro",
        label="Pro",
        monthly_brl=197.0,
        monthly_credits=10,
        trial_days=7,
        max_retries=3,
        retry_interval_days=3,
        sdr_allowed=True,
        sdr_cooldown_min=5,
        features=["site_5_paginas", "sdr_whatsapp", "blog_auto"],
    ),
    "agency": SubscriptionPlanSpec(
        id="agency",
        label="Agency",
        monthly_brl=497.0,
        monthly_credits=999,
        trial_days=0,
        max_retries=3,
        retry_interval_days=3,
        sdr_allowed=True,
        sdr_cooldown_min=3,
        features=[
            "site_ilimitado",
            "sdr_whatsapp",
            "blog_auto",
            "afiliados",
        ],
    ),
}

# Mapa de sinonimos (ex: "trial" no banco → "free")
PLAN_ALIASES: dict[str, str] = {
    "trial": "free",
    "gratis": "free",
    "ilimitado": "agency",
    "admin": "agency",
    "beta": "free",
}


def get_plan_spec(plan_id: str) -> Optional[SubscriptionPlanSpec]:
    """Resolve plan_id (ou alias) para SubscriptionPlanSpec."""
    lookup = (plan_id or "").lower().strip()
    spec = PLAN_SPECS.get(lookup)
    if spec:
        return spec
    resolved = PLAN_ALIASES.get(lookup)
    return PLAN_SPECS.get(resolved) if resolved else None


def is_paid_plan(plan_id: str) -> bool:
    """Retorna True se o plano e pago (tem mensalidade > 0)."""
    spec = get_plan_spec(plan_id)
    return bool(spec and spec.monthly_brl > 0)
