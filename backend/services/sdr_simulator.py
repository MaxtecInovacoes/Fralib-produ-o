"""Simulador do Franz (Sprint 1.1).

Permite ao admin rodar uma mensagem contra o cérebro do Franz sem disparar
no WhatsApp real. Útil para:
  - Validar mudanças de system prompt antes de subir
  - Debugar por que uma mensagem gerou uma resposta X
  - Auditar qual action do Kanban o Franz decidiria para uma intenção Y

Pipeline:
  1. Carrega sdr_settings do tenant via get_sdr_settings_runtime(user_id=tenant_id)
  2. Monta system prompt via build_sdr_system_prompt (reutiliza o já existente)
  3. Chama call_llm com claude-haiku-4-5
  4. Parseia intent/stage/action de dentro de um bloco ```json ... ``` na resposta
  5. Persiste em sdr_simulations + retorna dict

NOTA: este simulador USA o build_sdr_system_prompt existente (que tem o bug
do custom_knowledge). Sprint 1.2 vai consertar e o simulador se beneficia
automaticamente.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.core.database import engine as _default_engine
from services.llm_router import call_llm
from services.sdr_settings import (
    build_sdr_system_prompt,
    get_sdr_settings_runtime,
)

logger = logging.getLogger(__name__)


# System prompt base (mesmo texto curto que o runtime do Franz usa).
# Não contém regras tenant-specific — essas são injetadas por build_sdr_system_prompt.
_BASE_SYSTEM_PROMPT = """Voce e o Franz, SDR virtual da FraLib.
Seu papel: qualificar leads via WhatsApp, conduzir para o fechamento
ou transferir para humano quando o lead esta quente.

REGRAS ABSOLUTAS:
- NUNCA envie spam, promessa falsa, invasao de privacidade.
- NUNCA quebre opt-out ou de desconto abaixo do piso.
- Respostas curtas (max ~600 chars), tom humano.
- Quando o lead pedir humano / aceitar comprar / pedir pagamento,
  finalize com handoff.
"""

# Modelo canonico usado pelo simulador: haiku e' rapido e barato.
SIMULATOR_MODEL = "claude-haiku-4-5"

# Regex para extrair bloco ```json ... ``` dentro da resposta do LLM.
_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _parse_llm_response(raw: str) -> tuple[dict[str, Any], str]:
    """Extrai {intent, stage_after, kanban_action} do texto.

    Returns:
        (metadata_dict, plain_text_response). plain_text é o texto com o bloco
        JSON removido (para exibir so' a resposta em linguagem natural).
    """
    metadata: dict[str, Any] = {
        "intent": None,
        "stage_after": None,
        "kanban_action": None,
        "rules_applied": [],
    }
    if not raw:
        return metadata, ""

    match = _JSON_BLOCK_RE.search(raw)
    plain = raw
    if match:
        plain = (raw[: match.start()] + raw[match.end():]).strip()
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                metadata["intent"] = parsed.get("intent") or parsed.get("intent_label")
                metadata["stage_after"] = parsed.get("stage_after") or parsed.get("stage")
                metadata["kanban_action"] = (
                    parsed.get("kanban_action") or parsed.get("action")
                )
                rules = parsed.get("rules_applied") or parsed.get("rules") or []
                if isinstance(rules, list):
                    metadata["rules_applied"] = [str(r) for r in rules][:20]
        except Exception as exc:  # pragma: no cover - defensivo
            logger.warning("[sdr_simulator] JSON parse falhou: %s", exc)

    # Fallback heurístico: se nao veio JSON embutido, tenta inferir intent
    # a partir de palavras-chave simples.
    if not metadata["intent"]:
        lower = plain.lower()
        if any(k in lower for k in ("quero contratar", "fechar", "manda link", "pode mandar")):
            metadata["intent"] = "compra"
            metadata["stage_after"] = "fechamento"
            metadata["kanban_action"] = "move_to_fechamento"
        elif any(k in lower for k in ("falar com humano", "atendente", "pessoa")):
            metadata["intent"] = "pede_humano"
            metadata["kanban_action"] = "handoff"
        elif any(k in lower for k in ("nao quero", "para", "sair", "descad")):
            metadata["intent"] = "opt_out"
            metadata["kanban_action"] = "stop_sequence"

    return metadata, plain


def _build_user_message(message: str, history: list[dict[str, Any]] | None) -> str:
    """Monta prompt de usuario com historico inline.

    history: lista de {role, content}. Trunca a 10 ultimas msgs para economizar tokens.
    """
    history = history or []
    history = history[-10:]
    parts: list[str] = []
    if history:
        parts.append("Historico recente da conversa:")
        for turn in history:
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            tag = "Lead" if role in ("user", "lead", "human") else "Franz"
            parts.append(f"[{tag}] {content[:600]}")
        parts.append("")
    parts.append(f"Mensagem atual do lead: {message}")
    parts.append("")
    parts.append(
        "Responda em portugues, tom humano, max ~600 chars.\n"
        "Ao final, inclua um bloco ```json { \"intent\": ..., "
        "\"stage_after\": ..., \"kanban_action\": ..., "
        "\"rules_applied\": [...] } ```."
    )
    return "\n".join(parts)


def simulate(
    tenant_id: int,
    message: str,
    history: list[dict[str, Any]] | None = None,
    *,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Roda uma simulacao do Franz contra o tenant_id.

    Args:
        tenant_id: ID do tenant (tambem usado como user_id para sdr_settings).
        message: mensagem do lead.
        history: turnos anteriores (opcional).
        engine: SQLAlchemy engine (default: backend.core.database.engine).

    Returns:
        dict com:
          - response: texto natural da resposta
          - intent / stage_after / kanban_action / rules_applied
          - latency_ms
          - id (id da linha persistida em sdr_simulations, ou None se persistencia falhou)
    """
    eng = engine or _default_engine
    message = (message or "").strip()
    if not message:
        return {
            "response": "",
            "intent": None,
            "stage_after": None,
            "kanban_action": None,
            "rules_applied": [],
            "latency_ms": 0,
            "id": None,
            "error": "mensagem vazia",
        }

    # 1) Carrega sdr_settings
    settings: dict[str, Any] = {}
    try:
        settings = get_sdr_settings_runtime(int(tenant_id), eng) or {}
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning(
            "[sdr_simulator] get_sdr_settings_runtime falhou p/ tenant=%s: %s",
            tenant_id,
            exc,
        )
        settings = {}

    # 2) Monta system prompt usando o que JÁ EXISTE em sdr_settings
    system_prompt = build_sdr_system_prompt(_BASE_SYSTEM_PROMPT, settings)

    # 3) call_llm com haiku (rapido + barato para simulacao)
    user_prompt = _build_user_message(message, history)
    start = time.time()
    try:
        raw_response, _usage = call_llm(
            provider="anthropic",
            model_id=SIMULATOR_MODEL,
            system=system_prompt,
            user=user_prompt,
            temperature=0.4,
            max_tokens=600,
        )
    except Exception as exc:
        latency_ms = int((time.time() - start) * 1000)
        logger.warning("[sdr_simulator] call_llm falhou: %s", exc)
        return {
            "response": "",
            "intent": None,
            "stage_after": None,
            "kanban_action": None,
            "rules_applied": [],
            "latency_ms": latency_ms,
            "id": None,
            "error": str(exc),
        }
    latency_ms = int((time.time() - start) * 1000)

    # 4) Parseia metadata
    metadata, plain_text = _parse_llm_response(raw_response or "")

    result: dict[str, Any] = {
        "response": plain_text or (raw_response or ""),
        "intent": metadata["intent"],
        "stage_after": metadata["stage_after"],
        "kanban_action": metadata["kanban_action"],
        "rules_applied": metadata["rules_applied"],
        "latency_ms": latency_ms,
        "id": None,
    }

    # 5) Persiste em sdr_simulations (insert-only, fail-safe)
    try:
        with eng.begin() as conn:
            row = conn.execute(
                text(
                    """
                    INSERT INTO sdr_simulations (
                        tenant_id, message, response,
                        intent, stage_after, kanban_action,
                        rules_applied, latency_ms
                    ) VALUES (
                        :tenant_id, :message, :response,
                        :intent, :stage_after, :kanban_action,
                        CAST(:rules_applied AS JSONB), :latency_ms
                    )
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": int(tenant_id),
                    "message": message[:8000],
                    "response": (result["response"] or "")[:8000],
                    "intent": result["intent"],
                    "stage_after": result["stage_after"],
                    "kanban_action": result["kanban_action"],
                    "rules_applied": json.dumps(result["rules_applied"] or []),
                    "latency_ms": latency_ms,
                },
            ).first()
            if row is not None:
                result["id"] = int(row[0])
    except Exception as exc:  # pragma: no cover - persistencia e' fail-safe
        logger.warning("[sdr_simulator] INSERT falhou: %s", exc)

    return result


def list_simulations(
    tenant_id: int,
    limit: int = 10,
    *,
    engine: Engine | None = None,
) -> list[dict[str, Any]]:
    """Retorna as ultimas N simulacoes do tenant (default 10)."""
    eng = engine or _default_engine
    limit = max(1, min(int(limit), 100))
    try:
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, tenant_id, message, response,
                           intent, stage_after, kanban_action,
                           rules_applied, latency_ms, criado_em
                    FROM sdr_simulations
                    WHERE tenant_id = :tenant_id
                    ORDER BY criado_em DESC
                    LIMIT :limit
                    """
                ),
                {"tenant_id": int(tenant_id), "limit": limit},
            ).fetchall()
    except Exception as exc:
        logger.warning("[sdr_simulator] list_simulations falhou: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        rules = r[7]
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except Exception:
                rules = []
        out.append(
            {
                "id": int(r[0]),
                "tenant_id": int(r[1]),
                "message": r[2],
                "response": r[3],
                "intent": r[4],
                "stage_after": r[5],
                "kanban_action": r[6],
                "rules_applied": rules or [],
                "latency_ms": int(r[8]) if r[8] is not None else None,
                "criado_em": r[9].isoformat() if r[9] is not None else None,
            }
        )
    return out


__all__ = ["simulate", "list_simulations", "SIMULATOR_MODEL"]