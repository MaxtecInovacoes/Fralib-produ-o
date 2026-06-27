"""Deterministic factual requirements contract for site generation."""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.builder_contract_utils import first_value as _first, list_value as _list

logger = logging.getLogger(__name__)


def build_requirements_contract(facts: dict[str, Any]) -> dict[str, Any]:
    """Separate publishable facts from risks before design/coding starts."""
    name = _first(facts, "business_name", "nome", default="Negócio local")
    segment = _first(facts, "segmento", "nicho", default="negócio local")
    city = _first(facts, "cidade", "city", default="")
    address = _first(facts, "address", "endereco", default="")
    phone = _first(facts, "phone", "telefone", default="")
    rating = _first(facts, "rating", "reviews_rating", default="")
    reviews_count = _first(facts, "reviews_count", "total_avaliacoes", default="")
    services = _list(_first(facts, "services", "servicos", default=[]))[:8]
    photos = _list(_first(facts, "photos", "fotos", default=[]))[:8]
    hours = _first(facts, "hours", "horarios", default={}) or {}

    confirmed = [
        _fact("business_name", name),
        _fact("segmento", segment),
        _fact("cidade", city),
        _fact("address", address),
        _fact("phone", phone),
        _fact("rating", rating),
        _fact("reviews_count", reviews_count),
    ]
    if services:
        confirmed.append({"key": "services", "value": services})
    if hours:
        confirmed.append({"key": "hours", "value": hours})
    if photos:
        confirmed.append({"key": "editorial_media_available", "value": len(photos)})

    allowed_claims = [
        f"{name} atua como {segment}" if segment else name,
        f"Atendimento em {city}" if city else "",
        f"Endereço confirmado: {address}" if address else "",
        f"Contato oficial: {phone}" if phone else "",
        f"Avaliação pública {rating}" if rating else "",
        f"{reviews_count} avaliações públicas" if reviews_count else "",
    ]
    if services:
        allowed_claims.append("Serviços/atendimentos confirmados: " + ", ".join(map(str, services[:6])))

    missing = []
    if not address:
        missing.append("address")
    if not phone:
        missing.append("phone")
        logger.debug("[requirements_contract] phone/whatsapp ausente - site será gerado sem CTA de WhatsApp")
    if not services:
        missing.append("confirmed_services")
    if not photos:
        missing.append("editorial_media")

    return {
        "version": 1,
        "objective": "gerar site local verdadeiro, claro e orientado a conversão",
        "primary_conversion_goal": "whatsapp" if phone else "map_or_contact",
        "confirmed_facts": [item for item in confirmed if item.get("value") not in (None, "", [], {})],
        "allowed_claims": [claim for claim in allowed_claims if claim],
        "forbidden_claims": [
            "não inventar serviços, equipe, estrutura, equipamentos ou especialidades",
            "não afirmar que fotos editoriais são fotos reais do endereço",
            "não criar depoimentos ou métricas que não vieram dos dados públicos",
            "não publicar horários como certeza quando vierem vazios ou incompletos",
        ],
        "missing_but_required": missing,
        "business_risk": "alto risco de inventar oferta" if not services else "risco normal",
    }


def _fact(key: str, value: Any) -> dict[str, Any]:
    return {"key": key, "value": value}
