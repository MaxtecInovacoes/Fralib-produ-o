"""Step: Builder — Fase 4: Geração de HTML via OpenUI."""
import logging
import re
from backend.agents.manager.states import (
    PipelineState, STATE_BUILDING, STATE_VALIDATING, STATE_FAILED,
    _transition, _log_step_error, _record_agent_handoff,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")


def step_builder(state: PipelineState) -> PipelineState:
    """Fase 4: Builder gera HTML via OpenUI single-shot."""
    if state.current_state != STATE_BUILDING:
        return state

    try:
        from backend.agents.builder.agent import render_site
        from backend.agents.designer_prd import DesignerPRD, SectionSpec, ColorPalette, AnimationSpec

        if len((state.design_output or {}).get("photos") or []) < 3:
            from backend.agents.unsplash_fetcher import buscar_fotos_unsplash
            restored_photos = buscar_fotos_unsplash(
                segmento=state.segmento,
                quantidade=6,
                nome=(state.lead_data or {}).get("nome", ""),
                cidade=state.cidade,
            )
            state.design_output = dict(state.design_output or {})
            state.design_output["photos"] = restored_photos
            state.lead_data = dict(state.lead_data or {})
            state.lead_data["fotos"] = restored_photos

        from backend.agents.arquiteto_agent_loop import _enrich_prd
        state.design_output = _enrich_prd(
            dict(state.design_output or {}),
            dados_hunter=state.lead_data or {},
            cidade=state.cidade,
            segmento=state.segmento,
            dark_mode=bool((state.design_output or {}).get("dark_mode", False)),
        )

        # Reconstruct DesignerPRD from state.design_output using ACTUAL schema
        color_palette_data = state.design_output.get("color_palette", {}) or state.design_output.get("paleta_cores", {})
        if not color_palette_data:
            color_palette_data = {"primary": "#1a1a2e", "secondary": "#e94560", "accent": "#f5a623", "background": "#ffffff", "text": "#333333"}

        sections = []
        for s_data in state.design_output.get("sections", []):
            if isinstance(s_data, dict):
                sections.append(SectionSpec(**s_data))
            else:
                sections.append(SectionSpec(name=str(getattr(s_data, "name", "") or "")))

        animations = []
        for a_data in state.design_output.get("animations", []):
            animations.append(AnimationSpec(**a_data) if a_data else None)
        animations = [a for a in animations if a is not None]

        prd = DesignerPRD(
            business_name=state.design_output["business_name"],
            sections=sections,
            color_palette=ColorPalette(**(color_palette_data or {})),
            typography=state.design_output.get("typography", {}),
            animations=animations,
            reviews_count=state.design_output.get("reviews_count", 0),
            reviews_rating=state.design_output.get("reviews_rating", 0.0),
            reviews_list=state.design_output.get("reviews_list", []),
            address=state.design_output.get("address", ""),
            phone=state.design_output.get("phone", state.lead_data.get("telefone", "")),
            hours=state.design_output.get("hours"),
            photos=state.design_output.get("photos", []),
            videos=state.design_output.get("videos", []),
            google_maps_embed=state.design_output.get("google_maps_embed", ""),
            components_21dev=state.design_output.get("components_21dev", ["whatsapp-sticky-cta"]),
            competitor_analysis=state.design_output.get("competitor_analysis", ""),
            anti_patterns=state.design_output.get("anti_patterns", ["precos visiveis"]),
            schema_org_types=state.design_output.get("schema_org_types", ["LocalBusiness"]),
            cidade=state.design_output.get("cidade", state.lead_data.get("cidade", "") if state.lead_data else ""),
            segmento=state.design_output.get("segmento", state.lead_data.get("segmento", "") if state.lead_data else ""),
            geo=state.design_output.get("geo", None),
            design_system_slug=state.design_output.get("design_system_slug", None),
            dark_mode=state.design_output.get("dark_mode", False),
            faq_questions=state.design_output.get("faq_questions", []),
            value_props=state.design_output.get("value_props", []),
            layout_type=state.design_output.get("layout_type", ""),
            instrucao_criativa_para_dev=state.design_output.get("instrucao_criativa_para_dev", ""),
            seo_keywords=state.design_output.get("seo_keywords", []),
            visual_dna=state.design_output.get("visual_dna", {}),
            layout_blueprint=state.design_output.get("layout_blueprint", []),
            design_reference_pack=state.design_output.get("design_reference_pack", {}),
            site_build_plan=state.design_output.get("site_build_plan", {}),
            requirements_contract=state.design_output.get("requirements_contract", {}),
            visual_contract=state.design_output.get("visual_contract", {}),
            niche_brief=state.design_output.get("niche_brief", state.niche_brief or {}),
            creative_direction=state.design_output.get("creative_direction", state.creative_direction or {}),
            variation_blueprint=state.design_output.get("variation_blueprint", state.variation_blueprint or {}),
            media_plan=state.design_output.get("media_plan", state.media_plan or []),
        )
        # Instrumentação: verificar se os 3 contratos do Arquiteto chegaram ao Builder
        try:
            from loguru import logger as _mgr_logger
            _mgr_logger.info(
                "PRD_MANAGER: site_build_plan_keys={sbp_keys} "
                "requirements_contract_keys={rc_keys} "
                "visual_contract_keys={vc_keys}",
                sbp_keys=list(prd.site_build_plan.keys()) if prd.site_build_plan else [],
                rc_keys=list(prd.requirements_contract.keys()) if prd.requirements_contract else [],
                vc_keys=list(prd.visual_contract.keys()) if prd.visual_contract else [],
            )
        except Exception as exc:
            logger.warning("[manager] loguru instrumentation falhou (lead=%s): %s",
                           state.lead_id, exc)
        # Fase 3 SEO/GEO - AGENTE 19 TRUST SIGNALS: propagar rating do lead
        # para o JSON-LD LocalBusiness.aggregateRating do inject.py.
        lead_rating = state.lead_data.get("rating") if state.lead_data else None
        lead_reviews = (
            state.lead_data.get("reviews_count")
            or state.lead_data.get("total_avaliacoes")
        ) if state.lead_data else None
        lead_telefone = (
            state.lead_data.get("telefone")
        ) if state.lead_data else None
        if lead_rating:
            setattr(prd, "_lead_rating", float(lead_rating))
        if lead_reviews:
            setattr(prd, "_lead_reviews_count", int(lead_reviews))
        if lead_telefone:
            # Fase 4 — scrub de placeholder telefonico.
            setattr(prd, "_lead_telefone", str(lead_telefone))
        # Fase 5 — Entity-Placeholder resolution (inject.resolve_entity_tags
        # troca {{business_name}}/etc pelos valores reais, fora do LLM).
        if state.lead_data:
            setattr(prd, "_lead_data", dict(state.lead_data))
        setattr(prd, "_run_id", state.run_id)
        setattr(prd, "_lead_id", state.lead_id)
        slug = re.sub(r"[^a-z0-9]+", "-", state.lead_data.get("nome", "site").lower()).strip("-")[:50] or "site"
        canonical_url = f"https://app.seunegociofralib.site/sites/{state.tenant_id}/{slug}-{state.lead_id[:8]}/"
        setattr(prd, "canonical_url", canonical_url)
        result = render_site(prd, usar_llm=True)
        if not getattr(result, "success", False):
            raise RuntimeError(getattr(result, "error", "Builder falhou sem erro detalhado"))
        html = _enforce_pre_qa_contract(result.html, prd)
        state.build_output = {"html": html, "model": result.model}
        try:
            from backend.agents.builder.agent import _prd_to_spec
            from backend.agents.manager.states import _record_visual_custody

            state.openui_payload = _prd_to_spec(prd)
            _record_visual_custody(
                state,
                "openui_payload",
                received_decisions={
                    "creative_direction": bool(state.openui_payload.get("creative_direction")),
                    "variation_blueprint": bool(state.openui_payload.get("variation_blueprint")),
                    "media_plan": len(state.openui_payload.get("media_plan") or []),
                },
                preserved_decisions={
                    "section_order": (
                        state.openui_payload.get("variation_blueprint", {}).get("ordem_das_secoes")
                        or state.openui_payload.get("site_build_plan", {}).get("information_architecture", {}).get("section_order")
                    ),
                    "media_plan": state.openui_payload.get("media_plan", []),
                    "typography": state.openui_payload.get("typography", {}),
                    "palette": state.openui_payload.get("color_palette", {}),
                },
            )
        except Exception as exc:
            logger.warning("[Builder] openui payload custody falhou (lead=%s): %s", state.lead_id, exc)

        _record_agent_handoff(
            state,
            "builder_openui",
            received={
                "designer_prd": state.design_output or {},
                "openui_url": getattr(prd, "_openui_url", None),
            },
            produced={
                "model": result.model,
                "html_length": len(html),
                "html_counts": {
                    "main": html.lower().count("<main"),
                    "h1": html.lower().count("<h1"),
                    "section": html.lower().count("<section"),
                    "img": html.lower().count("<img"),
                    "background_image": html.lower().count("background-image"),
                },
                "html_preview": html[:2000],
            },
            preserved={
                "media_plan": (state.openui_payload or {}).get("media_plan", []),
                "section_order": (
                    (state.openui_payload or {}).get("variation_blueprint", {}).get("ordem_das_secoes")
                    or (state.openui_payload or {}).get("site_build_plan", {}).get("information_architecture", {}).get("section_order")
                ),
                "typography": (state.openui_payload or {}).get("typography", {}),
                "palette": (state.openui_payload or {}).get("color_palette", {}),
            },
        )

        try:
            from backend.agents.pipeline_checkpoint import gerar_pipeline_id, salvar_checkpoint

            pipeline_id = gerar_pipeline_id(
                state.tenant_id,
                state.lead_data.get("nome", "") if state.lead_data else "",
                state.segmento,
                state.cidade,
                state.lead_id,
            )
            salvar_checkpoint(pipeline_id, "builder", state.build_output)
        except Exception as exc:
            logger.warning("[Builder] checkpoint HTML falhou (lead=%s): %s", state.lead_id, exc)

        try:
            from backend.agents.artifact_store import write_html_artifact
            write_html_artifact(
                run_id=state.run_id,
                lead_id=state.lead_id,
                lead_name=state.lead_data.get("nome", "") if state.lead_data else "",
                filename="builder/final_html/03-builder-final.html",
                html=html,
                metadata={
                    "step": "builder",
                    "tenant_id": state.tenant_id,
                    "model": result.model,
                    "segmento": state.segmento,
                    "cidade": state.cidade,
                },
            )
        except Exception as exc:
            logger.warning("[Builder] artifact HTML falhou (lead=%s): %s", state.lead_id, exc)
    except Exception as e:
        _log_step_error(state, "Builder", e)
        state.error = f"Builder: {e}"
        return _transition(state, STATE_FAILED)

    # Knowledge Journal: ArtifactGenerated
    try:
        journal_record(
            project_id=state.lead_id,
            event_type="artifact_generated",
            hypothesis="HTML gerado pelo Builder a partir do PRD completo",
            payload={"model": state.build_output.get("model", "unknown"), "html_length": len(state.build_output.get("html", ""))},
        )
    except Exception as exc:
        logger.warning("[manager] journal artifact_generated falhou (lead=%s): %s",
                       state.lead_id, exc)

    return _transition(state, STATE_VALIDATING)


_EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\u2600-\u27BF"
    "]+",
    flags=re.UNICODE,
)


def _enforce_pre_qa_contract(html: str, prd) -> str:
    """Aplica e valida contratos determinísticos antes do QA pass-through."""
    cleaned = html or ""
    if 'data-renderer="builder"' not in cleaned.lower():
        cleaned = re.sub(
            r"(?is)<html\b([^>]*)>",
            r'<html\1 data-renderer="builder">',
            cleaned,
            count=1,
        )
    try:
        from backend.agents.html_builder_repair import repair_builder_publication_contract
        cleaned = repair_builder_publication_contract(cleaned, prd)
    except ModuleNotFoundError as exc:
        logger.warning("[Builder] reparador legado indisponível; usando contrato interno: %s", exc)
    cleaned = _EMOJI_RE.sub("", cleaned)

    photos = getattr(prd, "photos", []) or []
    og_image = photos[0].get("url") if photos and isinstance(photos[0], dict) else (photos[0] if photos else "")
    head_additions = []
    low = cleaned.lower()
    if 'rel="icon"' not in low and "rel='icon'" not in low:
        head_additions.append(
            '<link rel="icon" href="data:image/svg+xml,'
            '<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22>'
            '<rect width=%2264%22 height=%2264%22 rx=%2214%22 fill=%22%23111827%22/>'
            '<path d=%22M18 46V18h28v8H28v4h14v8H28v8z%22 fill=%22white%22/>'
            '</svg>">'
        )
    if og_image and 'property="og:image"' not in low:
        head_additions.append(f'<meta property="og:image" content="{og_image}">')
    if 'property="og:title"' not in low:
        head_additions.append(f'<meta property="og:title" content="{getattr(prd, "business_name", "Negócio local")}">')
    if head_additions:
        cleaned = re.sub(r"(?is)</head>", "\n".join(head_additions) + "\n</head>", cleaned, count=1)

    cleaned = _ensure_internal_publication_contract(cleaned, prd)

    required_markers = {
        "imagem": r"(?is)<img\b|background-image\s*:",
        "faq": r"(?is)faq|perguntas frequentes",
        "footer": r"(?is)<footer\b|section:footer",
        "descricao": r"(?is)<meta\s+name=[\"']description[\"']",
        "open_graph": r"(?is)<meta\s+property=[\"']og:",
        "favicon": r"(?is)<link\s+rel=[\"']icon[\"']",
        "json_ld": r"(?is)application/ld\+json",
        "lgpd": r"(?is)data-lgpd-banner",
    }
    missing = [name for name, pattern in required_markers.items() if not re.search(pattern, cleaned)]
    if missing:
        raise ValueError("HTML sem contrato pré-QA: " + ", ".join(missing))
    return cleaned


def _ensure_internal_publication_contract(html: str, prd) -> str:
    import html as html_lib
    import json

    cleaned = html or ""
    low = cleaned.lower()
    name = html_lib.escape(str(getattr(prd, "business_name", "Negócio local") or "Negócio local"), quote=True)
    city = html_lib.escape(str(getattr(prd, "cidade", "") or ""), quote=True)
    phone = html_lib.escape(str(getattr(prd, "phone", "") or ""), quote=True)
    address = html_lib.escape(str(getattr(prd, "address", "") or ""), quote=True)
    canonical = html_lib.escape(str(getattr(prd, "canonical_url", "") or ""), quote=True)
    keywords = ", ".join(str(item) for item in (getattr(prd, "seo_keywords", []) or [])[:10])
    description = f"{name} em {city}. Informações, serviços, localização e contato oficial.".strip()

    additions = []
    if "<title" not in low:
        additions.append(f"<title>{name} em {city}</title>")
    if 'name="description"' not in low:
        additions.append(f'<meta name="description" content="{description}">')
    if keywords and 'name="keywords"' not in low:
        additions.append(f'<meta name="keywords" content="{html_lib.escape(keywords, quote=True)}">')
    if canonical and 'rel="canonical"' not in low:
        additions.append(f'<link rel="canonical" href="{canonical}">')
    if 'property="og:url"' not in low and canonical:
        additions.append(f'<meta property="og:url" content="{canonical}">')
    if 'application/ld+json' not in low:
        schema = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": name,
            "url": canonical,
            "address": address or city,
            "telephone": phone,
        }
        additions.append(
            '<script type="application/ld+json">'
            + json.dumps({key: value for key, value in schema.items() if value}, ensure_ascii=False)
            + "</script>"
        )
    if additions:
        cleaned = re.sub(r"(?is)</head>", "\n".join(additions) + "\n</head>", cleaned, count=1)

    if "<footer" not in cleaned.lower():
        footer = (
            f'<footer id="footer" class="px-6 py-12 bg-neutral-950 text-white">'
            f'<p>{name}</p><p>{address or city}</p><p>{phone}</p>'
            '<nav aria-label="Links legais"><a href="/politica-de-privacidade">Privacidade</a> '
            '<a href="/termos-de-uso">Termos de uso</a></nav></footer>'
        )
        cleaned = re.sub(r"(?is)</main>", footer + "\n</main>", cleaned, count=1)
    if "data-lgpd-banner" not in cleaned.lower():
        banner = (
            '<div data-lgpd-banner class="fixed bottom-4 left-4 right-4 z-50 bg-neutral-950 text-white p-4">'
            '<span>Usamos dados apenas para atendimento e melhoria da experiência.</span>'
            '<button type="button" onclick="this.parentElement.remove()">Aceitar</button></div>'
        )
        cleaned = re.sub(r"(?is)</body>", banner + "\n</body>", cleaned, count=1)
    return cleaned
