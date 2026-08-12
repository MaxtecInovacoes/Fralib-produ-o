"""Step: Builder — Fase 4: Geração de HTML via OpenUI."""
import logging
from backend.agents.manager.states import (
    PipelineState, STATE_BUILDING, STATE_VALIDATING, STATE_FAILED,
    _transition, _log_step_error,
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

        # Reconstruct DesignerPRD from state.design_output using ACTUAL schema
        color_palette_data = state.design_output.get("color_palette", {}) or state.design_output.get("paleta_cores", {})
        if not color_palette_data:
            color_palette_data = {"primary": "#1a1a2e", "secondary": "#e94560", "accent": "#f5a623", "background": "#ffffff", "text": "#333333"}

        sections = []
        for s_data in state.design_output.get("sections", []):
            sections.append(SectionSpec(
                name=s_data.get("name", ""),
                title=s_data.get("title", ""),
                content=s_data.get("content", s_data.get("body", "")),
            ))

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
        result = render_site(prd, usar_llm=True)
        if not getattr(result, "success", False):
            raise RuntimeError(getattr(result, "error", "Builder falhou sem erro detalhado"))
        state.build_output = {"html": result.html, "model": result.model}

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
