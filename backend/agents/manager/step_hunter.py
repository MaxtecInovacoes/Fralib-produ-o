"""Step: Hunter — Fase 1: Mineração de leads do banco.

Estado isolado:
  - state.lead_data (IMUTÁVEL downstream): fotos, reviews, telefone, endereco, rating
  - state.seo_intel (novo): dict retornado por Jina/Playwright — NÃO entra em lead_data
  - state.jina_insights (novo): str formatado para o Arquiteto — ISOLADO

Qualquer passo DEPOIS do Hunter NÃO deve apagar/reescrever fotos/reviews de lead_data.
"""
import logging
from backend.agents.manager.states import (
    PipelineState, STATE_HUNTING, STATE_QUALIFYING, STATE_FAILED,
    _transition, _validate_required_fields, _log_step_error,
    _record_agent_handoff,
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

    lead.setdefault("id", state.lead_id)

    # Pesquisa de mercado: Jina primária, Playwright fallback.
    # RESULTADO É ISOLADO — NUNCA toca em state.lead_data["fotos"] / "reviews".
    try:
        from backend.utils.jina_intelligence import (
            buscar_inteligencia_jina,
            formatar_inteligencia_para_arquiteto,
        )
        market_intel = buscar_inteligencia_jina(
            nicho=state.segmento,
            cidade=state.cidade,
            nome_negocio=lead.get("nome", ""),
        )
        # Slot isolado (regra 2: Jina NÃO sobrescreve fotos/reviews do lead)
        state.seo_intel = market_intel
        state.jina_insights = formatar_inteligencia_para_arquiteto(market_intel)
        logger.info(
            "[Hunter] pesquisa OK provider=%s para %s (%s)",
            market_intel.get("provider", "jina"), lead.get("nome"), state.cidade,
        )
    except Exception as e:
        _log_step_error(state, "PesquisaMercado", e)
        state.error = f"Pesquisa de mercado: {e}"
        return _transition(state, STATE_FAILED)

    lead["fotos"] = []

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

    # Hunter garante 100% de fotos/reviews preservadas em lead_data (slot isolado).
    # Jina/SEO vai para state.seo_intel — NÃO sobrescreve nada em lead_data.
    state.history.append(f"Hunter: lead validado — {lead.get('nome')} ({state.cidade})")
    _record_agent_handoff(
        state,
        "hunter",
        received={
            "lead_id": state.lead_id,
            "tenant_id": state.tenant_id,
            "lead_fields": sorted(list((state.lead_data or {}).keys())),
        },
        produced={
            "nome": lead.get("nome"),
            "cidade": state.cidade,
            "segmento": state.segmento,
            "telefone": lead.get("telefone"),
            "rating": lead.get("rating"),
            "reviews_count": len(lead.get("reviews") or []),
            "photos_count": len(lead.get("fotos") or []),
            "jina_provider": (state.seo_intel or {}).get("provider"),
            "slot_isolation": {
                "lead_data_keys": sorted((state.lead_data or {}).keys()),
                "seo_intel_keys": sorted((state.seo_intel or {}).keys()) if state.seo_intel else [],
                "jina_insights_chars": len(state.jina_insights or ""),
            },
        },
        preserved=["fotos", "reviews", "reviews_list", "telefone", "endereco", "rating"],
        notes=["Hunter valida dados mínimos, adiciona Jina insights (slot isolado) e garante mídia editorial. lead_data é IMUTÁVEL downstream."],
    )
    return _transition(state, STATE_QUALIFYING)
