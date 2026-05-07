import os
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
Alex - Modelos Pydantic, constantes e design tokens
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class AlexInput(BaseModel):
    nome: str
    fotos: List[str]  # URLs brutas (logo + fotos misturadas)
    slug: str = ""  # Slug do negocio para salvar assets
    segmento: str


class AlexOutput(BaseModel):
    # Logo processada
    logo_svg: Optional[str] = None
    logo_webp: str
    logo_png: str
    logo_original: str

    # Paleta extraida
    paleta: Dict[str, str]

    # Fotos processadas
    fotos_webp: List[Dict]  # [{"original": "url", "webp": "url", "thumbnail": "url"}]
    fotos_qualidade: Dict[str, List[str]]

    # Design Tokens expandidos
    design_tokens: Dict[str, Any] = {}

    # Classificacao de fotos por tipo (para Designer PRD e Liam)
    fotos_classificadas: Dict[str, Any] = {}

    # Metadados
    total_fotos: int
    economia_mb: float = 0.0
    total_upscaled: int
    total_size_original: float  # MB
    total_size_otimizado: float  # MB
    economia_percentual: float
    assets_dir: str = ""  # Caminho local dos assets


ALEX_INSTRUCTIONS = """
Voce e o Alex, especialista em processamento de imagens.
"""


def gerar_design_tokens(paleta: Dict[str, str], is_dark: bool = False) -> Dict:
    """Gera sistema de design tokens completo a partir da paleta extraida."""
    primary = paleta.get("primaria", "#374151")
    secondary = paleta.get("secundaria", "#f9fafb")
    accent = paleta.get("acento", "#e85d04")

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def lighten(hex_color, factor=0.2):
        r, g, b = hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    def darken(hex_color, factor=0.2):
        r, g, b = hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    if is_dark:
        return {
            "mode": "dark",
            "colors": {
                "primary": primary, "primary_light": lighten(primary, 0.3),
                "primary_dark": darken(primary, 0.3), "secondary": secondary,
                "accent": accent, "accent_light": lighten(accent, 0.3),
                "background": "#0a0a0a", "surface": "#1a1a1a", "surface_2": "#2a2a2a",
                "on_background": "#f0f0f5", "on_surface": "#e5e5ea", "muted": "#6b6b7b",
                "border": "rgba(255,255,255,0.08)", "border_strong": "rgba(255,255,255,0.16)",
                "success": "#22c55e", "warning": "#f59e0b", "error": "#ef4444",
            },
            "gradients": {
                "hero": "linear-gradient(135deg, " + darken(primary, 0.4) + " 0%, #0a0a0a 100%)",
                "accent": "linear-gradient(135deg, " + accent + " 0%, " + lighten(accent, 0.2) + " 100%)",
                "surface": "linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)",
            },
            "shadows": {
                "sm": "0 2px 8px rgba(0,0,0,0.4)", "md": "0 4px 24px rgba(0,0,0,0.5)",
                "lg": "0 8px 48px rgba(0,0,0,0.6)", "glow": "0 0 32px " + accent + "40",
            }
        }
    else:
        def luminance(hex_c):
            r, g, b = [x/255.0 for x in hex_to_rgb(hex_c)]
            r, g, b = [x/12.92 if x <= 0.03928 else ((x+0.055)/1.055)**2.4 for x in [r, g, b]]
            return 0.2126*r + 0.7152*g + 0.0722*b

        def contrast_ratio(c1, c2):
            l1, l2 = luminance(c1), luminance(c2)
            return (max(l1, l2)+0.05)/(min(l1, l2)+0.05)

        text_on_primary = "#ffffff" if contrast_ratio(primary, "#ffffff") >= 4.5 else "#111827"
        text_on_accent  = "#ffffff" if contrast_ratio(accent,  "#ffffff") >= 4.5 else "#111827"
        bg_classes = {
            "hero":        "section-bg-dark",
            "sobre":       "section-bg-subtle",
            "servicos":    "section-bg-mesh",
            "depoimentos": "section-bg-dark",
            "localizacao": "section-bg-subtle",
            "contato":     "section-bg-brand",
            "footer":      "section-bg-dark",
        }
        return {
            "mode": "light",
            "colors": {
                "primary": primary, "primary_light": lighten(primary, 0.4),
                "primary_dark": darken(primary, 0.2), "secondary": secondary,
                "accent": accent, "accent_light": lighten(accent, 0.4),
                "background": "#ffffff", "surface": "#f9fafb", "surface_2": "#f3f4f6",
                "on_background": "#111827", "on_surface": "#374151", "muted": "#9ca3af",
                "border": "rgba(0,0,0,0.06)", "border_strong": "rgba(0,0,0,0.12)",
                "success": "#16a34a", "warning": "#d97706", "error": "#dc2626",
                "text_on_primary": text_on_primary, "text_on_accent": text_on_accent,
            },
            "gradients": {
                "hero": "linear-gradient(135deg, " + darken(primary, 0.5) + " 0%, #0a0a0a 100%)",
                "accent": "linear-gradient(135deg, " + primary + " 0%, " + accent + " 100%)",
                "surface": "linear-gradient(180deg, #f9fafb 0%, #ffffff 100%)",
                "mesh": "radial-gradient(at 40% 20%, " + lighten(primary, 0.6) + "22 0px, transparent 50%), radial-gradient(at 80% 0%, " + lighten(accent, 0.5) + "18 0px, transparent 50%)",
            },
            "shadows": {
                "sm": "0 1px 4px rgba(0,0,0,0.06)", "md": "0 4px 16px rgba(0,0,0,0.08)",
                "lg": "0 8px 32px rgba(0,0,0,0.12)", "glow": "0 0 24px " + accent + "30",
            },
            "bg_classes": bg_classes,
            "wcag": {
                "text_on_primary_ratio": round(contrast_ratio(primary, text_on_primary), 2),
                "text_on_accent_ratio":  round(contrast_ratio(accent,  text_on_accent),  2),
            }
        }
