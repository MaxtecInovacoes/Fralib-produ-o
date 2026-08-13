"""Deterministic post-PRD build plan for the Skill Renderer.

The DesignerPRD is the factual/creative brief. SiteBuildPlan is the execution
plan that decides information architecture, section roles, media policy,
style guide, motion and SEO before HTML is generated.
"""

from __future__ import annotations

from typing import Any

from backend.agents.builder_contract_utils import (
    archetype_id_from_visual_dna as _archetype_id,
    first_value as _first,
    list_value as _list,
)

try:
    from component_library import build_component_contracts
except Exception:  # pragma: no cover - package import variant
    from agents.component_library import build_component_contracts


def build_site_build_plan(facts: dict[str, Any]) -> dict[str, Any]:
    """Create an actionable build plan without inventing business facts."""
    name = _first(facts, "business_name", "nome", default="Negócio local")
    segment = _first(facts, "segmento", "nicho", default="negócio local")
    city = _first(facts, "cidade", "city", default="")
    address = _first(facts, "address", "endereco", default="")
    phone = _first(facts, "phone", "telefone", default="")
    photos = _list(_first(facts, "photos", "fotos", default=[]))[:8]
    services = _list(_first(facts, "services", "servicos", default=[]))[:8]
    reviews = _list(_first(facts, "reviews", "reviews_list", default=[]))[:4]
    visual_dna = facts.get("visual_dna") if isinstance(facts.get("visual_dna"), dict) else {}
    visual_contract = facts.get("visual_contract") if isinstance(facts.get("visual_contract"), dict) else {}
    requirements = facts.get("requirements_contract") if isinstance(facts.get("requirements_contract"), dict) else {}
    reference_pack = (
        facts.get("design_reference_pack")
        if isinstance(facts.get("design_reference_pack"), dict)
        else visual_dna.get("design_reference_pack", {})
    )
    variation = facts.get("variation_blueprint") if isinstance(facts.get("variation_blueprint"), dict) else {}
    upstream_media_plan = facts.get("media_plan") if isinstance(facts.get("media_plan"), list) else []
    archetype = _archetype_id(visual_dna) or str(visual_contract.get("archetype") or "TRUST_ELITE").upper()
    tokens = (
        facts.get("color_palette")
        if isinstance(facts.get("color_palette"), dict)
        else visual_dna.get("tokens", {})
    ) or {}
    typography = (
        facts.get("typography")
        if isinstance(facts.get("typography"), dict)
        else visual_dna.get("typography", {})
    ) or {}

    section_order = _authoritative_section_order(variation, bool(services), bool(reviews), bool(address))
    primary_goal = requirements.get("primary_conversion_goal") or ("whatsapp" if phone else "map_or_contact")
    component_contracts = build_component_contracts({**facts, "visual_dna": visual_dna})
    return {
        "version": 1,
        "purpose": "plano pos-PRD para transformar briefing factual em HTML final",
        "component_contracts": component_contracts,
        "business_context": {
            "name": name,
            "segment": segment,
            "city": city,
            "primary_conversion_goal": primary_goal,
        },
        "information_architecture": {
            "section_order": section_order,
            "section_order_source": "variation_blueprint" if variation.get("ordem_das_secoes") else "site_build_plan_fallback",
            "navigation_targets": [item for item in section_order if item not in {"trust_bar"}],
            "must_combine": ["location", "contact"],
            "must_not_duplicate": ["map", "location", "footer", "post_footer_gallery"],
        },
        "section_plan": _section_plan(section_order, has_services=bool(services), has_reviews=bool(reviews), has_address=bool(address)),
        "style_guide": {
            "archetype": archetype,
            "reference_pack_id": reference_pack.get("id") if isinstance(reference_pack, dict) else "",
            "tokens": tokens,
            "typography": typography,
            "spacing": "use clamp-based section padding; mobile px-4, desktop max-width containers; no content touching viewport edges",
            "surfaces": "alternate hero, proof, editorial, decision, location and footer backgrounds using the archetype tokens",
            "media_ratio": "16:9",
        },
        "media_plan": {
            "items": upstream_media_plan,
            "available_count": len(photos),
            "hero": "use one dominant 16:9/depth media surface when available; otherwise use CSS/SVG depth",
            "gallery": "use up to 3 editorial images inside one media-story section",
            "policy": "media is editorial support unless data explicitly confirms it is real venue media",
            "map": "one Google Maps query embed from confirmed address; never broad OSM fallback",
        },
        "interaction_plan": {
            "hero": ["data-parallax", "ken-burns", "cta-hover-glow"],
            "sections": ["data-reveal", "card-stagger", "line-draw"],
            "fallback": "all content remains visible without JavaScript or motion runtime",
        },
        "content_rules": {
            "allowed_claims": (requirements.get("allowed_claims") or [])[:8],
            "forbidden_claims": (requirements.get("forbidden_claims") or [])[:8],
            "services_policy": "render confirmed services only; if missing, use decision/FAQ copy instead of fake service cards",
            "no_lorem": True,
        },
        "seo_plan": {
            "title_strategy": f"{name} em {city}".strip(),
            "local_terms": [item for item in [segment, city, address] if item],
            "schema_type": "LocalBusiness",
        },
        "acceptance_criteria": visual_contract.get("acceptance_criteria") or {},
    }


def _authoritative_section_order(variation: dict[str, Any], has_services: bool, has_reviews: bool, has_address: bool) -> list[str]:
    order = variation.get("ordem_das_secoes") if isinstance(variation, dict) else None
    if isinstance(order, list) and order:
        normalized = [str(item).strip().lower() for item in order if str(item).strip()]
        if "hero" not in normalized:
            normalized.insert(0, "hero")
        if "footer" not in normalized:
            normalized.append("footer")
        return list(dict.fromkeys(normalized))
    return _section_order(has_services, has_reviews, has_address)


def _section_order(has_services: bool, has_reviews: bool, has_address: bool) -> list[str]:
    order = [
        "hero",
        "trust_bar",
        "decision_content",
        "media_story",
        "about",
    ]
    if has_services:
        order.append("confirmed_services")
    if has_reviews:
        order.append("social_proof")
    order.append("faq")
    order.append("location_contact" if has_address else "contact")
    order.append("footer")
    return order


def _section_plan(order: list[str], *, has_services: bool, has_reviews: bool, has_address: bool) -> list[dict[str, Any]]:
    roles = {
        "hero": ("attention", ["headline", "subheadline", "primary_cta", "proof_chip", "motion_hook"]),
        "trust_bar": ("confidence", ["rating_or_city", "review_count_or_contact", "local_context"]),
        "decision_content": ("education", ["criteria_by_niche", "truthful_local_context"]),
        "media_story": ("visual_depth", ["editorial_media", "16_9_frames", "media_disclaimer_if_needed"]),
        "about": ("context", ["business_name", "city", "address_or_contact"]),
        "confirmed_services": ("offer", ["only_confirmed_services"]),
        "social_proof": ("validation", ["real_review_excerpts", "no_fake_testimonials"]),
        "faq": ("objection_handling", ["contact", "location", "what_to_confirm"]),
        "location_contact": ("conversion", ["single_google_map", "confirmed_address", "phone_or_whatsapp"]),
        "contact": ("conversion", ["phone_or_contact", "city_context"]),
        "footer": ("closure", ["brand", "navigation", "contact", "trust_note"]),
    }
    plan: list[dict[str, Any]] = []
    for section_id in order:
        role, required = roles.get(section_id, ("support", []))
        plan.append(
            {
                "id": section_id,
                "role": role,
                "required_content": required,
                "visual_surface": _surface_for(section_id),
                "validation": _validation_for(section_id, has_services, has_reviews, has_address),
            }
        )
    return plan


def _surface_for(section_id: str) -> str:
    if section_id == "hero":
        return "campaign viewport with depth layer, 16:9 media/decor and CTA microinteraction"
    if section_id in {"media_story", "location_contact"}:
        return "16:9 editorial/map frame inside responsive container"
    if section_id == "footer":
        return "complete footer using readable palette contrast"
    return "intentional archetype background with responsive spacing"


def _validation_for(section_id: str, has_services: bool, has_reviews: bool, has_address: bool) -> list[str]:
    checks = ["no_lorem", "no_horizontal_overflow", "readable_contrast"]
    if section_id == "confirmed_services" and has_services:
        checks.append("services_are_confirmed")
    if section_id == "social_proof" and has_reviews:
        checks.append("reviews_are_real")
    if section_id == "location_contact" and has_address:
        checks.extend(["single_map_only", "google_maps_query_embed"])
    if section_id == "footer":
        checks.extend(["not_after_footer_content", "navigation_contact_trust"])
    return checks
