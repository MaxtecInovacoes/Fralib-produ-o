# Franz SDR Agent
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class FranzInput:
    nome: str
    cidade: str = ""
    segmento: str = ""
    telefone: str = ""
    whatsapp: str = ""
    rating: float = 0.0
    site_url: str = ""
    score_caio: int = 0
    tier: str = "STANDARD"
    proof: Optional[str] = None
    concorrentes: Optional[List[str]] = None
    lead_id: Optional[int] = None
    tenant_id: Optional[int] = None


@dataclass
class FranzOutput:
    reply: str = ""
    intent: str = ""
    next_stage: str = "hook"
    proximo_passo: str = ""
    update_facts: Dict[str, Any] = field(default_factory=dict)
    should_handoff: bool = False


def iniciar_contato(payload: FranzInput, user_id: int = None) -> FranzOutput:
    """Stub - Franz SDR outreach. Implementação completa em franz_tools.py."""
    return FranzOutput(
        reply=f"Olá {payload.nome}! Vi que você tem um negócio em {payload.cidade}. Posso te ajudar com um site profissional?",
        intent="greeting",
        next_stage="hook",
    )


def _dentro_do_horario() -> bool:
    return True


def _escolher_variante(segmento: str) -> str:
    return "default"


def responder_lead(payload, user_id=None):
    return iniciar_contato(payload, user_id)
