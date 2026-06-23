"""_system — Sistema de Variacao 4-Eixos do FraLib.

Este pacote prove a logica de variacao visual deterministica usada pelo
OpenUI builder para gerar sites com 4 eixos combinatorios:

    1. ESTETICA   (6 opcoes)
    2. TEMA       (10 opcoes)
    3. TIPOGRAFIA (5 familias)
    4. LAYOUT     (3 tipos)
    5. MOTION     (3 levels)

API PUBLICA (6 funcoes):
    - select_estetica(lead_id, segmento)         -> str
    - select_theme(lead_id, estetica)            -> str
    - select_typography(lead_id, estetica)       -> str
    - select_layout(lead_id)                     -> str
    - select_motion(lead_id, estetica)           -> str
    - generate_variation(lead_id, segmento)      -> dict

CATALOGO:
    - ESTETICAS, THEMES, TYPOGRAPHIES, LAYOUTS, MOTIONS
    - COHERENCE: matriz estetica -> (themes_validos, motions_validas)
    - count_valid_combinations() -> int

USO:
    from backend.templates._system import generate_variation
    v = generate_variation(lead_id=42, segmento="clinica_estetica")
    print(v["theme"], v["motion"], v["template_path"])
"""

from .variation import (
    select_estetica,
    select_theme,
    select_typography,
    select_layout,
    select_motion,
    generate_variation,
)

__all__ = [
    "select_estetica",
    "select_theme",
    "select_typography",
    "select_layout",
    "select_motion",
    "generate_variation",
]