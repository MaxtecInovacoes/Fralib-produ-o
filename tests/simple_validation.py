"""
Simple validation script for LangGraph integration
"""

import sys
import os
import asyncio

# Add the project root to the path
sys.path.append('C:/fralib')

async def validate_integration():
    """Validate LangGraph integration"""

    print("=== LangGraph Integration Validation ===\n")

    validation_results = []

    # Test 1: Component Imports
    print("1. Component Imports")
    print("-" * 30)

    try:
        from backend.agents.langgraph.state import AgentType, AgentConfig, create_initial_state
        from backend.agents.langgraph.profiles import get_agent_profile
        from backend.agents.langgraph.router import AgentRouter, IntentDetector
        from backend.agents.langgraph.memory import MemoryManager
        from backend.agents.langgraph.error_handler import ErrorHandler, ErrorType
        from backend.agents.langgraph.agent import LangGraphAgent
        from backend.agents.fralib_integration import FraLibLangGraphIntegration
        from backend.agents.integration_endpoints import router

        validation_results.append(("Component Imports", "PASSED"))
        print("   [OK] All components imported successfully")

    except Exception as e:
        validation_results.append(("Component Imports", f"FAILED: {e}"))
        print(f"   [ERROR] Import failed: {e}")

    # Test 2: Agent State Creation
    print("\n2. Agent State Creation")
    print("-" * 30)

    try:
        from backend.agents.langgraph.state import create_initial_state

        lead_facts = {
            "nicho": "restaurante",
            "cidade": "São Paulo",
            "tier": "PREMIUM",
            "qtd_reviews": 15,
            "tem_site": True,
            "servicos": ["delivery", "mesas", "bar"]
        }

        state = create_initial_state(lead_facts, "validation_test")

        assert state["session_id"] == "validation_test"
        assert state["current_agent"] == "atendimento"
        assert state["nicho"] == "restaurante"
        assert state["lead_facts"] == lead_facts

        validation_results.append(("Agent State Creation", "PASSED"))
        print("   [OK] Agent state created successfully")

    except Exception as e:
        validation_results.append(("Agent State Creation", f"FAILED: {e}"))
        print(f"   [ERROR] State creation failed: {e}")

    # Test 3: Agent Profiles
    print("\n3. Agent Profiles")
    print("-" * 30)

    try:
        from backend.agents.langgraph.profiles import get_agent_profile, AgentType

        profile = get_agent_profile(AgentType.VENDAS)
        assert profile.label == "Sales Agent"
        assert profile.mission is not None
        assert len(profile.subagents) > 0

        validation_results.append(("Agent Profiles", "PASSED"))
        print("   [OK] Agent profiles loaded successfully")

    except Exception as e:
        validation_results.append(("Agent Profiles", f"FAILED: {e}"))
        print(f"   [ERROR] Profile loading failed: {e}")

    # Test 4: Intent Detection
    print("\n4. Intent Detection")
    print("-" * 30)

    try:
        from backend.agents.langgraph.router import AgentRouter, IntentDetector

        router = AgentRouter()
        detector = IntentDetector()

        # Test various intents
        test_cases = [
            ("Quanto custa?", "price"),
            ("Quero agendar", "schedule"),
            ("Parar de me chamar", "opt_out"),
            ("Oi, tudo bem?", "greeting"),
            ("Não entendi", "confusion")
        ]

        for text, expected_intent in test_cases:
            detected_intent = detector.detect_intent(text)
            assert detected_intent == expected_intent

        validation_results.append(("Intent Detection", "PASSED"))
        print("   [OK] Intent detection working correctly")

    except Exception as e:
        validation_results.append(("Intent Detection", f"FAILED: {e}"))
        print(f"   [ERROR] Intent detection failed: {e}")

    # Test 5: Memory Manager
    print("\n5. Memory Manager")
    print("-" * 30)

    try:
        from backend.agents.langgraph.memory import MemoryManager

        memory_manager = MemoryManager()

        # Add experience
        entry = memory_manager.add_experience(
            session_id="validation_test",
            agent_type="vendas",
            nicho="restaurante",
            content="Test experience",
            confidence=0.7,
            tags=["successful"]
        )

        assert entry.content == "Test experience"
        assert entry.confidence == 0.7

        # Get memory context
        context = memory_manager.get_memory_context(
            session_id="validation_test",
            agent_type="vendas",
            nicho="restaurante"
        )

        assert "core_memory" in context
        assert "warm_memory" in context
        assert "total_tokens" in context

        validation_results.append(("Memory Manager", "PASSED"))
        print("   [OK] Memory manager working correctly")

    except Exception as e:
        validation_results.append(("Memory Manager", f"FAILED: {e}"))
        print(f"   [ERROR] Memory manager failed: {e}")

    # Test 6: Error Handler
    print("\n6. Error Handler")
    print("-" * 30)

    try:
        from backend.agents.langgraph.error_handler import ErrorHandler, ErrorType
        from backend.agents.langgraph.state import create_initial_state

        error_handler = ErrorHandler()
        state = create_initial_state({}, "validation_test")

        # Test error classification
        error = Exception("Timeout occurred")
        error_type = error_handler._classify_error(error)
        assert error_type == ErrorType.TIMEOUT

        # Test error severity
        severity = error_handler._determine_severity(ErrorType.TIMEOUT, state)
        assert severity.value == "low"

        validation_results.append(("Error Handler", "PASSED"))
        print("   [OK] Error handler working correctly")

    except Exception as e:
        validation_results.append(("Error Handler", f"FAILED: {e}"))
        print(f"   [ERROR] Error handler failed: {e}")

    # Test 7: Complexity Calculation
    print("\n7. Complexity Calculation")
    print("-" * 30)

    try:
        from backend.agents.langgraph.state import AgentConfig

        config = AgentConfig()

        # Test simple lead
        simple_lead = {
            "qtd_reviews": 0,
            "nicho": "barbearia",
            "tier": "STANDARD",
            "tem_site": False,
            "servicos": []
        }

        complexity = config.calculate_complexity(simple_lead)
        assert complexity.value == "simples"

        # Test complex lead
        complex_lead = {
            "qtd_reviews": 25,
            "nicho": "hotel",
            "tier": "PREMIUM",
            "tem_site": True,
            "servicos": ["spa", "restaurant", "gym", "pool", "business_center"]
        }

        complexity = config.calculate_complexity(complex_lead)
        assert complexity.value == "complexo"

        validation_results.append(("Complexity Calculation", "PASSED"))
        print("   [OK] Complexity calculation working correctly")

    except Exception as e:
        validation_results.append(("Complexity Calculation", f"FAILED: {e}"))
        print(f"   [ERROR] Complexity calculation failed: {e}")

    # Test 8: Integration Layer
    print("\n8. Integration Layer")
    print("-" * 30)

    try:
        from backend.agents.fralib_integration import FraLibLangGraphIntegration
        from backend.agents.langgraph.state import AgentType

        integration = FraLibLangGraphIntegration()

        # Test complexity calculation
        lead_facts = {
            "nicho": "restaurante",
            "cidade": "São Paulo",
            "tier": "PREMIUM",
            "qtd_reviews": 15,
            "tem_site": True,
            "servicos": ["delivery", "mesas", "bar"]
        }

        complexity = integration.calculate_lead_complexity(lead_facts)
        assert complexity in ["simples", "medio", "complexo"]

        # Test agent model config
        agent_config = integration.get_agent_model_config(AgentType.VENDAS, complexity)
        assert "model" in agent_config
        assert "max_tokens" in agent_config
        assert "temperature" in agent_config

        validation_results.append(("Integration Layer", "PASSED"))
        print("   [OK] Integration layer working correctly")

    except Exception as e:
        validation_results.append(("Integration Layer", f"FAILED: {e}"))
        print(f"   [ERROR] Integration layer failed: {e}")

    # Test 9: CLI Tool
    print("\n9. CLI Tool")
    print("-" * 30)

    try:
        from backend.agents.langgraph.cli import LangGraphCLI

        cli = LangGraphCLI()
        assert cli is not None
        assert cli.agent is not None
        assert cli.router is not None
        assert cli.memory_manager is not None

        validation_results.append(("CLI Tool", "PASSED"))
        print("   [OK] CLI tool initialized successfully")

    except Exception as e:
        validation_results.append(("CLI Tool", f"FAILED: {e}"))
        print(f"   [ERROR] CLI tool failed: {e}")

    # Test 10: API Endpoints
    print("\n10. API Endpoints")
    print("-" * 30)

    try:
        from backend.agents.integration_endpoints import router

        assert router is not None
        assert len(router.routes) > 0

        # Check for key endpoints
        endpoint_paths = [route.path for route in router.routes]
        key_endpoints = ["/conversation", "/complexity", "/agents", "/health"]

        for endpoint in key_endpoints:
            assert any(endpoint in path for path in endpoint_paths), f"Endpoint {endpoint} not found"

        validation_results.append(("API Endpoints", "PASSED"))
        print("   [OK] API endpoints configured correctly")

    except Exception as e:
        validation_results.append(("API Endpoints", f"FAILED: {e}"))
        print(f"   [ERROR] API endpoints failed: {e}")

    # Final Results
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in validation_results:
        print(f"{test_name}: {result}")
        if result == "PASSED":
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 30)
    print(f"TOTAL: {passed + failed} tests")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")

    if failed == 0:
        print("\nSUCCESS: ALL TESTS PASSED!")
        print("LangGraph integration is ready for production.")
        print("\nNext Steps:")
        print("1. Review the migration guide")
        print("2. Update your FraLib pipeline")
        print("3. Deploy to staging")
        print("4. Monitor performance")
    else:
        print(f"\nFAILURE: {failed} tests failed.")
        print("Please review the errors above.")

    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(validate_integration())
    sys.exit(0 if success else 1)