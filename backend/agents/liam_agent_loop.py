"""
Liam Managed Agent — Validação e auto-correção por seção.

Diferente do Arquiteto (loop agentic completo), o Liam usa um padrão
híbrido: gera com Opus (criativo) e valida/corrige com Sonnet (barato).

Fluxo por seção:
  1. Opus gera HTML da seção (mesmo que o Liam original)
  2. Tools validam: HTML, design tokens, SEO, acessibilidade, animações
  3. Se issues encontrados → Sonnet corrige o HTML
  4. Re-valida após correção
  5. Seção aprovada → próxima

Isso garante que CADA seção sai perfeita sem depender da Liz depois.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from liam_tools import execute_tool


# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════

MAX_FIX_ATTEMPTS = 2  # máximo de correções por seção


# ══════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE
# ══════════════════════════════════════════════════════════════════

def validate_section(html: str, section_name: str, keywords: list = None) -> dict:
    """
    Executa todas as validações numa seção HTML.
    Retorna dict com ok, all_issues, all_warnings.
    """
    all_issues = []
    all_warnings = []

    # 1. HTML structure
    result = json.loads(execute_tool("validate_html", {"html": html, "section_name": section_name}))
    if not result.get("ok"):
        all_issues.extend(result.get("issues", []))

    # 2. Design tokens
    result = json.loads(execute_tool("check_design_tokens", {"html": html}))
    if not result.get("ok"):
        all_issues.extend(result.get("issues", []))
    all_warnings.extend(result.get("warnings", []))

    # 3. SEO
    result = json.loads(execute_tool("check_seo_score", {
        "html": html,
        "section_name": section_name,
        "keywords": keywords or []
    }))
    if result.get("score", 100) < 70:
        all_issues.extend(result.get("issues", []))
    elif result.get("issues"):
        all_warnings.extend(result.get("issues", []))

    # 4. Accessibility
    result = json.loads(execute_tool("check_accessibility", {"html": html}))
    if not result.get("ok"):
        all_warnings.extend(result.get("issues", []))

    # 5. Animations
    result = json.loads(execute_tool("check_animations", {"html": html, "section_name": section_name}))
    if not result.get("ok"):
        all_issues.extend(result.get("issues", []))

    ok = len(all_issues) == 0
    return {
        "ok": ok,
        "issues": all_issues,
        "warnings": all_warnings,
    }


def fix_section_html(html: str, issues: list, section_name: str) -> str:
    """
    Usa Sonnet para corrigir issues no HTML de uma seção.
    Barato e rápido — não precisa de Opus pra correções mecânicas.
    """
    from llm_direct import call_claude

    issues_fmt = "\n".join(f"- {issue}" for issue in issues)

    prompt = f"""Corrija o HTML abaixo. Problemas encontrados:
{issues_fmt}

REGRAS:
- Retorne APENAS o HTML corrigido da <section>
- Comece com <section. Sem markdown, sem explicação.
- Mantenha todo o conteúdo/copy original
- Apenas corrija os problemas listados
- Use var(--bg), var(--fg), var(--accent), var(--surface), var(--muted), var(--border) para cores
- Adicione classes de animação onde faltam (.reveal, .scale-in, .stagger-item)
- Adicione alt em imagens, aria-label em botões de ícone

HTML ORIGINAL:
{html}"""

    fixed = call_claude(
        system="Você é um corretor de HTML. Corrija APENAS os problemas listados. Retorne APENAS HTML puro, sem markdown.",
        user=prompt,
        model="sonnet",
        max_tokens=8000,
        temperature=0.1,
        agent_name=None,  # Sem RAG/Skills — correção mecânica
    )

    # Limpar
    fixed = fixed.replace("```html", "").replace("```", "").strip()
    fs = fixed.lower().find("<section")
    if fs > 0:
        fixed = fixed[fs:]
    ls = fixed.lower().rfind("</section>")
    if ls > 0:
        fixed = fixed[:ls + len("</section>")]

    return fixed.strip()


def validate_and_fix_section(html: str, section_name: str, keywords: list = None) -> tuple:
    """
    Valida seção e corrige se necessário. Retorna (html_final, was_fixed, validation_result).
    """
    # Primeira validação
    result = validate_section(html, section_name, keywords)

    if result["ok"]:
        if result["warnings"]:
            print(f"[LiamAgent] {section_name}: OK com {len(result['warnings'])} warnings")
        else:
            print(f"[LiamAgent] {section_name}: OK perfeito")
        return html, False, result

    # Tem issues — tentar corrigir
    print(f"[LiamAgent] {section_name}: {len(result['issues'])} issues, corrigindo...")

    current_html = html
    for attempt in range(MAX_FIX_ATTEMPTS):
        current_html = fix_section_html(current_html, result["issues"], section_name)

        # Re-validar
        result = validate_section(current_html, section_name, keywords)
        if result["ok"]:
            print(f"[LiamAgent] {section_name}: corrigido na tentativa {attempt + 1}")
            return current_html, True, result

        print(f"[LiamAgent] {section_name}: ainda {len(result['issues'])} issues após tentativa {attempt + 1}")

    # Não conseguiu corrigir completamente — retorna melhor versão
    print(f"[LiamAgent] {section_name}: {len(result['issues'])} issues restantes após {MAX_FIX_ATTEMPTS} tentativas")
    return current_html, True, result
