"""Prompt agent PRD builder function for pipeline orchestration.

This module contains the build_prompt_agent_prd function that creates
a prompt-only payload for the temporary native Builder flow.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger("uvicorn")


def build_prompt_agent_prd(state: Any, tenant_id: int | str = "") -> SimpleNamespace:
    """Build the prompt-only payload used by the temporary native Builder flow.

    This function assembles a PRD namespace containing all the context needed
    for the prompt-based Builder renderer, including design context, visual DNA,
    SEO keywords, and media assets.

    Args:
        state: Pipeline state containing lead data, design context, and intelligence.
        tenant_id: Optional tenant ID for multi-tenant context.

    Returns:
        SimpleNamespace with prompt payload including:
        - contract: "fralib-prompt-agent-v1"
        - prompt_agent_payload: Full payload for prompt agent
        - builder_prompt: Generated builder prompt string
        - business_name, nome, segmento, cidade, address
        - phone, telefone, photos, videos, og_image, logo_url
        - subniche, neighborhood
        - visual_direction, visual_dna
        - seo_keywords, keywords, keyword_research, jina_insights
        - google_maps_embed, sections
        - renderer_owns_headings, heading_preservation_min
    """
    from backend.services.pipeline_validators import (
        derive_subniche,
        extract_neighborhood,
        build_local_keyword_terms,
        object_to_dict,
    )
    from backend.services.pipeline_media import deterministic_media_bundle

    raw = dict(getattr(state, "lead_raw_data", {}) or {})
    lead = getattr(getattr(state, "lead_obj", None), "lead", None)
    nome = getattr(state, "lead_nome", None) or raw.get("nome") or getattr(lead, "nome", "")
    segmento = (
        getattr(state, "segmento", None)
        or raw.get("segmento")
        or getattr(lead, "segmento", "")
        or "negocio local"
    )
    cidade = (
        getattr(state, "cidade", None)
        or raw.get("cidade")
        or getattr(lead, "cidade", "")
        or ""
    )
    tier = (
        getattr(getattr(state, "qualificacao_caio", None), "tier", None)
        or raw.get("tier")
        or "STANDARD"
    )
    visual_direction: dict[str, Any] = {}
    visual_dna: dict[str, Any] = {}
    try:
        try:
            from agents.design_context import get_design_context
            from agents.design_system_selector import select_design_system
            from core.design_system_router import build_design_dna
        except Exception:
            from design_context import get_design_context
            from design_system_selector import select_design_system
            from design_system_router import build_design_dna

        design_system_slug = (
            select_design_system(segmento, nome, tier) or {}
        ).get("slug", "")
        design = get_design_context(
            segmento,
            nome,
            tier,
            False,
            od_slug=design_system_slug,
            dados_lead=raw,
        ) or {}
        design_dna = build_design_dna(
            segmento=segmento,
            business_name=nome,
            lead_id=str(getattr(getattr(state, "lead_obj", None), "id", "") or nome),
            tier=tier,
            base_design=design,
            dados_lead=raw,
        )
        archetype = design_dna.get("archetype") or {}
        visual_direction = {
            "design_system": design_system_slug or design.get("direction") or "",
            "direction": design.get("direction") or "",
            "vibe": design.get("vibe") or "",
            "tokens": design_dna.get("tokens") or design.get("tokens") or {},
            "font_heading": design_dna.get("font_heading") or design.get("font_heading") or "",
            "font_body": design_dna.get("font_body") or design.get("font_body") or "",
            "composition": [
                "Hero forte no primeiro viewport.",
                "Ritmo visual variado entre secoes densas e abertas.",
                "CTA comercial claro e fechamento coerente.",
            ],
        }
        visual_dna = {
            "archetype": archetype.get("archetype") or "",
            "visual_voice": archetype.get("visual_voice") or "",
            "style_mix_instruction": design_dna.get("style_mix_instruction") or "",
            "reference_vibes": design_dna.get("reference_vibes") or [],
            "tokens": visual_direction.get("tokens") or {},
            "typography": {
                "heading": visual_direction.get("font_heading") or "",
                "body": visual_direction.get("font_body") or "",
            },
        }
    except Exception as exc:
        logger.warning(f"[PromptAgent] design context skip: {exc}")

    try:
        from agents.site_prompt_agent import build_prompt_agent_payload
    except Exception:
        from site_prompt_agent import build_prompt_agent_payload

    prompt_source = {
        "tenant_id": tenant_id,
        "pipeline_id": getattr(state, "pipeline_id", ""),
        "lead": {
            **raw,
            "nome": nome,
            "segmento": segmento,
            "cidade": cidade,
        },
        "caio": object_to_dict(getattr(state, "qualificacao_caio", None)),
        "jina_market_intelligence": object_to_dict(getattr(state, "jina_intel_dict", None)),
        "jina_insights": getattr(state, "jina_insights", "") or "",
        "keyword_research": getattr(state, "keyword_research", "") or "",
        "briefing_theo": getattr(state, "briefing_theo", "") or "",
        "nicho_briefing": object_to_dict(getattr(state, "nicho_briefing", None)),
        "variacao_estrutural": object_to_dict(getattr(state, "variacao_estrutural", None)),
        "visual_direction": visual_direction,
        "visual_dna": visual_dna,
    }
    payload = build_prompt_agent_payload(prompt_source)
    context = payload.get("context") or {}
    business = context.get("business") or {}
    media = context.get("media") or {}
    address = business.get("address") or raw.get("endereco") or ""
    services = (context.get("services") or raw.get("servicos") or raw.get("services") or [])
    reviews = raw.get("reviews") or raw.get("_raw_reviews") or []
    subniche = derive_subniche(
        business.get("segment") or segmento,
        services=services,
        reviews=reviews,
        keywords=(context.get("seo") or {}).get("primary_terms") or getattr(state, "keyword_research", "") or "",
        business_name=business.get("name") or nome,
    )
    neighborhood = extract_neighborhood(address)
    seo_keywords = build_local_keyword_terms(
        name=business.get("name") or nome,
        segment=business.get("segment") or segmento,
        city=business.get("city") or cidade,
        neighborhood=neighborhood,
        subniche=subniche,
        services=services,
        raw_keywords=(context.get("seo") or {}).get("primary_terms") or getattr(state, "keyword_research", "") or "",
    )
    photos, og_image = deterministic_media_bundle(
        segmento,
        media.get("photos") or raw.get("fotos") or [],
        media.get("og_image") or raw.get("og_image") or "",
    )
    # Sprint 16: extrair variation seed de variacao_estrutural para passar ao builder
    _var_estrutural = object_to_dict(getattr(state, "variacao_estrutural", None)) or {}
    _variation = _var_estrutural.get("variation") or {}
    return SimpleNamespace(
        contract="fralib-prompt-agent-v1",
        prompt_agent_payload=payload,
        builder_prompt=payload.get("builder_prompt", ""),
        business_name=business.get("name") or nome,
        nome=business.get("name") or nome,
        segmento=business.get("segment") or segmento,
        cidade=business.get("city") or cidade,
        address=address,
        endereco=address,
        phone=business.get("phone") or raw.get("telefone") or "",
        telefone=business.get("phone") or raw.get("telefone") or "",
        photos=photos,
        videos=media.get("videos") or raw.get("videos") or [],
        og_image=og_image,
        logo_url=media.get("logo_url") or raw.get("logo_url") or "",
        subniche=subniche,
        neighborhood=neighborhood,
        visual_direction=visual_direction,
        visual_dna=visual_dna,
        seo_keywords=seo_keywords,
        keywords=seo_keywords,
        keyword_research=getattr(state, "keyword_research", "") or "",
        jina_insights=getattr(state, "jina_insights", "") or "",
        google_maps_embed=raw.get("google_maps_embed", ""),
        sections=context.get("sections") or [],
        renderer_owns_headings=True,
        heading_preservation_min=0,
        # Sprint 16: variation seed completo para o builder usar
        variation=_variation,
    )
