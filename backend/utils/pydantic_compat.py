"""Pydantic v1/v2 compatibility shim for the FraLib backend.

Canônico para B5 do plano DRY (codex/dry-refactor).

Substitui o padrão:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj.__dict__
que aparece em 8+ arquivos (providers, agents, services).
"""
from __future__ import annotations

from typing import Any


def to_dict(model: Any) -> dict[str, Any]:
    """Serialize a Pydantic model (v1 or v2) to a plain dict.

    Tries, in order: ``model_dump`` (v2), ``dict`` (v1), ``__dict__``,
    or returns the model unchanged if it is already a ``dict``.
    """
    if isinstance(model, dict):
        return dict(model)
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(getattr(model, "__dict__", {}) or {})
