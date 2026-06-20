"""
Agent Router — Roteamento dinâmico de modelo por complexidade do lead (PRD #7)
Padrão: Agent Routing / Model Gateway
Classifica lead → decide modelo/tokens/temperature por agente.
"""

from contextvars import ContextVar
from typing import Optional

NICHOS_PREMIUM = [
    "restaurante", "hotel", "clinica_estetica", "arquitetura",
    "imobiliaria", "clinica_medica", "advocacia", "odontologia",
]

ROUTING_TABLE = {
    "builder_renderer": {"complexo": "sonnet", "medio": "sonnet", "simples": "sonnet"},
    "arquiteto_mestre": {"complexo": "sonnet", "medio": "sonnet", "simples": "haiku"},
    "designer_prd": {"complexo": "sonnet", "medio": "sonnet", "simples": "sonnet"},
    "agente_nicho": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "agente_variacao": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "validador": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "curadoria": {"complexo": "sonnet", "medio": "sonnet", "simples": "sonnet"},
    "franz": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "bryan": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
}

SKILL_RENDERER_MAX_TOKENS = {"complexo": 16000, "medio": 12000, "simples": 8000}
ARQUITETO_MAX_TOKENS = {"complexo": 6000, "medio": 4000, "simples": 3000}


def calcular_complexidade_lead(facts: dict) -> str:
    score = 0

    qtd_reviews = facts.get("qtd_reviews", 0) or 0
    if qtd_reviews >= 20:
        score += 3
    elif qtd_reviews >= 5:
        score += 1

    nicho = facts.get("nicho") or facts.get("segmento") or ""
    if nicho in NICHOS_PREMIUM:
        score += 3

    tier = facts.get("tier") or ""
    if tier == "PREMIUM":
        score += 3
    elif tier == "STANDARD":
        score += 1

    if facts.get("tem_site"):
        score += 2

    qtd_servicos = len(facts.get("servicos", []) or []) if isinstance(facts.get("servicos"), list) else facts.get("qtd_servicos", 0) or 0
    if qtd_servicos > 8:
        score += 2
    elif qtd_servicos > 4:
        score += 1

    if score >= 7:
        return "complexo"
    elif score >= 3:
        return "medio"
    return "simples"


class AgentRouter:
    def __init__(self, complexidade: str = "medio"):
        self.complexidade = complexidade

    def get_model(self, agente: str) -> str:
        return ROUTING_TABLE.get(agente, {}).get(self.complexidade, "sonnet")

    def get_max_tokens(self, agente: str) -> int:
        if agente == "builder_renderer":
            return SKILL_RENDERER_MAX_TOKENS.get(self.complexidade, 12000)
        elif agente == "arquiteto_mestre":
            return ARQUITETO_MAX_TOKENS.get(self.complexidade, 4000)
        elif agente in ("validador", "franz", "bryan", "agente_variacao"):
            return 2000
        elif agente == "agente_nicho":
            return 3000
        return 4000

    def get_temperature(self, agente: str) -> float:
        temps = {
            "builder_renderer": 0.82 if self.complexidade == "complexo" else 0.72,
            "arquiteto_mestre": 0.5,
            "designer_prd": 0.5,
            "agente_nicho": 0.6,
            "agente_variacao": 0.4,
            "validador": 0.3,
            "franz": 0.7,
            "bryan": 0.7,
        }
        return temps.get(agente, 0.7)

    def escalate(self, agente: str) -> str:
        current = self.get_model(agente)
        escalation = {"haiku": "sonnet", "sonnet": "opus", "opus": "opus"}
        novo = escalation.get(current, "opus")
        if novo != current:
            print(f"[ROUTER] Escalando {agente}: {current} → {novo}")
        return novo

    def resumo(self) -> str:
        modelos = {ag: self.get_model(ag) for ag in ROUTING_TABLE}
        return f"[ROUTER] Complexidade: {self.complexidade} | Modelos: {modelos}"


# ══════════════════════════════════════════════════════════════
# CONTEXT-VAR ROUTER — call_claude consulta automaticamente
# Suporta async/await corretamente (threading.local não funciona com asyncio)
# ══════════════════════════════════════════════════════════════
_router_ctx: ContextVar[Optional["AgentRouter"]] = ContextVar("router", default=None)


def set_router(router: "AgentRouter") -> None:
    _router_ctx.set(router)


def get_router() -> Optional["AgentRouter"]:
    return _router_ctx.get()
