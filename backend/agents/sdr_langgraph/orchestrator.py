"""SDR Orchestrator - ponto de entrada unificado.

Substitui o _next_stage antigo por uma decisao baseada em:
1. Intent (o que o lead quis dizer)
2. State (FSM)
3. Loop detection (lead travado em greeting/ack?)
4. Intent > Stage (intent sempre vence)

Usado pelo agent.py ao final de cada turno do Franz.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .intent_classifier import IntentResult
from .state_machine import (
    ConversationState,
    Intent,
    StateDecision,
    decide_transition,
    detect_loop,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorDecision:
    """Decisao completa do orchestrator para um turno."""
    intent: Intent
    intent_confidence: float
    intent_signals: list[str]
    state_before: ConversationState
    state_after: ConversationState
    stage_before: str
    stage_after: str
    reasoning: str
    should_advance: bool
    in_loop: bool
    force_break_loop: bool  # quando True, Composer deve fazer pergunta direta (sem repetir hook)


def orchestrate(
    incoming_message: str,
    current_state_str: str,
    current_stage: str,
    turn_count: int,
    suggested_stage: Optional[str] = None,
    enable_llm_fallback: bool = False,
) -> OrchestratorDecision:
    """Decide o que fazer com base na mensagem do lead + estado atual.

    Args:
        incoming_message: texto cru do lead.
        current_state_str: estado atual (string, ex: "idle", "waiting_response").
        current_stage: stage legado (ex: "hook", "qualify"). Usado so pra UI.
        turn_count: quantas mensagens o lead ja mandou.
        suggested_stage: stage que o LLM sugeriu no JSON (legado, ignoravel).
        enable_llm_fallback: se True, chama Haiku quando regex nao tem confidence alta.

    Returns:
        OrchestratorDecision com tudo que o caller precisa pra compor a resposta.
    """
    # 1) Parse state atual
    try:
        current_state = ConversationState(current_state_str)
    except ValueError:
        # estado legado nao mapeado (ex: "followup_24h", "scheduled", "pendente_wpp")
        # mantem como WAITING_RESPONSE pra nao quebrar
        if current_state_str in ("opt_out", "lost"):
            current_state = ConversationState.OPT_OUT
        elif current_state_str in ("won", "ganhos"):
            current_state = ConversationState.CLOSED_WON
        elif current_state_str in ("handoff",):
            current_state = ConversationState.HANDED_OFF
        elif current_state_str in ("scheduled",):
            current_state = ConversationState.SCHEDULED
        else:
            current_state = ConversationState.IDLE

    # 2) Detecta loop (lead travado em greeting/ack sem avancar)
    # turn_count = quantas mensagens o lead JA mandou. Loop so a partir do turno 3.
    in_loop = detect_loop(turn_count, current_state)
    force_break_loop = in_loop

    # 3) Classifica intent (regex only - sem fallback LLM)
    from .intent_classifier import classify_intent
    intent_result = classify_intent(incoming_message, message_count=turn_count + 1)

    # 4) Decide transicao via FSM
    decision: StateDecision = decide_transition(
        current_state=current_state,
        intent=intent_result.intent,
        suggested_stage=suggested_stage,
        turn_count=turn_count + 1,
    )

    # 5) Override de loop: se detectou loop E intent continua sendo GREETING/ACKNOWLEDGMENT,
    # força transicao pra ENGAGED+qualify. O Composer vai ter que fazer uma pergunta direta
    # (ex: "Olha, sem enrrolacao: voce e o dono?") pra quebrar o loop.
    if in_loop and intent_result.intent in (Intent.GREETING, Intent.ACKNOWLEDGMENT, Intent.UNKNOWN):
        logger.info(
            f"[orchestrator] Loop detectado: state={current_state}, turn={turn_count}, "
            f"intent={intent_result.intent}. Forcando transicao pra qualify."
        )
        decision = StateDecision(
            new_state=ConversationState.ENGAGED,
            new_stage="qualify",
            intent=intent_result.intent,
            confidence=0.7,
            reasoning=f"loop detectado apos {turn_count} turnos sem progresso; forcar qualify",
            should_advance=True,
        )

    return OrchestratorDecision(
        intent=intent_result.intent,
        intent_confidence=intent_result.confidence,
        intent_signals=intent_result.signals,
        state_before=current_state,
        state_after=decision.new_state,
        stage_before=current_stage,
        stage_after=decision.new_stage,
        reasoning=decision.reasoning,
        should_advance=decision.should_advance,
        in_loop=in_loop,
        force_break_loop=force_break_loop,
    )


def update_lead_memory_after_turn(
    memory,  # LeadMemory instance (Pydantic)
    orchestrator_decision: OrchestratorDecision,
) -> None:
    """Atualiza a LeadMemory com a decisao do orchestrator.

    Args:
        memory: LeadMemory (mutated in place).
        orchestrator_decision: decisao do orchestrator.
    """
    memory.conversation_state = orchestrator_decision.state_after.value
    memory.stage = orchestrator_decision.stage_after
    memory.turn_count = (memory.turn_count or 0) + 1
    memory.last_intent = orchestrator_decision.intent.value
    memory.last_intent_confidence = orchestrator_decision.intent_confidence
    memory.last_lead_response_at = datetime.now(timezone.utc).isoformat()
    # Atualiza last_message_received pra usar nas proximas composicoes
    # (mas o agent.py cuida disso via update_history; aqui so metadados de estado)