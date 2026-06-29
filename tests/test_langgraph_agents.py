"""
LangGraph Agent Tests - Comprehensive test suite
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from ..langgraph.state import (
    AgentState, AgentType, ConversationStage, LeadComplexity,
    AgentConfig, create_initial_state
)
from ..langgraph.profiles import (
    AGENT_PROFILES, get_agent_profile, build_agent_context,
    generate_agent_prompt
)
from ..langgraph.router import AgentRouter, IntentDetector, create_handoff_record
from ..langgraph.memory import (
    MemoryManager, MemoryEntry, CoreMemory, WarmMemory, ColdMemory,
    get_memory_manager
)
from ..langgraph.error_handler import (
    ErrorHandler, ErrorType, ErrorSeverity, CircuitBreaker,
    get_error_handler, get_circuit_breaker
)
from ..langgraph.agent import LangGraphAgent


# ══════════════════════════════════════════════════════════════
# STATE TESTS
# ══════════════════════════════════════════════════════════════


class TestAgentState:
    """Test agent state creation and management"""

    def test_create_initial_state(self):
        """Test initial state creation"""
        lead_facts = {
            "nicho": "restaurante",
            "cidade": "São Paulo",
            "tier": "PREMIUM"
        }

        state = create_initial_state(lead_facts, "test_session_001")

        assert state["session_id"] == "test_session_001"
        assert state["current_agent"] == AgentType.ATENDIMENTO
        assert state["conversation_stage"] == ConversationStage.HOOK
        assert state["lead_facts"] == lead_facts
        assert state["nicho"] == "restaurante"
        assert state["tier"] == "PREMIUM"
        assert state["messages"] == []
        assert state["attempt_count"] == 0

    def test_state_immutability(self):
        """Test that state updates create new instances"""
        state = create_initial_state({}, "test_session_002")

        updated_state = state.copy()
        updated_state["messages"].append({"role": "user", "content": "Test"})

        assert len(state["messages"]) == 0
        assert len(updated_state["messages"]) == 1


# ══════════════════════════════════════════════════════════════
# CONFIG TESTS
# ══════════════════════════════════════════════════════════════


class TestAgentConfig:
    """Test agent configuration"""

    def test_calculate_complexity_simple(self):
        """Test complexity calculation for simple lead"""
        config = AgentConfig()
        facts = {
            "qtd_reviews": 0,
            "nicho": "barbearia",
            "tier": "STANDARD",
            "tem_site": False,
            "servicos": []
        }

        complexity = config.calculate_complexity(facts)

        assert complexity == LeadComplexity.SIMPLE

    def test_calculate_complexity_medium(self):
        """Test complexity calculation for medium lead"""
        config = AgentConfig()
        facts = {
            "qtd_reviews": 3,
            "nicho": "restaurante",
            "tier": "STANDARD",
            "tem_site": True,
            "servicos": ["delivery", "mesas"]
        }

        complexity = config.calculate_complexity(facts)

        assert complexity == LeadComplexity.MEDIUM

    def test_calculate_complexity_complex(self):
        """Test complexity calculation for complex lead"""
        config = AgentConfig()
        facts = {
            "qtd_reviews": 25,
            "nicho": "hotel",
            "tier": "PREMIUM",
            "tem_site": True,
            "servicos": ["spa", "restaurant", "gym", "pool", "business_center", "event_space", "concierge", "room_service", "valet_parking", "laundry"]
        }

        complexity = config.calculate_complexity(facts)

        assert complexity == LeadComplexity.COMPLEX

    def test_get_model_selection(self):
        """Test model selection based on agent and complexity"""
        config = AgentConfig()
        complexity = LeadComplexity.SIMPLE

        model = config.get_model(AgentType.QUALIFICACAO, complexity)
        assert model == "haiku"

        model = config.get_model(AgentType.VENDAS, complexity)
        assert model == "haiku"


# ══════════════════════════════════════════════════════════════
# PROFILES TESTS
# ══════════════════════════════════════════════════════════════


class TestAgentProfiles:
    """Test agent profiles"""

    def test_get_agent_profile(self):
        """Test retrieving agent profile"""
        profile = get_agent_profile(AgentType.ABORDAGEM)

        assert profile.key == "abordagem"
        assert profile.label == "Opening Agent"
        assert profile.mission is not None
        assert profile.when_to_use is not None

    def test_all_agents_have_profiles(self):
        """Test that all agent types have profiles"""
        for agent_type in AgentType:
            profile = get_agent_profile(agent_type)
            assert profile is not None
            assert profile.key == agent_type.value

    def test_build_agent_context(self):
        """Test building agent context from state"""
        state = create_initial_state({"nicho": "restaurante"}, "test_session_003")
        state["current_agent"] = AgentType.ABORDAGEM

        context = build_agent_context(state)

        assert "selected_agent" in context
        assert "label" in context
        assert "mission" in context
        assert context["selected_agent"] == "abordagem"


# ══════════════════════════════════════════════════════════════
# ROUTER TESTS
# ══════════════════════════════════════════════════════════════


class TestIntentDetector:
    """Test intent detection"""

    def test_detect_opt_out(self):
        """Test opt-out intent detection"""
        detector = IntentDetector()

        text = "Não quero mais ser atendido"
        intent = detector.detect_intent(text)

        assert intent == "opt_out"

    def test_detect_price_intent(self):
        """Test price intent detection"""
        detector = IntentDetector()

        text = "Quanto custa o plano?"
        intent = detector.detect_intent(text)

        assert intent == "price"

    def test_detect_schedule_intent(self):
        """Test schedule intent detection"""
        detector = IntentDetector()

        text = "Posso marcar para amanhã?"
        intent = detector.detect_intent(text)

        assert intent == "schedule"

    def test_detect_greeting(self):
        """Test greeting intent detection"""
        detector = IntentDetector()

        text = "Oi, tudo bem?"
        intent = detector.detect_intent(text)

        assert intent == "greeting"


class TestAgentRouter:
    """Test agent routing"""

    def test_determine_next_agent_opt_out(self):
        """Test routing for opt-out intent"""
        router = AgentRouter()

        state = create_initial_state({}, "test_session_004")
        state["messages"].append({"role": "user", "content": "Parar de me chamar"})

        next_agent, reason = router.determine_next_agent(state, "Parar de me chamar")

        assert next_agent == AgentType.SUPERVISOR
        assert reason == "lead_pediu_para_parar"

    def test_determine_next_agent_price(self):
        """Test routing for price intent"""
        router = AgentRouter()

        state = create_initial_state({}, "test_session_005")
        state["messages"].append({"role": "user", "content": "Quanto custa?"})

        next_agent, reason = router.determine_next_agent(state, "Quanto custa?")

        assert next_agent == AgentType.VENDAS
        assert reason == "lead_perguntou_preco"

    def test_determine_next_agent_buy_intent(self):
        """Test routing for buy intent"""
        router = AgentRouter()

        state = create_initial_state({}, "test_session_006")
        state["messages"].append({"role": "user", "content": "Gostei, quero fechar"})

        next_agent, reason = router.determine_next_agent(state, "Gostei, quero fechar")

        assert next_agent == AgentType.VENDAS
        assert reason == "sinal_de_compra"


# ══════════════════════════════════════════════════════════════
# MEMORY TESTS
# ══════════════════════════════════════════════════════════════


class TestMemoryManager:
    """Test memory management"""

    def test_memory_entry_creation(self):
        """Test creating memory entry"""
        entry = MemoryEntry(
            session_id="test_session_007",
            agent_type="vendas",
            nicho="restaurante",
            content="Test content",
            confidence=0.7
        )

        assert entry.session_id == "test_session_007"
        assert entry.agent_type == "vendas"
        assert entry.content == "Test content"
        assert entry.confidence == 0.7

    def test_memory_entry_success_rate(self):
        """Test success rate calculation"""
        entry = MemoryEntry(
            session_id="test_session_008",
            agent_type="vendas",
            nicho="restaurante",
            content="Test content",
            usage_count=10,
            success_count=8,
            failure_count=2
        )

        assert entry.success_rate == 0.8

    @pytest.mark.asyncio
    async def test_memory_manager_add_experience(self):
        """Test adding experience to memory"""
        manager = MemoryManager()

        entry = manager.add_experience(
            session_id="test_session_009",
            agent_type="vendas",
            nicho="restaurante",
            content="Test experience",
            confidence=0.7,
            tags=["successful"]
        )

        assert entry is not None
        assert entry.content == "Test experience"

    def test_get_memory_context(self):
        """Test getting memory context"""
        manager = MemoryManager()

        context = manager.get_memory_context(
            session_id="test_session_010",
            agent_type="vendas",
            nicho="restaurante"
        )

        assert "core_memory" in context
        assert "warm_memory" in context
        assert "total_tokens" in context


# ══════════════════════════════════════════════════════════════
# ERROR HANDLER TESTS
# ══════════════════════════════════════════════════════════════


class TestErrorHandler:
    """Test error handling"""

    def test_error_classification(self):
        """Test error classification"""
        handler = ErrorHandler()

        # Test timeout classification
        timeout_error = TimeoutError("Request timed out")
        error_type = handler._classify_error(timeout_error)

        assert error_type == ErrorType.TIMEOUT

        # Test system error classification
        system_error = Exception("System error")
        error_type = handler._classify_error(system_error)

        assert error_type == ErrorType.SYSTEM_ERROR

    def test_error_severity_determination(self):
        """Test error severity determination"""
        handler = ErrorHandler()

        # Test high severity errors
        high_severity_error = handler._determine_severity(ErrorType.HUMAN_REQUIRED, None)
        assert high_severity_error == ErrorSeverity.HIGH

        # Test medium severity errors
        medium_severity_error = handler._determine_severity(ErrorType.INTENT_DRIFT, None)
        assert medium_severity_error == ErrorSeverity.MEDIUM

        # Test low severity errors
        low_severity_error = handler._determine_severity(ErrorType.LOW_CONFIDENCE, None)
        assert low_severity_error == ErrorSeverity.LOW

    def test_should_escalate(self):
        """Test escalation decision"""
        handler = ErrorHandler(max_retries=3)
        state = create_initial_state({}, "test_session_011")
        state["attempt_count"] = 3

        assert handler.should_escalate(state) is True

    def test_circuit_breaker_state(self):
        """Test circuit breaker state management"""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        # Test initial state
        assert breaker.get_state() == "closed"

        # Test failure recording
        for _ in range(5):
            breaker.record_failure()

        assert breaker.get_state() == "open"

        # Test recovery after timeout
        breaker.record_success()
        assert breaker.get_state() == "half-open"


# ══════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════


class TestLangGraphAgentIntegration:
    """Test LangGraph agent integration"""

    @pytest.mark.asyncio
    async def test_agent_process_message(self):
        """Test processing message through agent"""
        agent_instance = LangGraphAgent()

        lead_facts = {
            "nicho": "barbearia",
            "cidade": "Rio de Janeiro",
            "tier": "STANDARD"
        }

        result = await agent_instance.process_message(
            session_id="test_session_012",
            lead_facts=lead_facts,
            user_message="Oi, como posso ajudar?",
            is_outbound=False
        )

        assert result["status"] == "success"
        assert result["session_id"] == "test_session_012"
        assert "response" in result

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent_instance = LangGraphAgent()

        assert agent_instance is not None
        assert agent_instance.config is not None
        assert agent_instance.router is not None
        assert agent_instance.memory_manager is not None
        assert agent_instance.error_handler is not None


# ══════════════════════════════════════════════════════════════
# PERFORMANCE TESTS
# ══════════════════════════════════════════════════════════════


class TestPerformance:
    """Test performance characteristics"""

    def test_memory_operations_speed(self):
        """Test memory operations are fast"""
        import time

        manager = MemoryManager()

        start = time.time()
        for i in range(100):
            manager.add_experience(
                session_id=f"perf_test_{i}",
                agent_type="vendas",
                nicho="restaurante",
                content=f"Performance test {i}",
                confidence=0.5
            )
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should complete in under 1 second

    def test_router_deterministic(self):
        """Test routing decisions are deterministic"""
        router = AgentRouter()

        state = create_initial_state({}, "test_session_013")
        state["messages"].append({"role": "user", "content": "Quanto custa?"})

        # First decision
        decision1 = router.get_routing_decision(state, "Quanto custa?")

        # Second decision (same input)
        decision2 = router.get_routing_decision(state, "Quanto custa?")

        assert decision1["next_agent"] == decision2["next_agent"]


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])