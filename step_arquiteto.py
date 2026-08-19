"""Step: Arquiteto — Fase 3: Geração de PRD (DesignerPRD) via Managed Agent."""
import json
import logging
import time
from backend.agents.manager.states import (
    PipelineState, STATE_DESIGNING, STATE_BUILDING, STATE_FAILED,
    _transition, _is_transient_llm_error, _log_step_error, _record_agent_handoff,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")


def step_arquiteto(state: PipelineState) -> PipelineState:
    """Fase 3: Arquiteto gera DesignerPRD via Managed Agent (tool-use loop)."""
    if state.current_state != STATE_DESIGNING:
        return state

    caio = state.caio_output
    tier = caio.tier if caio else "STANDARD"
    score = caio.score if caio else 0
    dark_mode = getattr(caio, "dark_mode", False) if caio else False

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            from backend.agents.arquiteto_agent_loop import gerar_arquiteto_mestre_prd_agent

            keyword_research = ""
            try:
                try:
                    from backend.services.keyword_research import pesquisar_keywords
                except ModuleNotFoundError:
                    from backend.agents.keyword_research import pesquisar_keywords_nicho as pesquisar_keywords
                keyword_research = pesquisar_keywords(
                    segmento=state.segmento,
                    cidade=state.cidade,
                ) or ""
            except Exception as kw_err:
                logger.warning("[Arquiteto] keyword research falhou: %s", kw_err)

            jina_insights = state.lead_data.get("jina_insights", "") or ""

            prd = gerar_arquiteto_mestre_prd_agent(
                dados_hunter=state.lead_data,
                cidade=state.cidade,
                segmento=state.segmento,
                jina_insights=jina_insights,
                caio_tier=tier,
                caio_score=score,
                dark_mode=dark_mode,
                keyword_research=keyword_research,
                niche_brief=state.niche_brief,
                creative_direction=state.creative_direction,
                variation_blueprint=state.variation_blueprint,
            )

            if prd and hasattr(prd, "business_name"):
                state.design_output = _prd_to_dict(prd)
                if state.niche_brief:
                    state.design_output.setdefault("niche_brief", state.niche_brief)
                if state.creative_direction:
                    state.design_output.setdefault("creative_direction", state.creative_direction)
                if state.variation_blueprint:
                    state.design_output.setdefault("variation_blueprint", state.variation_blueprint)
                state.designer_prd = state.design_output
                # F5 — validate reviews_count matches reviews_list length
                prd_reviews_count = state.design_output.get("reviews_count", 0)
                prd_reviews_list = state.design_output.get("reviews_list", []) or []
                if prd_reviews_count != len(prd_reviews_list):
                    logger.warning(
                        "[Arquiteto] reviews_count mismatch PRD=%s list=%s lead=%s",
                        prd_reviews_count, len(prd_reviews_list), state.lead_id,
                    )
                    state.design_output["reviews_count"] = len(prd_reviews_list)
                state.visual_dna = state.design_output.get("visual_dna", {})
                state.media_plan = state.design_output.get("media_plan", [])
                state.history.append(f"Arquiteto: PRD OK ({len(state.design_output.get('sections', []))} seções)")
                try:
                    from backend.agents.manager.states import _record_visual_custody

                    _record_visual_custody(
                        state,
                        "designer_prd",
                        received_decisions={
                            "niche_brief": bool(state.niche_brief),
                            "creative_direction": bool(state.creative_direction),
                            "variation_blueprint": bool(state.variation_blueprint),
                        },
                        preserved_decisions={
                            "visual_dna": state.visual_dna,
                            "media_plan": state.media_plan,
                            "section_order": (state.variation_blueprint or {}).get("ordem_das_secoes", []),
                            "typography": state.design_output.get("typography", {}),
                            "color_palette": state.design_output.get("color_palette", {}),
                        },
                    )
                except Exception as exc:
                    logger.warning("[Arquiteto] visual custody falhou (lead=%s): %s", state.lead_id, exc)

                _record_agent_handoff(
                    state,
                    "designer_prd",
                    received={
                        "lead_data": state.lead_data or {},
                        "caio": {
                            "tier": tier,
                            "score": score,
                            "dark_mode": dark_mode,
                        },
                        "niche_brief": state.niche_brief or {},
                        "creative_direction": state.creative_direction or {},
                        "variation_blueprint": state.variation_blueprint or {},
                    },
                    produced=state.design_output,
                    preserved={
                        "section_order": (state.variation_blueprint or {}).get("ordem_das_secoes", []),
                        "media_plan": state.media_plan,
                        "typography": state.design_output.get("typography", {}),
                        "color_palette": state.design_output.get("color_palette", {}),
                        "reviews_count": state.design_output.get("reviews_count", 0),
                        "phone": state.design_output.get("phone", ""),
                    },
                    changed={
                        "typography_from_creative": (state.creative_direction or {}).get("typography_strategy", {}),
                        "typography_in_prd": state.design_output.get("typography", {}),
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
                    salvar_checkpoint(pipeline_id, "arquiteto", {"prd_json": state.design_output})
                except Exception as exc:
                    logger.warning("[Arquiteto] checkpoint PRD falhou (lead=%s): %s", state.lead_id, exc)

                try:
                    journal_record(
                        project_id=state.lead_id,
                        event_type="narrative_locked",
                        hypothesis=f"PRD gerado para {prd.business_name} ({state.segmento}, {state.cidade})",
                        payload={"tier": tier, "score": score, "sections": len(state.design_output.get("sections", []))},
                    )
                except Exception as exc:
                    logger.warning("[Arquiteto] journal narrative_locked falhou (lead=%s): %s", state.lead_id, exc)

                try:
                    journal_record(
                        project_id=state.lead_id,
                        event_type="identity_approved",
                        hypothesis=f"Design system aprovado: {state.design_output.get('color_palette', {}).get('reasoning', '')[:100]}",
                        payload={"color_palette": state.design_output.get("color_palette", {})},
                    )
                except Exception as exc:
                    logger.warning("[Arquiteto] journal identity_approved falhou (lead=%s): %s", state.lead_id, exc)

                return _transition(state, STATE_BUILDING)

            raise ValueError("PRD retornado vazio ou inválido")

        except Exception as e:
            if _is_transient_llm_error(e) and attempt < max_attempts - 1:
                wait = [5, 15, 45][attempt]
                logger.warning("[Arquiteto] LLM transient error (attempt %d/%d), aguardando %ds: %s",
                               attempt + 1, max_attempts, wait, e)
                time.sleep(wait)
                continue
            logger.exception("[Arquiteto] falha não transitória (lead=%s)", state.lead_id)
            _log_step_error(state, "Arquiteto", e)
            state.error = "Arquiteto: falha interna na geração do PRD"
            return _transition(state, STATE_FAILED)

    state.error = "Arquiteto: esgotadas todas as tentativas"
    return _transition(state, STATE_FAILED)


def _prd_to_dict(prd) -> dict:
    """Converte DesignerPRD para dict serializável."""
    result = {}
    for k, v in vars(prd).items():
        if hasattr(v, "model_dump"):
            result[k] = v.model_dump()
        elif hasattr(v, "dict"):
            result[k] = v.dict()
        elif isinstance(v, list):
            result[k] = [
                item.model_dump() if hasattr(item, "model_dump") else (
                    item.dict() if hasattr(item, "dict") else item
                )
                for item in v
            ]
        else:
            if isinstance(v, str):
                s2=v.strip()
                if (s2.startswith('{') and s2.endswith('}')) or (s2.startswith('[') and s2.endswith(']')):
                    try: v=__import__(json).loads(s2)
                    except Exception: pass
            result[k] = v
    sections = result.get("sections")
    if isinstance(sections, list):
        result["sections"] = [
            section
            for section in sections
            if str((section or {}).get("name") if isinstance(section, dict) else getattr(section, "name", "")).strip().lower() != "lgpd"
        ]
    variation = result.get("variation_blueprint")
    if isinstance(variation, dict):
        order = variation.get("ordem_das_secoes")
        if isinstance(order, list):
            variation["ordem_das_secoes"] = [item for item in order if str(item).strip().lower() != "lgpd"]
        required = variation.get("required_sections")
        if isinstance(required, list):
            variation["required_sections"] = [item for item in required if str(item).strip().lower() != "lgpd"]
    # normaliza campos que devem ser dict mas vieram como string JSON
    _DICT_FIELDS = {"variation_blueprint","typography","color_palette","media_plan",
        "visual_dna","creative_direction","niche_brief","site_build_plan",
        "requirements_contract","visual_contract","layout_blueprint",
        "design_reference_pack","anti_patterns","schema_org_types",
        "components_21dev","faq_questions","value_props","seo_keywords"}
    for _k in _DICT_FIELDS:
        if _k in result and isinstance(result[_k], str):
            _v = result[_k].strip()
            if (_v.startswith('{') and _v.endswith('}')) or (_v.startswith('[') and _v.endswith(']')):
                try: result[_k] = json.loads(_v)
                except Exception: pass
    # sanitize footer section (evita 'N\u00da QUE...' e footer vazio do chunked merge)
    _f = next((_s for _s in result.get('sections', []) if isinstance(_s, dict) and _s.get('name','').lower() == 'footer'), None)
    if _f and not (_f.get('copy') or _f.get('content') or _f.get('text')):
        _f['copy'] = result.get('business_name','') or ''
        _f['content'] = {'name':'footer', 'business_name': result.get('business_name','')}
    return result
