"""Step: Hunter — Fase 1: Mineração de leads do banco."""
import logging
from backend.agents.manager.states import (
    PipelineState, STATE_HUNTING, STATE_QUALIFYING, STATE_FAILED,
    _transition, _validate_required_fields, _log_step_error,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")


def step_hunter(state: PipelineState) -> PipelineState:
    """Fase 1: Hunter valida dados do lead e pesquisa mercado (Jina best-effort)."""
    if state.current_state != STATE_HUNTING:
        return state

    lead = state.lead_data
    if not lead:
        state.error = "lead_data vazio — Hunter não tem dados para processar"
        return _transition(state, STATE_FAILED)

    ok, msg = _validate_required_fields(lead, ["nome", "cidade", "telefone"])
    if not ok:
        state.error = f"Hunter: {msg}"
        return _transition(state, STATE_FAILED)

    # Jina research (best-effort — não bloqueia pipeline se falhar)
    try:
        from backend.services.jina_service import pesquisar_mercado
        jina_result = pesquisar_mercado(
            segmento=state.segmento,
            cidade=state.cidade,
            nome_negocio=lead.get("nome", ""),
        )
        if jina_result:
            state.lead_data.setdefault("jina_insights", jina_result)
            logger.info("[Hunter] Jina research OK para %s (%s)", lead.get("nome"), state.cidade)
    except Exception as e:
        logger.warning("[Hunter] Jina research falhou (não-bloqueante): %s", e)

    # Knowledge Journal: market_analyzed
    try:
        journal_record(
            project_id=state.lead_id,
            event_type="market_analyzed",
            hypothesis=f"Lead {lead.get('nome')} em {state.cidade} validado pelo Hunter",
            payload={
                "segmento": state.segmento,
                "cidade": state.cidade,
                "telefone": lead.get("telefone", ""),
            },
        )
    except Exception as exc:
        logger.warning("[Hunter] journal market_analyzed falhou (lead=%s): %s", state.lead_id, exc)

    state.history.append(f"Hunter: lead validado — {lead.get('nome')} ({state.cidade})")
    return _transition(state, STATE_QUALIFYING)
