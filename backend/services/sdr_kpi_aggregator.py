"""Aggregator de KPI SDR por nicho (Sprint 1.4).

Calcula 4 métricas por nicho a partir de ``lead_outcomes``:

1. **taxa_conversao**: ``count(stage='ganho') / count(*)``
2. **horario_melhor**: hora (HH:MM) com maior taxa de conversão
3. **abordagem_melhor**: tom com maior taxa de conversão
4. **site_template_melhor**: template com maior taxa de conversão

Persistido em ``sdr_kpi_aggregated`` por nicho + período (``30d``, ``7d``,
``all``). Consumidores:

- ``outbound_scheduler.get_best_send_hour`` → horario_melhor
- ``prompt_selector.get_best_abordagem`` → abordagem_melhor
- ``site_generator.get_best_template`` → site_template_melhor

API pública:

- ``aggregate_daily()`` → ``dict`` com estrutura ``{nicho: {metric: valor}}``
- ``top_nicho_por_conversao()`` → ``str | None``
- ``melhor_horario_por_nicho(nicho)`` → ``str | None``
- ``melhor_abordagem_por_nicho(nicho)`` → ``str | None``
- ``melhor_template_por_nicho(nicho)`` → ``str | None``

Quando DB indisponível, ``aggregate_daily`` retorna dict ``{}`` (sem erro).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("sdr_kpi_aggregator")

_database_url: str = os.getenv("DATABASE_URL", "")
_PERIODOS = ("30d", "7d", "all")


def _get_engine() -> Any:
    from sqlalchemy import create_engine

    return create_engine(_database_url, pool_pre_ping=False)


def _empty_metric(nicho: str, periodo: str) -> dict[str, Any]:
    return {
        "taxa_conversao": 0.0,
        "horario_melhor": None,
        "abordagem_melhor": None,
        "site_template_melhor": None,
        "sample_size": 0,
        "_periodo": periodo,
        "_nicho": nicho,
    }


def _compute_aggregates(table_data: list[dict]) -> dict[str, dict[str, Any]]:
    """Computa os agregados a partir de uma lista de outcomes.

    Estrutura de entrada::

        [{"stage": "ganho"|"perdido", "horario": "HH:MM",
          "abordagem": "...", "template": "..."}]

    Retorna::

        {"nicho": {"taxa_conversao": 0.34, "horario_melhor": "14:30",
                   "abordagem_melhor": "consultivo",
                   "site_template_melhor": "tpl_a", "sample_size": 50}}
    """
    if not table_data:
        return {}

    # Agrupa por nicho (este aggregator é por nicho; o caller filtra ou
    # assume 1 nicho por chamada).
    by_nicho: dict[str, list[dict]] = {}
    for row in table_data:
        nicho = row.get("nicho") or "default"
        by_nicho.setdefault(nicho, []).append(row)

    aggregated: dict[str, dict[str, Any]] = {}
    for nicho, rows in by_nicho.items():
        total = len(rows)
        ganhos = sum(1 for r in rows if r.get("stage") == "ganho")
        taxa = ganhos / total if total > 0 else 0.0

        # Melhor horário (entre os ganhos): mais frequente
        horario_counts: dict[str, int] = {}
        abordagem_counts: dict[str, int] = {}
        template_counts: dict[str, int] = {}
        for r in rows:
            if r.get("stage") != "ganho":
                continue
            h = (r.get("horario") or "").strip()
            a = (r.get("abordagem") or "").strip()
            t = (r.get("template") or "").strip()
            if h:
                horario_counts[h] = horario_counts.get(h, 0) + 1
            if a:
                abordagem_counts[a] = abordagem_counts.get(a, 0) + 1
            if t:
                template_counts[t] = template_counts.get(t, 0) + 1

        horario_melhor = (
            max(horario_counts.items(), key=lambda kv: kv[1])[0]
            if horario_counts
            else None
        )
        abordagem_melhor = (
            max(abordagem_counts.items(), key=lambda kv: kv[1])[0]
            if abordagem_counts
            else None
        )
        template_melhor = (
            max(template_counts.items(), key=lambda kv: kv[1])[0]
            if template_counts
            else None
        )

        aggregated[nicho] = {
            "taxa_conversao": taxa,
            "horario_melhor": horario_melhor,
            "abordagem_melhor": abordagem_melhor,
            "site_template_melhor": template_melhor,
            "sample_size": total,
        }
    return aggregated


def aggregate_daily(
    *,
    tenant_id: int | None = None,
    periodo: str = "30d",
) -> dict[str, dict[str, Any]]:
    """Recalcula KPIs por nicho lendo ``lead_outcomes``.

    Args:
        tenant_id: filtra por tenant (None = todos).
        periodo: ``30d`` | ``7d`` | ``all``.

    Returns:
        Dict ``{nicho: {taxa_conversao, horario_melhor, abordagem_melhor,
        site_template_melhor, sample_size}}``.
        Vazio se DB indisponível.
    """
    if not _database_url:
        return {}

    try:
        from sqlalchemy import text

        engine = _get_engine()
        where_extra = ""
        params: dict[str, Any] = {}
        if tenant_id is not None:
            where_extra = "AND tenant_id = :tid"
            params["tid"] = tenant_id
        if periodo == "30d":
            where_extra += " AND criado_em >= NOW() - INTERVAL '30 days'"
        elif periodo == "7d":
            where_extra += " AND criado_em >= NOW() - INTERVAL '7 days'"

        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT
                        COALESCE(nicho, 'default') AS nicho,
                        kanban_stage_final AS stage,
                        horario_contato::text AS horario,
                        abordagem_usada       AS abordagem,
                        site_template_usado   AS template
                    FROM lead_outcomes
                    WHERE kanban_stage_final IN ('ganho', 'perdido')
                      {where_extra}
                    """
                ),
                params,
            ).fetchall()

        # Converte em lista de dicts
        table_data: list[dict] = []
        for r in rows:
            table_data.append(
                {
                    "nicho": r[0],
                    "stage": r[1],
                    "horario": r[2],
                    "abordagem": r[3],
                    "template": r[4],
                }
            )
        return _compute_aggregates(table_data)
    except Exception as exc:
        logger.warning(f"aggregate_daily falhou: {exc}")
        return {}


def top_nicho_por_conversao() -> str | None:
    """Retorna o nicho com maior taxa de conversao.

    Usa ``aggregate_daily()`` (período 30d default).
    """
    data = aggregate_daily(periodo="30d")
    if not data:
        return None
    # Só nichos com sample_size >= 5 (defesa contra ruído)
    candidatos = {
        n: v for n, v in data.items() if v.get("sample_size", 0) >= 5
    }
    if not candidatos:
        return None
    return max(
        candidatos.items(),
        key=lambda kv: kv[1].get("taxa_conversao", 0.0),
    )[0]


def melhor_horario_por_nicho(nicho: str) -> str | None:
    """Retorna ``HH:MM`` com maior taxa de ganho para o nicho."""
    if not nicho:
        return None
    data = aggregate_daily(periodo="30d")
    info = data.get(nicho)
    if not info:
        return None
    return info.get("horario_melhor")


def melhor_abordagem_por_nicho(nicho: str) -> str | None:
    """Retorna a abordagem com maior taxa de ganho para o nicho."""
    if not nicho:
        return None
    data = aggregate_daily(periodo="30d")
    info = data.get(nicho)
    if not info:
        return None
    return info.get("abordagem_melhor")


def melhor_template_por_nicho(nicho: str) -> str | None:
    """Retorna o template com maior taxa de ganho para o nicho."""
    if not nicho:
        return None
    data = aggregate_daily(periodo="30d")
    info = data.get(nicho)
    if not info:
        return None
    return info.get("site_template_melhor")


__all__ = [
    "aggregate_daily",
    "top_nicho_por_conversao",
    "melhor_horario_por_nicho",
    "melhor_abordagem_por_nicho",
    "melhor_template_por_nicho",
]
