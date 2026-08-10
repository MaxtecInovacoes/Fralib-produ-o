# Franz Tools - MCP-like tool definitions for Franz agent loop
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class FranzAgentOutput:
    reply: str
    intent: str
    novo_stage: str
    tools_used: List[str]
    iterations: int
    resposta: str = ""
    should_handoff: bool = False
    followup_date: Optional[str] = None


@dataclass
class ToolResult:
    status: str
    result: Dict[str, Any]
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


# Tool registry: name -> (handler_func, schema)
_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(name: str, schema: Dict[str, Any], handler):
    """Register a Franz tool."""
    _TOOL_REGISTRY[name] = {"schema": schema, "handler": handler}


def execute_tool(tool_name: str, params: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
    """Execute a Franz tool by name."""
    entry = _TOOL_REGISTRY.get(tool_name)
    if not entry:
        return ToolResult(status="error", result={}, error=f"tool not found: {tool_name}")
    try:
        result = entry["handler"](params, context or {})
        return ToolResult(status="ok", result=result)
    except Exception as exc:
        return ToolResult(status="error", result={}, error=str(exc)[:500])


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def _tool_lookup_lead(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Look up lead data from context or DB."""
    lead_id = params.get("lead_id")
    context = ctx.get("lead_data", {})
    if context:
        return {
            "nome": context.get("nome", ""),
            "cidade": context.get("cidade", ""),
            "segmento": context.get("segmento", ""),
            "telefone": context.get("telefone", ""),
            "rating": context.get("rating", 0.0),
            "site_url": ctx.get("site_url", ""),
            "score_caio": context.get("score_caio", 0),
            "tier": context.get("tier", "STANDARD"),
        }
    return {"found": False, "error": "lead_data não disponível no contexto"}


def _tool_check_intent(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Classify lead intent from message."""
    message = (params.get("message") or "").lower().strip()
    # Simple keyword-based intent detection (deterministic fallback)
    intent_keywords = {
        "interesse": ["interesse", "quero", "preciso", "gostaria", "queria"],
        "objecao": ["caro", "nao posso", "nao tenho", "depois", "pensando"],
        "qualificacao": ["preco", "quanto", "valor", "custa", "plano"],
        "opt_out": ["parar", "sair", "cancelar", "nao quero", "remover"],
        "agendamento": ["reuniao", "call", "agendar", "horario", "disponivel"],
    }
    for intent, keywords in intent_keywords.items():
        if any(kw in message for kw in keywords):
            return {"intent": intent, "confidence": 0.7}
    return {"intent": "unknown", "confidence": 0.3}


def _tool_send_template(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Return a pre-approved template message."""
    template_id = params.get("template_id", "default")
    templates = {
        "greeting": "Olá! Tudo bem? Vi que você tem um negócio incrível e queria apresentar uma solução que pode ajudar.",
        "follow_up": "Oi! Estava pensando no que conversamos. Tem algum tempo para eu mostrar como funciona?",
        "closing": "Perfeito! Vou preparar tudo para você. Pode me confirmar o melhor horário?",
        "objection_price": "Entendo o orçamento. Vamos ver o que cabe no seu bolso — tenho opções acessíveis.",
        "objection_time": "Sem problemas! Quando for o melhor momento, estarei por aqui.",
    }
    reply = templates.get(template_id, templates["greeting"])
    return {"template_id": template_id, "reply": reply, "sent": False}


def _tool_escalate_human(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Flag lead for human follow-up."""
    reason = params.get("reason", "complex_question")
    return {"handoff": True, "reason": reason, "queue": "human_sdr"}


# Register tools
register_tool("lookup_lead", {"params": {"lead_id": "int"}}, _tool_lookup_lead)
register_tool("check_intent", {"params": {"message": "str"}}, _tool_check_intent)
register_tool("send_template", {"params": {"template_id": "str"}}, _tool_send_template)
register_tool("escalate_human", {"params": {"reason": "str"}}, _tool_escalate_human)


def get_available_tools() -> List[Dict[str, Any]]:
    """Return list of available tools with schemas."""
    return [{"name": name, "schema": entry["schema"]} for name, entry in _TOOL_REGISTRY.items()]
