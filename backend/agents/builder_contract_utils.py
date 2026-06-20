"""Small typed helpers for Builder/Prompt contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def first_value(data: Mapping[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def archetype_id_from_visual_dna(visual_dna: Mapping[str, Any], *, default: str = "") -> str:
    archetype = visual_dna.get("archetype")
    if isinstance(archetype, Mapping):
        return str(
            archetype.get("archetype")
            or archetype.get("id")
            or archetype.get("name")
            or default
        ).upper()
    return str(archetype or visual_dna.get("id") or default).upper()
