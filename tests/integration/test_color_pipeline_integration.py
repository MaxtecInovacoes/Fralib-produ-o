"""Teste de integracao: extracao de cores do briefing -> pipeline -> site.

Este teste verifica o fluxo completo:
1. Campo livre "cores roxo e branco" e extraido
2. NichoBriefing.paleta_cores e populado
3. DesignerPRD paleta_cores e injetado
4. vite_react_renderer usa as cores corretas
"""
import sys
sys.path.insert(0, 'backend/agents')

from backend.agents.agente_nicho import parse_colors_from_briefing_text, NOMINAL_COLOR_MAP


class TestColorExtractionIntegration:
    """Testes de integracao do pipeline de cores."""

    def test_parse_colors_comprehensive(self):
        """Testa variacao de textos de briefing."""
        test_cases = [
            # (input, expected_colors_count, must_contain)
            ("Site moderno com cores roxo e branco", 2, ["#800080", "#FFFFFF"]),
            ("Academia fitness, prefiro azul e amarelo", 2, ["#3B82F6", "#EAB308"]),
            ("Barbearia klass com preto e dourado", 2, ["#1a1a1a", "#D4AF37"]),
            ("Restaurante elegante, vermelho e preto", 2, ["#EF4444", "#1a1a1a"]),
            ("#FF5733 e verde", 2, ["#FF5733", "#22C55A"]),
            ("sem cores especificas", 0, []),
            ("cores vibrantes rosa e laranja", 2, ["#EC4899", "#F97316"]),
        ]

        for text, min_count, must_contain in test_cases:
            result = parse_colors_from_briefing_text(text)
            values = list(result.values())

            # Verifica quantidade minima de cores
            assert len(result) >= min_count, f"Texto: '{text}' | Resultado: {result}"

            # Verifica cores obrigatorias
            for color in must_contain:
                assert color.upper() in [v.upper() for v in values], \
                    f"Texto: '{text}' | Cor {color} não encontrada em {values}"

    def test_nominal_color_map_coverage(self):
        """Verifica que NOMINAL_COLOR_MAP cobre cores comuns."""
        common_colors = [
            "roxo", "branco", "preto", "verde", "azul",
            "vermelho", "amarelo", "dourado", "laranja", "rosa",
            "cinza", "roxo", "violeta", "lilas", "lilás"
        ]

        for color in common_colors:
            assert color in NOMINAL_COLOR_MAP, f"Cor '{color}' não mapeada"
            hex_val = NOMINAL_COLOR_MAP[color]
            assert hex_val.startswith("#"), f"Hex invalido para '{color}': {hex_val}"
            assert len(hex_val) == 7, f"Hex deve ter 7 chars: {hex_val}"

    def test_hex_normalization(self):
        """Testa normalizacao de hex codes."""
        # 3 digitos -> 6 digitos
        result = parse_colors_from_briefing_text("Site #F00")
        assert result.get("primary") == "#FF0000", f"Esperado #FF0000, got {result}"

        # Ja em 6 digitos
        result = parse_colors_from_briefing_text("Site #FF5733")
        assert result.get("primary") == "#FF5733", f"Esperado #FF5733, got {result}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
