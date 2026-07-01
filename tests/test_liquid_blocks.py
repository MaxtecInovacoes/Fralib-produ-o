"""
============================================================================
TESTES: Sistema de Blocos Líquidos - 4 Polos Estéticos
============================================================================
Testes unitários para validar inferência de polo e tokens.

Run: python -m pytest tests/test_liquid_blocks.py -v
============================================================================
"""

import pytest
import sys

sys.path.insert(0, "backend")


class TestInferAestheticPole:
    """Testes para infer_aesthetic_pole()"""

    def test_academia_returns_bold(self):
        """Academia deve retornar polo BOLD"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="academia", subniche="musculacao")
        assert result["pole"] == "bold"
        assert result["heat"] == 0.9

    def test_crossfit_returns_bold(self):
        """Crossfit deve retornar polo BOLD"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="crossfit", subniche="crossfit")
        assert result["pole"] == "bold"

    def test_barbearia_returns_soft(self):
        """Barbearia deve retornar polo SOFT"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="barbearia", subniche="barbearia_classica")
        assert result["pole"] == "soft"
        assert result["heat"] == 0.2

    def test_nutricionista_returns_soft(self):
        """Nutricionista deve retornar polo SOFT"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="nutricionista", subniche="emagrecimento")
        assert result["pole"] == "soft"

    def test_spa_returns_soft(self):
        """Spa deve retornar polo SOFT"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="spa", subniche="estetica")
        assert result["pole"] == "soft"

    def test_advogado_returns_corporate(self):
        """Advogado deve retornar polo CORPORATE"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="advogado", subniche="direito_corporativo")
        assert result["pole"] == "corporate"
        assert result["heat"] == 0.3

    def test_contabilidade_returns_corporate(self):
        """Contabilidade deve retornar polo CORPORATE"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="contabilidade", subniche="contador")
        assert result["pole"] == "corporate"

    def test_saas_returns_minimal(self):
        """SaaS deve retornar polo MINIMAL"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="saas", subniche="software")
        assert result["pole"] == "minimal"
        assert result["heat"] == 0.5

    def test_startup_returns_minimal(self):
        """Startup deve retornar polo MINIMAL"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="startup", subniche="tech")
        assert result["pole"] == "minimal"

    def test_eventos_returns_bold(self):
        """Eventos deve retornar polo BOLD"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="eventos", subniche="festivais")
        assert result["pole"] == "bold"

    def test_marketing_returns_bold(self):
        """Marketing Digital deve retornar polo BOLD"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="marketing", subniche="digital")
        assert result["pole"] == "bold"

    def test_clinica_medica_returns_corporate(self):
        """Clínica médica deve retornar polo CORPORATE"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="clinica", subniche="medicina")
        assert result["pole"] == "corporate"

    def test_pet_shop_returns_soft(self):
        """Pet Shop deve retornar polo SOFT"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        result = infer_aesthetic_pole(segment="pet_shop", subniche="pets")
        assert result["pole"] == "soft"

    def test_infer_with_tags(self):
        """Teste com tags que influenciam o resultado"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        # Tags de academia devem sobrepor segmento genérico
        result = infer_aesthetic_pole(
            segment="clinica",
            subniche="estetica",
            tags=["gym", "fitness", "musculacao"]
        )
        assert result["pole"] == "bold"

    def test_infer_with_description(self):
        """Teste com descrição que influencia o resultado"""
        from backend.services.vite_liquid_components import infer_aesthetic_pole

        # Descrição de academia deve sobrepor
        result = infer_aesthetic_pole(
            segment="clinica",
            subniche="geral",
            description="clinica de musculacao e crossfit com equipamentos modernos"
        )
        assert result["pole"] == "bold"


class TestPoleTokens:
    """Testes para POLO_TOKENS"""

    def test_polo_tokens_has_all_poles(self):
        """POLO_TOKENS deve ter todos os 4 polos"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert "soft" in POLO_TOKENS
        assert "bold" in POLO_TOKENS
        assert "corporate" in POLO_TOKENS
        assert "minimal" in POLO_TOKENS

    def test_soft_tokens_radius(self):
        """Tokens SOFT devem ter radius de 40px"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert POLO_TOKENS["soft"]["radius"] == "40px"

    def test_bold_tokens_radius(self):
        """Tokens BOLD devem ter radius de 0px"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert POLO_TOKENS["bold"]["radius"] == "0px"

    def test_corporate_tokens_radius(self):
        """Tokens CORPORATE devem ter radius de 6px"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert POLO_TOKENS["corporate"]["radius"] == "6px"

    def test_minimal_tokens_radius(self):
        """Tokens MINIMAL devem ter radius de 12px"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert POLO_TOKENS["minimal"]["radius"] == "12px"

    def test_bold_has_text_stroke(self):
        """Tokens BOLD devem ter text_stroke True"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert POLO_TOKENS["bold"]["text_stroke"] is True

    def test_bold_has_overlap(self):
        """Tokens BOLD devem ter overlap de -80px"""
        from backend.services.vite_liquid_components import POLO_TOKENS

        assert POLO_TOKENS["bold"]["overlap"] == "-80px"


class TestHeroDisplayModes:
    """Testes para HERO_DISPLAY_MODES"""

    def test_hero_display_modes_has_all_poles(self):
        """HERO_DISPLAY_MODES deve ter todos os 4 polos"""
        from backend.services.vite_liquid_components import HERO_DISPLAY_MODES

        assert "soft" in HERO_DISPLAY_MODES
        assert "bold" in HERO_DISPLAY_MODES
        assert "corporate" in HERO_DISPLAY_MODES
        assert "minimal" in HERO_DISPLAY_MODES

    def test_get_hero_display_mode_bold(self):
        """get_hero_display_mode deve retornar 'impact' para BOLD"""
        from backend.services.vite_liquid_components import get_hero_display_mode

        mode = get_hero_display_mode("bold")
        assert mode["name"] == "IMPACT"

    def test_get_hero_display_mode_soft(self):
        """get_hero_display_mode deve retornar modo centrado para SOFT"""
        from backend.services.vite_liquid_components import get_hero_display_mode

        mode = get_hero_display_mode("soft")
        assert "Centered" in mode["name"]

    def test_get_hero_display_mode_unknown_returns_default(self):
        """Modo desconhecido deve retornar primeiro disponível"""
        from backend.services.vite_liquid_components import get_hero_display_mode

        mode = get_hero_display_mode("unknown_pole")
        assert mode is not None
        assert "name" in mode


class TestTemperatureConfig:
    """Testes para TEMPERATURE_CONFIG"""

    def test_temperature_config_has_agents(self):
        """TEMPERATURE_CONFIG deve ter configurações para todos os agentes"""
        from backend.services.vite_liquid_prompts import TEMPERATURE_CONFIG

        assert "agente_variacao" in TEMPERATURE_CONFIG
        assert "arquiteto_mestre" in TEMPERATURE_CONFIG
        assert "vite_react_renderer" in TEMPERATURE_CONFIG

    def test_get_temperature_for_agent(self):
        """get_temperature_for_agent deve retornar temperatura correta"""
        from backend.services.vite_liquid_prompts import get_temperature_for_agent

        # Agente variação normal
        temp = get_temperature_for_agent("agente_variacao", "soft")
        assert temp == 0.7

        # Agente variação + BOLD = max
        temp = get_temperature_for_agent("agente_variacao", "bold")
        assert temp == 0.8

        # Arquiteto mestre
        temp = get_temperature_for_agent("arquiteto_mestre", "corporate")
        assert temp == 0.4

        # Renderer + BOLD
        temp = get_temperature_for_agent("vite_react_renderer", "bold")
        assert temp == 0.6


class TestPoleSystemPrompts:
    """Testes para POLE_SYSTEM_PROMPTS"""

    def test_pole_system_prompts_has_all_poles(self):
        """POLE_SYSTEM_PROMPTS deve ter todos os 4 polos"""
        from backend.services.vite_liquid_prompts import POLE_SYSTEM_PROMPTS

        assert "soft" in POLE_SYSTEM_PROMPTS
        assert "bold" in POLE_SYSTEM_PROMPTS
        assert "corporate" in POLE_SYSTEM_PROMPTS
        assert "minimal" in POLE_SYSTEM_PROMPTS

    def test_build_liquid_system_prompt(self):
        """build_liquid_system_prompt deve gerar prompt válido"""
        from backend.services.vite_liquid_prompts import build_liquid_system_prompt

        prompt = build_liquid_system_prompt(pole="bold", design_heat=0.9)

        assert "POLO BOLD" in prompt
        assert "QUENTE" in prompt
        assert len(prompt) > 500

    def test_build_hero_prompt(self):
        """build_hero_prompt deve gerar prompt específico para hero"""
        from backend.services.vite_liquid_prompts import build_hero_prompt

        prompt = build_hero_prompt(pole="bold", business_name="Test Gym", tagline="Train hard")

        assert "BOLD" in prompt or "bold" in prompt
        assert "Test Gym" in prompt


class TestVisualLanesIntegration:
    """Testes de integração com vite_visual_lanes"""

    def test_resolve_visual_lane_returns_pole_info(self):
        """resolve_visual_lane deve retornar informações de polo"""
        from backend.services.vite_visual_lanes import resolve_visual_lane

        # Academia
        result = resolve_visual_lane(segment="academia", subnicho="musculacao")
        assert "pole" in result
        assert result["pole"] == "bold"
        assert "pole_heat" in result
        assert "pole_tokens" in result

    def test_resolve_visual_lane_bold_heat(self):
        """Academia deve ter heat alto (0.9)"""
        from backend.services.vite_visual_lanes import resolve_visual_lane

        result = resolve_visual_lane(segment="academia", subnicho="musculacao")
        assert result["pole_heat"] >= 0.8

    def test_resolve_visual_lane_soft_heat(self):
        """Barbearia deve ter heat baixo (0.2)"""
        from backend.services.vite_visual_lanes import resolve_visual_lane

        result = resolve_visual_lane(segment="barbearia", subnicho="barbearia")
        assert result["pole_heat"] <= 0.3


class TestReactRendererIntegration:
    """Testes de integração com vite_react_renderer"""

    def test_inject_pole_tokens_function_exists(self):
        """_inject_pole_tokens deve existir"""
        from backend.services.vite_react_renderer import _inject_pole_tokens

        assert callable(_inject_pole_tokens)

    def test_inject_pole_tokens_adds_pole_info(self):
        """_inject_pole_tokens deve adicionar informações de polo aos facts"""
        from backend.services.vite_react_renderer import _inject_pole_tokens

        facts = {
            "segment": "academia",
            "subniche": "musculacao",
        }

        result = _inject_pole_tokens(facts)

        assert "pole" in result
        assert result["pole"] == "bold"
        assert "pole_heat" in result
        assert "pole_tokens" in result

    def test_get_pole_css_tokens_returns_css(self):
        """_get_pole_css_tokens deve retornar string CSS"""
        from backend.services.vite_react_renderer import _get_pole_css_tokens

        css = _get_pole_css_tokens("bold")

        assert isinstance(css, str)
        assert "POLO BOLD" in css
        assert "--" in css


class TestVitePromptsIntegration:
    """Testes de integração com vite_prompts"""

    def test_build_pole_tokens_block(self):
        """_build_pole_tokens_block deve gerar bloco de tokens"""
        from backend.services.vite_prompts import _build_pole_tokens_block

        facts = {
            "pole": "bold",
            "pole_heat": 0.9,
            "pole_display_mode": "impact",
            "pole_tokens": {"radius": "0px", "text_stroke": True},
        }

        block = _build_pole_tokens_block(facts)

        assert "POLO BOLD" in block
        assert "LIQUID DESIGN" in block
        assert "--radius" in block

    def test_build_pole_tokens_block_empty_for_no_pole(self):
        """_build_pole_tokens_block deve retornar vazio se não houver pole"""
        from backend.services.vite_prompts import _build_pole_tokens_block

        block = _build_pole_tokens_block({})
        assert block == ""

        block = _build_pole_tokens_block(None)
        assert block == ""

    def test_build_vite_react_system_prompt_with_pole(self):
        """System prompt deve incluir pole tokens quando disponível"""
        from backend.services.vite_prompts import _build_vite_react_system_prompt_with_facts

        facts = {
            "pole": "soft",
            "pole_heat": 0.2,
            "pole_display_mode": "centered",
            "pole_tokens": {"radius": "40px"},
        }

        prompt = _build_vite_react_system_prompt_with_facts(facts)

        assert "POLO SOFT" in prompt or "POLO soft" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
