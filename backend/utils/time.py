"""Time helpers for the FraLib backend.

Canônico para M14 do plano DRY (codex/dry-refactor).

Fornece now_iso_utc() — substitui 13 cópias inline de
``datetime.now(timezone.utc).isoformat()``.

Também oferece ``utcnow()`` (datetime com tz UTC, sem formatar)
para aritmética/comparação sem precisar de `.replace(tzinfo=...)`.
"""
from __future__ import annotations

from datetime import datetime, timezone


def now_iso_utc() -> str:
    """Return current UTC time as ISO-8601 string.

    Equivalente a ``datetime.now(timezone.utc).isoformat()``.
    Garante formato consistente em todos os call sites — Hermes usava
    ``timespec='seconds'`` (inconsistência) que essa versão unifica.
    """
    return datetime.now(timezone.utc).isoformat()


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    Equivalente a ``datetime.now(timezone.utc)``.
    Helper para aritmética/comparação sem ter que importar timezone.
    """
    return datetime.now(timezone.utc)


__all__ = ["now_iso_utc", "utcnow"]