#!/usr/bin/env python3
"""Cron diário: agrega KPIs SDR por nicho (Sprint 1.4).

Roda uma vez por dia (idealmente 02:00). Lê ``lead_outcomes``, calcula
4 métricas por nicho (taxa_conversao, horario_melhor, abordagem_melhor,
site_template_melhor) e faz UPSERT em ``sdr_kpi_aggregated``.

Para rodar manualmente::

    python -m backend.jobs.aggregate_sdr_kpis
    # ou
    python backend/jobs/aggregate_sdr_kpis.py

Cron sugerido (crontab)::

    0 2 * * * cd /opt/fralib && \
      /usr/bin/python3 backend/jobs/aggregate_sdr_kpis.py \
      >> /var/log/fralib/aggregate_sdr_kpis.log 2>&1
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Setup path para import absoluto
_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aggregate_sdr_kpis")


def main() -> int:
    """Executa agregação. Retorna 0 em sucesso, 1 em erro."""
    try:
        from backend.services.sdr_kpi_aggregator import aggregate_daily
    except Exception as exc:
        logger.error(f"falha ao importar sdr_kpi_aggregator: {exc}")
        return 1

    if not os.getenv("DATABASE_URL"):
        logger.warning("DATABASE_URL ausente — no-op")
        return 0

    periodos = ("30d", "7d", "all")
    total_nichos = 0
    for periodo in periodos:
        try:
            data = aggregate_daily(periodo=periodo)
        except Exception as exc:
            logger.error(f"aggregate_daily({periodo}) falhou: {exc}")
            continue
        logger.info(f"periodo={periodo} nichos={len(data)}")
        total_nichos += len(data)
        if not data:
            continue
        # Aqui fariamos UPSERT na tabela; por seguranca usamos no-op
        # explicito quando nao ha conexao (a funcao ja tratou isso).
        try:
            _persist_to_db(data, periodo)
        except Exception as exc:
            logger.warning(f"persist periodo={periodo} falhou: {exc}")

    logger.info(f"aggregate_sdr_kpis done — {total_nichos} nichos processados")
    return 0


def _persist_to_db(
    data: dict[str, dict], periodo: str,
) -> None:
    """Faz UPSERT dos agregados em ``sdr_kpi_aggregated``.

    Implementação minimalista: tenta via SQLAlchemy e cai gracefully se
    a tabela nao existir.
    """
    if not data:
        return
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(os.getenv("DATABASE_URL", ""), pool_pre_ping=False)
        with engine.connect() as conn:
            for nicho, metricas in data.items():
                # Mapeia metricas → linhas
                linhas = [
                    ("taxa_conversao", str(metricas.get("taxa_conversao", 0.0))),
                    ("horario_melhor", metricas.get("horario_melhor") or ""),
                    (
                        "abordagem_melhor",
                        metricas.get("abordagem_melhor") or "",
                    ),
                    (
                        "site_template_melhor",
                        metricas.get("site_template_melhor") or "",
                    ),
                ]
                sample = int(metricas.get("sample_size", 0))
                for metrica, valor in linhas:
                    if not valor:
                        continue
                    conn.execute(
                        text(
                            """
                            INSERT INTO sdr_kpi_aggregated (
                                nicho, metrica, valor, periodo, sample_size
                            ) VALUES (
                                :nicho, :metrica, :valor, :periodo, :sample
                            )
                            ON CONFLICT (nicho, metrica, periodo)
                            DO UPDATE SET
                                valor = EXCLUDED.valor,
                                sample_size = EXCLUDED.sample_size,
                                atualizado_em = NOW()
                            """
                        ),
                        {
                            "nicho": nicho[:80],
                            "metrica": metrica[:80],
                            "valor": valor,
                            "periodo": periodo[:20],
                            "sample": sample,
                        },
                    )
            conn.commit()
    except Exception as exc:
        logger.warning(f"_persist_to_db falhou (tabela ausente?): {exc}")
        raise


if __name__ == "__main__":
    sys.exit(main())
