"""Deterministic visual fingerprint for generated landing pages."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any


def build_visual_fingerprint(html: str, prd: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract a compact, comparable visual signature from final HTML + PRD."""
    prd = prd or {}
    lower = (html or "").lower()
    section_order = _section_order(html) or _contract_section_order(prd)
    palette = _palette(html, prd)
    typography = _typography(html, prd)
    fingerprint = {
        "version": 1,
        "hero": _hero_signature(html, prd),
        "section_order": section_order,
        "container": _container_signature(lower),
        "grids": _count_classes(lower, ("grid", "columns-", "flex", "bento")),
        "typography": typography,
        "palette": palette,
        "media_count": len(re.findall(r"<img\b|background-image\s*:", lower)),
        "density": _density(html),
        "cards": _count_classes(lower, ("card", "rounded", "shadow", "border")),
        "borders": lower.count("border"),
        "radius": _radius_signature(lower),
        "motion": _motion_signature(lower),
    }
    fingerprint["hash"] = _stable_hash(fingerprint)
    return fingerprint


def fingerprint_similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Return 0..1 similarity between two visual fingerprints."""
    if not a or not b:
        return 0.0
    scores = [
        _jaccard(a.get("section_order", []), b.get("section_order", [])),
        _jaccard(a.get("palette", []), b.get("palette", [])),
        _jaccard(_dict_values(a.get("typography", {})), _dict_values(b.get("typography", {}))),
        1.0 if a.get("hero") == b.get("hero") else 0.0,
        1.0 - min(abs(int(a.get("media_count", 0)) - int(b.get("media_count", 0))) / 8, 1.0),
        1.0 if a.get("container") == b.get("container") else 0.0,
        1.0 if a.get("density") == b.get("density") else 0.0,
        1.0 if a.get("radius") == b.get("radius") else 0.0,
    ]
    return round(sum(scores) / len(scores), 4)


def _section_order(html: str) -> list[str]:
    sections = []
    for match in re.finditer(r"<section\b([^>]*)>", html or "", re.IGNORECASE):
        attrs = match.group(1)
        ident = _attr(attrs, "id") or _data_block(attrs) or _first_class(attrs)
        if ident:
            sections.append(_normalize(ident))
    return sections[:16]


def _contract_section_order(prd: dict[str, Any]) -> list[str]:
    variation = prd.get("variation_blueprint") if isinstance(prd.get("variation_blueprint"), dict) else {}
    order = variation.get("ordem_das_secoes") if isinstance(variation, dict) else []
    return [_normalize(item) for item in order or [] if str(item).strip()]


def _hero_signature(html: str, prd: dict[str, Any]) -> str:
    variation = prd.get("variation_blueprint") if isinstance(prd.get("variation_blueprint"), dict) else {}
    if variation.get("template_hero"):
        return str(variation["template_hero"])
    first_section = re.search(r"<section\b([^>]*)>", html or "", re.IGNORECASE)
    if not first_section:
        return "unknown"
    attrs = first_section.group(1).lower()
    if "full" in attrs or "bleed" in attrs:
        return "full-bleed"
    if "split" in attrs or "grid" in attrs:
        return "split-grid"
    if "center" in attrs:
        return "centered"
    return _first_class(attrs) or "section-hero"


def _palette(html: str, prd: dict[str, Any]) -> list[str]:
    palette = []
    color_palette = prd.get("color_palette") if isinstance(prd.get("color_palette"), dict) else {}
    tokens = color_palette.get("tokens_oklch") if isinstance(color_palette.get("tokens_oklch"), dict) else {}
    palette.extend(str(value).lower() for value in tokens.values() if value)
    palette.extend(re.findall(r"#[0-9a-fA-F]{3,8}", html or "")[:12])
    palette.extend(re.findall(r"oklch\([^)]+\)", html or "", re.IGNORECASE)[:12])
    return list(dict.fromkeys(palette))[:16]


def _typography(html: str, prd: dict[str, Any]) -> dict[str, str]:
    typography = prd.get("typography") if isinstance(prd.get("typography"), dict) else {}
    fonts = re.findall(r"font-family\s*:\s*([^;}]+)", html or "", re.IGNORECASE)
    result = {str(key): str(value) for key, value in typography.items() if value}
    if fonts:
        result.setdefault("html_font_sample", fonts[0].strip("\"' "))
    return result


def _container_signature(lower: str) -> str:
    if "max-w-7xl" in lower or "max-width:1280" in lower:
        return "wide"
    if "max-w-5xl" in lower or "max-width:1024" in lower:
        return "medium"
    if "container" in lower:
        return "container"
    return "fluid"


def _radius_signature(lower: str) -> str:
    if "rounded-full" in lower or "border-radius:999" in lower:
        return "pill"
    if "rounded-3xl" in lower or "32px" in lower:
        return "large"
    if "rounded" in lower or "border-radius" in lower:
        return "medium"
    return "sharp"


def _motion_signature(lower: str) -> list[str]:
    markers = ["reveal", "parallax", "ken-burns", "stagger", "transition", "animate-", "data-reveal"]
    return [marker for marker in markers if marker in lower]


def _density(html: str) -> str:
    text_len = len(re.sub(r"<[^>]+>", "", html or "").strip())
    sections = max((html or "").lower().count("<section"), 1)
    per_section = text_len / sections
    if per_section > 900:
        return "dense"
    if per_section > 450:
        return "balanced"
    return "sparse"


def _count_classes(lower: str, markers: tuple[str, ...]) -> int:
    return sum(lower.count(marker) for marker in markers)


def _attr(attrs: str, name: str) -> str:
    match = re.search(rf"{name}\s*=\s*['\"]([^'\"]+)['\"]", attrs or "", re.IGNORECASE)
    return match.group(1) if match else ""


def _data_block(attrs: str) -> str:
    return _attr(attrs, "data-block") or _attr(attrs, "data-section")


def _first_class(attrs: str) -> str:
    classes = _attr(attrs, "class")
    return classes.split()[0] if classes else ""


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _dict_values(value: dict[str, Any]) -> list[str]:
    return [str(item).lower() for item in value.values() if item]


def _jaccard(a: list[Any], b: list[Any]) -> float:
    left = set(map(str, a or []))
    right = set(map(str, b or []))
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _stable_hash(fingerprint: dict[str, Any]) -> str:
    payload = repr({key: value for key, value in fingerprint.items() if key != "hash"})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
