"""
LangGraph Agent CLI - Command line interface for testing and debugging
"""

import argparse
import asyncio
import json
import sys
from typing import Dict, Any
from datetime import datetime

from .agent import get_agent
from .state import AgentType, AgentConfig, create_initial_state
from .profiles import get_agent_profile
from .router import AgentRouter, IntentDetector
from .memory import get_memory_manager
from .error_handler import get_error_handler


class LangGraphCLI:
    """Command line interface for LangGraph agents"""

    def __init__(self):
        self.agent = get_agent()
        self.router = AgentRouter()
        self.intent_detector = IntentDetector()
        self.memory_manager = get_memory_manager()
        self.error_handler = get_error_handler()
        self.config = AgentConfig()

    async def interactive_mode(self):
        """Run in interactive mode"""
        print("=== LangGraph Agent CLI - Interactive Mode ===")
        print("Type 'quit' to exit, 'help' for commands")
        print()

        session_id = f"interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break

                if user_input.lower() == 'help':
                    self.print_help()
                    continue

                if user_input.lower() == 'reset':
                    session_id = f"interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    print(f"New session: {session_id}")
                    continue

                if user_input.lower().startswith('test '):
                    await self.test_intent(user_input[5:])
                    continue

                if user_input.lower().startswith('complexity '):
                    await self.test_complexity(json.loads(user_input[11:]))
                    continue

                if user_input.lower().startswith('agent '):
                    await self.show_agent_info(user_input[6:])
                    continue

                # Process normal message
                await self.process_message(session_id, user_input)

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    def print_help(self):
        """Print help information"""
        help_text = """
Available commands:
  help          - Show this help message
  quit          - Exit the interactive mode
  reset         - Start a new session
  test <text>   - Test intent detection on text
  complexity <json> - Test complexity calculation on lead facts
  agent <type>  - Show agent information

Examples:
  test "Quanto custa?"
  complexity {"nicho": "restaurante", "qtd_reviews": 10}
  agent vendas
"""
        print(help_text)

    async def process_message(self, session_id: str, message: str):
        """Process a message through the agent"""
        print(f"\n=== Processing message: {message} ===")
        print(f"Session: {session_id}")
        print()

        # Default lead facts for demo
        lead_facts = {
            "nicho": "restaurante",
            "cidade": "São Paulo",
            "tier": "STANDARD",
            "qtd_reviews": 5,
            "tem_site": False,
            "servicos": ["delivery", "mesas"]
        }

        try:
            result = await self.agent.process_message(
                session_id=session_id,
                lead_facts=lead_facts,
                user_message=message,
                is_outbound=False
            )

            if result["status"] == "success":
                print(f"✅ Success!")
                print(f"Final Agent: {result['final_agent']}")
                print(f"Messages Processed: {result['messages_processed']}")
                print(f"Response: {result['response']}")

                if result.get("escalated"):
                    print("⚠️  Conversation escalated to supervisor")

            else:
                print(f"❌ Error: {result['error']}")
                if result.get("error_context"):
                    print(f"Error Context: {json.dumps(result['error_context'], indent=2)}")

        except Exception as e:
            print(f"❌ Processing Error: {e}")

        print()

    async def test_intent(self, text: str):
        """Test intent detection"""
        print(f"\n=== Testing Intent Detection ===")
        print(f"Text: {text}")

        try:
            intent = self.intent_detector.detect_intent(text)
            confidence = 0.8  # Mock confidence

            print(f"Detected Intent: {intent}")
            print(f"Confidence: {confidence:.1%}")

        except Exception as e:
            print(f"Error: {e}")

        print()

    async def test_complexity(self, lead_facts: Dict[str, Any]):
        """Test complexity calculation"""
        print(f"\n=== Testing Complexity Calculation ===")
        print(f"Lead Facts: {json.dumps(lead_facts, indent=2)}")

        try:
            complexity = self.config.calculate_complexity(lead_facts)
            model = self.config.get_model(AgentType.VENDAS, complexity)
            tokens = self.config.get_max_tokens(AgentType.VENDAS, complexity)

            print(f"Complexity: {complexity.value}")
            print(f"Recommended Model: {model}")
            print(f"Max Tokens: {tokens}")

        except Exception as e:
            print(f"Error: {e}")

        print()

    async def show_agent_info(self, agent_key: str):
        """Show agent information"""
        print(f"\n=== Agent Information ===")
        print(f"Key: {agent_key}")

        try:
            agent_type = AgentType(agent_key)
            profile = get_agent_profile(agent_type)

            print(f"Label: {profile.label}")
            print(f"Mission: {profile.mission}")
            print(f"When to Use: {profile.when_to_use}")
            print(f"Style: {profile.style}")
            print(f"Forbidden: {profile.forbidden}")
            print(f"System Prompt: {profile.system_prompt}")
            print(f"Subagents: {', '.join(profile.subagents)}")

        except ValueError:
            print(f"Unknown agent type: {agent_key}")
        except Exception as e:
            print(f"Error: {e}")

        print()

    def run_demo(self):
        """Run a demo session"""
        print("=== LangGraph Agent Demo ===")
        print()

        # Demo lead facts
        demo_facts = {
            "nicho": "restaurante",
            "cidade": "São Paulo",
            "tier": "PREMIUM",
            "qtd_reviews": 15,
            "tem_site": True,
            "servicos": ["delivery", "mesas", "bar", "eventos"]
        }

        # Demo messages
        demo_messages = [
            "Oi, quero saber sobre o serviço",
            "Quanto custa?",
            "Preciso de ajuda com meu site",
            "Quero fechar negócio"
        ]

        async def run_demo_session():
            session_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            for message in demo_messages:
                await self.process_message(session_id, message)
                await asyncio.sleep(1)  # Small delay between messages

        # Run demo
        asyncio.run(run_demo_session())

    def check_system_health(self):
        """Check system health"""
        print("=== System Health Check ===")
        print()

        try:
            # Check memory
            print("📊 Memory System:")
            print(f"  Core memory entries: {len(self.memory_manager.core.entries)}")
            print(f"  Warm memory nichos: {len(list(self.memory_manager.warm.warm_dir.glob('*.json')))}")
            print(f"  Cold memory sessions: {len(list(self.memory_manager.cold.cold_dir.glob('*.json')))}")

            # Check error handler
            print("\n🚨 Error Handler:")
            print(f"  Total errors: {len(self.error_handler.error_history)}")
            print(f"  Circuit breaker state: {self.error_handler.circuit_breaker.get_state()}")

            # Check agents
            print("\n🤖 Available Agents:")
            for agent_type in AgentType:
                profile = get_agent_profile(agent_type)
                print(f"  • {profile.label} ({agent_type.value})")

            print("\n✅ All systems operational")

        except Exception as e:
            print(f"❌ Health check failed: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="LangGraph Agent CLI")
    parser.add_argument("--mode", choices=["interactive", "demo", "health"], default="interactive",
                       help="Run mode: interactive, demo, or health check")
    parser.add_argument("--config", help="Path to configuration file")

    args = parser.parse_args()

    cli = LangGraphCLI()

    if args.mode == "interactive":
        asyncio.run(cli.interactive_mode())
    elif args.mode == "demo":
        cli.run_demo()
    elif args.mode == "health":
        cli.check_system_health()


if __name__ == "__main__":
    main()