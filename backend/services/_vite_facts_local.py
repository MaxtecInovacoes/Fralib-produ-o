"""Local facts extraction helpers for vite_react_renderer and vite_templates.

Canônico para M1 do plano DRY (codex/dry-refactor).

Quatro cópias idênticas (byte-a-byte) destas funções existiam em:
  - backend/services/vite_react_renderer.py
  - backend/services/vite_templates.py

Há também variantes diferentes em ``backend/services/vite_facts.py``
(usadas por ``vite_modules.py`` e ``vite_build_executor.py``) — estas
produzem JSON-LD mais simples e devem permanecer separadas.
"""
from __future__ import annotations

from typing import Any


def business(facts: dict[str, Any]) -> dict[str, Any]:
    """Extract the ``business`` container from facts (or empty dict)."""
    return facts.get("business") if isinstance(facts.get("business"), dict) else {}


def publication_url(facts: dict[str, Any]) -> str:
    """Find the canonical site URL by probing known containers/keys."""
    for container_name in ("publication", "seo", "business"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        for key in ("canonical_url", "site_url", "canonical", "url_site"):
            url = str(container.get(key) or "").strip()
            if url.startswith(("http://", "https://")):
                return url
    return ""


def og_image(facts: dict[str, Any]) -> str:
    """Find the OG image URL from containers, then from photos arrays."""
    for container_name in ("publication", "seo", "business", "media"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        image = str(container.get("og_image") or "").strip()
        if image.startswith(("http://", "https://")):
            return image
    for source in (facts.get("photos"), business(facts).get("photos")):
        if isinstance(source, list):
            for item in source:
                image = str(item or "").strip()
                if image.startswith(("http://", "https://")):
                    return image
    return ""


def json_ld(facts: dict[str, Any]) -> str:
    """Build the schema.org LocalBusiness (or nicho-specific) JSON-LD blob."""
    import json

    biz = business(facts)
    site_url = publication_url(facts)
    image = og_image(facts)
    # Sprint 12.x: schema_type dinâmico por nicho (advogado→LegalService, etc.)
    segmento = (
        biz.get("segment")
        or biz.get("segmento")
        or facts.get("segmento")
        or facts.get("segment")
        or ""
    )
    try:
        from backend.config.nicho_registry import get_schema_type
        schema_type = get_schema_type(segmento)
    except Exception:
        schema_type = "LocalBusiness"
    data = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": biz.get("name") or biz.get("business_name") or "",
        "url": site_url,
        "image": image,
        "telephone": biz.get("phone") or biz.get("whatsapp") or "",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": biz.get("address") or biz.get("endereco") or "",
            "addressLocality": biz.get("city") or biz.get("cidade") or facts.get("cidade") or "",
            "addressCountry": "BR",
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": biz.get("rating") or "",
            "reviewCount": biz.get("total_avaliacoes") or biz.get("reviews_count") or "",
        },
    }
    cleaned = {key: value for key, value in data.items() if value not in ("", None, {}, [])}
    if isinstance(cleaned.get("aggregateRating"), dict):
        agg = {key: value for key, value in cleaned["aggregateRating"].items() if value not in ("", None)}
        if len(agg) <= 1:
            cleaned.pop("aggregateRating", None)
        else:
            cleaned["aggregateRating"] = agg
    return json.dumps(cleaned, ensure_ascii=False)
