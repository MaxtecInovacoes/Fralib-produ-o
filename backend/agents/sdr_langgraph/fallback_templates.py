"""Sprint 1.5: fallback templates para estagios do Franz.

Problema P1: SDRFallbackError sem fallback. Se LLM falhar 2x seguidas, Franz
fica em silencio (lead recebe timeout sem resposta).

Fix: templates hardcoded por estagio, com texto generico mas profissional.
Se LLM der fallback, usa template. Melhor que silencio.
"""

from __future__ import annotations

from typing import Optional

# Templates por stage. Substituivel por personalizacao futura.
FALLBACK_TEMPLATES: dict[str, list[str]] = {
    "hook": [
        "Oi! Vi que você tem um negócio interessante. Posso te ajudar a atrair mais clientes?",
        "Olá! Tudo bem? Notei seu perfil e achei que poderia te ajudar com algo.",
        "Oi! Posso te contar como outros negócios do seu segmento estão crescendo?",
    ],
    "qualify": [
        "Me conta um pouco mais sobre seu negócio — qual o principal desafio hoje?",
        "Para eu te ajudar melhor, qual seu maior objetivo nos próximos 3 meses?",
        "Você já tentou alguma solução pra isso antes? Como foi a experiência?",
    ],
    "pain": [
        "Entendo. Esse é um problema comum no seu segmento, e tem solução.",
        "Faz sentido. Já ajudei outros negócios parecidos a resolver isso.",
        "Boa pergunta. Vou te mostrar como atacar isso de forma prática.",
    ],
    "amplify": [
        "A maioria dos negócios que conheci tinham esse mesmo desafio, e os que resolveram viram crescimento de 2-3x.",
        "Esse tipo de problema, quando bem atacado, costuma gerar resultado em 30-60 dias.",
        "Faz sentido investir nisso agora. Posso te mostrar um exemplo prático?",
    ],
    "tease": [
        "Posso te mandar um exemplo prático de como funciona, sem compromisso?",
        "Que tal eu te mostrar um案例 real de cliente do seu segmento?",
        "Quer ver um rascunho do que dá pra fazer pro seu negócio em 24h?",
    ],
    "proof": [
        "Deixa eu te mandar um print de resultado de cliente similar.",
        "Tenho cases reais, posso compartilhar contigo.",
        "Vou te enviar um exemplo de site que fizemos pro seu segmento.",
    ],
    "reveal": [
        "Funciona assim: a gente cuida de tudo, você só precisa aprovar no final.",
        "O processo leva em média 5-7 dias, e o investimento é proporcional ao tamanho do negócio.",
        "Você pode começar com um plano simples e crescer conforme os resultados aparecem.",
    ],
    "feedback": [
        "Faz sentido pra você?",
        "Quer que eu te explique melhor algum ponto?",
        "Tem alguma dúvida?",
    ],
    "close": [
        "Posso te mandar o link pra você começar agora?",
        "Quer que eu te ajude a dar o próximo passo?",
        "Se fizer sentido, é só me avisar que eu cuido do resto.",
    ],
    "opt_out": [
        "Tudo bem, sem problema. Se mudar de ideia, é só me chamar. Abraço!",
        "Tranquilo! Quando precisar, estou por aqui. Sucesso!",
    ],
    "greeting": [
        "Oi! Tudo bem?",
        "Olá! Como posso te ajudar hoje?",
    ],
}


def get_fallback(stage: str, *, idx: int = 0) -> Optional[str]:
    """Retorna template de fallback para o stage.

    Args:
        stage: nome do estagio (hook, qualify, pain, etc)
        idx: qual variacao usar (rotaciona entre opcoes)

    Returns:
        String do template, ou None se stage nao tem fallback.
    """
    templates = FALLBACK_TEMPLATES.get(stage)
    if not templates:
        return None
    return templates[idx % len(templates)]


def get_fallback_safe(stage: str) -> str:
    """Retorna fallback ou string generica se stage nao existe."""
    template = get_fallback(stage)
    if template is not None:
        return template
    return "Oi! Como posso te ajudar?"


def get_all_stages() -> list[str]:
    """Lista todos os stages com fallback disponivel."""
    return list(FALLBACK_TEMPLATES.keys())


# ── Humanized delay ──────────────────────────────────────────────────────


def humanized_delay(text: str) -> float:
    """Calcula delay humanizado baseado no tamanho do texto.

    Formula: delay = max(1.5, min(8.0, len(text) / 90 + 2.0))

    - Texto curto (< 90 chars): ~2.0s
    - Texto medio (270 chars): ~5.0s
    - Texto longo (540+ chars): cap em 8.0s
    - Minimo: 1.5s (impede resposta instantanea = bot)
    - Maximo: 8.0s (impede espera longa demais)

    Args:
        text: texto da resposta

    Returns:
        delay em segundos
    """
    if not text:
        return 2.0
    n = len(text)
    return max(1.5, min(8.0, n / 90.0 + 2.0))
