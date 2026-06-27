"""Helper unificado pra carregar contexto completo do lead.

Todos os entry points do Franz (listener, cron, reengajar) devem usar
get_full_history() para garantir contexto consistente.

Importante: contexto completo = ate 100 mensagens. Se > 30, resume com
Haiku via _summarize_history (ja existe em sdr_reply_service).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("history_helper")

# Limite maximo de mensagens retornadas
MAX_HISTORY = 100
# Acima deste limite, Haiku resume as antigas
SUMMARY_THRESHOLD = 30


def get_full_history(engine, lead_id: str, user_id: int) -> list[dict]:
    """Carrega ate MAX_HISTORY mensagens do lead (contexto completo).

    Args:
        engine: SQLAlchemy engine
        lead_id: ID do lead
        user_id: tenant

    Returns:
        Lista de dicts com chaves: role, content, criado_em, direcao
        Ordenada do mais antigo pro mais recente (pro LLM).
    """
    from sqlalchemy import text
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT mensagem, direcao, criado_em
            FROM interacoes
            WHERE lead_id = :lid AND user_id = :uid
            ORDER BY criado_em DESC
            LIMIT :max
        """), {"lid": lead_id, "uid": user_id, "max": MAX_HISTORY}).fetchall()

    if not rows:
        return []

    # rows vem do mais recente pro mais antigo, inverte
    history = []
    for msg, direcao, criado_em in reversed(rows):
        role = "assistant" if direcao == "saida" else "user"
        history.append({
            "role": role,
            "content": msg or "",
            "criado_em": criado_em.isoformat() if criado_em else "",
            "direcao": direcao,
        })
    return history


def get_context_with_summary(engine, lead_id: str, user_id: int) -> list[dict]:
    """Retorna contexto com summary se > SUMMARY_THRESHOLD mensagens.

    Returns:
        Lista de dicts (com summary no topo + recentes)
    """
    history = get_full_history(engine, lead_id, user_id)

    if len(history) <= SUMMARY_THRESHOLD:
        return history

    # Resumir antigas (> SUMMARY_THRESHOLD)
    try:
        from backend.whatsapp.sdr_reply_service import _summarize_history
        older = history[:-SUMMARY_THRESHOLD]
        recent = history[-SUMMARY_THRESHOLD:]

        summary = _summarize_history(older)
        if summary:
            # Adicionar summary no topo
            return [{"role": "system", "content": f"[Resumo de {len(older)} mensagens anteriores] {summary}"}] + recent
    except Exception as e:
        logger.warning(f"summary falhou, usando mensagens recentes: {e}")

    return history[-SUMMARY_THRESHOLD:]


__all__ = ["get_full_history", "get_context_with_summary", "MAX_HISTORY", "SUMMARY_THRESHOLD"]
