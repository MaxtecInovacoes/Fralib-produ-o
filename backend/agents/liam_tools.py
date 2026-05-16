"""
Liam Agent Tools — Ferramentas de validação para o Liam Managed Agent.

Após gerar cada seção HTML (Opus), o agent loop valida com estas tools
e corrige problemas antes de passar para a próxima seção.
"""
import json
import re
from typing import Dict, List


# ══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ══════════════════════════════════════════════════════════════════

LIAM_TOOLS = [
    {
        "name": "validate_html",
        "description": "Valida HTML da seção: tags fechadas, atributos corretos, sem DOCTYPE/html/head/body, section com id. Retorna issues encontrados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "HTML da seção para validar"},
                "section_name": {"type": "string", "description": "Nome da seção (hero, sobre, etc)"}
            },
            "required": ["html", "section_name"]
        }
    },
    {
        "name": "check_design_tokens",
        "description": "Verifica se o HTML usa APENAS CSS vars permitidas (--bg, --fg, --accent, --surface, --muted, --border) e não tem cores hardcoded proibidas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "HTML da seção"}
            },
            "required": ["html"]
        }
    },
    {
        "name": "check_seo_score",
        "description": "Verifica SEO da seção: keywords nos headings, alt em imagens, hierarquia de headings correta, links com texto descritivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "HTML da seção"},
                "section_name": {"type": "string", "description": "Nome da seção"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords que devem aparecer"}
            },
            "required": ["html", "section_name"]
        }
    },
    {
        "name": "check_accessibility",
        "description": "Verifica acessibilidade: alt em imgs, aria-labels em botões, contraste mínimo, roles semânticos, focus states.",
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "HTML da seção"}
            },
            "required": ["html"]
        }
    },
    {
        "name": "check_animations",
        "description": "Verifica se animações obrigatórias estão aplicadas: .reveal, .scale-in, .stagger-item, data-parallax, .pulse-cta.",
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "HTML da seção"},
                "section_name": {"type": "string", "description": "Nome da seção"}
            },
            "required": ["html", "section_name"]
        }
    },
]


# ══════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ══════════════════════════════════════════════════════════════════

def execute_tool(tool_name: str, tool_input: dict, context: dict = None) -> str:
    try:
        if tool_name == "validate_html":
            return _tool_validate_html(tool_input)
        elif tool_name == "check_design_tokens":
            return _tool_check_design_tokens(tool_input)
        elif tool_name == "check_seo_score":
            return _tool_check_seo_score(tool_input)
        elif tool_name == "check_accessibility":
            return _tool_check_accessibility(tool_input)
        elif tool_name == "check_animations":
            return _tool_check_animations(tool_input)
        else:
            return json.dumps({"error": f"Tool desconhecida: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── validate_html ─────────────────────────────────────────────────

def _tool_validate_html(tool_input: dict) -> str:
    html = tool_input.get("html", "")
    section_name = tool_input.get("section_name", "")
    issues = []

    # Must start with <section
    stripped = html.strip()
    if not stripped.lower().startswith("<section"):
        issues.append("HTML não começa com <section>. Deve iniciar com <section id=...")

    # Must end with </section>
    if not stripped.lower().rstrip().endswith("</section>"):
        issues.append("HTML não termina com </section>. Tag não fechada.")

    # No DOCTYPE, html, head, body
    forbidden = ["<!doctype", "<html", "</html>", "<head", "</head>", "<body", "</body>"]
    for f in forbidden:
        if f in html.lower():
            issues.append(f"Tag proibida encontrada: {f}")

    # Section must have id
    if not re.search(r'<section[^>]+id=', html, re.IGNORECASE):
        issues.append(f"Section sem id. Deve ter id=\"{section_name}\"")

    # Check unclosed tags (basic)
    open_tags = re.findall(r'<(div|span|p|ul|ol|li|a|button|form|nav|article|aside|main|figure|figcaption)\b', html, re.IGNORECASE)
    close_tags = re.findall(r'</(div|span|p|ul|ol|li|a|button|form|nav|article|aside|main|figure|figcaption)>', html, re.IGNORECASE)
    open_count = len(open_tags)
    close_count = len(close_tags)
    if open_count - close_count > 3:
        issues.append(f"Possíveis tags não fechadas: {open_count} abertas vs {close_count} fechadas (diff={open_count-close_count})")

    # No empty href="#"
    empty_hrefs = len(re.findall(r'href=["\']#["\']', html))
    if empty_hrefs > 0:
        issues.append(f"{empty_hrefs} links com href='#' vazio. Todos devem ter URL real (WhatsApp, Maps, tel:).")

    # Check markdown artifacts
    if "```" in html:
        issues.append("Contém artifacts de markdown (```). Deve ser HTML puro.")

    ok = len(issues) == 0
    return json.dumps({"ok": ok, "issues": issues, "html_length": len(html)}, ensure_ascii=False)


# ── check_design_tokens ───────────────────────────────────────────

def _tool_check_design_tokens(tool_input: dict) -> str:
    html = tool_input.get("html", "")
    issues = []
    warnings = []

    # Forbidden hardcoded colors in text
    slop_colors = ["#6366f1", "#4f46e5", "#4338ca", "#8b5cf6", "#7c3aed"]
    for color in slop_colors:
        if color in html.lower():
            issues.append(f"Cor AI-slop detectada: {color}. Use var(--accent) em vez disso.")

    # Check for hardcoded hex in color/background-color (not in img src or url())
    hex_in_style = re.findall(r'(?:color|background(?:-color)?)\s*:\s*(#[0-9a-fA-F]{3,8})', html)
    allowed_hex = ["#000", "#000000", "#fff", "#ffffff"]  # permitidos em contextos específicos
    bad_hex = [h for h in hex_in_style if h.lower() not in allowed_hex]
    if len(bad_hex) > 3:
        warnings.append(f"{len(bad_hex)} cores hex hardcoded encontradas. Preferir var(--bg/--fg/--accent/--surface/--muted/--border).")

    # Check for forbidden var names
    forbidden_vars = ["var(--color-primary)", "var(--color-background)", "var(--color-accent)", "var(--color-text)"]
    for fv in forbidden_vars:
        if fv in html:
            issues.append(f"Var proibida: {fv}. Use var(--bg), var(--fg), var(--accent), var(--surface).")

    # Check text-white usage (should use var(--fg))
    text_white_count = len(re.findall(r'\btext-white\b', html))
    if text_white_count > 5:
        warnings.append(f"text-white usado {text_white_count}x. Preferir style com var(--fg) para compatibilidade light/dark.")

    # Accent overuse
    accent_count = len(re.findall(r'var\(--accent\)', html))
    if accent_count > 6:
        issues.append(f"var(--accent) usado {accent_count}x. Máximo 2 por tela visível (regra craft).")

    ok = len(issues) == 0
    return json.dumps({"ok": ok, "issues": issues, "warnings": warnings}, ensure_ascii=False)


# ── check_seo_score ───────────────────────────────────────────────

def _tool_check_seo_score(tool_input: dict) -> str:
    html = tool_input.get("html", "")
    section_name = tool_input.get("section_name", "")
    keywords = tool_input.get("keywords", [])
    issues = []
    score = 100

    # Hero must have H1
    if section_name == "hero":
        if not re.search(r'<h1\b', html, re.IGNORECASE):
            issues.append("Hero sem H1. Obrigatório para SEO.")
            score -= 30
        else:
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
            if h1_match:
                h1_text = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
                if len(h1_text.split()) < 5:
                    issues.append(f"H1 muito curto ({len(h1_text.split())} palavras). Deve ter 8+ palavras com benefício + cidade.")
                    score -= 15

    # Images must have alt
    imgs_no_alt = re.findall(r'<img(?![^>]*alt=)[^>]*>', html, re.IGNORECASE)
    if imgs_no_alt:
        issues.append(f"{len(imgs_no_alt)} imagens sem atributo alt.")
        score -= 10 * len(imgs_no_alt)

    # Keywords in headings
    if keywords and section_name in ("hero", "servicos", "sobre"):
        headings = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html, re.DOTALL | re.IGNORECASE)
        heading_text = " ".join(re.sub(r'<[^>]+>', '', h) for h in headings).lower()
        kw_found = sum(1 for kw in keywords[:5] if kw.lower() in heading_text)
        if kw_found == 0 and keywords:
            issues.append("Nenhuma keyword SEO encontrada nos headings. Incluir pelo menos 1.")
            score -= 15

    return json.dumps({"score": max(0, score), "issues": issues, "section": section_name}, ensure_ascii=False)


# ── check_accessibility ───────────────────────────────────────────

def _tool_check_accessibility(tool_input: dict) -> str:
    html = tool_input.get("html", "")
    issues = []

    # Buttons without accessible text
    buttons_no_text = re.findall(r'<button[^>]*>\s*<(?:i|svg|img)[^>]*>\s*</button>', html, re.IGNORECASE)
    if buttons_no_text:
        issues.append(f"{len(buttons_no_text)} botões sem texto acessível (apenas ícone). Adicionar aria-label.")

    # Links without text
    links_empty = re.findall(r'<a[^>]*>\s*<(?:i|svg|img)[^>]*>\s*</a>', html, re.IGNORECASE)
    if links_empty:
        issues.append(f"{len(links_empty)} links sem texto (apenas ícone). Adicionar aria-label.")

    # Images without alt (redundant with SEO but important for a11y)
    imgs_no_alt = re.findall(r'<img(?![^>]*alt=)[^>]*>', html, re.IGNORECASE)
    if imgs_no_alt:
        issues.append(f"{len(imgs_no_alt)} imagens sem alt text.")

    # Form inputs without labels
    inputs = re.findall(r'<input[^>]*>', html, re.IGNORECASE)
    labels = re.findall(r'<label\b', html, re.IGNORECASE)
    aria_labels = re.findall(r'aria-label=', html, re.IGNORECASE)
    if len(inputs) > len(labels) + len(aria_labels):
        issues.append("Inputs sem label ou aria-label associado.")

    # Min touch target (check for very small buttons)
    tiny_buttons = re.findall(r'(?:py-1|py-0|p-1|p-0|h-6|h-4|w-6|w-4)(?:\s|")', html)
    if len(tiny_buttons) > 2:
        issues.append("Possíveis botões/links com target < 44px. Mínimo py-3 ou h-11 para touch.")

    ok = len(issues) == 0
    return json.dumps({"ok": ok, "issues": issues, "wcag_level": "AA" if ok else "needs_fixes"}, ensure_ascii=False)


# ── check_animations ──────────────────────────────────────────────

def _tool_check_animations(tool_input: dict) -> str:
    html = tool_input.get("html", "")
    section_name = tool_input.get("section_name", "")
    issues = []
    found = []

    # Required animations per section
    if section_name == "hero":
        if "scale-in" not in html:
            issues.append("Hero H1 deve ter class .scale-in")
        else:
            found.append("scale-in")
        if "reveal" not in html:
            issues.append("Hero subtítulo deve ter class .reveal")
        else:
            found.append("reveal")
        if "pulse-cta" not in html and "btn-primary" not in html:
            issues.append("Hero CTA deve ter class .pulse-cta ou .btn-primary")
        else:
            found.append("pulse-cta/btn-primary")
        if "data-parallax" not in html:
            issues.append("Hero deve ter div com data-parallax para efeito parallax")
        else:
            found.append("data-parallax")
    else:
        # Other sections: must have .reveal on containers
        if "reveal" not in html and "stagger-item" not in html:
            issues.append(f"Seção {section_name} sem animações (.reveal ou .stagger-item). Obrigatório.")
        else:
            if "reveal" in html:
                found.append("reveal")
            if "stagger-item" in html:
                found.append("stagger-item")

    # Cards should have stagger
    if re.search(r'class="[^"]*card[^"]*"', html, re.IGNORECASE):
        if "stagger-item" not in html and "--i" not in html:
            issues.append("Cards detectados sem .stagger-item e --i para entrada sequencial.")

    # Hover interactions on cards
    if "card" in html.lower() and "hover:" not in html:
        issues.append("Cards sem hover interaction (hover:scale, hover:shadow). Adicionar micro-interação.")

    ok = len(issues) == 0
    return json.dumps({"ok": ok, "issues": issues, "animations_found": found, "section": section_name}, ensure_ascii=False)
