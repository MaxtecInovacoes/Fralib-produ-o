"""Manager agent — orquestrador supervisor (FSM pura em Python).

Coordena a esteira canonica:
  Hunter → Caio → Arquiteto → Builder → Quality Gate v2 (Vision) → Deploy → Franz

Cada agente retorna output estruturado. O Manager valida, decide retry ou avança.
State central persiste entre transicoes (em memoria).

Este arquivo e o barrel publico — re-exports de todos os submodulos.
"""
import os
from backend.agents.pipeline_checkpoint import gerar_pipeline_id, salvar_checkpoint, get_dados_agente, resumo_checkpoint

# Feature flag: usa Quality Gate v2 (Playwright + Vision) em vez do v1 (regex)
USE_QA_V2 = os.getenv("FRALIB_QA_V2", "true").lower() in ("1", "true", "yes")

# Import states, constants, and helpers
from backend.agents.manager.states import (
    PipelineState,
    STATE_INIT,
    STATE_HUNTING,
    STATE_QUALIFYING,
    STATE_NICHE_BRIEFING,
    STATE_DIRECTING,
    STATE_VARIATING,
    STATE_DESIGNING,
    STATE_BUILDING,
    STATE_VALIDATING,
    STATE_PUBLISHING,
    STATE_OUTREACH,
    STATE_DONE,
    STATE_FAILED,
    _transition,
    _validate_required_fields,
    _is_transient_llm_error,
    _log_step_error,
)

# Import step functions
from backend.agents.manager.step_hunter import step_hunter
from backend.agents.manager.step_caio import step_caio
from backend.agents.manager.step_nicho import step_nicho
from backend.agents.manager.step_design_director import step_design_director
from backend.agents.manager.step_variacao import step_variacao
from backend.agents.manager.step_arquiteto import step_arquiteto
from backend.agents.manager.step_builder import step_builder
from backend.agents.manager.step_quality_gate import step_quality_gate
from backend.agents.manager.step_deploy import step_deploy
from backend.agents.manager.step_franz import step_franz

# Pipeline completa (lista de steps em ordem)
PIPELINE_STEPS = [
    step_hunter,
    step_caio,
    step_nicho,
    step_design_director,
    step_variacao,
    step_arquiteto,
    step_builder,
    step_quality_gate,
    step_deploy,
    step_franz,
]

logger = __import__("logging").getLogger("manager.pipeline")


def _save_resume_checkpoint(state: PipelineState) -> None:
    """Persiste PRD/HTML disponiveis para retomada em retries futuros."""
    if not state.tenant_id or not state.lead_id:
        return
    try:
        pipeline_id = gerar_pipeline_id(
            state.tenant_id,
            state.lead_data.get("nome", "") if state.lead_data else "",
            state.segmento,
            state.cidade,
            state.lead_id,
        )
        if state.design_output and state.design_output.get("business_name"):
            salvar_checkpoint(pipeline_id, "arquiteto", {"prd_json": state.design_output})
        if state.build_output and state.build_output.get("html"):
            salvar_checkpoint(pipeline_id, "builder", state.build_output)
    except Exception as exc:
        logger.warning("[Checkpoint] persistencia final falhou lead_id=%s: %s", state.lead_id, exc)


def _hydrate_from_checkpoint(state: PipelineState) -> PipelineState:
    """Retoma pipeline do checkpoint: restaura dados de etapas concluídas e avança o state."""
    if not state.tenant_id or not state.lead_id:
        return state
    if getattr(state, "forcar_renovacao", False):
        state.history.append("Checkpoint: ignorado por renovacao forcada")
        return state

    try:
        pipeline_id = gerar_pipeline_id(
            state.tenant_id,
            state.lead_data.get("nome", "") if state.lead_data else "",
            state.segmento,
            state.cidade,
            state.lead_id,
        )
        resumo = resumo_checkpoint(pipeline_id)
        if resumo == "nenhum checkpoint":
            return state

        # Hunter: se já rodou, restaura seus dados e avança para QUALIFYING
        hunter_cached = get_dados_agente(pipeline_id, "hunter")
        if hunter_cached and state.current_state == STATE_HUNTING:
            state.lead_data = state.lead_data or hunter_cached.get("lead_data", {})
            state.seo_intel = hunter_cached.get("seo_intel") or state.seo_intel
            state.jina_insights = hunter_cached.get("jina_insights") or state.jina_insights
            state.history.append(f"Checkpoint: Hunter reutilizado; pulando para Qualifying ({resumo})")
            return _transition(state, STATE_QUALIFYING)

        # Builder: se já tem HTML, avança direto para Quality Gate
        builder_cached = get_dados_agente(pipeline_id, "builder")
        if builder_cached and builder_cached.get("html"):
            state.build_output = builder_cached
            state.history.append(f"Checkpoint: Builder reutilizado; retomando em Quality Gate ({resumo})")
            return _transition(state, STATE_VALIDATING)

        # Arquiteto: se já tem PRD, avança para Builder
        arquiteto_cached = get_dados_agente(pipeline_id, "arquiteto")
        prd_json = (arquiteto_cached or {}).get("prd_json")
        if prd_json and prd_json.get("business_name"):
            state.design_output = prd_json
            state.history.append(f"Checkpoint: PRD reutilizado; retomando em Builder ({resumo})")
            return _transition(state, STATE_BUILDING)
    except Exception as exc:
        logger.warning("[Checkpoint] retomada falhou lead_id=%s: %s", state.lead_id, exc)

    return state


def run_pipeline(state: PipelineState, trace: object = None) -> PipelineState:
    """Executa toda a pipeline com suporte a retry.

    O loop externo (while) permite que o Quality Gate retorne ao Builder
    quando o score for insuficiente. O loop interno (for) percorre os steps
    em ordem. Quando o Quality Gate seta state=BUILDING, o loop externo
    reinicia para que step_builder seja re-executado.

    O Quality Gate tem contador de attempts interno (max 3), entao nao ha
    risco de loop infinito.

    Custo: tracking via token_tracker existente.

    trace: opcional — instancia de observability.Trace para spans de fase.
    """
    try:
        state = _hydrate_from_checkpoint(state)
        max_passes = 10  # safety contra loop inesperado
        passes = 0
        _t = trace
        while state.current_state not in (STATE_DONE, STATE_FAILED) and passes < max_passes:
            passes += 1
            prev_state = state.current_state
            for step in PIPELINE_STEPS:
                # Observability: iniciar span para este step
                if _t is not None:
                    step_name = step.__name__.replace("step_", "")
                    span = _t.iniciar_span(f"step_{step_name}", step_name, "")
                state = step(state)
                # Observability: finalizar span
                if _t is not None:
                    _span = _t.span_atual()
                    if _span and _span.nome == f"step_{step_name}":
                        s = "success" if state.current_state not in (STATE_FAILED,) else "error"
                        _span.finalizar(s)
                # Atualiza phase/agent conforme transicao do pipeline
                new_state = state.current_state
                if new_state != prev_state:
                    phase_map = {
                        STATE_HUNTING: "hunting",
                        STATE_QUALIFYING: "qualifying",
                        STATE_NICHE_BRIEFING: "niche_briefing",
                        STATE_DIRECTING: "directing",
                        STATE_VARIATING: "variating",
                        STATE_DESIGNING: "designing",
                        STATE_BUILDING: "building",
                        STATE_VALIDATING: "validating",
                        STATE_OUTREACH: "outreach",
                        STATE_DONE: "done",
                        STATE_FAILED: "failed",
                    }
                    agent_map = {
                        STATE_HUNTING: "hunter",
                        STATE_QUALIFYING: "caio",
                        STATE_NICHE_BRIEFING: "agente_nicho",
                        STATE_DIRECTING: "design_director",
                        STATE_VARIATING: "agente_variacao",
                        STATE_DESIGNING: "arquiteto",
                        STATE_BUILDING: "builder",
                        STATE_VALIDATING: "qa_vision",
                        STATE_OUTREACH: "franz",
                        STATE_DONE: "manager",
                        STATE_FAILED: "manager",
                    }
                    prev_state = new_state
                if state.current_state in (STATE_DONE, STATE_FAILED):
                    break
        if passes >= max_passes:
            logger.error("run_pipeline esgotou passes (%s) sem completar", max_passes)
            if not state.error:
                state.error = f"pipeline estagnou apos {max_passes} passes"
            state = _transition(state, STATE_FAILED)
        return state
    finally:
        _save_resume_checkpoint(state)
        # 2.1 Deduzir creditos por custo real do pipeline (fail-safe)
        try:
            from backend.services.credits_manager import deduzir_creditos_por_pipeline
            from backend.core.database import SessionLocal
            if state.tenant_id and state.run_id:
                _db = SessionLocal()
                try:
                    result = deduzir_creditos_por_pipeline(
                        db=_db,
                        tenant_id=state.tenant_id,
                        run_id=state.run_id,
                    )
                    logger.info(
                        "[credits_manager] pipeline run_id=%s tenant_id=%d deduzidos=%d custo_usd=%.4f ok=%s",
                        state.run_id, state.tenant_id, result.get("deduzidos", 0), result.get("custo_usd", 0.0), result.get("ok"),
                    )
                finally:
                    _db.close()
            else:
                result = None
        except Exception as exc:
            logger.warning("[credits_manager] deducao no run_pipeline falhou run_id=%s: %s", state.run_id, exc)
