"""
Biblioteca de Design Systems + Templates Nichados.

Cada nicho tem:
- Paleta de cores (curada Awwwards-grade)
- Typography (display + body)
- Motion hooks (data-parallax, data-reveal, mask-reveal)
- Layout pattern (hero, sections, density)
- Componentes preferidos

Inspirado em: Awwwards, SiteInspire, godly.website
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ColorPalette:
    primary: str
    secondary: str
    accent: str
    bg: str
    fg: str
    muted: str


@dataclass(frozen=True)
class Typography:
    display: str  # "Oswald", "Cormorant Garamond", "Fraunces"
    body: str  # "Inter", "DM Sans"
    weight_display: int
    weight_body: int
    contrast: Literal["high", "medium", "low"]


@dataclass(frozen=True)
class MotionConfig:
    parallax: bool
    reveal_on_scroll: bool
    mask_reveal: bool
    cursor_effects: bool
    video_allowed: bool


@dataclass(frozen=True)
class SectionConfig:
    hero_type: Literal["video", "split", "fullscreen", "diagonal", "magazine"]
    has_testimonials: bool
    has_pricing: bool
    has_faq: bool
    has_location_map: bool
    density: Literal["sparse", "medium", "dense"]


@dataclass(frozen=True)
class DesignSystem:
    nicho: str
    subnicho: str
    paleta: ColorPalette
    typography: Typography
    motion: MotionConfig
    sections: SectionConfig
    inspiration_refs: tuple[str, ...] = field(default_factory=tuple)


# ════════════════════════════════════════════════════════════════════
# ACADEMIA / CROSSFIT / PILATES / MUAY THAI / JIU JITSU
# ════════════════════════════════════════════════════════════════════

ACADEMIA = DesignSystem(
    nicho="academia",
    subnicho="crossfit",
    paleta=ColorPalette(
        primary="#0A0A0A",  # black
        secondary="#E63946",  # red energy
        accent="#F4A261",  # warm orange
        bg="#FFFFFF",
        fg="#0A0A0A",
        muted="#6C757D",
    ),
    typography=Typography(
        display="Oswald",
        body="Inter",
        weight_display=700,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=True,
        reveal_on_scroll=True,
        mask_reveal=True,
        cursor_effects=True,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="video",
        has_testimonials=True,
        has_pricing=True,
        has_faq=True,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Crossfit boxes", "Crossfit Crown", "Norcal Crossfit"),
)

PILATES = DesignSystem(
    nicho="academia",
    subnicho="pilates",
    paleta=ColorPalette(
        primary="#F8F4F0",  # cream
        secondary="#9D8189",  # dusty rose
        accent="#D4A5A5",  # soft pink
        bg="#FBF8F5",
        fg="#2C2C2C",
        muted="#A89B95",
    ),
    typography=Typography(
        display="Cormorant Garamond",
        body="DM Sans",
        weight_display=300,
        weight_body=400,
        contrast="low",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=False,
        cursor_effects=False,
        video_allowed=False,
    ),
    sections=SectionConfig(
        hero_type="fullscreen",
        has_testimonials=True,
        has_pricing=True,
        has_faq=False,
        has_location_map=True,
        density="sparse",
    ),
    inspiration_refs=("Studio Pilates", "Breathe Pilates", "Polestar Pilates"),
)

# ════════════════════════════════════════════════════════════════════
# RESTAURANTE / BAR / CAFE / PIZZARIA / HAMBURGUERIA
# ════════════════════════════════════════════════════════════════════

RESTAURANTE_BISTRO = DesignSystem(
    nicho="restaurante",
    subnicho="bistro",
    paleta=ColorPalette(
        primary="#2A1810",  # dark coffee
        secondary="#D4A574",  # warm gold
        accent="#C9302C",  # burgundy
        bg="#FAF6F0",
        fg="#2A1810",
        muted="#8B7355",
    ),
    typography=Typography(
        display="Cormorant Garamond",
        body="Lato",
        weight_display=600,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=True,
        reveal_on_scroll=True,
        mask_reveal=True,
        cursor_effects=False,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="fullscreen",
        has_testimonials=True,
        has_pricing=False,
        has_faq=True,
        has_location_map=True,
        density="sparse",
    ),
    inspiration_refs=("Eleven Madison Park", "French Laundry", "Balthazar"),
)

HAMBURGUERIA = DesignSystem(
    nicho="restaurante",
    subnicho="hamburgueria",
    paleta=ColorPalette(
        primary="#FF6B35",  # bold orange
        secondary="#1A1A1A",  # black
        accent="#FFD23F",  # mustard
        bg="#FFFFFF",
        fg="#1A1A1A",
        muted="#666666",
    ),
    typography=Typography(
        display="Anton",
        body="Inter",
        weight_display=700,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=True,
        cursor_effects=True,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="split",
        has_testimonials=True,
        has_pricing=False,
        has_faq=False,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Five Guys", "Shake Shack", "Bob's Burgers"),
)

# ════════════════════════════════════════════════════════════════════
# CLINICA / DENTISTA / ESTETICA / VETERINARIA
# ════════════════════════════════════════════════════════════════════

CLINICA_DENTAL = DesignSystem(
    nicho="clinica",
    subnicho="dentista",
    paleta=ColorPalette(
        primary="#FFFFFF",
        secondary="#0EA5E9",  # sky blue
        accent="#06B6D4",  # cyan
        bg="#F8FAFC",
        fg="#1E293B",
        muted="#64748B",
    ),
    typography=Typography(
        display="Fraunces",
        body="DM Sans",
        weight_display=500,
        weight_body=400,
        contrast="medium",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=False,
        cursor_effects=False,
        video_allowed=False,
    ),
    sections=SectionConfig(
        hero_type="split",
        has_testimonials=True,
        has_pricing=True,
        has_faq=True,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Dental clinics moderno", "Aspen Dental", "Heartland Dental"),
)

ESTETICA = DesignSystem(
    nicho="clinica",
    subnicho="estetica",
    paleta=ColorPalette(
        primary="#1A1A1A",
        secondary="#E8B4B8",  # rose gold
        accent="#F8E5E5",  # blush
        bg="#FFFFFF",
        fg="#1A1A1A",
        muted="#8B8680",
    ),
    typography=Typography(
        display="Italiana",
        body="Manrope",
        weight_display=400,
        weight_body=400,
        contrast="medium",
    ),
    motion=MotionConfig(
        parallax=True,
        reveal_on_scroll=True,
        mask_reveal=True,
        cursor_effects=True,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="fullscreen",
        has_testimonials=True,
        has_pricing=True,
        has_faq=True,
        has_location_map=True,
        density="sparse",
    ),
    inspiration_refs=("Skin clinics", "Goop", "Glossier"),
)

# ════════════════════════════════════════════════════════════════════
# BARBEARIA / SALAO / SPA / MANICURE
# ════════════════════════════════════════════════════════════════════

BARBEARIA = DesignSystem(
    nicho="barbearia",
    subnicho="tradicional",
    paleta=ColorPalette(
        primary="#2C1810",  # dark brown
        secondary="#D4A574",  # brass
        accent="#C9302C",  # barber red
        bg="#FAF7F2",
        fg="#1A0F0A",
        muted="#6B5544",
    ),
    typography=Typography(
        display="Playfair Display",
        body="Roboto",
        weight_display=700,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=False,
        cursor_effects=False,
        video_allowed=False,
    ),
    sections=SectionConfig(
        hero_type="split",
        has_testimonials=True,
        has_pricing=True,
        has_faq=False,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Barbearias modernas", "Blind Barber", "Fellow Barber"),
)

SALAO_BELEZA = DesignSystem(
    nicho="salao",
    subnicho="beleza",
    paleta=ColorPalette(
        primary="#FFFFFF",
        secondary="#FF6B9D",  # pink
        accent="#C44569",  # mauve
        bg="#FFF8F8",
        fg="#2C2C2C",
        muted="#A89B95",
    ),
    typography=Typography(
        display="Playfair Display",
        body="Poppins",
        weight_display=500,
        weight_body=400,
        contrast="medium",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=True,
        cursor_effects=True,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="magazine",
        has_testimonials=True,
        has_pricing=True,
        has_faq=False,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Saloes premium", "Drybar", "Benjamin Salon"),
)

# ════════════════════════════════════════════════════════════════════
# OFICINA / MECANICA / LAVAGEM
# ════════════════════════════════════════════════════════════════════

OFICINA = DesignSystem(
    nicho="oficina",
    subnicho="mecanica",
    paleta=ColorPalette(
        primary="#1C1C1E",
        secondary="#FF3B30",  # brake red
        accent="#FFD60A",  # caution yellow
        bg="#FFFFFF",
        fg="#1C1C1E",
        muted="#8E8E93",
    ),
    typography=Typography(
        display="Barlow Condensed",
        body="Inter",
        weight_display=700,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=False,
        cursor_effects=False,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="diagonal",
        has_testimonials=True,
        has_pricing=True,
        has_faq=True,
        has_location_map=True,
        density="dense",
    ),
    inspiration_refs=("Mecanicas premium", "Auto detailing", "Tuner shops"),
)

# ════════════════════════════════════════════════════════════════════
# PET SHOP / VETERINARIA / HOTEL PET
# ════════════════════════════════════════════════════════════════════

PET_SHOP = DesignSystem(
    nicho="pet",
    subnicho="pet_shop",
    paleta=ColorPalette(
        primary="#FFB84D",  # warm orange
        secondary="#4ECDC4",  # teal
        accent="#FF6B6B",  # coral
        bg="#FFF9F0",
        fg="#2C3E50",
        muted="#95A5A6",
    ),
    typography=Typography(
        display="Fredoka",
        body="Nunito",
        weight_display=600,
        weight_body=400,
        contrast="medium",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=False,
        cursor_effects=True,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="magazine",
        has_testimonials=True,
        has_pricing=True,
        has_faq=True,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Pet shops modernos", "Bark", "Petco"),
)

# ════════════════════════════════════════════════════════════════════
# IMOBILIARIA / CORRETOR / CONSTRUTORA
# ════════════════════════════════════════════════════════════════════

IMOBILIARIA = DesignSystem(
    nicho="imobiliaria",
    subnicho="venda",
    paleta=ColorPalette(
        primary="#0F1419",  # charcoal
        secondary="#C9A96E",  # gold
        accent="#8B7355",  # bronze
        bg="#FAFAF7",
        fg="#0F1419",
        muted="#6B6B6B",
    ),
    typography=Typography(
        display="Cormorant Garamond",
        body="Inter",
        weight_display=500,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=True,
        reveal_on_scroll=True,
        mask_reveal=True,
        cursor_effects=False,
        video_allowed=True,
    ),
    sections=SectionConfig(
        hero_type="fullscreen",
        has_testimonials=True,
        has_pricing=False,
        has_faq=True,
        has_location_map=True,
        density="sparse",
    ),
    inspiration_refs=("Imobiliarias premium", "Sotheby's", "Christie's"),
)

# ════════════════════════════════════════════════════════════════════
# ADVOCACIA / ESCRITORIO / CONTABILIDADE
# ════════════════════════════════════════════════════════════════════

ADVOCACIA = DesignSystem(
    nicho="advocacia",
    subnicho="generalista",
    paleta=ColorPalette(
        primary="#1A2942",  # navy
        secondary="#C9A96E",  # gold accent
        accent="#A82B1E",  # burgundy
        bg="#FFFFFF",
        fg="#1A2942",
        muted="#6B7280",
    ),
    typography=Typography(
        display="Crimson Text",
        body="Lato",
        weight_display=600,
        weight_body=400,
        contrast="high",
    ),
    motion=MotionConfig(
        parallax=False,
        reveal_on_scroll=True,
        mask_reveal=False,
        cursor_effects=False,
        video_allowed=False,
    ),
    sections=SectionConfig(
        hero_type="split",
        has_testimonials=True,
        has_pricing=False,
        has_faq=True,
        has_location_map=True,
        density="medium",
    ),
    inspiration_refs=("Escritorios premium", "Big Law", "boutique firms"),
)


# ════════════════════════════════════════════════════════════════════
# REGISTRY
# ════════════════════════════════════════════════════════════════════

ALL_DESIGN_SYSTEMS: dict[str, DesignSystem] = {
    "academia/crossfit": ACADEMIA,
    "academia/pilates": PILATES,
    "restaurante/bistro": RESTAURANTE_BISTRO,
    "restaurante/hamburgueria": HAMBURGUERIA,
    "clinica/dentista": CLINICA_DENTAL,
    "clinica/estetica": ESTETICA,
    "barbearia/tradicional": BARBEARIA,
    "salao/beleza": SALAO_BELEZA,
    "oficina/mecanica": OFICINA,
    "pet/pet_shop": PET_SHOP,
    "imobiliaria/venda": IMOBILIARIA,
    "advocacia/generalista": ADVOCACIA,
}


NICHO_SYNONYMS = {
    "academia": "academia",
    "crossfit": "academia",
    "pilates": "academia",
    "musculacao": "academia",
    "jiu jitsu": "academia",
    "muay thai": "academia",
    "yoga": "academia",
    "restaurante": "restaurante",
    "bistro": "restaurante",
    "hamburgueria": "restaurante",
    "pizzaria": "restaurante",
    "cafe": "restaurante",
    "bar": "restaurante",
    "clinica": "clinica",
    "dentista": "clinica",
    "odontologia": "clinica",
    "estetica": "clinica",
    "veterinaria": "clinica",
    "barbearia": "barbearia",
    "salao": "salao",
    "cabeleireiro": "salao",
    "manicure": "salao",
    "oficina": "oficina",
    "mecanica": "oficina",
    "funilaria": "oficina",
    "pet shop": "pet",
    "veterinario": "pet",
    "imobiliaria": "imobiliaria",
    "corretor": "imobiliaria",
    "advocacia": "advocacia",
    "escritorio": "advocacia",
    "contabilidade": "advocacia",
}


def resolve_nicho(segmento: str, subnicho: str = "") -> DesignSystem | None:
    """Resolve o Design System baseado em segmento + subnicho."""
    seg_norm = (segmento or "").lower().strip()
    sub_norm = (subnicho or "").lower().strip()

    # 1. Match direto "nicho/subnicho"
    key = f"{seg_norm}/{sub_norm}"
    if key in ALL_DESIGN_SYSTEMS:
        return ALL_DESIGN_SYSTEMS[key]

    # 2. Match por subnicho (se passado e o subnicho existe em qualquer DS)
    if sub_norm:
        for full_key, ds in ALL_DESIGN_SYSTEMS.items():
            if full_key.endswith(f"/{sub_norm}"):
                return ds

    # 3. Sinonimo: pilates/hamburgueria/etc mapeiam para subnichos
    syn_to_sub = {
        "pilates": "pilates",
        "hamburgueria": "hamburgueria",
        "pet_shop": "pet_shop",
        "pet shop": "pet_shop",
        "petshop": "pet_shop",
        "pizzaria": "bistro",
        "cafe": "bistro",
        "bar": "bistro",
        "musculacao": "crossfit",
        "jiu jitsu": "crossfit",
        "muay thai": "crossfit",
        "yoga": "pilates",
        "odontologia": "dentista",
        "cabeleireiro": "beleza",
        "manicure": "beleza",
        "mecanica": "mecanica",
        "funilaria": "mecanica",
        "veterinario": "pet_shop",
        "corretor": "venda",
        "construtora": "venda",
        "escritorio": "generalista",
        "contabilidade": "generalista",
    }
    if seg_norm in syn_to_sub:
        target_sub = syn_to_sub[seg_norm]
        for full_key, ds in ALL_DESIGN_SYSTEMS.items():
            if full_key.endswith(f"/{target_sub}"):
                return ds

    # 4. Sinonimo simples: dentista -> clinica/dentista
    if seg_norm in NICHO_SYNONYMS:
        real_nicho = NICHO_SYNONYMS[seg_norm]
        for full_key, ds in ALL_DESIGN_SYSTEMS.items():
            if full_key.startswith(f"{real_nicho}/"):
                return ds

    return None


def list_all_nichos() -> list[str]:
    """Lista todos os nichos disponiveis."""
    return list(ALL_DESIGN_SYSTEMS.keys())
