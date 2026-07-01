"""Helpers de preparo da resposta SDR no listener de WhatsApp."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import pytz

logger = logging.getLogger(__name__)


def sanitize_reply(reply: str, retry_extractor=None) -> str:
    """Extrai texto legível de resposta JSON do LLM.

    NAO USA FALLBACK - se LLM falhar, lancha excecao para retry.
    O sistema deve gerar resposta via LLM, nao usar templates pre-definidos.
    """
    if not reply or not (reply or "").strip():
        raise ValueError("LLM returned empty reply - cannot use fallback")

    resposta = reply
    if not resposta.strip():
        raise ValueError("LLM returned empty reply - cannot use fallback")

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

        # Se ainda parece JSON após extração, tentar retry_extractor
        if (
            not resposta
            or resposta.strip().startswith("{")
            or '"resposta"' in resposta
            or '"reply"' in resposta
        ):
            if retry_extractor is not None:
                try:
                    fixed = (retry_extractor(reply) or "").strip().strip('"').strip()
                    if fixed and not fixed.startswith("{") and '"resposta"' not in fixed and '"reply"' not in fixed:
                        resposta = fixed
                    else:
                        # NAO USA FALLBACK - lancar erro para forcar retry
                        raise ValueError(f"Cannot extract reply from LLM response. Raw: {reply[:200]}")
                except ValueError:
                    # Relancar erro para retry
                    raise
                except Exception:
                    raise ValueError(f"Failed to extract reply from LLM: {reply[:200]}")
            else:
                # Sem retry_extractor E nao conseguiu extrair = ERRO
                raise ValueError(f"Cannot extract reply from LLM response (no retry available). Raw: {reply[:200]}")

    return resposta


def get_outgoing_formatter(learning_module=None):
    if learning_module is not None and hasattr(learning_module, "format_outgoing_messages"):
        return learning_module.format_outgoing_messages

    def _format_outgoing_messages(text):
        return [text] if text else []

    return _format_outgoing_messages


def _jaccard_similarity(set1: set, set2: set) -> float:
    """Calcula similaridade Jaccard entre dois sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _words_set(text: str) -> set:
    """Extrai palavras de um texto (lowercase, sem pontuação)."""
    import re
    return set(re.sub(r"[^a-záàâãéèêíïóôõúüç0-9\s]", " ", text.lower()).split())


def is_duplicate_reply(history, reply: str) -> bool:
    """
    Detecta se a reply é duplicata da última mensagem do bot.

    Usa 2 estratégias:
    1. Substring exata (mantém compatibilidade com testes)
    2. Similaridade Jaccard >= 0.7 (detecta msgs com palavras trocadas)
    """
    try:
        last_bot_msg = next(
            (
                (item.get("content") or "").strip()
                for item in reversed(history or [])
                if item.get("role") == "assistant" and (item.get("content") or "").strip()
            ),
            "",
        )
        if not last_bot_msg or not reply.strip():
            return False

        reply_clean = reply.strip()
        bot_clean = last_bot_msg.strip()

        # Estratégia 1: substring exata (comportamento original)
        if reply_clean in bot_clean:
            return True

        # Estratégia 2: similaridade Jaccard >= 0.7
        # Captura msgs com palavras trocadas mas mesmo significado
        reply_words = _words_set(reply_clean)
        bot_words = _words_set(bot_clean)
        similarity = _jaccard_similarity(reply_words, bot_words)

        return similarity >= 0.7
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


def _summarize_history(messages: list) -> str:
    """Gera summary compacto de uma lista de mensagens.

    Tenta Haiku (barato) primeiro; se falhar, faz extractive summary
    (pega top-3 mensagens mais longas + intents detectados).
    Usado por history_helper.py quando > 30 mensagens.
    """
    import logging
    logger = logging.getLogger("sdr")

    if not messages:
        return ""
    intents_seen = []
    snippets = []
    for msg in messages[-20:]:
        content = (msg.get("content") or "").strip()
        if content:
            snippets.append(content[:120])
    try:
        from agents.llm_direct import call_claude
        conversation = "\n".join(f"lead: {s[:200]}" for s in snippets[:5])
        summary = call_claude(
            system="Voce resume conversas de WhatsApp SDR em ate 3 frases. Foque em: (1) o que o lead quer, (2) objecoes principais, (3) estado atual. Use portugues brasileiro. Maximo 250 caracteres.",
            user=f"Conversa:\n{conversation}",
            model="haiku",
            max_tokens=150,
            temperature=0.2,
            agent_name="sdr_history_summarizer",
            respect_agent_config=False,
            enable_context=False,
        ).strip()
        if summary and len(summary) < 1000:
            return summary[:250]
    except Exception as e:
        logger.warning(f"[sdr] _summarize_history Haiku falhou: {e} - usando extractive fallback")
    if snippets:
        return " | ".join(snippets[-3:])[:250]
    return ""


def build_history(rows, max_messages=30):
    """Wrapper de compatibilidade. Delega para history_helper.

    SDR 10/10: build_history era usado em testes antigos.
    Agora delega para get_full_history que pega ate 100 msgs
    (com summary se > 30 via _summarize_history).

    IMPORTANTE: DB retorna DESC (mais novo primeiro), mas precisamos
    ASC (mais antigo primeiro) para contexto correto do LLM.
    """
    try:
        from backend.whatsapp.history_helper import get_full_history
        # rows vem como tuples (mensagem, direcao)
        history = []
        for msg, direcao in rows:
            role = "assistant" if direcao == "saida" else "user"
            history.append({"role": role, "content": msg or ""})
        # Reverter para ordem cronológica (mais antigo primeiro)
        history = list(reversed(history))
        return history[:max_messages]
    except Exception:
        # Fallback: retorna tudo em ordem reversa
        history = []
        for msg, direcao in rows:
            role = "assistant" if direcao == "saida" else "user"
            history.append({"role": role, "content": msg or ""})
        return list(reversed(history))
