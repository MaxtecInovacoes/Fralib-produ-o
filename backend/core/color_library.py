"""Validated palette library for deterministic visual diversity."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any


PALETTES: dict[str, list[dict[str, Any]]] = {
    "BOLD_ENERGY": [
        {"id": "bold-electric-red", "strategy": "drenched", "tokens": {"--bg": "#050505", "--surface": "#111111", "--fg": "#fff7ed", "--muted": "#c7bfb7", "--border": "#343434", "--accent": "#ff2b2b"}},
        {"id": "bold-acid-lime", "strategy": "committed", "tokens": {"--bg": "#070a08", "--surface": "#121a16", "--fg": "#f4fff7", "--muted": "#b8c9be", "--border": "#294137", "--accent": "#b8ff3d"}},
        {"id": "bold-safety-orange", "strategy": "drenched", "tokens": {"--bg": "#080706", "--surface": "#1a1510", "--fg": "#fff8ef", "--muted": "#d5c6b5", "--border": "#463626", "--accent": "#ff6b1a"}},
        {"id": "bold-cobalt", "strategy": "committed", "tokens": {"--bg": "#05070d", "--surface": "#10172b", "--fg": "#f5f8ff", "--muted": "#bec8e0", "--border": "#29375d", "--accent": "#4f7cff"}},
    ],
    "TRUST_ELITE": [
        {"id": "trust-navy-copper", "strategy": "restrained", "tokens": {"--bg": "#f8fafc", "--surface": "#ffffff", "--fg": "#102033", "--muted": "#526579", "--border": "#cad5df", "--accent": "#a64b2a"}},
        {"id": "trust-deep-teal", "strategy": "committed", "tokens": {"--bg": "#f4fbfa", "--surface": "#ffffff", "--fg": "#102b2a", "--muted": "#496b69", "--border": "#c2d9d6", "--accent": "#00796f"}},
        {"id": "trust-ink-gold", "strategy": "restrained", "tokens": {"--bg": "#faf9f6", "--surface": "#ffffff", "--fg": "#20242a", "--muted": "#616a73", "--border": "#d8d4ca", "--accent": "#9a6a16"}},
        {"id": "trust-plum-slate", "strategy": "committed", "tokens": {"--bg": "#fbf8fc", "--surface": "#ffffff", "--fg": "#2a1830", "--muted": "#705d75", "--border": "#ddd0df", "--accent": "#7b3f88"}},
    ],
    "ZEN_PURE": [
        {"id": "zen-mineral-teal", "strategy": "committed", "tokens": {"--bg": "#073b3a", "--surface": "#0f4f49", "--fg": "#f2fff9", "--muted": "#b8ddd3", "--border": "#3b7c72", "--accent": "#f27d64"}},
        {"id": "zen-deep-ocean", "strategy": "committed", "tokens": {"--bg": "#073444", "--surface": "#104b5b", "--fg": "#f0fbff", "--muted": "#b7dbe2", "--border": "#3b7887", "--accent": "#77d9c2"}},
        {"id": "zen-terracotta-mineral", "strategy": "drenched", "tokens": {"--bg": "#40261f", "--surface": "#5a3328", "--fg": "#fff8f3", "--muted": "#e4c8bb", "--border": "#946153", "--accent": "#5fd0b4"}},
        {"id": "zen-plum-eucalyptus", "strategy": "committed", "tokens": {"--bg": "#302844", "--surface": "#42345c", "--fg": "#fbf8ff", "--muted": "#d7cbea", "--border": "#6e5b8a", "--accent": "#88d8b8"}},
    ],
    "MODERN_TECH": [
        {"id": "tech-cyan", "strategy": "committed", "tokens": {"--bg": "#060b12", "--surface": "#0e1824", "--fg": "#f0fbff", "--muted": "#a4bdca", "--border": "#24465a", "--accent": "#28c8ee"}},
        {"id": "tech-violet", "strategy": "committed", "tokens": {"--bg": "#090711", "--surface": "#171126", "--fg": "#fbf7ff", "--muted": "#c3b4d6", "--border": "#43315f", "--accent": "#a970ff"}},
        {"id": "tech-emerald", "strategy": "drenched", "tokens": {"--bg": "#050d0b", "--surface": "#0d1d19", "--fg": "#effff9", "--muted": "#a7c7bc", "--border": "#28564a", "--accent": "#36dda4"}},
        {"id": "tech-blue", "strategy": "restrained", "tokens": {"--bg": "#f5f8ff", "--surface": "#ffffff", "--fg": "#14213d", "--muted": "#586783", "--border": "#cbd5e7", "--accent": "#3867e8"}},
    ],
    "LUXURY_ELITE": [
        {"id": "luxury-oxblood", "strategy": "drenched", "tokens": {"--bg": "#100707", "--surface": "#211010", "--fg": "#fff8f2", "--muted": "#d2bdb3", "--border": "#54302d", "--accent": "#d96a4b"}},
        {"id": "luxury-forest", "strategy": "committed", "tokens": {"--bg": "#07100d", "--surface": "#10221b", "--fg": "#f7fff9", "--muted": "#bdd0c3", "--border": "#315042", "--accent": "#c6a55b"}},
        {"id": "luxury-ink", "strategy": "restrained", "tokens": {"--bg": "#0b0b0d", "--surface": "#18181c", "--fg": "#faf8f2", "--muted": "#c8c3b9", "--border": "#3d3b3a", "--accent": "#d2b36e"}},
        {"id": "luxury-porcelain", "strategy": "restrained", "tokens": {"--bg": "#fbfaf8", "--surface": "#ffffff", "--fg": "#211f1c", "--muted": "#6e675e", "--border": "#ddd8d0", "--accent": "#80533c"}},
    ],
}


def choose_palette(archetype: str, visual_seed: str) -> dict[str, Any]:
    """Pick one curated palette and assert readable text contrast."""
    pool = PALETTES.get(archetype, PALETTES["TRUST_ELITE"])
    digest = hashlib.sha256(f"{archetype}:{visual_seed}".encode("utf-8")).hexdigest()
    palette = deepcopy(pool[int(digest[:8], 16) % len(pool)])
    palette["archetype"] = archetype
    palette["contrast"] = {
        "page": round(contrast_ratio(palette["tokens"]["--bg"], palette["tokens"]["--fg"]), 2),
        "surface": round(contrast_ratio(palette["tokens"]["--surface"], palette["tokens"]["--fg"]), 2),
        "muted_page": round(contrast_ratio(palette["tokens"]["--bg"], palette["tokens"]["--muted"]), 2),
        "muted_surface": round(contrast_ratio(palette["tokens"]["--surface"], palette["tokens"]["--muted"]), 2),
    }
    if min(palette["contrast"].values()) < 4.5:
        raise ValueError(f"Palette {palette['id']} violates WCAG text contrast")
    return palette


def contrast_ratio(background: str, foreground: str) -> float:
    lighter = max(_relative_luminance(background), _relative_luminance(foreground))
    darker = min(_relative_luminance(background), _relative_luminance(foreground))
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: str) -> float:
    raw = color.lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"Expected six-digit hex color, received {color!r}")
    channels = [int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
