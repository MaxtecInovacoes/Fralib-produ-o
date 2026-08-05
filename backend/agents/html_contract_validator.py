"""Contract validations for generated HTML (SEO, LGPD, Phase 6)."""

from __future__ import annotations

import re

from backend.domain.phase6_contract import (
    phase6_business_segment as _shared_phase6_business_segment,
    phase6_should_use_video_hero as _shared_phase6_should_use_video_hero,
)


def publication_contract_problems(html: str) -> list[str]:
    """Require SEO sharing and LGPD guards on the canonical renderer output."""
    low = (html or "").lower()
    if 'data-renderer="builder"' not in low:
        return []
    required = {
        'meta property="og:image"': "HTML publico sem og:image para compartilhamento",
        'meta property="og:url"': "HTML publico sem og:url canonica",
        'meta name="twitter:card"': "HTML publico sem twitter:card",
        'link rel="canonical"': "HTML publico sem canonical",
        "data-lgpd-banner": "HTML publico sem banner LGPD",
        "data-lgpd-accept": "HTML publico sem botao de aceite LGPD",
    }
    return [message for token, message in required.items() if token not in low]


def phase6_contract_problems(html: str) -> list[str]:
    """Phase 6/T contract validations for Builder output."""
    low = (html or "").lower()
    if 'data-renderer="builder"' not in low:
        return []
    problems: list[str] = []
    hero = re.search(r"(?is)<header\b[^>]*>", html or "")
    if not hero or not re.search(
        r'data-hero-type\s*=\s*["\'](?:video|image)["\']', hero.group(0), re.I
    ):
        problems.append("Fase 6/T1: hero sem data-hero-type")
    elif (
        'data-hero-type="video"' in hero.group(0).lower()
        and not re.search(
            r"(?is)<video\b(?=[^>]*\bautoplay\b)(?=[^>]*\bmuted\b)(?=[^>]*\bloop\b)(?=[^>]*\bplaysinline\b)",
            html or "",
        )
    ):
        problems.append("Fase 6/T1: hero video sem autoplay muted loop playsinline")
    required_any = {
        "Fase 6/T3: smooth scroll ausente": ("lenis", "fralibsmoothscroll"),
        "Fase 6/T4: magnetic ausente": ("magnetic-cta", "data-magnetic"),
        "Fase 6/T5: letter reveal ausente": ("fralib-letter-reveal",),
        "Fase 6/T6: text scramble ausente": ("fralib-text-scramble", "data-text-scramble"),
        "Fase 6/T7: grain ausente": ("fralib-grain",),
        "Fase 6/T9: backdrop blur ausente": ("backdrop-filter", "-webkit-backdrop-filter"),
        "Fase 6/T10: custom scrollbar ausente": ("::-webkit-scrollbar", "scrollbar-color"),
        "Fase 6/T11: card interativo ausente": ("fralib-card-interactive",),
    }
    for message, tokens in required_any.items():
        if not any(token in low for token in tokens):
            problems.append(message)
    required_all = {
        "Fase 6/T2: cursor custom ausente": (
            "fralib-cursor",
            "fralib-cursor-follower",
        ),
        "Fase 6/T8: reading progress ausente": (
            "fralib-reading-progress",
            'role="progressbar"',
        ),
        "Fase 6/T12: a11y incompleto": (
            "fralib-skip-link",
            'href="#main"',
            "focus-visible",
            '<main id="main">',
        ),
        "Fase 6/T13: SEO avancado incompleto": (
            "breadcrumblist",
            'property="og:image:width"',
            'content="1200"',
            'property="og:image:height"',
            'content="630"',
        ),
        "Fase 6/T14: performance fonts incompleta": (
            "fonts.gstatic.com",
            "display=swap",
        ),
        "Fase 6/T15: theme toggle ausente": (
            "fralib-theme-toggle",
            'aria-label="alternar tema"',
            "data-theme=",
            '[data-theme="dark"]',
        ),
        "Fase 6/T16: GSAP/Lenis ausente": (
            "cdn.jsdelivr.net/npm/gsap",
            "cdn.jsdelivr.net/npm/lenis",
            "gsap.registerplugin",
        ),
    }
    for message, tokens in required_all.items():
        if any(token not in low for token in tokens):
            problems.append(message)
    if (
        hero
        and 'data-hero-type="video"' in hero.group(0).lower()
        and "https://videos.pexels.com" not in low
    ):
        problems.append("Fase 6/T14: hero video sem preconnect Pexels")
    return problems


def visual_contract_problems(html: str, prd) -> list[str]:
    """Validate visual contract requirements via external gate."""
    if not _get_field(prd, "visual_contract", default={}):
        return []
    try:
        try:
            from agents.visual_contract_gate import audit_visual_contract
        except Exception:
            from visual_contract_gate import audit_visual_contract

        return audit_visual_contract(html, prd).problems
    except Exception as exc:
        return [f"visual_contract: erro ao auditar contrato visual ({exc})"]


def _get_field(obj, *names, default=None):
    """Get value from dict or object attribute, trying multiple field names."""
    if isinstance(obj, dict):
        for name in names:
            value = obj.get(name)
            if value not in (None, "", [], {}):
                return value
        return default
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _phase6_business_segment(prd) -> str:
    """Delegate to shared phase6 module."""
    return _shared_phase6_business_segment(prd)


def _phase6_should_use_video_hero(prd) -> bool:
    """Delegate to shared phase6 module."""
    return _shared_phase6_should_use_video_hero(prd, require_video_asset=True)
