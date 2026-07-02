"""
============================================================================
POLO PROMPTS — Bloco de injeção de polo para system prompts LLM
============================================================================

Sprint 12.x: injeta o polo escolhido (SOFT | BOLD | CLASSIC | TECH) dentro
dos prompts do pipeline (bloco_estrutura, bloco_copy, build_design_dna,
system prompts). O polo vem do nicho_registry (fonte única de verdade).

O bloco gerado contém:
1. POLO canonical (string maiúscula)
2. Tokens estruturais (radius, spacing, motion, typography)
3. CopyDefaults (tone, voice, cta_primary)
4. DesignLogic (radius_multiplier, spacing_multiplier, allow_overlap, etc.)
5. Sub-nicho override (se houver, ex: nutricionista + atleta -> BOLD)

Cada um dos 4 system prompts do pipeline consome esse helper para garantir
que o LLM esteja olhando para o mesmo polo.

Uso:
    from polo_prompts import build_polo_prompt_block
    block = build_polo_prompt_block("nutricionista", subnicho="atleta")
    # 'POLO: BOLD\n...'
============================================================================
"""

from __future__ import annotations

from typing import Any


# Tokens estruturais por polo — espelha design-system-tokens.css
_POLO_TOKENS: dict[str, dict[str, str]] = {
    "SOFT": {
        "radius": "40-50px",
        "heading_font": "Playfair Display / serif",
        "heading_case": "capitalize",
        "heading_style": "normal",
        "spacing": "relaxed (py-32, gap-12)",
        "shadow": "diffuse, colored",
        "motion": "slow (600ms+), ease suave",
        "overlap": "none",
        "skew": "0deg",
        "text_stroke": "no",
    },
    "BOLD": {
        "radius": "0px",
        "heading_font": "Anton / display condensado",
        "heading_case": "uppercase",
        "heading_style": "italic",
        "spacing": "tight (py-4, gap-2)",
        "shadow": "harsh offset (8px 8px 0)",
        "motion": "fast (100-200ms), spring",
        "overlap": "-80px",
        "skew": "-5deg",
        "text_stroke": "yes (2px primary)",
    },
    "CLASSIC": {
        "radius": "6px",
        "heading_font": "Inter / sans-serif sóbria",
        "heading_case": "capitalize",
        "heading_style": "normal",
        "spacing": "standard (py-16, gap-8)",
        "shadow": "subtle, monochrome",
        "motion": "medium (300ms), fade",
        "overlap": "0px",
        "skew": "0deg",
        "text_stroke": "no",
    },
    "TECH": {
        "radius": "12px",
        "heading_font": "Space Grotesk / mono geométrica",
        "heading_case": "lowercase",
        "heading_style": "normal",
        "spacing": "precise (py-20, gap-6)",
        "shadow": "neon glow",
        "motion": "scroll-based, parallax",
        "overlap": "-40px",
        "skew": "2deg",
        "text_stroke": "no",
    },
}


_POLO_LABELS: dict[str, str] = {
    "SOFT": "Orgânico / Acolhedor (nutrição, estética, pet)",
    "BOLD": "Agressivo / Impacto (academia, oficina, eventos)",
    "CLASSIC": "Sério / Seguro (advogado, clínica, contábil)",
    "TECH": "Moderno / Limpo (startups, energia solar, design)",
}


def _resolve_polo(nicho: str | None, subnicho: str | None = None) -> str:
    """Resolve o polo via nicho_registry (com fallback)."""
    try:
        from backend.config.nicho_registry import resolve_polo_for_lead
        polo = resolve_polo_for_lead(nicho or "", subnicho=subnicho or "")
        return (polo or "CLASSIC").upper()
    except Exception:
        return "CLASSIC"


def _copy_defaults(nicho: str | None) -> tuple[str, str, str]:
    """Retorna (tone, voice, cta_primary) do nicho_registry."""
    try:
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config(nicho)
        cp = cfg.copy_defaults
        return cp.tone, cp.voice, cp.cta_primary
    except Exception:
        return "profissional, neutro", "2a pessoa do singular", "Falar no WhatsApp"


def _design_logic_str(nicho: str | None) -> str:
    """Serializa DesignLogic em string legível."""
    try:
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic(nicho)
        return (
            f"radius_multiplier={dl.radius_multiplier}, "
            f"spacing_multiplier={dl.spacing_multiplier}, "
            f"allow_overlap={dl.allow_overlap}, "
            f"allow_skew={dl.allow_skew}, "
            f"allow_text_stroke={dl.allow_text_stroke}, "
            f"image_treatment={dl.image_treatment}, "
            f"gallery_density={dl.gallery_density}"
        )
    except Exception:
        return "radius_multiplier=1.0, spacing_multiplier=1.0, allow_overlap=False"


def _format_tokens_table(tokens: dict[str, str]) -> str:
    """Formata dict de tokens em linhas 'chave: valor'."""
    return "\n".join(f"  - {k}: {v}" for k, v in tokens.items())


def build_polo_prompt_block(
    nicho: str | None,
    subnicho: str | None = None,
    *,
    include_copy: bool = True,
    include_design_logic: bool = True,
    extra: dict[str, Any] | None = None,
) -> str:
    """Monta bloco de polo para injetar em prompts LLM.

    Args:
        nicho: Nome do nicho (segmento). Aceita aliases via nicho_registry.
        subnicho: Sub-nicho opcional (ex: "atleta", "infantil", "yoga").
        include_copy: Se True, inclui bloco CopyDefaults (tone/voice/cta).
        include_design_logic: Se True, inclui bloco DesignLogic.
        extra: Dict opcional com campos extras a serem injetados.

    Returns:
        String formatada pronta para concatenar em prompt LLM.
        Começa com '=== POLO ===' e termina com '=== FIM POLO ==='.
    """
    polo = _resolve_polo(nicho, subnicho)
    tokens = _POLO_TOKENS.get(polo, _POLO_TOKENS["CLASSIC"])
    polo_label = _POLO_LABELS.get(polo, polo)

    sections: list[str] = []
    sections.append("=== POLO ESTÉTICO (sigam RIGOROSAMENTE) ===")
    sections.append(f"POLO: {polo} ({polo_label})")
    sections.append("Nicho: " + (nicho or "default"))
    if subnicho:
        sections.append(f"Sub-nicho: {subnicho}")
    sections.append("")
    sections.append("Tokens estruturais:")
    sections.append(_format_tokens_table(tokens))
    sections.append("")

    if include_copy:
        tone, voice, cta = _copy_defaults(nicho)
        sections.append("Copy defaults:")
        sections.append(f"  - tone: {tone}")
        sections.append(f"  - voice: {voice}")
        sections.append(f"  - cta_primary: {cta}")
        sections.append("")

    if include_design_logic:
        sections.append("DesignLogic (DNA estrutural):")
        sections.append(f"  {_design_logic_str(nicho)}")
        sections.append("")

    if extra:
        for key, value in extra.items():
            sections.append(f"{key}: {value}")
        sections.append("")

    sections.append(
        f"REGRA: se voce ver instrucoes conflitantes, o POLO '{polo}' vence. "
        f"Respeite radius, font, motion e spacing acima mesmo que o nicho sugira outro."
    )
    sections.append("=== FIM POLO ===")
    return "\n".join(sections)


def build_polo_short(nicho: str | None, subnicho: str | None = None) -> str:
    """Versão compacta do bloco de polo (1 linha) para system prompts."""
    polo = _resolve_polo(nicho, subnicho)
    return f"POLO={polo} (nicho={nicho or 'default'}, subnicho={subnicho or '-'})"


__all__ = [
    "build_polo_prompt_block",
    "build_polo_short",
]