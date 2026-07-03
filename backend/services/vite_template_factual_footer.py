"""Factual footer builder — extrai dados reais do lead sem depender de LLM.

Regra do projeto: NUNCA usar fallback silencioso. Se um campo critico
faltar no lead, levanta DadosIncompletosError para o caller tratar.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus


class DadosIncompletosError(ValueError):
    """Levantada quando campos criticos do briefing estao ausentes."""

    def __init__(self, message: str, missing_fields: list[str]):
        super().__init__(message)
        self.missing_fields = missing_fields


def _digits(raw: str) -> str:
    return re.sub(r"\D+", "", str(raw or "").strip())


def _whatsapp_href(phone: str) -> str:
    digits = _digits(phone)
    if not digits:
        return ""
    if not digits.startswith("55"):
        digits = "55" + digits.lstrip("0")
    return f"https://wa.me/{digits}"


def _tel_href(phone: str) -> str:
    digits = _digits(phone)
    if not digits:
        return ""
    return f"tel:+{digits}"


def _maps_targets(
    *,
    name: str,
    city: str,
    address: str,
    maps_url: str = "",
) -> tuple[str, str]:
    href = str(maps_url or "").strip()
    query = " ".join(part for part in (address, name, city) if str(part or "").strip()).strip()
    if not query and href:
        query = href
    if not query:
        return ("", "")
    embed = f"https://www.google.com/maps?q={quote_plus(query)}&output=embed&z=15"
    if not href:
        href = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
    return href, embed


def _extract_name(business: dict, facts: dict) -> str:
    name = (
        business.get("name") or business.get("business_name")
        or business.get("nome") or facts.get("business_name")
        or facts.get("name") or facts.get("nome")
    )
    if not name or not str(name).strip():
        raise DadosIncompletosError(
            "briefing.business.name ausente",
            ["business.name"],
        )
    return str(name).strip()


def _extract_city(business: dict, facts: dict) -> str:
    city = (
        business.get("city") or business.get("cidade")
        or facts.get("city") or facts.get("cidade")
    )
    if not city or not str(city).strip():
        raise DadosIncompletosError(
            "briefing.business.city ausente",
            ["business.city"],
        )
    return str(city).strip()


def _extract_segment(business: dict, facts: dict) -> str:
    segment = (
        business.get("segment") or business.get("segmento")
        or facts.get("segment") or facts.get("segmento")
    )
    if not segment or not str(segment).strip():
        raise DadosIncompletosError(
            "briefing.business.segment ausente",
            ["business.segment"],
        )
    return str(segment).strip()


def _extract_contact(business: dict, facts: dict) -> str:
    phone = (
        business.get("whatsapp") or business.get("phone")
        or facts.get("whatsapp") or facts.get("phone")
    )
    if not phone or not str(phone).strip():
        raise DadosIncompletosError(
            "briefing precisa de pelo menos um contato (whatsapp ou phone)",
            ["business.whatsapp"],
        )
    return str(phone).strip()


def build_factual_contact_data(facts: dict[str, Any]) -> dict[str, Any]:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}

    name = _extract_name(business, facts)
    city = _extract_city(business, facts)
    segment = _extract_segment(business, facts)
    raw_phone = _extract_contact(business, facts)

    phone_digits = _digits(raw_phone)
    whatsapp_href = _whatsapp_href(raw_phone)
    tel_href = _tel_href(raw_phone)

    raw_address = str(
        business.get("address") or business.get("endereco")
        or facts.get("address") or facts.get("endereco") or ""
    ).strip()
    raw_maps_url = str(
        business.get("maps_url") or business.get("map_url")
        or facts.get("maps_url") or ""
    ).strip()
    price_range = str(
        business.get("price_range") or facts.get("price_range") or ""
    ).strip()

    maps_href, maps_embed_src = _maps_targets(
        name=name, city=city, address=raw_address, maps_url=raw_maps_url,
    )

    location_kicker = f"Presença local em {city}"
    location_title = f"Atendimento em {city}"
    location_intro = f"Endereço e WhatsApp aparecem juntos para facilitar contato em {city}."
    location_cta_title = f"Fale com {name} pelo WhatsApp"
    location_cta_body = "Contato e endereço ficam juntos para facilitar a decisão."
    location_cta_primary = "Falar no WhatsApp"

    if raw_phone and raw_address:
        footer_tagline = (
            f"{name} em {city}: contato direto pelo WhatsApp, "
            f"endereço em {raw_address[:60]} e horário de funcionamento."
        )
    elif raw_phone:
        footer_tagline = (
            f"{name} em {city}: contato direto pelo WhatsApp "
            f"e informações úteis para quem está na região."
        )
    elif raw_address:
        footer_tagline = (
            f"{name} em {city}: endereço em {raw_address[:60]} "
            f"e informações úteis para quem está na região."
        )
    else:
        footer_tagline = f"{name}: {segment} em {city} com contato direto e informações claras."

    return {
        "address": raw_address,
        "mapsUrl": raw_maps_url,
        "mapsHref": maps_href,
        "mapsEmbedSrc": maps_embed_src,
        "phone": raw_phone,
        "phoneDigits": phone_digits,
        "whatsappHref": whatsapp_href,
        "telHref": tel_href,
        "price_range": price_range,
        "location_kicker": location_kicker,
        "location_title": location_title,
        "location_intro": location_intro,
        "location_cta_title": location_cta_title,
        "location_cta_body": location_cta_body,
        "location_cta_primary": location_cta_primary,
        "footer_tagline": footer_tagline,
    }


def merge_factual_into_sitecopy(
    sitecopy: dict[str, Any], factual: dict[str, Any],
) -> dict[str, Any]:
    factual_phone = factual.get("phoneDigits") or factual.get("phone_digits") or ""
    merged = dict(sitecopy)
    if factual_phone:
        merged["phone_digits"] = factual_phone
    if factual.get("phoneDigits"):
        merged["phoneDigits"] = factual["phoneDigits"]
    for key in ("whatsappHref", "telHref", "mapsHref", "mapsEmbedSrc", "mapsUrl"):
        if factual.get(key):
            merged[key] = factual[key]
    for key in (
        "location_kicker", "location_title", "location_cta_title",
        "location_cta_body", "location_cta_primary",
    ):
        if factual.get(key):
            merged[key] = factual[key]
    if factual.get("address"):
        merged.setdefault("address", factual["address"])
    if factual.get("price_range"):
        merged.setdefault("price_range", factual["price_range"])
    if factual.get("footer_tagline"):
        merged["footer_tagline"] = factual["footer_tagline"]
    return merged