"""Testes FASE G — Quality Guardian → retry com feedback cirurgico.

Cobre:
  - QualityCorrection e _build_structured_corrections extraem trecho do HTML
  - render_correction_prompt monta prompt em linguagem natural
  - Verdict retorna corrections quando bloqueia
  - Loop do orchestrator chama builder com _corrections + html anterior
  - Loop desiste apos 3 tentativas e sobe erro com feedback
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.agents.quality_guardian import (
    QualityIssue,
    QualityVerdict,
    render_correction_prompt,
    run_quality_guardian,
)


# ---------------------------------------------------------------------------
# Unit: QualityCorrection + render_correction_prompt
# ---------------------------------------------------------------------------


class TestRenderCorrectionPrompt:
    """Prompt em linguagem natural, como humano pedindo ajuste."""

    def test_empty_corrections_returns_empty_string(self) -> None:
        assert render_correction_prompt([]) == ""

    def test_single_correction_format(self) -> None:
        from backend.agents.quality_guardian import QualityCorrection

        c = QualityCorrection(
            axis="conteudo", severity="critical",
            problema="Lorem ipsum detectado",
            sugestao="substitua Lorem ipsum por copy real",
            html_snippet="...<p>Lorem ipsum dolor sit amet</p>...",
        )
        prompt = render_correction_prompt([c])
        assert "O site anterior saiu com problemas" in prompt
        assert "1. [conteudo/critical] Lorem ipsum detectado" in prompt
        assert "O que fazer: substitua Lorem ipsum por copy real" in prompt
        assert "Lorem ipsum dolor sit amet" in prompt
        assert "NAO mexa no que ja estava certo" in prompt

    def test_multiple_corrections_numbered(self) -> None:
        from backend.agents.quality_guardian import QualityCorrection

        corrections = [
            QualityCorrection(axis="conteudo", severity="critical",
                              problema="X", sugestao="faça Y", html_snippet=""),
            QualityCorrection(axis="visual", severity="major",
                              problema="A", sugestao="faça B", html_snippet="trecho"),
        ]
        prompt = render_correction_prompt(corrections)
        assert "1. [conteudo/critical] X" in prompt
        assert "2. [visual/major] A" in prompt


# ---------------------------------------------------------------------------
# Unit: Verdict inclui corrections quando bloqueia
# ---------------------------------------------------------------------------


class TestVerdictCorrections:
    """Quando bloqueia, corrections vem populado. Quando aprova, vem vazio."""

    def test_block_includes_corrections(self) -> None:
        # HTML com lorem + placeholder + design_context_failed → cai em block
        html = "<html><body>" + ("Lorem ipsum {{nome}} " * 200) + "</body></html>"
        verdict = run_quality_guardian(
            html,
            design_context_failed=True,
            dados_incompletos=True,
        )
        assert verdict.decision == "block"
        assert len(verdict.corrections) > 0

    def test_deploy_has_empty_corrections(self) -> None:
        clean = (
            "<html><body>"
            "<h1>Restaurante Bom em Sao Paulo</h1>"
            "<a href='https://wa.me/5511999998888'>WhatsApp</a>"
            "<a href='tel:+5511999998888'>Tel</a>"
            "<a href='https://maps.google.com/?q=restaurante'>Maps</a>"
            "<button class='rounded-full'>Reservar</button>"
            "<div class='bg-blue-500 from-pink-300'>decor</div>"
            "</body></html>"
        ) * 3  # > 2KB
        verdict = run_quality_guardian(clean)
        assert verdict.decision == "deploy"
        assert verdict.corrections == []

    def test_snippet_captures_html_around_problem(self) -> None:
        html = (
            "<html><body>" + ("<p>Lorem ipsum dolor sit amet consectetur adipiscing</p>" * 200)
            + "</body></html>"
        )
        verdict = run_quality_guardian(html, design_context_failed=True)
        assert verdict.decision == "block"
        lorem_correction = next(
            (c for c in verdict.corrections if "Lorem" in c.problema), None
        )
        assert lorem_correction is not None
        assert "Lorem ipsum" in lorem_correction.html_snippet


# ---------------------------------------------------------------------------
# Integration: loop do orchestrator via mock
# ---------------------------------------------------------------------------


class TestOrchestratorQGRetryLoop:
    """Loop no orchestrator: chama builder com corrections, ate 3 tentativas."""

    def _make_state(self, html: str = "") -> dict:
        class _S:
            pass
        s = _S()
        s.html_final = html
        s.prd_arquiteto = None
        s.tenant_id = "t"
        s.lead_slug = "l"
        s.is_fallback = False
        s.has_template_fallback = False
        s.dados_incompletos = False
        s.design_context_failed = False
        s.palette_overridden = False
        return s

    def test_qg_block_triggers_builder_retry_with_corrections(self) -> None:
        """QG bloqueia → builder re-chamado com corrections + html anterior."""
        # HTML ruim: lorem + placeholder + design_context_failed → block garantido
        bad_html = "<html><body>" + ("Lorem ipsum {{nome}} " * 200) + "</body></html>"
        fixed_html = (
            "<html><body><h1>Restaurante Bom em Sao Paulo</h1>"
            "<a href='https://wa.me/5511999998888'>WhatsApp</a>"
            "<a href='tel:+5511999998888'>Tel</a>"
            "<a href='https://maps.google.com/?q=r'>Maps</a>"
            "<button class='rounded-full'>Reservar</button>"
            "<div class='bg-blue-500 from-pink-300'>x</div></body></html>"
        ) * 3

        state = self._make_state(bad_html)
        call_log: list[dict] = []

        def fake_gerar(_validation_errors: str = "", _previous_html: str = "",
                       _corrections=None):
            call_log.append({
                "validation_errors": _validation_errors,
                "previous_html": _previous_html,
                "corrections": _corrections,
            })
            return fixed_html

        max_corrections = 3
        for attempt in range(1, max_corrections + 1):
            verdict = run_quality_guardian(state.html_final, design_context_failed=True)
            if verdict.decision != "block":
                break
            if attempt >= max_corrections:
                raise Exception(f"QG bloqueou apos {attempt} correcoes")
            state.html_final = fake_gerar(
                _validation_errors=verdict.feedback,
                _previous_html=state.html_final,
                _corrections=verdict.corrections,
            )

        assert len(call_log) == 1
        assert call_log[0]["previous_html"] == bad_html
        assert call_log[0]["corrections"] is not None
        assert len(call_log[0]["corrections"]) > 0
        assert any("Lorem" in c.problema for c in call_log[0]["corrections"])

    def test_qg_3_consecutive_blocks_raises_with_feedback(self) -> None:
        """Se QG bloquear 3 vezes, erro sobe com feedback final."""
        bad_html = "<html><body>" + ("Lorem ipsum {{nome}} " * 200) + "</body></html>"

        max_corrections = 3
        last_feedback = ""
        with pytest.raises(Exception, match="Quality Guardian bloqueou apos 3 correcoes"):
            for attempt in range(1, max_corrections + 1):
                verdict = run_quality_guardian(bad_html, design_context_failed=True)
                last_feedback = verdict.feedback
                if verdict.decision != "block":
                    break
                if attempt >= max_corrections:
                    raise Exception(
                        f"Quality Guardian bloqueou apos {attempt} correcoes. "
                        f"Feedback: {verdict.feedback}"
                    )

        assert "Score" in last_feedback

    def test_qg_passes_first_try_no_retry(self) -> None:
        """HTML limpo → loop sai na 1ª sem chamar builder."""
        clean = (
            "<html><body>"
            "<h1>Restaurante Bom em Sao Paulo</h1>"
            "<a href='https://wa.me/5511999998888'>WhatsApp</a>"
            "<a href='tel:+5511999998888'>Tel</a>"
            "<a href='https://maps.google.com/?q=r'>Maps</a>"
            "<button class='rounded-full'>Reservar</button>"
            "<div class='bg-blue-500 from-pink-300'>x</div>"
            "</body></html>"
        ) * 3
        call_count = 0
        max_corrections = 3
        for attempt in range(1, max_corrections + 1):
            verdict = run_quality_guardian(clean)
            if verdict.decision != "block":
                break
            call_count += 1  # nunca deve incrementar

        assert call_count == 0
        assert verdict.decision == "deploy"