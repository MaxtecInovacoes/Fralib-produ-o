"""
Agent Router - Determine next agent based on conversation state and intent
"""

import re
from typing import Dict, List, Tuple
from .state import AgentType, AgentState, ConversationStage, LeadComplexity
from .profiles import get_stage_agent


class IntentDetector:
    """Detect user intent from message"""

    def __init__(self):
        self.intent_patterns = {
            "opt_out": [r"parar", r"remover", r"nao chama", r"não chama", r"cancelar", r"delete"],
            "schedule": [r"amanha", r"amanhã", r"segunda", r"terca", r"terça", r"quarta",
                        r"quinta", r"sexta", r"sabado", r"domingo", r"horario", r"horário",
                        r"agendar", r"marcar"],
            "price": [r"preco", r"preço", r"valor", r"quanto custa", r"plano", r"mensalidade",
                     r"pagamento", r"pix", r"parcela", r"parcelado", r"investimento"],
            "human": [r"humano", r"pessoa", r"contrato", r"boleto", r"falar com pessoa",
                     r"atendente", r"gerente"],
            "buy_intent": [r"gostei", r"curti", r"quero", r"fechar", r"vamos", r"pode fazer",
                          r"quero comprar", r"interesse", r"confirmar"],
            "greeting": [r"ola", r"olá", r"oi", r"bom dia", r"boa tarde", r"boa noite", r"e ai"],
            "confusion": [r"nao entendi", r"não entendi", r"confuso", r"claro", r"explicar"],
            "objection": [r"caro", r"barato", r"tempo", r"urgente", r"preciso", r"não tenho"],
        }

    def detect_intent(self, text: str) -> str:
        """Detect primary intent from text"""
        text_lower = text.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent
        return "other"


class AgentRouter:
    """Route conversations between agents"""

    def __init__(self):
        self.intent_detector = IntentDetector()

    def determine_next_agent(
        self,
        state: AgentState,
        user_message: str
    ) -> Tuple[AgentType, str]:
        """Determine next agent based on state and message"""
        current_agent = state["current_agent"]
        stage = state["conversation_stage"]
        is_outbound = state["is_outbound"]

        # Detect intent from user message
        intent = self.intent_detector.detect_intent(user_message)

        # Apply deterministic routing rules
        if intent == "opt_out":
            return AgentType.SUPERVISOR, "lead_pediu_para_parar"

        if intent == "schedule":
            return AgentType.FOLLOWUP, "lead_pediu_agendamento"

        if intent == "price":
            return AgentType.VENDAS, "lead_perguntou_preco"

        if intent == "human":
            return AgentType.SUPERVISOR, "pedido_sensivel_ou_humano"

        if intent == "buy_intent":
            return AgentType.VENDAS, "sinal_de_compra"

        if intent == "greeting" and stage in [ConversationStage.HOOK, ConversationStage.QUALIFY] and not is_outbound:
            return AgentType.ATENDIMENTO, "lead_abriu_conversa"

        if intent == "confusion":
            return AgentType.ATENDIMENTO, "lead_nao_entendeu"

        # Fallback to stage-based routing
        stage_agent = get_stage_agent(stage.value)

        # Check if we should escalate based on failure
        if state.get("attempt_count", 0) >= 2:
            return AgentType.SUPERVISOR, "multiplos_falhas"

        return stage_agent, f"stage_{stage.value}"

    def should_escalate_model(self, agent: AgentType, complexity: LeadComplexity) -> bool:
        """Check if we should escalate to a more powerful model"""
        # Escalation logic based on agent type and complexity
        escalation_rules = {
            AgentType.QUALIFICACAO: complexity == LeadComplexity.COMPLEX,
            AgentType.VENDAS: complexity in [LeadComplexity.COMPLEX, LeadComplexity.MEDIUM],
            AgentType.ATENDIMENTO: complexity == LeadComplexity.COMPLEX,
        }

        return escalation_rules.get(agent, False)

    def get_routing_decision(self, state: AgentState, user_message: str) -> Dict[str, any]:
        """Get complete routing decision"""
        next_agent, reason = self.determine_next_agent(state, user_message)

        decision = {
            "current_agent": state["current_agent"],
            "next_agent": next_agent,
            "reason": reason,
            "should_escalate": self.should_escalate_model(next_agent, LeadComplexity.SIMPLE),  # Simplified for now
            "confidence": self._calculate_routing_confidence(state, user_message),
        }

        return decision

    def _calculate_routing_confidence(self, state: AgentState, user_message: str) -> float:
        """Calculate confidence in routing decision"""
        confidence = 0.5  # Base confidence

        # Increase confidence if we have conversation history
        if len(state["messages"]) > 3:
            confidence += 0.2

        # Increase confidence if lead has been qualified
        if state["lead_facts"].get("tier") == "PREMIUM":
            confidence += 0.1

        # Decrease confidence if there are errors
        if state.get("last_error"):
            confidence -= 0.2

        return min(max(confidence, 0.1), 1.0)


def create_handoff_record(
    from_agent: AgentType,
    to_agent: AgentType,
    reason: str,
    session_id: str
) -> Dict[str, any]:
    """Create handoff record for memory"""
    return {
        "from_agent": from_agent.value,
        "to_agent": to_agent.value,
        "reason": reason,
        "session_id": session_id,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


def update_agent_notes(state: AgentState, agent_key: str, note: str) -> AgentState:
    """Update agent notes in state"""
    notes = state.get("agent_notes", {}).copy()
    notes[agent_key] = note[:500]  # Limit note size

    updated_state = state.copy()
    updated_state["agent_notes"] = notes
    updated_state["updated_at"] = __import__("datetime").datetime.now().isoformat()

    return updated_state