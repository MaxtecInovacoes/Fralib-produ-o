"""Step: Caio — Fase 2: Qualificação do lead via agente Caio.

Regra de estado (protocolo 2026-08-18):
  - state.lead_data É IMUTÁVEL — Caio NÃO pode alterar/reatribuir.
  - Saída vai EXCLUSIVAMENTE em state.caio_output.
  - Se qualificar_lead() retornar dados, o dict é isolado em caio_output.
"""
import logging
from backend.agents.manager.states import (
    PipelineState, STATE_QUALIFYING, STATE_NICHE_BRIEFING, STATE_FAILED,
    _transition, _log_step_error, _record_agent_handoff,
)

logger = logging.getLogger("manager.pipeline")


def step_caio(state: PipelineState) -> PipelineState:
    """Fase 2: Caio qualifica o lead (score, tier, motivo)."""
    if state.current_state != STATE_QUALIFYING:
        return state

    try:
        from backend.agents.caio import qualificar_lead
        caio_output = qualificar_lead(
            lead=state.lead_data,
            segmento=state.segmento,
            cidade=state.cidade,
        )
        state.caio_output = caio_output
        state.history.append(f"Caio: score={caio_output.score}, tier={caio_output.tier}")
        _record_agent_handoff(
            state,
            "caio",
            received={
                "nome": (state.lead_data or {}).get("nome"),
                "segmento": state.segmento,
                "cidade": state.cidade,
                "rating": (state.lead_data or {}).get("rating"),
            },
            produced={
                "score": getattr(caio_output, "score", None),
                "tier": getattr(caio_output, "tier", None),
                "dark_mode": getattr(caio_output, "dark_mode", None),
                "motivo": getattr(caio_output, "motivo", None),
            },
            notes=["Caio qualifica se o lead pode seguir para briefing e define tier visual/comercial."],
        )
    except Exception as e:
        _log_step_error(state, "Caio", e)
        state.error = f"Caio: {e}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_NICHE_BRIEFING)
