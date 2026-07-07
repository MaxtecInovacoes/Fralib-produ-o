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
    surface_style = str(variation.get("surface_style") or "solid")
    anti_repetition_rule = str(variation.get("anti_repetition_rule") or "")
    hero_layout = str(variation.get("hero_layout") or "")
    section_order_style = str(
        variation.get("section_order_style") or "credibility_first"
    )
    visual_lane = str(variation.get("visual_lane") or "")
    lane = resolve_visual_lane(
        segment=segment,
        subnicho=str(variation.get("subnicho") or ""),
        visual_lane=visual_lane,
        prompt_priority=str(variation.get("prompt_priority") or ""),
    )
    lane_blocks = lane.get("blocks") if isinstance(lane.get("blocks"), dict) else {}
    lane_copy = lane.get("copy") if isinstance(lane.get("copy"), dict) else {}
    pricing_variant = str(
        variation.get("pricing_variant")
        or lane_blocks.get("pricing_variant")
        or "plan_grid"
    )
    stats_variant = str(
        variation.get("stats_variant")
        or lane_blocks.get("stats_variant")
        or "inline_hero_stats"
    )
    aesthetic_mode = str(
        variation.get("aesthetic_mode")
        or lane_blocks.get("aesthetic_mode")
        or "balanced"
    )
    spacing_density = str(
        variation.get("spacing_density")
        or lane_blocks.get("spacing_density")
        or "normal"
    )
    radius_mode = str(
        variation.get("radius_mode") or lane_blocks.get("radius_mode") or "balanced"
    )
    container_strategy = str(
        variation.get("container_strategy")
        or lane_blocks.get("container_strategy")
        or "contained"
    )
    typography_scale = str(
        variation.get("typography_scale")
        or lane_blocks.get("typography_scale")
        or "strong"
    )
    heading_style = str(
        variation.get("heading_style") or lane_blocks.get("heading_style") or "clean"
    )
    surface_depth = str(
        variation.get("surface_depth") or lane_blocks.get("surface_depth") or "elevated"
    )
    overlap_mode = str(
        variation.get("overlap_mode") or lane_blocks.get("overlap_mode") or "none"
    )
    motion_intensity = str(
        variation.get("motion_intensity")
        or lane_blocks.get("motion_intensity")
        or "composed"
    )
    image_treatment = str(
        variation.get("image_treatment")
        or lane_blocks.get("image_treatment")
        or "clean"
    )
    layout_mode = str(
        variation.get("layout_mode") or lane_blocks.get("layout_mode") or ""
    ).strip().lower()
    if layout_mode not in {"symmetric", "asymmetric", "organic"}:
        if (
            aesthetic_mode in {"impact", "technical", "dynamic"}
            or hero_layout in {"asymmetric", "video", "fullbleed"}
            or container_strategy in {"edge_to_edge", "overlap"}
            or overlap_mode not in {"", "none"}
        ):
            layout_mode = "asymmetric"
        elif (
            aesthetic_mode in {"wellness", "premium"}
            or radius_mode in {"soft", "pill"}
            or spacing_density == "spacious"
        ):
            layout_mode = "organic"
        else:
            layout_mode = "symmetric"

    has_explicit_services = bool(variation.get("services_variant"))
    services_variant = str(
        variation.get("services_variant")
        or lane_blocks.get("services_variant")
        or "split_editorial"
    )
    if not has_explicit_services and surface_style in {"solid", "soft_tint"}:
        services_variant = "stacked_cards"
    if not has_explicit_services and proof_style == "card_marquee":
        services_variant = "stats_then_cards"

    faq_variant = str(
        variation.get("faq_variant") or lane_blocks.get("faq_variant") or "panel"
    )
    if section_order_style in {"conversion_first", "gallery_first"}:
        faq_variant = "inline"

    has_explicit_location = bool(variation.get("location_variant"))
    location_variant = str(
        variation.get("location_variant")
        or lane_blocks.get("location_variant")
        or "split_local"
    )
    if not has_explicit_location and (
        "academia" in segment.lower() or hero_layout in {"fullbleed", "video"}
    ):
        location_variant = "feature_local"

    motion_mix = (
        variation.get("motion_mix")
        if isinstance(variation.get("motion_mix"), list)
        else []
    )
    hero_variant = str(
        variation.get("hero_variant")
        or hero_layout
        or lane_blocks.get("hero_variant")
        or "split"
    )
    reviews_variant = str(
        variation.get("reviews_variant")
        or lane_blocks.get("reviews_variant")
        or proof_style
    )
    about_variant = str(
        variation.get("about_variant") or lane_blocks.get("about_variant") or ""
    )
    if not about_variant:
        if hero_variant in {"video", "fullbleed", "center"}:
            about_variant = "manifesto_split"
        elif hero_variant == "asymmetric" or services_variant == "stats_then_cards":
            about_variant = "proof_sidebar"
        elif services_variant == "split_editorial":
            about_variant = "manifesto_split"
        else:
            about_variant = "feature_grid"
    surface_style = str(
        variation.get("surface_style")
        or lane_blocks.get("surface_style")
        or surface_style
    )
    if anti_repetition_rule == "avoid_glass" and surface_style == "glass":
        surface_style = "solid" if services_variant == "split_editorial" else "outline"

    gallery_density = str(variation.get("gallery_density") or "")
    if not gallery_density:
        if reviews_variant == "editorial_case":
            gallery_density = "editorial_grid"
        elif reviews_variant == "card_marquee":
            gallery_density = "mosaic"
        elif hero_variant in {"video", "fullbleed"}:
            gallery_density = "cinematic_strip"
        else:
            gallery_density = "balanced_grid"

    cta_style = str(variation.get("cta_style") or "")
    if not cta_style:
        if hero_variant in {"video", "fullbleed"}:
            cta_style = "poster_band"
        elif reviews_variant == "card_marquee":
            cta_style = "split_card"
        elif services_variant == "split_editorial":
            cta_style = "minimal_inline"
        else:
            cta_style = "solid_panel"

    surface_mix = (
        variation.get("surface_mix")
        if isinstance(variation.get("surface_mix"), list)
        else []
    )
    if anti_repetition_rule == "avoid_glass":
        surface_mix = [item for item in surface_mix if item != "glass"]
    if not surface_mix and surface_style == "glass":
        surface_mix = ["solid", "outline", "soft_tint"]

    section_surface_map = variation.get("section_surface_map")
    if not isinstance(section_surface_map, dict):
        section_surface_map = {}

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
        "about_variant": about_variant,
        "reviews_variant": reviews_variant,
        "faq_variant": faq_variant,
        "location_variant": location_variant,
        "pricing_variant": pricing_variant,
        "stats_variant": stats_variant,
        "aesthetic_mode": aesthetic_mode,
        "spacing_density": spacing_density,
        "radius_mode": radius_mode,
        "container_strategy": container_strategy,
        "typography_scale": typography_scale,
        "heading_style": heading_style,
        "surface_depth": surface_depth,
        "overlap_mode": overlap_mode,
        "motion_intensity": motion_intensity,
        "image_treatment": image_treatment,
        "layout_mode": layout_mode,
        "surface_style": surface_style,
        "surface_mix": surface_mix,
        "section_surface_map": section_surface_map,
        "color_strategy": str(variation.get("color_strategy") or ""),
        "typography_mood": str(variation.get("typography_mood") or ""),
        "gallery_density": gallery_density,
        "cta_style": cta_style,
        "prompt_priority": str(variation.get("prompt_priority") or ""),
        "anti_repetition_rule": anti_repetition_rule,
        "motion_style": str(variation.get("motion_style") or ""),
        "motion_mix": motion_mix,
        "hero_text_side": str(variation.get("hero_text_side") or ""),
        "creative_concept": str(variation.get("creative_concept") or ""),
        "brand_archetype": str(variation.get("brand_archetype") or ""),
        "emotional_outcome": str(variation.get("emotional_outcome") or ""),
        "anti_identity": str(variation.get("anti_identity") or ""),
        "story_arc": str(variation.get("story_arc") or ""),
        "cinematic_direction": str(variation.get("cinematic_direction") or ""),
        "conversion_strategy": str(variation.get("conversion_strategy") or ""),
        "visual_metaphor": str(variation.get("visual_metaphor") or ""),
        "section_order_style": section_order_style,
        "visual_lane": lane.get("id") or visual_lane,
        "visual_lane_name": lane.get("name") or "",
    }
