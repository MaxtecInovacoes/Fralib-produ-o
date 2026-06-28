from __future__ import annotations

from typing import Any


def _normalize_hex(value: str | None, fallback: str) -> str:
    raw = str(value or "").strip()
    if len(raw) == 7 and raw.startswith("#"):
        try:
            int(raw[1:], 16)
            return raw.lower()
        except ValueError:
            return fallback
    if len(raw) == 4 and raw.startswith("#"):
        try:
            return "#" + "".join(ch * 2 for ch in raw[1:]).lower()
        except Exception:
            return fallback
    return fallback


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = _normalize_hex(value, "#000000")
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(v))) for v in rgb])


def _mix_hex(color_a: str, color_b: str, weight_a: float) -> str:
    weight_a = max(0.0, min(1.0, float(weight_a)))
    ra, ga, ba = _hex_to_rgb(color_a)
    rb, gb, bb = _hex_to_rgb(color_b)
    return _rgb_to_hex(
        (
            round(ra * weight_a + rb * (1 - weight_a)),
            round(ga * weight_a + gb * (1 - weight_a)),
            round(ba * weight_a + bb * (1 - weight_a)),
        )
    )


def _luminance(color: str) -> float:
    def _channel(value: int) -> float:
        v = value / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(color)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(color_a: str, color_b: str) -> float:
    la = _luminance(color_a)
    lb = _luminance(color_b)
    lighter = max(la, lb)
    darker = min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def best_text_for_background(bg: str, *, dark: str = "#09130f", light: str = "#f8faf7") -> str:
    dark_ratio = contrast_ratio(bg, dark)
    light_ratio = contrast_ratio(bg, light)
    return dark if dark_ratio >= light_ratio else light


def resolve_cinematic_theme(
    facts: dict[str, Any],
    *,
    fallback_palette: dict[str, str],
    fallback_archetype: str,
    typography: dict[str, Any] | None = None,
    fonts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    segment = str(
        (
            (facts.get("business") or {}).get("segment")
            if isinstance(facts.get("business"), dict)
            else ""
        )
        or (facts.get("business") or {}).get("segmento")
        if isinstance(facts.get("business"), dict)
        else ""
        or facts.get("segmento")
        or facts.get("segment")
        or "servicos"
    ).lower()

    source = facts.get("color_palette")
    if not isinstance(source, dict) or not source.get("primary"):
        source = facts.get("paleta_cores")
    if not isinstance(source, dict) or not source.get("primary"):
        design_dna = facts.get("design_dna")
        source = design_dna.get("tokens") if isinstance(design_dna, dict) else None

    if not isinstance(source, dict) or not source.get("primary"):
        source = fallback_palette
        archetype = fallback_archetype
    else:
        archetype = str(source.get("archetype") or fallback_archetype).strip() or fallback_archetype

    primary = _normalize_hex(source.get("primary") or source.get("accent"), fallback_palette["primary"])
    secondary = _normalize_hex(source.get("secondary") or source.get("muted"), fallback_palette["secondary"])
    accent = _normalize_hex(source.get("accent") or primary, primary)
    bg_dark = _normalize_hex(source.get("background") or source.get("bg_dark"), fallback_palette["bg_dark"])
    bg_light = _normalize_hex(source.get("surface") or source.get("bg_light"), fallback_palette["bg_light"])
    text_dark = _normalize_hex(source.get("text") or source.get("text_dark"), fallback_palette["text_dark"])
    text_light = best_text_for_background(bg_dark)
    accent_contrast = best_text_for_background(primary)
    accent_dark = _mix_hex(primary, bg_dark, 0.3) if contrast_ratio(primary, bg_dark) < 2.4 else secondary
    accent_soft = _mix_hex(primary, "#ffffff", 0.2) if contrast_ratio(primary, "#ffffff") >= 2.2 else _mix_hex(primary, bg_light, 0.35)
    panel_text = best_text_for_background(bg_light, dark=text_dark, light=text_light)
    text_muted = _mix_hex(text_light, bg_dark, 0.62)

    palette = {
        "primary": primary,
        "primary_contrast": accent_contrast,
        "secondary": secondary,
        "accent": accent,
        "bg_dark": bg_dark,
        "bg_light": bg_light,
        "text_dark": text_dark,
        "text_light": text_light,
        "text_muted": text_muted,
        "accent_dark": accent_dark,
        "accent_soft": accent_soft,
        "accent_contrast": accent_contrast,
        "panel_text": panel_text,
        "border": source.get("border", "rgba(0,0,0,0.10)"),
        "gradient_start": source.get("gradient_start", "rgba(0,0,0,0.05)"),
        "gradient_end": source.get("gradient_end", "rgba(0,0,0,0.01)"),
    }
    return {
        "segment": segment,
        "archetype": archetype,
        "palette": palette,
        "typography": typography or {},
        "fonts": fonts or {},
    }
