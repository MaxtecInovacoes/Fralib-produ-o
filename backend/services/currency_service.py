"""Currency Service — cotação USD/BRL e conversões (Sprint 0.3).

Operações:
  - get_usd_brl_rate() — lê cotação cacheada ou busca em API pública (AwesomeAPI).
  - refresh_usd_brl_rate() — força refresh + persiste em cost_events.
  - convert_usd_to_brl(usd, rate) — converter valor USD → BRL.
"""

from __future__ import annotations

import json
import logging
import os
import time
from decimal import Decimal
from typing import Any

logger = logging.getLogger("fralib.currency_service")


# API pública brasileira para USD-BRL (AwesomeAPI / economia.awesomeapi.com.br).
# Não requer key. Fallback: 5.65 (default estático).
_AWESOME_URL = os.getenv(
    "USD_BRL_API_URL",
    "https://economia.awesomeapi.com.br/json/last/USD-BRL",
)


def fetch_usd_brl_quote(timeout_s: float = 5.0) -> float | None:
    """Busca cotação USD/BRL em API pública.

    Returns:
        Cotação como float, ou None em caso de erro.
    """
    import requests

    try:
        r = requests.get(_AWESOME_URL, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        # AwesomeAPI formato: {"USDBRL": {"bid": "5.6543", ...}}
        if isinstance(data, dict):
            pair = data.get("USDBRL") or data.get("usdbrl") or data
            if isinstance(pair, dict):
                bid = pair.get("bid") or pair.get("ask")
                if bid is not None:
                    return float(bid)
        logger.warning("[currency] resposta inesperada: %s", json.dumps(data)[:200])
    except Exception as exc:
        logger.warning("[currency] fetch falhou: %s", exc)
    return None


def convert_usd_to_brl(
    usd: float,
    rate: float | None = None,
    *,
    default: float | None = None,
) -> float:
    """Converte valor em USD para BRL.

    Args:
        usd: valor em USD.
        rate: cotação USD/BRL (None = usa default estático 5.65).
        default: override do default estático.

    Returns:
        Valor convertido em BRL (arredondado em 4 casas decimais).
    """
    if usd is None:
        return 0.0
    used_rate = rate if rate and rate > 0 else (default or 5.65)
    try:
        brl = Decimal(str(usd)) * Decimal(str(used_rate))
        return float(brl.quantize(Decimal("0.0001")))
    except Exception:
        return 0.0


def refresh_usd_brl_rate(engine: Any) -> dict[str, Any]:
    """Cron-friendly: busca cotação atual e persiste 1 cost_event (metadata).

    Returns:
        Dict com {rate, source, persisted, error}.
    """
    rate = fetch_usd_brl_quote()
    persisted = False
    if rate is None:
        rate = 5.65  # fallback estático
        source = "fallback"
    else:
        source = "awesomeapi"

    try:
        from backend.agents.cost_tracker import record_cost_event

        persisted = record_cost_event(
            provider="currency_service",
            service="refresh_usd_brl",
            custo_usd=0.0,
            custo_brl=0.0,
            cotacao_usd_brl=rate,
            status="success",
            metadata={"source": source, "rate": rate, "kind": "currency_quote"},
        )
    except Exception as exc:
        logger.warning("[currency] persist falhou: %s", exc)

    return {
        "rate": rate,
        "source": source,
        "persisted": persisted,
        "checked_at": int(time.time()),
    }


def last_known_usd_brl(engine: Any) -> float:
    """Recupera última cotação conhecida do cost_events (metadata.kind='currency_quote')."""
    if engine is None:
        return 5.65
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT metadata FROM cost_events
                    WHERE provider = 'currency_service'
                      AND service = 'refresh_usd_brl'
                      AND status = 'success'
                    ORDER BY criado_em DESC
                    LIMIT 1
                    """
                )
            ).fetchone()
        if row:
            meta = row[0] if not hasattr(row, "_mapping") else row._mapping.get("metadata")
            if isinstance(meta, str):
                meta = json.loads(meta)
            if isinstance(meta, dict):
                rate = meta.get("rate")
                if rate:
                    return float(rate)
    except Exception as exc:
        logger.warning("[currency] last_known falhou: %s", exc)
    return 5.65
