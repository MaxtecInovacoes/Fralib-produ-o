"""Shared database row helpers for FraLib scripts.

Canônico para T1 do plano DRY (codex/dry-refactor).
Os scripts ``audit_one_truth.py`` e ``fix_one_truth_mirror.py`` usavam cópias
idênticas desta função; ``reconcile_one_truth.py`` mantém sua versão local
porque propaga exceções em vez de engolir — ver nota no plano.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text


def rows(conn, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute ``sql`` on ``conn`` and return rows as dicts.

    On failure, returns ``[{"error": "<first line of exception>"}]`` so the
    caller can surface a structured failure instead of crashing the script.
    """
    try:
        return [dict(r._mapping) for r in conn.execute(text(sql), params or {}).fetchall()]
    except Exception as exc:
        return [{"error": str(exc).splitlines()[0]}]