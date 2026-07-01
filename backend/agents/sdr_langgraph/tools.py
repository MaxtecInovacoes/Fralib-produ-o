"""
SDR Tools - Ações que o agente pode executar.
RAG, memória, validação, envio.
"""

from __future__ import annotations
import os
import time
import hashlib
from typing import Optional, List

import sys

# Setup paths
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(AGENTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, AGENTS_DIR)


# ════════════════════════════════════════════════════════════════════
# CACHE DE RAG
# ════════════════════════════════════════════════════════════════════

_RAG_CACHE_TTL = 3600  # 1 hora
_RAG_CACHE: dict[str, tuple[str, float]] = {}  # key -> (content, timestamp)


def _get_rag_cache_key(agent_key: str) -> str:
    """Gera chave de cache baseada no agent_key."""
    return hashlib.md5(agent_key.encode()).hexdigest()[:8]


# ════════════════════════════════════════════════════════════════════
# TOOL: RAG (buscar contexto de conhecimento)
# ════════════════════════════════════════════════════════════════════

def load_rag(agent_key: str = "", force_reload: bool = False) -> str:
    """Carrega RAG base + conhecimento especifico do agente ativo.

    Usa cache com TTL de 1 hora para evitar ler disco toda vez.
    """
    cache_key = _get_rag_cache_key(agent_key)
    now = time.time()

    # Retorna do cache se valido
    if not force_reload and cache_key in _RAG_CACHE:
        cached_content, cached_time = _RAG_CACHE[cache_key]
        if now - cached_time < _RAG_CACHE_TTL:
            return cached_content

    # Carrega do disco
    chunks: list[str] = []
    try:
        rag_path = os.path.join(BACKEND_DIR, "rag_knowledge", "franz.md")
        if os.path.exists(rag_path):
            with open(rag_path, "r", encoding="utf-8") as f:
                chunks.append(f.read())

        if agent_key:
            agent_rag_path = os.path.join(
                BACKEND_DIR, "rag_knowledge", "sdr_agents", f"{agent_key}.md"
            )
            if os.path.exists(agent_rag_path):
                with open(agent_rag_path, "r", encoding="utf-8") as f:
                    chunks.append(f.read())

            try:
                from .multi_agent import agent_rag_overlay
                chunks.append(agent_rag_overlay(agent_key))
            except Exception as e:
                print(f"[RAG] Overlay agente falhou: {e}")
    except Exception as e:
        print(f"[RAG] Erro: {e}")

    content = "\n\n".join(chunk for chunk in chunks if chunk)

    # Salva no cache
    _RAG_CACHE[cache_key] = (content, now)

    # Cleanup do cache se muito grande
    if len(_RAG_CACHE) > 50:
        expired = [k for k, (_, t) in _RAG_CACHE.items() if now - t >= _RAG_CACHE_TTL]
        for k in expired:
            del _RAG_CACHE[k]

    return content


# ════════════════════════════════════════════════════════════════════
# TOOL: Detectar Intent (LLM)
# ════════════════════════════════════════════════════════════════════

INTENT_DETECTION_PROMPT = """Classify the lead intent into exactly ONE category.

- opt_out: "não quero", "para", "me tira", "chega", "remover"
- gatekeeper: "sou recepcionista", "não sou o dono", "ele não está", "dono saiu"
- schedule: "amanhã", "semana que vem", "depois", "agendar", "marcar"
- is_decisor: "sou o dono", "eu mesmo", "pode falar comigo", "eu que cuido"
- acceptance: "sim", "quero", "bora", "fechado", "aceito", "manda"
- objection_price: "quanto", "preço", "valor", "custa", "caro", "desconto", "pix", "parcelado"
- objection_trust: "quem é", "golpe", "fake", "como pegou", "não confio"
- wants_link: "mostra", "manda o link", "quero ver", "site"
- rejection: "não", "sem interesse", "não preciso", "já tenho"
- greeting: "oi", "olá", "bom dia", "boa tarde"
- other: anything else

LEAD MESSAGE: "{message}"

Return only the category name, no explanation."""


def detect_intent_with_llm(message: str, agent_name: str = "franz") -> str:
    """Detecta intent usando regex para casos obvios e LLM para ambiguos."""
    if not message or not message.strip():
        return "other"
    regex_intent = detect_intent_regex(message)
    if regex_intent != "other":
        return regex_intent

    try:
        from agents.llm_direct import call_claude

        response = call_claude(
            system=INTENT_DETECTION_PROMPT,
            user=message,
            model="sonnet",  # SONNET (consistente com resto do Franz)
            max_tokens=20,
            temperature=0.0,
            agent_name=agent_name,
            enable_context=False,
        )
        intent = response.strip().lower().split()[0].rstrip(".,;:")
        valid_intents = {
            "opt_out", "gatekeeper", "schedule", "is_decisor", "acceptance",
            "objection_price", "objection_trust", "wants_link", "rejection",
            "greeting", "other"
        }
        if intent in valid_intents:
            return intent
        raise ValueError(f"LLM returned invalid intent: {intent!r}")
    except Exception as e:
        raise RuntimeError(f"intent detection failed: {type(e).__name__}: {e}") from e


def detect_intent_regex(message: str) -> str:
    """Deteccao deterministica para intents obvios."""
    l = message.lower().strip()
    compact = l.strip(" .,!?\n\t")
    if compact in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"}:
        return "greeting"
    if compact in {"ok", "okay", "blz", "beleza", "certo", "ta", "tá"}:
        return "acceptance"
    if any(t in l for t in ["para", "stop", "remover", "não quero", "chega"]):
        return "opt_out"
    if any(t in l for t in ["sou recepcionista", "não sou o dono", "dono não está"]):
        return "gatekeeper"
    if any(t in l for t in ["amanhã", "semana que vem", "depois", "agendar"]):
        return "schedule"
    if any(t in l for t in ["sou o dono", "eu mesmo", "pode falar comigo"]):
        return "is_decisor"
    if any(t in l for t in ["muito caro", "desconto", "valor", "preço", "preco", "quanto custa", "pix", "parcelado", "pagamento"]):
        return "objection_price"
    if any(t in l for t in ["quem é", "golpe", "fake"]):
        return "objection_trust"
    if any(t in l for t in ["mostra", "manda o link", "quero ver"]):
        return "wants_link"
    if any(t in l for t in ["sim", "quero", "bora", "fechado", "aceito"]):
        return "acceptance"
    if any(t in l for t in ["bom dia", "boa tarde", "boa noite"]):
        return "greeting"
    if any(t in l for t in ["não", "sem interesse", "já tenho"]):
        return "rejection"
    return "other"


# ════════════════════════════════════════════════════════════════════
# TOOL: Validação de Segmento (substitui o G12)
# ════════════════════════════════════════════════════════════════════

# Palavras contaminadas por segmento
SEGMENT_CONTAMINATION = {
    "academia": ["delivery", "cardápio", "ifood", "pizzaria", "restaurante", "entrega", "marmita"],
    "restaurante": ["musculação", "personal trainer", "treino funcional", "matrícula", "alunos novos"],
}


def check_segment_contamination(reply: str, segmento: str) -> List[str]:
    """Retorna lista de palavras contaminadas (vazio = ok)"""
    seg = (segmento or "").lower()
    reply_lower = (reply or "").lower()
    contaminado = []

    academia_terms = [
        "musculação",
        "musculacao",
        "treino funcional",
        "funcional",
        "personal trainer",
        "alunos novos",
        "matrícula",
        "matricula",
    ]
    if seg and not any(a in seg for a in ("academia", "fitness", "crossfit", "pilates", "gym")):
        for p in academia_terms:
            if p in reply_lower:
                contaminado.append(p)

    for seg_key, palavras in SEGMENT_CONTAMINATION.items():
        if any(m in seg for m in seg_key.split()):
            for p in palavras:
                if p in reply_lower:
                    contaminado.append(p)
    return contaminado


# ════════════════════════════════════════════════════════════════════
# TOOL: Validação de Comprimento
# ════════════════════════════════════════════════════════════════════

def is_valid_length(reply: str) -> bool:
    """Valida se mensagem tem comprimento adequado (1-4 linhas, <300 chars)"""
    if not reply:
        return False
    linhas = reply.count("\n") + 1
    if linhas > 4:
        return False
    if len(reply) > 300:
        return False
    return True


def has_one_question(reply: str) -> bool:
    """Valida se tem exatamente 0 ou 1 pergunta"""
    if not reply:
        return False
    return reply.count("?") <= 1


# ════════════════════════════════════════════════════════════════════
# TOOL: Horário de Atendimento
# ════════════════════════════════════════════════════════════════════

def is_within_schedule(user_id: Optional[int] = None) -> bool:
    """Verifica se está dentro do horário (default: seg-sáb 8h-21h)"""
    try:
        from datetime import datetime, timezone, timedelta
        agora = datetime.now(timezone(timedelta(hours=-3)))

        if user_id:
            try:
                from .compat import _get_horario_config
                config = _get_horario_config(user_id)
                if config:
                    if config.get("modo") == "livre":
                        return True
                    hora_inicio = config.get("hora_inicio", 8)
                    hora_fim = config.get("hora_fim", 21)
                    dias_bloqueados = config.get("dias_bloqueados", [6])
                else:
                    hora_inicio, hora_fim, dias_bloqueados = 8, 21, [6]
            except Exception:
                hora_inicio, hora_fim, dias_bloqueados = 8, 21, [6]
        else:
            hora_inicio, hora_fim, dias_bloqueados = 8, 21, [6]

        if agora.weekday() in dias_bloqueados:
            return False
        return hora_inicio <= agora.hour < hora_fim
    except Exception:
        return True  # Em caso de erro, permitir


# ════════════════════════════════════════════════════════════════════
# TOOL: Saudação por Horário
# ════════════════════════════════════════════════════════════════════

def get_greeting() -> str:
    """Saudacao baseada no horario de Brasilia - NAO usa fallback."""
    from datetime import datetime, timezone, timedelta
    hora = datetime.now(timezone(timedelta(hours=-3))).hour
    if hora < 12:
        return "Bom dia"
    if hora < 18:
        return "Boa tarde"
    return "Boa noite"


# ════════════════════════════════════════════════════════════════════
# TOOL: Saudação + Variante
# ════════════════════════════════════════════════════════════════════

def get_agent_name(user_id: Optional[int] = None) -> str:
    """Nome público do agente"""
    try:
        if user_id:
            from services.sdr_settings import agent_name
            from .compat import _get_sdr_settings_for_user
            return agent_name(_get_sdr_settings_for_user(user_id)) or "Franz"
    except Exception:
        pass
    return "Franz"


def choose_variant(lead_id: str, segmento: str = "", user_id: Optional[int] = None) -> str:
    """Escolhe variante A/B/C/D"""
    if not segmento:
        return "A"
    # Hash determinístico do lead_id
    h = sum(ord(c) for c in str(lead_id))
    variantes = ["A", "B", "C", "D"]
    return variantes[h % 4]
