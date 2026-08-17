"""Deterministic visual contract audit for generated sites."""


import re
from dataclasses import dataclass
from typing import Any


class VisualContractGateError(ValueError):
    """Raised when HTML violates the visual contract."""


@dataclass
class VisualContractReport:
    approved: bool
    problems: list[str]


def audit_visual_contract(html: str, prd: Any) -> VisualContractReport:
    contract = _get(prd, "visual_contract", default={}) or {}
    if not isinstance(contract, dict):
        contract = {}
    problems: list[str] = []
    low = (html or "").lower()
    visible = _visible_text(html)

    section_count = len(re.findall(r"<!--\s*section:", low))
    if section_count == 0:
        section_count = len(re.findall(r"(?is)<section\b", html or ""))
    minimum = int(((contract.get("acceptance_criteria") or {}).get("minimum_sections") or 3))
    if section_count < minimum:
        problems.append(f"visual_contract: poucas secoes ({section_count}/{minimum})")

    if not re.search(
        r"(?is)<(?:section|header)\b[^>]*(?:id=['\"]?hero|data-builder-hero|builder-experience-hero|hf-reference-hero|fralib-deterministic-hero|data-component-id=)",
        html or "",
    ):
        problems.append("visual_contract: hero sem contrato experience")
    hero = _hero_block(html)
    if hero:
        hero_low = hero.lower()
        if "<h1" not in hero_low:
            problems.append("visual_contract: hero sem h1")
        if not re.search(r"<a\b|<button\b", hero_low):
            problems.append("visual_contract: hero sem CTA")
        if not any(token in hero_low for token in ("data-parallax", "kenburns", "fralibkenburns", "mask-reveal")):
            problems.append("visual_contract: hero sem motion/parallax")
        city = _normalize(str(_get(prd, "cidade", "") or _get(prd, "city", "")))
        hero_text = _normalize(_visible_text(hero))
        if not any(token in hero_low for token in ("fralib-proof-chip", "proof", "avaliacao", "avaliação", "cidade")) and (
            not city or city not in hero_text
        ):
            problems.append("visual_contract: hero sem prova/contexto local")

    if not _has_media_ratio_guard(low):
        problems.append("visual_contract: midia sem regra 16:9")
    if re.search(r"(?is)<section\b[^>]*class=['\"][^'\"]*fralib-map-section", html or ""):
        if "maps.google.com/maps?q=" not in low:
            problems.append("visual_contract: mapa nao usa Google Maps por query")
        if "openstreetmap" in low:
            problems.append("visual_contract: mapa OSM amplo detectado")
    if low.count("<footer") != 1:
        problems.append("visual_contract: footer ausente ou duplicado")
    if "<footer" in low:
        footer = _footer_block(html)
        footer_text = _visible_text(footer).lower()
        if "contato" not in footer_text and not re.search(r"(?is)<footer\b.*?(tel:|wa\.me|whatsapp)", footer):
            problems.append("visual_contract: footer sem contato")
        if len(re.findall(r"(?is)<a\b", footer)) < 2:
            problems.append("visual_contract: footer sem navegação")
        if not any(token in _normalize(footer_text) for token in ("confianca", "privacidade", "lgpd", "cookies", "seguranca")):
            problems.append("visual_contract: footer sem nota de confianca")
    if "lorem ipsum" in _normalize(visible):
        problems.append("visual_contract: lorem ipsum visivel")
    if "atividades sob consulta" in _normalize(visible):
        problems.append("visual_contract: fallback de atividades visivel")
    if not _has_mobile_overflow_guard(low):
        problems.append("visual_contract: sem trava mobile anti-overflow")

    return VisualContractReport(approved=not problems, problems=problems)


def validate_visual_contract(html: str, prd: Any) -> None:
    report = audit_visual_contract(html, prd)
    if not report.approved:
        raise VisualContractGateError("; ".join(report.problems))


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _hero_block(html: str) -> str:
    match = re.search(r"(?is)<!--\s*SECTION:hero\s*-->(.*?)<!--\s*/SECTION:hero\s*-->", html or "")
    if match:
        return match.group(1)
    match = re.search(r"(?is)<(?:section|header)\b[^>]*(?:id=['\"]?hero|hero)[^>]*>.*?</(?:section|header)>", html or "")
    return match.group(0) if match else ""


def _footer_block(html: str) -> str:
    match = re.search(r"(?is)<footer\b.*?</footer>", html or "")
    return match.group(0) if match else ""


def _has_mobile_overflow_guard(html_lower: str) -> bool:
    compact = re.sub(r"\s+", "", html_lower or "")
    return "overflow-x:hidden" in compact or (
        "max-width:100vw" in compact and "overflow:hidden" in compact
    )


def _has_media_ratio_guard(html_lower: str) -> bool:
    compact = re.sub(r"\s+", "", html_lower or "")
    return (
        "aspect-ratio:16/9" in compact
        or "aspect-ratio:16/10" in compact
        or "aspect-ratio:4/3" in compact
        or "object-fit:cover" in compact
    )


def _visible_text(html: str) -> str:
    text = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", html or "")
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize(value: str) -> str:
    return (
        str(value or "")
        .lower()
        .replace("ç", "c")
        .replace("á", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
    )
