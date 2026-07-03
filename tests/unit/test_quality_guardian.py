"""Tests para Quality Guardian agent."""

from __future__ import annotations

import pytest

from backend.agents.quality_guardian import (
    run_quality_guardian, QualityVerdict,
    AXIS_VISUAL, AXIS_CONTENT, AXIS_CONVERSION, AXIS_TECHNICAL, AXIS_ORIGINALITY,
)


HTML_GOOD = """
<html><body>
<h1>Barbearia do Zé</h1>
<a href="https://wa.me/5511999887766">WhatsApp</a>
<a href="tel:+5511999887766">Telefone</a>
<a href="https://maps.google.com/?place=barbearia">Maps</a>
<button class="rounded-full">Agendar</button>
<section class="bg-gradient-to-r from-black">Hero</section>
</body></html>
"""


class TestQualityGuardianBasics:
    def test_returns_quality_verdict(self) -> None:
        v = run_quality_guardian(HTML_GOOD)
        assert isinstance(v, QualityVerdict)

    def test_overall_score_in_range(self) -> None:
        v = run_quality_guardian(HTML_GOOD)
        assert 0.0 <= v.overall_score <= 10.0


class TestQualityGuardianDecisions:
    def test_deploy_on_high_score(self) -> None:
        v = run_quality_guardian(HTML_GOOD)
        assert v.decision in ("deploy", "deploy_with_warning")

    def test_block_on_empty(self) -> None:
        v = run_quality_guardian("")
        assert v.decision == "block"


class TestQualityGuardianFallbackFlags:
    def test_is_fallback_penalizes(self) -> None:
        v_normal = run_quality_guardian(HTML_GOOD)
        v_fallback = run_quality_guardian(HTML_GOOD, is_fallback=True)
        assert v_fallback.overall_score < v_normal.overall_score

    def test_design_context_failed_penalizes(self) -> None:
        v_normal = run_quality_guardian(HTML_GOOD)
        v_failed = run_quality_guardian(HTML_GOOD, design_context_failed=True)
        assert v_failed.overall_score < v_normal.overall_score

    def test_template_fallback_penalizes_originality(self) -> None:
        v_normal = run_quality_guardian(HTML_GOOD)
        v_fallback = run_quality_guardian(HTML_GOOD, has_template_fallback=True)
        assert v_fallback.axis_scores[AXIS_ORIGINALITY] < v_normal.axis_scores[AXIS_ORIGINALITY]


class TestQualityGuardianNoFallback:
    def test_empty_returns_issues_not_quiet_pass(self) -> None:
        v = run_quality_guardian("")
        assert len(v.issues) > 0
        assert v.decision != "deploy"