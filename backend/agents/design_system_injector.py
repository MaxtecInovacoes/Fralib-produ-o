"""
Integrador entre design_systems_library e o Vite Builder.

Recebe facts (segment, subnicho, etc) e retorna o Design System Awwwards-grade
adequado. Injeta paleta + typography + motion + sections no prompt do Builder.
"""
from __future__ import annotations

from typing import Any

from backend.agents.design_systems_library import (
    DesignSystem,
    resolve_nicho,
)


def get_design_system(facts: dict[str, Any]) -> DesignSystem | None:
    """Resolve o Design System a partir dos facts do lead.

    Ordem de prioridade:
    1. facts["design_system"] (se ja foi pre-selecionado)
    2. facts["niche"] + facts["subnicho"]
    3. facts["niche"] sozinho (resolve via sinonimo)
    4. facts["segment"] sozinho (resolve via sinonimo)
    """
    if facts.get("design_system"):
        ds = facts["design_system"]
        if isinstance(ds, DesignSystem):
            return ds
    nicho = facts.get("niche", "") or ""
    subnicho = facts.get("subnicho", "") or ""
    if nicho or subnicho:
        return resolve_nicho(nicho, subnicho)
    segment = facts.get("segment", "") or ""
    if segment:
        return resolve_nicho(segment)
    return None


def build_design_system_block(ds: DesignSystem) -> str:
    """Constroi bloco de design system pra injetar no prompt."""
    p = ds.paleta
    t = ds.typography
    m = ds.motion
    s = ds.sections
    parts = [
        "DESIGN SYSTEM (curated Awwwards-grade, USE EXACTAMENTE):",
        "",
        "PALETA DE CORES (use these exact hex codes):",
        f"- primary: {p.primary}",
        f"- secondary: {p.secondary}",
        f"- accent: {p.accent}",
        f"- bg: {p.bg}",
        f"- fg: {p.fg}",
        f"- muted: {p.muted}",
        "",
        "TYPOGRAPHY:",
        f"- display font: '{t.display}' (weight {t.weight_display})",
        f"- body font: '{t.body}' (weight {t.weight_body})",
        f"- contrast: {t.contrast}",
        "",
        "MOTION:",
        f"- parallax: {m.parallax}",
        f"- reveal-on-scroll: {m.reveal_on_scroll}",
        f"- mask-reveal: {m.mask_reveal}",
        f"- cursor-effects: {m.cursor_effects}",
        f"- video-allowed: {m.video_allowed}",
        "",
        "LAYOUT/SECTIONS:",
        f"- hero type: {s.hero_type}",
        f"- has testimonials: {s.has_testimonials}",
        f"- has pricing: {s.has_pricing}",
        f"- has FAQ: {s.has_faq}",
        f"- has location map: {s.has_location_map}",
        f"- density: {s.density}",
    ]
    if ds.inspiration_refs:
        parts.append("")
        parts.append(f"INSPIRATION REFS: {', '.join(ds.inspiration_refs)}")
    return "\n".join(parts)


def inject_design_system_into_prompt(
    user_prompt: str,
    facts: dict[str, Any],
) -> str:
    """Injeta bloco de design system no user prompt se nicho reconhecido."""
    ds = get_design_system(facts)
    if not ds:
        return user_prompt
    block = build_design_system_block(ds)
    return f"{user_prompt}\n\n{block}"


def get_tailwind_tokens(ds: DesignSystem) -> dict[str, str]:
    """Retorna tokens Tailwind pre-configurados para o design system."""
    p = ds.paleta
    return {
        "color-primary": p.primary,
        "color-secondary": p.secondary,
        "color-accent": p.accent,
        "color-bg": p.bg,
        "color-fg": p.fg,
        "color-muted": p.muted,
        "font-display": ds.typography.display,
        "font-body": ds.typography.body,
    }
