"""BANT/MEDDIC extractor - detecta e extrai informacoes de qualificacao.

BANT = Budget, Authority, Need, Timeline
MEDDIC = Metrics, Economic buyer, Decision criteria, Decision process,
         Identify pain, Champion

A deteccao e feita por:
1. Regex patterns (rapido, comum)
2. LLM fallback (casos ambiguos)

Resultado e salvo em LeadMemory (campos bant_*, meddic_*).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BudgetLevel(str, Enum):
    NAO_QUIS_DIZER = "nao_quero_dizer"
    MENOS_500 = "menos_500"
    DE_500_A_1500 = "500_1500"
    DE_1500_A_5000 = "1500_5000"
    MAIS_5000 = "mais_5000"
    JA_TEM = "ja_tem_site"
    PIX = "pix"  # pediu pix/pagamento rapido

    @property
    def score(self) -> int:
        return {
            "nao_quero_dizer": 0,
            "menos_500": 5,
            "500_1500": 8,
            "1500_5000": 10,
            "mais_5000": 10,
            "ja_tem_site": 3,
            "pix": 7,
        }.get(self.value, 0)


class AuthorityLevel(str, Enum):
    DECISOR = "decisor"  # "eu decido", "sou dono"
    INFLUENCIA = "influencia"  # "vou ver com meu socio"
    CONSULTA = "consulta"  # "preciso falar com..."
    NAO_SEI = "nao_sei"  # "nao sei dizer"

    @property
    def score(self) -> int:
        return {
            "decisor": 5,
            "influencia": 3,
            "consulta": 1,
            "nao_sei": 0,
        }.get(self.value, 0)


class TimelineLevel(str, Enum):
    URGENTE = "urgente"  # "preciso pra ontem", "essa semana"
    TRINTA_DIAS = "30_dias"
    NOVENTA_DIAS = "90_dias"
    SEM_PREVISAO = "sem_previsao"

    @property
    def score(self) -> int:
        return {
            "urgente": 10,
            "30_dias": 8,
            "90_dias": 5,
            "sem_previsao": 1,
        }.get(self.value, 0)


# Patterns regex para deteccao
BUDGET_PATTERNS = [
    (r"(?i)menos\s+(?:de\s+)?(?:r\$?\s*)?500", BudgetLevel.MENOS_500),
    (r"(?i)(?:r\$?\s*)?(?:1\.|uma?\s+)?(?:a\s+)?1\.?500", BudgetLevel.DE_500_A_1500),
    (r"(?i)(?:r\$?\s*)?2\.?500|2\.?500\s+a\s+5\.?000|2\s+a\s+5|\br\$\s*2\.?000\b|\br\$\s*3000\b", BudgetLevel.DE_1500_A_5000),
    (r"(?i)(?:r\$?\s*)?5\.?000\s+ou\s+mais|mais\s+de\s+5", BudgetLevel.MAIS_5000),
    (r"(?i)ja\s+tenho\s+site|tenho\s+site", BudgetLevel.JA_TEM),
    (r"(?i)no\s+pix|a\s+vista|pagamento\s+rapido", BudgetLevel.PIX),
    (r"(?i)nao\s+(?:quero\s+)?(?:te\s+)?dizer|particular", BudgetLevel.NAO_QUIS_DIZER),
]

AUTHORITY_PATTERNS = [
    # INFLUENCIA primeiro: "vou ver com socio" NAO deve virar DECISOR
    (r"(?i)vou\s+ver\s+com\s+(?:meu|o)\s+(?:socio|chefe|esposa|marido|patrao)|preciso\s+ver\s+com", AuthorityLevel.INFLUENCIA),
    (r"(?i)eu\s+(?:sou\s+)?dono|eu\s+mesmo\s+decido|eu\s+decido|eu\s+comando|sou\s+(?:o\s+)?dono|eu\s+sou\s+socio\s+unico", AuthorityLevel.DECISOR),
    (r"(?i)preciso\s+(?:falar|conversar|consultar|pedir)", AuthorityLevel.CONSULTA),
    (r"(?i)nao\s+sei\s+(?:te\s+)?dizer|depende", AuthorityLevel.NAO_SEI),
]

TIMELINE_PATTERNS = [
    (r"(?i)(?:preciso|quero|ja)\s+(?:pra|para|nessa|esta|nesse)\s+(?:semana|hoje|ontem|amanha|agora)", TimelineLevel.URGENTE),
    (r"(?i)urgente|com\s+pressa|rapido", TimelineLevel.URGENTE),
    (r"(?i)30\s+dias|um\s+mes|este\s+mes|mes\s+que\s+vem", TimelineLevel.TRINTA_DIAS),
    (r"(?i)90\s+dias|tres\s+meses|trimestre|proximo\s+trimestre", TimelineLevel.NOVENTA_DIAS),
    (r"(?i)sem\s+previsao|nao\s+tenho\s+prazo|um\s+dia\s+destes|quando\s+der", TimelineLevel.SEM_PREVISAO),
]

NEED_INDICATORS = [
    r"(?i)preciso\s+(?:de|um)",
    r"(?i)meu\s+problema\s+e",
    r"(?i)ta\s+dificil",
    r"(?i)nao\s+funciona",
    r"(?i)perco\s+cliente",
    r"(?i)preciso\s+aumentar",
    r"(?i)quero\s+crescer",
    r"(?i)meu\s+concorrente",
    r"(?i)trafego",
    r"(?i)conversao",
    r"(?i)divulgar",
    r"(?i)aparecer\s+no\s+google",
    r"(?i)vender\s+mais",
    r"(?i)captação",
    r"(?i)lead\s+novo",
    r"(?i)novos\s+clientes",
]

PAIN_PATTERNS = [
    r"(?i)site\s+(?:velho|feio|lento|quebrado|nao\s+funciona)",
    r"(?i)sem\s+(?:site|presenca\s+digital)",
    r"(?i)nao\s+aparece\s+(?:no\s+)?google",
    r"(?i)perco\s+cliente",
    r"(?i)(?:orcamento|grana)\s+apertado",
    r"(?i)concorrente\s+(?:na\s+)?frente",
    r"(?i)divulgar\s+meu\s+(?:trabalho|servico|negocio)",
    r"(?i)agenda\s+vazia",
    r"(?i)horario\s+ocioso",
    r"(?i)(?:taxa|comissao)\s+alta\s+do\s+app",
]

CHAMPION_PATTERNS = [
    r"(?i)(?:eu|me)\s+(?:vou\s+)?(?:defender|apoiar|indicar|comprar|fechar)",
    r"(?i)vou\s+(?:defender|apoiar|indicar|levar|comprar|fechar)",
    r"(?i)(?:sou|estou)\s+aqui\s+para\s+ajudar",
    r"(?i)levo\s+isso\s+(?:adante|adiante|a\s+frente)",
    r"(?i)interesso\s+(?:pelo|nesse)\s+assunto",
    r"(?i)defendo\s+(?:isso|esta|esta\s+ideia)",
    r"(?i)eu\s+compro\s+a\s+ideia",
]


@dataclass(frozen=True)
class BantResult:
    budget: BudgetLevel | None
    authority: AuthorityLevel | None
    need_score: int  # 0-10
    timeline: TimelineLevel | None
    total_score: int
    confidence: float  # 0-1


@dataclass(frozen=True)
class MeddicResult:
    metrics: str
    economic_buyer: str
    decision_criteria: str
    decision_process: str
    pain_identified: str
    champion: bool
    total_score: int  # 0-10


def detect_budget(msg: str) -> BudgetLevel | None:
    """Detecta orcamento mencionado na mensagem."""
    for pattern, level in BUDGET_PATTERNS:
        if re.search(pattern, msg):
            return level
    return None


def detect_authority(msg: str) -> AuthorityLevel | None:
    """Detecta nivel de autoridade do lead."""
    for pattern, level in AUTHORITY_PATTERNS:
        if re.search(pattern, msg):
            return level
    return None


def detect_timeline(msg: str) -> TimelineLevel | None:
    """Detecta urgencia/prazo."""
    for pattern, level in TIMELINE_PATTERNS:
        if re.search(pattern, msg):
            return level
    return None


def compute_need_score(msg: str) -> int:
    """Calcula score de necessidade baseado em indicadores."""
    score = 0
    for pattern in NEED_INDICATORS:
        if re.search(pattern, msg):
            score += 1
    return min(score * 2, 10)  # cap em 10


def compute_bant(messages: list[str]) -> BantResult:
    """Calcula BANT agregado a partir de historico de mensagens."""
    budget = None
    authority = None
    timeline = None
    need_total = 0
    count = 0
    for msg in messages:
        count += 1
        # Pega o primeiro match (mais confiavel)
        b = detect_budget(msg)
        if b and not budget:
            budget = b
        a = detect_authority(msg)
        if a and not authority:
            authority = a
        t = detect_timeline(msg)
        if t and not timeline:
            timeline = t
        need_total += compute_need_score(msg)

    avg_need = min(need_total, 10) if count > 0 else 0
    total = (
        (budget.score if budget else 0)
        + (authority.score if authority else 0)
        + avg_need
        + (timeline.score if timeline else 0)
    )
    # Confianca baseada em quantas dimensoes foram detectadas
    detected = sum(1 for x in [budget, authority, timeline] if x)
    has_need = avg_need > 0
    confidence = (detected + (1 if has_need else 0)) / 4.0
    return BantResult(
        budget=budget,
        authority=authority,
        need_score=avg_need,
        timeline=timeline,
        total_score=total,
        confidence=confidence,
    )


def compute_meddic(messages: list[str]) -> MeddicResult:
    """Calcula MEDDIC agregado."""
    all_text = " ".join(messages)
    # Metrics: detectar mencao a numeros/resultados
    metrics_match = re.search(
        r"(?i)(?:quero|preciso|atingir|lutar)\s+([\w][\w\s]{4,80}?)(?:\.|$|,|\s\s|que)",
        all_text,
    )
    metrics = metrics_match.group(1).strip() if metrics_match else ""
    # Economic buyer: quem paga
    eb_match = re.search(
        r"(?i)(?:eu|meu|minha)\s+(dono|socio|esposa|marido|patrao|pai|mae)\s+(?:que\s+)?(?:paga|decide|aprova)",
        all_text,
    )
    eb = eb_match.group(0) if eb_match else ""
    # Decision criteria
    dc_match = re.search(
        r"(?i)(?:importa|preciso\s+que|conta\s+que)\s+([\w\s]{5,80}?)(?:\.|$)",
        all_text,
    )
    decision_criteria = dc_match.group(1).strip() if dc_match else ""
    # Pain
    pain_set = set()
    for pattern in PAIN_PATTERNS:
        for m in re.finditer(pattern, all_text):
            pain_set.add(m.group(0).strip())
    pain = " | ".join(sorted(pain_set)[:3]) if pain_set else ""
    # Champion
    champion = any(re.search(p, all_text) for p in CHAMPION_PATTERNS)
    # Score
    score = 0
    if metrics:
        score += 2
    if eb:
        score += 1
    if decision_criteria:
        score += 2
    if pain:
        score += 3
    if champion:
        score += 2
    return MeddicResult(
        metrics=metrics,
        economic_buyer=eb,
        decision_criteria=decision_criteria,
        decision_process="",
        pain_identified=pain,
        champion=champion,
        total_score=min(score, 10),
    )
