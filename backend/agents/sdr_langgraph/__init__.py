"""
═══════════════════════════════════════════════════════════════════════════════
                    SDR LANGGRAPH AGENT (FRANZ)
                        Substitui o bryan.py
═══════════════════════════════════════════════════════════════════════════════

POR QUE LANGGRAPH:
- Estados explícitos (cada stage é um node, não um palpite do LLM)
- Transições validadas (não pula stages)
- Memória persistente nativa (langgraph.checkpoint)
- Cada node tem responsabilidade clara e testável
- Lógica de negócio separada do prompt (regras no código, não na LLM)
- Suporta human-in-the-loop (se lead pede humano, handoff claro)

ARQUITETURA:
    User message → load_memory → detect_intent → [branch by intent] →
    → stage_node (hook/qualify/pain/...) → guard_check → save_memory →
    → send_response

STAGES:
    hook → qualify → pain → amplify → tease → proof → reveal → feedback → close
    + off_topic, gatekeeper, schedule, opt_out, followup, scheduled
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

_AGENT_EXPORTS = {
    "SDRGraph",
    "get_sdr_graph",
}

_STATE_EXPORTS = {
    "SDRState",
    "LeadMemory",
    "StageEnum",
}

_COMPAT_EXPORTS = {
    "iniciar_contato",
    "responder_lead",
    "followup_automatico",
    "gerar_followup",
    "BryanInput",
    "BryanOutput",
    "FranzInput",
    "FranzOutput",
    "ESTADOS_SDR",
    "ESTADO_TO_STAGE",
    "_HORARIO_CACHE",
    "_dentro_do_horario",
    "_escolher_variante",
    "_agent_name_for_user",
    "_get_horario_config",
    "_get_sdr_settings_for_user",
}

__all__ = sorted(_AGENT_EXPORTS | _STATE_EXPORTS | _COMPAT_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load the heavy LangGraph agent only when the caller asks for it.

    Lightweight imports such as ``sdr_langgraph.lead_lock`` must not import
    LangGraph. That keeps cron/provider tests and operational helpers from
    failing because of unrelated LLM agent dependencies.
    """
    if name in _AGENT_EXPORTS:
        from . import agent as _agent

        value = getattr(_agent, name)
    elif name in _STATE_EXPORTS:
        from . import state as _state

        value = getattr(_state, name)
    elif name in _COMPAT_EXPORTS:
        from . import compat as _compat

        value = getattr(_compat, name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    globals()[name] = value
    return value
