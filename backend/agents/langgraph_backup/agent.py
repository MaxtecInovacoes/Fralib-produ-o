"""
LangGraph Agent Implementation - Core agent nodes and edges
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import AnyMessage

from .state import AgentState, AgentType, AgentConfig, create_initial_state
from .profiles import get_agent_profile, build_agent_context, generate_agent_prompt
from .router import AgentRouter, create_handoff_record
from .memory import get_memory_manager
from .error_handler import get_error_handler, get_circuit_breaker, ErrorType, ErrorSeverity

logger = logging.getLogger("langgraph_agent")


class LangGraphAgent:
    """Main LangGraph agent implementation"""

    def __init__(self):
        self.config = AgentConfig()
        self.router = AgentRouter()
        self.memory_manager = get_memory_manager()
        self.error_handler = get_error_handler()
        self.circuit_breaker = get_circuit_breaker()

        # Initialize the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        graph = StateGraph(AgentState)

        # Add nodes for each agent
        graph.add_node("approach", self._approach_agent)
        graph.add_node("support", self._support_agent)
        graph.add_node("qualification", self._qualification_agent)
        graph.add_node("sales", self._sales_agent)
        graph.add_node("followup", self._followup_agent)
        graph.add_node("supervisor", self._supervisor_agent)

        # Add decision node
        graph.add_node("decide_next_agent", self._decide_next_agent)

        # Add edges
        graph.add_edge(START, "decide_next_agent")

        # Conditional edges from decision node
        graph.add_conditional_edges(
            "decide_next_agent",
            self._should_continue,
            {
                "approach": "approach",
                "support": "support",
                "qualification": "qualification",
                "sales": "sales",
                "followup": "followup",
                "supervisor": "supervisor",
                "end": END
            }
        )

        return graph.compile(checkpointer=None)

    async def process_message(
        self,
        session_id: str,
        lead_facts: Dict[str, Any],
        user_message: str,
        is_outbound: bool = True
    ) -> Dict[str, Any]:
        """Process a user message through the agent system"""
        # Check circuit breaker
        if not self.circuit_breaker.should_allow_request():
            return {
                "error": "Service temporarily unavailable",
                "status": "service_unavailable",
                "session_id": session_id
            }

        # Create initial state
        initial_state = create_initial_state(lead_facts, session_id)
        initial_state["is_outbound"] = is_outbound

        # Add user message
        user_msg = {"role": "user", "content": user_message}
        initial_state["messages"].append(user_msg)

        try:
            # Process through the graph
            result = await self.graph.ainvoke(initial_state)

            # Record success
            self.circuit_breaker.record_success()

            return {
                "result": result,
                "status": "success",
                "session_id": session_id,
                "final_agent": result["current_agent"].value,
                "messages_processed": len(result["messages"])
            }

        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure()

            # Handle error
            error_context = self.error_handler.handle_error(e, initial_state)

            return {
                "error": str(e),
                "error_context": error_context.to_dict(),
                "status": "error",
                "session_id": session_id,
                "escalated": error_context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
            }

    async def _approach_agent(self, state: AgentState) -> AgentState:
        """Approach agent node"""
        return await self._run_agent(state, AgentType.ABORDAGEM)

    async def _support_agent(self, state: AgentState) -> AgentState:
        """Support agent node"""
        return await self._run_agent(state, AgentType.ATENDIMENTO)

    async def _qualification_agent(self, state: AgentState) -> AgentState:
        """Qualification agent node"""
        return await self._run_agent(state, AgentType.QUALIFICACAO)

    async def _sales_agent(self, state: AgentState) -> AgentState:
        """Sales agent node"""
        return await self._run_agent(state, AgentType.VENDAS)

    async def _followup_agent(self, state: AgentState) -> AgentState:
        """Follow-up agent node"""
        return await self._run_agent(state, AgentType.FOLLOWUP)

    async def _supervisor_agent(self, state: AgentState) -> AgentState:
        """Supervisor agent node"""
        return await self._run_agent(state, AgentType.SUPERVISOR)

    async def _run_agent(self, state: AgentState, agent_type: AgentType) -> AgentState:
        """Run a specific agent"""
        profile = get_agent_profile(agent_type)
        complexity = self.config.calculate_complexity(state["lead_facts"])

        # Build agent context
        context = build_agent_context(state)
        context["selected_agent"] = agent_type.value
        context["complexity"] = complexity.value

        # Generate system prompt
        system_prompt = generate_agent_prompt(context)

        # Get memory context
        memory_context = self.memory_manager.get_memory_context(
            state["session_id"],
            agent_type.value,
            state["nicho"]
        )

        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{memory_context['core_memory']}"
        if memory_context["warm_memory"]:
            full_prompt += f"\n{memory_context['warm_memory']}"

        # Add conversation history
        conversation_history = [msg.content for msg in state["messages"]]
        full_prompt += f"\n\nCONVERSATION HISTORY:\n{' '.join(conversation_history[-5:])}"

        # Update state
        updated_state = state.copy()
        updated_state["current_agent"] = agent_type.value  # Convert to string
        updated_state["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Simulate agent response (in real implementation, this would call LLM)
        try:
            # Mock LLM response for now
            response = await self._call_llm(full_prompt, agent_type, complexity)

            # Create new message list with the response
            updated_messages = updated_state["messages"].copy()
            response_msg = {"role": "assistant", "content": response}
            updated_messages.append(response_msg)

            # Update state with new messages
            final_state = updated_state.copy()
            final_state["messages"] = updated_messages

            # Record interaction
            self.memory_manager.record_interaction(
                state["session_id"],
                agent_type.value,
                state["nicho"],
                response,
                success=True
            )

            # Check if we need to hand off
            if agent_type != AgentType.SUPERVISOR:
                routing_decision = self.router.get_routing_decision(final_state, response)

                if routing_decision["next_agent"] != agent_type:
                    # Create handoff record
                    handoff = create_handoff_record(
                        agent_type,
                        routing_decision["next_agent"],
                        routing_decision["reason"],
                        state["session_id"]
                    )

                    final_state["handoff_log"].append(handoff)
                    final_state["next_agent"] = routing_decision["next_agent"].value  # Convert to string
                    final_state["handoff_reason"] = routing_decision["reason"]
                    final_state["previous_agent"] = agent_type.value  # Convert to string

            return final_state

        except Exception as e:
            # Handle error
            error_context = self.error_handler.handle_error(e, state)

            # Add error message
            error_msg = {"role": "assistant", "content": f"Desculpe, ocorreu um erro. Estou transferindo para um supervisor."}
            updated_state["messages"].append(error_msg)

            # Escalate to supervisor
            updated_state["next_agent"] = AgentType.SUPERVISOR
            updated_state["handoff_reason"] = "error_occurred"
            updated_state["last_error"] = str(e)

            return updated_state

    async def _call_llm(self, prompt: str, agent_type: AgentType, complexity) -> str:
        """Mock LLM call - in real implementation, this would call the actual LLM"""
        # Simulate processing time
        await asyncio.sleep(0.1)

        # Mock response based on agent type
        responses = {
            AgentType.ABORDAGEM: "Olá! Vi que você tem um negócio de [nicho] em [cidade]. Posso fazer uma pergunta?",
            AgentType.ATENDIMENTO: "Olá! Como posso ajudar você hoje com seu negócio de [nicho]?",
            AgentType.QUALIFICACAO: "Para entender melhor sua necessidade, você é o responsável pelas decisões do negócio?",
            AgentType.VENDAS: "Nosso serviço custa R$ 1.499 em até 12x. Quer ver como podemos ajudar seu negócio?",
            AgentType.FOLLOWUP: "Tudo bem? Gostaria de revisitar nossa conversa sobre o site para seu [nicho]?",
            AgentType.SUPERVISOR: "Entendo sua situação. Vou conectar você com um especialista humano para ajudar melhor."
        }

        return responses.get(agent_type, "Estou aqui para ajudar!")

    def _decide_next_agent(self, state: AgentState) -> str:
        """Decide next agent based on current state"""
        # Check if we should escalate
        if self.error_handler.should_escalate(state):
            return "supervisor"

        # Check if there's a next agent specified
        if state.get("next_agent"):
            return state["next_agent"].value

        # Default to current agent
        return state["current_agent"].value

    def _should_continue(self, state: AgentState) -> str:
        """Determine if conversation should continue"""
        # Check for opt-out
        if state.get("next_agent") == AgentType.SUPERVISOR and "parar" in str(state.get("messages", [])):
            return "end"

        # Check for natural end conditions
        if len(state["messages"]) > 20:  # Prevent infinite conversations
            return "end"

        # Check for escalation
        if self.error_handler.should_escalate(state):
            return "supervisor"

        return state["current_agent"].value


# Global agent instance
agent = LangGraphAgent()


def get_agent() -> LangGraphAgent:
    """Get global agent instance"""
    return agent


# Example usage
async def example_usage():
    """Example of how to use the agent"""
    agent_instance = get_agent()

    # Lead facts
    lead_facts = {
        "nicho": "restaurante",
        "cidade": "São Paulo",
        "tier": "PREMIUM",
        "qtd_reviews": 15,
        "tem_site": False,
        "servicos": ["delivery", "mesas", "bar"]
    }

    # Process message
    result = await agent_instance.process_message(
        session_id="test_session_001",
        lead_facts=lead_facts,
        user_message="Oi, quero saber mais sobre o serviço",
        is_outbound=False
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(example_usage())