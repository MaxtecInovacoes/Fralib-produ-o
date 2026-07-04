"""Safe JSON parsing helpers for the FraLib backend.

Canônico para M7 do plano DRY (codex/dry-refactor).

Fornece safe_json_load() para substituir o padrão repetido de
    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        data = {}
que aparece em ~40 call sites no projeto.
"""
from __future__ import annotations

import json
from typing import Any


def safe_json_load(
    raw: Any,
    default: Any = None,
) -> Any:
    """Parse ``raw`` as JSON, falling back to ``default`` on failure.

    Catches both ``ValueError`` (raw ``json.loads`` raises) and any other
    decoding error. Returns ``default`` (default ``None``) on failure.

    For call sites that need to log on failure, wrap manually — this helper
    deliberately does NOT log to preserve existing logging behavior at the
    call site.
    """
    if raw is None or raw == "":
        return default if default is not None else None
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default if default is not None else None
