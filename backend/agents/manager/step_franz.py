"""Step: Franz — Fase 7: Outreach via SDR WhatsApp."""
import logging
from backend.agents.manager.states import (
    PipelineState, STATE_OUTREACH, STATE_DONE, STATE_FAILED,
    _transition, _log_step_error,
)

logger = logging.getLogger("manager.pipeline")


def step_franz(state: PipelineState) -> PipelineState:
    """Fase 7: Franz outreach — marca lead como concluido.

    O outreach real via WhatsApp e delegado ao cron dispatcher
    (leads WHERE status='concluido' AND sdr_stage='pendente_wpp').
    """
    if state.current_state != STATE_OUTREACH:
        return state

    state.history.append(f"Franz: lead marcado como concluido, site_url={state.deploy_url}")
    return _transition(state, STATE_DONE)
