"""archetype_resolver — Sprint 14.6.

Carrega studio_archetypes.json (cached em memoria) e resolve qual
variation (v1/v2/v3) de cada archetype aplicar baseado no
VariationSeed gerado por counter rotation.

Mapping:
- hero_layout split/center/asymmetric/fullbleed/video → layout_variations.v1-v3
- motion_style sharp/smooth/minimal → motion_variations.v1-v3
- copy_voice aggressive/friendly/authoritative → copy_variations.v1-v3

Cada mapping usa (seed XOR offset) % 3 para escolher entre v1, v2, v3.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_ARCHETYPES_PATH = Path(__file__).resolve().parent / "studio_archetypes.json"


@lru_cache(maxsize=1)
def _load_archetypes() -> dict[str, Any]:
    try:
        with _ARCHETYPES_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[archetype_resolver] falhou ao carregar studio_archetypes.json: {e}")
        return {"archetypes": {}}


# Mapeamentos hero_layout → qual variant prefere (Sprint 14.6 enrichment)
# Como HERO_LAYOUTS tem 5 valores e cada archetype tem 3 layout_variations,
# agrupamos para garantir uso das 3 variants diferentes.
_HERO_TO_LAYOUT_KEY = {
    "split": "v2_split_story",
    "center": "v1_centered_intro",
    "asymmetric": "v3_asymmetric_grid",
    "fullbleed": "v2_fullscreen_video",
    "video": "v2_fullscreen_video",
}

# Counter rotation: a cada 3 leads, proximo variant do archetype
# garante que v1/v2/v3 sao exercitados mesmo com mesmo hero_layout.
# Sprint 14.6: usa counter para garantir variacao maxima.
def _layout_with_counter(base_key: str, layout_variations: dict, counter: int) -> str:
    if not layout_variations:
        return base_key
    keys = list(layout_variations.keys())
    if base_key in keys:
        # usa base_key mas com offset de counter
        idx = keys.index(base_key)
        target_idx = (idx + counter) % len(keys)
        return keys[target_idx]
    return keys[counter % len(keys)]


# Mapeamentos motion_style → variant (3 valores)
# Sprint 14.6: 3 motion_styles → 3 variants (1:1 limpo)
_MOTION_TO_MOTION_KEY = {
    "sharp": "v1_explosive",
    "smooth": "v1_fade_slide",
    "minimal": "v3_no_motion",
}

# Mapeamentos copy_voice → variant (3 valores)
# Sprint 14.6: 3 copy_voices → 3 variants (1:1 limpo)
_COPY_TO_COPY_KEY = {
    "aggressive": "v1_aggressive",
    "friendly": "v1_community",
    "authoritative": "v1_experience",
}


def _pick_key(mapping: dict[str, str], value: str) -> str:
    return mapping.get(value) or next(iter(mapping.values()), "")


def resolve_archetype_variation(
    archetype: str,
    variation,
    *,
    subnicho: str | None = None,
    counter: int = 0,
) -> dict[str, Any]:
    """Resolve qual variation (v1/v2/v3) aplicar baseado em archetype + VariationSeed.

    Returns dict com:
      - layout_variant: nome do layout_variation escolhido (ex: v3_asymmetric_grid)
      - motion_variant: nome do motion_variation escolhido
      - copy_variant: nome do copy_variation escolhido
      - layout_config: dict com as classes/config do layout escolhido
      - motion_config: dict com a config de motion
      - copy_config: dict com patterns de copy
      - hero_classes: string com classes Tailwind da hero
      - section_order: lista de secao na ordem canonica do archetype
    """
    data = _load_archetypes()
    archetypes = data.get("archetypes") or {}
    arch = archetypes.get(archetype) or archetypes.get("PROFESSIONAL_TRUST") or {}

    layout_variations = arch.get("layout_variations") or {}
    motion_variations = arch.get("motion_variations") or {}
    copy_variations = arch.get("copy_variations") or {}
    base_layout = arch.get("layout") or {}

    # hero_layout → qual variant (fallback: primeira disponivel)
    hero_layout = getattr(variation, "hero_layout", "split") or "split"
    layout_key = _pick_key(_HERO_TO_LAYOUT_KEY, hero_layout)
    layout_key = _layout_with_counter(layout_key, layout_variations, counter)
    layout_config = layout_variations.get(layout_key) or (
        next(iter(layout_variations.values())) if layout_variations else {}
    )

    # motion_style → qual variant
    motion_style = getattr(variation, "motion_style", "smooth") or "smooth"
    motion_key = _pick_key(_MOTION_TO_MOTION_KEY, motion_style)
    motion_config = motion_variations.get(motion_key) or (
        next(iter(motion_variations.values())) if motion_variations else {}
    )

    # copy_voice → qual variant
    copy_voice = getattr(variation, "copy_voice", "friendly") or "friendly"
    copy_key = _pick_key(_COPY_TO_COPY_KEY, copy_voice)
    copy_config = copy_variations.get(copy_key) or (
        next(iter(copy_variations.values())) if copy_variations else {}
    )

    # Hero classes vem do variation do archetype + override da variation
    hero_classes = str(layout_config.get("hero_classes") or "").strip()

    # Section order canonica do archetype (baseline) — pode ser overridada por subnicho
    section_order = list(base_layout.get("section_order") or [])

    return {
        "archetype": archetype,
        "layout_variant": layout_key,
        "motion_variant": motion_key,
        "copy_variant": copy_key,
        "layout_config": layout_config,
        "motion_config": motion_config,
        "copy_config": copy_config,
        "hero_classes": hero_classes,
        "section_order": section_order,
        "subnicho": subnicho,
        "counter": counter,
    }


def archetype_for_segment(segmento: str | None) -> str:
    """Resolve archetype canonico a partir do segmento (reusa _get_archetype_for_segment)."""
    try:
        from backend.services.vite_react_renderer import _get_archetype_for_segment
    except ImportError:
        try:
            from services.vite_react_renderer import _get_archetype_for_segment
        except ImportError:
            return "PROFESSIONAL_TRUST"
    return _get_archetype_for_segment(segmento or "servicos")
