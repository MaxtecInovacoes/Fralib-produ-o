"""
Simple test for LangGraph functionality
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.langgraph.state import AgentType, AgentConfig, create_initial_state
from backend.agents.langgraph.profiles import get_agent_profile
from backend.agents.langgraph.router import AgentRouter, IntentDetector
from backend.agents.langgraph.memory import MemoryManager
from backend.agents.langgraph.error_handler import ErrorHandler, ErrorType
from backend.agents.langgraph.agent import LangGraphAgent

async def test_basic_functionality():
    """Test basic LangGraph functionality"""
    print("=== Testing LangGraph Agent Components ===\n")

    # Test 1: Agent State
    print("1. Testing Agent State...")
    lead_facts = {
        "nicho": "restaurante",
        "cidade": "São Paulo",
        "tier": "PREMIUM",
        "qtd_reviews": 15,
        "tem_site": True,
        "servicos": ["delivery", "mesas", "bar"]
    }

    state = create_initial_state(lead_facts, "test_session_001")
    print("   [OK] State created with session_id: {}".format(state['session_id']))
    print("   [OK] Current agent: {}".format(state['current_agent']))
    print("   [OK] Nicho: {}".format(state['nicho']))

    # Test 2: Agent Profiles
    print("\n2. Testing Agent Profiles...")
    profile = get_agent_profile(AgentType.VENDAS)
    print("   [OK] Sales agent profile loaded: {}".format(profile.label))
    print("   [OK] Mission: {}".format(profile.mission))

    # Test 3: Agent Router
    print("\n3. Testing Agent Router...")
    router = AgentRouter()
    detector = IntentDetector()

    # Test intent detection
    intent = detector.detect_intent("Quanto custa o plano?")
    print("   [OK] Intent detected: {}".format(intent))

    # Test routing
    next_agent, reason = router.determine_next_agent(state, "Quanto custa o plano?")
    print("   [OK] Next agent: {}, Reason: {}".format(next_agent, reason))

    # Test 4: Memory Manager
    print("\n4. Testing Memory Manager...")
    memory_manager = MemoryManager()

    # Add experience
    entry = memory_manager.add_experience(
        session_id="test_session_002",
        agent_type="vendas",
        nicho="restaurante",
        content="Test experience",
        confidence=0.7,
        tags=["successful"]
    )
    print("   [OK] Experience added: {}".format(entry.content))

    # Get memory context
    context = memory_manager.get_memory_context(
        session_id="test_session_002",
        agent_type="vendas",
        nicho="restaurante"
    )
    print("   [OK] Memory context retrieved: {} tokens".format(context['total_tokens']))

    # Test 5: Error Handler
    print("\n5. Testing Error Handler...")
    error_handler = ErrorHandler()

    # Test error classification
    error = Exception("Timeout occurred")
    error_type = error_handler._classify_error(error)
    print("   [OK] Error classified: {}".format(error_type))

    # Test error severity
    severity = error_handler._determine_severity(ErrorType.TIMEOUT, state)
    print("   [OK] Error severity: {}".format(severity))

    # Test 6: Complexity Calculation
    print("\n6. Testing Complexity Calculation...")
    config = AgentConfig()
    complexity = config.calculate_complexity(lead_facts)
    print("   [OK] Complexity calculated: {}".format(complexity.value))

    # Test 7: Agent Processing
    print("\n7. Testing Agent Processing...")
    agent_instance = LangGraphAgent()

    result = await agent_instance.process_message(
        session_id="test_session_003",
        lead_facts=lead_facts,
        user_message="Oi, quero saber sobre o serviço",
        is_outbound=False
    )

    print("   [OK] Processing result: {}".format(result['status']))
    print("   [OK] Final agent: {}".format(result.get('final_agent', 'unknown')))
    print("   [OK] Response: {}".format(result.get('response', 'No response')))

    print("\n=== All Tests Completed Successfully! ===")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())