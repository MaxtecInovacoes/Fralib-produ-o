"""Core PRD builder functions for pipeline orchestration.

This module contains the main PRD building functions that assemble
requirements, visual, and build contracts for the Builder renderer.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger("uvicorn")


def _contract_builders():
    """Factory function that imports and returns the contract builder functions.

    Handles both package and module import fallbacks for the contract builders.

    Returns:
        Tuple of (build_requirements_contract, build_visual_contract, build_site_build_plan).
    """
    try:
        from agents.requirements_contract import build_requirements_contract
        from agents.visual_contract import build_visual_contract
        from agents.site_build_plan import build_site_build_plan
    except Exception:  # pragma: no cover - package import variant
        from backend.agents.requirements_contract import build_requirements_contract
        from backend.agents.visual_contract import build_visual_contract
        from backend.agents.site_build_plan import build_site_build_plan
    return build_requirements_contract, build_visual_contract, build_site_build_plan


def build_skill_fast_prd(state: Any) -> SimpleNamespace:
    """Build the complete PRD namespace for the skill-based Builder fast path.

    This is the main PRD assembly function that combines lead data, design context,
    visual DNA, contracts, and section layouts into a single namespace for rendering.

    Args:
        state: Pipeline state containing lead_raw_data, lead_obj, and other attributes.

    Returns:
        SimpleNamespace with complete PRD data including:
        - business_name, segmento, cidade, address, phone
        - reviews, services, photos, og_image
        - subniche, neighborhood, seo_keywords
        - visual_direction, visual_dna
        - requirements_contract, visual_contract, site_build_plan
        - layout_blueprint, sections
        - instruction_criativa_para_dev
    """
    from backend.services.pipeline_validators import (
        derive_subniche,
        extract_neighborhood,
        build_local_keyword_terms,
        review_highlights_from_reviews,
    )
    from backend.services.pipeline_media import (
        deterministic_media_bundle,
        clean_public_text,
    )

    raw = getattr(state, "lead_raw_data", {}) or {}
    lead = getattr(getattr(state, "lead_obj", None), "lead", None)
    nome = getattr(state, "lead_nome", None) or raw.get("nome") or getattr(lead, "nome", "")
    segmento = getattr(state, "segmento", None) or raw.get("segmento") or getattr(lead, "segmento", "")
    cidade = getattr(state, "cidade", None) or raw.get("cidade") or getattr(lead, "cidade", "")
    endereco = clean_public_text(raw.get("endereco") or raw.get("address") or getattr(lead, "endereco", "") or cidade)
    telefone = raw.get("telefone") or raw.get("phone") or getattr(lead, "telefone", "")
    rating = raw.get("rating") or raw.get("avaliacao") or getattr(lead, "rating", 0) or 0
    reviews_count = (
        raw.get("reviews_count")
        or raw.get("total_avaliacoes")
        or getattr(lead, "reviews_count", 0)
        or 0
    )
    reviews = raw.get("reviews") or raw.get("_raw_reviews") or []
    horarios = raw.get("horarios") or raw.get("hours") or {}
    services = raw.get("servicos") or raw.get("services") or []
    neighborhood = extract_neighborhood(endereco)
    subniche = derive_subniche(
        segmento,
        services=services,
        reviews=reviews,
        keywords=getattr(state, "keyword_research", "") or "",
        business_name=nome,
    )
    photos, og_image = deterministic_media_bundle(
        segmento,
        raw.get("fotos") or raw.get("photos") or [],
        raw.get("og_image") or "",
    )
    keywords = getattr(state, "keyword_research", "") or ""
    seo_keywords = build_local_keyword_terms(
        name=nome,
        segment=segmento,
        city=cidade,
        neighborhood=neighborhood,
        subniche=subniche,
        services=services,
        raw_keywords=keywords,
    )
    try:
        from agents.design_context import get_design_context
        from agents.design_system_selector import select_design_system
        from core.design_system_router import build_design_dna, choose_section_variant
    except Exception:
        from design_context import get_design_context
        from design_system_selector import select_design_system
        from design_system_router import build_design_dna, choose_section_variant

    tier = (
        getattr(getattr(state, "qualificacao_caio", None), "tier", None)
        or raw.get("tier")
        or "STANDARD"
    )
    design_system_slug = ""
    try:
        design_system_slug = (select_design_system(segmento, nome, tier) or {}).get("slug", "")
    except Exception:
        design_system_slug = ""
    design = get_design_context(
        segmento,
        nome,
        tier,
        False,
        od_slug=design_system_slug,
        dados_lead=raw,
    ) or {}
    tokens = design.get("tokens") or {}
    font_heading = design.get("font_heading") or "Outfit"
    font_body = design.get("font_body") or "Outfit"
    lead_id = (
        raw.get("id")
        or getattr(lead, "id", "")
        or getattr(getattr(state, "lead_obj", None), "id", "")
        or getattr(state, "lead_id", "")
    )
    design_dna = build_design_dna(
        segmento=segmento,
        business_name=nome,
        lead_id=str(lead_id or nome),
        tier=tier,
        base_design=design,
        dados_lead=raw,
    )
    visual_seed = design_dna["visual_seed"]
    archetype = design_dna["archetype"]
    dna_tokens = design_dna.get("tokens") or tokens
    font_heading = design_dna.get("font_heading") or font_heading
    font_body = design_dna.get("font_body") or font_body
    visual_direction = {
        "design_system": design_system_slug or design.get("direction") or "local-editorial",
        "direction": design.get("direction") or "",
        "vibe": design.get("vibe") or "",
        "tokens": dna_tokens,
        "font_heading": font_heading,
        "font_body": font_body,
        "archetype": archetype["archetype"],
        "visual_seed": visual_seed,
        "dna_combo": design_dna["dna_combo"],
        "design_reference_pack_id": (design_dna.get("design_reference_pack") or {}).get("id"),
        "footer_policy": "Footer deve continuar a paleta do site; usar fechamento escuro somente se os tokens forem dark.",
        "media_policy": "Fotos fornecidas sao mídia editorial/stock aprovada para narrativa visual; nao chamar de foto real do espaco.",
        "subniche_policy": (
            f"Subnicho confirmado: {subniche}. Toda copy, galeria, prova social e CTA devem permanecer nesse recorte."
            if subniche
            else f"Segmento confirmado: {segmento}. Evitar vocabulário de subnichos não confirmados."
        ),
        "composition": [
            "Hero experience-led com parallax/Ken Burns, imagem/forma dominante, CTA e proof chip no primeiro viewport.",
            "Alternar bloco aberto, prova social densa, bloco visual, conteudo de decisao, FAQ e contato.",
            "Evitar card solto ocupando metade da linha; quando houver poucos itens, usar spotlight/bento assimetrico.",
            "Cada secao deve ter fundo intencional: surface, mesh, faixa saturada, textura ou bloco editorial.",
        ],
    }
    visual_dna = {
        "archetype": archetype["archetype"],
        "visual_voice": archetype["visual_voice"],
        "color_theory": archetype["color_theory"],
        "visual_seed": visual_seed,
        "dna_combo": design_dna["dna_combo"],
        "style_mix_instruction": design_dna["style_mix_instruction"],
        "reference_vibes": design_dna["reference_vibes"],
        "design_reference_pack": design_dna.get("design_reference_pack") or {},
        "variation": design_dna["variation"],
        "tokens": dna_tokens,
        "palette_id": design_dna.get("palette_id"),
        "color_strategy": design_dna.get("color_strategy"),
        "palette_contrast": design_dna.get("palette_contrast") or {},
        "typography": {
            "heading": font_heading,
            "body": font_body,
            **archetype.get("typography", {}),
        },
        "composition_laws": archetype["composition_laws"],
        "creative_director_protocol": {
            "impact_hierarchy": "Headlines display 72px+ desktop, weight 900 quando combinar com o arquetipo.",
            "depth": "Usar z-index, sobreposicoes, negative margins e camadas visuais.",
            "background": "Nao depender de fundo branco plano; usar textura, mesh, imagem ou bloco disruptivo.",
            "rhythm": "Alternar full-bleed, leitura estreita e grid assimetrico.",
            "cta": archetype["cta_policy"],
            "decor": "Usar grafismos abstratos, marcas dagua discretas, linhas ou blur conforme o DNA.",
        },
    }
    review_highlights = review_highlights_from_reviews(reviews)

    def _variant(name: str) -> str:
        return choose_section_variant(name, visual_seed, archetype["archetype"])

    sections = [
        {
            "name": "hero",
            "layout_type": _variant("hero"),
            "title": f"{nome} em {cidade}".strip(),
            "copy": {
                "body": "Apresente a proposta real do negocio com impacto visual, foto editorial se disponivel, parallax/Ken Burns, CTA direto e proof chip factual."
            },
            "media_role": "hero/editorial",
        },
        {
            "name": "trust-bar",
            "layout_type": _variant("trust-bar"),
            "title": "Sinais reais",
            "items": [
                {"label": "Avaliação", "value": rating},
                {"label": "Depoimentos", "value": reviews_count},
                {"label": "Cidade", "value": cidade},
            ],
        },
        {
            "name": "sobre",
            "layout_type": _variant("sobre"),
            "title": f"Sobre {nome}".strip(),
            "copy": {
                "body": "Use endereco, avaliacao e sinais reais. Nao invente equipe, estrutura, especialidades ou promessas."
            },
            "media_role": "supporting/editorial",
        },
        {
            "name": "conteudo-decisao",
            "layout_type": _variant("conteudo-decisao"),
            "title": "O que observar antes de escolher",
            "copy": {
                "body": "Crie uma secao educativa e comercial com criterios de decisao ligados ao nicho, sem inventar servicos. Use fatos reais como cidade, contato, avaliacao e endereco."
            },
        },
        {
            "name": "experiencia-visual",
            "layout_type": _variant("experiencia-visual"),
            "title": "Presenca visual do atendimento",
            "copy": {
                "body": "Use imagens editoriais do nicho como narrativa: detalhe, textura, produto/contexto e ritmo. Nao afirmar que sao fotos reais do local."
            },
            "media_role": "editorial/gallery",
        },
    ]
    if review_highlights:
        sections.append(
            {
                "name": "diferenciais",
                "layout_type": _variant("diferenciais"),
                "title": "O que os pacientes destacam",
                "items": review_highlights,
            }
        )
    if services:
        sections.append(
            {
                "name": "servicos",
                "layout_type": _variant("servicos"),
                "title": "Atendimentos confirmados",
                "items": services[:6],
            }
        )
    sections.extend(
        [
            {
                "name": "depoimentos",
                "layout_type": _variant("depoimentos"),
                "title": "Depoimentos reais",
                "items": reviews[:4] if isinstance(reviews, list) else [],
            },
            {
                "name": "faq",
                "layout_type": _variant("faq"),
                "title": "Perguntas antes do contato",
                "copy": {
                    "body": "Responda objeções comuns do nicho usando apenas dados confirmados: como falar, onde fica, o que confirmar pelo WhatsApp e como planejar a visita."
                },
            },
            {
                "name": "localizacao",
                "layout_type": _variant("localizacao"),
                "title": "Localização e horários",
                "copy": {"body": "Mostre endereço completo, horários e mapa quando disponível."},
            },
            {
                "name": "contato",
                "layout_type": _variant("contato"),
                "title": "Contato",
                "copy": {"body": "Mostre telefone, endereço completo e chamada para WhatsApp."},
            },
            {"name": "footer", "layout_type": _variant("footer"), "title": nome},
        ]
    )
    layout_blueprint = [
        {
            "section": section.get("name"),
            "variant": section.get("layout_type"),
            "reason": f"visual_seed={visual_seed}; archetype={archetype['archetype']}",
        }
        for section in sections
    ]
    contract_facts = {
        "business_name": nome,
        "segmento": segmento,
        "subniche": subniche,
        "cidade": cidade,
        "neighborhood": neighborhood,
        "address": endereco,
        "phone": telefone,
        "rating": rating,
        "reviews_count": reviews_count,
        "reviews": reviews,
        "hours": horarios,
        "services": services,
        "photos": photos,
        "og_image": og_image,
        "seo_keywords": seo_keywords,
        "visual_dna": visual_dna,
    }
    build_requirements_contract, build_visual_contract, build_site_build_plan = _contract_builders()
    requirements_contract = build_requirements_contract(contract_facts)
    visual_contract = build_visual_contract(contract_facts)
    site_build_plan = build_site_build_plan(
        {
            **contract_facts,
            "requirements_contract": requirements_contract,
            "visual_contract": visual_contract,
            "design_reference_pack": design_dna.get("design_reference_pack") or {},
            "layout_blueprint": layout_blueprint,
            "color_palette": dna_tokens,
            "typography": {"heading": font_heading, "body": font_body},
        }
    )
    return SimpleNamespace(
        business_name=nome,
        nome=nome,
        segmento=segmento,
        cidade=cidade,
        address=endereco,
        endereco=endereco,
        phone=telefone,
        telefone=telefone,
        reviews_rating=rating,
        rating=rating,
        reviews_count=reviews_count,
        total_avaliacoes=reviews_count,
        reviews=reviews,
        reviews_list=reviews,
        subniche=subniche,
        neighborhood=neighborhood,
        hours=horarios,
        horarios=horarios,
        servicos=services,
        services=services,
        visual_direction=visual_direction,
        visual_dna=visual_dna,
        requirements_contract=requirements_contract,
        visual_contract=visual_contract,
        site_build_plan=site_build_plan,
        layout_blueprint=layout_blueprint,
        dna_combo=design_dna["dna_combo"],
        design_reference_pack=design_dna.get("design_reference_pack") or {},
        visual_seed=visual_seed,
        color_palette=dna_tokens,
        typography={"heading": font_heading, "body": font_body},
        layout_type="editorial",
        instrucao_criativa_para_dev=(
            f"BRAND DNA: {nome} deve parecer confiavel, local e memoravel em {cidade}. "
            f"Arquetipo {archetype['archetype']}: {archetype['visual_voice']}. "
            f"DNA Mixer: {design_dna['style_mix_instruction']} "
            "COMPOSICAO: hero com imagem/forma dominante, secoes com ritmo variado, prova social real e fechamento coerente. "
            "CREATIVE DIRECTOR: tipografia display, profundidade, camadas, uma secao disruptiva e CTA com acento raro. "
            "ANTI-PATTERNS: sem hero centralizado generico, sem cards repetidos, sem footer preto fora da paleta, sem servicos inventados."
        ),
        seo_keywords=seo_keywords,
        keywords=seo_keywords,
        jina_insights=str(getattr(state, "jina_insights", "") or "")[:2500],
        google_maps_embed=raw.get("google_maps_embed", ""),
        renderer_owns_headings=True,
        heading_preservation_min=1,
        photos=photos,
        og_image=og_image,
        sections=sections,
    )


def ensure_prd_design_reference(prd: Any, state: Any) -> str:
    """Attach current curated design reference pack to any PRD before rendering.

    Computes design DNA, visual direction, and layout blueprint for the PRD
    and attaches them as attributes. Returns the design reference pack ID.

    Args:
        prd: The PRD object to enhance with design reference.
        state: Pipeline state containing lead data and configuration.

    Returns:
        The design reference pack ID string.
    """
    from backend.services.pipeline_validators import (
        derive_subniche,
        extract_neighborhood,
        build_local_keyword_terms,
    )
    from backend.services.pipeline_media import deterministic_media_bundle

    if not prd:
        return ""
    raw = getattr(state, "lead_raw_data", {}) or {}
    nome = (
        getattr(prd, "business_name", None)
        or getattr(prd, "nome", None)
        or raw.get("nome")
        or getattr(state, "lead_nome", "")
    )
    segmento = (
        getattr(prd, "segmento", None)
        or getattr(state, "segmento", None)
        or raw.get("segmento")
        or "negocio local"
    )
    tier = (
        getattr(getattr(state, "qualificacao_caio", None), "tier", None)
        or raw.get("tier")
        or "STANDARD"
    )
    lead_id = (
        raw.get("id")
        or getattr(getattr(state, "lead_obj", None), "id", "")
        or getattr(state, "lead_id", "")
        or nome
    )
    try:
        from agents.design_context import get_design_context
        from agents.design_system_selector import select_design_system
        from core.design_system_router import build_design_dna, choose_section_variant
    except Exception:
        from design_context import get_design_context
        from design_system_selector import select_design_system
        from design_system_router import build_design_dna, choose_section_variant

    try:
        design_system_slug = (select_design_system(segmento, nome, tier) or {}).get("slug", "")
    except Exception:
        design_system_slug = ""
    design = get_design_context(segmento, nome, tier, False, od_slug=design_system_slug, dados_lead=raw) or {}
    design_dna = build_design_dna(
        segmento=segmento,
        business_name=nome,
        lead_id=str(lead_id),
        tier=tier,
        base_design=design,
        dados_lead=raw,
    )
    archetype = design_dna["archetype"]
    visual_seed = design_dna["visual_seed"]
    tokens = design_dna.get("tokens") or design.get("tokens") or {}
    font_heading = design_dna.get("font_heading") or design.get("font_heading") or "Outfit"
    font_body = design_dna.get("font_body") or design.get("font_body") or "Outfit"
    visual_dna = {
        "archetype": archetype["archetype"],
        "visual_voice": archetype["visual_voice"],
        "color_theory": archetype["color_theory"],
        "visual_seed": visual_seed,
        "dna_combo": design_dna["dna_combo"],
        "style_mix_instruction": design_dna["style_mix_instruction"],
        "reference_vibes": design_dna["reference_vibes"],
        "design_reference_pack": design_dna.get("design_reference_pack") or {},
        "variation": design_dna["variation"],
        "tokens": tokens,
        "palette_id": design_dna.get("palette_id"),
        "color_strategy": design_dna.get("color_strategy"),
        "palette_contrast": design_dna.get("palette_contrast") or {},
        "typography": {"heading": font_heading, "body": font_body, **archetype.get("typography", {})},
        "composition_laws": archetype["composition_laws"],
        "creative_director_protocol": {
            "impact_hierarchy": "Headlines display 72px+ desktop quando combinar com o arquetipo.",
            "depth": "Usar z-index, sobreposicoes, negative margins e camadas visuais.",
            "background": "Nao depender de fundo branco plano; usar textura, mesh, imagem ou bloco disruptivo.",
            "rhythm": "Alternar full-bleed, leitura estreita e grid assimetrico.",
            "cta": archetype["cta_policy"],
        },
    }
    sections = getattr(prd, "sections", []) or []
    layout_blueprint = []
    for section in sections:
        name = (
            getattr(section, "name", None)
            if not isinstance(section, dict)
            else section.get("name")
        ) or ""
        layout = (
            getattr(section, "layout_type", None)
            if not isinstance(section, dict)
            else section.get("layout_type")
        )
        if name:
            layout_blueprint.append(
                {
                    "section": name,
                    "variant": layout or choose_section_variant(name, visual_seed, archetype["archetype"]),
                    "reason": f"visual_seed={visual_seed}; reference_pack={(design_dna.get('design_reference_pack') or {}).get('id', '')}",
                }
            )
    setattr(prd, "visual_dna", visual_dna)
    setattr(prd, "visual_direction", {
        "design_system": design_system_slug or design.get("direction") or "local-editorial",
        "direction": design.get("direction") or "",
        "vibe": design.get("vibe") or "",
        "tokens": tokens,
        "font_heading": font_heading,
        "font_body": font_body,
        "archetype": archetype["archetype"],
        "visual_seed": visual_seed,
        "dna_combo": design_dna["dna_combo"],
        "design_reference_pack_id": (design_dna.get("design_reference_pack") or {}).get("id"),
    })
    setattr(prd, "layout_blueprint", layout_blueprint)
    setattr(prd, "dna_combo", design_dna["dna_combo"])
    setattr(prd, "design_reference_pack", design_dna.get("design_reference_pack") or {})
    setattr(prd, "visual_seed", visual_seed)
    setattr(prd, "typography", {"heading": font_heading, "body": font_body})
    current_palette = getattr(prd, "color_palette", None)
    if isinstance(current_palette, dict):
        current_palette.update(tokens)
    return (design_dna.get("design_reference_pack") or {}).get("id", "")


def ensure_prd_contracts(prd: Any, state: Any) -> None:
    """Ensure PRD has all required contracts attached.

    Computes and attaches subniche, neighborhood, SEO keywords, media,
    and the three required contracts (requirements, visual, site build plan)
    if they are not already present on the PRD.

    Args:
        prd: The PRD object to ensure contracts for.
        state: Pipeline state containing lead data.
    """
    from backend.services.pipeline_validators import (
        derive_subniche,
        extract_neighborhood,
        build_local_keyword_terms,
    )
    from backend.services.pipeline_media import deterministic_media_bundle

    raw_data = getattr(state, "lead_raw_data", {}) or {}
    segment = getattr(prd, "segmento", None) or getattr(state, "segmento", "")
    address = getattr(prd, "address", None) or getattr(prd, "endereco", None) or raw_data.get("endereco", "")
    city = getattr(prd, "cidade", None) or getattr(getattr(state, "lead_obj", None), "cidade", "")
    services = getattr(prd, "services", None) or getattr(prd, "servicos", None) or []
    reviews = getattr(prd, "reviews", None) or getattr(prd, "reviews_list", None) or []
    keyword_seed = getattr(prd, "seo_keywords", None) or getattr(prd, "keywords", None) or getattr(state, "keyword_research", "") or ""
    subniche = getattr(prd, "subniche", None) or derive_subniche(
        segment,
        services=services,
        reviews=reviews,
        keywords=keyword_seed,
        business_name=getattr(prd, "business_name", None) or getattr(prd, "nome", None) or getattr(state, "lead_nome", ""),
    )
    neighborhood = getattr(prd, "neighborhood", None) or extract_neighborhood(address)
    normalized_photos, og_image = deterministic_media_bundle(
        segment,
        getattr(prd, "photos", None) or raw_data.get("fotos", []),
        getattr(prd, "og_image", None) or raw_data.get("og_image", ""),
    )
    setattr(prd, "photos", normalized_photos)
    setattr(prd, "og_image", og_image)
    setattr(prd, "subniche", subniche)
    setattr(prd, "neighborhood", neighborhood)
    local_keywords = build_local_keyword_terms(
        name=getattr(prd, "business_name", None) or getattr(prd, "nome", None) or getattr(state, "lead_nome", ""),
        segment=segment,
        city=city,
        neighborhood=neighborhood,
        subniche=subniche,
        services=services,
        raw_keywords=keyword_seed,
    )
    setattr(prd, "seo_keywords", local_keywords)
    setattr(prd, "keywords", local_keywords)
    facts = {
        "business_name": getattr(prd, "business_name", None)
        or getattr(prd, "nome", None)
        or getattr(state, "lead_nome", ""),
        "segmento": getattr(prd, "segmento", None) or getattr(state, "segmento", ""),
        "subniche": subniche,
        "cidade": city,
        "neighborhood": neighborhood,
        "address": address,
        "phone": getattr(prd, "phone", None)
        or getattr(prd, "telefone", None)
        or (getattr(state, "lead_raw_data", {}) or {}).get("telefone", ""),
        "rating": getattr(prd, "rating", None) or getattr(prd, "reviews_rating", None),
        "reviews_count": getattr(prd, "reviews_count", None) or getattr(prd, "total_avaliacoes", None),
        "reviews": reviews,
        "hours": getattr(prd, "hours", None) or getattr(prd, "horarios", None) or {},
        "services": services,
        "photos": normalized_photos,
        "og_image": og_image,
        "seo_keywords": local_keywords,
        "visual_dna": getattr(prd, "visual_dna", {}) or {},
        "design_reference_pack": getattr(prd, "design_reference_pack", {}) or {},
        "layout_blueprint": getattr(prd, "layout_blueprint", []) or [],
        "color_palette": getattr(prd, "color_palette", {}) or {},
        "typography": getattr(prd, "typography", {}) or {},
    }
    build_requirements_contract, build_visual_contract, build_site_build_plan = _contract_builders()
    if not getattr(prd, "requirements_contract", None):
        setattr(prd, "requirements_contract", build_requirements_contract(facts))
    if not getattr(prd, "visual_contract", None):
        setattr(prd, "visual_contract", build_visual_contract(facts))
    if not getattr(prd, "site_build_plan", None):
        setattr(
            prd,
            "site_build_plan",
            build_site_build_plan(
                {
                    **facts,
                    "requirements_contract": getattr(prd, "requirements_contract", {}) or {},
                    "visual_contract": getattr(prd, "visual_contract", {}) or {},
                }
            ),
        )


def ensure_prd_publication_identity(prd: Any, state: Any, tenant_id: int) -> None:
    """Attach the final multi-tenant URL before the renderer builds SEO metadata.

    Sets site_url, canonical_url, and related publication metadata on the PRD
    based on the lead slug and tenant ID.

    Args:
        prd: The PRD object (SimpleNamespace or dict) to attach publication identity.
        state: Pipeline state containing lead_slug.
        tenant_id: The tenant ID for URL construction.
    """
    slug = getattr(state, "lead_slug", "") or getattr(prd, "site_slug", "")
    if not slug:
        return
    site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{slug}/"
    if isinstance(prd, dict):
        business = prd.setdefault("business", {}) if isinstance(prd.get("business"), dict) else prd.setdefault("business", {})
        seo = prd.setdefault("seo", {}) if isinstance(prd.get("seo"), dict) else prd.setdefault("seo", {})
        publication = prd.setdefault("publication", {}) if isinstance(prd.get("publication"), dict) else prd.setdefault("publication", {})
        business["tenant_id"] = tenant_id
        business["site_slug"] = slug
        business["site_url"] = site_url
        business["canonical_url"] = site_url
        if prd.get("og_image"):
            business.setdefault("og_image", prd.get("og_image"))
            seo.setdefault("og_image", prd.get("og_image"))
            publication.setdefault("og_image", prd.get("og_image"))
        if prd.get("seo_keywords"):
            seo["primary_terms"] = list(prd.get("seo_keywords") or [])
        prd["tenant_id"] = tenant_id
        prd["site_slug"] = slug
        prd["site_url"] = site_url
        prd["canonical_url"] = site_url
        publication["site_url"] = site_url
        publication["canonical_url"] = site_url
        seo["site_url"] = site_url
        seo["canonical_url"] = site_url
        return
    setattr(prd, "tenant_id", tenant_id)
    setattr(prd, "site_slug", slug)
    setattr(prd, "site_url", site_url)
    setattr(prd, "canonical_url", site_url)
