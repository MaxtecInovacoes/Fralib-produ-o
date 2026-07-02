"""Tests for Quick Wins from auditoria_agentes_2026_07.

Validates:
  QW #1: 5 chaves no facts (pipeline_builders.py)
    - maps_url, google_maps_embed, whatsapp, phone_digits, price_range
  QW #2: "academia" deixa de ser default (benchmarker.py)
    - _match_nicho retorna None para nichos nao mapeados
    - is_fallback=True em todos consumidores
  QW #3: rating nao inventa 5.0 (vite_templates.py)
    - retorna string vazia + is_fallback=True quando rating ausente
"""
from __future__ import annotations

import pytest

from backend.services.pipeline_builders import _phone_digits, _safe_str
from backend.services.vite_templates import _visual_business_payload


class TestQWFallbackHelpers:
    """QW #1: helpers _safe_str e _phone_digits."""

    def test_safe_str_none_vazio(self) -> None:
        assert _safe_str(None) == ""

    def test_safe_str_empty_vazio(self) -> None:
        assert _safe_str("") == ""

    def test_safe_str_strip(self) -> None:
        assert _safe_str("  hello  ") == "hello"

    def test_safe_str_converte_numero(self) -> None:
        assert _safe_str(123) == "123"

    def test_safe_str_whitespace_only_vazio(self) -> None:
        assert _safe_str("   ") == ""

    def test_phone_digits_empty_vazio(self) -> None:
        assert _phone_digits("") == ""

    def test_phone_digits_none_vazio(self) -> None:
        assert _phone_digits(None) == ""

    def test_phone_digits_extrai_digitos(self) -> None:
        assert _phone_digits("+55 (11) 98765-4321") == "5511987654321"

    def test_phone_digits_preserva(self) -> None:
        assert _phone_digits("11987654321") == "11987654321"

    def test_phone_digits_lida_com_numericos(self) -> None:
        # Aceita inteiros/float vindos do banco como rating campos
        assert _phone_digits(5511987654321) == "5511987654321"


class TestQWBenchmarker:
    """QW #2: "academia" deixa de ser default silencioso."""

    def test_match_nicho_nao_mapeado_retorna_none(self) -> None:
        from backend.agents.benchmarker import _match_nicho

        assert _match_nicho("xyz-negocio-impossivel") is None

    def test_match_nicho_conhecido_retorna_chave(self) -> None:
        from backend.agents.benchmarker import _match_nicho

        # musculacao -> academia (mapping explicito)
        assert _match_nicho("Academia de musculacao") == "academia"
        # dentista -> odontologia
        assert _match_nicho("Dentista especialista") == "odontologia"
        # barbearia
        assert _match_nicho("Barbearia central") == "barbearia"

    def test_analisar_concorrencia_marca_is_fallback_em_nicho_inexistente(self) -> None:
        from backend.agents.benchmarker import analisar_concorrencia

        result = analisar_concorrencia("xyz-negocio-impossivel")
        assert result.get("is_fallback") is True
        assert result["nicho"] is None
        assert result["source"] == "fallback-explicito"

    def test_analisar_concorrencia_is_fallback_false_em_nicho_mapeado(self) -> None:
        from backend.agents.benchmarker import analisar_concorrencia

        result = analisar_concorrencia("nutricionista")
        assert result.get("is_fallback") is False
        assert result["nicho"] == "nutricionista"

    def test_get_patterns_por_nicho_is_fallback_em_nicho_inexistente(self) -> None:
        from backend.agents.benchmarker import get_patterns_por_nicho

        patterns = get_patterns_por_nicho("xyz-negocio-impossivel")
        assert patterns.get("is_fallback") is True
        # Estrutura esperada sempre presente (fallback explicito)
        assert "estrutura_comum" in patterns

    def test_get_patterns_por_nicho_is_fallback_false_em_nicho_mapeado(self) -> None:
        from backend.agents.benchmarker import get_patterns_por_nicho

        patterns = get_patterns_por_nicho("pet")
        assert patterns.get("is_fallback") is False


class TestQWViteTemplatesRating:
    """QW #3: rating nao inventa 5.0 quando ausente."""

    def test_payload_rating_ausente_string_vazia(self) -> None:
        facts = {
            "business_name": "Loja X",
            "business": {"segmento": "pet", "cidade": "Sao Paulo"},
        }
        payload = _visual_business_payload(facts)
        assert payload["rating"] == "", (
            f"rating ausente deve ser string vazia, retornou {payload['rating']!r}"
        )
        assert payload["rating_is_fallback"] is True

    def test_payload_rating_preservado_quando_existe(self) -> None:
        facts = {
            "business_name": "Loja X",
            "business": {
                "rating": 4.7,
                "total_avaliacoes": 87,
                "segmento": "pet",
                "cidade": "Sao Paulo",
            },
        }
        payload = _visual_business_payload(facts)
        assert payload["rating"] == "4.7"
        assert payload["rating_is_fallback"] is False

    def test_payload_rating_zero_e_zero(self) -> None:
        # rating 0 eh dado valido (sem avaliacoes), nao deve virar ''/5.0
        facts = {
            "business_name": "Loja Nova",
            "business": {"rating": 0, "segmento": "pet"},
        }
        payload = _visual_business_payload(facts)
        assert payload["rating"] == "0", (
            f"rating=0 deve ser preservado como '0', retornou {payload['rating']!r}"
        )
