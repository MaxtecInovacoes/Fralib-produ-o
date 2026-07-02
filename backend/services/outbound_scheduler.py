"""Outbound Scheduler (Sprint 1.4).

Camada fina que consulta o KPI aggregator para escolher o melhor horário
para enviar uma mensagem outbound por nicho.

API pública:

- ``get_best_send_hour(tenant_id, nicho)`` → ``str | None``
  Retorna ``HH:MM`` com maior taxa de conversão histórica para o nicho.
  Se não houver dados suficientes, retorna ``None``.

- ``schedule_outbound(tenant_id, lead_id, nicho, message)`` → ``dict``
  Combina melhor horário + enqueue_outbound (lógica de scheduling).

Quando DB/KPI indisponível, retorna ``None`` (fail-safe).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("outbound_scheduler")


def get_best_send_hour(
    tenant_id: int | None = None,
    nicho: str | None = None,
) -> str | None:
    """Retorna o melhor horário (HH:MM) para enviar outbound para um nicho.

    Lê ``sdr_kpi_aggregated`` via ``sdr_kpi_aggregator.melhor_horario_por_nicho``.

    Returns:
        String ``HH:MM`` ou ``None`` se sem dados.
    """
    if not nicho:
        return None
    try:
        from backend.services.sdr_kpi_aggregator import (
            melhor_horario_por_nicho,
        )
        return melhor_horario_por_nicho(nicho)
    except Exception as exc:
        logger.warning(f"get_best_send_hour falhou: {exc}")
        return None


def get_best_send_hour_from_kpi(nicho: str) -> str | None:
    """Wrapper de lookup direta, para monkeypatch nos testes."""
    return get_best_send_hour(nicho=nicho)


def schedule_outbound(
    tenant_id: int,
    lead_id: str,
    nicho: str,
    message: str,
) -> dict[str, Any]:
    """Decide horário e enfileira msg na outbound_queue.

    Sempre enfileira (não é bloqueante). O KPI apenas informa o melhor
    horário, mas a fila é respeitada pelo worker outbound.
    """
    best_hour = get_best_send_hour(tenant_id=tenant_id, nicho=nicho)
    result: dict[str, Any] = {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "nicho": nicho,
        "best_send_hour": best_hour,
        "queued": False,
        "queue_id": None,
    }
    try:
        from sqlalchemy import create_engine
        from datetime import datetime, timedelta
        from backend.services.outbound_queue import enqueue_outbound

        engine = create_engine(
            __import__("os").getenv("DATABASE_URL", ""),
            pool_pre_ping=False,
        )
        scheduled_delay = 0
        if best_hour:
            # Calcula delay até o horário
            try:
                hh, mm = [int(x) for x in best_hour.split(":")[:2]]
                now = datetime.now()
                target = now.replace(hour=hh, minute=mm, second=0)
                if target < now:
                    target = target + timedelta(days=1)
                scheduled_delay = int((target - now).total_seconds())
            except Exception:
                scheduled_delay = 0

        qid = enqueue_outbound(
            engine,
            tenant_id=tenant_id,
            lead_id=str(lead_id),
            phone="",
            message=message,
            source="kpi_scheduler",
            priority=4,
            delay_sec=scheduled_delay,
        )
        result["queued"] = qid is not None
        result["queue_id"] = qid
    except Exception as exc:
        logger.warning(f"schedule_outbound no-op: {exc}")
    return result


__all__ = ["get_best_send_hour", "schedule_outbound"]
