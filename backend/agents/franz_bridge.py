"""
Bridge de integração entre o novo sistema LangGraph e o SDR/Franz existente.

Este módulo conecta:
- Novo memory system (Core/Warm/Cold)
- Sistema de routing inteligente
- Error handling avançado

Com:
- SDR LangGraph existente (sdr_langgraph/)
- LeadMemory do Franz
- Handoff para closer
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .langgraph.memory import MemoryManager, get_memory_manager
from .langgraph.router import AgentRouter, IntentDetector
from .langgraph.error_handler import ErrorHandler, get_error_handler

log = logging.getLogger("franz_bridge")

# Global instances
_memory_manager = get_memory_manager()
_router = AgentRouter()
_error_handler = get_error_handler()


def sync_memory_to_sdr(memory_data: Dict[str, Any], session_id: str, user_id: int) -> Dict[str, Any]:
    """
    Sincroniza dados entre o novo memory system e a LeadMemory do SDR.

    Args:
        memory_data: Dados do LeadMemory (do SDR)
        session_id: ID da sessão
        user_id: ID do tenant

    Returns:
        Dados sincronizados
    """
    try:
        # Extrair informações relevantes
        agent_type = memory_data.get("active_agent", "atendimento")
        nicho = memory_data.get("segmento", "general")
        lead_id = memory_data.get("lead_id", session_id)

        # Adicionar experiência ao memory manager
        if memory_data.get("stage"):
            experience_content = f"Stage: {memory_data['stage']}"

            # Detectar se foi sucesso
            stage = memory_data.get("stage", "")
            success = stage in ["won", "scheduled", "close"]

            _memory_manager.add_experience(
                session_id=session_id,
                agent_type=agent_type,
                nicho=nicho,
                content=experience_content,
                confidence=0.7 if success else 0.4,
                tags=["sdr", "stage_transition"] if success else ["sdr", "stage_failed"],
                source="sdr_sync"
            )

        # Adicionar notas do agente
        agent_notes = memory_data.get("agent_notes", {})
        for agent_key, note in agent_notes.items():
            if note:
                _memory_manager.add_experience(
                    session_id=session_id,
                    agent_type=agent_key,
                    nicho=nicho,
                    content=note[:200],
                    confidence=0.6,
                    tags=["agent_note"],
                    source="sdr_note_sync"
                )

        # Atualizar memória com contexto do SDR
        updated_data = memory_data.copy()

        # Buscar contexto relevante do memory manager
        memory_context = _memory_manager.get_memory_context(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho
        )

        updated_data["_memory_context"] = memory_context

        return updated_data

    except Exception as e:
        log.error(f"[Bridge] Erro ao sincronizar memória SDR: {e}")
        return memory_data


def get_sdr_routing_context(session_id: str, user_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtém contexto de routing para o SDR baseado no memory system.

    Args:
        session_id: ID da sessão
        user_id: ID do tenant
        lead_data: Dados do lead

    Returns:
        Contexto de routing com sugestões de agente
    """
    try:
        agent_type = lead_data.get("active_agent", "atendimento")
        nicho = lead_data.get("segmento", "general")
        stage = lead_data.get("stage", "hook")

        # Obter memória relevante
        memory_context = _memory_manager.get_memory_context(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho
        )

        # Calcular confiança baseada na memória
        confidence = 0.5
        if memory_context["core_entries_count"] > 0:
            confidence += 0.2
        if memory_context["warm_entries_count"] > 0:
            confidence += 0.1

        # Obter decisão de routing
        from .langgraph.state import AgentType, create_initial_state

        state = create_initial_state(lead_data, session_id)
        state["current_agent"] = agent_type
        state["conversation_stage"] = stage

        # Simular routing
        last_msg = lead_data.get("last_message_received", "")
        next_agent, reason = _router.determine_next_agent(state, last_msg)

        return {
            "recommended_agent": next_agent.value,
            "routing_reason": reason,
            "confidence": confidence,
            "memory_context": memory_context,
            "stage": stage,
            "nicho": nicho,
        }

    except Exception as e:
        log.error(f"[Bridge] Erro ao obter contexto de routing: {e}")
        return {
            "recommended_agent": lead_data.get("active_agent", "atendimento"),
            "routing_reason": "fallback",
            "confidence": 0.5,
            "memory_context": {},
            "stage": lead_data.get("stage", "hook"),
            "nicho": lead_data.get("segmento", "general"),
        }


def handle_sdr_error(error: Exception, state: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Trata erros do SDR usando o error handler do novo sistema.

    Args:
        error: Exceção ocorrida
        state: Estado atual do SDR
        session_id: ID da sessão

    Returns:
        Contexto do erro com recomendações
    """
    try:
        # Criar estado temporário para o error handler
        from .langgraph.state import create_initial_state

        temp_state = create_initial_state(state, session_id)
        temp_state["current_agent"] = state.get("active_agent", "atendimento")
        temp_state["attempt_count"] = state.get("attempts", 0)

        # Processar erro
        error_context = _error_handler.handle_error(error, temp_state)

        return {
            "error_type": error_context.error_type.value,
            "severity": error_context.severity.value,
            "recovery_action": error_context.recovery_actions[-1] if error_context.recovery_actions else "fallback",
            "should_escalate": _error_handler.should_escalate(temp_state),
            "circuit_breaker_state": _error_handler.circuit_breaker.get_state(),
            "error_message": str(error),
        }

    except Exception as e:
        log.error(f"[Bridge] Erro ao processar erro SDR: {e}")
        return {
            "error_type": "unknown",
            "severity": "high",
            "recovery_action": "escalate_to_supervisor",
            "should_escalate": True,
            "error_message": str(error),
        }


def record_sdr_interaction(
    session_id: str,
    user_id: int,
    lead_data: Dict[str, Any],
    user_message: str,
    agent_response: str,
    stage: str,
    success: bool
) -> None:
    """
    Registra uma interação do SDR no memory system.

    Args:
        session_id: ID da sessão
        user_id: ID do tenant
        lead_data: Dados do lead
        user_message: Mensagem do lead
        agent_response: Resposta do agente
        stage: Estágio atual
        success: Se a interação foi bem sucedida
    """
    try:
        agent_type = lead_data.get("active_agent", "atendimento")
        nicho = lead_data.get("segmento", "general")

        # Registrar interação completa
        interaction = f"Lead: {user_message[:100]}\nAgent: {agent_response[:100]}"
        _memory_manager.record_interaction(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho,
            interaction=interaction,
            success=success
        )

        # Adicionar experiência específica do SDR
        _memory_manager.add_experience(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho,
            content=f"Stage {stage}: {agent_response[:150]}",
            confidence=0.8 if success else 0.3,
            tags=["sdr_interaction", f"stage_{stage}"] if success else ["sdr_interaction", "failed"],
            source="sdr_interaction"
        )

    except Exception as e:
        log.error(f"[Bridge] Erro ao registrar interação SDR: {e}")


def enrich_sdr_state_with_memory(
    sdr_state: Dict[str, Any],
    session_id: str,
    user_id: int
) -> Dict[str, Any]:
    """
    Enriquece o estado do SDR com contexto do memory system.

    Args:
        sdr_state: Estado atual do SDR
        session_id: ID da sessão
        user_id: ID do tenant

    Returns:
        Estado enriquecido com memória
    """
    try:
        agent_type = sdr_state.get("active_agent", "atendimento")
        nicho = sdr_state.get("segmento", sdr_state.get("sdr_stage", "general"))

        # Obter contexto de memória
        memory_context = _memory_manager.get_memory_context(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho
        )

        # Adicionar ao estado
        enriched = sdr_state.copy()
        enriched["_memory_context"] = memory_context
        enriched["_memory_tokens"] = memory_context.get("total_tokens", 0)
        enriched["_memory_entries"] = memory_context.get("core_entries_count", 0)

        return enriched

    except Exception as e:
        log.error(f"[Bridge] Erro ao enriquecer estado SDR: {e}")
        return sdr_state


def get_intent_from_message(message: str) -> Dict[str, Any]:
    """
    Detecta intent de uma mensagem usando o router do novo sistema.

    Args:
        message: Mensagem do lead

    Returns:
        Dicionário com intent e confiança
    """
    try:
        detector = IntentDetector()
        intent = detector.detect_intent(message)

        return {
            "intent": intent,
            "confidence": 0.8,
            "message": message[:100],
        }

    except Exception as e:
        log.error(f"[Bridge] Erro ao detectar intent: {e}")
        return {
            "intent": "other",
            "confidence": 0.5,
            "message": message[:100],
        }


def calculate_lead_complexity_for_sdr(lead_data: Dict[str, Any]) -> str:
    """
    Calcula complexidade do lead para seleção de modelo.

    Args:
        lead_data: Dados do lead

    Returns:
        Complexidade: 'simples', 'medio', ou 'complexo'
    """
    try:
        from .langgraph.state import AgentConfig

        config = AgentConfig()
        complexity = config.calculate_complexity(lead_data)

        return complexity.value

    except Exception as e:
        log.error(f"[Bridge] Erro ao calcular complexidade: {e}")
        return "medio"


# ════════════════════════════════════════════════════════════════════
# WATCHDOG SYNC
# ════════════════════════════════════════════════════════════════════

def should_block_outbound_sdr(session_id: str, user_id: int, current_stage: str) -> tuple[bool, str]:
    """
    Verifica se deve bloquear mensagem outbound baseado no memory system.

    Args:
        session_id: ID da sessão
        user_id: ID do tenant
        current_stage: Estágio atual do SDR

    Returns:
        (should_block, reason)
    """
    try:
        # Buscar experiências recentes
        from .langgraph.memory import WarmMemory

        warm_memory = WarmMemory()
        nicho = "general"  # Em produção, pegar do lead

        recent_entries = warm_memory.search_entries(
            nicho=nicho,
            agent_type="abordagem",
            min_confidence=0.3,
            limit=3
        )

        # Verificar se houve falha recente
        for entry in recent_entries:
            if entry.failure_count > 0:
                recent_failures = entry.failure_count / max(1, entry.usage_count)
                if recent_failures > 0.5:
                    return True, f"high_failure_rate_{entry.id[:8]}"

        # Verificar circuit breaker
        if _error_handler.circuit_breaker.get_state() == "open":
            return True, "circuit_breaker_open"

        return False, ""

    except Exception as e:
        log.error(f"[Bridge] Erro no watchdog: {e}")
        return False, ""


# ════════════════════════════════════════════════════════════════════
# CLOSER HANDOFF INTEGRATION
# ════════════════════════════════════════════════════════════════════

def prepare_closer_handoff_context(
    session_id: str,
    user_id: int,
    lead_data: Dict[str, Any],
    history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Prepara contexto enriquecido para handoff ao closer humano.

    Args:
        session_id: ID da sessão
        user_id: ID do tenant
        lead_data: Dados do lead
        history: Histórico de mensagens

    Returns:
        Contexto enriquecido para o closer
    """
    try:
        agent_type = lead_data.get("active_agent", "vendas")
        nicho = lead_data.get("segmento", "general")

        # Obter memória do vendedor
        memory_context = _memory_manager.get_memory_context(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho
        )

        # Calcular score baseado na memória
        memory_score = 0
        if memory_context["core_entries_count"] > 0:
            memory_score += 25
        if memory_context["warm_entries_count"] > 0:
            memory_score += 15

        # Score BANT do lead_data
        bant_score = 0
        if lead_data.get("bant_budget"):
            bant_score += 10
        if lead_data.get("bant_authority"):
            bant_score += 5
        bant_score += lead_data.get("bant_need_score", 0)
        if lead_data.get("bant_timeline"):
            bant_score += 10

        return {
            "session_id": session_id,
            "user_id": user_id,
            "lead_id": lead_data.get("lead_id", ""),
            "lead_nome": lead_data.get("nome", ""),
            "lead_telefone": lead_data.get("telefone", ""),
            "stage": lead_data.get("stage", ""),
            "temperature": lead_data.get("lead_temperature", "morno"),
            "bant_score": bant_score,
            "memory_score": memory_score,
            "total_score": bant_score + memory_score,
            "memory_context": memory_context,
            "pain_identified": lead_data.get("pain_identified", ""),
            "main_objection": lead_data.get("main_objection", ""),
            "agent_notes": lead_data.get("agent_notes", {}),
            "recent_interactions": history[-5:] if history else [],
            "recommended_action": "call" if memory_score > 30 else "whatsapp",
        }

    except Exception as e:
        log.error(f"[Bridge] Erro ao preparar handoff: {e}")
        return {
            "session_id": session_id,
            "user_id": user_id,
            "lead_id": lead_data.get("lead_id", ""),
            "lead_nome": lead_data.get("nome", ""),
            "lead_telefone": lead_data.get("telefone", ""),
            "stage": lead_data.get("stage", ""),
            "memory_context": {},
            "error": str(e),
        }