"""
Integration of LangGraph agents with FraLib pipeline
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .langgraph.agent import LangGraphAgent, get_agent
from .langgraph.state import AgentType, LeadComplexity, AgentConfig, create_initial_state
from .langgraph.profiles import get_agent_profile
from .langgraph.router import AgentRouter
from .langgraph.memory import get_memory_manager


class FraLibLangGraphIntegration:
    """Integration layer between FraLib pipeline and LangGraph agents"""

    def __init__(self):
        self.agent = get_agent()
        self.config = AgentConfig()
        self.router = AgentRouter()
        self.memory_manager = get_memory_manager()

    async def process_lead_conversation(
        self,
        lead_facts: Dict[str, Any],
        conversation_history: list = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Process lead conversation through LangGraph agents

        Args:
            lead_facts: Lead information (nicho, cidade, tier, etc.)
            conversation_history: Previous conversation messages
            session_id: Unique session identifier

        Returns:
            Conversation result with agent response and metadata
        """
        if not session_id:
            session_id = f"fralib_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Create initial state
        initial_state = create_initial_state(lead_facts, session_id)

        # Add conversation history if provided
        if conversation_history:
            initial_state["messages"] = conversation_history

        # Process through LangGraph
        result = await self.agent.process_message(
            session_id=session_id,
            lead_facts=lead_facts,
            user_message=conversation_history[-1]["content"] if conversation_history else "Iniciar conversa",
            is_outbound=True
        )

        return result

    async def get_agent_response(
        self,
        lead_facts: Dict[str, Any],
        user_message: str,
        current_agent: AgentType = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Get response from specific agent

        Args:
            lead_facts: Lead information
            user_message: User message to process
            current_agent: Current agent type
            session_id: Session identifier

        Returns:
            Agent response with metadata
        """
        if not session_id:
            session_id = f"fralib_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Create state with current agent
        state = create_initial_state(lead_facts, session_id)
        if current_agent:
            state["current_agent"] = current_agent.value

        # Process message
        result = await self.agent.process_message(
            session_id=session_id,
            lead_facts=lead_facts,
            user_message=user_message,
            is_outbound=False
        )

        return result

    def calculate_lead_complexity(self, lead_facts: Dict[str, Any]) -> str:
        """Calculate lead complexity for model selection"""
        complexity = self.config.calculate_complexity(lead_facts)
        return complexity.value

    def get_agent_model_config(self, agent_type: AgentType, complexity: str) -> Dict[str, Any]:
        """Get model configuration for agent"""
        # Convert complexity string to LeadComplexity enum
        try:
            complexity_enum = LeadComplexity(complexity)
        except ValueError:
            # Fallback to medium complexity
            complexity_enum = LeadComplexity.MEDIUM

        return {
            "model": self.config.get_model(agent_type, complexity_enum),
            "max_tokens": self.config.get_max_tokens(agent_type, complexity_enum),
            "temperature": self.config.get_temperature(agent_type)
        }

    def get_memory_context(self, session_id: str, agent_type: AgentType, nicho: str) -> Dict[str, str]:
        """Get memory context for agent"""
        return self.memory_manager.get_memory_context(
            session_id=session_id,
            agent_type=agent_type.value,
            nicho=nicho
        )

    def record_conversation_experience(
        self,
        session_id: str,
        agent_type: AgentType,
        nicho: str,
        user_message: str,
        agent_response: str,
        success: bool = True
    ) -> None:
        """Record conversation experience for learning"""
        # Record the interaction
        self.memory_manager.record_interaction(
            session_id=session_id,
            agent_type=agent_type.value,
            nicho=nicho,
            interaction=f"User: {user_message}\nAgent: {agent_response}",
            success=success
        )

        # Add experience to memory
        self.memory_manager.add_experience(
            session_id=session_id,
            agent_type=agent_type.value,
            nicho=nicho,
            content=f"Successfully handled: {user_message[:100]}",
            confidence=0.8 if success else 0.3,
            tags=["successful"] if success else ["failed"]
        )


# ════════════════════════════════════════════════════════════════════
# SDR/FRANZ INTEGRATION FUNCTIONS
# ════════════════════════════════════════════════════════════════════

def sync_sdr_memory(memory_data: Dict[str, Any], session_id: str, user_id: int) -> Dict[str, Any]:
    """
    Sincroniza dados do LeadMemory do SDR/Franz com o memory system.

    Args:
        memory_data: Dados do LeadMemory (do SDR/Franz)
        session_id: ID da sessão
        user_id: ID do tenant

    Returns:
        Dados sincronizados com contexto de memória
    """
    from .franz_bridge import sync_memory_to_sdr
    return sync_memory_to_sdr(memory_data, session_id, user_id)


def get_sdr_routing_context(session_id: str, user_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtém contexto de routing para o SDR baseado no memory system.

    Args:
        session_id: ID da sessão
        user_id: ID do tenant
        lead_data: Dados do lead

    Returns:
        Contexto de routing com recomendações
    """
    from .franz_bridge import get_sdr_routing_context as _get_context
    return _get_context(session_id, user_id, lead_data)


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
    from .franz_bridge import handle_sdr_error as _handle_error
    return _handle_error(error, state, session_id)


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
    from .franz_bridge import record_sdr_interaction as _record
    _record(session_id, user_id, lead_data, user_message, agent_response, stage, success)


def prepare_closer_handoff(
    session_id: str,
    user_id: int,
    lead_data: Dict[str, Any],
    history: list
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
    from .franz_bridge import prepare_closer_handoff_context
    return prepare_closer_handoff_context(session_id, user_id, lead_data, history)


def detect_sdr_intent(message: str) -> Dict[str, Any]:
    """
    Detecta intent de uma mensagem usando o router do novo sistema.

    Args:
        message: Mensagem do lead

    Returns:
        Dicionário com intent e confiança
    """
    from .franz_bridge import get_intent_from_message
    return get_intent_from_message(message)


def calculate_sdr_lead_complexity(lead_data: Dict[str, Any]) -> str:
    """
    Calcula complexidade do lead para seleção de modelo.

    Args:
        lead_data: Dados do lead

    Returns:
        Complexidade: 'simples', 'medio', ou 'complexo'
    """
    from .franz_bridge import calculate_lead_complexity_for_sdr
    return calculate_lead_complexity_for_sdr(lead_data)


# Global integration instance
integration = FraLibLangGraphIntegration()


async def example_integration_usage():
    """Example of how to integrate with FraLib pipeline"""

    # Lead facts from FraLib pipeline
    lead_facts = {
        "nicho": "restaurante",
        "cidade": "São Paulo",
        "tier": "PREMIUM",
        "qtd_reviews": 25,
        "tem_site": True,
        "servicos": ["delivery", "mesas", "bar", "eventos", "cardapio_digital"],
        "nome_lead": "Restaurante Sabor & Arte"
    }

    # Initialize integration
    integration = FraLibLangGraphIntegration()

    # Calculate complexity
    complexity = integration.calculate_lead_complexity(lead_facts)
    print(f"Lead complexity: {complexity}")

    # Get agent configuration
    agent_config = integration.get_agent_model_config(AgentType.VENDAS, complexity)
    print(f"Agent config: {agent_config}")

    # Process conversation
    result = await integration.process_lead_conversation(
        lead_facts=lead_facts,
        conversation_history=[
            {"role": "user", "content": "Oi, quero saber sobre o serviço"}
        ]
    )

    print(f"Conversation result: {result['status']}")
    print(f"Agent response: {result.get('response', 'No response')}")

    # Record experience
    integration.record_conversation_experience(
        session_id="example_session",
        agent_type=AgentType.VENDAS,
        nicho="restaurante",
        user_message="Oi, quero saber sobre o serviço",
        agent_response=result.get('response', ''),
        success=True
    )

    print("Integration example completed successfully!")


if __name__ == "__main__":
    asyncio.run(example_integration_usage())