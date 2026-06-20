"""Helpers de preparo da resposta SDR no listener de WhatsApp."""

import re
from datetime import datetime, timedelta

import pytz


def build_history(rows):
    history = []
    for mensagem_hist, direcao_hist in reversed(rows or []):
        history.append(
            {
                "role": "assistant" if direcao_hist == "saida" else "user",
                "content": mensagem_hist or "",
            }
        )
    return history


def sanitize_reply(reply: str, retry_extractor=None, fallback_reply="Opa, tudo bem? Me dá um minuto que já te respondo! 👍"):
    resposta = reply or ""
    if not resposta.strip():
        return resposta

    if resposta.strip().startswith("{") or '"resposta"' in resposta or '"novo_stage"' in resposta:
        resp_match = re.search(r'"resposta"\s*:\s*"((?:[^"\\]|\\.)*)"', resposta)
        if resp_match:
            resposta = resp_match.group(1).replace('\\"', '"').replace("\\n", "\n")
        else:
            resposta = re.sub(r"\{[\s\S]*?\}", "", resposta).strip()
            resposta = re.sub(r"```[\s\S]*?```", "", resposta).strip()

        if (not resposta or resposta.strip().startswith("{") or '"resposta"' in resposta) and retry_extractor is not None:
            try:
                fixed = (retry_extractor(reply) or "").strip().strip('"').strip()
                if fixed and not fixed.startswith("{") and '"resposta"' not in fixed:
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
