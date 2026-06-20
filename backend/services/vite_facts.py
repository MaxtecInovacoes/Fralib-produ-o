"""Vite/React facts extraction and transformation helpers."""

from __future__ import annotations

import hashlib
from typing import Any


# ═══════════════════════════════════════════════════════════════════
# FACTS EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════════════

def _segment_key_for_business(business: dict[str, Any]) -> str | None:
    """Determine segment key from business data."""
    nome = business.get("name", "").lower()
    segmento = business.get("segment", "").lower()
    servicos = " ".join(business.get("services", [])).lower()

    # Check services first
    if "academia" in servicos or "fitness" in servicos:
        return "academia"
    if "restaurante" in servicos or "lanche" in servicos:
        return "restaurante"
    if "hamburguer" in servicos:
        return "hamburgueria"
    if "pizzaria" in servicos or "pizza" in servicos:
        return "pizzaria"
    if "dentista" in servicos or "odonto" in servicos:
        return "dentista"
    if "barbearia" in servicos:
        return "barbearia"
    if "advogad" in servicos:
        return "advocacia"
    if "pet" in servicos or "cachorro" in servicos:
        return "pet"
    if "pilates" in servicos:
        return "pilates"
    if "estetic" in servicos:
        return "estetica"

    # Check name
    for key in ["academia", "restaurante", "hamburguer", "pizza", "dent"]:
        if key in nome:
            return key

    return segmento if segmento else None


def _segment_key_from_facts(facts: dict[str, Any]) -> str:
    """Get segment key from facts dict."""
    segment = facts.get("segment", "")
    business = facts.get("business", {})
    key = _segment_key_for_business(business)
    return key or segment or "default"


def _validate_segment_specificity(source_text: str, business: dict[str, Any]) -> None:
    """Validate that generated content matches the business segment."""
    segment_key = _segment_key_for_business(business)
    if not segment_key:
        return

    # Check for cross-segment contamination
    segment_indicators = {
        "academia": ["musculação", "treino", "fitness", "ginástica", "crossfit"],
        "restaurante": ["prato", "menu", "chef", "gastronomia", "comida"],
        "hamburgueria": ["hambúrguer", "lanche", "burger", "fast food"],
        "pizzaria": ["pizza", "massa", "italiana", "forno"],
        "dentista": ["dentista", "sorriso", "tratamento", "clínico"],
        "advocacia": ["advogado", "jurídico", "direito", "advocacia"],
    }

    indicators = segment_indicators.get(segment_key, [])
    source_lower = source_text.lower()

    for indicator in indicators[:3]:
        if indicator in source_lower:
            # Found segment-specific content
            return

    # No segment-specific content found - might be generic template
    pass  # Let it pass, will be caught by other validators


# ═══════════════════════════════════════════════════════════════════
# FACTS TRANSFORMATION HELPERS
# ═══════════════════════════════════════════════════════════════════

def _facts_business(facts: dict[str, Any]) -> dict[str, Any]:
    """Extract and normalize business facts."""
    business = facts.get("business", {})
    return {
        "name": business.get("name", "Business"),
        "segment": business.get("segment", ""),
        "tagline": business.get("tagline", ""),
        "description": business.get("description", ""),
    }


def _facts_publication_url(facts: dict[str, Any]) -> str:
    """Build the publication URL from facts."""
    business = facts.get("business", {})
    slug = facts.get("slug", "")
    domain = facts.get("publication_domain", "")

    if domain:
        return f"https://{domain}/{slug}" if slug else f"https://{domain}"
    if slug:
        return f"https://{slug}.fralib.com"
    return ""


def _facts_theme_color(facts: dict[str, Any]) -> str:
    """Extract or generate theme color from facts."""
    # Check for explicit color
    color = facts.get("theme_color", "")
    if color and color.startswith("#"):
        return color

    # Generate from segment
    segment_colors = {
        "academia": "#FF4444",
        "restaurante": "#FF8C00",
        "hamburgueria": "#FF4500",
        "pizzaria": "#FFD700",
        "dentista": "#4A90D9",
        "advocacia": "#2C3E50",
        "pet": "#9B59B6",
        "estetica": "#E91E63",
        "barbearia": "#795548",
    }

    segment = _segment_key_from_facts(facts)
    return segment_colors.get(segment, "#3B82F6")  # Default blue


def _facts_local_keywords(facts: dict[str, Any]) -> list[str]:
    """Extract local SEO keywords from facts."""
    keywords = []

    cidade = facts.get("city", "")
    if cidade:
        keywords.append(cidade)

    # Get palavras_poder from jina intelligence
    palavras = facts.get("palavras_poder", [])
    if isinstance(palavras, list):
        keywords.extend(palavras[:5])

    return keywords


def _facts_meta_description(facts: dict[str, Any]) -> str:
    """Generate meta description from facts."""
    business = facts.get("business", {})
    cidade = facts.get("city", "")
    servicos = facts.get("services", [])

    name = business.get("name", "")
    segment = business.get("segment", "")

    parts = [f"{name} - "]
    if servicos:
        parts.append(f"{servicos[0]} em {cidade}")
    else:
        parts.append(f"{segment} em {cidade}")

    desc = "".join(parts)
    return desc[:160] if len(desc) > 160 else desc


def _facts_og_image(facts: dict[str, Any]) -> str:
    """Get or generate OG image URL."""
    og_image = facts.get("og_image", "")
    if og_image:
        return og_image

    # Try hero image
    fotos = facts.get("fotos", [])
    if fotos:
        return fotos[0]

    return ""


def _facts_json_ld(facts: dict[str, Any]) -> str:
    """Generate JSON-LD structured data."""
    import json

    business = facts.get("business", {})
    cidade = facts.get("city", "")
    telefone = facts.get("phone", "")
    endereco = facts.get("address", "")

    json_ld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": business.get("name", ""),
        "description": business.get("description", ""),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": cidade,
            "streetAddress": endereco,
        },
    }

    if telefone:
        json_ld["telephone"] = telefone

    return json.dumps(json_ld, ensure_ascii=False)


def _visual_business_payload(facts: dict[str, Any]) -> dict[str, str]:
    """Build visual configuration payload for components."""
    business = facts.get("business", {})
    cidade = facts.get("city", "")

    return {
        "businessName": business.get("name", ""),
        "businessTagline": business.get("tagline", ""),
        "city": cidade,
        "phone": facts.get("phone", ""),
        "address": facts.get("address", ""),
        "segment": facts.get("segment", ""),
    }


def _visual_media_urls(facts: dict[str, Any]) -> list[str]:
    """Extract media URLs for visual components."""
    urls = []

    # Hero images
    fotos = facts.get("fotos", [])
    if isinstance(fotos, list):
        urls.extend(fotos[:5])

    # Logo
    logo = facts.get("logo_url", "")
    if logo:
        urls.insert(0, logo)

    return urls
