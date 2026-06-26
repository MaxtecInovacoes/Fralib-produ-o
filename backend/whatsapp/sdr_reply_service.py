"""Helpers de preparo da resposta SDR no listener de WhatsApp."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import pytz

logger = logging.getLogger(__name__)

# Sliding window config
HISTORY_WINDOW = 30  # ultimas N mensagens vao cruas no prompt
SUMMARY_THRESHOLD = 30  # se history > N, gera summary das mais antigas
SUMMARY_MAX_TOKENS = 250  # limite do summary (chars estimados)


def build_history(rows, max_messages: int = HISTORY_WINDOW):
    """Constroi historico OpenAI-style com sliding window.

    Se o numero total de mensagens > max_messages:
    - Gera summary das mensagens mais antigas (Haiku, mais barato)
    - Mantem as ultimas max_messages cruas no array
    - Injeta summary como primeira mensagem do tipo "system"

    Args:
        rows: lista de tuplas (mensagem, direcao) vinda do banco.
        max_messages: limite de mensagens raw no prompt.

    Returns:
        Lista de dicts {"role": ..., "content": ...} pronta pra OpenAI API.
    """
    history = []
    rows = rows or []
    for mensagem_hist, direcao_hist in reversed(rows):
        history.append(
            {
                "role": "assistant" if direcao_hist == "saida" else "user",
                "content": mensagem_hist or "",
            }
        )

    if len(history) <= max_messages:
        return history

    # Sliding window: gera summary das mensagens antigas
    older = history[:-max_messages]
    recent = history[-max_messages:]
    summary = _summarize_history(older)
    if summary:
        # summary como system message no topo
        return [
            {"role": "system", "content": f"[Resumo das mensagens anteriores] {summary}"}
        ] + recent
    return recent


def _summarize_history(messages: list[dict]) -> str:
    """Gera summary compacto de uma lista de mensagens.

    Tenta Haiku (barato) primeiro; se falhar, faz extractive summary
    (pega top-3 mensagens mais longas + intents detectados).
    """
    if not messages:
        return ""

    # 1. Fallback rapido: extractive summary sem LLM (nao bloqueia)
    intents_seen = []
    snippets = []
    for msg in messages[-20:]:  # limite defensivo
        content = (msg.get("content") or "").strip()
        if content:
            snippets.append(content[:120])

    # 2. Tentar LLM (Haiku) pra melhor qualidade
    try:
        from agents.llm_direct import call_claude
        conversation = "\n".join(
            f"{msg.get('role', 'user')}: {(msg.get('content') or '')[:200]}"
            for msg in messages[-50:]  # limite de 50 msgs pra nao estourar input
        )
        summary = call_claude(
            system=(
                "Voce resume conversas de WhatsApp SDR em ate 3 frases. "
                "Foque em: (1) o que o lead quer, (2) objecoes principais, "
                "(3) estado atual da conversa. Use portugues brasileiro. "
                "Maximo 250 caracteres."
            ),
            user=f"Conversa:\n{conversation}",
            model="sonnet",  # SONNET (consistente com resto do Franz)
            max_tokens=300,
            temperature=0.2,
            agent_name="sdr_history_summarizer",
            respect_agent_config=False,
            enable_context=False,
        ).strip()
        if summary and len(summary) < 800:
            return summary[:SUMMARY_MAX_TOKENS * 4]  # 250 tokens ~ 1000 chars
    except Exception as e:
        logger.warning(f"[build_history] Haiku summary falhou, usando extractive: {e}")

    # 3. Fallback extractive
    if snippets:
        return " | ".join(snippets[-3:])[:SUMMARY_MAX_TOKENS * 4]
    return ""


def sanitize_reply(reply: str, retry_extractor=None, fallback_reply="Opa, tudo bem? Me dá um minuto que já te respondo! 👍"):
    resposta = reply or ""
    if not resposta.strip():
        return resposta

    # Detecta QUALQUER formato de JSON retornado pelo LLM:
    # - JSON cru {...
    # - Markdown code block ```json ... ```
    # - Campo "resposta" (PT) ou "reply" (EN) solto
    # - Campo "novo_stage" (PT) ou "next_stage" (EN)
    looks_like_json = (
        resposta.strip().startswith("{")
        or '"resposta"' in resposta
        or '"novo_stage"' in resposta
        or '"reply"' in resposta
        or '"next_stage"' in resposta
        or resposta.strip().startswith("```json")
        or resposta.strip().startswith("```")
        or resposta.lstrip().startswith("```json")
    )

    if looks_like_json:
        # Tentar extrair campo "resposta" (PT) ou "reply" (EN)
        # Regex tolera string SEM fechamento (caso de LLM truncado por max_tokens)
        resp_match = re.search(r'"(?:resposta|reply)"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', resposta)
        if resp_match:
            resposta = resp_match.group(1).replace('\\"', '"').replace("\\n", "\n")
        else:
            # Remover blocos JSON e markdown code blocks (```json ... ```)
            # Primeiro remove code blocks markdown
            resposta = re.sub(r"```(?:json)?\s*[\s\S]*?\s*```", "", resposta).strip()
            # Depois remove JSON cru (mesmo malformado/incompleto)
            resposta = re.sub(r"\{[\s\S]*", "", resposta).strip()
            # Remove backticks soltos que sobraram
            resposta = re.sub(r"```\w*", "", resposta).strip()

        # Fallback se ainda parece JSON
        if (
            not resposta
            or resposta.strip().startswith("{")
            or '"resposta"' in resposta
            or '"reply"' in resposta
        ) and retry_extractor is not None:
            try:
                fixed = (retry_extractor(reply) or "").strip().strip('"').strip()
                if fixed and not fixed.startswith("{") and '"resposta"' not in fixed and '"reply"' not in fixed:
                    resposta = fixed
                else:
                    resposta = fallback_reply
            except Exception:
                resposta = fallback_reply

    return resposta


def get_outgoing_formatter(learning_module=None):
    if learning_module is not None and hasattr(learning_module, "format_outgoing_messages"):
        return learning_module.format_outgoing_messages

    def _format_outgoing_messages(text):
        return [text] if text else []

    return _format_outgoing_messages


def is_duplicate_reply(history, reply: str) -> bool:
    try:
        last_bot_msg = next(
            (
                (item.get("content") or "").strip()
                for item in reversed(history or [])
                if item.get("role") == "assistant" and (item.get("content") or "").strip()
            ),
            "",
        )
        return bool(last_bot_msg and reply.strip() and reply.strip() in last_bot_msg)
    except Exception:
        return False


def map_next_stage(next_stage: str, current_stage: str, mapping: dict):
    raw_stage = next_stage or current_stage or "hook"
    return raw_stage, mapping.get(raw_stage, raw_stage)


def normalize_followup_date(raw_followup_date: str, timezone_name="America/Sao_Paulo"):
    """Normaliza follow-up para uma data futura valida no timezone informado."""
    hoje = datetime.now(pytz.timezone(timezone_name)).date()
    try:
        data_parsed = datetime.strptime(raw_followup_date, "%Y-%m-%d").date()
        if data_parsed <= hoje:
            return (hoje + timedelta(days=1)).strftime("%Y-%m-%d"), "past"
        return raw_followup_date, "ok"
    except (ValueError, TypeError):
        return (hoje + timedelta(days=1)).strftime("%Y-%m-%d"), "invalid"
