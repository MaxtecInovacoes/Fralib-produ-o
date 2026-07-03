"""Lead supply filters module - normalization and deduplication utilities."""

from __future__ import annotations

import re
from typing import Any

from backend.services.lead_supply_providers import PLAN_DAILY_CAPS


def normalize_list(value: Any) -> list[str]:
    """Normalize a list of values, deduplicating and limiting to 25 items."""
    if value is None:
        return []
    if isinstance(value, str):
        raw = re.split(r"[,;\n]+|\s+\+\s+", value)
    elif isinstance(value, (list, tuple, set)):
        raw = []
        for item in value:
            if isinstance(item, str):
                raw.extend(re.split(r"[,;\n]+|\s+\+\s+", item))
            else:
                raw.append(item)
    else:
        raw = [value]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text_value = re.sub(r"\s+", " ", str(item or "").strip())
        key = text_value.lower()
        if text_value and key not in seen:
            cleaned.append(text_value)
            seen.add(key)
    return cleaned[:25]


def default_targets(plano: str, meta_diaria: int | None = None) -> dict[str, int]:
    """Calculate default inventory targets based on plan and daily goal."""
    plano_norm = (plano or "trial").lower()
    cap = PLAN_DAILY_CAPS.get(plano_norm, 1)
    daily = max(1, min(int(meta_diaria or cap), cap))
    monthly = daily * 30
    ideal = max(daily * 10, int(monthly * 1.2))
    minimum = max(daily * 3, int(ideal * 0.72))
    return {
        "meta_diaria": daily,
        "estoque_minimo": minimum,
        "estoque_alvo": ideal,
        "limite_diario_plano": cap,
    }


def dedupe_key(tenant_id: int, lead: dict[str, Any]) -> str:
    """Generate a deduplication key for a lead."""
    import hashlib

    place = str(lead.get("place_id") or "").strip().lower()
    if place:
        marker = f"place:{place}"
    else:
        digits = re.sub(r"\D+", "", str(lead.get("whatsapp") or lead.get("telefone") or ""))
        if digits.startswith("55") and len(digits) > 11:
            digits = digits[2:]
        website = re.sub(r"^https?://(www\.)?", "", str(lead.get("website") or "").strip().lower()).split("/")[0]
        nome = _slug(str(lead.get("nome") or ""))
        cidade = _slug(str(lead.get("cidade") or ""))
        endereco = _slug(str(lead.get("endereco") or ""))[:48]
        if digits:
            marker = f"phone:{digits}"
        elif website:
            marker = f"web:{website}"
        else:
            marker = f"name:{nome}:{cidade}:{endereco}"
    return hashlib.sha1(f"{tenant_id}:{marker}".encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    """Convert a string to a URL-safe slug."""
    import unicodedata

    norm = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")


__all__ = [
    "normalize_list",
    "default_targets",
    "dedupe_key",
    "_slug",
]
