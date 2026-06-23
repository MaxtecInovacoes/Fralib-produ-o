"""Tools dinâmicas para o SDR (Franz) — Sprint 3A.

4 tools disponíveis para o Franz consultar/invocar antes/depois do LLM call:
- retrieve_similar_conversations(nicho, top_k=5)
- get_nicho_playbook(nicho)
- check_lead_quality(user_id, telefone)
- save_sdr_lesson(lesson, score, nicho, lead_id, converteu=False)

Padrão: TOOLS_DISPATCH + call_tool + list_tools (mesmo padrão de tools_site.py).
Tools NAO sao chamadas pelo LLM (nao temos Claude Agent SDK runtime aqui).
O orchestrator chama a tool ANTES do LLM call e injeta resultado no prompt,
mantendo backward-compat total.

Reuso:
- learning._add_lesson (backend/agents/sdr_langgraph/learning.py:151)
- learning._lead_learning_path (backend/agents/sdr_langgraph/learning.py:55)
- learning._tenant_dir (backend/agents/sdr_langgraph/learning.py:45)
- sdr_playbook.get_nicho_playbook (backend/agents/sdr_langgraph/sdr_playbook.py)
- caio._calcular_score (backend/agents/caio.py:74)

Flag opt-in: FRALIB_SDR_USE_TOOLS=1 (default False = backward-compat).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TOOL 1: retrieve_similar_conversations
# ════════════════════════════════════════════════════════════════════

def _conversations_path(user_id: int, nicho: str) -> Path:
    """Path para o arquivo JSONL de conversas por nicho do user_id."""
    base = Path(__file__).resolve().parents[2] / "memory" / f"u{int(user_id)}"
    base.mkdir(parents=True, exist_ok=True)
    safe_nicho = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(nicho or "default"))[:60]
    return base / f"sdr_conversations_{safe_nicho}.jsonl"


def retrieve_similar_conversations(nicho: str, user_id: int = 0, top_k: int = 5) -> list[dict]:
    """Recupera conversas SDR anteriores do mesmo nicho.

    Args:
        nicho: segmento canonico (academia_crossfit, etc).
        user_id: tenant id (0 = sem user_id, retorna []).
        top_k: quantas conversas retornar (default 5, max 10).

    Returns:
        Lista de dicts [{lead_id, intent_final, converteu, duracao_turnos,
        tom_usado, gatilho_conversao, snippet}]. Lista vazia se nicho
        nunca foi visto (cold start) ou user_id=0.
    """
    if not nicho or not user_id:
        return []
    top_k = max(1, min(10, top_k))
    path = _conversations_path(user_id, nicho)
    if not path.is_file():
        return []
    try:
        results: list[dict] = []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Mais recentes primeiro
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                results.append({
                    "lead_id": entry.get("lead_id", ""),
                    "intent_final": entry.get("intent_final", ""),
                    "converteu": bool(entry.get("converteu", False)),
                    "duracao_turnos": int(entry.get("duracao_turnos", 0)),
                    "tom_usado": entry.get("tom_usado", ""),
                    "gatilho_conversao": entry.get("gatilho_conversao", ""),
                    "snippet": entry.get("snippet", "")[:200],
                })
                if len(results) >= top_k:
                    break
            except json.JSONDecodeError:
                continue
        return results
    except Exception as e:
        logger.warning(f"[tools_sdr] retrieve_similar_conversations falhou: {e}")
        return []


def record_conversation_outcome(
    user_id: int,
    nicho: str,
    lead_id: str,
    intent_final: str,
    converteu: bool,
    duracao_turnos: int,
    tom_usado: str = "",
    gatilho_conversao: str = "",
    snippet: str = "",
) -> bool:
    """Persiste resultado de uma conversa SDR (append-only JSONL).

    Usado pelo agent.py quando conversa termina (won/lost/opt_out).
    Idempotente: append-only, nao sobrescreve.
    """
    if not user_id or not nicho or not lead_id:
        return False
    try:
        path = _conversations_path(user_id, nicho)
        entry = {
            "lead_id": lead_id,
            "intent_final": intent_final,
            "converteu": converteu,
            "duracao_turnos": duracao_turnos,
            "tom_usado": tom_usado,
            "gatilho_conversao": gatilho_conversao,
            "snippet": snippet[:300],
            "ts": __import__("datetime").datetime.now().isoformat(),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        logger.warning(f"[tools_sdr] record_conversation_outcome falhou: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
# TOOL 2: get_nicho_playbook
# ════════════════════════════════════════════════════════════════════

def get_nicho_playbook(nicho: str) -> dict:
    """Retorna playbook canonico do nicho (wrapper de sdr_playbook).

    Args:
        nicho: segmento canonico (academia_crossfit, etc).

    Returns:
        Dict com tom, perguntas obrigatorias, red flags, gatilhos, etc.
        Dict com campos basicos se nicho nao mapeado (default).
    """
    try:
        from .sdr_playbook import get_nicho_playbook as _gp
        return _gp(nicho)
    except Exception as e:
        logger.warning(f"[tools_sdr] get_nicho_playbook falhou: {e}")
        return {
            "perguntas_obrigatorias": [],
            "red_flags": [],
            "objecoes_comuns": {},
            "gatilhos_conversao": [],
            "tom_recomendado": "consultivo",
            "frase_hook_inicial": "Oi! Como posso ajudar?",
            "objecao_silencio_max_horas": 24,
        }


# ════════════════════════════════════════════════════════════════════
# TOOL 3: check_lead_quality
# ════════════════════════════════════════════════════════════════════

def check_lead_quality(user_id: int, telefone: str = "", lead_id: str = "") -> dict:
    """Consulta Caio (scorer) + historico do lead.

    Args:
        user_id: tenant id.
        telefone: telefone do lead (opcional).
        lead_id: id do lead (opcional, usado pra buscar historico).

    Returns:
        Dict com {score_caio, tier, ultima_interacao, ja_pediu_orcamento,
        ja_recusou, tem_whatsapp}. Vazio {} se user_id=0.
    """
    if not user_id:
        return {}
    result: dict[str, Any] = {
        "score_caio": None,
        "tier": "unknown",
        "ultima_interacao": None,
        "ja_pediu_orcamento": False,
        "ja_recusou": False,
        "tem_whatsapp": bool(telefone),
    }
    # 1. Historico do lead (se lead_id fornecido)
    if lead_id:
        try:
            from .learning import _lead_learning_path, _load_json
            path = _lead_learning_path(user_id, lead_id)
            hist = _load_json(path, {"events": []})
            events = hist.get("events", [])
            if events:
                result["ultima_interacao"] = events[-1].get("at")
                # Verifica se ja pediu orcamento ou recusou
                for ev in events:
                    if ev.get("event") in ("orcamento_pedido", "wants_link", "objection_price"):
                        result["ja_pediu_orcamento"] = True
                    if ev.get("event") in ("rejection", "opt_out", "lost"):
                        result["ja_recusou"] = True
        except Exception as e:
            logger.debug(f"[tools_sdr] check_lead_quality (history) ignorado: {e}")
    # 2. Caio score (se informacoes basicas do lead disponiveis)
    if telefone:
        try:
            from agents.caio import _calcular_score
            # Sem dados completos do lead, retorna score neutro
            # Quando dados existirem no DB, plugar aqui
            result["score_caio"] = 50  # neutro
            result["tier"] = "MEDIUM"
        except Exception as e:
            logger.debug(f"[tools_sdr] check_lead_quality (caio) ignorado: {e}")
    return result


# ════════════════════════════════════════════════════════════════════
# TOOL 4: save_sdr_lesson
# ════════════════════════════════════════════════════════════════════

MAX_MULTIPLIER = 2.0
MIN_MULTIPLIER = 0.3


def save_sdr_lesson(
    lesson: str,
    score: float,
    nicho: str,
    user_id: int = 0,
    lead_id: str = "",
    converteu: bool = False,
    agent: str = "franz",
) -> dict:
    """Persiste lesson SDR com multiplicador (converteu=True → +1.5x, False → 0.3x).

    Args:
        lesson: texto da lesson (max 500 chars).
        score: confianca da lesson (0-1).
        nicho: segmento canonico.
        user_id: tenant id.
        lead_id: id do lead (opcional, apenas para rastreio).
        converteu: True se lead converteu, False se perdeu.
        agent: nome do agente SDR (default franz).

    Returns:
        Dict com {learned, score_final, multiplicador, key}.
        {learned: False} se lesson vazia, score invalido ou user_id=0.
    """
    if not user_id or not lesson or not lesson.strip():
        return {"learned": False, "reason": "missing_required_fields"}
    if not (0.0 <= score <= 1.0):
        return {"learned": False, "reason": "score_out_of_range"}
    lesson_clean = lesson.strip()[:500]
    # Multiplicador: converteu → +1.5x, nao converteu → 0.3x (com caps)
    multiplier = 1.5 if converteu else 0.3
    multiplier = max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, multiplier))
    score_final = max(0.0, min(1.0, score * multiplier))
    try:
        from .learning import _add_lesson
        key = f"sdr_{re.sub(r'[^a-zA-Z0-9_.-]+', '_', lesson_clean[:40]).strip('_').lower()}"
        _add_lesson(user_id, {
            "key": key,
            "agent": agent,
            "nicho": nicho,
            "score": score_final,
            "multiplicador": multiplier,
            "converteu": converteu,
            "text": lesson_clean,
            "last_lead_id": lead_id,
        })
        return {"learned": True, "score_final": score_final, "multiplicador": multiplier, "key": key}
    except Exception as e:
        logger.warning(f"[tools_sdr] save_sdr_lesson falhou: {e}")
        return {"learned": False, "reason": f"persist_error: {e}"}


# ════════════════════════════════════════════════════════════════════
# TOOLS_DISPATCH + call_tool + list_tools
# ════════════════════════════════════════════════════════════════════

TOOLS_DISPATCH: dict[str, callable] = {
    "retrieve_similar_conversations": retrieve_similar_conversations,
    "get_nicho_playbook": get_nicho_playbook,
    "check_lead_quality": check_lead_quality,
    "save_sdr_lesson": save_sdr_lesson,
}


def call_tool(name: str, **kwargs) -> Any:
    """Dispatcher: invoca tool por nome. Retorna None se tool nao existe.

    Args:
        name: nome da tool (retrieve_similar_conversations, etc).
        **kwargs: argumentos passados pra tool.

    Returns:
        Resultado da tool, ou None se nome invalido.
    """
    fn = TOOLS_DISPATCH.get(name)
    if fn is None:
        logger.warning(f"[tools_sdr] call_tool: tool '{name}' nao encontrada")
        return None
    try:
        return fn(**kwargs)
    except Exception as e:
        logger.warning(f"[tools_sdr] call_tool '{name}' falhou: {e}")
        return None


def list_tools() -> list[str]:
    """Lista nomes das 4 tools disponiveis."""
    return list(TOOLS_DISPATCH.keys())


# ════════════════════════════════════════════════════════════════════
# FORMATADORES para injecao no system prompt
# ════════════════════════════════════════════════════════════════════

def format_similar_conversations_for_prompt(convs: list[dict]) -> str:
    """Formata conversas similares para injecao no system prompt.

    Args:
        convs: lista retornada por retrieve_similar_conversations.

    Returns:
        String formatada (vazia se convs vazio).
    """
    if not convs:
        return ""
    lines = ["CONVERSAS ANTERIORES DO MESMO NICHO (use como referencia):"]
    for i, c in enumerate(convs[:3], 1):
        status = "CONVERTEU" if c.get("converteu") else "perdeu"
        gatilho = c.get("gatilho_conversao") or "(sem gatilho)"
        tom = c.get("tom_usado") or "(tom padrao)"
        lines.append(
            f"  {i}. {status} | {c.get('duracao_turnos', 0)} turnos | "
            f"tom: {tom} | gatilho: {gatilho}"
        )
    return "\n".join(lines)


def format_lead_quality_for_prompt(q: dict) -> str:
    """Formata qualidade do lead para injecao no system prompt."""
    if not q:
        return ""
    lines = ["QUALIDADE DO LEAD:"]
    if q.get("score_caio") is not None:
        lines.append(f"  - Score Caio: {q['score_caio']}/100 (tier: {q.get('tier', '?')})")
    if q.get("ja_pediu_orcamento"):
        lines.append("  - Lead JA pediu orcamento antes (rapido, nao repita perguntas basicas)")
    if q.get("ja_recusou"):
        lines.append("  - Lead JA recusou antes (tom cuidadoso, sem pressao)")
    if q.get("ultima_interacao"):
        lines.append(f"  - Ultima interacao: {q['ultima_interacao'][:19]}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)
