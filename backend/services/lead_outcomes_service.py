"""Serviço de outcome do lead (Sprint 1.4).

Quando o SDR muda um lead para ``ganho`` ou ``perdido``, este módulo grava
1 linha em ``lead_outcomes``. Esse log é a fonte de verdade para o
aggregator diário que retroalimenta outbound/prompt_selector/site_generator
com o melhor horário, abordagem e template por nicho.

API pública:

- ``record_outcome(lead_id, tenant_id, nicho, horario_contato,
  abordagem_usada, site_template_usado, kanban_stage_final,
  dias_ate_fechamento)`` → ``int | None``

Comportamento:

- Falha transparente: se DB indisponível, retorna ``None`` sem levantar
  exceção (o hook do SDR agent não pode quebrar o grafo).
- Idempotente no nível de inserção simples (INSERT puro); se quiser
  idempotência estrita, use ``ON CONFLICT DO NOTHING`` passando
  ``idempotency_key``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("lead_outcomes_service")

# Defaults opcionais (para testes sem DB)
_database_url: str = os.getenv("DATABASE_URL", "")


def _get_engine() -> Any:
    """Cria engine SQLAlchemy a partir de ``DATABASE_URL``."""
    from sqlalchemy import create_engine

    return create_engine(_database_url, pool_pre_ping=False)


def record_outcome(
    lead_id: int | str,
    tenant_id: int,
    nicho: str | None = None,
    horario_contato: str | None = None,
    abordagem_usada: str | None = None,
    site_template_usado: str | None = None,
    kanban_stage_final: str | None = None,
    dias_ate_fechamento: int | None = None,
    *,
    idempotency_key: str | None = None,
) -> int | None:
    """Insere 1 linha em ``lead_outcomes``.

    Args:
        lead_id: id do lead (int ou string).
        tenant_id: id do tenant.
        nicho: nicho/segmento do lead. Default: ``None``.
        horario_contato: hora do 1º contato (string ``HH:MM`` ou ``HH:MM:SS``).
        abordagem_usada: tom de abordagem (``consultivo`` / ``lobo`` etc).
        site_template_usado: template renderizado (``tpl_clarity`` etc).
        kanban_stage_final: ``ganho`` / ``perdido``.
        dias_ate_fechamento: dias entre 1º contato e fechamento.
        idempotency_key: chave opcional para ON CONFLICT.

    Returns:
        ID inserido ou ``None`` se DB indisponível / erro.
    """
    if not _database_url:
        logger.info("record_outcome no-op: DATABASE_URL ausente")
        return None
    if not lead_id or not tenant_id:
        return None
    try:
        from sqlalchemy import text

        engine = _get_engine()
        with engine.connect() as conn:
            if idempotency_key:
                row = conn.execute(
                    text(
                        """
                        INSERT INTO lead_outcomes (
                            lead_id, tenant_id, nicho, horario_contato,
                            abordagem_usada, site_template_usado,
                            kanban_stage_final, dias_ate_fechamento
                        ) VALUES (
                            :lid, :tid, :nicho, :horario,
                            :abordagem, :template, :stage, :dias
                        )
                        ON CONFLICT DO NOTHING
                        RETURNING id
                        """
                    ),
                    {
                        "lid": int(lead_id) if str(lead_id).isdigit() else lead_id,
                        "tid": tenant_id,
                        "nicho": (nicho or "")[:80],
                        "horario": horario_contato,
                        "abordagem": (abordagem_usada or "")[:80],
                        "template": (site_template_usado or "")[:80],
                        "stage": (kanban_stage_final or "")[:40],
                        "dias": dias_ate_fechamento,
                    },
                ).fetchone()
            else:
                row = conn.execute(
                    text(
                        """
                        INSERT INTO lead_outcomes (
                            lead_id, tenant_id, nicho, horario_contato,
                            abordagem_usada, site_template_usado,
                            kanban_stage_final, dias_ate_fechamento
                        ) VALUES (
                            :lid, :tid, :nicho, :horario,
                            :abordagem, :template, :stage, :dias
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "lid": int(lead_id) if str(lead_id).isdigit() else lead_id,
                        "tid": tenant_id,
                        "nicho": (nicho or "")[:80],
                        "horario": horario_contato,
                        "abordagem": (abordagem_usada or "")[:80],
                        "template": (site_template_usado or "")[:80],
                        "stage": (kanban_stage_final or "")[:40],
                        "dias": dias_ate_fechamento,
                    },
                ).fetchone()
            conn.commit()
        if row:
            try:
                return int(row[0])
            except Exception:
                return None
        return None
    except Exception as exc:
        # Falha transparente - nunca quebrar o agente SDR.
        logger.warning(f"record_outcome no-op: {exc}")
        return None


__all__ = ["record_outcome"]
