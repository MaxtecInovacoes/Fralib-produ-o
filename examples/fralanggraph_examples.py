"""
Example: Using LangGraph agents in FraLib pipeline
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.fralib_integration import FraLibLangGraphIntegration
from backend.agents.langgraph.state import AgentType
from backend.agents.langgraph.endpoints import router as langgraph_router


async def example_pipeline_integration():
    """
    Example of integrating LangGraph agents into FraLib pipeline
    """
    print("=== FraLangGraph Pipeline Integration Example ===\n")

    # Initialize integration
    integration = FraLibLangGraphIntegration()

    # Example 1: Lead qualification conversation
    print("1. Lead Qualification Conversation")
    print("-" * 40)

    lead_facts = {
        "nicho": "restaurante",
        "cidade": "São Paulo",
        "tier": "PREMIUM",
        "qtd_reviews": 25,
        "tem_site": True,
        "servicos": ["delivery", "mesas", "bar", "eventos", "cardapio_digital"],
        "nome_lead": "Restaurante Sabor & Arte"
    }

    # Start conversation
    result = await integration.get_agent_response(
        lead_facts=lead_facts,
        user_message="Oi, sou o proprietário do Restaurante Sabor & Arte",
        current_agent=AgentType.ABORDAGEM
    )

    print(f"Agent: {result['final_agent']}")
    print(f"Response: {result['response']}")
    print(f"Status: {result['status']}\n")

    # Example 2: Price inquiry
    print("2. Price Inquiry Conversation")
    print("-" * 40)

    result = await integration.get_agent_response(
        lead_facts=lead_facts,
        user_message="Quanto custa o serviço de criação de site?",
        current_agent=AgentType.VENDAS
    )

    print(f"Agent: {result['final_agent']}")
    print(f"Response: {result['response']}")
    print(f"Status: {result['status']}\n")

    # Example 3: Technical support
    print("3. Technical Support Conversation")
    print("-" * 40)

    result = await integration.get_agent_response(
        lead_facts=lead_facts,
        user_message="Meu site não está carregando corretamente",
        current_agent=AgentType.ATENDIMENTO
    )

    print(f"Agent: {result['final_agent']}")
    print(f"Response: {result['response']}")
    print(f"Status: {result['status']}\n")

    # Example 4: Follow-up
    print("4. Follow-up Conversation")
    print("-" * 40)

    result = await integration.get_agent_response(
        lead_facts=lead_facts,
        user_message="Lembrei que precisava de ajuda com o site",
        current_agent=AgentType.FOLLOWUP
    )

    print(f"Agent: {result['final_agent']}")
    print(f"Response: {result['response']}")
    print(f"Status: {result['status']}\n")

    print("=== Integration Examples Completed ===")


async def example_complexity_analysis():
    """
    Example of lead complexity analysis
    """
    print("\n=== Lead Complexity Analysis Example ===\n")

    integration = FraLibLangGraphIntegration()

    # Test different lead profiles
    test_leads = [
        {
            "name": "Simple Barber Shop",
            "facts": {
                "nicho": "barbearia",
                "cidade": "Rio de Janeiro",
                "tier": "STANDARD",
                "qtd_reviews": 3,
                "tem_site": False,
                "servicos": ["corte", "barba"]
            }
        },
        {
            "name": "Premium Restaurant",
            "facts": {
                "nicho": "restaurante",
                "cidade": "São Paulo",
                "tier": "PREMIUM",
                "qtd_reviews": 25,
                "tem_site": True,
                "servicos": ["delivery", "mesas", "bar", "eventos", "cardapio_digital"]
            }
        },
        {
            "name": "Medical Clinic",
            "facts": {
                "nicho": "clinica_medica",
                "cidade": "Porto Alegre",
                "tier": "PREMIUM",
                "qtd_reviews": 40,
                "tem_site": True,
                "servicos": ["consultas", "exames", "urgencias", "especialidades"]
            }
        }
    ]

    for lead in test_leads:
        complexity = integration.calculate_lead_complexity(lead["facts"])
        agent_config = integration.get_agent_model_config(AgentType.VENDAS, complexity)

        print(f"Lead: {lead['name']}")
        print(f"Complexity: {complexity}")
        print(f"Recommended Model: {agent_config['model']}")
        print(f"Max Tokens: {agent_config['max_tokens']}")
        print(f"Temperature: {agent_config['temperature']}")
        print("-" * 30)


async def example_memory_learning():
    """
    Example of memory and learning system
    """
    print("\n=== Memory Learning Example ===\n")

    integration = FraLibLangGraphIntegration()

    # Simulate multiple conversations
    conversations = [
        {
            "user": "Quanto custa?",
            "agent": "R$ 1.499 em até 12x sem juros",
            "success": True
        },
        {
            "user": "Preciso de ajuda urgente",
            "agent": "Vou conectar você com um supervisor",
            "success": True
        },
        {
            "user": "Isso é muito caro",
            "agent": "Entendo sua preocupação, temos opções de pagamento",
            "success": False
        }
    ]

    session_id = "learning_example"
    nicho = "restaurante"

    for conv in conversations:
        integration.record_conversation_experience(
            session_id=session_id,
            agent_type=AgentType.VENDAS,
            nicho=nicho,
            user_message=conv["user"],
            agent_response=conv["agent"],
            success=conv["success"]
        )

    # Retrieve memory context
    memory_context = integration.get_memory_context(session_id, AgentType.VENDAS, nicho)

    print(f"Session: {session_id}")
    print(f"Memory Entries: {memory_context['core_entries_count']}")
    print(f"Warm Entries: {memory_context['warm_entries_count']}")
    print(f"Total Tokens: {memory_context['total_tokens']}")
    print("\nCore Memory:")
    print(memory_context['core_memory'])
    print("\nWarm Memory:")
    print(memory_context['warm_memory'])


async def main():
    """
    Main example runner
    """
    print("Starting FraLangGraph Integration Examples...\n")

    try:
        # Run all examples
        await example_pipeline_integration()
        await example_complexity_analysis()
        await example_memory_learning()

        print("\n=== All Examples Completed Successfully! ===")
        print("\nNext Steps:")
        print("1. Review the examples above")
        print("2. Integrate into your FraLib pipeline")
        print("3. Test with real leads")
        print("4. Monitor performance and memory usage")

    except Exception as e:
        print(f"Error running examples: {e}")
        print("Please check the migration guide and ensure all dependencies are installed.")


if __name__ == "__main__":
    asyncio.run(main())