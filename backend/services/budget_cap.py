"""Sprint 1.2: budget cap por plano.

Problema P0: credits=0 só notifica, não bloqueia chamadas LLM.
Risco: $$$ ilimitado se um tenant spammar simulador.

Fix:
  - MAX_MONTHLY_SPEND_PER_PLAN: dict plano -> USD maximo/mes (None = sem teto)
  - BudgetExhaustedError: levantada quando credits <= 0 OU gasto_mes >= teto
  - check_budget(tenant_id, plan) -> raises se excedeu

Usado em:
  - ia_manager.py: antes de chamar LLM, chama check_budget
  - simulador Franz: se budget exhausted, retorna 429
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("fralib.services.budget_cap")

# Teto mensal em USD por plano (None = sem teto, ex: enterprise)
MAX_MONTHLY_SPEND_PER_PLAN: dict[str, Optional[float]] = {
    "free": 50.0,
    "trial": 20.0,
    "starter": 500.0,
    "pro": 2000.0,
    "enterprise": None,  # sem teto
    # Fallback para planos desconhecidos
    "_default": 100.0,
}


class BudgetExhaustedError(Exception):
    """Levantada quando tenant excedeu budget mensal OU credits = 0."""

    def __init__(self, tenant_id: int, plan: str, reason: str):
        self.tenant_id = tenant_id
        self.plan = plan
        self.reason = reason
        super().__init__(
            f"BudgetExhausted: tenant={tenant_id} plan={plan} reason={reason}"
        )


def get_plan_teto(plan: str) -> Optional[float]:
    """Retorna teto mensal em USD para o plano. None = sem teto."""
    p = (plan or "").lower().strip()
    if p in MAX_MONTHLY_SPEND_PER_PLAN:
        return MAX_MONTHLY_SPEND_PER_PLAN[p]
    return MAX_MONTHLY_SPEND_PER_PLAN["_default"]


def check_budget(
    tenant_id: int,
    plan: str,
    *,
    credits: Optional[int] = None,
    spent_this_month_usd: Optional[float] = None,
    cost_about_to_incur_usd: float = 0.0,
) -> None:
    """Verifica se tenant pode fazer chamada LLM. Levanta BudgetExhaustedError se nao.

    Args:
        tenant_id: ID do tenant
        plan: nome do plano (free, trial, starter, pro, enterprise)
        credits: creditos restantes (None = nao checa credit gate)
        spent_this_month_usd: gasto do mes ate agora (None = nao checa teto)
        cost_about_to_incur_usd: custo estimado da chamada que vai fazer

    Raises:
        BudgetExhaustedError: se credits <= 0 OU spent + cost > teto
    """
    # Gate 1: credits = 0 (assinatura acabou)
    if credits is not None and credits <= 0:
        logger.warning(
            f"[budget_cap] tenant={tenant_id} plan={plan} credits={credits} — BLOQUEADO"
        )
        raise BudgetExhaustedError(
            tenant_id=tenant_id, plan=plan, reason="credits_exhausted"
        )

    # Gate 2: teto mensal do plano
    teto = get_plan_teto(plan)
    if teto is None:
        return  # sem teto (enterprise)

    if spent_this_month_usd is not None:
        total = spent_this_month_usd + cost_about_to_incur_usd
        if total > teto:
            logger.warning(
                f"[budget_cap] tenant={tenant_id} plan={plan} "
                f"spent=${spent_this_month_usd:.2f} + cost=${cost_about_to_incur_usd:.4f} "
                f"= ${total:.2f} > teto ${teto:.2f} — BLOQUEADO"
            )
            raise BudgetExhaustedError(
                tenant_id=tenant_id, plan=plan, reason="monthly_cap_exceeded"
            )

    # Gate 3: alerta 10% do teto
    if spent_this_month_usd is not None and teto > 0:
        pct = spent_this_month_usd / teto
        if pct >= 0.9:
            logger.warning(
                f"[budget_cap] tenant={tenant_id} plan={plan} "
                f"spent=${spent_this_month_usd:.2f} / teto ${teto:.2f} "
                f"= {pct*100:.1f}% (>90%) — ALERTA"
            )


def credit_alert_threshold_pct() -> float:
    """Threshold de alerta quando credits < 10% do limite."""
    return float(os.getenv("BUDGET_ALERT_THRESHOLD_PCT", "10")) / 100.0
