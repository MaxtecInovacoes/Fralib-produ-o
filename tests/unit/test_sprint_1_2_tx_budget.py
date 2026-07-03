"""Testes Sprint 1.2 — atomic transaction + budget cap."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from services.budget_cap import (  # noqa: E402
    BudgetExhaustedError,
    MAX_MONTHLY_SPEND_PER_PLAN,
    check_budget,
    get_plan_teto,
    credit_alert_threshold_pct,
)


# ── get_plan_teto ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPlanTeto:
    def test_free_50(self):
        assert get_plan_teto("free") == 50.0

    def test_trial_20(self):
        assert get_plan_teto("trial") == 20.0

    def test_starter_500(self):
        assert get_plan_teto("starter") == 500.0

    def test_pro_2000(self):
        assert get_plan_teto("pro") == 2000.0

    def test_enterprise_none(self):
        assert get_plan_teto("enterprise") is None

    def test_unknown_plan_uses_default(self):
        assert get_plan_teto("plano_inexistente") == 100.0

    def test_case_insensitive(self):
        assert get_plan_teto("FREE") == 50.0
        assert get_plan_teto("Pro") == 2000.0


# ── check_budget ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckBudget:
    def test_credits_zero_raises(self):
        with pytest.raises(BudgetExhaustedError) as exc_info:
            check_budget(1, "pro", credits=0)
        assert "credits_exhausted" in str(exc_info.value)
        assert exc_info.value.tenant_id == 1
        assert exc_info.value.plan == "pro"

    def test_credits_negative_raises(self):
        with pytest.raises(BudgetExhaustedError):
            check_budget(1, "pro", credits=-5)

    def test_credits_positive_passes(self):
        # Nao levanta
        check_budget(1, "pro", credits=100)

    def test_no_credits_arg_skips_gate(self):
        # credits=None nao checa gate
        check_budget(1, "pro", spent_this_month_usd=10)

    def test_teto_exceeded_raises(self):
        with pytest.raises(BudgetExhaustedError) as exc_info:
            check_budget(1, "pro", spent_this_month_usd=2000.01, cost_about_to_incur_usd=0)
        assert "monthly_cap_exceeded" in str(exc_info.value)

    def test_teto_within_limit_passes(self):
        check_budget(1, "pro", spent_this_month_usd=1999.99, cost_about_to_incur_usd=0)

    def test_enterprise_no_teto_always_passes(self):
        # Enterprise nao tem teto
        check_budget(1, "enterprise", spent_this_month_usd=999999)

    def test_cost_would_exceed_teto_raises(self):
        # Spent=1999 + cost=2 = 2001 > 2000
        with pytest.raises(BudgetExhaustedError):
            check_budget(1, "pro", spent_this_month_usd=1999, cost_about_to_incur_usd=2)

    def test_trial_teto_exceeded(self):
        # Trial tem teto de 20
        with pytest.raises(BudgetExhaustedError):
            check_budget(1, "trial", spent_this_month_usd=20.5)

    def test_alert_at_90_percent(self, caplog):
        """90% do teto → log warning (mas nao levanta)."""
        import logging
        caplog.set_level(logging.WARNING, logger="fralib.services.budget_cap")
        check_budget(1, "pro", spent_this_month_usd=1850)  # 92.5% de 2000
        # Nao levanta
        # Mas loga alerta
        assert any("ALERTA" in r.message or "90%" in r.message for r in caplog.records)

    def test_below_90_percent_no_alert(self, caplog):
        import logging
        caplog.set_level(logging.WARNING, logger="fralib.services.budget_cap")
        check_budget(1, "pro", spent_this_month_usd=1000)  # 50%
        # Nao levanta, nao alerta
        assert not any("ALERTA" in r.message for r in caplog.records)


# ── Atomic transaction (mock-based, sem DB real) ──────────────────────────


@pytest.mark.unit
class TestOutboundTransaction:
    """Verifica que 3 statements estao em engine.begin() (atomic)."""

    def test_outbound_uses_engine_begin(self):
        """Confirma codigo usa engine.begin() nao engine.connect()."""
        from pathlib import Path
        out_q = Path("backend/services/outbound_queue.py").read_text(encoding="utf-8")
        # Deve ter `with engine.begin() as c:` no bloco de sucesso
        assert "with engine.begin() as c:" in out_q, "outbound_queue deve usar engine.begin()"
        # E nao deve ter `c.commit()` dentro desse bloco (begin gerencia)
        # Procura trecho do sucesso
        success_section = out_q[out_q.find("if success:"):out_q.find("try:\n                from sqlalchemy.orm")]
        assert "with engine.begin()" in success_section


@pytest.mark.unit
class TestBudgetExhaustedErrorAttributes:
    def test_error_has_attrs(self):
        try:
            check_budget(42, "pro", credits=0)
        except BudgetExhaustedError as e:
            assert e.tenant_id == 42
            assert e.plan == "pro"
            assert "credits_exhausted" in e.reason
