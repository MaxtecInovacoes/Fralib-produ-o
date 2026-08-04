# Franz SDR Agent (substitui Bryan legacy)
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import os
import json


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
    """Stub - Franz SDR outreach."""
    return FranzOutput(
        reply=f"Ola {payload.nome}! Vi que voce tem um negocio em {payload.cidade}. Posso te ajudar?",
        intent="greeting",
        next_stage="hook",
    )


def _dentro_do_horario() -> bool:
    return True


def _escolher_variante(segmento: str) -> str:
    return "default"


# Backward compatibility aliases for bryan->franz migration
BryanInput = FranzInput
BryanOutput = FranzOutput


def responder_lead(payload, user_id=None):
    return iniciar_contato(payload, user_id)
