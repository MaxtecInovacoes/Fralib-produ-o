"""Step: Caio — Fase 2: Qualificação do lead via agente Caio."""
import logging
import traceback
from backend.agents.manager.states import (
    PipelineState, STATE_QUALIFYING, STATE_NICHE_BRIEFING, STATE_FAILED,
    _transition, _log_step_error,
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
    except Exception as e:
        _log_step_error(state, "Caio", e)
        state.error = f"Caio: {e}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_NICHE_BRIEFING)
