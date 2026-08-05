# Franz Agent Loop - MCP-like agent loop for WhatsApp conversations
from typing import Optional, List, Dict, Any
from .franz_tools import FranzAgentOutput

def franz_agent_loop(lead_id: int, tenant_id: int, message: str, history: List[Dict]) -> FranzAgentOutput:
    """Franz agent loop stub."""
    return FranzAgentOutput(
        reply="Olá! Estou pronto para conversar.",
        intent="greeting",
        novo_stage="hook",
        tools_used=[],
        iterations=0
    )
