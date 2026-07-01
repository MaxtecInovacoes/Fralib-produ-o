"""SDR Intent Classifier.

Classifica o que o lead quis dizer em UMA chamada. Sem LLM por padrao (regex + keywords),
opcional com Haiku call quando confidence < threshold.

Saida: Intent + confidence + signals (quais matches foram encontrados).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# Re-import do enum localmente pra evitar import circular
from .state_machine import Intent


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    signals: list[str] = field(default_factory=list)
    raw_text: str = ""


# Patterns por intent (ordenados por prioridade: do mais especifico ao mais generico)
_PATTERNS: dict[Intent, list[re.Pattern]] = {
    Intent.OPT_OUT: [
        # Opt-out EXPLICITO: precisa de pedido DIRETO de sair/remover/parar.
        # NAO casar com "nao atendo", "nao trabalho com X", "nao sou Y" - essas sao qualificacao.
        # Bug fix: Carolina Ragugnetti 2026-06-25 - LangGraph marcou "nao atendo atletas" como opt_out.
        re.compile(r"\b(para|parar|pare|stop|chega)\s+de\s+me\s+(mandar|enviar|ligar|falar|escrever|contatar)", re.I),
        re.compile(r"\b(me\s+(tira|tire|remove|remova|exclui|exclua))\s*(do\s+contato|da\s+lista|das\s+mensagens)?", re.I),
        re.compile(r"\b(remova|remover|exclui|excluir)\s*(me|meu\s+(numero|contato))", re.I),
        re.compile(r"\b(sair|sai|encerrar|descadastr|descadastra)\w*\s*(da\s+lista|do\s+contato)?", re.I),
        re.compile(r"\b(desculpa|desculpe)\s+(mas\s+)?(nao|não)\s+(quero|posso|tenho\s+interesse|interessa|mais)\b", re.I),
        # Mensagens curtas que sao claramente opt-out (<=4 palavras)
        re.compile(r"^\s*(parar|stop|sair|tchau|adeus|bye)\s*[.!]?\s*$", re.I),
        # Curto e explicito: "nao quero mais" / "nao quero nada" / "nao quero"
        re.compile(r"^\s*(nao|não)\s+(quero|preciso|mais|interessa)\s*(mais|nada)?\s*[.!]?\s*$", re.I),
        re.compile(r"^\s*(me\s+)?(tira|remove|exclui)\s*(me|do\s+contato)?\s*[.!]?\s*$", re.I),
    ],
    Intent.GATEKEEPER: [
        re.compile(r"\b(não\s+sou|nao\s+sou)\s+(o\s+)?(dono|responsavel|encarregado)", re.I),
        re.compile(r"\b(ele|ela|dono)\s+(não|nao)\s+(esta|tá|esteve)", re.I),
        re.compile(r"\b(sou\s+(recepcionista|atendente|secretaria|funcionario|funcionaria))\b", re.I),
        re.compile(r"\b(repasse|encaminhe|manda\s+pro\s+dono)\b", re.I),
    ],
    Intent.BUYING_INTENT: [
        re.compile(r"\b(quero|bora|fechado|aceito|manda|aceitar)\b", re.I),
        re.compile(r"\b(manda\s+o\s+link|quero\s+ver|mostra|mostrar)", re.I),
        re.compile(r"\b(fecha|fechar|contrata|contratar)\b", re.I),
        re.compile(r"\b(como\s+contrato|como\s+faço|como\s+faco)", re.I),
    ],
    Intent.SCHEDULE: [
        # SEM ACENTOS para evitar problemas de encoding
        re.compile(r"\b(amanha|amanha mesmo|depois|mais\s+tarde|outro\s+dia)\b", re.I),
        re.compile(r"\b(semana\s+que\s+vem|proxima\s+semana)\b", re.I),
        re.compile(r"\b(agendar|agenda|marca|marcar|horario)\b", re.I),
        re.compile(r"\b(posso\s+pensar|depois\s+te\s+aviso|depois\s+retorno)\b", re.I),
    ],
    Intent.OBJECTION: [
        # objecao de preco
        re.compile(r"\b(car[oó]|muito\s+caro|não\s+tenho|nao\s+tenho|orçamento|orcamento)\b", re.I),
        re.compile(r"\b(desconto|cupom|promocional|mais\s+barato|mais\s+em\s+conta)\b", re.I),
        re.compile(r"\b(quanto\s+custa|qual\s+o\s+valor|qual\s+o\s+preço|qual\s+o\s+preco)\b", re.I),
        re.compile(r"\b(acordo|parcela|parcelado|boleto|cartão|cartao|pix)\b", re.I),
        # objecao de confianca
        re.compile(r"\b(golpe|fake|fraude|mentira|engano)\b", re.I),
        re.compile(r"\b(quem\s+vocês|quem\s+sao|quem\s+são|quem\s+sao)\b", re.I),
        re.compile(r"\b(não\s+confio|nao\s+confio|não\s+conheço|nao\s+conheco)\b", re.I),
        # objecao de necessidade
        re.compile(r"\b(não\s+preciso|nao\s+preciso|já\s+tenho|ja\s+tenho)\b", re.I),
        re.compile(r"\b(não\s+tenho\s+tempo|nao\s+tenho\s+tempo|sem\s+tempo)\b", re.I),
        re.compile(r"\b(já\s+resolvi|ja\s+resolvi|resolvido)\b", re.I),
    ],
    Intent.QUESTION: [
        re.compile(r"\?", re.I),
        re.compile(r"^(como|quando|onde|qual|quais|por\s+que|porque|o\s+que|oq)\b", re.I),
        re.compile(r"\b(me\s+explica|me\s+conta|explica|conta)\b", re.I),
        re.compile(r"\b(tem\s+como|dá\s+para|da\s+para)\b", re.I),
    ],
    Intent.GREETING: [
        re.compile(r"^(oi|olá|ola|bom\s+dia|boa\s+tarde|boa\s+noite|tudo\s+bem|td\s+bem|blz|belezura|fala|eai)\b", re.I),
        re.compile(r"^\s*(oi|olá|ola|bom\s+dia|boa\s+tarde|boa\s+noite)", re.I),
    ],
    Intent.ACKNOWLEDGMENT: [
        re.compile(r"^(ok|okay|blz|ta|tá|hm|hmm|ah|aham|entendi|combinado|perfeito|show)\s*[.!]?\s*$", re.I),
        re.compile(r"^(sim|não|nao)\s*[.!]?\s*$", re.I),
    ],
}


# Mensagens que claramente sao engajamento (responderam uma pergunta)
_ENGAGEMENT_MARKERS = [
    re.compile(r"\b(porque|por\s+que|pois|afinal|na\s+verdade|na\s+realidade)\b", re.I),
    re.compile(r"\b(nós|nos|a\s+gente|temos|temos|atendemos|funcionamos)\b", re.I),
    re.compile(r"\b(sim|não|nao)\s+(mas|porém|porem|só|so|apenas)", re.I),
    re.compile(r"\b(tem|temos|temos|existimos|abrimos|trabalhamos|usamos|usamos)\b", re.I),
]


def classify_intent(text: str, message_count: int = 0) -> IntentResult:
    """Classifica intent de uma mensagem do lead.

    Args:
        text: mensagem do lead.
        message_count: quantas mensagens o lead ja mandou ate agora (ajuda em desempate).

    Returns:
        IntentResult com intent, confidence (0-1), signals (matches encontrados).
    """
    if not text or not text.strip():
        return IntentResult(intent=Intent.UNKNOWN, confidence=0.0, signals=[], raw_text=text or "")

    text_lower = text.strip()
    if len(text_lower) > 2000:
        text_lower = text_lower[:2000]  # cap

    # Pontua cada intent
    scores: dict[Intent, float] = {intent: 0.0 for intent in Intent}
    signals: dict[Intent, list[str]] = {intent: [] for intent in Intent}

    for intent, patterns in _PATTERNS.items():
        for pat in patterns:
            m = pat.search(text_lower)
            if m:
                scores[intent] += 1.0
                signals[intent].append(m.group(0)[:50])

    # Bonus por marcadores de engajamento
    eng_count = sum(1 for pat in _ENGAGEMENT_MARKERS if pat.search(text_lower))
    if eng_count > 0:
        scores[Intent.ENGAGEMENT] += eng_count * 0.5
        signals[Intent.ENGAGEMENT].append(f"{eng_count} engagement markers")

    # Comprimento da mensagem (mensagens longas com texto sao mais provaveis de ser ENGAGEMENT)
    word_count = len(text_lower.split())
    if word_count >= 8:
        scores[Intent.ENGAGEMENT] += 1.0
        signals[Intent.ENGAGEMENT].append(f"long_msg({word_count}_words)")
    elif word_count >= 3:
        scores[Intent.ENGAGEMENT] += 0.3

    # Tie-breaker para greeting vs question: "tudo bem?", "como vai?", etc.
    # Se for uma pergunta MUITO curta (<=3 palavras), provavelmente é greeting,
    # nao uma pergunta real sobre o negocio.
    if word_count <= 3 and scores[Intent.QUESTION] > 0 and scores[Intent.GREETING] > 0:
        # empate tecnico: greeting vence
        scores[Intent.GREETING] += 0.5

    # Achar intent vencedor
    best_intent = max(scores, key=lambda i: scores[i])
    best_score = scores[best_intent]

    # Se nenhum match -> UNKNOWN
    if best_score == 0:
        return IntentResult(intent=Intent.UNKNOWN, confidence=0.2, signals=[], raw_text=text)

    # Se houver empate (top 2 com mesma score), preferir ordem de prioridade:
    # OPT_OUT > GATEKEEPER > BUYING > SCHEDULE > OBJECTION > QUESTION > ENGAGEMENT > GREETING > ACKNOWLEDGMENT > UNKNOWN
    priority = [
        Intent.OPT_OUT,
        Intent.GATEKEEPER,
        Intent.BUYING_INTENT,
        Intent.SCHEDULE,
        Intent.OBJECTION,
        Intent.QUESTION,
        Intent.ENGAGEMENT,
        Intent.GREETING,
        Intent.ACKNOWLEDGMENT,
        Intent.UNKNOWN,
    ]
    tied = [i for i, s in scores.items() if s == best_score and i != best_intent]
    if tied:
        for p in priority:
            if p == best_intent or p in tied:
                best_intent = p
                break

    # Confidence: normalizar pelo numero maximo de matches possiveis pra aquele intent
    max_possible = max(1.0, float(len(_PATTERNS.get(best_intent, []))))
    confidence = min(1.0, best_score / max_possible)
    if word_count >= 8 and best_intent == Intent.ENGAGEMENT:
        confidence = min(1.0, confidence + 0.2)

    return IntentResult(
        intent=best_intent,
        confidence=round(confidence, 2),
        signals=signals[best_intent][:5],  # top 5 sinais
        raw_text=text,
    )