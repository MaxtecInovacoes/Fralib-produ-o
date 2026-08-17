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
    """SDR outreach: builds system prompt from active conversion axes and returns
    a stage-appropriate opening message."""
    from backend.agents.franz.franz_agent_loop import _generate_reply

    lead_data = {
        "nome": payload.nome,
        "cidade": payload.cidade,
        "segmento": payload.segmento,
        "telefone": payload.telefone,
        "whatsapp": payload.whatsapp,
        "rating": payload.rating,
        "site_url": payload.site_url,
        "score_caio": payload.score_caio,
        "tier": payload.tier,
        "lead_id": payload.lead_id,
    }
    reply = _generate_reply(
        nome=payload.nome or "parceiro",
        segmento=payload.segmento or "seu segmento",
        cidade=payload.cidade or "sua região",
        stage="hook",
        mensagem="",
        intent="greeting",
        lead_data=lead_data,
    )
    return FranzOutput(
        reply=reply,
        intent="greeting",
        next_stage="hook",
    )


def _dentro_do_horario() -> bool:
    return True


def _escolher_variante(segmento: str) -> str:
    return "default"


def responder_lead(payload: FranzInput, mensagem: str = "", user_id: int = None):
    """Full SDR response: delegates to franz_agent_loop for intent detection
    and stage-aware reply generation."""
    from backend.agents.franz.franz_agent_loop import franz_agent_loop

    lead_data = {
        "nome": payload.nome,
        "cidade": payload.cidade,
        "segmento": payload.segmento,
        "telefone": payload.telefone,
        "whatsapp": payload.whatsapp,
        "rating": payload.rating,
        "site_url": payload.site_url,
        "score_caio": payload.score_caio,
        "tier": payload.tier,
        "lead_id": payload.lead_id,
    }
    result = franz_agent_loop(
        lead_data=lead_data,
        mensagem=mensagem or "",
        sdr_stage="hook",
        user_id=user_id or payload.tenant_id or 0,
    )
    return FranzOutput(
        reply=result.reply,
        intent=result.intent,
        next_stage=result.novo_stage,
        should_handoff=result.should_handoff,
    )
