"""Step: Nicho — gera briefing de nicho antes da direção criativa."""
import logging

from backend.agents.manager.states import (
    PipelineState,
    STATE_NICHE_BRIEFING,
    STATE_DIRECTING,
    STATE_FAILED,
    _transition,
    _log_step_error,
    _record_visual_custody,
    _record_agent_handoff,
)

logger = logging.getLogger("manager.pipeline")


def step_nicho(state: PipelineState) -> PipelineState:
    if state.current_state != STATE_NICHE_BRIEFING:
        return state

    try:
        from backend.agents.agente_nicho import gerar_briefing

        briefing = gerar_briefing(
            dados_lead=state.lead_data or {},
            segmento=state.segmento,
            cidade=state.cidade,
            jina_insights=(state.lead_data or {}).get("jina_insights", ""),
            task_id=state.run_id,
        )
        state.niche_brief = briefing.model_dump() if hasattr(briefing, "model_dump") else briefing.dict()
        state.history.append(f"Nicho: briefing OK ({state.niche_brief.get('confianca', 'media')})")
        _record_visual_custody(
            state,
            "niche_brief",
            received_decisions={
                "segmento": state.segmento,
                "cidade": state.cidade,
                "jina_insights": bool((state.lead_data or {}).get("jina_insights")),
                "reviews": len((state.lead_data or {}).get("reviews") or []),
            },
            preserved_decisions={
                "audience": state.niche_brief.get("publico_alvo", []),
                "positioning": state.niche_brief.get("usp", []),
                "tone": state.niche_brief.get("tom_de_voz", ""),
                "keywords": state.niche_brief.get("keywords", []),
            },
        )
        _record_agent_handoff(
            state,
            "niche_brief",
            received={
                "segmento": state.segmento,
                "cidade": state.cidade,
                "jina_insights_present": bool((state.lead_data or {}).get("jina_insights")),
                "lead_name": (state.lead_data or {}).get("nome"),
            },
            produced=state.niche_brief,
            preserved={
                "nicho": state.niche_brief.get("nicho"),
                "tom_de_voz": state.niche_brief.get("tom_de_voz"),
                "keywords": state.niche_brief.get("keywords", []),
            },
        )
        _write_artifact(state, "02-niche-brief.json", state.niche_brief, "niche_brief")
    except Exception as exc:
        _log_step_error(state, "Nicho", exc)
        state.error = f"Nicho: {exc}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_DIRECTING)


def _write_artifact(state: PipelineState, filename: str, payload: dict, step: str) -> None:
    try:
        from backend.agents.artifact_store import write_json_artifact

        write_json_artifact(
            run_id=state.run_id,
            lead_id=state.lead_id,
            lead_name=(state.lead_data or {}).get("nome", ""),
            filename=filename,
            payload=payload,
            metadata={"step": step, "tenant_id": state.tenant_id},
        )
    except Exception as exc:
        logger.warning("[%s] artifact falhou (lead=%s): %s", step, state.lead_id, exc)
