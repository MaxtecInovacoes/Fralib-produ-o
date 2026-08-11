"""Step: Arquiteto — Fase 3: Geração de PRD (DesignerPRD) via Managed Agent."""
import logging
import os
import time
import json
from backend.agents.manager.states import (
    PipelineState, STATE_DESIGNING, STATE_BUILDING, STATE_FAILED,
    _transition, _is_transient_llm_error, _log_step_error,
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
                from backend.services.keyword_research import pesquisar_keywords
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
            )

            if prd and hasattr(prd, "business_name"):
                state.design_output = _prd_to_dict(prd)
                state.history.append(f"Arquiteto: PRD OK ({len(state.design_output.get('sections', []))} seções)")

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
            _log_step_error(state, "Arquiteto", e)
            state.error = f"Arquiteto: {e}"
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
            result[k] = v
    return result
