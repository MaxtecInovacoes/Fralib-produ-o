from __future__ import annotations

from typing import Any

try:
    from backend.services.vite_visual_lanes import resolve_visual_lane
except ImportError:
    from services.vite_visual_lanes import resolve_visual_lane  # type: ignore


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


def _resolve_nav_label(section: str, lane_copy: dict[str, Any]) -> str:
    copy_key_map = {
        "about": "nav_about",
        "services": "nav_services",
        "gallery": "nav_gallery",
        "faq": "nav_faq",
        "reviews": "nav_reviews",
        "location": "nav_location",
        "lifestyle": "nav_lifestyle",
        "contact-cta": "nav_contact",
    }
    key = copy_key_map.get(section, "")
    value = str(lane_copy.get(key) or "").strip()
    if value:
        return value
    return _NAV_LINK_MAP[section][0]


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
    visual_lane = str(variation.get("visual_lane") or "")
    lane = resolve_visual_lane(segment=segment, subnicho=str(variation.get("subnicho") or ""), visual_lane=visual_lane)
    lane_blocks = lane.get("blocks") if isinstance(lane.get("blocks"), dict) else {}
    lane_copy = lane.get("copy") if isinstance(lane.get("copy"), dict) else {}

    services_variant = str(lane_blocks.get("services_variant") or "split_editorial")
    if surface_style in {"solid", "soft_tint"}:
        services_variant = "stacked_cards"
    if proof_style == "card_marquee":
        services_variant = "stats_then_cards"

    faq_variant = str(lane_blocks.get("faq_variant") or "panel")
    if section_order_style in {"conversion_first", "gallery_first"}:
        faq_variant = "inline"

    location_variant = str(lane_blocks.get("location_variant") or "split_local")
    if "academia" in segment.lower() or hero_layout in {"fullbleed", "video"}:
        location_variant = "feature_local"

    hero_variant = str(lane_blocks.get("hero_variant") or hero_layout or "split")
    reviews_variant = str(lane_blocks.get("reviews_variant") or proof_style)
    surface_style = str(lane_blocks.get("surface_style") or surface_style)

    nav_links = [
        {"label": _resolve_nav_label(section, lane_copy), "href": href}
        for section, (_label, href) in _NAV_LINK_MAP.items()
        if section in section_order
    ]
    return {
        "archetype": archetype,
        "segment": segment,
        "section_order": section_order,
        "nav_links": nav_links,
        "hero_variant": hero_variant,
        "services_variant": services_variant,
        "reviews_variant": reviews_variant,
        "faq_variant": faq_variant,
        "location_variant": location_variant,
        "surface_style": surface_style,
        "section_order_style": section_order_style,
        "visual_lane": lane.get("id") or visual_lane,
        "visual_lane_name": lane.get("name") or "",
    }
