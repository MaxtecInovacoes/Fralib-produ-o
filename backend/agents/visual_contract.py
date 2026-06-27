"""Visual contract generated before renderer execution."""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.builder_contract_utils import archetype_id_from_visual_dna as _archetype_id

logger = logging.getLogger(__name__)


def build_visual_contract(facts: dict[str, Any]) -> dict[str, Any]:
    visual_dna = facts.get("visual_dna") if isinstance(facts.get("visual_dna"), dict) else {}
    archetype = _archetype_id(visual_dna) or _archetype_from_segment(str(facts.get("segmento") or ""))
    has_address = bool(facts.get("address") or facts.get("endereco"))
    has_phone = bool(facts.get("phone") or facts.get("telefone"))
    if not has_phone:
        logger.debug("[visual_contract] phone/whatsapp ausente - hero usara CTA de contato generico")
    has_reviews = bool(facts.get("rating") or facts.get("reviews_rating") or facts.get("reviews_count"))
    has_photos = bool(facts.get("photos") or facts.get("fotos"))

    return {
        "version": 1,
        "archetype": archetype,
        "acceptance_criteria": {
            "minimum_sections": 7,
            "required_sections": [
                "hero",
                "trust_or_proof",
                "decision_content",
                "media_story",
                "location",
                "faq",
                "footer",
            ],
            "mobile": ["no_horizontal_overflow", "cta_visible", "headline_not_clipped"],
            "truth": ["no_lorem", "no_fake_services", "no_fake_reviews", "no_internal_policy_leak"],
        },
        "hero": {
            "required": [
                "headline",
                "subheadline",
                "primary_cta" if has_phone else "clear_contact_cta",
                "proof_chip" if has_reviews else "local_context_chip",
                "media_16_9_or_depth_layer",
                "motion_hook",
            ],
            "forbidden": [
                "generic_centered_block",
                "mobile_overflow",
                "unreadable_outline",
                "hidden_reveal_without_fallback",
            ],
        },
        "sections": {
            "required": {
                "decision_content": "educa a escolha com critérios reais do nicho",
                "media_story": "usa imagens como narrativa editorial sem chamar de foto real",
                "location": "mostra mapa único e endereço confirmado" if has_address else "mostra cidade/contato sem mapa falso",
                "faq": "remove objeções práticas antes do contato",
            },
            "media_ratio": "16:9",
            "backgrounds": "cada seção deve ter superfície/fundo intencional, não pilha branca genérica",
        },
        "footer": {
            "required": ["brand", "navigation", "contact", "address_or_city", "hours_or_confirmation_note", "trust_note"],
            "forbidden": ["unreadable_contrast", "generic_black_fallback", "post_footer_gallery"],
        },
        "media": {
            "available": has_photos,
            "ratio": "16:9",
            "policy": "editorial support only unless explicitly marked real venue media",
        },
        "location": {
            "requires_exact_map": has_address,
            "single_map_only": True,
            "zoom": 18,
        },
    }


def _archetype_from_segment(segment: str) -> str:
    text = _normalize(segment)
    if any(token in text for token in ("academia", "fitness", "crossfit", "treino")):
        return "BOLD_ENERGY"
    if any(token in text for token in ("nutric", "psicolog", "yoga", "spa", "estetica")):
        return "ZEN_PURE"
    if any(token in text for token in ("software", "tech", "ia", "app", "saas")):
        return "MODERN_TECH"
    if any(token in text for token in ("restaurante", "pizzaria", "cafe", "imobiliaria", "joia")):
        return "LUXURY_ELITE"
    return "TRUST_ELITE"


def _normalize(value: str) -> str:
    return (
        value.lower()
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
