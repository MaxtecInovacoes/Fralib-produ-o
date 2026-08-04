# Franz Tools - MCP-like tool definitions for Franz agent loop
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass
class FranzAgentOutput:
    reply: str
    intent: str
    novo_stage: str
    tools_used: List[str]
    iterations: int
    resposta: str = 
    should_handoff: bool = False

# Tool definitions (stub)
def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Franz tool."""
    return {"status": "ok", "result": {}}
