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
class QualityVerdict:
    overall_score: float
    axis_scores: dict[str, float]
    issues: list[QualityIssue] = field(default_factory=list)
    decision: str = "deploy"
    feedback: str = ""
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

    tech_critical = 0
    for problem in gate_problems:
        severity = "critical" if "critical" in str(problem).lower() else "major"
        if severity == "critical":
            tech_critical += 1
        issues.append(QualityIssue(AXIS_TECHNICAL, severity, str(problem)))

    visual_score = _score_visual(html, issues)
    content_score = _score_content(html, issues)
    conversion_score = _score_conversion(html, issues)
    originality_score = _score_originality(
        html, has_template_fallback=has_template_fallback,
        design_context_failed=design_context_failed,
        palette_overridden=palette_overridden, issues=issues,
    )
    tech_score = _score_tech(gate_problems, html, issues)

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
        feedback = _build_retry_feedback(issues, axis_scores)
    elif overall < SCORE_DEPLOY_OK:
        decision = "deploy_with_warning"
        feedback = ""
    else:
        decision = "deploy"
        feedback = ""

    return QualityVerdict(
        overall_score=overall, axis_scores=axis_scores,
        issues=issues, decision=decision, feedback=feedback,
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


def _score_conversion(html: str, issues: list[QualityIssue]) -> float:
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


def _score_tech(gate_problems: list[Any], html: str, issues: list[QualityIssue]) -> float:
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