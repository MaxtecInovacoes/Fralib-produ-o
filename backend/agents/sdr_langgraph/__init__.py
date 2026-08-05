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

from .agent import SDRGraph, get_sdr_graph
from .state import SDRState, LeadMemory, StageEnum
from .compat import (
    iniciar_contato,
    responder_lead,
    followup_automatico,
    gerar_followup,
    BryanInput,
    BryanOutput,
    FranzInput,
    FranzOutput,
    ESTADOS_SDR,
    ESTADO_TO_STAGE,
    _HORARIO_CACHE,
    _dentro_do_horario,
    _escolher_variante,
    _agent_name_for_user,
    _get_horario_config,
    _get_sdr_settings_for_user,
)

__all__ = [
    "SDRGraph",
    "get_sdr_graph",
    "SDRState",
    "LeadMemory",
    "StageEnum",
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
]
