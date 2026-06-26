"""Pre-processador de mensagens recebidas do WhatsApp.

Detecta ANTES do Franz processar:
- Respostas automaticas de bots (ex: "Meu nome e Monica, sou assistente...")
- Mensagens de ausencia de recepcao (ex: "Estamos fora do horario")
- Midia sem legenda (ex: [imagem])
- Mensagens reenviadas/encaminhadas
- Mensagens de opt-out claras

Cada categoria tem comportamento especifico, evitando que o Franz
responda de forma inapropriada ou spame o lead com 5 mensagens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MessageType(str, Enum):
    """Tipo da mensagem recebida."""
    LEAD_REAL = "lead_real"           # Mensagem real de um humano (lead)
    BOT_ASSISTANT = "bot_assistant"   # Bot/assistente virtual (Mônica, Bia, etc)
    AUTO_AUSENTE = "auto_ausente"     # Resposta automatica de ausencia
    AUTO_BOAS_VINDAS = "auto_bv"      # Boas-vindas automaticas
    MIDIA_SEM_TEXTO = "midia_vazia"   # Imagem/audio/video sem legenda
    ENCAMINHADA = "encaminhada"       # Mensagem encaminhada de outro chat
    OPT_OUT = "opt_out"               # Pedido explicito de opt-out
    UNKNOWN = "unknown"


@dataclass
class ProcessResult:
    """Resultado do pre-processamento."""
    msg_type: MessageType
    confidence: float
    signals: list[str] = field(default_factory=list)
    action: str = "forward_to_franz"  # forward_to_franz | ask_human | handoff | no_response
    auto_reply: Optional[str] = None   # Resposta automatica sugerida


# Patterns de deteccao por tipo

# Bot/assistente virtual - geralmente se apresenta, tem horarios, fala em nome de alguem
_BOT_PATTERNS = [
    re.compile(r"(meu nome e|me chamo|sou a? assistente|sou o? assistente)", re.I),
    re.compile(r"(atendente|secretaria|recepcionista)\s+(da|do|virtual)", re.I),
    re.compile(r"(horario|horarios)\s+de\s+atendimento", re.I),
    re.compile(r"(em breve|em alguns minutos)\s+(a (nossa |equipe )? equipe|te (respondo|atendo))", re.I),
    re.compile(r"(retornaremos|retornaramos)\s+o?\s+seu\s+contato", re.I),
    re.compile(r"(nao sou uma ia|nao sou um robo|nao e? um bot)", re.I),
    re.compile(r"^\s*ol[áa]?\s*,?\s*seja\s+bem[- ]?vind[ao]?\s*\(?[ao]?\)?\s*[!.]?\s*$", re.I),
    re.compile(r"(atendimento|digital)\s+(das|de)\s+\d", re.I),
    re.compile(r"somos?\s+(uma? )?(clinica|empresa|consultorio|escritorio)", re.I),
    # Patterns adicionais para Curitiba Fitness e similares
    re.compile(r"(a (nossa )?equipe|nos)\s+(entrara|entraremos|entrarei|ira|irao)\s+(em contato|responder)", re.I),
    re.compile(r"(em alguns minutos|a (nossa )?equipe entrara|equipe entrara em contato)", re.I),
    re.compile(r"(nos|equipe)\s+entraremos?\s+em\s+contato", re.I),
    re.compile(r"(em que podemos ajudar|em que podemos te ajudar|em que posso ajudar)", re.I),
    re.compile(r"(seja bem[- ]?vind[oa])\s+(a|à)", re.I),
    # Patterns para bots como Tropa da Nutri, canais de atendimento:
    re.compile(r"(canal|atendimento)\s+de\s+(atendimento|suporte|apoio)\b", re.I),  # "canal de atendimento da..."
    re.compile(r"(e|e um|e uma)\s+(prazer|um prazer|uma honra)\s+(te|em|conhecer|receber|ajudar)", re.I),  # "E um prazer te receber"
    re.compile(r"(em breve|brevemente)\s+(nossa )?equipe\s+(vai|ira|entrara|entraremos|retornara)", re.I),  # "em breve nossa equipe vai te responder"
    re.compile(r"(equipe|nos|time|staff)\s+(vai|ira|retornara|entrara)\s+(te|entrar|lhe|responder|contatar|ajudar)", re.I),
    re.compile(r"^\s*ol[áa]!?\s*[!]?\s*$", re.I),  # msg "Ola!" pura
    re.compile(r"(ap|a o|ao)\s+canal\s+de\s+atendimento", re.I),  # typo comum "ap canal" (deveria ser "ao canal")
    re.compile(r"\b(ap\s+canal|de\s+atendimento|equipe\s+vai|em\s+breve\s+(nossa|equipe|n[ooa]s))\b", re.I),
]

# Resposta de ausencia (recepcao)
_AUSENTE_PATTERNS = [
    re.compile(r"(estamos|estamo)\s+fora\s+(do\s+)?(horario|expediente)", re.I),
    re.compile(r"(recepcao|atendimento)\s+encontra[- ]?se\s+fora", re.I),
    re.compile(r"(retornaremos|retornaramos)\s+o?\s+contato\s+assim\s+que", re.I),
    re.compile(r"(aberto|funcionando)\s+(das|de)\s+\d.*(as|a)s?\s+\d", re.I),
    re.compile(r"obrigad[ao]\s+pela\s+compreensao", re.I),
]

# Opt-out claros (mensagem curta, sem ambiguidade)
_OPT_OUT_PATTERNS = [
    re.compile(r"^\s*(nao|não)\s+quero\s+mais\s+receber", re.I),
    re.compile(r"^\s*remover\s+meu?\s+(numero|contato)", re.I),
    re.compile(r"^\s*me\s+(tira|tire)\s+do\s+contato", re.I),
    re.compile(r"^\s*pare\s+de\s+me\s+(mandar|enviar|ligar)", re.I),
    re.compile(r"^\s*(parar|stop|sair)\s*[.!]?\s*$", re.I),
]


def is_media_without_text(text: str) -> bool:
    """Detecta se a mensagem é mídia sem texto."""
    if not text:
        return True
    t = text.strip().lower()
    return t in ("[mídia]", "[midia]", "[imagem]", "[audio]", "[vídeo]", "[video]", "[documento]", "[sticker]")


def is_forwarded_message(msg_data: dict) -> bool:
    """Detecta se a mensagem foi encaminhada de outro chat."""
    # whatsmeow / MeoWhats geralmente marca forwarding em contextInfo
    context = msg_data.get("contextInfo", {}) if msg_data else {}
    return bool(context.get("isForwarded") or context.get("forwardingScore"))


def classify_incoming_message(text: str, msg_data: Optional[dict] = None) -> ProcessResult:
    """Classifica mensagem recebida e define acao.

    Args:
        text: Texto da mensagem
        msg_data: Dict opcional do JSON do WhatsApp (para detectar forwarding, etc)

    Returns:
        ProcessResult com tipo, confidence, signals e acao recomendada
    """
    if not text or not text.strip():
        return ProcessResult(
            msg_type=MessageType.MIDIA_SEM_TEXTO,
            confidence=1.0,
            signals=["empty_text"],
            action="ask_human",
            auto_reply=(
                "Oi! Recebi sua mensagem mas não veio texto junto. "
                "Pode me escrever o que precisa? 🙂"
            ),
        )

    text_clean = text.strip()

    # 1. Verificar opt-out PRIMEIRO (mais sensivel)
    for pat in _OPT_OUT_PATTERNS:
        if pat.search(text_clean):
            return ProcessResult(
                msg_type=MessageType.OPT_OUT,
                confidence=0.95,
                signals=[pat.pattern[:50]],
                action="no_response",
                auto_reply=None,  # Franz tem mensagem propria
            )

    # 2. Detectar midia sem texto
    if is_media_without_text(text_clean):
        return ProcessResult(
            msg_type=MessageType.MIDIA_SEM_TEXTO,
            confidence=0.95,
            signals=["media_only"],
            action="ask_human",
            auto_reply=(
                "Oi! Recebi sua mídia mas não consigo ver. "
                "Pode me mandar uma mensagem descrevendo o que precisa? 📝"
            ),
        )

    # 3. Detectar encaminhada
    if msg_data and is_forwarded_message(msg_data):
        return ProcessResult(
            msg_type=MessageType.ENCAMINHADA,
            confidence=0.7,
            signals=["forwarded"],
            action="ask_human",
            auto_reply=(
                "Oi! Vi que voce encaminhou uma mensagem. "
                "Pode me contar com suas palavras o que precisa? 🙂"
            ),
        )

    # 4. Detectar ausencia (recepcao)
    ausente_signals = []
    for pat in _AUSENTE_PATTERNS:
        if pat.search(text_clean):
            ausente_signals.append(pat.pattern[:50])
    if len(ausente_signals) >= 1:
        return ProcessResult(
            msg_type=MessageType.AUTO_AUSENTE,
            confidence=min(0.6 + 0.2 * len(ausente_signals), 0.95),
            signals=ausente_signals,
            action="no_response",  # Nao responder agora, aguardar retorno
            auto_reply=None,
        )

    # 5. Detectar bot/assistente virtual
    bot_signals = []
    for pat in _BOT_PATTERNS:
        if pat.search(text_clean):
            bot_signals.append(pat.pattern[:50])

    # Sinais fortes: auto-apresentacao + falar em nome de alguem
    strong_bot_signals = sum(
        1 for s in bot_signals
        if any(kw in s.lower() for kw in [
            "meu nome", "me chamo", "sou a assistente", "sou o assistente",
            "equipe entrara", "equipe entrara em contato",
            "em alguns minutos", "em breve irei",
            "horario", "horarios de atendimento",
        ])
    )

    if len(bot_signals) >= 2 or strong_bot_signals >= 1:
        confidence = min(0.7 + 0.1 * len(bot_signals), 0.95)
        if strong_bot_signals >= 1 and len(bot_signals) == 1:
            confidence = 0.8
        return ProcessResult(
            msg_type=MessageType.BOT_ASSISTANT,
            confidence=confidence,
            signals=bot_signals,
            action="handoff",
            auto_reply=(
                "Oi! Sou o Franz, assistente virtual da FraLib. "
                "Estou entrando em contato sobre uma proposta comercial. "
                "Voce e o responsavel ou prefere que eu fale com alguem da equipe? 🙂"
            ),
        )

    # 6. Se for uma msg CURTA e única, nao e bot (saudacao normal)
    if len(bot_signals) == 1 and len(text_clean.split()) <= 5:
        # Provavelmente saudacao simples, nao bot
        pass

    # Default: mensagem real de lead
    return ProcessResult(
        msg_type=MessageType.LEAD_REAL,
        confidence=0.8,
        signals=bot_signals[:2] if bot_signals else [],
        action="forward_to_franz",
        auto_reply=None,
    )


def should_franz_respond(text: str, msg_data: Optional[dict] = None) -> tuple[bool, Optional[str]]:
    """Helper rapido: Franz deve responder esta mensagem?

    Returns:
        (should_respond: bool, auto_reply_or_none: Optional[str])
        Se should_respond=False, auto_reply e a resposta sugerida (pode ser None).
    """
    result = classify_incoming_message(text, msg_data)
    if result.action == "forward_to_franz":
        return True, None
    if result.action == "no_response":
        return False, None
    # ask_human ou handoff: responder com auto_reply, NAO mandar pro Franz
    return False, result.auto_reply