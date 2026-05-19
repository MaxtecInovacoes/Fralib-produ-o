"""
Agent Router — Roteamento dinâmico de modelo por complexidade do lead (PRD #7)
Padrão: Agent Routing / Model Gateway
Classifica lead → decide modelo/tokens/temperature por agente.
"""


NICHOS_PREMIUM = [
    "restaurante", "hotel", "clinica_estetica", "arquitetura",
    "imobiliaria", "clinica_medica", "advocacia", "odontologia",
]

ROUTING_TABLE = {
    "liam": {"complexo": "opus", "medio": "opus", "simples": "sonnet"},
    "arquiteto": {"complexo": "sonnet", "medio": "sonnet", "simples": "haiku"},
    "theo": {"complexo": "sonnet", "medio": "haiku", "simples": "haiku"},
    "liz": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "bryan": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "liam_critica": {"complexo": "haiku", "medio": "haiku", "simples": "haiku"},
    "liam_revisao": {"complexo": "opus", "medio": "sonnet", "simples": "sonnet"},
}

LIAM_MAX_TOKENS = {"complexo": 8000, "medio": 6000, "simples": 4000}
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
        if agente == "liam":
            return LIAM_MAX_TOKENS.get(self.complexidade, 6000)
        elif agente == "arquiteto":
            return ARQUITETO_MAX_TOKENS.get(self.complexidade, 4000)
        elif agente in ("liz", "bryan", "liam_critica"):
            return 2000
        elif agente == "theo":
            return 3000
        return 4000

    def get_temperature(self, agente: str) -> float:
        temps = {
            "liam": 0.9 if self.complexidade == "complexo" else 0.7,
            "arquiteto": 0.5,
            "theo": 0.6,
            "liz": 0.3,
            "bryan": 0.7,
            "liam_critica": 0.2,
            "liam_revisao": 0.3,
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
# THREAD-LOCAL ROUTER — call_claude consulta automaticamente
# ══════════════════════════════════════════════════════════════
import threading
_thread_local = threading.local()


def set_router(router):
    _thread_local.router = router


def get_router():
    return getattr(_thread_local, 'router', None)
