"""Teste E2E do pipeline (F1 plano 2026-07-02).

Cobre:
  - BriefingParser valida entrada
  - QualityGuardian rejeita HTML com fallbacks hardcoded
  - RetryHelper tenta 3x antes de propagar erro
  - FactualFooter levanta DadosIncompletosError se briefing incompleto
"""

from __future__ import annotations

import pytest

from backend.agents.briefing_parser import parse_briefing, BriefingParseError
from backend.agents.quality_guardian import run_quality_guardian
from backend.services.retry_helper import retry_with_backoff
from backend.services.vite_template_factual_footer import (
    build_factual_contact_data,
    DadosIncompletosError,
)


VALID_BRIEFING = {
    "business": {
        "name": "Restaurante São Jorge",
        "city": "Recife",
        "segment": "restaurante",
        "whatsapp": "81999887766",
        "address": "Rua das Laranjeiras 200",
        "maps_url": "https://maps.google.com/?place=sao-jorge",
        "price_range": "R$ 50 - R$ 120",
    },
    "tenant_id": "tenant-1",
    "tier": "PREMIUM",
}


class TestE2EPipelineValidBriefing:
    """Briefing valido passa por todas as camadas."""

    def test_briefing_parser_validates(self) -> None:
        result = parse_briefing(VALID_BRIEFING)
        assert result.business.name == "Restaurante São Jorge"
        assert result.business.city == "Recife"
        assert result.tier == "PREMIUM"

    def test_factual_contact_extracts(self) -> None:
        result = build_factual_contact_data(VALID_BRIEFING)
        assert result["whatsappHref"] == "https://wa.me/5581999887766"
        assert result["address"] == "Rua das Laranjeiras 200"
        assert result["price_range"] == "R$ 50 - R$ 120"
        assert "Recife" in result["location_kicker"]

    def test_quality_guardian_accepts_clean_html(self) -> None:
        clean_html = """
        <html><body>
        <h1>Restaurante São Jorge em Recife</h1>
        <a href="https://wa.me/5581999887766">WhatsApp</a>
        <a href="tel:+5581999887766">Telefone</a>
        <a href="https://maps.google.com/?place=sao-jorge">Maps</a>
        <button class="rounded-full">Reservar</button>
        </body></html>
        """
        verdict = run_quality_guardian(clean_html)
        assert verdict.overall_score >= 6.0
        assert verdict.decision in ("deploy", "deploy_with_warning")


class TestE2EPipelineRejectsHardcodedFallbacks:
    """Quality Guardian deve pegar HTML com fallbacks hardcoded."""

    def test_rejects_html_with_neg_negocio_local(self) -> None:
        bad_html = """
        <html><body>
        <h1>Negócio local em sua cidade</h1>
        </body></html>
        """
        verdict = run_quality_guardian(bad_html)
        # Score deve ser menor para HTML com placeholder
        assert verdict.overall_score < 8.0

    def test_rejects_empty_html(self) -> None:
        verdict = run_quality_guardian("")
        assert verdict.decision == "block"

    def test_rejects_lorem_ipsum(self) -> None:
        bad_html = "<html><body>Lorem ipsum dolor sit amet</body></html>"
        verdict = run_quality_guardian(bad_html)
        assert any("Lorem ipsum" in i.description for i in verdict.issues)


class TestE2EPipelineNoSilentFallback:
    """Camada de briefing NAO aceita dado incompleto."""

    def test_factual_footer_raises_for_missing_name(self) -> None:
        incomplete = {"business": {
            "city": "X", "segment": "y", "whatsapp": "119"
        }}
        with pytest.raises(DadosIncompletosError) as exc:
            build_factual_contact_data(incomplete)
        assert "business.name" in exc.value.missing_fields

    def test_factual_footer_raises_for_missing_contact(self) -> None:
        incomplete = {"business": {
            "name": "X", "city": "Y", "segment": "z"
        }}
        with pytest.raises(DadosIncompletosError):
            build_factual_contact_data(incomplete)

    def test_briefing_parser_rejects_invalid(self) -> None:
        with pytest.raises(BriefingParseError):
            parse_briefing({"business": {}})


class TestE2ERetryHelperPropagates:
    """retry_helper NAO usa fallback — propaga erro apos 3 tentativas."""

    def test_propagates_after_3_attempts(self) -> None:
        calls = []

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_fails() -> str:
            calls.append(1)
            raise RuntimeError("persistent")

        with pytest.raises(RuntimeError, match="persistent"):
            always_fails()
        assert len(calls) == 3

    def test_no_silent_default_returned(self) -> None:
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_fails() -> str:
            raise RuntimeError("boom")

        # NAO existe fallback retornando string vazia.
        with pytest.raises(RuntimeError):
            always_fails()