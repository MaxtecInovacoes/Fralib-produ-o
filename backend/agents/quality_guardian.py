"""Quality Guardian Agent — avalia HTML gerado em 5 eixos."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

AXIS_VISUAL = "visual"
AXIS_CONTENT = "conteudo"
AXIS_CONVERSION = "conversao"
AXIS_TECHNICAL = "tecnico"
AXIS_ORIGINALITY = "originalidade"
ALL_AXES = (AXIS_VISUAL, AXIS_CONTENT, AXIS_CONVERSION, AXIS_TECHNICAL, AXIS_ORIGINALITY)
AXIS_WEIGHTS = {
    AXIS_VISUAL: 0.25, AXIS_CONTENT: 0.25,
    AXIS_CONVERSION: 0.20, AXIS_TECHNICAL: 0.15, AXIS_ORIGINALITY: 0.15,
}
SCORE_DEPLOY_BLOCKED = 5.0
SCORE_DEPLOY_OK = 7.0


@dataclass
class QualityIssue:
    axis: str
    severity: str
    description: str
    location: str = ""


@dataclass
class QualityCorrection:
    """Correcao cirurgica para o builder re-renderizar so o trecho com defeito."""

    axis: str
    severity: str
    problema: str
    sugestao: str
    html_snippet: str = ""


@dataclass
class QualityVerdict:
    overall_score: float
    axis_scores: dict[str, float]
    issues: list[QualityIssue] = field(default_factory=list)
    decision: str = "deploy"
    feedback: str = ""
    corrections: list[QualityCorrection] = field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0


def run_quality_guardian(
    html: str,
    *,
    is_fallback: bool = False,
    has_template_fallback: bool = False,
    dados_incompletos: bool = False,
    design_context_failed: bool = False,
    palette_overridden: bool = False,
) -> QualityVerdict:
    issues: list[QualityIssue] = []
    gate_problems = _tech_heuristics(html)

    for problem in gate_problems:
        severity = "critical" if "critical" in str(problem).lower() else "major"
        issues.append(QualityIssue(AXIS_TECHNICAL, severity, str(problem)))

    visual_score = _score_visual(html, issues)
    content_score = _score_content(html, issues)
    conversion_score = _score_conversion(html)
    originality_score = _score_originality(
        html, has_template_fallback=has_template_fallback,
        design_context_failed=design_context_failed,
        palette_overridden=palette_overridden, issues=issues,
    )
    tech_score = _score_tech(gate_problems, html)

    axis_scores = {
        AXIS_VISUAL: visual_score, AXIS_CONTENT: content_score,
        AXIS_CONVERSION: conversion_score, AXIS_TECHNICAL: tech_score,
        AXIS_ORIGINALITY: originality_score,
    }
    overall = sum(axis_scores[a] * AXIS_WEIGHTS[a] for a in ALL_AXES)

    if is_fallback:
        overall -= 1.0
        issues.append(QualityIssue(AXIS_CONTENT, "major",
                                   "Site gerado com is_fallback=True"))
    if dados_incompletos:
        overall -= 0.5
        issues.append(QualityIssue(AXIS_CONTENT, "major",
                                   "Briefing original com dados incompletos"))
    if design_context_failed:
        overall -= 1.5
        issues.append(QualityIssue(AXIS_VISUAL, "critical",
                                   "design_context falhou — tokens genericos"))

    overall = max(0.0, min(10.0, overall))
    critical_count = sum(1 for i in issues if i.severity == "critical")

    if overall < SCORE_DEPLOY_BLOCKED or critical_count >= 3:
        decision = "block"
        corrections = _build_structured_corrections(issues, html)
        feedback = _build_retry_feedback(issues, axis_scores)
    elif overall < SCORE_DEPLOY_OK:
        decision = "deploy_with_warning"
        feedback = ""
        corrections = []
    else:
        decision = "deploy"
        feedback = ""
        corrections = []

    return QualityVerdict(
        overall_score=overall, axis_scores=axis_scores,
        issues=issues, decision=decision, feedback=feedback,
        corrections=corrections,
        total_issues=len(issues), critical_count=critical_count,
    )


def _tech_heuristics(html: str) -> list[str]:
    problems: list[str] = []
    if not html:
        problems.append("HTML vazio")
        return problems
    if len(html) < 2000:
        problems.append(f"HTML muito pequeno ({len(html)} bytes)")
    if html.count("<html") > html.count("</html>"):
        problems.append("Tag <html> nao fechada")
    if html.count("<body") > html.count("</body>"):
        problems.append("Tag <body> nao fechada")
    if "<script" in html.lower() and "console.log" in html:
        problems.append("console.log detectado em producao")
    return problems


def _score_visual(html: str, issues: list[QualityIssue]) -> float:
    score = 7.0
    if not html:
        score -= 5.0
        issues.append(QualityIssue(AXIS_VISUAL, "critical", "HTML vazio"))
    if len(html) < 2000:
        score -= 2.0
        issues.append(QualityIssue(AXIS_VISUAL, "major", "HTML muito pequeno (<2KB)"))
    if "bg-" in html and "from-" in html:
        score += 0.5
    if "rounded" in html or "border-radius" in html:
        score += 0.3
    return max(0.0, min(10.0, score))


def _score_content(html: str, issues: list[QualityIssue]) -> float:
    score = 7.0
    placeholders = re.findall(r"\{\{[^}]+\}\}", html)
    if placeholders:
        score -= len(placeholders) * 0.5
        issues.append(QualityIssue(
            AXIS_CONTENT, "critical",
            f"Placeholders {{}} nao substituidos: {len(placeholders)}",
        ))
    if re.search(r"lorem ipsum", html, re.IGNORECASE):
        score -= 3.0
        issues.append(QualityIssue(AXIS_CONTENT, "critical", "Lorem ipsum detectado"))
    return max(0.0, min(10.0, score))


def _score_conversion(html: str) -> float:
    score = 5.0
    if "wa.me/" in html or "whatsapp" in html.lower() or "wpp" in html.lower():
        score += 2.5
    if "tel:" in html:
        score += 0.5
    if "cta" in html.lower() or "agendar" in html.lower() or "fale" in html.lower():
        score += 1.0
    if "maps.google" in html or "google.com/maps" in html:
        score += 1.0
    return max(0.0, min(10.0, score))


def _score_tech(gate_problems: list[Any], html: str) -> float:
    if not html:
        return 0.0
    score = 10.0 - min(len(gate_problems), 10)
    return max(0.0, min(10.0, score))


def _score_originality(
    html: str, *, has_template_fallback: bool, design_context_failed: bool,
    palette_overridden: bool, issues: list[QualityIssue],
) -> float:
    score = 8.0
    if has_template_fallback:
        score -= 2.0
        issues.append(QualityIssue(AXIS_ORIGINALITY, "major",
                                   "Template de subnicho foi fallback"))
    if design_context_failed:
        score -= 2.5
    if palette_overridden:
        score += 0.5
    return max(0.0, min(10.0, score))


def _build_retry_feedback(issues: list[QualityIssue], axis_scores: dict[str, float]) -> str:
    critical = [i for i in issues if i.severity == "critical"]
    parts = [
        f"Score {sum(axis_scores[a] * AXIS_WEIGHTS[a] for a in ALL_AXES):.1f}/10.",
        f"{len(critical)} problemas criticos identificados.",
    ]
    if critical:
        parts.append("Criticos: " + "; ".join(c.description for c in critical[:5]))
    weakest_axis = min(axis_scores, key=axis_scores.get)
    parts.append(f"Eixo mais fraco: {weakest_axis} (score {axis_scores[weakest_axis]:.1f}).")
    return " ".join(parts)


_SUGESTOES = {
    "HTML vazio": "renderize o body inteiro com conteudo real",
    "Lorem ipsum detectado": "substitua Lorem ipsum por copy real do segmento/nicho",
    "Placeholders {{}} nao substituidos": "substitua cada {{var}} pelo valor real do lead",
    "Tag <html> nao fechada": "feche a tag <html> antes do fim do documento",
    "Tag <body> nao fechada": "feche a tag </body> antes de </html>",
    "console.log detectado em producao": "remova todos os console.log do HTML",
    "design_context falhou": "use tokens OKLch do briefing em vez de cores genericas",
    "Site gerado com is_fallback=True": "refaca usando dados reais do briefing, sem fallback",
    "Briefing original com dados incompletos": "preencha os campos faltantes (nome, cidade, segmento, whatsapp)",
    "Template de subnicho foi fallback": "use o template especifico do subnicho detectado",
    "HTML muito pequeno": "gere secoes completas (hero, features, testimonials, FAQ, footer)",
}


def _snippet(html: str, needle: str, ctx: int = 60) -> str:
    """Pega um trecho do HTML em torno da primeira ocorrencia de needle."""
    if not html or not needle:
        return ""
    idx = html.lower().find(needle.lower())
    if idx < 0:
        return ""
    start = max(0, idx - ctx)
    end = min(len(html), idx + len(needle) + ctx)
    return html[start:end].replace("\n", " ")


def _build_structured_corrections(
    issues: list[QualityIssue], html: str,
) -> list[QualityCorrection]:
    """Transforma issues em correcoes cirurgicas para o builder re-renderizar."""
    out: list[QualityCorrection] = []
    for issue in issues:
        if issue.severity not in ("critical", "major"):
            continue
        problema = issue.description
        sugestao = _SUGESTOES.get(problema, "ajuste o trecho afetado")
        needle = ""
        if "{{" in problema:
            needle = "{{"
        elif "Lorem" in problema:
            needle = "lorem"
        elif "console.log" in problema:
            needle = "console.log"
        elif "<html" in problema:
            needle = "<html"
        elif "<body" in problema:
            needle = "<body"
        out.append(QualityCorrection(
            axis=issue.axis,
            severity=issue.severity,
            problema=problema,
            sugestao=sugestao,
            html_snippet=_snippet(html, needle) if needle else "",
        ))
    return out


def render_correction_prompt(corrections: list[QualityCorrection]) -> str:
    """Monta um prompt em linguagem natural, como se fosse um humano pedindo ajuste."""
    if not corrections:
        return ""
    lines = ["O site anterior saiu com problemas. Corrija SO o que esta errado, mantendo o resto igual:", ""]
    for i, c in enumerate(corrections, 1):
        lines.append(f"{i}. [{c.axis}/{c.severity}] {c.problema}")
        lines.append(f"   O que fazer: {c.sugestao}")
        if c.html_snippet:
            lines.append(f"   Trecho atual: ...{c.html_snippet}...")
        lines.append("")
    lines.append("Devolva o HTML inteiro ja corrigido. NAO mexa no que ja estava certo.")
    return "\n".join(lines)
