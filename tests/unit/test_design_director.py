"""Tests for design_director.py - Design Director Agent."""

from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _disable_design_cache(monkeypatch):
    monkeypatch.setattr(
        "backend.agents.design_director._cache_get",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "backend.agents.design_director._cache_set",
        lambda *_args, **_kwargs: None,
    )


class TestGerarDirecaoCriativa:
    """Test suite for gerar_direcao_criativa() function."""

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_returns_valid_direction_structure(
        self, mock_design_context, mock_call_claude
    ):
        """Test that function returns expected structure with all required keys."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = {
            "dir_key": "cafe",
            "tokens": {"--bg": "oklch(97% 0.003 30)", "--accent": "oklch(28% 0.034 25)"},
            "font_heading": "Poppins",
            "font_body": "Poppins",
            "animation_profile": {"hero_type": "fade-up"},
            "hero_style": {"layout": "hero-split"},
            "craft": {},
            "vibe": "aconchegante",
            "animation": "elegante",
        }

        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#D4866A"}}'

        result = gerar_direcao_criativa(
            nicho="restaurante",
            cidade="Sao Paulo",
            nome_negocio="Restaurante Teste",
        )

        assert "direcao_visual" in result
        assert "motion_style" in result
        assert "tom_de_voz" in result
        assert "estrutura_unica" in result
        assert "design_tokens" in result

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_uses_design_tokens_when_available(
        self, mock_design_context, mock_call_claude
    ):
        """Test that design_tokens are injected into result when available."""
        from backend.agents.design_director import gerar_direcao_criativa

        expected_tokens = {
            "dir_key": "editorial",
            "tokens": {"--bg": "oklch(100% 0.0 0)"},
            "font_heading": "Gelasio",
            "font_body": "Gelasio",
            "animation_profile": {"hero_type": "fade-up"},
            "hero_style": {"layout": "hero-center"},
            "craft": {},
            "vibe": "revista",
            "animation": "elegante",
        }
        mock_design_context.return_value = expected_tokens
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#333"}}'

        result = gerar_direcao_criativa(
            nicho="nutricionista",
            cidade="Rio de Janeiro",
            nome_negocio="Nutri Vida",
        )

        assert result["design_tokens"] is not None
        assert result["design_tokens"]["dir_key"] == "editorial"
        assert result["design_tokens"]["source"] == "design_context"

    @patch("backend.agents.design_director.call_claude")
    def test_fallback_deterministic_for_nutricionista(self, mock_call_claude):
        """Test that fallback returns deterministic palette for nicho."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_call_claude.side_effect = Exception("LLM fails")

        result = gerar_direcao_criativa(
            nicho="nutricionista",
            cidade="Sao Paulo",
            nome_negocio="Nutri Test",
        )

        assert result["direcao_visual"]["paleta_primaria"] == "#7A9B7E"
        assert result["direcao_visual"]["paleta_secundaria"] == "#F5F1E8"
        assert result["direcao_visual"]["paleta_acento"] == "#D4866A"

    @patch("backend.agents.design_director.call_claude")
    def test_fallback_deterministic_for_dentista(self, mock_call_claude):
        """Test that fallback returns correct palette for dentista niche."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_call_claude.side_effect = Exception("LLM fails")

        result = gerar_direcao_criativa(
            nicho="dentista",
            cidade="Curitiba",
            nome_negocio="Odonto Plus",
        )

        assert result["direcao_visual"]["paleta_primaria"] == "#1A2B4A"
        assert result["direcao_visual"]["paleta_acento"] == "#C9A961"

    @patch("backend.agents.design_director.call_claude")
    def test_fallback_deterministic_for_academia(self, mock_call_claude):
        """Test that fallback returns correct palette for academia niche."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_call_claude.side_effect = Exception("LLM fails")

        result = gerar_direcao_criativa(
            nicho="academia",
            cidade="Belo Horizonte",
            nome_negocio="Fit Power",
        )

        assert result["direcao_visual"]["paleta_primaria"] == "#0A0A0A"
        assert result["direcao_visual"]["paleta_acento"] == "#FFD60A"

    @patch("backend.agents.design_director.call_claude")
    def test_fallback_returns_default_for_unknown_niche(self, mock_call_claude):
        """Test that fallback returns default palette for unknown niche."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_call_claude.side_effect = Exception("LLM fails")

        result = gerar_direcao_criativa(
            nicho="unknown_niche_xyz",
            cidade="Sao Paulo",
            nome_negocio="Negocio Desconhecido",
        )

        assert result["direcao_visual"]["paleta_primaria"] == "#3B82F6"
        assert result["direcao_visual"]["paleta_acento"] == "#10B981"

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_fallback_includes_design_tokens_when_available(
        self, mock_design_context, mock_call_claude
    ):
        """Test that fallback also injects design_tokens if they were obtained."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = {
            "dir_key": "minimal",
            "tokens": {"--bg": "oklch(98% 0.0 0)"},
            "font_heading": "Inter",
            "font_body": "Inter",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "clean",
            "animation": "elegante",
        }
        mock_call_claude.side_effect = Exception("LLM fails")

        result = gerar_direcao_criativa(
            nicho="farmacia",
            cidade="Porto Alegre",
            nome_negocio="Farmacia Central",
        )

        assert result["design_tokens"] is not None
        assert result["design_tokens"]["source"] == "design_context_fallback"

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_parses_json_with_markdown_fences(
        self, mock_design_context, mock_call_claude
    ):
        """Test that JSON with markdown fences is parsed correctly."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = None
        mock_call_claude.return_value = """```json
{"direcao_visual":{"paleta_primaria":"#FF6B6B","estilo":"bold"}}
```"""

        result = gerar_direcao_criativa(
            nicho="barbearia",
            cidade="Recife",
            nome_negocio="Barbearia Nova",
        )

        assert result["direcao_visual"]["paleta_primaria"] == "#FF6B6B"
        assert result["direcao_visual"]["estilo"] == "bold"

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_detects_dark_mode_for_academia_niche(
        self, mock_design_context, mock_call_claude
    ):
        """Test that dark_mode is True for academia niche."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.assert_not_called()
        mock_design_context.return_value = {
            "dir_key": "bold",
            "tokens": {},
            "font_heading": "Archivo Black",
            "font_body": "Inter",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "energetic",
            "animation": "energetico",
        }
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#000"}}'

        gerar_direcao_criativa(
            nicho="academia",
            cidade="Sao Paulo",
            nome_negocio="Academia Forte",
        )

        call_kwargs = mock_design_context.call_args
        assert call_kwargs[1]["dark_mode"] is True

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_detects_dark_mode_for_barbearia_niche(
        self, mock_design_context, mock_call_claude
    ):
        """Test that dark_mode is True for barbearia niche."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = {
            "dir_key": "luxury",
            "tokens": {},
            "font_heading": "Inter",
            "font_body": "Inter",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "premium",
            "animation": "elegante",
        }
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#111"}}'

        gerar_direcao_criativa(
            nicho="barbearia",
            cidade="Sao Paulo",
            nome_negocio="Barbearia Style",
        )

        call_kwargs = mock_design_context.call_args
        assert call_kwargs[1]["dark_mode"] is True

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_light_mode_for_nutricionista_niche(
        self, mock_design_context, mock_call_claude
    ):
        """Test that dark_mode is False for nutricionista niche."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = {
            "dir_key": "friendly",
            "tokens": {},
            "font_heading": "Poppins",
            "font_body": "Poppins",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "acolhedor",
            "animation": "elegante",
        }
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#7A9B7E"}}'

        gerar_direcao_criativa(
            nicho="nutricionista",
            cidade="Sao Paulo",
            nome_negocio="Nutri Saude",
        )

        call_kwargs = mock_design_context.call_args
        assert call_kwargs[1]["dark_mode"] is False

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_includes_tier_in_design_context_call(
        self, mock_design_context, mock_call_claude
    ):
        """Test that tier parameter is passed to design_context."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = {
            "dir_key": "minimal",
            "tokens": {},
            "font_heading": "Inter",
            "font_body": "Inter",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "clean",
            "animation": "elegante",
        }
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#333"}}'

        gerar_direcao_criativa(
            nicho="farmacia",
            cidade="Sao Paulo",
            nome_negocio="Farmacia Vida",
            tier="PREMIUM",
        )

        call_kwargs = mock_design_context.call_args
        assert call_kwargs[1]["tier"] == "PREMIUM"

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_includes_dados_lead_in_design_context_call(
        self, mock_design_context, mock_call_claude
    ):
        """Test that dados_lead is passed to design_context."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.return_value = {
            "dir_key": "cafe",
            "tokens": {},
            "font_heading": "Poppins",
            "font_body": "Poppins",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "aconchegante",
            "animation": "elegante",
        }
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#D4866A"}}'

        dados_lead = {"rating": 4.5, "total_avaliacoes": 120}

        gerar_direcao_criativa(
            nicho="restaurante",
            cidade="Sao Paulo",
            nome_negocio="Restaurante Gourmet",
            dados_lead=dados_lead,
        )

        call_kwargs = mock_design_context.call_args
        assert call_kwargs[1]["dados_lead"] == dados_lead

    @patch("backend.agents.design_director.call_claude")
    @patch("backend.agents.design_director.get_design_context")
    def test_design_context_failure_uses_fallback(
        self, mock_design_context, mock_call_claude
    ):
        """Test that design_context failure gracefully falls back."""
        from backend.agents.design_director import gerar_direcao_criativa

        mock_design_context.side_effect = Exception("DB connection failed")
        mock_call_claude.return_value = '{"direcao_visual":{"paleta_primaria":"#FF0000"}}'

        result = gerar_direcao_criativa(
            nicho="nutricionista",
            cidade="Sao Paulo",
            nome_negocio="Nutri Test",
        )

        assert "direcao_visual" in result
        assert result["design_tokens"] is None


class TestFallbackDirection:
    """Test suite for _fallback_direction helper."""

    def test_returns_valid_structure(self):
        """Test that fallback returns all required keys."""
        from backend.agents.design_director import _fallback_direction

        result = _fallback_direction("generic")

        assert "direcao_visual" in result
        assert "motion_style" in result
        assert "tom_de_voz" in result
        assert "estrutura_unica" in result
        assert "anti_repeticao" in result

    def test_motion_style_has_required_fields(self):
        """Test that motion_style has all required motion fields."""
        from backend.agents.design_director import _fallback_direction

        result = _fallback_direction("academia")

        assert "intensidade" in result["motion_style"]
        assert "efeito_principal" in result["motion_style"]
        assert "scroll_speed" in result["motion_style"]

    def test_estrutura_unica_has_ordem_secoes(self):
        """Test that estrutura_unica has ordem_secoes."""
        from backend.agents.design_director import _fallback_direction

        result = _fallback_direction("restaurante")

        assert "ordem_secoes" in result["estrutura_unica"]
        assert isinstance(result["estrutura_unica"]["ordem_secoes"], list)
        assert len(result["estrutura_unica"]["ordem_secoes"]) > 0

    def test_with_design_tokens_injects_them(self):
        """Test that design_tokens are injected into fallback result."""
        from backend.agents.design_director import _fallback_direction

        tokens = {
            "dir_key": "bold",
            "tokens": {"--bg": "oklch(0% 0.0 0)"},
            "font_heading": "Archivo Black",
            "font_body": "Inter",
            "animation_profile": {},
            "hero_style": {},
            "craft": {},
            "vibe": "energetic",
            "animation": "energetico",
        }

        result = _fallback_direction("academia", design_tokens=tokens)

        assert result["design_tokens"] is not None
        assert result["design_tokens"]["dir_key"] == "bold"
