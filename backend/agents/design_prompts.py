"""design_prompts.py — Geração de prompts LLM a partir do Design System por Nicho.

Este módulo fornece funções para formatar o contexto de design em prompts
legíveis por modelos de linguagem, extraindo a lógica de formatação do
design_context.py.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from design_context import get_design_context


def get_design_context_prompt(
    segmento: str,
    nome_negocio: str = "",
    tier: str = "STANDARD",
    dark_mode: bool = False,
    od_slug: str = "",
) -> str:
    """Gera um prompt formatado com o Design System do nicho para injeção em prompts LLM.

    Args:
        segmento: Segmento/nicho do negócio (ex: "restaurante", "clinica").
        nome_negocio: Nome fantasia do negócio.
        tier: Nível de sofisticação visual (STANDARD, PREMIUM, etc).
        dark_mode: Se True, aplica variant dark mode.
        od_slug: Slug da direção visual do Open Design.

    Returns:
        String formatada com o Design System completo para uso em prompts LLM.
    """
    # Lazy import para evitar dependência circular
    from design_context import get_design_context as _get_design_context

    ctx = _get_design_context(segmento, nome_negocio, tier, dark_mode, od_slug=od_slug)
    tokens_str = "\n".join(f"  {k}: {v}" for k, v in ctx["tokens"].items())
    anim = ctx["animation_profile"]
    _posture = ctx.get("posture", [])
    posture_fmt = "\n".join("  - " + p for p in _posture) if _posture else "  padrao"

    # Sprint 12.x: injeta polo canônico (vem do nicho_registry)
    try:
        from polo_prompts import build_polo_short
        _polo_short = build_polo_short(segmento, subnicho="")
    except Exception:
        _polo_short = f"POLO=CLASSIC (nicho={segmento or 'default'})"

    result = f"""
=== DESIGN SYSTEM DO NICHO — SIGA OBRIGATORIAMENTE ===
SEGMENTO: {ctx['segmento'].upper()} | TIER: {ctx['tier']} | DIREÇÃO: {ctx['dir_nome']}
{_polo_short}

CSS TOKENS (6 universais — use EXATAMENTE estes valores no :root):
{tokens_str}

TIPOGRAFIA:
  heading: {ctx['font_heading']}
  body:    {ctx['font_body']}

VIBE: {ctx['vibe']}

PERFIL DE ANIMAÇÃO: {ctx['animation']}
  enter:      {anim['enter']} | feedback: {anim['feedback']}
  easing_std: {anim['easing_std']}
  hero_type:  {anim['hero_type']} | card_type: {anim['card_type']}
  stagger:    {anim['stagger']}
  OBRIGATÓRIO: @media (prefers-reduced-motion: reduce) substitui translate/scale por opacity

COMPONENTES OBRIGATÓRIOS:
  {ctx['components']}

TOM DE VOZ: {ctx['tom']}

SEO LOCAL: {ctx['seo']}

ANTI-PATTERNS (proibido neste nicho):
  {ctx['anti']}

POSTURA VISUAL (cues de layout):
{posture_fmt}
=== FIM DESIGN SYSTEM ===
"""
    return result
