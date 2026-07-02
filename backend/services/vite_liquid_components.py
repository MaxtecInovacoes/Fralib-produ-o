"""
============================================================================
FRA LIB - VITE LIQUID COMPONENTS
============================================================================
Registry de componentes líquidos - 4 Polos Estéticos + Inferência automática

Este módulo fornece:
1. POLO_TOKENS - DNA estrutural de cada polo
2. HERO_DISPLAY_MODES - Modos de display do Hero por polo
3. COMPONENT_VARIANTS - Variantes de componentes por polo
4. infer_aesthetic_pole() - Função de inferência automática do polo
5. get_liquid_component_guide() - Prompt para LLM

Uso:
    from vite_liquid_components import infer_aesthetic_pole, POLO_TOKENS

    pole_info = infer_aesthetic_pole("academia", "musculacao")
    # Returns: {"pole": "bold", "heat": 0.9, "tokens": {...}, "temperature": 0.8}

============================================================================
"""

from __future__ import annotations

from typing import Any, TypedDict

# ═══════════════════════════════════════════════════════════════════════════
# TIPOS
# ═══════════════════════════════════════════════════════════════════════════


class PoleInfo(TypedDict):
    """Informações do polo inferido."""
    pole: str
    heat: float
    tokens: dict[str, Any]
    temperature: float
    display_mode: str


# ═══════════════════════════════════════════════════════════════════════════
# POLO TOKENS - DNA Estrutural de cada polo
# ═══════════════════════════════════════════════════════════════════════════

POLO_TOKENS: dict[str, dict[str, Any]] = {
    "soft": {
        # Geometria
        "radius": "40px",
        "section_overlap": "0px",
        "overlap": "0px",
        "text_skew": "0deg",
        # Tipografia
        "heading_font": "'Playfair Display', Georgia, serif",
        "heading_case": "capitalize",
        "heading_style": "normal",
        "heading_letter_spacing": "0.03em",
        "heading_scale": "clamp(1.75rem, 4vw, 3rem)",
        "hero_scale": "clamp(2.5rem, 7vw, 5rem)",
        # Espaçamento
        "section_gap": "6rem",
        "section_padding_y": "6rem",
        "card_padding": "2rem",
        "grid_gap": "3rem",
        # Shadows
        "shadow_card": "0 8px 32px rgba(139, 92, 246, 0.12)",
        "shadow_button": "0 4px 16px rgba(139, 92, 246, 0.25)",
        "shadow_glow": "0 8px 32px rgba(139, 92, 246, 0.2)",
        # Motion
        "motion_intensity": 0.3,
        "motion_speed": "600ms",
        "motion_ease": "cubic-bezier(0.4, 0, 0.2, 1)",
        # Text Effects
        "text_stroke": False,
        "text_stroke_width": "0px",
        # Cores
        "primary": "#8b5cf6",
        "primary_hover": "#7c3aed",
        "accent": "#f472b6",
    },
    "bold": {
        # Geometria
        "radius": "0px",
        "section_overlap": "-80px",
        "overlap": "-80px",
        "text_skew": "-5deg",
        # Tipografia
        "heading_font": "'Anton', Impact, sans-serif",
        "heading_case": "uppercase",
        "heading_style": "italic",
        "heading_letter_spacing": "-0.02em",
        "heading_scale": "clamp(2.5rem, 8vw, 5rem)",
        "hero_scale": "clamp(4rem, 15vw, 12vw)",
        # Espaçamento
        "section_gap": "0rem",
        "section_padding_y": "2rem",
        "card_padding": "1.5rem",
        "grid_gap": "0rem",
        # Shadows
        "shadow_card": "8px 8px 0px var(--fralib-primary)",
        "shadow_button": "4px 4px 0px var(--fralib-accent)",
        "shadow_glow": "0 0 40px rgba(239, 68, 68, 0.4)",
        # Motion
        "motion_intensity": 1.0,
        "motion_speed": "150ms",
        "motion_ease": "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
        # Text Effects
        "text_stroke": True,
        "text_stroke_width": "2px",
        "text_stroke_color": "var(--fralib-primary)",
        # Cores
        "primary": "#ef4444",
        "primary_hover": "#dc2626",
        "accent": "#fbbf24",
        "bg_dark": "#0f0f0f",
    },
    "corporate": {
        # Geometria
        "radius": "6px",
        "section_overlap": "0px",
        "overlap": "0px",
        "text_skew": "0deg",
        # Tipografia
        "heading_font": "'Inter', system-ui, sans-serif",
        "heading_case": "capitalize",
        "heading_style": "normal",
        "heading_letter_spacing": "-0.01em",
        "heading_scale": "clamp(1.75rem, 4vw, 3rem)",
        "hero_scale": "clamp(2.5rem, 6vw, 4.5rem)",
        # Espaçamento
        "section_gap": "4rem",
        "section_padding_y": "4rem",
        "card_padding": "1.5rem",
        "grid_gap": "2rem",
        # Shadows
        "shadow_card": "0 1px 3px rgba(0, 0, 0, 0.1)",
        "shadow_button": "none",
        "shadow_glow": "0 0 20px rgba(59, 130, 246, 0.15)",
        # Motion
        "motion_intensity": 0.4,
        "motion_speed": "300ms",
        "motion_ease": "ease",
        # Text Effects
        "text_stroke": False,
        "text_stroke_width": "0px",
        # Cores
        "primary": "#1e40af",
        "primary_hover": "#1e3a8a",
        "accent": "#3b82f6",
    },
    "minimal": {
        # Geometria
        "radius": "12px",
        "section_overlap": "-40px",
        "overlap": "-40px",
        "text_skew": "2deg",
        # Tipografia
        "heading_font": "'Space Grotesk', system-ui, sans-serif",
        "heading_case": "lowercase",
        "heading_style": "normal",
        "heading_letter_spacing": "-0.02em",
        "heading_scale": "clamp(1.75rem, 4vw, 3rem)",
        "hero_scale": "clamp(3rem, 8vw, 6rem)",
        # Espaçamento
        "section_gap": "5rem",
        "section_padding_y": "5rem",
        "card_padding": "2rem",
        "grid_gap": "1.5rem",
        # Shadows
        "shadow_card": "0 0 40px rgba(59, 130, 246, 0.15)",
        "shadow_button": "0 0 20px rgba(59, 130, 246, 0.4)",
        "shadow_glow": "0 0 60px rgba(59, 130, 246, 0.3)",
        # Motion
        "motion_intensity": 0.6,
        "motion_speed": "400ms",
        "motion_ease": "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        # Text Effects
        "text_stroke": False,
        "text_stroke_width": "0px",
        # Glass
        "glass_bg": "rgba(255, 255, 255, 0.05)",
        "glass_blur": "12px",
        # Cores
        "primary": "#3b82f6",
        "primary_hover": "#2563eb",
        "accent": "#06b6d4",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# HERO DISPLAY MODES - Por polo
# ═══════════════════════════════════════════════════════════════════════════

HERO_DISPLAY_MODES: dict[str, dict[str, dict[str, Any]]] = {
    "soft": {
        "centered": {
            "name": "Centered Calm",
            "description": "Layout centralizado com respiro e elegância",
            "layout": "flex flex-col items-center justify-center text-center min-h-[70vh]",
            "headline_class": "text-center max-w-3xl",
            "image_style": "rounded-[40px] shadow-2xl max-w-lg",
            "cta_style": "rounded-full px-8 py-4",
            "badge_style": "rounded-full px-4 py-2 bg-[--primary]/10 text-[--primary]",
        },
        "card_overlay": {
            "name": "Card Overlay",
            "description": "Card sobreposto à imagem com blur",
            "layout": "relative grid md:grid-cols-2 gap-8 items-center",
            "headline_class": "text-left",
            "image_style": "rounded-[40px] shadow-2xl",
            "overlay_style": "absolute bottom-8 left-8 right-8 bg-white/80 backdrop-blur-md rounded-[40px] p-8",
            "cta_style": "rounded-full",
        },
        "split_soft": {
            "name": "Split Soft",
            "description": "50/50 texto e imagem com cards arredondados",
            "layout": "grid md:grid-cols-2 gap-12 items-center",
            "headline_class": "text-left",
            "image_style": "rounded-[40px]",
            "cta_style": "rounded-full",
        },
    },
    "bold": {
        "impact": {
            "name": "IMPACT",
            "description": "Título cortando imagem, text-stroke, skew - HIGH FITNESS",
            "layout": "relative overflow-hidden min-h-screen",
            "headline_class": "uppercase italic skew-x-[-5deg] text-[clamp(4rem,15vw,12vw)] leading-none",
            "text_stroke": True,
            "image_style": "absolute inset-0 w-full h-full object-cover opacity-30",
            "cta_style": "rounded-none px-8 py-4 uppercase tracking-wider shadow-[4px_4px_0px_var(--fralib-accent)] hover:translate-x-1 hover:translate-y-1 hover:shadow-none",
            "badge_style": "rounded-none px-4 py-2 bg-[--primary] text-white uppercase tracking-widest",
            "overlap_next": "-80px",
        },
        "split_tension": {
            "name": "Split Tension",
            "description": "Texto e imagem com tensão visual",
            "layout": "relative grid grid-cols-1 lg:grid-cols-12 gap-0 min-h-screen",
            "headline_class": "col-span-7 uppercase italic text-[clamp(3rem,8vw,8rem)] leading-none",
            "image_style": "col-span-5 -ml-8 rounded-none shadow-none",
            "cta_style": "rounded-none uppercase",
            "text_skew": "-3deg",
        },
        "full_bleed": {
            "name": "Full Bleed",
            "description": "Imagem fullscreen com texto sobreposto",
            "layout": "relative min-h-screen flex items-end pb-24",
            "headline_class": "text-white uppercase italic text-[clamp(3rem,10vw,10rem)] leading-none px-8",
            "image_style": "absolute inset-0 w-full h-full object-cover",
            "overlay_style": "absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent",
            "cta_style": "rounded-none",
        },
    },
    "corporate": {
        "split": {
            "name": "Split Professional",
            "description": "Layout 50/50 limpo e profissional",
            "layout": "grid md:grid-cols-2 gap-8 items-center py-16",
            "headline_class": "text-4xl font-semibold",
            "image_style": "rounded-lg",
            "cta_style": "rounded-md px-6 py-3",
            "badge_style": "rounded px-3 py-1 bg-[--primary]/10 text-[--primary] text-sm",
        },
        "centered_credibility": {
            "name": "Centered Credibility",
            "description": "Centro com stats band",
            "layout": "flex flex-col items-center text-center",
            "headline_class": "text-5xl font-semibold",
            "cta_style": "rounded-md px-6 py-3",
            "stats_band": True,
        },
        "sidebar": {
            "name": "Sidebar Info",
            "description": "Info lateral com card de destaque",
            "layout": "grid md:grid-cols-3 gap-8 items-start",
            "headline_class": "col-span-2 text-4xl",
            "sidebar_style": "sticky top-8",
            "cta_style": "rounded-md",
        },
    },
    "minimal": {
        "bento": {
            "name": "Bento Grid",
            "description": "Grid assimétrico estilo Bento Box",
            "layout": "grid grid-cols-12 gap-4 auto-rows-[minmax(100px,auto)]",
            "headline_class": "col-span-8 text-6xl lowercase font-medium",
            "image_style": "col-span-4 rounded-xl",
            "card_style": "glass-card",
        },
        "glass_overlay": {
            "name": "Glass Overlay",
            "description": "Card com efeito glass sobre imagem",
            "layout": "relative min-h-[80vh] flex items-center",
            "headline_class": "text-7xl lowercase font-medium",
            "card_style": "glass-card max-w-2xl p-12",
            "image_style": "absolute inset-0 w-full h-full object-cover -z-10",
        },
        "asymmetric": {
            "name": "Asymmetric Tech",
            "description": "Layout assimétrico com elementos geométricos",
            "layout": "grid grid-cols-12 gap-8 items-center py-20",
            "headline_class": "col-span-7 text-6xl lowercase skew-x-[2deg]",
            "image_style": "col-span-5 rounded-xl shadow-2xl",
            "cta_style": "rounded-xl",
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# COMPONENT VARIANTS - Props líquidas por componente
# ═══════════════════════════════════════════════════════════════════════════

COMPONENT_VARIANTS: dict[str, dict[str, str]] = {
    "Button": {
        "soft": "rounded-full px-8 py-4 shadow-lg hover:shadow-xl transition-all duration-300 font-medium",
        "bold": "rounded-none px-6 py-3 uppercase tracking-wider shadow-[4px_4px_0px_var(--fralib-accent)] hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all duration-150 font-bold",
        "corporate": "rounded-md px-6 py-3 hover:bg-[--fralib-primary-hover] transition-colors duration-200 font-medium",
        "minimal": "rounded-xl px-6 py-3 shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)] transition-shadow duration-300 font-medium",
    },
    "Card": {
        "soft": "rounded-[40px] p-8 shadow-[0_8px_32px_rgba(139,92,246,0.12)] hover:shadow-[0_8px_32px_rgba(139,92,246,0.2)] transition-shadow duration-300",
        "bold": "rounded-none border-2 border-[--fralib-primary] shadow-[8px_8px_0px_var(--fralib-primary)] hover:shadow-[4px_4px_0px_var(--fralib-primary)] transition-all duration-150",
        "corporate": "rounded-md p-6 shadow-[0_1px_3px_rgba(0,0,0,0.1)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.15)] transition-shadow duration-200",
        "minimal": "rounded-xl p-6 border border-white/10 glass-card",
    },
    "Badge": {
        "soft": "rounded-full px-4 py-1.5 bg-[--fralib-primary]/10 text-[--fralib-primary] text-sm font-medium",
        "bold": "rounded-none px-3 py-1 bg-[--fralib-primary] text-white uppercase tracking-widest text-xs font-bold",
        "corporate": "rounded px-3 py-1 bg-[--fralib-primary]/10 text-[--fralib-primary] text-sm",
        "minimal": "rounded-xl px-4 py-1.5 glass-card text-sm font-medium",
    },
    "Input": {
        "soft": "rounded-[20px] px-6 py-4 border-0 shadow-[0_4px_16px_rgba(139,92,246,0.15)] focus:ring-2 focus:ring-[--fralib-primary]/30 transition-all duration-300",
        "bold": "rounded-none px-4 py-3 border-2 border-[--fralib-primary] focus:border-[--fralib-accent] transition-colors duration-150 font-bold uppercase",
        "corporate": "rounded-md px-4 py-3 border border-gray-300 focus:border-[--fralib-primary] focus:ring-1 focus:ring-[--fralib-primary]/30 transition-colors",
        "minimal": "rounded-xl px-4 py-3 border border-white/20 bg-white/5 focus:border-[--fralib-primary] focus:ring-2 focus:ring-[--fralib-primary]/30 backdrop-blur transition-all",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# TRIGGERS DE INFERÊNCIA - Palavras-chave por polo
# ═══════════════════════════════════════════════════════════════════════════

POLE_TRIGGERS: dict[str, dict[str, Any]] = {
    "soft": {
        "keywords": [
            "nutri", "estetica", "estética", "spa", "yoga", "psicologo",
            "psicólogo", "fisio", "fisioterapia", "moda", "pet", "petshop",
            "beleza", "infantil", "crianca", "criança", "salao", "salão",
            "barbearia", "barber", "cabelo", "estetica_capilar",
            "terapia", "massagem", "acupuntura", "meditacao", "bem-estar",
            "slow", "zen", "natural", "organic", "vegan", " cruelty-free",
        ],
        "heat": 0.2,
        "temperature": 0.7,
        "default_display_mode": "centered",
    },
    "bold": {
        "keywords": [
            "academia", "crossfit", "gym", "musculacao", "musculação",
            "suplemento", "evento", "festival", "marketing", "digital",
            "agencia", "agência", "app", "game", "gaming",
            "fitness", "workout", "fit", "dance", "musica", "música",
            "festa", "balada", "show", "power",
            "cross", "athlete", "atleta", "pro", "champion", "elite",
        ],
        "heat": 0.9,
        "temperature": 0.8,
        "default_display_mode": "impact",
    },
    "corporate": {
        "keywords": [
            "advogado", "advocacia", "contador", "contabilidade", "engenh",
            "engenharia", "logist", "logística", "imoveis", "imóveis",
            "consultoria", "clinica", "clínica", "médico", "dentista",
            "farmacia", "farmácia", "hospital", "laboratorio", "laboratório",
            "escritorio", "escritório", "buro", "departamento", "agência",
            "oficina", "mecanica", "mecânica", "concessionaria", "seguros",
            "financeira", "banco", "investimento", "corretora", "advocacia",
        ],
        "heat": 0.3,
        "temperature": 0.4,
        "default_display_mode": "split",
    },
    "minimal": {
        "keywords": [
            "saas", "software", "solar", "energia", "arquitetura", "design",
            "fotografia", "agencia", "digital", "seo", "dev", "developer",
            "data", "ai", "machine", "learning", "cloud", "hosting",
            "tech", "iot", "smart", "innovation", "inova", "disrupt",
            "app", "mobile", "web", "ux", "ui", "product", "platform",
            "fintech", "edtech", "healthtech", "proptech", "regtech",
        ],
        "heat": 0.5,
        "temperature": 0.6,
        "default_display_mode": "bento",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE INFERÊNCIA
# ═══════════════════════════════════════════════════════════════════════════


def infer_aesthetic_pole(
    segment: str = "",
    subniche: str = "",
    tags: list[str] | None = None,
    description: str = "",
) -> PoleInfo:
    """
    Infere o polo estético baseado no segmento, subnicho e contexto.

    Args:
        segment: Segmento principal do negócio (ex: "academia")
        subniche: Subnicho ou especialidade (ex: "musculacao")
        tags: Tags adicionais do lead (ex: ["crossfit", "funcional"])
        description: Descrição do negócio

    Returns:
        PoleInfo com polo, heat, tokens, temperature e display_mode

    Example:
        >>> pole = infer_aesthetic_pole("academia", "musculacao")
        >>> print(pole["pole"])
        "bold"
    """
    # Combinar texto para análise
    text = " ".join([
        segment or "",
        subniche or "",
        description or "",
        " ".join(tags or []),
    ]).lower()

    # Scores por polo
    scores: dict[str, int] = {"soft": 0, "bold": 0, "corporate": 0, "minimal": 0}

    # Calcular scores baseado em triggers
    for pole, config in POLE_TRIGGERS.items():
        for keyword in config["keywords"]:
            if keyword in text:
                scores[pole] += 1

    # Determinar polo com maior score
    if not any(scores.values()):
        # Default para corporate se nenhuma trigger
        pole = "corporate"
    else:
        pole = max(scores, key=scores.get)  # type: ignore

    # Obter config do polo
    config = POLE_TRIGGERS[pole]
    tokens = POLO_TOKENS[pole]

    return {
        "pole": pole,
        "heat": config["heat"],
        "tokens": tokens,
        "temperature": config["temperature"],
        "display_mode": config["default_display_mode"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# SERVICES DISPLAY MODES - Modos de display da secao de Servicos por polo
# ═══════════════════════════════════════════════════════════════════════════

SERVICES_DISPLAY_MODES: dict[str, dict[str, dict[str, Any]]] = {
    "soft": {
        "stacked_cards": {
            "name": "Stacked Editorial Cards",
            "description": "Cards arredondados em coluna unica, foco em respiro e tipografia",
            "container": "flex flex-col gap-12 max-w-3xl mx-auto",
            "card_class": "rounded-[40px] p-10 bg-[--surface] shadow-[0_8px_32px_rgba(139,92,246,0.10)]",
            "icon_class": "w-16 h-16 rounded-full bg-[--primary]/10 text-[--primary] flex items-center justify-center",
            "title_class": "text-2xl font-serif mt-6",
            "body_class": "text-base text-[--muted] mt-3 leading-relaxed",
            "image_treatment": "warm",
            "density": "editorial",
        },
        "alternating_split": {
            "name": "Alternating Split",
            "description": "Imagem alterna com texto, esquerda/direita, ritmo calmo",
            "container": "flex flex-col gap-20",
            "row_class": "grid md:grid-cols-2 gap-12 items-center",
            "row_reverse": True,
            "card_class": "rounded-[40px]",
            "image_treatment": "warm",
            "density": "editorial",
        },
    },
    "bold": {
        "mosaic": {
            "name": "Mosaic Aggressive",
            "description": "Grid quebrado, mosaico de tamanhos diferentes, sobreposicoes",
            "container": "grid grid-cols-12 gap-2 auto-rows-[180px]",
            "card_class": "rounded-none border-2 border-[--primary] shadow-[6px_6px_0px_var(--primary)] bg-[--surface]",
            "card_sizes": ["col-span-7 row-span-2", "col-span-5", "col-span-4", "col-span-8", "col-span-6"],
            "title_class": "uppercase italic text-3xl tracking-tight",
            "body_class": "text-sm uppercase tracking-wider",
            "image_treatment": "grayscale",
            "density": "mosaic",
        },
        "split_tension": {
            "name": "Split Tension Cards",
            "description": "Cards em duas metades com tensao visual, sem arredondar",
            "container": "grid md:grid-cols-2 gap-0 border-y-2 border-[--primary]",
            "card_class": "p-8 border-r-2 border-[--primary] last:border-r-0",
            "title_class": "uppercase italic text-4xl",
            "body_class": "uppercase text-sm tracking-widest mt-4",
            "image_treatment": "grayscale",
            "density": "mosaic",
        },
    },
    "corporate": {
        "three_column": {
            "name": "Three Column Grid",
            "description": "Grid 3 colunas, cards limpos, profissional e legivel",
            "container": "grid md:grid-cols-3 gap-6",
            "card_class": "rounded-md p-6 bg-[--surface] border border-[--border]",
            "title_class": "text-xl font-semibold",
            "body_class": "text-sm text-[--muted] mt-3",
            "image_treatment": "clean",
            "density": "balanced",
        },
        "list_with_icon": {
            "name": "List With Icon",
            "description": "Lista vertical com icone lateral, foco em autoridade",
            "container": "flex flex-col divide-y divide-[--border] max-w-3xl mx-auto",
            "card_class": "py-6 flex items-start gap-4",
            "title_class": "text-lg font-medium",
            "body_class": "text-sm text-[--muted] mt-1",
            "image_treatment": "clean",
            "density": "tight",
        },
    },
    "minimal": {
        "bento_grid": {
            "name": "Bento Grid",
            "description": "Grid Bento com celulas de tamanhos diferentes, glass-card",
            "container": "grid grid-cols-12 gap-3 auto-rows-[minmax(140px,auto)]",
            "card_class": "rounded-xl glass-card p-6",
            "card_sizes": ["col-span-7 row-span-2", "col-span-5", "col-span-4", "col-span-4", "col-span-4"],
            "title_class": "text-xl lowercase font-medium",
            "body_class": "text-sm text-[--muted] mt-2",
            "image_treatment": "glass",
            "density": "tight",
        },
        "feature_list": {
            "name": "Feature List",
            "description": "Lista minimalista com icone geometrico",
            "container": "grid md:grid-cols-2 gap-x-12 gap-y-8",
            "card_class": "border-t border-white/10 pt-6",
            "title_class": "text-lg lowercase",
            "body_class": "text-sm text-[--muted] mt-2",
            "image_treatment": "glass",
            "density": "balanced",
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# GALLERY DISPLAY MODES - Modos de display da Galeria por polo
# ═══════════════════════════════════════════════════════════════════════════

GALLERY_DISPLAY_MODES: dict[str, dict[str, dict[str, Any]]] = {
    "soft": {
        "masonry": {
            "name": "Masonry Soft",
            "description": "Masonry classico com padding generoso e imagens arredondadas",
            "container": "columns-1 md:columns-2 lg:columns-3 gap-6",
            "card_class": "rounded-[32px] mb-6 break-inside-avoid",
            "image_class": "rounded-[32px] w-full",
            "image_treatment": "warm",
            "density": "editorial",
        },
        "carousel_soft": {
            "name": "Carousel Soft",
            "description": "Carousel horizontal com cards grandes e respiro",
            "container": "flex gap-6 overflow-x-auto snap-x snap-mandatory pb-4",
            "card_class": "rounded-[32px] min-w-[320px] snap-center",
            "image_class": "rounded-[32px] aspect-[4/5]",
            "image_treatment": "warm",
            "density": "balanced",
        },
    },
    "bold": {
        "mosaic_chaos": {
            "name": "Mosaic Chaos",
            "description": "Grid com sobreposicoes agressivas, sem gap, imagens gritando",
            "container": "grid grid-cols-12 gap-1",
            "card_class": "rounded-none",
            "card_sizes": ["col-span-8 row-span-2", "col-span-4", "col-span-5", "col-span-7", "col-span-6", "col-span-6"],
            "image_class": "rounded-none grayscale contrast-125 w-full h-full object-cover",
            "image_treatment": "grayscale",
            "density": "mosaic",
        },
        "strip": {
            "name": "Horizontal Strip",
            "description": "Strip horizontal unica, ritmo rapido",
            "container": "flex gap-1 overflow-x-auto",
            "card_class": "rounded-none min-w-[260px] flex-shrink-0",
            "image_class": "rounded-none aspect-square w-full object-cover",
            "image_treatment": "grayscale",
            "density": "tight",
        },
    },
    "corporate": {
        "grid_clean": {
            "name": "Grid Clean",
            "description": "Grid 3 colunas, leve gap, imagens objetivas",
            "container": "grid md:grid-cols-3 gap-4",
            "card_class": "rounded-md overflow-hidden",
            "image_class": "rounded-md aspect-square w-full object-cover",
            "image_treatment": "clean",
            "density": "balanced",
        },
        "lightbox_grid": {
            "name": "Lightbox Grid",
            "description": "Grid com lightbox no clique, foco em portfolio profissional",
            "container": "grid md:grid-cols-4 gap-3",
            "card_class": "rounded-sm overflow-hidden cursor-zoom-in",
            "image_class": "rounded-sm aspect-square w-full object-cover",
            "image_treatment": "clean",
            "density": "tight",
        },
    },
    "minimal": {
        "bento_gallery": {
            "name": "Bento Gallery",
            "description": "Bento grid com proporcoes variadas, glass-card",
            "container": "grid grid-cols-12 gap-2 auto-rows-[minmax(120px,auto)]",
            "card_class": "rounded-xl glass-card overflow-hidden",
            "card_sizes": ["col-span-8 row-span-2", "col-span-4", "col-span-4", "col-span-4", "col-span-4", "col-span-7", "col-span-5"],
            "image_class": "rounded-xl w-full h-full object-cover",
            "image_treatment": "glass",
            "density": "tight",
        },
        "mosaic_tech": {
            "name": "Mosaic Tech",
            "description": "Mosaico moderno com proporcoes douradas",
            "container": "grid grid-cols-4 gap-2 auto-rows-[180px]",
            "card_class": "rounded-lg overflow-hidden",
            "card_sizes": ["col-span-2 row-span-2", "col-span-2", "col-span-2", "col-span-1", "col-span-1", "col-span-2"],
            "image_class": "rounded-lg w-full h-full object-cover",
            "image_treatment": "glass",
            "density": "balanced",
        },
    },
}


def get_hero_display_mode(pole: str, mode: str | None = None) -> dict[str, Any]:
    """
    Retorna a configuração do display mode do Hero.

    Args:
        pole: Polo estético
        mode: Modo específico (opcional, usa default se None)

    Returns:
        Dict com configurações do hero
    """
    modes = HERO_DISPLAY_MODES.get(pole, HERO_DISPLAY_MODES["corporate"])

    if mode and mode in modes:
        return modes[mode]

    # Default display mode - usar corporate quando o polo vier desconhecido.
    trigger = POLE_TRIGGERS.get(pole, POLE_TRIGGERS["corporate"])
    default_mode = trigger["default_display_mode"]
    if default_mode in modes:
        return modes[default_mode]

    # Fallback seguro: primeiro modo disponível
    return list(modes.values())[0]


def get_component_variant(component: str, pole: str) -> str:
    """
    Retorna a classe CSS do componente para o polo.

    Args:
        component: Nome do componente (Button, Card, Badge, Input)
        pole: Polo estético

    Returns:
        String com classes CSS
    """
    variants = COMPONENT_VARIANTS.get(component, {})
    return variants.get(pole, variants.get("corporate", ""))


def get_services_display_mode(pole: str, mode: str | None = None) -> dict[str, Any]:
    """
    Retorna a configuracao do display mode da secao de Servicos.

    Args:
        pole: Polo estetico (soft | bold | corporate | minimal)
        mode: Modo especifico (opcional, usa default do polo se None)

    Returns:
        Dict com container/card/title/body classes + image_treatment/density
    """
    pole = (pole or "").lower().strip()
    modes = SERVICES_DISPLAY_MODES.get(pole, SERVICES_DISPLAY_MODES["corporate"])

    if mode and mode in modes:
        return modes[mode]

    # Default por polo
    if pole == "soft":
        default = "stacked_cards"
    elif pole == "bold":
        default = "mosaic"
    elif pole == "minimal":
        default = "bento_grid"
    else:
        default = "three_column"

    if default in modes:
        return modes[default]

    # Fallback seguro: primeiro modo disponivel
    return list(modes.values())[0]


def get_gallery_display_mode(pole: str, mode: str | None = None) -> dict[str, Any]:
    """
    Retorna a configuracao do display mode da Galeria.

    Args:
        pole: Polo estetico (soft | bold | corporate | minimal)
        mode: Modo especifico (opcional, usa default do polo se None)

    Returns:
        Dict com container/card/image classes + image_treatment/density
    """
    pole = (pole or "").lower().strip()
    modes = GALLERY_DISPLAY_MODES.get(pole, GALLERY_DISPLAY_MODES["corporate"])

    if mode and mode in modes:
        return modes[mode]

    # Default por polo
    if pole == "soft":
        default = "masonry"
    elif pole == "bold":
        default = "mosaic_chaos"
    elif pole == "minimal":
        default = "bento_gallery"
    else:
        default = "grid_clean"

    if default in modes:
        return modes[default]

    return list(modes.values())[0]


# ═══════════════════════════════════════════════════════════════════════════
# LLM PROMPT GUIDE
# ═══════════════════════════════════════════════════════════════════════════


def get_liquid_component_guide(pole: str, hero_mode: str | None = None) -> str:
    """
    Gera o guide de componentes líquidos para o LLM.

    Args:
        pole: Polo estético
        hero_mode: Modo do hero (opcional)

    Returns:
        String com o guide formatado
    """
    tokens = POLO_TOKENS.get(pole, POLO_TOKENS["corporate"])
    hero_config = get_hero_display_mode(pole, hero_mode)
    services_config = get_services_display_mode(pole)
    gallery_config = get_gallery_display_mode(pole)

    tokens_lines = "\n".join(
        f"  --{key}: {value}" if not isinstance(value, bool) else f"  --{key}: {str(value).lower()}"
        for key, value in tokens.items()
    )

    return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LIQUID COMPONENTS - POLO {pole.upper():<10}                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

DESIGN TOKENS for this pole (apply these EXACTLY):
{tokens_lines}

HERO DISPLAY MODE: {hero_config.get('name', 'Default')}
{hero_config.get('description', '')}

HERO LAYOUT EXAMPLE:
```tsx
<section className="{hero_config.get('layout', '')}">
  <span className="{hero_config.get('badge_style', '')}">{{badge}}</span>
  <h1 className="{hero_config.get('headline_class', '')}">{{headline}}</h1>
  <button className="{hero_config.get('cta_style', '')}">{{cta}}</button>
</section>
```

SERVICES DISPLAY MODE: {services_config.get('name', 'Default')}
{services_config.get('description', '')}
- container: `{services_config.get('container', '')}`
- card_class: `{services_config.get('card_class', '')}`
- title_class: `{services_config.get('title_class', '')}`
- body_class: `{services_config.get('body_class', '')}`
- image_treatment: {services_config.get('image_treatment', '')}
- density: {services_config.get('density', '')}

GALLERY DISPLAY MODE: {gallery_config.get('name', 'Default')}
{gallery_config.get('description', '')}
- container: `{gallery_config.get('container', '')}`
- card_class: `{gallery_config.get('card_class', '')}`
- image_class: `{gallery_config.get('image_class', '')}`
- image_treatment: {gallery_config.get('image_treatment', '')}
- density: {gallery_config.get('density', '')}

COMPONENT CLASSES:
- Button: {get_component_variant('Button', pole)}
- Card: {get_component_variant('Card', pole)}
- Badge: {get_component_variant('Badge', pole)}
- Input: {get_component_variant('Input', pole)}

CSS VARIABLES TO USE:
- border-radius: var(--pole-radius)
- box-shadow: var(--pole-shadow-card)
- font-family: var(--pole-heading-font)
- transform: skewX(var(--pole-text-skew))
- transition: all var(--pole-motion-speed) var(--pole-motion-ease)

IMPORTANT:
- Use ONLY classes from this pole, don't mix with other poles
- Apply {pole} design tokens consistently across ALL components
- For BOLD pole: use text-stroke, skew, overlap effects
- For SOFT pole: use rounded corners, soft shadows, serif fonts
- For CORPORATE pole: use clean grid, subtle shadows, sans-serif
- For MINIMAL pole: use glass effects, geometric shapes, lowercase
"""


def get_css_variables_for_pole(pole: str) -> str:
    """
    Gera a string de variáveis CSS para um polo.

    Args:
        pole: Polo estético

    Returns:
        String com variáveis CSS formatadas
    """
    tokens = POLO_TOKENS.get(pole, POLO_TOKENS["corporate"])

    lines = [f"  /* POLO {pole.upper()} */"]
    for key, value in tokens.items():
        # Converter underscore para hífen para CSS
        css_key = key.replace("_", "-")
        lines.append(f"  --{css_key}: {value};")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# COMPATIBILITY EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

# Para manter compatibilidade com código existente
AESTHETIC_PERSONALITIES = POLO_TOKENS

__all__ = [
    "POLO_TOKENS",
    "HERO_DISPLAY_MODES",
    "SERVICES_DISPLAY_MODES",
    "GALLERY_DISPLAY_MODES",
    "COMPONENT_VARIANTS",
    "POLE_TRIGGERS",
    "infer_aesthetic_pole",
    "get_hero_display_mode",
    "get_services_display_mode",
    "get_gallery_display_mode",
    "get_component_variant",
    "get_liquid_component_guide",
    "get_css_variables_for_pole",
    "AESTHETIC_PERSONALITIES",
    "PoleInfo",
]
