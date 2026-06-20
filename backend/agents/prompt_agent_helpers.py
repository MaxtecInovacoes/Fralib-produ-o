"""Prompt Agent helpers: utility, parsing, extraction, formatting functions."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


def _section_name(item: Any) -> str:
    data = _dict(item)
    if data:
        return str(data.get("id") or data.get("name") or data.get("title") or "seção")
    return str(item)


def _infer_prompt_archetype(segment: str) -> str:
    normalized = _normalize(segment)
    if any(token in normalized for token in ("academia", "fitness", "crossfit", "treino")):
        return "BOLD_ENERGY"
    if any(token in normalized for token in ("nutric", "psicolog", "yoga", "spa", "estetica")):
        return "ZEN_PURE"
    if any(token in normalized for token in ("restaurante", "pizzaria", "cafe", "gastronomia")):
        return "LUXURY_ELITE"
    if any(token in normalized for token in ("software", "saas", "tech", "ia")):
        return "MODERN_TECH"
    return "TRUST_ELITE"


def _normalize_target(target: str) -> str:
    from backend.agents.prompt_agent_context import _VALID_TARGETS

    value = str(target or "landing-page").strip().lower().replace("_", "-")
    if value not in _VALID_TARGETS:
        raise ValueError(f"target invalido: {target!r}")
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if hasattr(value, "__dict__"):
            dumped = {**dumped, **vars(value)}
        return dumped
    if hasattr(value, "dict"):
        dumped = value.dict()
        if hasattr(value, "__dict__"):
            dumped = {**dumped, **vars(value)}
        return dumped
    if hasattr(value, "__dict__"):
        return vars(value)
    return {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else _as_dict(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in re.split(r"[,;\n]", value) if item.strip()]
    return []


def _first(*args: Any, default: Any = "") -> Any:
    sources: list[dict[str, Any]] = []
    keys: list[str] = []
    reading_sources = True
    for arg in args:
        if reading_sources and isinstance(arg, dict):
            sources.append(arg)
            continue
        reading_sources = False
        keys.append(str(arg))
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value not in (None, "", [], {}):
                return value
    return default


def _compact(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _dump_compact(value: Any, limit: int) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return _compact(value, limit)
    try:
        return _compact(json.dumps(_as_dict(value) or value, ensure_ascii=False, default=str), limit)
    except TypeError:
        return _compact(str(value), limit)


def _media_urls(raw: Any) -> list[str]:
    urls: list[str] = []
    for item in _as_list(raw):
        if isinstance(item, str) and item.startswith("http"):
            urls.append(item)
        elif isinstance(item, dict):
            url = item.get("url") or item.get("src") or item.get("regular") or item.get("full")
            if isinstance(url, str) and url.startswith("http"):
                urls.append(url)
    return list(dict.fromkeys(urls))


def _extract_keyword_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for line in str(text or "").splitlines():
        clean = re.sub(r"^[\s\-*#0-9.)]+", "", line).strip()
        clean = _sanitize_primary_term(clean)
        if clean:
            candidates.append(clean)
    return candidates[:16]


def _sanitize_primary_term(value: Any) -> str:
    clean = " ".join(str(value or "").split()).strip(" -–—:;,.")
    if not clean:
        return ""
    low = _normalize(clean)
    blocked = (
        "keyword research",
        "buscas reais",
        "google suggest",
        "intencao transacional",
        "intencao informacional",
        "concorrencia local",
        "instrucao",
        "instrucoes",
        "atualizado",
        "priorize",
    )
    if clean.startswith(("===", "---")) or any(marker in low for marker in blocked):
        return ""
    if len(clean) > 80:
        return ""
    if not any(ch.isalpha() for ch in clean):
        return ""
    return clean


def _allowed_numeric_claims(business: dict[str, Any]) -> list[str]:
    claims = []
    rating = business.get("rating")
    if rating not in (None, ""):
        claims.append(f"rating {rating}")
    reviews_count = business.get("reviews_count")
    if reviews_count not in (None, ""):
        claims.append(f"{reviews_count} avaliações")
    return claims


def _infer_subniche(segment: str) -> str:
    normalized = _normalize(segment)
    if any(token in normalized for token in ("pizzaria", "restaurante", "cafe")):
        return "alimentacao local"
    if any(token in normalized for token in ("academia", "fitness", "crossfit")):
        return "fitness e treino"
    if any(token in normalized for token in ("dentista", "odontologia")):
        return "saude bucal"
    if any(token in normalized for token in ("nutricionista", "nutricao")):
        return "saude e alimentacao"
    if any(token in normalized for token in ("otica", "optica", "oculos")):
        return "otica e cuidados visuais"
    return ""


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _clean_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _market_intelligence_context(value: Any) -> Any:
    data = _dict(value)
    if data:
        return _clean_dict(
            {
                "market_voice": _first(data, {}, "tom_de_voz", "market_voice", default=""),
                "sales_language": _as_list(_first(data, {}, "palavras_poder", "sales_language", default=[]))[:16],
                "reference_headlines": _as_list(_first(data, {}, "headlines_referencia", "headlines", default=[]))[:8],
                "reference_ctas": _as_list(_first(data, {}, "ctas_referencia", "ctas", default=[]))[:8],
                "visual_style": _first(data, {}, "estilo_visual", "visual_style", default=""),
                "audience_notes": _first(data, {}, "publico_alvo", "audience", default=""),
                "source_urls": _as_list(_first(data, {}, "fontes_analisadas", "sources", default=[]))[:8],
            }
        )
    return _compact(_strip_legacy_control_text(value), 6000)


def _ideal_customer_context(lead: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(_first(lead, facts, "cliente_ideal", "ideal_customer", "perfil_cliente", default={}))
    if raw:
        return _clean_dict(
            {
                "audience": _first(raw, {}, "audience", "publico", "quem", default=""),
                "age_range": _first(raw, {}, "age_range", "idade", default=""),
                "profession_or_segment": _first(raw, {}, "profession_or_segment", "profissao", "segmento", default=""),
                "main_problems": _as_list(_first(raw, {}, "main_problems", "problemas", "dores", default=[]))[:10],
                "goals": _as_list(_first(raw, {}, "goals", "objetivos", default=[]))[:10],
                "buying_trigger": _first(raw, {}, "buying_trigger", "motivo_procura", "gatilho", default=""),
            }
        )
    research = _dict(_first(facts, {}, "jina_market_intelligence", "jina_intel_dict", default={}))
    return _clean_dict(
        {
            "audience": _first(facts, research, "publico_alvo", "audience", default=""),
            "main_problems": _as_list(_first(facts, {}, "dores", "problemas", default=[]))[:10],
            "goals": _as_list(_first(facts, {}, "objetivos", default=[]))[:10],
            "buying_trigger": _first(facts, {}, "motivo_procura", "gatilho_compra", default=""),
        }
    )


def _strip_legacy_control_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    blocked_markers = (
        "PALAVRAS PROIBIDAS",
        "REPROVO",
        "NUNCA usar",
        "NUNCA use",
        "site REJEITADO",
        "REGRA:",
        "NÃO devemos copiar",
    )
    lines: list[str] = []
    skip_until_blank = False
    for line in text.splitlines():
        raw = line.strip()
        if skip_until_blank:
            if not raw:
                skip_until_blank = False
            continue
        if "PALAVRAS PROIBIDAS" in raw:
            skip_until_blank = True
            continue
        if any(marker in raw for marker in blocked_markers):
            continue
        lines.append(line)
    return _compact("\n".join(lines), 6000)


def _fmt_contract_facts(business: dict[str, Any]) -> str:
    fact_keys = [
        ("Nome", "name"),
        ("Segmento", "segment"),
        ("Subnicho", "subniche"),
        ("Cidade", "city"),
        ("Cidade/região", "service_region"),
        ("Endereço", "address"),
        ("Telefone", "phone"),
        ("WhatsApp", "whatsapp"),
        ("E-mail", "email"),
        ("Site atual", "website"),
        ("Redes sociais", "socials"),
        ("Rating", "rating"),
        ("Quantidade de avaliações", "reviews_count"),
        ("Horário", "hours"),
        ("Faixa de preço", "price_range"),
    ]
    lines = []
    for label, key in fact_keys:
        value = business.get(key)
        if value not in (None, "", [], {}):
            lines.append(f"- {label}: {_fmt_value(value)}")
    return "\n".join(lines) if lines else "- Nenhum fato confirmado além do nicho informado."


def _fmt_missing_contract_fields(business: dict[str, Any], content: dict[str, Any]) -> str:
    checks = [
        ("Telefone", business.get("phone") or business.get("whatsapp")),
        ("E-mail", business.get("email")),
        ("Endereço", business.get("address")),
        ("Site atual", business.get("website")),
        ("Redes sociais", business.get("socials")),
        ("Horário", business.get("hours")),
        ("Faixa de preço", business.get("price_range")),
        ("Serviços/produtos oficiais", content.get("services") or content.get("attributes")),
        ("Mapa confiável", content.get("maps_embed") or content.get("maps_url")),
    ]
    missing = [label for label, value in checks if value in (None, "", [], {})]
    if not missing:
        return "- Nenhum campo crítico ausente."
    return "\n".join(f"- {label}: não inventar; resolver com CTA, texto neutro ou bloco sem fato específico." for label in missing)


def _fmt_value(value: Any) -> str:
    if value in (None, "", [], {}):
        return "não informado"
    if isinstance(value, (dict, list, tuple, set)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value)
    return _strip_legacy_control_text(text)


def _fmt_list(value: Any) -> str:
    items = _as_list(value)
    if not items:
        return "- não informado"
    return "\n".join(f"- {_fmt_value(item)}" for item in items[:16])


def _fmt_sections(sections: Any) -> str:
    items = _as_list(sections)
    if not items:
        return "- O Builder pode definir a estrutura conforme o briefing."
    lines = []
    for item in items[:12]:
        data = _dict(item)
        if data:
            title = data.get("title") or data.get("name") or data.get("id") or "seção"
            intent = data.get("intent") or data.get("body") or ""
            lines.append(f"- {title}: {intent}".rstrip(": "))
        else:
            lines.append(f"- {_fmt_value(item)}")
    return "\n".join(lines)


def _fmt_research(research: dict[str, Any], seo: dict[str, Any]) -> str:
    market = research.get("jina_market_intelligence")
    lines = []
    if market:
        lines.append(f"Inteligência Jina: {_fmt_value(market)}")
    if research.get("keyword_research"):
        lines.append(f"Keyword research: {_fmt_value(research.get('keyword_research'))}")
    if seo.get("primary_terms"):
        lines.append("Termos de busca e SEO local:")
        lines.append(_fmt_list(seo.get("primary_terms")))
    if seo.get("search_intent_notes"):
        lines.append(f"Notas de intenção de busca: {_fmt_value(seo.get('search_intent_notes'))}")
    return "\n".join(lines) if lines else "não informado"


def _qualification_summary(qualification: dict[str, Any], business: dict[str, Any]) -> str:
    parts = []
    if business.get("rating"):
        parts.append(f"rating {business.get('rating')}")
    if business.get("reviews_count") not in (None, ""):
        parts.append(f"{business.get('reviews_count')} avaliações")
    if qualification.get("decision"):
        parts.append(f"Caio: {qualification.get('decision')}")
    if qualification.get("score"):
        parts.append(f"score {qualification.get('score')}")
    if qualification.get("reason"):
        parts.append(str(qualification.get("reason")))
    return " | ".join(parts)
