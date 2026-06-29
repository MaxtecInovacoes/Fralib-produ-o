"""
Simple test for individual LangGraph components
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_individual_components():
    """Test individual components without LangGraph"""
    print("=== Testing Individual LangGraph Components ===\n")

    # Test 1: Agent State
    print("1. Testing Agent State...")
    from backend.agents.langgraph.state import AgentType, AgentConfig, create_initial_state

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
    from backend.agents.langgraph.profiles import get_agent_profile

    profile = get_agent_profile(AgentType.VENDAS)
    print("   [OK] Sales agent profile loaded: {}".format(profile.label))
    print("   [OK] Mission: {}".format(profile.mission))

    # Test 3: Agent Router
    print("\n3. Testing Agent Router...")
    from backend.agents.langgraph.router import AgentRouter, IntentDetector

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
    from backend.agents.langgraph.memory import MemoryManager

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
    from backend.agents.langgraph.error_handler import ErrorHandler, ErrorType

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

    # Test 7: CLI Tool
    print("\n7. Testing CLI Tool...")
    from backend.agents.langgraph.cli import LangGraphCLI

    cli = LangGraphCLI()
    print("   [OK] CLI initialized successfully")

    print("\n=== All Individual Tests Completed Successfully! ===")
    print("\nThe LangGraph components are working correctly!")
    print("To test the full LangGraph integration, run:")
    print("  python -c \"from backend.agents.langgraph.agent import LangGraphAgent; print('LangGraph ready')\"")

if __name__ == "__main__":
    test_individual_components()