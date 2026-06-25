"""Prompt Agent context builders: business, qualification, research, SEO, content, media, design, publication."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.prompt_agent_helpers import (
    _as_list,
    _clean_dict,
    _compact,
    _dict,
    _dump_compact,
    _extract_keyword_candidates,
    _first,
    _ideal_customer_context,
    _infer_prompt_archetype,
    _infer_subniche,
    _market_intelligence_context,
    _media_urls,
    _normalize,
    _normalize_target,
    _sanitize_primary_term,
    _section_name,
)

_VALID_TARGETS = {"landing-page", "institutional-site", "app", "crm"}


def _business_context(lead: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    segment = _first(lead, facts, "segmento", "segment", "nicho", default="negócio local")
    # Sprint 12.16: also try nested business.name (when PRD has business={name:...})
    _biz = (lead.get("business") if isinstance(lead.get("business"), dict) else
            facts.get("business") if isinstance(facts.get("business"), dict) else {})
    _biz_name = (_biz.get("name") or _biz.get("business_name") or _biz.get("nome")) if _biz else ""
    return _clean_dict(
        {
            "name": _first(lead, facts, "nome", "business_name", "name", default="Negócio local") or _biz_name,
            "segment": segment,
            "subniche": _first(lead, facts, "subnicho", "subniche", default=_infer_subniche(segment)),
            "city": _first(lead, facts, "cidade", "city", default=""),
            "service_region": _first(lead, facts, "regiao_atendimento", "service_region", "area_atendida", default=""),
            "address": _first(lead, facts, "endereco", "address", default=""),
            "phone": _first(lead, facts, "telefone", "phone", default=""),
            "whatsapp": _first(lead, facts, "whatsapp", default=""),
            "email": _first(lead, facts, "email", "e_mail", default=""),
            "website": _first(lead, facts, "website", "site", default=""),
            "socials": _as_list(_first(lead, facts, "redes_sociais", "socials", "instagram", "facebook", default=[])),
            "rating": _first(lead, facts, "rating", "reviews_rating", default=""),
            "reviews_count": _first(lead, facts, "total_avaliacoes", "reviews_count", default=""),
            "hours": _first(lead, facts, "horarios", "hours", default={}) or {},
            "price_range": _first(lead, facts, "faixa_preco", "price_range", default=""),
            "canonical_url": _first(lead, facts, "canonical_url", "site_url", "url_site", default=""),
        }
    )


def _qualification_context(caio: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    return _clean_dict(
        {
            "tier": _first(caio, facts, "tier", "caio_tier", default=""),
            "score": _first(caio, facts, "score", "caio_score", default=""),
            "decision": _first(caio, facts, "qualificacao", "qualificado", default=""),
            "reason": _first(caio, facts, "motivo", "caio_motivo", default=""),
        }
    )


def _research_context(facts: dict[str, Any]) -> dict[str, Any]:
    jina_source = _first(
        facts,
        {},
        "jina_market_intelligence",
        "jina_intel_dict",
        default={},
    )
    if not jina_source:
        jina_source = _first(facts, {}, "jina_insights", "market_intelligence", default="")
    return _clean_dict(
        {
            "jina_market_intelligence": _market_intelligence_context(jina_source),
            "keyword_research": _compact(_first(facts, {}, "keyword_research", default=""), 3500),
            "competitor_analysis": _compact(_first(facts, {}, "competitor_analysis", default=""), 2500),
            "niche_briefing": _dump_compact(_first(facts, {}, "nicho_briefing", default=""), 2200),
            "structural_variation": _dump_compact(_first(facts, {}, "variacao", "variacao_estrutural", default=""), 1600),
        }
    )


def _seo_context(facts: dict[str, Any]) -> dict[str, Any]:
    keywords = _as_list(_first(facts, {}, "seo_keywords", "keywords", default=[]))
    keyword_text = _first(facts, {}, "keyword_research", default="")
    if isinstance(keyword_text, str):
        keywords.extend(_extract_keyword_candidates(keyword_text))
    cleaned_terms = []
    for keyword in keywords:
        clean = _sanitize_primary_term(keyword)
        if clean:
            cleaned_terms.append(clean)
    return _clean_dict(
        {
            "primary_terms": list(dict.fromkeys(cleaned_terms))[:24],
            "local_focus": _first(facts, {}, "cidade", "city", default=""),
            "canonical_url": _first(facts, {}, "canonical_url", "site_url", "url_site", default=""),
            "search_intent_notes": _compact(str(keyword_text or ""), 2200),
        }
    )


def _content_context(lead: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    return _clean_dict(
        {
            "services": _as_list(_first(lead, facts, "servicos", "services", default=[]))[:16],
            "attributes": _as_list(_first(lead, facts, "atributos", "attributes", default=[]))[:16],
            "ideal_customer": _ideal_customer_context(lead, facts),
            "reviews": _as_list(_first(lead, facts, "reviews", "reviews_list", default=[]))[:8],
            "maps_embed": _compact(_first(lead, facts, "google_maps_embed", default=""), 1800),
            "maps_url": _compact(
                _first(lead, facts, "maps_url", "google_maps_url", "map_url", default=""),
                900,
            ),
            "raw_notes": _compact(_first(facts, {}, "briefing_theo", "briefing", default=""), 2000),
        }
    )


def _media_context(lead: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    return _clean_dict(
        {
            "photos": _media_urls(_first(lead, facts, "fotos", "photos", default=[]))[:12],
            "videos": _media_urls(_first(lead, facts, "videos", default=[]))[:6],
            "logo_url": _first(lead, facts, "logo_url", default=""),
        }
    )


def _design_context(
    design: dict[str, Any], visual_dna: dict[str, Any], facts: dict[str, Any]
) -> dict[str, Any]:
    tokens = _dict(_first(design, visual_dna, facts, "tokens", "color_palette", default={}))
    typography = _dict(_first(design, visual_dna, facts, "typography", default={}))
    return _clean_dict(
        {
            "expected_feeling": _first(design, visual_dna, facts, "vibe", "visual_voice", "direction", default=""),
            "archetype": _first(design, visual_dna, facts, "archetype", default=""),
            "color_tokens": tokens,
            "typography": typography,
            "design_reference": _first(design, visual_dna, facts, "design_reference_pack_id", "reference_vibes", default=""),
            "style_mix": _first(visual_dna, facts, "style_mix_instruction", "instrucao_criativa_para_dev", default=""),
            "composition_notes": _as_list(_first(design, facts, "composition", default=[]))[:10],
        }
    )


def _publication_context(lead: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    return _clean_dict(
        {
            "canonical_url": _first(lead, facts, "canonical_url", "site_url", "url_site", default=""),
            "language": "pt-BR",
            "seo_output": [
                "title factual com nome, nicho e cidade",
                "meta description local sem claim não confirmado",
                "meta keywords com termos reais de nicho/cidade",
                "Open Graph e Twitter cards",
                "JSON-LD LocalBusiness com campos confirmados",
            ],
            "motion_policy": "HTML estático seguro: CSS e hooks; sem scripts arbitrários, iframes ou handlers inline.",
        }
    )


def _section_request(lead: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sections = _as_list(_first(facts, {}, "sections", "secoes", default=[]))
    if raw_sections:
        sections = []
        for item in raw_sections[:12]:
            if not isinstance(item, dict):
                continue
            copy = _dict(item.get("copy"))
            sections.append(
                _clean_dict(
                    {
                        "name": item.get("name") or item.get("id") or item.get("title"),
                        "title": item.get("title") or copy.get("h1") or copy.get("h2"),
                        "intent": item.get("body") or copy.get("body"),
                        "items": item.get("items"),
                    }
                )
            )
        if sections:
            return sections
    requested = [
        ("hero", "Primeiro impacto com nome, nicho, cidade e CTA principal."),
        ("prova", "Sinais reais: avaliação, quantidade de reviews, cidade e contato."),
        ("contexto", "Resumo comercial conectado ao nicho e subnicho."),
        ("servicos", "Serviços ou atributos úteis quando fizer sentido para o site."),
        ("midia", "Uso das fotos, vídeos ou tratamento visual gerado pelo Builder."),
        ("depoimentos", "Reviews ou síntese de reputação quando houver material."),
        ("seo", "Conteúdo local guiado pelas palavras-chave e intenção de busca."),
        ("localizacao", "Endereço, mapa ou chamada de visita quando houver dados."),
        ("contato", "Telefone, WhatsApp, formulário ou CTA final."),
        ("footer", "Fechamento consistente com a identidade do site."),
    ]
    if not _as_list(_first(lead, facts, "servicos", "services", default=[])):
        requested = [item for item in requested if item[0] != "servicos"]
    return [{"name": name, "intent": intent} for name, intent in requested]


def _premium_delivery_contract(context: dict[str, Any]) -> str:
    from backend.agents.prompt_agent_helpers import (
        _as_list,
    )

    section_names = _section_sequence_for_niche(  # noqa: F821 — defined later in this module
        _first(context.get("business") or {}, "segmento", "segment", default=""),
        _first(context.get("design") or {}, "archetype", default=""),
        has_services=bool(_as_list(_first(context.get("business") or {}, "servicos", "services", default=[]))),
    )

    business = context.get("business") or {}
    content = context.get("content") or {}
    design = context.get("design") or {}
    seo = context.get("seo") or {}
    visual_contract = context.get("visual_contract") or {}
    build_plan = context.get("site_build_plan") or {}
    segment = str(business.get("segment") or "").lower()
    archetype = str(
        design.get("archetype")
        or visual_contract.get("archetype")
        or _infer_prompt_archetype(segment)
    ).upper()
    section_names = _as_list(
        (build_plan.get("information_architecture") or {}).get("section_order")
        or build_plan.get("section_plan")
        or []
    )
    services = _as_list(content.get("services") or content.get("attributes"))
    if not section_names:
        section_names = _section_sequence_for_niche(segment, archetype, has_services=bool(services))
    keywords = _as_list(seo.get("primary_terms"))
    lines = [
        "- Isto não é checklist legado nem reparo manual: é o padrão mínimo do pedido ao Builder.",
        "- Entregue página de marca/landing comercial, não diretório local, componente demo ou template genérico.",
        "- Use pelo menos 7 seções semânticas úteis com ritmo editorial: "
        + ", ".join(_section_name(item) for item in section_names[:10])
        + ".",
        "- O primeiro viewport precisa ter uma ideia visual forte: hero full-bleed ou composição com mídia dominante, H1 único, CTA principal, CTA secundário quando fizer sentido e prova/localidade visível.",
        "- O screenshot inicial precisa parecer campanha de agência em 2026: composição com profundidade, paleta comprometida, escala tipográfica própria, movimento planejado e assinatura visual impossível de confundir com template Tailwind de 2023.",
        "- O Builder deve entregar qualidade de fonte comparável a AI Studio: Tailwind real (utility classes inline no HTML), data-attributes para motion (data-reveal, data-parallax, data-marquee, data-mask-reveal, data-card-stagger), hero impactante, galeria CSS-only ou com imagens reais do briefing, modal/lightbox implementado com `<dialog>` nativo, imagens reais/editoriais e copy autoral por nicho.",
        "- A saída magra reprova: 20KB de fonte, zero motion, zero imagens, hero+cards+footer sem narrativa ou CSS-only sem galeria não é entrega premium.",
        "- Antes de escolher cores/fonte/fundo, assuma uma decisão de direção de arte: cena física, estratégia de cor, par tipográfico, material de fundo, geometria dos cards e comportamento do menu. Essas decisões precisam aparecer no HTML/CSS.",
        "- Estruture a narrativa com AIDA ou PAS de forma orgânica: escolha AIDA quando a promessa precisa abrir desejo rápido e PAS quando a dor/objeção precisa conduzir a decisão; a escolha deve mudar a ordem, a densidade e o foco das seções, nunca ser um find/replace superficial.",
        "- A arquitetura deve variar por nicho e subnicho: não reutilize a mesma sequência de hero, prova, serviços, contato e footer entre academias, nutrição, barbearias ou clínicas.",
        "- Tailwind precisa nascer da identidade do nicho: varie paleta, contraste, radius, spacing, tipografia e ritmo de grid para que duas páginas diferentes nunca pareçam o mesmo tema com texto trocado.",
        "- SEO de corpo: um único H1, H2/H3 claros, termos locais naturais e conteúdo escaneável; nada de keyword stuffing.",
        "- Publicação deve conter base para SEO técnico: title, description, keywords, canonical quando houver URL, Open Graph, Twitter card e JSON-LD LocalBusiness usando apenas fatos confirmados.",
        "- Motion seguro obrigatório: use hooks data-reveal, data-parallax, mask-reveal, line-draw e card-stagger; anime somente opacity/transform; inclua fallback visual e respeite prefers-reduced-motion.",
        "- Não use scripts, handlers inline, iframes, data: URLs, javascript: URLs, mapa genérico ou elemento que dependa de código ativo para revelar conteúdo essencial.",
        "- Use imagens reais do briefing primeiro. Se usar mídia editorial/stock fornecida pela FraLib, trate como apoio visual; nunca declare que é foto real do local sem confirmação.",
        "- Evite saída pobre: hero centrado genérico, azul/índigo padrão, pilha de cards iguais, footer preto padrão, seções rasas, ausência de CTA, ausência de prova local, contraste fraco ou layout sem direção.",
        "- Evite scaffolds saturados: `max-w-7xl mx-auto px-4`, botões `bg-blue-600`, grids 3x de cards arredondados, títulos pequenos demais e galeria sem narrativa visual.",
        "- Evite assinatura 2023 reprovável: `bg-white rounded-xl/2xl shadow-lg` repetido, navbar branca genérica, footer preto genérico, `font-sans` como única voz e background plano sem material.",
        "- Responsividade: mobile-first, sem overflow horizontal, títulos com clamp(), touch targets 44px+, nav sem cobrir o hero e texto sempre legível.",
    ]
    if keywords:
        lines.append("- Termos SEO prioritários a distribuir com naturalidade: " + ", ".join(str(k) for k in keywords[:10]) + ".")
    if not services:
        lines.append("- Serviços/produtos oficiais ausentes: não crie cards de serviços/preços. Use blocos de decisão, dúvidas e contato sem fingir catálogo.")
    skill_pack = _runtime_site_skill_pack()
    if skill_pack:
        lines.extend(
            [
                "",
                "SITE SKILL PACK FRA LIB APLICAVEL AO BUILDER:",
                skill_pack,
            ]
        )
    if archetype == "BOLD_ENERGY" or any(token in segment for token in ("academia", "fitness", "crossfit", "treino")):
        lines.extend(
            [
                "- Arquétipo BOLD_ENERGY: a página deve parecer uma campanha premium de treino, não um cartão de academia.",
                "- Use base preta/carbão, vermelho elétrico, branco quente, tipografia display condensada/impactante, cortes diagonais, imagem escura/crop agressivo e stats em slabs perto da dobra. Azul corporativo reprova.",
                "- Inclua manifesto forte após o hero, especialidades/estrutura quando confirmadas, reputação, FAQ e CTA final com energia visual comparável a uma peça de lançamento fitness.",
            ]
        )
    elif any(token in segment for token in ("energia", "solar", "eletrica", "elétrica", "fotovoltaica", "infraestrutura")):
        lines.extend(
            [
                "- Arquétipo energia/infra: busque impacto como landing de agência para energia, com luz, grade, feixes, contraste técnico, prova econômica e sensação de engenharia confiável.",
                "- Use motion hooks para linhas luminosas, reveals de números/provas e profundidade no hero; evite cards azuis genéricos e ilustração SaaS.",
            ]
        )
    elif archetype == "ZEN_PURE":
        lines.extend(
            [
                "- Arquétipo ZEN_PURE: use clareza, respiro, fotografia editorial de cuidado, superfícies leves e motion suave; evite layout hospitalar ou SaaS frio.",
                "- Mesmo em estética clara, mantenha densidade comercial: prova, objeções, contato e localização visíveis.",
            ]
        )
    elif archetype == "LUXURY_ELITE":
        lines.extend(
            [
                "- Arquétipo LUXURY_ELITE: imagem full-bleed, contraste sofisticado, escala tipográfica, poucas palavras fortes e composição editorial; evite luxo automotivo sem relação com o nicho.",
                "- Para gastronomia, o desejo deve vir de atmosfera, textura, processo e CTA, não de claims inventados sobre cardápio, origem ou preço.",
            ]
        )
    return "\n".join(lines)


def _section_sequence_for_niche(segment: str, archetype: str, *, has_services: bool) -> list[str]:

    normalized = _normalize(segment)
    if any(token in normalized for token in ("nutric", "saude", "alimentacao", "bem estar", "bem-estar")):
        return [
            "hero",
            "dor e contexto",
            "rotina/transformacao",
            "prova social",
            "servicos confirmados" if has_services else "abordagem e metodo",
            "nutricao na pratica",
            "faq de objeções",
            "localizacao/contato",
            "cta final",
            "footer",
        ]
    if any(token in normalized for token in ("barbearia", "cabelo", "estetica masculina", "barba")):
        return [
            "hero",
            "impacto visual",
            "servicos confirmados" if has_services else "assinatura do atendimento",
            "experiencia premium",
            "prova social",
            "ritual/atendimento",
            "faq de decisão",
            "localizacao/contato",
            "cta final",
            "footer",
        ]
    if archetype == "BOLD_ENERGY":
        return [
            "hero",
            "dor/aspiracao",
            "treino/resultado",
            "prova social",
            "estrutura/servicos" if has_services else "metodo",
            "transformacao",
            "faq",
            "localizacao/contato",
            "cta final",
            "footer",
        ]
    return [
        "hero",
        "dor e contexto",
        "prova social",
        "servicos confirmados" if has_services else "posicionamento",
        "midia/narrativa visual",
        "faq de decisão",
        "localizacao/contato",
        "cta final",
        "footer",
    ]


def _visual_direction_contract(context: dict[str, Any]) -> dict[str, Any]:
    """Create the concrete art-direction contract the Builder must compose from."""
    from backend.agents.prompt_agent_helpers import _as_list

    business = context.get("business") or {}
    media = context.get("media") or {}
    content = context.get("content") or {}
    design = context.get("design") or {}
    visual_contract = context.get("visual_contract") or {}
    build_plan = context.get("site_build_plan") or {}
    segment = str(business.get("segment") or "negócio local")
    archetype = str(
        design.get("archetype")
        or visual_contract.get("archetype")
        or _infer_prompt_archetype(segment)
    ).upper()
    photos = _as_list(media.get("photos"))
    has_address = bool(business.get("address") or content.get("maps_url"))
    has_reviews = bool(business.get("rating") or business.get("reviews_count"))
    section_order = _visual_section_order(build_plan, has_address=has_address)
    scene, color, hero, surfaces = _direction_for_archetype(
        archetype,
        segment=segment,
        has_photos=bool(photos),
        has_reviews=has_reviews,
        has_address=has_address,
    )
    return {
        "version": "fralib-visual-director-v2",
        "runtime_output": {
            "engine": "OpenUI static HTML + Tailwind utility classes inline + data-attributes for motion",
            "format": "single self-contained HTML document with inline Tailwind classes; deploy injects Motion Runtime JS for data-attributes",
            "studio_contract": [
                "Tailwind v4 utility classes inline (no build step)",
                "data-attribute motion (data-reveal, data-parallax, data-marquee, data-mask-reveal, data-card-stagger) picked up by FraLib Motion Runtime",
                "Hero image-led plus gallery/lifestyle sections",
                "Modal/lightbox via native <dialog> element",
                "dense semantic HTML comparable to AI Studio output",
            ],
            "creates": [
                "package.json",
                "index.html",
                "vite.config.ts",
                "tsconfig.json",
                "src/main.tsx",
                "src/App.tsx",
                "src/index.css",
                "src/types.ts",
                "src/pages/Index.tsx",
                "src/components/Navbar.tsx",
                "src/components/GallerySection.tsx",
                "src/components/LifestyleSection.tsx",
                "src/components/BookingModal.tsx",
                "src/components/*.tsx",
                "dist/index.html",
                "builder-render.json",
                "vite-render.json",
            ],
            "does_not_create": [
                "Next.js app router",
                "server-side routes",
                "auth/database/admin modules",
            ],
        },
        "archetype": archetype,
        "scene": scene,
        "color_strategy": color,
        "hero_storyboard": hero,
        "section_direction": section_order,
        "surface_system": surfaces,
        "media_strategy": {
            "hero": "use the strongest provided photo as a dominant crop/depth layer"
            if photos
            else "build a CSS-only editorial depth scene; never leave a flat blank hero",
            "supporting": "reuse media as one narrative strip/collage, not scattered filler cards",
            "fallback": "if media is absent, create material surfaces, silhouettes, light fields or typographic depth",
        },
        "hard_rejections": [
            "centered brochure hero without dominant media/depth",
            "single-file static HTML when Vite/React source was requested",
            "bg-white rounded-xl/2xl shadow-lg repeated as the main system",
            "cream/sand/beige wellness default",
            "default blue/indigo Tailwind CTA",
            "generic black footer unrelated to the page",
            "gallery after footer or post-footer content",
        ],
    }


def _visual_section_order(
    build_plan: dict[str, Any], *, has_address: bool
) -> list[dict[str, str]]:
    from backend.agents.prompt_agent_helpers import _as_list

    raw = (
        (build_plan.get("information_architecture") or {}).get("section_order")
        or build_plan.get("section_plan")
        or []
    )
    if raw:
        order = [_section_name(item) for item in _as_list(raw)]
    else:
        order = [
            "hero",
            "trust_bar",
            "decision_content",
            "media_story",
            "about",
            "faq",
            "location_contact" if has_address else "contact",
            "footer",
        ]
    surface = {
        "hero": "campaign first viewport with one dominant visual idea",
        "trust_bar": "proof integrated near the fold, not a floating metric cliché",
        "decision_content": "editorial section that teaches how to choose this service",
        "media_story": "image-led 16:9 or collage section with narrative intent",
        "about": "business context with asymmetric copy/media rhythm",
        "confirmed_services": "only confirmed offers; avoid invented catalog cards",
        "social_proof": "reviews/proof as editorial evidence, not fake testimonials",
        "faq": "objection handling with compact readable rhythm",
        "location_contact": "address/contact conversion section with one map/link treatment",
        "contact": "conversion section with city and contact clarity",
        "footer": "designed closure in the same palette, never generic fallback",
    }
    return [
        {"id": item, "visual_role": surface.get(item, "intentional non-template section")}
        for item in order[:10]
    ]


def _direction_for_archetype(
    archetype: str,
    *,
    segment: str,
    has_photos: bool,
    has_reviews: bool,
    has_address: bool,
) -> tuple[str, str, dict[str, Any], list[str]]:

    normalized = _normalize(segment)
    if archetype == "BOLD_ENERGY" or any(
        token in normalized for token in ("academia", "fitness", "crossfit", "treino")
    ):
        return (
            "academia como campanha noturna de treino: luz dura, suor, contraste e ação local",
            "drenched dark charcoal with electric red action system; no corporate blue",
            {
                "composition": "full-viewport poster hero with cropped media/texture, diagonal cut, giant condensed H1 and red CTA",
                "proof": "3 stat/proof slabs inside the fold" if has_reviews else "local/context chip inside the fold",
                "motion": "data-parallax on hero media, mask reveal on headline and line-draw accents",
                "media": "dominant photo crop" if has_photos else "cinematic CSS light/texture layer",
            },
            ["black/red campaign base", "manifesto band", "cropped media slabs", "dark footer with red rule"],
        )
    if archetype == "ZEN_PURE":
        return (
            "consulta/cuidado premium com luz natural, material mineral e presença humana",
            "committed mineral teal/eucalyptus with coral warmth; avoid cream, sand and gray hospital UI",
            {
                "composition": "asymmetric editorial hero with oversized display copy, organic media frame and visible contact path",
                "proof": "rating/city/contact chip near hero" if has_reviews else "local care chip near hero",
                "motion": "soft parallax on media/depth layer, staggered proof and gentle mask reveal",
                "media": "human/editorial wellness crop" if has_photos else "layered botanical/mineral CSS scene",
            },
            ["mineral teal body", "off-white only as controlled inset surface", "coral CTA", "image-led story band"],
        )
    if archetype == "LUXURY_ELITE":
        return (
            "negócio de desejo local tratado como editorial de revista, textura e atmosfera",
            "deep ink/oxblood/forest or porcelain with one rich accent; no cheap gold gradient",
            {
                "composition": "monumental image/type hero with sparse copy, tension and precise CTA",
                "proof": "local proof and contact integrated as a refined strip",
                "motion": "slow image mask, parallax depth and restrained reveals",
                "media": "full-bleed food/product/place crop" if has_photos else "typographic/editorial texture scene",
            },
            ["full-bleed image moments", "editorial copy bands", "few non-identical panels", "luxury footer"],
        )
    if archetype == "MODERN_TECH":
        return (
            "serviço técnico em ambiente de precisão, clareza operacional e luz de produto",
            "committed technical dark/bright contrast with one energetic accent",
            {
                "composition": "structured asymmetric hero with product/system metaphor and conversion path",
                "proof": "business outcome chips near fold",
                "motion": "line-draw, interface-like reveal and subtle parallax",
                "media": "interface/product crop if available, otherwise engineered CSS grid/light",
            },
            ["engineered grid", "technical proof panels", "sharp CTA", "structured footer"],
        )
    return (
        "serviço local confiável com autoridade editorial e prova prática",
        "restrained but not generic: avoid default blue; choose a committed accent from the business scene",
        {
            "composition": "authority hero with asymmetry, proof chip, clear CTA and location/contact early",
            "proof": "rating/address/contact visibly inside first viewport"
            if has_address or has_reviews
            else "local trust chip inside first viewport",
            "motion": "subtle reveal, line-draw and one depth layer",
            "media": "real business/category media when available; otherwise material backdrop",
        },
        ["authority surface", "proof band", "decision section", "contact/footer in same system"],
    )


def _fmt_visual_direction(direction: dict[str, Any]) -> str:
    if not direction:
        return "- Direção visual ausente; Builder deve criar uma antes do layout."
    return json.dumps(direction, ensure_ascii=False, indent=2)


def _runtime_site_skill_pack() -> str:
    """Load the compact repo-owned design skill pack for Builder prompts."""
    try:
        from .site_skill_pack import SITE_SKILL_PACK
    except Exception:
        try:
            from agents.site_skill_pack import SITE_SKILL_PACK
        except Exception:
            return ""
    return str(SITE_SKILL_PACK or "").strip()[:7000]
