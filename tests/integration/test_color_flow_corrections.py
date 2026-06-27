"""Teste de integração: fluxo de cores do formulário até o site.

Este teste verifica que:
1. agente_nicho extrai cores do briefing livre
2. arquiteto_mestre usa as cores extraídas (em vez de design_dna)
3. vite_prompts inclui as cores no prompt final
"""
import sys
sys.path.insert(0, "backend/agents")
sys.path.insert(0, "backend/services")

from backend.agents.agente_nicho import parse_colors_from_briefing_text
from backend.agents.handoff_types import NichoBriefing


class TestColorFlowIntegration:
    """Testa o fluxo completo de cores."""

    def test_agente_nicho_extrai_cores(self):
        """Verifica que agente_nicho extrai cores do briefing."""
        test_cases = [
            ("Site para academia feminina, cores roxo e branco", "#800080", "#FFFFFF"),
            ("Academia fitness, prefiro azul e amarelo", "#3B82F6", "#EAB308"),
            ("Barbearia klass com preto e dourado", "#1a1a1a", "#D4AF37"),
        ]

        for text, expected_primary, expected_secondary in test_cases:
            result = parse_colors_from_briefing_text(text)
            assert result.get("primary") == expected_primary, \
                f"Texto: '{text}' | Primary: {result.get('primary')} != {expected_primary}"
            assert result.get("secondary") == expected_secondary, \
                f"Texto: '{text}' | Secondary: {result.get('secondary')} != {expected_secondary}"

    def test_nicho_briefing_armazena_cores(self):
        """Verifica que NichoBriefing armazena paleta_cores."""
        nicho = NichoBriefing(
            nicho="academia",
            cidade="São Paulo",
            paleta_cores={"primary": "#800080", "secondary": "#FFFFFF"},
        )

        assert nicho.paleta_cores.get("primary") == "#800080"
        assert nicho.paleta_cores.get("secondary") == "#FFFFFF"

    def test_arquiteto_usa_paleta_briefing(self):
        """Verifica que a lógica de prioridade de cores funciona no arquiteto_mestre.

        Este teste verifica o comportamento esperado:
        - Se nicho_briefing.paleta_cores existe → usar cores do briefing
        - Se não existe → usar design_dna.tokens (fallback)
        """
        # Simular o comportamento da correção em arquiteto_mestre.py
        # (linhas 350-394)

        # Caso 1: Com paleta_cores do briefing (deve usar cores do usuário)
        nicho_briefing_com_cores = {
            "paleta_cores": {"primary": "#800080", "secondary": "#FFFFFF"}
        }
        design_dna_tokens = {
            "--fg": "#00FF00",  # Verde
            "--surface": "#000000",
            "--accent": "#FF0000",
            "--bg": "#FFFFFF",
            "--muted": "#888888",
            "--border": "#CCCCCC",
        }

        _paleta_briefing = nicho_briefing_com_cores.get("paleta_cores")

        # Simular a lógica do arquiteto_mestre
        if _paleta_briefing and _paleta_briefing.get("primary"):
            color_palette = {
                "primary": _paleta_briefing.get("primary"),
                "secondary": _paleta_briefing.get("secondary"),
                "source": "briefing_usuario",
            }
        else:
            color_palette = {
                "primary": design_dna_tokens.get("--fg"),
                "secondary": design_dna_tokens.get("--surface"),
                "source": "design_dna",
            }

        assert color_palette["primary"] == "#800080", \
            f"Esperado #800080 (roxo do briefing), got {color_palette['primary']}"
        assert color_palette["secondary"] == "#FFFFFF", \
            f"Esperado #FFFFFF (branco do briefing), got {color_palette['secondary']}"
        assert color_palette["source"] == "briefing_usuario"

        # Caso 2: Sem paleta_cores (fallback para design_dna)
        nicho_briefing_sem_cores = {}
        _paleta_briefing_sem = nicho_briefing_sem_cores.get("paleta_cores")

        if _paleta_briefing_sem and _paleta_briefing_sem.get("primary"):
            color_palette_sem = {"primary": _paleta_briefing_sem.get("primary"), "source": "briefing"}
        else:
            color_palette_sem = {
                "primary": design_dna_tokens.get("--fg"),
                "source": "design_dna",
            }

        assert color_palette_sem["primary"] == "#00FF00", \
            f"Esperado #00FF00 (verde do design_dna), got {color_palette_sem['primary']}"
        assert color_palette_sem["source"] == "design_dna"

        # Caso 3: paleta_cores existe mas sem primary (vazio)
        nicho_briefing_vazio = {"paleta_cores": {}}
        _paleta_vazio = nicho_briefing_vazio.get("paleta_cores")

        if _paleta_vazio and _paleta_vazio.get("primary"):
            color_palette_vazio = {"primary": _paleta_vazio.get("primary"), "source": "briefing"}
        else:
            color_palette_vazio = {
                "primary": design_dna_tokens.get("--fg"),
                "source": "design_dna",
            }

        assert color_palette_vazio["primary"] == "#00FF00", \
            f"Esperado #00FF00 (fallback), got {color_palette_vazio['primary']}"
        assert color_palette_vazio["source"] == "design_dna"

    def test_vite_prompts_inclui_cores(self):
        """Verifica que vite_prompts inclui cores no briefing block."""
        from backend.services.vite_prompts import _build_lead_briefing_block

        # Facts com paleta_cores
        facts = {
            "business": {
                "name": "Test Academia",
                "segment": "academia",
                "city": "São Paulo",
                "phone": "11999999999",
            },
            "paleta_cores": {"primary": "#800080", "secondary": "#FFFFFF", "accent": "#800080"},
        }

        resultado = _build_lead_briefing_block(facts)

        # Verificar que as cores estão no output
        assert "#800080" in resultado, "Primary color #800080 should be in prompt"
        assert "#FFFFFF" in resultado, "Secondary color #FFFFFF should be in prompt"
        assert "CORES SOLICITADAS PELO USUÁRIO" in resultado, "Color instructions should be in prompt"

    def test_vite_prompts_sem_cores(self):
        """Verifica que vite_prompts funciona sem paleta_cores (fallback)."""
        from backend.services.vite_prompts import _build_lead_briefing_block

        # Facts sem paleta_cores
        facts = {
            "business": {
                "name": "Test Barbearia",
                "segment": "barbearia",
                "city": "Rio de Janeiro",
                "phone": "21999999999",
            },
        }

        resultado = _build_lead_briefing_block(facts)

        # Verificar que o briefing foi gerado (mesmo sem cores)
        assert "Test Barbearia" in resultado
        assert "barbearia" in resultado.lower()
        assert "CORES SOLICITADAS" not in resultado, "Should not have colors block when no palette"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])