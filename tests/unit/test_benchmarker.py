"""Tests for Benchmarker agent - Competitor analysis for sites."""

import sys
from pathlib import Path

import pytest

# Setup path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from agents.benchmarker import (
    analisar_concorrencia,
    get_nichos_disponiveis,
    get_patterns_por_nicho,
    NICHO_PATTERNS,
)


class TestAnalisarConcorrencia:
    """Test suite for analisar_concorrencia function."""

    def test_analisar_concorrencia_returns_dict(self):
        """Test that analisar_concorrencia returns a dictionary."""
        result = analisar_concorrencia(nicho="academia", cidade="Sao Paulo")

        assert isinstance(result, dict)
        assert "nicho" in result
        assert "cidade" in result
        assert "patterns" in result
        assert "diferenciacao_sugerida" in result
        assert "elementos_extras" in result

    def test_analisar_concorrencia_deterministic(self):
        """Test that same input always returns same output (deterministic)."""
        params = {"nicho": "nutricionista", "cidade": "Curitiba"}

        result1 = analisar_concorrencia(**params)
        result2 = analisar_concorrencia(**params)
        result3 = analisar_concorrencia(nicho="nutricionista", cidade="Curitiba")

        assert result1 == result2 == result3
        # Verify deterministic fields
        assert result1["nicho"] == result2["nicho"]
        assert result1["patterns"] == result2["patterns"]
        assert result1["diferenciacao_sugerida"] == result2["diferenciacao_sugerida"]

    def test_analisar_concorrencia_includes_patterns(self):
        """Test that result includes all expected pattern fields."""
        result = analisar_concorrencia(nicho="academia")

        patterns = result["patterns"]
        assert "estrutura_comum" in patterns
        assert "cta_predominante" in patterns
        assert "cores_tipicas" in patterns
        assert "secoes_obrigatorias" in patterns

    def test_analisar_concorrencia_academia(self):
        """Test specific niche: academia."""
        result = analisar_concorrencia(nicho="academia")

        assert result["nicho"] == "academia"
        assert "WhatsApp" in result["patterns"]["cta_predominante"]
        assert "planos" in result["patterns"]["secoes_obrigatorias"]

    def test_analisar_concorrencia_barbearia(self):
        """Test specific niche: barbearia."""
        result = analisar_concorrencia(nicho="barbearia")

        assert result["nicho"] == "barbearia"
        assert "antes/depois" in result["elementos_extras"]

    def test_analisar_concorrencia_nutricionista(self):
        """Test specific niche: nutricionista."""
        result = analisar_concorrencia(nicho="nutricionista")

        assert result["nicho"] == "nutricionista"
        assert "calculadora" in result["diferenciacao_sugerida"].lower()

    def test_analisar_concorrencia_dentista(self):
        """Test specific niche: dentista/odontologia."""
        result = analisar_concorrencia(nicho="dentista")

        assert result["nicho"] == "odontologia"
        assert "tratamentos" in result["patterns"]["secoes_obrigatorias"]

    def test_analisar_concorrencia_unknown_uses_default(self):
        """Test that unknown niche falls back explicitly (QW #2: 'academia' silencioso removido)."""
        result = analisar_concorrencia(nicho="xyz_unknown_niche_12345")

        # QW #2: nicho retorna None para indicar que nao ha mapeamento.
        # Padroes ainda usam fallback explicito internamente.
        assert result["nicho"] is None
        assert result["is_fallback"] is True
        assert result["source"] == "fallback-explicito"

    def test_analisar_concorrencia_cidade_preserved(self):
        """Test that cidade is preserved in output."""
        result = analisar_concorrencia(nicho="restaurante", cidade="Rio de Janeiro")

        assert result["cidade"] == "Rio de Janeiro"

    def test_analisar_concorrencia_empty_cidade(self):
        """Test handling of empty cidade."""
        result = analisar_concorrencia(nicho="salao", cidade="")

        assert result["cidade"] == "local"  # Default fallback

    def test_analisar_concorrencia_source_field(self):
        """Test that result includes source field."""
        result = analisar_concorrencia(nicho="farmacia")

        assert "source" in result
        assert result["source"] == "fallback-inteligente"


class TestGetNichosDisponiveis:
    """Test suite for get_nichos_disponiveis function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = get_nichos_disponiveis()
        assert isinstance(result, list)

    def test_includes_common_niches(self):
        """Test that common niches are included."""
        result = get_nichos_disponiveis()

        expected = ["academia", "barbearia", "nutricionista", "restaurante"]
        for niche in expected:
            assert niche in result

    def test_returns_string_list(self):
        """Test that list contains only strings."""
        result = get_nichos_disponiveis()
        assert all(isinstance(n, str) for n in result)

    def test_minimum_niche_count(self):
        """Test that at least 10 niches are supported."""
        result = get_nichos_disponiveis()
        assert len(result) >= 10


class TestGetPatternsPorNicho:
    """Test suite for get_patterns_por_nicho function."""

    def test_returns_patterns_dict(self):
        """Test that function returns patterns dictionary."""
        result = get_patterns_por_nicho("academia")

        assert isinstance(result, dict)
        assert "estrutura_comum" in result
        assert "cta_predominante" in result
        assert "cores_tipicas" in result
        assert "secoes_obrigatorias" in result

    def test_patterns_for_different_niches(self):
        """Test that different niches have different patterns."""
        academia = get_patterns_por_nicho("academia")
        barbearia = get_patterns_por_nicho("barbearia")

        # They should have different structures
        assert academia["estrutura_comum"] != barbearia["estrutura_comum"]
        # But same structure
        assert "cta_predominante" in academia
        assert "secoes_obrigatorias" in academia

    def test_unknown_niche_returns_default(self):
        """Test that unknown niche returns default patterns."""
        result = get_patterns_por_nicho("xyz_unknown")

        # Should return academia defaults
        assert result["estrutura_comum"] == NICHO_PATTERNS["academia"]["estrutura_comum"]

    def test_partial_match(self):
        """Test partial niche matching."""
        result = get_patterns_por_nicho("crossfit box")

        assert result["estrutura_comum"] == NICHO_PATTERNS["crossfit"]["estrutura_comum"]


class TestNichoPatterns:
    """Test suite for NICHO_PATTERNS constant."""

    def test_has_required_keys(self):
        """Test that all patterns have required keys."""
        required_keys = [
            "estrutura_comum",
            "cta_predominante",
            "cores_tipicas",
            "secoes_obrigatorias",
            "diferenciacao_sugerida",
            "elementos_extras",
        ]

        for nicho, patterns in NICHO_PATTERNS.items():
            for key in required_keys:
                assert key in patterns, f"Missing {key} in {nicho}"

    def test_cores_are_valid_hex(self):
        """Test that colors are valid hex codes."""
        import re

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

        for nicho, patterns in NICHO_PATTERNS.items():
            for color in patterns["cores_tipicas"]:
                assert hex_pattern.match(color), f"Invalid hex color {color} in {nicho}"

    def test_cta_is_valid(self):
        """Test that CTAs are valid options."""
        valid_ctas = ["WhatsApp", "Telefone", "Reserva Online", "Pedido Online"]

        for nicho, patterns in NICHO_PATTERNS.items():
            cta = patterns["cta_predominante"]
            assert cta in valid_ctas, f"Invalid CTA {cta} in {nicho}"

    def test_secoes_is_list(self):
        """Test that secoes_obrigatorias is a list."""
        for nicho, patterns in NICHO_PATTERNS.items():
            assert isinstance(patterns["secoes_obrigatorias"], list)
            assert len(patterns["secoes_obrigatorias"]) > 0

    def test_elementos_extras_is_list(self):
        """Test that elementos_extras is a list."""
        for nicho, patterns in NICHO_PATTERNS.items():
            assert isinstance(patterns["elementos_extras"], list)


class TestDeterminism:
    """Test suite for deterministic behavior verification."""

    def test_multiple_calls_same_result(self):
        """Test that multiple calls with same params always return same result."""
        params_list = [
            {"nicho": "academia", "cidade": "Sao Paulo"},
            {"nicho": "nutricionista", "cidade": "Rio"},
            {"nicho": "barbearia", "cidade": ""},
            {"nicho": "restaurante", "cidade": "Belo Horizonte"},
        ]

        for params in params_list:
            results = [analisar_concorrencia(**params) for _ in range(5)]
            # All results should be identical
            first = results[0]
            for i, result in enumerate(results[1:], 1):
                assert result == first, f"Non-deterministic at call {i+1} with {params}"

    def test_different_params_different_results(self):
        """Test that different params can produce different results."""
        result1 = analisar_concorrencia(nicho="academia")
        result2 = analisar_concorrencia(nicho="nutricionista")

        # Different niches should have different patterns
        assert result1["nicho"] != result2["nicho"]
        assert result1["patterns"]["estrutura_comum"] != result2["patterns"]["estrutura_comum"]

    def test_patterns_consistency_with_niche_matching(self):
        """Test that niche matching is consistent."""
        # Same niche variations should map to same patterns
        variations = [
            "crossfit",
            "CROSSFIT",
            "CrossFit Box",
            "box de crossfit",
        ]

        results = [analisar_concorrencia(nicho=v) for v in variations]

        # All should have same nicho
        niche_set = {r["nicho"] for r in results}
        assert len(niche_set) == 1, f"Inconsistent niche matching: {niche_set}"
