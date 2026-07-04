"""Safe env-var parsing helpers for the FraLib backend.

Canônico para M3 do plano DRY (codex/dry-refactor).

Substitui o padrão _env_int() que aparecia byte-idêntico (ou quase) em:
  - backend/utils/google_scraper_helpers.py
  - backend/utils/agente1_hunter_v2.py
  - backend/services/vite_react_renderer.py
  - backend/services/vite_config_helpers.py
  - backend/services/vite_config.py
"""
from __future__ import annotations

import os
from typing import Optional


def env_int(
    name: str,
    default: int,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """Parse an integer from an environment variable.

    Falls back to ``default`` if the variable is missing or unparseable.
    Optionally clamps to ``[min_value, max_value]`` when both are provided
    (``min_value`` and/or ``max_value`` may also be passed individually).
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        value = default
    else:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(value, max_value)
    return value
