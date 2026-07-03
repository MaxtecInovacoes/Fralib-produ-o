"""Testes Sprint 1.5 — LLM fallback + humanized delay + templates."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from agents.sdr_langgraph.fallback_templates import (  # noqa: E402
    FALLBACK_TEMPLATES,
    get_fallback,
    get_fallback_safe,
    get_all_stages,
    humanized_delay,
)


# ── Fallback templates ────────────────────────────────────────────────────


@pytest.mark.unit
class TestFallbackTemplates:
    def test_all_main_stages_have_fallback(self):
        """Stages criticos do Franz DEVEM ter fallback."""
        for stage in ["hook", "qualify", "pain", "amplify", "tease", "proof", "reveal", "close"]:
            assert stage in FALLBACK_TEMPLATES, f"Stage {stage} sem fallback"

    def test_get_fallback_returns_string(self):
        result = get_fallback("hook")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_fallback_rotates(self):
        """idx diferente retorna template diferente (se >1 variacao)."""
        a = get_fallback("hook", idx=0)
        b = get_fallback("hook", idx=1)
        # Se so tem 1 template, ambos sao iguais — nao falha
        # Se tem 2+, sao diferentes
        if len(FALLBACK_TEMPLATES["hook"]) > 1:
            assert a != b, "idx diferentes deveriam dar templates diferentes"

    def test_get_fallback_unknown_stage_returns_none(self):
        assert get_fallback("stage_inexistente") is None

    def test_get_fallback_safe_returns_default(self):
        result = get_fallback_safe("stage_inexistente")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_all_stages(self):
        stages = get_all_stages()
        assert "hook" in stages
        assert "close" in stages
        assert len(stages) >= 8

    def test_template_quality_no_placeholder(self):
        """Templates nao tem placeholder nao-substituido."""
        for stage, templates in FALLBACK_TEMPLATES.items():
            for t in templates:
                assert "{nome}" not in t, f"{stage} tem placeholder nao-substituido"
                assert "TODO" not in t, f"{stage} tem TODO"
                assert "FIXME" not in t, f"{stage} tem FIXME"


# ── Humanized delay ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestHumanizedDelay:
    def test_short_text(self):
        """Texto curto (60 chars) → ~2.0s + 60/90 = ~2.67s."""
        delay = humanized_delay("Oi tudo bem?")
        assert 2.0 <= delay <= 3.0

    def test_medium_text(self):
        """Texto medio (270 chars) → 270/90 + 2.0 = 5.0s."""
        text = "a" * 270
        delay = humanized_delay(text)
        assert 4.5 <= delay <= 5.5

    def test_long_text_capped_at_8s(self):
        """Texto muito longo (1000+ chars) → cap em 8.0s."""
        text = "a" * 1000
        delay = humanized_delay(text)
        assert delay == 8.0

    def test_empty_text_default(self):
        """Texto vazio → 2.0s (delay base)."""
        assert humanized_delay("") == 2.0

    def test_minimum_delay(self):
        """Texto de 1 char → 1/90 + 2 = ~2.01s (formula pura)."""
        # Formula: max(1.5, min(8.0, n/90 + 2.0))
        # 1/90 + 2 = 2.011, max com 1.5 = 2.011
        delay = humanized_delay("a")
        assert 1.5 <= delay <= 2.5

    def test_cap_8s(self):
        """Texto >= 540 chars → cap em 8s."""
        for n in [540, 700, 1000, 5000]:
            delay = humanized_delay("a" * n)
            assert delay == 8.0, f"n={n} deveria cap em 8.0, deu {delay}"
