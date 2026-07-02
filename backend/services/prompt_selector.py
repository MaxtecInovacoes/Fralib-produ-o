"""Prompt Selector (Sprint 1.4).

Camada fina que consulta o KPI aggregator para escolher a melhor abordagem
(tom de voz) por nicho ao montar system prompt do SDR.

API pública:

- ``get_best_abordagem(tenant_id, nicho)`` → ``str | None``
  Retorna ``"consultivo"`` / ``"lobo"`` / etc, conforme histórico.

Quando DB/KPI indisponível, retorna ``None`` e o caller cai para default.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("prompt_selector")


def get_best_abordagem(
    tenant_id: int | None = None,
    nicho: str | None = None,
) -> str | None:
    """Retorna a melhor abordagem (tom) para o nicho.

    Lê ``sdr_kpi_aggregated`` via ``sdr_kpi_aggregator.melhor_abordagem_por_nicho``.

    Returns:
        String ``"consultivo"`` / ``"lobo"`` / outro, ou ``None``.
    """
    if not nicho:
        return None
    try:
        from backend.services.sdr_kpi_aggregator import (
            melhor_abordagem_por_nicho,
        )
        return melhor_abordagem_por_nicho(nicho)
    except Exception as exc:
        logger.warning(f"get_best_abordagem falhou: {exc}")
        return None


def get_best_abordagem_from_kpi(nicho: str) -> str | None:
    """Wrapper de lookup direta, para monkeypatch nos testes."""
    return get_best_abordagem(nicho=nicho)


__all__ = ["get_best_abordagem"]
