"""template_loader.py — Carrega e renderiza templates esteticos FraLib.

Este modulo faz a ponte entre:
    - 6 templates HTML estaticos em backend/templates/{estetica}/index.html
    - Sistema de variacao 4-eixos (variation.py) que gera tema/tipografia/layout/motion
    - Contexto do lead (facts) para substituir placeholders {{BUSINESS_NAME}} etc

Tres responsabilidades principais:
    1. load_template(estetica) -> str
       Le o HTML canonico da estetica (BOLD_ENERGY, EDITORIAL, ...).

    2. render_with_variation(template_html, lead_context, variation) -> str
       Substitui placeholders, injeta CSS variables inline (4-eixos), carrega
       motion_runtime.js FraLib + tokens.css + themes.css no <head>.

    3. validate_template_output(html) -> dict
       Sanity-check: tem <html>, <body>, nenhum {{PLACEHOLDER}} nao substituido.

USO NO BUILDER:
    from backend.services.template_loader import (
        load_template, render_with_variation, validate_template_output,
    )
    html = load_template("BOLD_ENERGY")
    final = render_with_variation(html, facts, variation)
    report = validate_template_output(final)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# PATH RESOLUTION
# ============================================================================

# backend/services/template_loader.py -> backend/services/ -> backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATES_ROOT = _BACKEND_ROOT / "templates"
_SYSTEM_DIR = _TEMPLATES_ROOT / "_system"
_MOTION_RUNTIME_PATH = Path(__file__).resolve().parent / "motion_runtime.js"

_ESTETICA_TO_DIR = {
    "BOLD_ENERGY": "bold_energy",
    "EDITORIAL": "editorial",
    "MINIMAL": "minimal",
    "KINETIC": "kinetic",
    "SCROLL": "scroll",
    "IMMERSIVE_3D": "immersive_3d",
}


# ============================================================================
# PLACEHOLDER MAP: {{TOKEN}} -> facts[...].get(...)
# ----------------------------------------------------------------------------
# O contexto do lead (facts) vem do agent_prompt_agent_payload (builder_worker).
# Estrutura esperada:
#   facts = {
#       "business": {"name", "tagline", "city", "address", "phone", ...},
#       "description": "...",   # ABOUT_TEXT
#       "instagram_handle": "...",
#       ...
#   }
#
# Templates usam:
#   {{BUSINESS_NAME}}, {{BUSINESS_NAME_INITIAL}}, {{BUSINESS_HANDLE}}
#   {{TAGLINE}}, {{HERO_TITLE}}, {{HERO_SUBTITLE}}
#   {{CITY}}, {{ADDRESS}}, {{PHONE}}, {{EMAIL}}, {{INSTAGRAM_HANDLE}}
#   {{ABOUT_TEXT}}, {{PRIMARY_COLOR}}, {{MOTION_LEVEL}}
#
# Servicos/FAQ/Testimonials: aqueles placeholders mais raros ({{SERVICE_1_TITLE}},
# {{FAQ_1_ANSWER}}, etc.) sao resolvidos via facts.get("sections") / facts.get("faq")
# quando o Nicho agent popula. Quando ausentes, recebem default seguro (sem quebrar).
# ============================================================================

def _resolve_placeholder(token: str, facts: dict[str, Any]) -> str:
    """Resolve 1 placeholder {{TOKEN}} -> string substituivel.

    Ordem de busca:
        1. facts["business"][key] para chaves canonicas
        2. facts[key] raiz
        3. facts["sections"][...] para SERVICE_*, FAQ_*, TESTIMONIAL_*
        4. default seguro (string vazia ou valor derivado)
    """
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    sections = facts.get("sections") if isinstance(facts.get("sections"), dict) else {}
    faq_items = facts.get("faq") if isinstance(facts.get("faq"), list) else []
    testimonials = facts.get("testimonials") if isinstance(facts.get("testimonials"), list) else []
    services = sections.get("services") if isinstance(sections.get("services"), list) else []
    name = str(business.get("name") or facts.get("business_name") or "").strip()
    initial = name[:1].upper() if name else "F"
    handle = (name or "fralib").lower().replace(" ", "")

    defaults: dict[str, str] = {
        "BUSINESS_NAME": name or "Franquia",
        "BUSINESS_NAME_INITIAL": initial,
        "BUSINESS_HANDLE": handle,
        "TAGLINE": str(business.get("tagline") or business.get("slogan") or "").strip(),
        "HERO_TITLE": str(business.get("hero_title") or name or "Seu negocio, sua marca").strip(),
        "HERO_SUBTITLE": str(
            business.get("description") or facts.get("description") or ""
        ).strip()[:240],
        "ABOUT_TEXT": str(
            business.get("about") or business.get("description") or facts.get("description") or ""
        ).strip(),
        "CITY": str(business.get("city") or facts.get("city") or "").strip(),
        "ADDRESS": str(business.get("address") or facts.get("address") or "").strip(),
        "PHONE": str(business.get("phone") or business.get("whatsapp") or "").strip(),
        "EMAIL": str(business.get("email") or "").strip(),
        "INSTAGRAM_HANDLE": str(
            business.get("instagram") or facts.get("instagram_handle") or handle
        ).lstrip("@").strip(),
        "PRIMARY_COLOR": str(business.get("primary_color") or "ff5722").lstrip("#").strip(),
        "MOTION_LEVEL": str(facts.get("motion_level") or "medium").strip(),
    }

    # Servicos 1..3 (titles + descs)
    for idx in (1, 2, 3):
        svc = services[idx - 1] if idx - 1 < len(services) and isinstance(services[idx - 1], dict) else {}
        defaults[f"SERVICE_{idx}_TITLE"] = str(svc.get("title") or f"Servico {idx}").strip()
        defaults[f"SERVICE_{idx}_DESC"] = str(svc.get("description") or "").strip()[:200]

    # FAQ 1..4
    for idx in (1, 2, 3, 4):
        item = faq_items[idx - 1] if idx - 1 < len(faq_items) and isinstance(faq_items[idx - 1], dict) else {}
        defaults[f"FAQ_{idx}_ANSWER"] = str(item.get("answer") or item.get("a") or "").strip()

    # Testimonials 1..2
    for idx in (1, 2):
        t = testimonials[idx - 1] if idx - 1 < len(testimonials) and isinstance(testimonials[idx - 1], dict) else {}
        t_name = str(t.get("name") or "").strip()
        defaults[f"TESTIMONIAL_{idx}_QUOTE"] = str(t.get("quote") or t.get("text") or "").strip()
        defaults[f"TESTIMONIAL_{idx}_NAME"] = t_name
        defaults[f"TESTIMONIAL_{idx}_ROLE"] = str(t.get("role") or "").strip()
        defaults[f"TESTIMONIAL_{idx}_INITIAL"] = t_name[:1].upper() if t_name else ""

    # HERO_TITLE_LINE_1 / LINE_2 — defaults a partir do HERO_TITLE
    hero = defaults["HERO_TITLE"]
    if "|" in hero:
        parts = [p.strip() for p in hero.split("|", 1)]
    elif " - " in hero:
        parts = [p.strip() for p in hero.split(" - ", 1)]
    else:
        parts = [hero, ""]
    defaults["HERO_TITLE_LINE_1"] = parts[0] if parts else ""
    defaults["HERO_TITLE_LINE_2"] = parts[1] if len(parts) > 1 else ""

    return defaults.get(token, "")


# ============================================================================
# 1. LOAD TEMPLATE
# ============================================================================

def load_template(estetica: str) -> str:
    """Le o HTML canonico da estetica.

    Args:
        estetica: chave canonica (BOLD_ENERGY, EDITORIAL, MINIMAL, KINETIC,
                  SCROLL, IMMERSIVE_3D). Case-insensitive.

    Returns:
        Conteudo HTML completo do template (com placeholders {{TOKEN}} intactos).

    Raises:
        FileNotFoundError: se a pasta/arquivo da estetica nao existir.
        ValueError: se a estetica nao for uma chave valida.
    """
    if not estetica:
        raise ValueError("estetica vazia")
    canonical = estetica.strip().upper()
    folder = _ESTETICA_TO_DIR.get(canonical)
    if not folder:
        raise ValueError(
            f"estetica invalida: {estetica!r}. "
            f"Validas: {sorted(_ESTETICA_TO_DIR.keys())}"
        )
    template_path = _TEMPLATES_ROOT / folder / "index.html"
    if not template_path.exists():
        raise FileNotFoundError(
            f"template nao encontrado para estetica {canonical}: {template_path}"
        )
    html = template_path.read_text(encoding="utf-8")
    logger.info(
        "[template_loader] loaded estetica=%s path=%s chars=%d",
        canonical,
        template_path.name,
        len(html),
    )
    return html


# ============================================================================
# 2. RENDER WITH VARIATION
# ============================================================================

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def _substitute_placeholders(html: str, facts: dict[str, Any]) -> tuple[str, list[str]]:
    """Substitui todos os {{TOKEN}} por valores de facts.

    Returns:
        (html_substituido, lista_tokens_nao_resolvidos)

    Estrategia defensiva: qualquer placeholder nao resolvido vira string vazia
    (NAO levanta erro) para que o site nunca quebre por falta de dado. A lista
    retornada permite ao caller logar/alertar sobre lacunas.
    """
    business_name = (facts.get("business") or {}).get("name") if isinstance(facts.get("business"), dict) else None
    if not business_name:
        business_name = facts.get("business_name")
    unresolved: list[str] = []

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        try:
            value = _resolve_placeholder(token, facts)
        except Exception as exc:  # pragma: no cover - defensiva
            logger.warning("[template_loader] falha resolvendo %s: %s", token, exc)
            value = ""
        if not value and token != "MOTION_LEVEL":
            unresolved.append(token)
        return _html_escape(value)

    rendered = _PLACEHOLDER_RE.sub(repl, html)
    # Dedup para logs
    unresolved_sorted = sorted(set(unresolved))
    if unresolved_sorted:
        logger.info(
            "[template_loader] placeholders sem dados (defaults aplicados): %s (lead=%s)",
            unresolved_sorted[:15],
            business_name or "?",
        )
    return rendered, unresolved_sorted


def _html_escape(value: str) -> str:
    """Escape minimalista para valor de atributo/texto."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _read_asset(path: Path, *, label: str) -> str:
    """Le arquivo com fallback graceful (retorna string vazia se nao existir)."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("[template_loader] asset ausente: %s path=%s", label, path)
        return ""
    except Exception as exc:  # pragma: no cover - defensiva
        logger.warning("[template_loader] falha lendo %s: %s", label, exc)
        return ""


def _inject_into_head(html: str, *, snippets: list[str]) -> str:
    """Insere uma lista de snippets antes de </head>.

    Se </head> nao existir, tenta <body>; senao prepende.
    Idempotente se o caller ja checar (nao duplica blocos com mesmo id).
    """
    if not snippets:
        return html
    block = "\n".join(snippets) + "\n"
    if "</head>" in html:
        return html.replace("</head>", block + "</head>", 1)
    if "<body" in html:
        return re.sub(r"(<body[^>]*>)", r"\1\n" + block, html, count=1, flags=re.IGNORECASE)
    return block + html


def _inject_into_body(html: str, *, snippets: list[str]) -> str:
    """Insere uma lista de snippets antes de </body>.

    Fallback: antes de </head>; senao concatena.
    """
    if not snippets:
        return html
    block = "\n".join(snippets) + "\n"
    if "</body>" in html:
        return html.replace("</body>", block + "</body>", 1)
    if "</head>" in html:
        return html.replace("</head>", block + "</head>", 1)
    return html + block


def _ensure_data_motion_attr(html: str, motion_level: str) -> str:
    """Garante data-motion no <html> ou <body> para os overrides do template."""
    level = (motion_level or "medium").strip().lower()
    if level not in {"subtle", "medium", "cinematic"}:
        level = "medium"
    if 'data-motion="' in html:
        return re.sub(
            r'data-motion="[^"]*"',
            f'data-motion="{level}"',
            html,
            count=1,
        )
    # Adiciona no <html> (primeira ocorrencia)
    return re.sub(
        r"<html\b",
        f'<html data-motion="{level}"',
        html,
        count=1,
        flags=re.IGNORECASE,
    )


def _ensure_engine_marker(html: str) -> str:
    """Marca o HTML com data-renderer + data-builder-engine para QA."""
    if 'data-renderer="builder"' in html:
        return html
    return re.sub(
        r"<html\b",
        '<html data-renderer="builder" data-builder-engine="openui_template"',
        html,
        count=1,
        flags=re.IGNORECASE,
    )


def render_with_variation(
    template_html: str,
    lead_context: dict[str, Any],
    variation: dict[str, Any],
) -> str:
    """Aplica placeholders + injeta CSS variables + motion runtime + tokens/temas.

    Args:
        template_html: HTML cru do template (com {{TOKEN}}).
        lead_context: facts do lead ({"business": {...}, ...}).
        variation: dict retornado por variation.generate_variation() com chaves
                   estetica/theme/typography/layout/motion/css_vars_inline.

    Returns:
        HTML pronto para publicar (estatico, com motion runtime inline).
    """
    if not template_html:
        raise ValueError("template_html vazio")
    if not isinstance(variation, dict):
        raise ValueError("variation precisa ser dict")

    # 1) Substituir placeholders {{TOKEN}} -> dados do lead
    html, unresolved = _substitute_placeholders(template_html, lead_context or {})

    # 2) Engine marker (QA gate usa para distinguir template vs LLM)
    html = _ensure_engine_marker(html)

    # 3) data-motion="<level>" no <html> para overrides CSS por nivel
    motion_level = str(variation.get("motion") or "medium").strip().lower()
    html = _ensure_data_motion_attr(html, motion_level)

    # 4) CSS variables inline (variation.py ja gera o bloco <style>)
    css_vars_inline = variation.get("css_vars_inline") or ""
    head_snippets: list[str] = []
    if css_vars_inline:
        head_snippets.append(css_vars_inline)

    # 5) Carregar tokens.css + themes.css (system) — leve, mas completo
    tokens_css = _read_asset(_SYSTEM_DIR / "tokens.css", label="tokens.css")
    themes_css = _read_asset(_SYSTEM_DIR / "themes.css", label="themes.css")
    if tokens_css:
        head_snippets.append('<style id="fralib-tokens">\n' + tokens_css + "\n</style>")
    if themes_css:
        head_snippets.append('<style id="fralib-themes">\n' + themes_css + "\n</style>")

    # 6) Injeta <style data-theme="..."> no head para o variation.theme
    theme_name = str(variation.get("theme") or "").strip()
    if theme_name:
        head_snippets.append(
            f'<style id="fralib-theme-active">:root {{ --fralib-active-theme: {theme_name}; }}</style>'
        )

    html = _inject_into_head(html, snippets=head_snippets)

    # 7) Injeta motion_runtime.js FraLib (inline) antes de </body>
    motion_js = _read_asset(_MOTION_RUNTIME_PATH, label="motion_runtime.js")
    body_snippets: list[str] = []
    if motion_js and "fralib-motion-runtime" not in html:
        body_snippets.append(
            '<script id="fralib-motion-runtime">\n' + motion_js + "\n</script>"
        )
    html = _inject_into_body(html, snippets=body_snippets)

    logger.info(
        "[template_loader] rendered estetica=%s theme=%s motion=%s unresolved=%d chars=%d",
        variation.get("estetica"),
        variation.get("theme"),
        variation.get("motion"),
        len(unresolved),
        len(html),
    )
    return html


# ============================================================================
# 3. VALIDATE TEMPLATE OUTPUT
# ============================================================================

def validate_template_output(html: str) -> dict[str, Any]:
    """Sanity-check do HTML renderizado.

    Returns:
        dict com chaves:
            ok: bool (True se passou todos os checks)
            has_doctype: bool
            has_html: bool
            has_body: bool
            has_motion_runtime: bool
            has_css_vars: bool
            has_theme_attr: bool
            unresolved_placeholders: list[str]
            char_count: int
            errors: list[str]
    """
    errors: list[str] = []
    if not html or not html.strip():
        return {
            "ok": False,
            "has_doctype": False,
            "has_html": False,
            "has_body": False,
            "has_motion_runtime": False,
            "has_css_vars": False,
            "has_theme_attr": False,
            "unresolved_placeholders": [],
            "char_count": 0,
            "errors": ["html vazio"],
        }

    low = html.lower()
    has_doctype = bool(re.search(r"<!doctype\b", low))
    has_html = "<html" in low and "</html>" in low
    has_body = "<body" in low and "</body>" in low
    has_motion = "fralib-motion-runtime" in html
    has_css_vars = bool(re.search(r"--fralib-theme|--fralib-typography|--fralib-layout", html))
    has_theme_attr = bool(re.search(r'data-motion=|--fralib-active-theme', html))

    unresolved = _PLACEHOLDER_RE.findall(html)

    if not has_doctype:
        errors.append("falta <!doctype html>")
    if not has_html:
        errors.append("falta tag <html>...</html>")
    if not has_body:
        errors.append("falta tag <body>...</body>")
    if not has_motion:
        errors.append("motion_runtime.js FraLib nao foi injetado")
    if not has_css_vars:
        errors.append("CSS variables de variacao nao foram injetadas")
    if unresolved:
        errors.append(f"placeholders nao substituidos: {sorted(set(unresolved))[:10]}")

    if len(html) < 5000:
        errors.append(f"HTML curto demais ({len(html)} chars) - possivel template vazio")

    return {
        "ok": not errors,
        "has_doctype": has_doctype,
        "has_html": has_html,
        "has_body": has_body,
        "has_motion_runtime": has_motion,
        "has_css_vars": has_css_vars,
        "has_theme_attr": has_theme_attr,
        "unresolved_placeholders": sorted(set(unresolved)),
        "char_count": len(html),
        "errors": errors,
    }


# ============================================================================
# ERROS
# ============================================================================

class TemplateLoaderError(RuntimeError):
    """Levantada quando template_loader falha de forma nao-recuperavel."""


__all__ = [
    "load_template",
    "render_with_variation",
    "validate_template_output",
    "TemplateLoaderError",
]