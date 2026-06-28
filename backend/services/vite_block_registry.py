from __future__ import annotations

from typing import Any


_NAV_LINK_MAP = {
    "about": ("Abordagem", "#sobre"),
    "services": ("Como funciona", "#servicos"),
    "gallery": ("Prova visual", "#galeria"),
    "faq": ("Dúvidas", "#faq"),
    "reviews": ("Avaliações", "#avaliacoes"),
    "location": ("Local", "#localizacao"),
    "lifestyle": ("Experiência", "#experiencia"),
    "contact-cta": ("Contato", "#contato"),
}


def resolve_cinematic_block_plan(
    *,
    section_order: list[str],
    variation: dict[str, Any] | None = None,
    archetype: str = "",
    segment: str = "",
) -> dict[str, Any]:
    variation = variation if isinstance(variation, dict) else {}
    proof_style = str(variation.get("proof_style") or "score_wall")
    surface_style = str(variation.get("surface_style") or "glass")
    hero_layout = str(variation.get("hero_layout") or "")
    section_order_style = str(variation.get("section_order_style") or "credibility_first")

    services_variant = "split_editorial"
    if surface_style in {"solid", "soft_tint"}:
        services_variant = "stacked_cards"
    if proof_style == "card_marquee":
        services_variant = "stats_then_cards"

    faq_variant = "panel"
    if section_order_style in {"conversion_first", "gallery_first"}:
        faq_variant = "inline"

    location_variant = "split_local"
    if "academia" in segment.lower() or hero_layout in {"fullbleed", "video"}:
        location_variant = "feature_local"

    nav_links = [
        {"label": label, "href": href}
        for section, (label, href) in _NAV_LINK_MAP.items()
        if section in section_order
    ]
    return {
        "archetype": archetype,
        "segment": segment,
        "section_order": section_order,
        "nav_links": nav_links,
        "hero_variant": hero_layout or "split",
        "services_variant": services_variant,
        "reviews_variant": proof_style,
        "faq_variant": faq_variant,
        "location_variant": location_variant,
        "surface_style": surface_style,
        "section_order_style": section_order_style,
    }
