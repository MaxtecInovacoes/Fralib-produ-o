"""Helpers de envio HTTP para o Meowhats + detecção de erros de saúde.

send_text_parts (legado): assinatura original, preservada para callers
que só precisam de (ok, error).

send_text_parts_with_health: versão nova que detecta padrões de erro
do whatsmeow (440, 429, restricted, banned) e grava em phone_health_events.
Retorna (ok, error, severity) onde severity ∈ {None, 'warn', 'error', 'critical'}.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# Padrões de erro whatsmeow/WhatsApp Web que indicam restrição real.
# Quando o whatsmeow devolve XML com <error code="...">, esses são os
# códigos relevantes para qualidade do número.
RESTRICTION_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # (regex, event_type, severity)
    (re.compile(r'code="131047"', re.I), "restricted", "critical"),     # generic restriction
    (re.compile(r'code="131056"', re.I), "rate_limited", "error"),      # rate limit exceeded
    (re.compile(r'code="429"', re.I), "rate_limited", "warn"),
    (re.compile(r'code="440"', re.I), "rate_limited", "error"),
    (re.compile(r"temporarily banned", re.I), "banned", "critical"),
    (re.compile(r"phone.{0,5}number.{0,5}banned", re.I), "banned", "critical"),
    (re.compile(r"account.{0,5}banned", re.I), "banned", "critical"),
    (re.compile(r"spam.{0,5}detected", re.I), "restricted", "critical"),
    (re.compile(r"quality.{0,5}rating", re.I), "restricted", "warn"),
]

# Status HTTP relevantes
HTTP_RESTRICTION_STATUSES: dict[int, str] = {
    403: "forbidden",
    429: "rate_limited",
    440: "rate_limited",
    503: "service_unavailable",
}


def send_presence_composing(
    http_client: Any, base_url: str, api_key: str, tenant_id: str, jid: str,
) -> Any:
    """Envia presence=typing; falhas daqui não devem derrubar o fluxo."""
    return http_client.post(
        f"{base_url}/api/sessions/{tenant_id}/presence",
        headers={"X-API-Key": api_key},
        json={"jid": jid, "type": "composing"},
    )


def send_text_parts(
    http_client: Any,
    base_url: str,
    api_key: str,
    tenant_id: str,
    jid: str,
    parts: list[str],
    before_send: Any = None,
) -> tuple[bool, str]:
    """Envia resposta em múltiplas partes. Mantida para compatibilidade."""
    last_error = ""
    for idx, part in enumerate(parts):
        if before_send is not None:
            before_send(idx, part)
        response = http_client.post(
            f"{base_url}/api/sessions/{tenant_id}/send",
            headers={"X-API-Key": api_key},
            json={"jid": jid, "type": "text", "text": part},
        )
        if response.status_code != 200:
            last_error = (response.text or "")[:80]
            return False, last_error
    return True, last_error


def send_text_parts_with_health(
    http_client: Any,
    base_url: str,
    api_key: str,
    tenant_id: str,
    jid: str,
    parts: list[str],
    *,
    engine: Engine | None,
    user_id: int | None,
    before_send: Any = None,
) -> tuple[bool, str, str | None]:
    """Versão instrumentada de send_text_parts.

    Detecta erros de restrição e grava em phone_health_events.
    Retorna (ok, last_error, severity) onde severity ∈ {None, 'warn', 'error', 'critical'}.
    """
    last_error = ""
    last_severity: str | None = None
    last_event_type: str | None = None

    for idx, part in enumerate(parts):
        if before_send is not None:
            before_send(idx, part)
        response = http_client.post(
            f"{base_url}/api/sessions/{tenant_id}/send",
            headers={"X-API-Key": api_key},
            json={"jid": jid, "type": "text", "text": part},
        )
        if response.status_code != 200:
            body = response.text or ""
            last_error = body[:200]
            severity, event_type = classify_error(response.status_code, body)
            last_severity = severity
            last_event_type = event_type

            if severity is not None and engine is not None and user_id is not None:
                _record_health_event(
                    engine,
                    user_id=user_id,
                    severity=severity,
                    event_type=event_type,
                    detail={
                        "status_code": response.status_code,
                        "body_excerpt": body[:500],
                        "jid": jid,
                        "part_index": idx,
                    },
                )
            return False, last_error, severity

    return True, last_error, None


def send_handoff_notification(
    http_client: Any,
    base_url: str,
    api_key: str,
    tenant_id: str,
    closer_number: str,
    text: str,
) -> Any:
    """Notifica o closer humano pelo mesmo device do tenant."""
    closer_jid = f"{closer_number}@s.whatsapp.net"
    return http_client.post(
        f"{base_url}/api/sessions/{tenant_id}/send",
        headers={"X-API-Key": api_key},
        json={"jid": closer_jid, "type": "text", "text": text},
    )


# ── Helpers internos ───────────────────────────────────────────────────

def classify_error(status_code: int, body: str) -> tuple[str | None, str]:
    """Classifica um erro HTTP em (severity, event_type).

    Retorna (None, 'ok') se não for erro de saúde (apenas erro genérico).
    """
    for pattern, event_type, severity in RESTRICTION_PATTERNS:
        if pattern.search(body):
            return severity, event_type
    if status_code in HTTP_RESTRICTION_STATUSES:
        return "warn", HTTP_RESTRICTION_STATUSES[status_code]
    return None, "ok"


def _record_health_event(
    engine: Engine,
    *,
    user_id: int,
    severity: str,
    event_type: str,
    detail: dict[str, Any],
) -> None:
    """Grava evento em phone_health_events. Tolerante a falha."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO phone_health_events
                      (user_id, severity, event_type, detail)
                    VALUES
                      (:user_id, :severity, :event_type, CAST(:detail AS JSONB))
                    """
                ),
                {
                    "user_id": user_id,
                    "severity": severity,
                    "event_type": event_type,
                    "detail": json.dumps(detail),
                },
            )
        # Marcar ultima_restricao_em quando severity=critical
        if severity == "critical":
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE phone_health_score
                        SET ultima_restricao_em = NOW()
                        WHERE user_id = :user_id
                          AND (ultima_restricao_em IS NULL OR ultima_restricao_em < NOW() - INTERVAL '1 hour')
                        """
                    ),
                    {"user_id": user_id},
                )
    except Exception as exc:
        logger.warning(
            "[phone_health_events] insert falhou (user=%s severity=%s): %s",
            user_id, severity, exc,
        )