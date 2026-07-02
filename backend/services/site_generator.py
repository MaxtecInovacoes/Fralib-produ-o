"""Site Generator (Sprint 1.4).

Camada fina que consulta o KPI aggregator para escolher o melhor template
de site por nicho.

API pública:

- ``get_best_template(tenant_id, nicho)`` → ``str | None``
  Retorna id do template com maior taxa de conversão histórica.

Quando DB/KPI indisponível, retorna ``None`` e o caller cai para o
template padrão do nicho (heurística legada).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("site_generator")


def get_best_template(
    tenant_id: int | None = None,
    nicho: str | None = None,
) -> str | None:
    """Retorna o melhor template de site para o nicho.

    Lê ``sdr_kpi_aggregated`` via ``sdr_kpi_aggregator.melhor_template_por_nicho``.

    Returns:
        String id do template (``tpl_clarity`` etc) ou ``None``.
    """
    if not nicho:
        return None
    try:
        from backend.services.sdr_kpi_aggregator import (
            melhor_template_por_nicho,
        )
        return melhor_template_por_nicho(nicho)
    except Exception as exc:
        logger.warning(f"get_best_template falhou: {exc}")
        return None


def get_best_template_from_kpi(nicho: str) -> str | None:
    """Wrapper de lookup direta, para monkeypatch nos testes."""
    return get_best_template(nicho=nicho)


__all__ = ["get_best_template"]
