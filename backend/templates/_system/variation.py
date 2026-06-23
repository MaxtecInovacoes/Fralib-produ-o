"""variation.py — Sistema de Variacao 4-Eixos (FraLib OpenUI).

Este modulo gera, deterministicamente, uma combinacao coerente de 4 eixos
visuais para cada lead:

    EIXO 1: ESTETICA   (6 opcoes)  - bold_energy, editorial, minimal,
                                     kinetic, scroll, immersive_3d
    EIXO 2: TEMA       (10 opcoes) - bold-dark, bold-red, kinetic-acid,
                                     trust-navy, trust-elite, zen-pure,
                                     zen-warm, editorial-cream,
                                     glassmorphism, brutalist-mono
    EIXO 3: TIPOGRAFIA (5 familias) - Inter, Playfair Display,
                                     JetBrains Mono, Space Grotesk,
                                     IBM Plex Sans
    EIXO 4: LAYOUT     (3 tipos)   - centered, magazine, bento
    EIXO 5: MOTION     (3 levels)  - subtle, medium, cinematic

DETERMINISMO:
    A mesma entrada (lead_id, segmento) produz SEMPRE a mesma saida.
    Seed = int(hashlib.md5(f"{lead_id}:{segmento}").hexdigest(), 16)
    Nao usamos random global — cada funcao cria seu proprio random.Random(seed).

COERENCIA:
    Nao basta sortear valores independentes. Existem regras que impedem
    combinacoes absurdas (ex: BOLD_ENERGY + zen-pure quebraria a estetica).
    A matriz COHERENCE abaixo define o produto cartesiano valido.

USO NO BUILDER:
    from backend.templates._system.variation import generate_variation
    v = generate_variation(lead_id=123, segmento="clinica_estetica")
    html_template = load(v["template_path"])
    rendered = html_template.replace("{{CSS_VARS}}", v["css_vars_inline"])
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Dict, List


# ============================================================================
# CATALOGO COMPLETO
# ============================================================================

ESTETICAS: List[str] = [
    "BOLD_ENERGY",
    "EDITORIAL",
    "MINIMAL",
    "KINETIC",
    "SCROLL",
    "IMMERSIVE_3D",
]

THEMES: List[str] = [
    "bold-dark",
    "bold-red",
    "kinetic-acid",
    "trust-navy",
    "trust-elite",
    "zen-pure",
    "zen-warm",
    "editorial-cream",
    "glassmorphism",
    "brutalist-mono",
]

TYPOGRAPHIES: List[str] = [
    "Inter",
    "Playfair Display",
    "JetBrains Mono",
    "Space Grotesk",
    "IBM Plex Sans",
]

LAYOUTS: List[str] = [
    "centered",
    "magazine",
    "bento",
]

MOTIONS: List[str] = [
    "subtle",
    "medium",
    "cinematic",
]


# ============================================================================
# MATRIZ DE COERENCIA
# ----------------------------------------------------------------------------
# Chaves: estetica -> (themes_validos, motions_validas)
# Tipografia e layout sao livres (qualquer combinacao eh esteticamente viavel).
# ============================================================================

COHERENCE: Dict[str, Dict[str, List[str]]] = {
    "BOLD_ENERGY": {
        "themes": ["bold-dark", "bold-red", "kinetic-acid", "brutalist-mono"],
        "motions": ["cinematic"],
        "preferred_typography": ["Space Grotesk", "Inter", "JetBrains Mono"],
        "preferred_layout": ["centered", "bento"],
    },
    "EDITORIAL": {
        "themes": ["editorial-cream", "zen-warm", "trust-navy"],
        "motions": ["medium"],
        "preferred_typography": ["Playfair Display", "IBM Plex Sans"],
        "preferred_layout": ["magazine", "centered"],
    },
    "MINIMAL": {
        "themes": ["zen-pure", "zen-warm"],
        "motions": ["subtle"],
        "preferred_typography": ["Inter", "IBM Plex Sans"],
        "preferred_layout": ["centered", "magazine"],
    },
    "KINETIC": {
        "themes": ["kinetic-acid", "bold-dark", "glassmorphism", "brutalist-mono"],
        "motions": ["medium", "cinematic"],
        "preferred_typography": ["Space Grotesk", "JetBrains Mono"],
        "preferred_layout": ["bento", "magazine"],
    },
    "SCROLL": {
        "themes": ["editorial-cream", "zen-warm", "trust-navy", "trust-elite"],
        "motions": ["medium", "cinematic"],
        "preferred_typography": ["Playfair Display", "IBM Plex Sans", "Inter"],
        "preferred_layout": ["magazine", "centered"],
    },
    "IMMERSIVE_3D": {
        "themes": ["bold-dark", "kinetic-acid", "glassmorphism", "trust-elite"],
        "motions": ["cinematic"],
        "preferred_typography": ["Space Grotesk", "Inter"],
        "preferred_layout": ["bento", "magazine"],
    },
}


# ============================================================================
# PATH RESOLUTION
# ============================================================================

_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent  # backend/templates/


def _template_path_for(estetica: str) -> str:
    """Resolve o path do template HTML canonico da estetica.

    Mapeamento:
        BOLD_ENERGY  -> templates/bold_energy/index.html
        EDITORIAL    -> templates/editorial/index.html
        MINIMAL      -> templates/minimal/index.html
        KINETIC      -> templates/kinetic/index.html
        SCROLL       -> templates/scroll/index.html
        IMMERSIVE_3D -> templates/immersive_3d/index.html
    """
    folder = estetica.lower().replace("_3d", "_3d")
    return str(_TEMPLATES_ROOT / folder / "index.html")


# ============================================================================
# SEED DETERMINISTICO
# ============================================================================

def _seed(lead_id: int, segmento: str) -> int:
    """Seed deterministico: hash MD5 de 'lead_id:segmento' convertido para int.

    MD5 hex tem 32 chars hex. Convertendo para int gera um numero de ate
    128 bits, mais que suficiente para random.Random.
    """
    raw = f"{lead_id}:{segmento}"
    return int(hashlib.md5(raw.encode("utf-8")).hexdigest(), 16)


def _rng(lead_id: int, segmento: str, salt: str = "") -> random.Random:
    """random.Random isolado por chamada (sem contaminacao do global).

    O salt permite sortear valores DIFERENTES dentro de uma mesma chamada
    (ex: theme vs motion precisam de escolhas independentes).
    """
    base = _seed(lead_id, segmento)
    if salt:
        salted = f"{base}:{salt}"
        seed = int(hashlib.md5(salted.encode("utf-8")).hexdigest(), 16)
    else:
        seed = base
    return random.Random(seed)


# ============================================================================
# 6 FUNCOES PUBLICAS
# ============================================================================

def select_estetica(lead_id: int, segmento: str) -> str:
    """EIXO 1: seleciona a estetica macro do site.

    Distribuicao intencionalmente NAO-uniforme: nichos premium puxam EDITORIAL,
    segmentos high-energy puxam BOLD/KINETIC. Mas como nao temos mapeamento
    aqui (ficaria no SDR ou Nicho agent), usamos uniforme + seed.

    Args:
        lead_id: ID do lead (int)
        segmento: slug do segmento (ex: 'clinica_estetica')

    Returns:
        Nome da estetica (uma de ESTETICAS).
    """
    rng = _rng(lead_id, segmento, salt="estetica")
    return rng.choice(ESTETICAS)


def select_theme(lead_id: int, estetica: str) -> str:
    """EIXO 2: seleciona tema coerente com a estetica.

    Args:
        lead_id: ID do lead (int)
        estetica: ja escolhida por select_estetica

    Returns:
        Nome do tema (um da lista COHERENCE[estetica]['themes']).
    """
    valid_themes = COHERENCE[estetica]["themes"]
    rng = _rng(lead_id, estetica, salt="theme")
    return rng.choice(valid_themes)


def select_typography(lead_id: int, estetica: str) -> str:
    """EIXO 3: seleciona a familia tipografica principal.

    Usa 'preferred_typography' da matriz de coerencia, com fallback
    para qualquer uma das 5 familias se a preferencia estiver vazia.

    Returns:
        Nome da familia (uma de TYPOGRAPHIES).
    """
    preferred = COHERENCE[estetica].get("preferred_typography", [])
    pool = preferred if preferred else TYPOGRAPHIES
    rng = _rng(lead_id, estetica, salt="typography")
    return rng.choice(pool)


def select_layout(lead_id: int) -> str:
    """EIXO 4: seleciona o layout (ortogonal a estetica).

    Layouts sao globais — qualquer estetica aceita qualquer layout
    (a combinacao eh resolvida pelo template via CSS Grid).
    """
    rng = _rng(lead_id, "global", salt="layout")
    return rng.choice(LAYOUTS)


def select_motion(lead_id: int, estetica: str) -> str:
    """EIXO 5: seleciona o nivel de motion coerente com a estetica.

    Args:
        lead_id: ID do lead (int)
        estetica: ja escolhida por select_estetica

    Returns:
        Nome do level (um de COHERENCE[estetica]['motions']).
    """
    valid_motions = COHERENCE[estetica]["motions"]
    rng = _rng(lead_id, estetica, salt="motion")
    return rng.choice(valid_motions)


def generate_variation(lead_id: int, segmento: str) -> Dict[str, str]:
    """Orquestrador: chama os 5 selectores e monta o pacote completo.

    Returns:
        dict com chaves:
            - estetica:       str (ESTETICAS)
            - theme:          str (THEMES, coerente com estetica)
            - typography:     str (TYPOGRAPHIES, coerente com estetica)
            - layout:         str (LAYOUTS)
            - motion:         str (MOTIONS, coerente com estetica)
            - template_path:  str (path absoluto do HTML template)
            - css_vars_inline: str (bloco <style> com --motion-* e --layout-* inline)
    """
    estetica = select_estetica(lead_id, segmento)
    theme = select_theme(lead_id, estetica)
    typography = select_typography(lead_id, estetica)
    layout = select_layout(lead_id)
    motion = select_motion(lead_id, estetica)
    template_path = _template_path_for(estetica)
    css_vars_inline = _build_css_vars_inline(theme, typography, layout, motion)

    return {
        "estetica": estetica,
        "theme": theme,
        "typography": typography,
        "layout": layout,
        "motion": motion,
        "template_path": template_path,
        "css_vars_inline": css_vars_inline,
    }


# ============================================================================
# CSS VARS INLINE BUILDER
# ----------------------------------------------------------------------------
# Como o variation.py pode ser consumido tanto por templates estaticos
# (sem SSR) quanto pelo OpenUI builder, geramos um bloco <style> ja
# pronto para ser injetado no <head> do HTML.
# ============================================================================

_MOTION_VALUES = {
    "subtle":    ("0.3s",                     "ease-out"),
    "medium":    ("0.6s",                     "cubic-bezier(0.4, 0, 0.2, 1)"),
    "cinematic": ("1.2s",                     "cubic-bezier(0.16, 1, 0.3, 1)"),
}

_LAYOUT_VALUES = {
    "centered": ("1200px",  "24px"),
    "magazine": ("1440px",  "32px"),
    "bento":    ("1320px",  "20px"),
}


def _build_css_vars_inline(
    theme: str,
    typography: str,
    layout: str,
    motion: str,
) -> str:
    """Monta o bloco CSS com overrides para os 4 eixos do lead.

    O bloco assume que tokens.css + themes.css ja foram carregados.
    Aqui sobrescrevemos apenas o que VARIAR por lead.
    """
    motion_dur, motion_ease = _MOTION_VALUES[motion]
    container_max, gutter = _LAYOUT_VALUES[layout]

    # Tipografia: a variavel --font-display eh setada por temas serif-only
    # (editorial-cream, trust-navy, trust-elite, zen-warm). Para os demais,
    # sobrescrevemos explicitamente aqui.
    css = (
        f"<style id=\"fralib-variation-inline\">\n"
        f"  :root {{\n"
        f"    --fralib-theme: {theme};\n"
        f"    --fralib-typography: '{typography}';\n"
        f"    --fralib-layout: {layout};\n"
        f"    --fralib-motion: {motion};\n"
        f"    --motion-duration: {motion_dur};\n"
        f"    --motion-easing: {motion_ease};\n"
        f"    --layout-container-max: {container_max};\n"
        f"    --layout-gutter: {gutter};\n"
        f"  }}\n"
        f"</style>"
    )
    return css


# ============================================================================
# CONTAGEM DE COMBINACOES VALIDAS (para docs/testes)
# ============================================================================

def count_valid_combinations() -> int:
    """Calcula o numero total de combinacoes validas no produto cartesiano.

    Combina validas = soma sobre esteticas de:
        len(themes_validos) * len(typographies_preferidas) * len(layouts) * len(motions_validas)

    Onde typographies_preferidas = preferred_typography ou todas as 5 se vazio.
    """
    total = 0
    for estetica, rules in COHERENCE.items():
        n_themes = len(rules["themes"])
        n_typo = len(rules.get("preferred_typography", []) or TYPOGRAPHIES)
        n_layouts = len(LAYOUTS)
        n_motions = len(rules["motions"])
        total += n_themes * n_typo * n_layouts * n_motions
    return total