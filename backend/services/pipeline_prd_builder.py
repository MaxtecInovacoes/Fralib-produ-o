"""PRD Builder - Compatibility wrapper module.

This module re-exports functions from specialized pipeline modules for backward compatibility.
All functions are now organized into dedicated modules:
- pipeline_validators: Pure validation and sanitization functions
- pipeline_media: Media handling and image processing functions
- pipeline_builders: Core PRD building functions
- pipeline_prompt_agent: Prompt agent PRD builder

For new code, import directly from the specialized modules.
"""

from __future__ import annotations

# Re-export from validators module
from backend.services.pipeline_validators import (
    normalize_segment,
    ascii_text,
    sanitize_keyword_term,
    extract_neighborhood,
    derive_subniche,
    build_local_keyword_terms,
    review_highlights_from_reviews,
    object_to_dict,
    LOCAL_STOPWORDS,
    SUBNICHE_RULES,
)

# Re-export from media module
from backend.services.pipeline_media import (
    is_supported_editorial_image_url,
    normalize_editorial_image_url,
    editorial_image_reachable,
    media_defaults_for_segment,
    deterministic_media_bundle,
    extract_media_urls,
    clean_public_text,
    NICHE_MEDIA_LIBRARY,
)

# Re-export from builders module
from backend.services.pipeline_builders import (
    build_skill_fast_prd,
    ensure_prd_design_reference,
    ensure_prd_contracts,
    ensure_prd_publication_identity,
    _contract_builders,
)

# Re-export from prompt agent module
from backend.services.pipeline_prompt_agent import build_prompt_agent_prd


# ─── Legacy alias functions (for backward compatibility) ────────────────────────

def _normalize_segment(segmento):
    """Deprecated: Use normalize_segment from pipeline_validators."""
    return normalize_segment(segmento)


def _ascii_text(value):
    """Deprecated: Use ascii_text from pipeline_validators."""
    return ascii_text(value)


def _sanitize_keyword_term(value, *, limit=60):
    """Deprecated: Use sanitize_keyword_term from pipeline_validators."""
    return sanitize_keyword_term(value, limit=limit)


def _extract_neighborhood(address):
    """Deprecated: Use extract_neighborhood from pipeline_validators."""
    return extract_neighborhood(address)


def _derive_subniche(segmento, *, services, reviews, keywords, business_name):
    """Deprecated: Use derive_subniche from pipeline_validators."""
    return derive_subniche(segmento, services=services, reviews=reviews, keywords=keywords, business_name=business_name)


def _build_local_keyword_terms(*, name, segment, city, neighborhood, subniche, services, raw_keywords):
    """Deprecated: Use build_local_keyword_terms from pipeline_validators."""
    return build_local_keyword_terms(
        name=name,
        segment=segment,
        city=city,
        neighborhood=neighborhood,
        subniche=subniche,
        services=services,
        raw_keywords=raw_keywords,
    )


def _is_supported_editorial_image_url(url):
    """Deprecated: Use is_supported_editorial_image_url from pipeline_media."""
    return is_supported_editorial_image_url(url)


def _normalize_editorial_image_url(url, *, og=False):
    """Deprecated: Use normalize_editorial_image_url from pipeline_media."""
    return normalize_editorial_image_url(url, og=og)


def _editorial_image_reachable(url):
    """Deprecated: Use editorial_image_reachable from pipeline_media."""
    return editorial_image_reachable(url)


def _media_defaults_for_segment(segmento):
    """Deprecated: Use media_defaults_for_segment from pipeline_media."""
    return media_defaults_for_segment(segmento)


def _deterministic_media_bundle(segmento, raw_photos, raw_og_image=""):
    """Deprecated: Use deterministic_media_bundle from pipeline_media."""
    return deterministic_media_bundle(segmento, raw_photos, raw_og_image)


# ─── Additional exports that were in original module ─────────────────────────

def visual_archetype_id(segmento: str, nome: str = "", dados_lead: dict | None = None) -> str:
    """Get the visual archetype ID for a segment.

    Args:
        segmento: The business segment.
        nome: Optional business name.
        dados_lead: Optional lead data dictionary.

    Returns:
        The archetype string identifier.
    """
    try:
        from core.archetypes import select_archetype
    except Exception:
        from archetypes import select_archetype
    try:
        return select_archetype(segmento, nome, dados_lead).get("archetype", "")
    except Exception:
        return ""
