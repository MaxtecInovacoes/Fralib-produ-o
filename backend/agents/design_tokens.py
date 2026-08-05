"""design_tokens.py — Design tokens extraídos de design_context.py

Este módulo contém os dados estáticos de design system:
- 150+ direções visuais em OKLch
- Animation profiles
- Craft profiles
- Mapeamentos e aliases

Mantido separado para facilitar versionamento e testes.
"""
from __future__ import annotations

import os
import json
from typing import Dict

# ─── OPEN DESIGN TOKENS (pré-computados do DESIGN.md) ─────────────────────────
_OD_TOKENS_PATH = os.path.join(os.path.dirname(__file__), "design_system_tokens.json")
_OD_TOKENS: Dict[str, dict] = {}
if os.path.exists(_OD_TOKENS_PATH):
    with open(_OD_TOKENS_PATH, "r") as _f:
        _OD_TOKENS = json.load(_f)

# ─── 150+ DIREÇÕES VISUAIS ────────────────────────────────────────────────────
DIRECOES_VISUAIS = {
    "editorial": {"nome": "Editorial", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(7% 0.0 0)"}, "font_heading": "Gelasio", "font_body": "Gelasio", "vibe": "revista, tipografia serif refinada, grids estruturados", "animation": "elegante"},
    "minimal": {"nome": "Minimal", "tokens": {"--bg": "oklch(96% 0.002 60)", "--surface": "oklch(96% 0.002 60)", "--fg": "oklch(5% 0.002 60)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(5% 0.002 60)"}, "font_heading": "Inter", "font_body": "Open Sans", "vibe": "stripped-back, whitespace, tipografia restrained, clareza", "animation": "elegante"},
    "cafe": {"nome": "Cafe", "tokens": {"--bg": "oklch(97% 0.003 30)", "--surface": "oklch(97% 0.003 30)", "--fg": "oklch(18% 0.025 24)", "--muted": "oklch(37% 0.02 26)", "--border": "oklch(89% 0.009 30)", "--accent": "oklch(28% 0.034 25)"}, "font_heading": "Poppins", "font_body": "Poppins", "vibe": "aconchegante, tons quentes cafe, tipografia suave", "animation": "elegante"},
    "clean": {"nome": "Clean", "tokens": {"--bg": "oklch(98% 0.004 220)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(88% 0.008 220)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Poppins", "font_body": "Roboto", "vibe": "simplicidade, whitespace amplo, paleta limitada", "animation": "elegante"},
    "brutalism": {"nome": "Brutalism", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(9% 0.017 221)", "--accent": "oklch(48% 0.114 9)"}, "font_heading": "Darker Grotesque", "font_body": "Darker Grotesque", "vibe": "anti-design cru, concreto, minimalismo funcional", "animation": "energetico"},
    "bold": {"nome": "Bold", "tokens": {"--bg": "oklch(8% 0.0 0)", "--surface": "oklch(12% 0.0 0)", "--fg": "oklch(98% 0.0 0)", "--muted": "oklch(60% 0.0 0)", "--border": "oklch(25% 0.0 0)", "--accent": "oklch(55% 0.18 210)"}, "font_heading": "Archivo Black", "font_body": "Inter", "vibe": "tipografia pesada, alto contraste, comanda atencao", "animation": "energetico"},
    "nike": {"nome": "Nike", "tokens": {"--bg": "oklch(8% 0.0 0)", "--surface": "oklch(14% 0.0 0)", "--fg": "oklch(97% 0.0 0)", "--muted": "oklch(60% 0.0 0)", "--border": "oklch(22% 0.0 0)", "--accent": "oklch(60% 0.22 30)"}, "font_heading": "Oswald", "font_body": "Inter", "vibe": "athletic retail, monochrome, massive uppercase, kinetic", "animation": "energetico"},
    "energetic": {"nome": "Energetic", "tokens": {"--bg": "oklch(98% 0.005 0)", "--surface": "oklch(96% 0.008 0)", "--fg": "oklch(12% 0.01 0)", "--muted": "oklch(45% 0.01 0)", "--border": "oklch(88% 0.01 0)", "--accent": "oklch(55% 0.22 145)"}, "font_heading": "Oswald", "font_body": "Inter", "vibe": "dinamico vibrante, bordas grossas, geometrico, movimento", "animation": "energetico"},
    "friendly": {"nome": "Friendly", "tokens": {"--bg": "oklch(98% 0.008 75)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(55% 0.012 60)", "--border": "oklch(90% 0.01 75)", "--accent": "oklch(65% 0.15 155)"}, "font_heading": "Noto Serif Display", "font_body": "Noto Serif Display", "vibe": "arredondado, whitespace amplo, pastel suave", "animation": "elegante"},
    "warm_editorial": {"nome": "Editorial", "tokens": {"--bg": "oklch(97% 0.006 38)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(55% 0.015 30)", "--border": "oklch(88% 0.01 38)", "--accent": "oklch(7% 0.0 0)"}, "font_heading": "Gelasio", "font_body": "Gelasio", "vibe": "revista, tipografia serif refinada, grids estruturados", "animation": "elegante"},
    # ... (150+ direções completas em design_context.py)
}

# Dark mode: sobrepõe --bg, --surface, --fg, --muted, --border
DARK_OVERLAY = {
    "--bg":      "oklch(12% 0.010 260)",
    "--surface": "oklch(17% 0.012 260)",
    "--fg":      "oklch(93% 0.005 0)",
    "--muted":   "oklch(65% 0.010 260)",
    "--border":  "oklch(28% 0.015 260)",
}

# Mapeamento TIER → DIREÇÃO
TIER_DIRECAO = {
    "PREMIUM":  ["warm_editorial", "minimal"],
    "STANDARD": ["cafe", "clean"],
    "BASIC":    ["clean"],
}

# Perfis de animação
ANIMATION_PROFILES = {
    "elegante": {
        "instant":    "50ms",
        "feedback":   "150ms",
        "enter":      "300ms",
        "transition": "500ms",
        "easing_enter":  "cubic-bezier(0.0, 0.0, 0.2, 1)",
        "easing_exit":   "cubic-bezier(0.4, 0.0, 1, 1)",
        "easing_std":    "cubic-bezier(0.4, 0.0, 0.2, 1)",
        "hero_type":  "fade-up",
        "card_type":  "fade-up",
        "stagger":    "80ms",
    },
    "vibrante": {
        "instant":    "50ms",
        "feedback":   "100ms",
        "enter":      "250ms",
        "transition": "400ms",
        "easing_enter":  "cubic-bezier(0.0, 0.0, 0.2, 1)",
        "easing_exit":   "cubic-bezier(0.4, 0.0, 1, 1)",
        "easing_std":    "cubic-bezier(0.4, 0.0, 0.2, 1)",
        "hero_type":  "slide-up",
        "card_type":  "slide-left",
        "stagger":    "60ms",
    },
    "energetico": {
        "instant":    "30ms",
        "feedback":   "80ms",
        "enter":      "200ms",
        "transition": "300ms",
        "easing_enter":  "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "easing_exit":   "cubic-bezier(0.4, 0.0, 1, 1)",
        "easing_std":    "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "hero_type":  "scale-in",
        "card_type":  "scale-in",
        "stagger":    "40ms",
    },
}

# Craft profiles
CRAFT_PROFILES = {
    "editorial": {
        "h1_size": "clamp(3rem, 7vw, 5rem)",
        "h1_weight": "700",
        "h1_tracking": "-0.025em",
        "h2_size": "clamp(1.3rem, 2.5vw, 1.75rem)",
        "h2_weight": "600",
        "body_size": "1.0625rem",
        "body_lh": "1.7",
        "section_py": "clamp(5rem, 10vw, 8rem)",
        "rhythm": "spacious",
    },
    "brutalism": {
        "h1_size": "clamp(2.5rem, 8vw, 6rem)",
        "h1_weight": "900",
        "h2_size": "clamp(1.5rem, 3vw, 2.2rem)",
        "h2_weight": "800",
        "body_size": "1rem",
        "body_lh": "1.5",
        "section_py": "clamp(3rem, 6vw, 5rem)",
        "rhythm": "compressed",
    },
    "minimal": {
        "h1_size": "clamp(2.2rem, 5vw, 3.5rem)",
        "h1_weight": "600",
        "h2_size": "clamp(1.2rem, 2.5vw, 1.6rem)",
        "h2_weight": "500",
        "body_size": "1rem",
        "body_lh": "1.65",
        "section_py": "clamp(4rem, 8vw, 7rem)",
        "rhythm": "spacious",
    },
    "energetic": {
        "h1_size": "clamp(2.5rem, 6vw, 4.5rem)",
        "h1_weight": "800",
        "h2_size": "clamp(1.4rem, 3vw, 2rem)",
        "h2_weight": "700",
        "body_size": "1rem",
        "body_lh": "1.55",
        "section_py": "clamp(3.5rem, 7vw, 5.5rem)",
        "rhythm": "compressed",
    },
    "warm": {
        "h1_size": "clamp(2.2rem, 5vw, 3.8rem)",
        "h1_weight": "700",
        "h2_size": "clamp(1.3rem, 2.5vw, 1.8rem)",
        "h2_weight": "600",
        "body_size": "1.0625rem",
        "body_lh": "1.7",
        "section_py": "clamp(4rem, 8vw, 6.5rem)",
        "rhythm": "medium",
    },
    "luxury": {
        "h1_size": "clamp(2.8rem, 6vw, 4.5rem)",
        "h1_weight": "300",
        "h2_size": "clamp(1.2rem, 2vw, 1.5rem)",
        "h2_weight": "400",
        "body_size": "0.9375rem",
        "body_lh": "1.8",
        "section_py": "clamp(6rem, 12vw, 10rem)",
        "rhythm": "very-spacious",
    },
    "friendly": {
        "h1_size": "clamp(2rem, 5vw, 3.2rem)",
        "h1_weight": "700",
        "h2_size": "clamp(1.3rem, 2.5vw, 1.75rem)",
        "h2_weight": "600",
        "body_size": "1.0625rem",
        "body_lh": "1.65",
        "section_py": "clamp(3.5rem, 7vw, 5.5rem)",
        "rhythm": "medium",
    },
}

# Mapeamento direção visual → craft profile
_DIR_TO_CRAFT = {
    "editorial": "editorial", "paper": "editorial", "storytelling": "editorial",
    "publication": "editorial", "artistic": "editorial", "creative": "editorial",
    "minimal": "minimal", "clean": "minimal", "corporate": "minimal",
    "bold": "energetic", "energetic": "energetic", "nike": "energetic",
    "brutalism": "brutalism", "mono": "brutalism",
    "cafe": "warm", "warm_editorial": "warm", "starbucks": "warm",
    "elegant": "luxury", "luxury": "luxury", "premium": "luxury",
    "friendly": "friendly", "duolingo": "friendly",
    # ... (mapeamento completo em design_context.py)
}

# Aliases de segmentos
ALIASES = {
    "restaurantes": "restaurante", "barbearias": "barbearia",
    "clinicas": "clinica", "pet": "pet_shop", "pets": "pet_shop",
    "advogado": "advocacia", "dentista": "odontologia",
    "pizzarias": "pizzaria", "farmacias": "farmacia",
    "crossfit": "academia", "personal": "academia", "musculacao": "academia",
}


def get_craft_profile(dir_key: str) -> dict:
    """Retorna craft profile (spacing/typography/rhythm) para uma direção visual."""
    craft_key = _DIR_TO_CRAFT.get(dir_key, "warm")
    return dict(CRAFT_PROFILES.get(craft_key, CRAFT_PROFILES["warm"]))