"""Pre-processador inteligente de mensagens recebidas do WhatsApp.

Estrategia fail-closed (3 niveis):
1. Regex rapida: casos OBVIOS (midia sem texto, opt-out explicito, ausencia)
2. Heuristicas: bloqueio apenas quando ha certeza alta de bot
3. LLM: juiz final pra casos ambiguos (bot vs lead real)

Por que nao regex pra tudo? Cada lead tem contexto diferente. Regex nunca
consegue cobrir todas variacoes. LLM com contexto do tenant faz melhor.

Custo: cache 24h reduz a zero em msgs repetidas.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MessageType(str, Enum):
    """Tipo da mensagem recebida."""
    LEAD_REAL = "lead_real"           # Mensagem real de um humano (lead)
    BOT_ASSISTANT = "bot_assistant"   # Bot/assistente virtual (Mônica, Tropa da Nutri, etc)
    AUTO_AUSENTE = "auto_ausente"     # Resposta automatica de ausencia
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
    auto_reply: Optional[str] = None


# ════════════════════════════════════════════════════════════════════
# NIVEL 1: REGEX RAPIDA - casos obvios
# ════════════════════════════════════════════════════════════════════

# Opt-out EXPLÍCITO (palavras CLARAS de bloqueio)
_OPT_OUT_PATTERNS = [
    re.compile(r"^\s*(nao|não)\s+quero\s+mais\s+receber", re.I),
    re.compile(r"^\s*remover\s+meu?\s+(numero|contato)", re.I),
    re.compile(r"^\s*me\s+(tira|tire)\s+do\s+contato", re.I),
    re.compile(r"^\s*pare\s+de\s+me\s+(mandar|enviar|ligar)", re.I),
    re.compile(r"^\s*(parar|stop|sair|tchau)\s*[.!]?\s*$", re.I),
]

# Midia sem texto (placeholders do MeoWhats)
_MEDIA_PLACEHOLDERS = {"[mídia]", "[midia]", "[imagem]", "[audio]", "[vídeo]", "[video]", "[documento]", "[sticker]"}

# Resposta de ausencia (recepcao)
_AUSENTE_PATTERNS = [
    re.compile(r"(estamos|estamo)\s+fora\s+(do\s+)?(horario|expediente)", re.I),
    re.compile(r"(recepcao|atendimento)\s+encontra[- ]?se\s+fora", re.I),
    re.compile(r"(retornaremos|retornaramos)\s+o?\s+contato\s+assim\s+que", re.I),
    re.compile(r"(aberto|funcionando)\s+(das|de)\s+\d.*(as|a)s?\s+\d", re.I),
]


def _check_opt_out(text: str) -> bool:
    return any(p.search(text) for p in _OPT_OUT_PATTERNS)


def _check_media(text: str) -> bool:
    return text.strip().lower() in _MEDIA_PLACEHOLDERS


def _check_ausente(text: str) -> bool:
    return any(p.search(text) for p in _AUSENTE_PATTERNS)


# ════════════════════════════════════════════════════════════════════
# NIVEL 2: HEURISTICAS - features simples
# ════════════════════════════════════════════════════════════════════

def _heuristic_features(text: str) -> dict[str, float]:
    """Extrai features da msg pra ajudar decisao."""
    text_lower = text.lower()
    word_count = len(text_lower.split())

    # Auto-apresentacao (comum em bots)
    has_self_intro = bool(re.search(r"\b(meu nome|me chamo|sou [oa]? ?(assistente|recepcionista|atendente))\b", text_lower))

    # Horario de atendimento (comum em recepcao automatizada)
    has_schedule = bool(re.search(r"\b(horario|horarios|das?\s+\d.*[aá]s?\s+\d|segunda.*sexta)\b", text_lower))

    # Equipe falando (comum em bots) - "nossa equipe", "minha equipe", "nos vamos"
    has_team_speaking = bool(re.search(r"\b(nossa equipe|minha equipe|nos vamos|a gente)\b", text_lower))

    # Emoji de boas-vindas (🤗👋✨ comum em bots)
    has_welcome_emoji = bool(re.search(r"[\U0001F91F\U0001F44B✨\U0001F64C]", text))

    # Texto curto (bot costuma mandar msgs curtas de boas-vindas)
    is_short = word_count <= 8

    return {
        "word_count": word_count,
        "has_self_intro": 1.0 if has_self_intro else 0.0,
        "has_schedule": 1.0 if has_schedule else 0.0,
        "has_team_speaking": 1.0 if has_team_speaking else 0.0,
        "has_welcome_emoji": 1.0 if has_welcome_emoji else 0.0,
        "is_short": 1.0 if is_short else 0.0,
    }


def _heuristic_bot_score(features: dict[str, float]) -> float:
    """Score de 0.0 (claramente lead) a 1.0 (claramente bot).

    Combina features simples. NAO decide sozinho - e heuristica inicial.
    """
    score = 0.0
    # Pesos calibrados pra msgs de bot comuns
    score += features["has_self_intro"] * 0.6       # "Meu nome e Bia, sou assistente" - muito forte
    score += features["has_schedule"] * 0.3        # "Horarios de atendimento"
    score += features["has_team_speaking"] * 0.4   # "nossa equipe vai te responder"
    score += features["has_welcome_emoji"] * 0.2   # saudacao com emoji
    score += features["is_short"] * 0.1
    return min(score, 1.0)


# ════════════════════════════════════════════════════════════════════
# NIVEL 3: SONNET LLM - juiz final
# ════════════════════════════════════════════════════════════════════

_LLM_CACHE: dict[str, tuple[float, "ProcessResult"]] = {}
_LLM_CACHE_TTL = 86400  # 24h
_LLM_CACHE_LOCK = __import__("threading").Lock()

# Prompts do Sonnet (otimizados pra baixa latencia/custo)
_LLM_SYSTEM_PROMPT = """Voce classifica uma mensagem de WhatsApp Business de um lead em UMA categoria.

CATEGORIAS:
- LEAD_REAL: humano respondendo (pergunta, duvida, qualificacao, agendamento, conversa)
- BOT_ASSISTANT: resposta automatica de bot/assistente virtual
- AUTO_AUSENTE: resposta de recepcao fora do horario

BOT_ASSISTANT tem estas marcas tipicas:
- Se apresenta como assistente/atendente/recepcionista/canal de atendimento
- Diz "em breve nossa equipe vai te responder" ou similar
- Diz "e um prazer te receber"
- Canal de atendimento/suporte
- Horarios de atendimento

LEAD_REAL responde perguntas, fala sobre o negocio, ou tem tom pessoal.

Responda APENAS JSON: {"tipo": "LEAD_REAL"|"BOT_ASSISTANT"|"AUTO_AUSENTE", "confianca": 0.0-1.0}"""


def _call_llm_classifier(text: str) -> tuple[str, float, str]:
    """Chama LLM pra classificar. Se falhar, levanta erro e bloqueia automacao."""
    from agents.llm_direct import call_claude
    import json

    response = call_claude(
        system=_LLM_SYSTEM_PROMPT,
        user=text[:500],
        model="haiku",  # classificador barato, mas sem fallback silencioso
        max_tokens=50,
        temperature=0.0,
        agent_name="sdr_msg_classifier",
        respect_agent_config=False,
        enable_context=False,
    ).strip()

    response_clean = response.replace("```json", "").replace("```", "").strip()

    # Tentar parse JSON direto
    try:
        data = json.loads(response_clean)
    except json.JSONDecodeError as exc:
        # Tentar extrair JSON, mas sem inferir por palavra-chave.
        m = re.search(r'\{[^{}]*\}', response_clean)
        if not m:
            raise ValueError("message classifier returned non-json output") from exc
        try:
            data = json.loads(m.group())
        except Exception as nested_exc:
            raise ValueError("message classifier returned invalid json object") from nested_exc

    tipo = str(data.get("tipo", "")).strip().upper()
    if tipo not in {"LEAD_REAL", "BOT_ASSISTANT", "AUTO_AUSENTE"}:
        raise ValueError(f"message classifier returned unsupported tipo: {tipo!r}")
    confianca = float(data.get("confianca", 0.0))
    if not 0.0 <= confianca <= 1.0:
        raise ValueError(f"message classifier returned invalid confianca: {confianca!r}")
    return tipo, confianca, "haiku_classifier"


def _llm_classify_cached(text: str) -> tuple[str, float, str]:
    """Classifica com cache 24h."""
    cache_key = hashlib.sha256(text.strip().lower().encode()).hexdigest()[:32]

    with _LLM_CACHE_LOCK:
        cached = _LLM_CACHE.get(cache_key)
        if cached and (time.time() - cached[0]) < _LLM_CACHE_TTL:
            return cached[1]

    tipo, confianca, motivo = _call_llm_classifier(text)

    with _LLM_CACHE_LOCK:
        # Limpar cache se muito grande
        if len(_LLM_CACHE) > 10000:
            _LLM_CACHE.clear()
        _LLM_CACHE[cache_key] = (time.time(), (tipo, confianca, motivo))

    return tipo, confianca, motivo


# ════════════════════════════════════════════════════════════════════
# ORQUESTRADOR - decide qual nivel usar
# ════════════════════════════════════════════════════════════════════

def classify_incoming_message(text: str, msg_data: Optional[dict] = None) -> ProcessResult:
    """Classifica mensagem recebida usando estrategia hibrida.

    Args:
        text: Texto da mensagem
        msg_data: Dict opcional do JSON do WhatsApp

    Returns:
        ProcessResult com tipo, confidence, signals e acao recomendada
    """
    if not text or not text.strip():
        return ProcessResult(
            msg_type=MessageType.MIDIA_SEM_TEXTO,
            confidence=1.0,
            signals=["empty_text"],
            action="ask_human",
            auto_reply="Oi! Recebi sua mensagem mas nao veio texto junto. Pode me escrever o que precisa? 🙂",
        )

    text_clean = text.strip()

    # ═══ NIVEL 1: REGEX RAPIDA (casos obvios) ═══

    # Opt-out explicito
    if _check_opt_out(text_clean):
        return ProcessResult(
            msg_type=MessageType.OPT_OUT,
            confidence=0.95,
            signals=["opt_out_pattern"],
            action="no_response",
        )

    # Midia sem texto
    if _check_media(text_clean):
        return ProcessResult(
            msg_type=MessageType.MIDIA_SEM_TEXTO,
            confidence=0.95,
            signals=["media_placeholder"],
            action="ask_human",
            auto_reply="Oi! Recebi sua midia mas nao consigo ver. Pode me mandar uma mensagem descrevendo o que precisa? 📝",
        )

    # Encaminhada
    if msg_data and msg_data.get("contextInfo", {}).get("isForwarded"):
        return ProcessResult(
            msg_type=MessageType.ENCAMINHADA,
            confidence=0.7,
            signals=["forwarded"],
            action="ask_human",
            auto_reply="Oi! Vi que voce encaminhou uma mensagem. Pode me contar com suas palavras o que precisa? 🙂",
        )

    # Ausencia de recepcao
    if _check_ausente(text_clean):
        return ProcessResult(
            msg_type=MessageType.AUTO_AUSENTE,
            confidence=0.9,
            signals=["ausente_pattern"],
            action="no_response",
        )

    # ═══ NIVEL 2: HEURISTICAS (features simples) ═══
    features = _heuristic_features(text_clean)
    heuristic_score = _heuristic_bot_score(features)

    # Se heuristica tem MUITA certeza (>=0.6 = bot OBVIO), nao chama LLM
    if heuristic_score >= 0.6:
        return ProcessResult(
            msg_type=MessageType.BOT_ASSISTANT,
            confidence=heuristic_score,
            signals=[k for k, v in features.items() if v > 0],
            action="handoff",
            auto_reply=(
                "Oi! Sou o Franz, assistente virtual da FraLib. "
                "Estou entrando em contato sobre uma proposta comercial. "
                "Voce e o responsavel ou prefere que eu fale com alguem da equipe? 🙂"
            ),
        )

    # ═══ NIVEL 3: LLM (juiz final) ═══
    try:
        tipo, confianca, motivo = _llm_classify_cached(text_clean)
    except Exception as exc:
        return ProcessResult(
            msg_type=MessageType.UNKNOWN,
            confidence=0.0,
            signals=[f"llm_classifier_error:{type(exc).__name__}"],
            action="ask_human",
        )

    # Se LLM nao tem certeza, bloqueia automacao em vez de inferir por fallback.
    if confianca < 0.6:
        return ProcessResult(
            msg_type=MessageType.UNKNOWN,
            confidence=confianca,
            signals=[f"llm_low_conf({confianca})", f"heuristic({heuristic_score:.2f})"],
            action="ask_human",
        )

    if tipo == "BOT_ASSISTANT":
        return ProcessResult(
            msg_type=MessageType.BOT_ASSISTANT,
            confidence=confianca,
            signals=[f"llm:{motivo}"],
            action="handoff",
            auto_reply=(
                "Oi! Sou o Franz, assistente virtual da FraLib. "
                "Estou entrando em contato sobre uma proposta comercial. "
                "Voce e o responsavel ou prefere que eu fale com alguem da equipe? 🙂"
            ),
        )
    elif tipo == "AUTO_AUSENTE":
        return ProcessResult(
            msg_type=MessageType.AUTO_AUSENTE,
            confidence=confianca,
            signals=[f"llm:{motivo}"],
            action="no_response",
        )

    if tipo == "LEAD_REAL":
        return ProcessResult(
            msg_type=MessageType.LEAD_REAL,
            confidence=confianca,
            signals=[f"llm:{motivo}"],
            action="forward_to_franz",
        )

    return ProcessResult(
        msg_type=MessageType.UNKNOWN,
        confidence=confianca,
        signals=[f"llm_unsupported:{tipo}"],
        action="ask_human",
    )


def should_franz_respond(text: str, msg_data: Optional[dict] = None) -> tuple[bool, Optional[str]]:
    """Helper: Franz deve responder?"""
    result = classify_incoming_message(text, msg_data)
    if result.action == "forward_to_franz":
        return True, None
    if result.action == "no_response":
        return False, None
    return False, result.auto_reply
