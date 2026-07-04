"""Safe numeric casting helpers for the FraLib backend.

Canônico para M10 do plano DRY (codex/dry-refactor).

Fornece safe_int(value) / safe_float(value) (default 0 / 0.0, soma listas)
e safe_cast_int(value, default=None) / safe_cast_float(value, default=None)
(default explícito, sem soma listas).

Unifica 2 pares divergentes:
  - backend/services/facebook_ads_service.py:86 (soma listas, default 0/0.0)
  - backend/agents/sdr_langgraph/agent.py:1850 (default explícito, sem soma)

Os call sites têm semântica diferente:
  - Facebook Ads API retorna listas de valores por dia → soma faz sentido.
  - SDR state tem campos singulares → default explícito, sem soma.

Por isso oferecemos dois pares de funções:
  - safe_int / safe_float: para agregação de listas (default 0/0.0)
  - safe_cast_int / safe_cast_float: para campos singulares (default None)
"""
from __future__ import annotations

from typing import Any


def safe_int(value: Any, default: int = 0) -> int:
    """Converte ``value`` para int, somando listas.

    None, falsy (False, "", []), ou falha de conversão → ``default``.
    Listas são somadas (filtrando elementos falsy).
    """
    if isinstance(value, list):
        try:
            return sum(int(x) for x in value if x)
        except (TypeError, ValueError):
            return default
    try:
        return int(value) if value else default
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Converte ``value`` para float, somando listas.

    None, falsy, ou falha de conversão → ``default``.
    Listas são somadas (filtrando elementos falsy).
    """
    if isinstance(value, list):
        try:
            return sum(float(x) for x in value if x)
        except (TypeError, ValueError):
            return default
    try:
        return float(value) if value else default
    except (TypeError, ValueError):
        return default


def safe_cast_int(value: Any, default: int | None = None) -> int | None:
    """Converte ``value`` para int sem somar listas.

    None → ``default``. Falha de conversão → ``default``.
    Não trata listas (levanta TypeError se receber).
    """
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_cast_float(value: Any, default: float | None = 0.0) -> float | None:
    """Converte ``value`` para float sem somar listas.

    None → ``default``. Falha de conversão → ``default``.
    Não trata listas (levanta TypeError se receber).
    """
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = ["safe_int", "safe_float", "safe_cast_int", "safe_cast_float"]