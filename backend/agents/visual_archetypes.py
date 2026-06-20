"""Compatibility helpers for the canonical visual archetype engine."""

from __future__ import annotations

try:
    from core.archetypes import select_archetype
except Exception:  # pragma: no cover - fallback for direct agent imports
    from archetypes import select_archetype  # type: ignore


def select_visual_archetype(segmento: str, business_name: str = "") -> dict[str, str]:
    """Return compact visual DNA using the canonical core archetypes."""
    dna = select_archetype(segmento, business_name)
    composition = "; ".join(dna.get("composition_laws") or [])
    media = ", ".join(dna.get("media_query_modifiers") or [])
    typography = dna.get("typography") or {}
    return {
        "name": str(dna.get("archetype") or "TRUST_ELITE"),
        "voice": str(dna.get("visual_voice") or ""),
        "composition": composition,
        "media": media,
        "motion": str(dna.get("section_disruption") or ""),
        "avoid": "layout institucional generico, claims sem prova, cards repetidos sem hierarquia",
        "color_theory": str(dna.get("color_theory") or ""),
        "typography": ", ".join(str(value) for value in typography.values() if value),
    }


def archetype_prompt(segmento: str, business_name: str = "") -> str:
    dna = select_visual_archetype(segmento, business_name)
    return (
        f"VISUAL ARCHETYPE: {dna['name']}\n"
        f"VOICE: {dna['voice']}\n"
        f"COLOR THEORY: {dna['color_theory']}\n"
        f"TYPOGRAPHY: {dna['typography']}\n"
        f"COMPOSITION: {dna['composition']}\n"
        f"MOTION: {dna['motion']}\n"
        f"AVOID: {dna['avoid']}"
    )
