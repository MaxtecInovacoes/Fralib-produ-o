"""Deterministic Design DNA mixer over the existing design token library."""


import hashlib
import random
from copy import deepcopy
from typing import Any

try:
    from agents.design_context import DIRECOES_VISUAIS
except Exception:  # pragma: no cover - local import variant
    from design_context import DIRECOES_VISUAIS

try:
    from core.archetypes import select_archetype
except Exception:  # pragma: no cover - local import variant
    from archetypes import select_archetype

try:
    from core.color_library import choose_palette
except Exception:  # pragma: no cover - local import variant
    from color_library import choose_palette

try:
    from core.design_reference_packs import (
        build_design_reference_pack,
        build_visual_seed as _build_reference_visual_seed,
    )
except Exception:  # pragma: no cover - local import variant
    from design_reference_packs import (
        build_design_reference_pack,
        build_visual_seed as _build_reference_visual_seed,
    )


ARCHETYPE_REFERENCES: dict[str, dict[str, list[str]]] = {
    "BOLD_ENERGY": {
        "structure": ["nike", "bold", "bmw_m", "spotify", "theverge", "uber"],
        "typography": ["bold", "uber", "theverge", "spacex", "energetic"],
        "color": ["bmw_m", "spotify", "renault", "vodafone", "bold"],
        "motion": ["energetic", "vibrant", "spotify", "theverge"],
        "spacing": ["nike", "bold", "spacex", "dramatic"],
    },
    "TRUST_ELITE": {
        "structure": ["apple", "bmw", "corporate", "linear", "wise", "webflow"],
        "typography": ["apple", "bmw", "refined", "linear", "corporate"],
        "color": ["bmw", "coinbase", "wise", "webex", "corporate"],
        "motion": ["apple", "elegant", "linear", "webflow"],
        "spacing": ["apple", "spacious", "corporate", "linear"],
    },
    "ZEN_PURE": {
        "structure": ["airbnb", "apple", "warm_editorial", "clay", "starbucks", "clean"],
        "typography": ["warm_editorial", "apple", "airbnb", "refined", "clean"],
        "color": ["starbucks", "airbnb", "clay", "clean", "claude"],
        "motion": ["elegant", "airbnb", "clay", "warm_editorial"],
        "spacing": ["spacious", "apple", "airbnb", "clean"],
    },
    "MODERN_TECH": {
        "structure": ["linear", "vercel", "linear", "cursor", "supabase", "webflow"],
        "typography": ["vercel", "linear", "cursor", "supabase", "webflow"],
        "color": ["linear", "supabase", "cursor", "canva", "webflow"],
        "motion": ["linear", "vercel", "canva", "vibrant"],
        "spacing": ["vercel", "linear", "linear", "webflow"],
    },
    "LUXURY_ELITE": {
        "structure": ["bugatti", "bmw", "runwayml", "warm_editorial", "refined"],
        "typography": ["bugatti", "refined", "warm_editorial", "bmw"],
        "color": ["bugatti", "runwayml", "bmw", "resend", "warm_editorial"],
        "motion": ["bugatti", "runwayml", "elegant", "refined"],
        "spacing": ["bugatti", "spacious", "runwayml", "refined"],
    },
}


def build_visual_seed(lead_id: str = "", business_name: str = "", segmento: str = "") -> str:
    return _build_reference_visual_seed(lead_id, business_name, segmento)


def build_design_dna(
    segmento: str,
    business_name: str = "",
    lead_id: str = "",
    tier: str = "STANDARD",
    base_design: dict[str, Any] | None = None,
    dados_lead: dict | None = None,
) -> dict[str, Any]:
    """Create a unique but controlled visual DNA for one generated site."""
    archetype = select_archetype(segmento, business_name, dados_lead)
    archetype_id = archetype["archetype"]
    visual_seed = build_visual_seed(lead_id, business_name, segmento)
    rng = random.Random(int(visual_seed[:12], 16))
    reference_pack = build_design_reference_pack(
        segmento=segmento,
        business_name=business_name,
        lead_id=lead_id,
        tier=tier,
        base_design=base_design,
        dados_lead=dados_lead,
    )
    refs = ARCHETYPE_REFERENCES.get(archetype_id, ARCHETYPE_REFERENCES["TRUST_ELITE"])

    def pick(group: str) -> str:
        pool = [item for item in refs[group] if item in DIRECOES_VISUAIS]
        if not pool:
            pool = list(DIRECOES_VISUAIS.keys())
        return rng.choice(pool)

    dna_combo = reference_pack.get("dna_combo") or {
        "structure_ref": pick("structure"),
        "typography_ref": pick("typography"),
        "color_ref": pick("color"),
        "motion_ref": pick("motion"),
        "spacing_ref": pick("spacing"),
    }
    structure = DIRECOES_VISUAIS.get(dna_combo["structure_ref"], {})
    typography = DIRECOES_VISUAIS.get(dna_combo["typography_ref"], {})
    color = DIRECOES_VISUAIS.get(dna_combo["color_ref"], {})
    motion = DIRECOES_VISUAIS.get(dna_combo["motion_ref"], {})
    palette = choose_palette(archetype_id, visual_seed)
    mixed_tokens = deepcopy(palette["tokens"])
    reference_pack = deepcopy(reference_pack)
    reference_pack["tokens"] = deepcopy(mixed_tokens)
    reference_pack["runtime_palette"] = {
        "id": palette["id"],
        "strategy": palette["strategy"],
        "contrast": palette["contrast"],
    }
    visual_variation = _build_variation(rng, archetype_id)
    pack_typography = reference_pack.get("typography") or {}
    return {
        "visual_seed": visual_seed,
        "archetype": archetype,
        "dna_combo": dna_combo,
        "tokens": mixed_tokens,
        "palette_id": palette["id"],
        "color_strategy": palette["strategy"],
        "palette_contrast": palette["contrast"],
        "font_heading": pack_typography.get("heading") or typography.get("font_heading") or (base_design or {}).get("font_heading"),
        "font_body": pack_typography.get("body") or typography.get("font_body") or (base_design or {}).get("font_body"),
        "style_mix_instruction": (
            reference_pack.get("instruction")
            or f"Use estrutura inspirada em {dna_combo['structure_ref']}, "
            f"tipografia de {dna_combo['typography_ref']}, paleta de {dna_combo['color_ref']}, "
            f"motion de {dna_combo['motion_ref']} e espaco de {dna_combo['spacing_ref']}."
        ),
        "reference_vibes": {
            "structure": structure.get("vibe", ""),
            "typography": typography.get("vibe", ""),
            "color": color.get("vibe", ""),
            "motion": motion.get("vibe", ""),
        },
        "design_reference_pack": reference_pack,
        "variation": visual_variation,
        "tier": tier,
    }


def _build_variation(rng: random.Random, archetype_id: str) -> dict[str, Any]:
    radius = rng.choice(["10px", "14px", "18px", "24px", "32px"])
    padding = rng.choice(["96px", "112px", "128px", "144px"])
    hero_density = rng.choice(["cinematic", "editorial", "immersive"])
    image_treatment = rng.choice(["soft-mask", "hard-crop", "full-bleed", "floating"])
    grid_bias = rng.choice(["asymmetric-left", "asymmetric-right", "z-pattern", "centered-break"])
    if archetype_id == "BOLD_ENERGY":
        hero_density = rng.choice(["cinematic", "immersive"])
        image_treatment = rng.choice(["hard-crop", "full-bleed"])
    elif archetype_id == "ZEN_PURE":
        radius = rng.choice(["24px", "32px", "999px"])
        image_treatment = rng.choice(["soft-mask", "floating"])
    return {
        "radius": radius,
        "section_padding": padding,
        "hero_density": hero_density,
        "image_treatment": image_treatment,
        "grid_bias": grid_bias,
    }


def choose_section_variant(section: str, visual_seed: str, archetype_id: str = "") -> str:
    variants = {
        "hero": ["hero-split-left", "hero-full-bleed", "hero-editorial-stack", "hero-image-overlay", "hero-z-pattern"],
        "trust-bar": ["stats-horizontal", "proof-strip", "score-wall"],
        "sobre": ["about-editorial", "about-proof-led", "about-image-aside", "about-statement"],
        "diferenciais": ["insight-bento", "proof-led-list", "asymmetric-feature-grid"],
        "servicos": ["services-bento", "services-marquee", "services-editorial-list"],
        "depoimentos": ["reviews-spotlight", "reviews-marquee", "reviews-editorial-quotes", "reviews-score-wall"],
        "localizacao": ["location-split", "map-editorial", "local-proof-panel"],
        "contato": ["contact-panel", "contact-split", "footer-integrated-contact"],
        "footer": ["footer-themed", "footer-editorial", "footer-integrated"],
    }
    seed = int(hashlib.md5(f"{visual_seed}:{section}:{archetype_id}".encode()).hexdigest()[:8], 16)
    pool = variants.get(section, [section])
    return pool[seed % len(pool)]
