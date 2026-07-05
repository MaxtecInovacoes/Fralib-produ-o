"""
Humanization helpers - Anti-robô, variação natural, timing realista.

Implementa os principios do SDD_ATTENDANCE.md:
- Atraso humano variável (1-3s tipico)
- Deteccao de duplicatas (anti-repete-msgs)
- Personalização por perfil do lead
- Wall Street close automático quando hesita
"""
from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass

from backend.agents._text_utils import whitespace_normalize  # noqa: E402  — M13 DRY
from typing import Any, Dict, Optional


# Aberturas variaveis (nao usar sempre "Oi, tudo bem?")
ABERTURAS: Dict[str, list[str]] = {
    "lead_novo": [
        "Vi que vocês",
        "Notei que",
        "Tava olhando",
        "Pesquisei sobre",
        "Me apareceu",
    ],
    "lead_retorno": [
        "Voltando aqui",
        "Sobre o que a gente tava falando",
        "Oi de novo",
        "Tudo certo?",
        "Me conta uma coisa",
    ],
    "lead_objetou": [
        "Entendo",
        "Faz sentido",
        "Hmm, entendi",
        "Justo",
        "Boa",
    ],
    "lead_quente": [
        "Massa",
        "Show",
        "Que bom",
        "Perfeito",
        "Top",
    ],
}

# Closings variaveis (sempre termina com CTA ou Wall Street)
CLOSINGS_NATURAIS: list[str] = [
    "Me conta mais?",
    "Faz sentido pra você?",
    "O que você acha?",
    "Quer ver como fica?",
    "Posso te mandar um exemplo?",
    "Como você vê isso?",
    "Topa dar uma olhada?",
    "Faz sentido pra você?",
]

# Wall Street close - quando lead hesita
WALL_STREET_CLOSES: list[str] = [
    "Já tenho o modelo pronto pro seu segmento. Posso te mandar pra dar uma olhada? 30 segundos do seu tempo. Se curtir, a gente conversa. Se não curtir, descarta. Você não perde nada.",
    "Seu concorrente [X] já saiu na frente com site premium. Não quer ver como tá o seu antes de ficar pra trás?",
    "Todo dia sem site bom é cliente que vai pro concorrente. Posso te mandar o exemplo pronto? Sem compromisso.",
    "Imagina quando alguém pesquisar '[seu negócio] perto de mim' e aparecer um site lindo. Posso te mandar como ficaria o seu?",
]

# Anti-robô: variações de concordância
CONCORDANCIA_VARIAVEL: list[str] = [
    "Concordo",
    "Faz sentido",
    "Justo",
    "Verdade",
    "Boa",
    "Entendi",
    "Hmm, sim",
    "Pois é",
]


@dataclass(frozen=True)
class HumanizeDelay:
    seconds: float
    reason: str


def calc_humanize_delay(
    *,
    last_response_time_min: Optional[float],
    is_objetou: bool,
    is_first_msg: bool,
    is_quente: bool,
) -> HumanizeDelay:
    """Calcula delay humanizado antes de enviar msg.

    Regras (SDD §1.4):
    - Lead quente (< 2min) → 1-2s
    - Lead morno (2-30min) → 30-90s
    - Lead frio (> 30min) → 1-3min
    - Primeira msg (cold) → 2-4s
    - Pós-objecao → 3-5s
    - Lead quente engajado → 1-2s
    """
    if is_first_msg:
        return HumanizeDelay(random.uniform(2.0, 4.0), "primeira_msg_cold")
    if is_objetou:
        return HumanizeDelay(random.uniform(3.0, 5.0), "pos_objeção_pensando")
    if is_quente:
        return HumanizeDelay(random.uniform(1.0, 2.0), "lead_quente_engajado")
    if last_response_time_min is None:
        return HumanizeDelay(random.uniform(1.5, 3.0), "default")
    if last_response_time_min < 2:
        return HumanizeDelay(random.uniform(1.0, 2.0), "respondeu_rapido")
    if last_response_time_min < 30:
        return HumanizeDelay(random.uniform(30, 90), "respondeu_morno")
    return HumanizeDelay(random.uniform(60, 180), "respondeu_frio")


def detect_msg_duplicate(
    new_msg: str,
    previous_msgs: list[str],
    *,
    threshold: float = 0.55,
) -> bool:
    """Detecta se a msg nova é quase igual a alguma anterior (anti-repete).

    Usa similaridade Jaccard em trigrama + palavras.
    Threshold 0.55 captura msgs muito similares (mesmo conteudo, palavras trocadas).
    """
    if not previous_msgs:
        return False
    new_trigrams = _trigrams(new_msg.lower())
    if not new_trigrams:
        return False
    new_words = _words(new_msg.lower())
    for prev in previous_msgs:
        prev_trigrams = _trigrams(prev.lower())
        if not prev_trigrams:
            continue
        prev_words = _words(prev.lower())
        # Jaccard em trigrama
        jaccard_trigram = len(new_trigrams & prev_trigrams) / len(new_trigrams | prev_trigrams)
        # Jaccard em palavras
        jaccard_word = len(new_words & prev_words) / max(len(new_words | prev_words), 1)
        # Score combinado (mais permissivo)
        score = max(jaccard_trigram, jaccard_word * 0.95)
        if score >= threshold:
            return True
    return False


def _words(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return set(text.split())


def _trigrams(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = whitespace_normalize(text)
    words = text.split()
    if not words:
        return set()
    return {f"#{w}#" for w in words} | {" ".join(words[i:i + 2]) for i in range(len(words) - 1)}


def msg_hash(text: str) -> str:
    """Hash curto pra dedup persistente."""
    return hashlib.sha256(text.lower().strip().encode("utf-8")).hexdigest()[:16]


def pick_wall_street_close(segment: str = "") -> str:
    """Wrapper retrocompativel: pega Wall Street close especifico do segmento."""
    base = random.choice(WALL_STREET_CLOSES)
    # Personaliza pelo segmento se aplicavel
    if segment and "modelo pronto pro seu segmento" in base:
        return base.replace("pro seu segmento", f"pro {segment}")
    return base


def pick_opening(context: str = "lead_novo") -> str:
    """Pega abertura variavel baseada no contexto da conversa.

    Args:
        context: tipo de lead
            - lead_novo: primeira interacao
            - lead_retorno: voltou apos tempo
            - lead_objetou: acabou de objetar
            - lead_quente: engajado e interessado

    Returns:
        String com abertura natural para usar na msg
    """
    openings = ABERTURAS.get(context, ABERTURAS["lead_novo"])
    return random.choice(openings)


def pick_closing(natural: bool = True) -> str:
    """Pega closing variavel natural ou Wall Street.

    Args:
        natural: True = closing natural (CTAs), False = Wall Street close

    Returns:
        String com closing para append na msg
    """
    if natural:
        return random.choice(CLOSINGS_NATURAIS)
    return pick_wall_street_close()


def pick_concordancia() -> str:
    """Pega variacao de concordancia/resposta.

    Returns:
        String como "Faz sentido", "Justo", etc.
    """
    return random.choice(CONCORDANCIA_VARIAVEL)


def is_robot_like(msg: str) -> bool:
    """Detecta se msg parece robô. Retorna True se parecer."""
    robot_signals = [
        r"(?i)excelente pergunta",
        r"(?i)temos a solução ideal",
        r"(?i)poderia me informar",
        r"(?i)seria um prazer",
        r"(?i)agradeço o contato",
        r"(?i)fico à disposição",
        r"!!+",
        r"💪🔥🚀|✨💯|🎉🎊",
    ]
    return any(re.search(p, msg) for p in robot_signals)
