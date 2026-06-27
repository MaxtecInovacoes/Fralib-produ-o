"""Test: extrair cores do briefing text.

Specs:
- Dado texto "cores roxo e branco" → extrair hex codes
- Dado texto com hex codes (#FF5733) → usar direto
- Dado texto sem cores → fallback para archetype
"""
import pytest
import sys
sys.path.insert(0, 'backend/agents')

# Mapeamento de cores nominais para hex (subset para teste)
NOMINAL_COLOR_MAP = {
    "roxo": "#800080", "violeta": "#800080", "purple": "#800080",
    "branco": "#FFFFFF", "white": "#FFFFFF",
    "preto": "#000000", "black": "#000000",
    "verde": "#22C55A", "green": "#22C55A",
    "azul": "#3B82F6", "blue": "#3B82F6",
    "vermelho": "#EF4444", "red": "#EF4444",
    "amarelo": "#EAB308", "yellow": "#EAB308",
    "dourado": "#D4AF37", "gold": "#D4AF37",
    "laranja": "#F97316", "orange": "#F97316",
    "rosa": "#EC4899", "pink": "#EC4899",
    "cinza": "#6B7280", "gray": "#6B7280",
}

def parse_colors_from_text(text: str) -> dict:
    """Extrai cores do texto livre do briefing."""
    import re
    result = {}

    # 1. Hex codes diretos (#RGB ou #RRGGBB)
    hex_pattern = r'#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b'
    hex_matches = re.findall(hex_pattern, text, re.IGNORECASE)
    if hex_matches:
        hex_val = hex_matches[0]
        if len(hex_val) == 3:
            hex_val = ''.join(c*2 for c in hex_val)
        result["primary"] = f"#{hex_val.upper()}"

    # 2. Nomes de cores nominais
    text_lower = text.lower()
    found_colors = []
    for color_name, hex_code in NOMINAL_COLOR_MAP.items():
        if color_name in text_lower:
            found_colors.append((color_name, hex_code))

    # Remove duplicatas (mesmo hex)
    seen = set()
    for name, hex_code in found_colors:
        if hex_code not in seen:
            seen.add(hex_code)
            if "primary" not in result:
                result["primary"] = hex_code
            elif "secondary" not in result:
                result["secondary"] = hex_code
            elif "accent" not in result:
                result["accent"] = hex_code

    return result


class TestParseColorsFromBriefing:
    """Testes para extracao de cores do briefing."""

    def test_parses_roxo_branco(self):
        """Dado 'cores roxo e branco' deve extrair."""
        text = "Site para academia feminina, cores roxo e branco"
        result = parse_colors_from_text(text)

        # Deve ter encontrado cores
        assert len(result) >= 2, f"Expected 2+ colors, got {result}"

        # Deve conter roxo (#800080) e branco (#FFFFFF)
        values = list(result.values())
        assert "#800080" in values, f"Expected roxo #800080 in {values}"
        assert "#FFFFFF" in values, f"Expected branco #FFFFFF in {values}"

    def test_parses_hex_direct(self):
        """Dado texto com hex codes deve usar direto."""
        text = "Site com cores #FF5733 e #33FF57"
        result = parse_colors_from_text(text)

        assert "primary" in result
        assert result["primary"].upper() == "#FF5733"

    def test_empty_text_returns_empty(self):
        """Dado texto sem cores deve retornar dict vazio."""
        text = "Site moderno para barbearia"
        result = parse_colors_from_text(text)

        assert result == {} or len(result) == 0

    def test_multiple_color_names_same_hex(self):
        """Cores diferentes mas mesmo hex devem ser deduplicadas."""
        text = "cores roxo e violeta"  # Ambos = #800080
        result = parse_colors_from_text(text)

        # Só deve ter 1 cor (deduplicado)
        assert len(result) <= 1, f"Expected dedup, got {result}"


if __name__ == "__main__":
    # Rodar testes
    pytest.main([__file__, "-v"])
