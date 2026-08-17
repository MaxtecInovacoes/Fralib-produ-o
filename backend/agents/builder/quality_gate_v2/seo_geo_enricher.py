"""
seo_geo_enricher.py — SEO & structured-data enrichment for FraLib landing pages.

Sprint 4+5 additions:
  - canonical URL injection
  - hreflang="pt-BR"
  - FAQPage schema.org (when FAQ section exists in HTML)
  - AggregateRating schema (when rating data exists in PRD)
  - Organization schema (always)

Usage:
    from seo_geo_enricher import enrich_seo
    result = enrich_seo(html, prd)
    # result["html"] → enriched HTML
    # result["structured_data_types"] → list of schema types injected
"""


import json
import re
from typing import Any, Dict, List, Optional


# ============================================================================
# Helpers
# ============================================================================

def _safe(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely extract a value from a dict."""
    val = data.get(key, default)
    return default if val is None else val


def _build_organization_schema(prd: Dict[str, Any]) -> Dict[str, Any]:
    """Build Organization structured data from PRD."""
    schema: Dict[str, Any] = {
        "@type": "Organization",
        "name": _safe(prd, "marca", _safe(prd, "brand_name", "")),
        "url": _safe(prd, "canonical_url", _safe(prd, "url", "")),
    }

    phone = _safe(prd, "telefone", _safe(prd, "phone", ""))
    if phone:
        schema["telephone"] = phone

    address_parts: List[str] = []
    city = _safe(prd, "cidade", _safe(prd, "city", ""))
    state = _safe(prd, "estado", _safe(prd, "state", ""))
    street = _safe(prd, "rua", _safe(prd, "street", ""))
    number = _safe(prd, "numero", _safe(prd, "number", ""))
    neighborhood = _safe(prd, "bairro", _safe(prd, "neighborhood", ""))
    cep = _safe(prd, "cep", "")

    if street:
        address_parts.append(street)
    if number:
        address_parts.append(number)
    if neighborhood:
        address_parts.append(neighborhood)
    if city:
        address_parts.append(city)
    if state:
        address_parts.append(state)
    if cep:
        address_parts.append(f"CEP: {cep}")

    if address_parts:
        schema["address"] = {
            "@type": "PostalAddress",
            "streetAddress": ", ".join(address_parts[:3]),
            "addressLocality": city,
            "addressRegion": state,
            "postalCode": cep,
        }

    logo = _safe(prd, "logo_url", _safe(prd, "logo", ""))
    if logo:
        schema["logo"] = logo

    return schema


def _build_faq_schema(html: str) -> Optional[Dict[str, Any]]:
    """Extract FAQ items from HTML and build FAQPage schema.org.

    Looks for .faq-item blocks with itemprop Question/Answer.
    """
    faq_pattern = re.compile(
        r'<div[^>]+class=["\'][^"\']*faq-item[^"\']*["\'][^>]*>.*?'
        r'itemprop="name"[^>]*>(.*?)</.*?'
        r'itemprop="text"[^>]*>(.*?)</',
        re.DOTALL | re.IGNORECASE,
    )

    questions = faq_pattern.findall(html)
    if not questions:
        return None

    faq_items = []
    for q_text, a_text in questions[:10]:  # max 10 FAQs
        q_clean = re.sub(r'<[^>]+>', '', q_text).strip()
        a_clean = re.sub(r'<[^>]+>', '', a_text).strip()
        if q_clean:
            faq_items.append({
                "@type": "Question",
                "name": q_clean,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a_clean,
                },
            })

    if not faq_items:
        return None

    return {
        "@type": "FAQPage",
        "mainEntity": faq_items,
    }


def _build_aggregate_rating_schema(prd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build AggregateRating schema if PRD provides rating data."""
    rating_value = _safe(prd, "rating", _safe(prd, "aggregate_rating", ""))
    review_count = _safe(prd, "review_count", _safe(prd, "total_reviews", ""))

    if not rating_value and not review_count:
        return None

    try:
        rv = float(rating_value) if rating_value else 4.5
    except (ValueError, TypeError):
        rv = 4.5

    try:
        rc = int(review_count) if review_count else 100
    except (ValueError, TypeError):
        rc = 100

    return {
        "@type": "AggregateRating",
        "ratingValue": min(rv, 5.0),
        "reviewCount": rc,
        "bestRating": 5,
    }


def _build_schemas(prd: Dict[str, Any], html: str) -> List[Dict[str, Any]]:
    """Build all structured data schemas for this page."""
    schemas: List[Dict[str, Any]] = []

    # Organization (always)
    org = _build_organization_schema(prd)
    if org.get("name"):
        schemas.append(org)

    # AggregateRating (conditional — PRD has rating)
    rating_schema = _build_aggregate_rating_schema(prd)
    if rating_schema:
        schemas.append(rating_schema)

    # FAQPage (conditional — HTML has FAQ section)
    faq_schema = _build_faq_schema(html)
    if faq_schema:
        schemas.append(faq_schema)

    # WebSite (always, with search action)
    canonical_url = _safe(prd, "canonical_url", "")
    if canonical_url:
        site_schema: Dict[str, Any] = {
            "@type": "WebSite",
            "name": _safe(prd, "marca", _safe(prd, "brand_name", "")),
            "url": canonical_url,
            "inLanguage": "pt-BR",
        }
        schemas.append(site_schema)

    return schemas


def _build_structured_data_script(schemas: List[Dict[str, Any]]) -> str:
    """Serialize schemas to a JSON-LD <script> block."""
    if not schemas:
        return ""
    single = schemas[0] if len(schemas) == 1 else {
        "@context": "https://schema.org",
        "@graph": schemas,
    }
    return (
        '\n<script type="application/ld+json">\n'
        + json.dumps(single, ensure_ascii=False, indent=2)
        + "\n</script>\n"
    )


# ============================================================================
# SEO tag operations
# ============================================================================

def _inject_canonical(html: str, canonical_url: str) -> str:
    """Add or replace <link rel="canonical"> in the <head>.

    Idempotent: if one already exists, it's replaced.
    """
    canonical_tag = f'<link rel="canonical" href="{canonical_url}" />'

    # If a canonical already exists, replace it
    existing = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]*>',
        html,
        re.IGNORECASE,
    )
    if existing:
        return html[:existing.start()] + canonical_tag + html[existing.end():]

    # Otherwise insert after the opening <head> tag
    head_match = re.search(r'<head[^>]*>', html, re.IGNORECASE)
    if head_match:
        pos = head_match.end()
        return html[:pos] + "\n    " + canonical_tag + html[pos:]

    # Fallback: prepend to the document
    return canonical_tag + "\n" + html


def _inject_hreflang(html: str, canonical_url: str, langs: Optional[List[str]] = None) -> str:
    """Add hreflang="pt-BR" (and optional extra langs) after canonical.

    Idempotent: existing hreflang tags are stripped and replaced.
    """
    if langs is None:
        langs = ["pt-BR"]

    # Remove existing hreflang tags
    html = re.sub(
        r'<link[^>]+hreflang[^>]*>\s*\n?',
        "",
        html,
        flags=re.IGNORECASE,
    )

    hreflang_tags = ""
    for lang in langs:
        hreflang_tags += f'    <link rel="alternate" hreflang="{lang}" href="{canonical_url}" />\n'

    # Insert after the canonical tag (or after <head> if no canonical yet)
    canonical_match = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]*>\s*\n?',
        html,
        re.IGNORECASE,
    )
    if canonical_match:
        pos = canonical_match.end()
        return html[:pos] + "\n" + hreflang_tags + html[pos:]

    head_match = re.search(r'<head[^>]*>', html, re.IGNORECASE)
    if head_match:
        pos = head_match.end()
        return html[:pos] + "\n    " + hreflang_tags.strip() + html[pos:]

    return hreflang_tags + html


def _inject_structured_data(html: str, schemas: List[Dict[str, Any]]) -> str:
    """Inject JSON-LD structured data before </head>.

    Idempotent: existing FraLib JSON-LD blocks are replaced.
    """
    script_block = _build_structured_data_script(schemas)
    if not script_block:
        return html

    # Remove existing FraLib structured data blocks
    html = re.sub(
        r'\n?<script type="application/ld\+json">.*?</script>\s*\n?',
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    head_close = html.rfind("</head>")
    if head_close != -1:
        return html[:head_close] + script_block + html[head_close:]

    # Fallback: after <head> open tag
    head_match = re.search(r'<head[^>]*>', html, re.IGNORECASE)
    if head_match:
        pos = head_match.end()
        return html[:pos] + script_block + html[pos:]

    return script_block + html


def _set_lang_attribute(html: str) -> str:
    """Ensure <html> has lang="pt-BR"."""
    return re.sub(
        r'(<html[^>]*?)lang=["\'][^"\']*["\']',
        r'\1lang="pt-BR"',
        html,
        count=1,
        flags=re.IGNORECASE,
    )


# ============================================================================
# Public API
# ============================================================================

def enrich_seo(
    html: str,
    prd: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enrich HTML with SEO improvements and structured data.

    Actions performed:
      1. Set lang="pt-BR" on <html> tag
      2. Inject <link rel="canonical">
      3. Inject <link rel="alternate" hreflang="pt-BR">
      4. Inject JSON-LD structured data (Organization, WebSite, FAQPage, AggregateRating)

    Args:
        html: Full HTML document string.
        prd:  Designer PRD dict. Key fields:
            - canonical_url (required for canonical/hreflang)
            - marca / brand_name
            - cidade / city
            - telefone / phone
            - cep, rua, estado
            - rating / aggregate_rating (float 0-5)
            - review_count / total_reviews (int)

    Returns:
        Dict with:
            "html"                  → enriched HTML
            "structured_data_types" → list of schema.org types injected
            "has_canonical"         → bool
            "has_hreflang"          → bool
            "has_structured_data"   → bool
    """
    prd = prd or {}
    structured_data_types: List[str] = []

    # --- 1. Language attribute ---
    html = _set_lang_attribute(html)

    # --- 2. Canonical URL ---
    canonical_url = _safe(prd, "canonical_url", "")
    has_canonical = False
    if canonical_url:
        html = _inject_canonical(html, canonical_url)
        has_canonical = True

    # --- 3. Hreflang ---
    has_hreflang = False
    if canonical_url:
        html = _inject_hreflang(html, canonical_url)
        has_hreflang = True

    # --- 4. Structured data (schemas) ---
    schemas = _build_schemas(prd, html)
    for s in schemas:
        stype = s.get("@type", "unknown")
        if isinstance(stype, list):
            # @graph case — record each nested type
            for item in schemas:
                if isinstance(item, dict):
                    t = item.get("@type", "")
                    if t:
                        structured_data_types.append(str(t))
        else:
            structured_data_types.append(str(stype))

    has_structured_data = bool(schemas)
    html = _inject_structured_data(html, schemas)

    return {
        "html": html,
        "structured_data_types": list(set(structured_data_types)),
        "has_canonical": has_canonical,
        "has_hreflang": has_hreflang,
        "has_structured_data": has_structured_data,
    }
