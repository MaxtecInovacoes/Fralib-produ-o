"""Shared Phase 6 visual contract helpers."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any, Literal


HeroMediaType = Literal["video", "image"]

VIDEO_HERO_MATRIX: dict[str, HeroMediaType] = {
    "academia": "video",
    "crossfit": "video",
    "funcional": "video",
    "restaurante": "video",
    "pizzaria": "video",
    "cafe": "video",
    "barbearia": "video",
    "salao_beleza": "video",
    "estetica": "video",
    "spa": "video",
    "pet_shop": "video",
    "padaria": "video",
    "confeitaria": "video",
    "loja_roupas": "video",
    "nutricionista_esportiva": "video",
    "nutricao_esportiva": "video",
    "nutricionista_infantil": "image",
    "nutricionista_clinica": "image",
    "clinica": "image",
    "dentista": "image",
    "advocacia": "image",
    "imobiliaria": "image",
    "escola": "image",
    "curso": "image",
    "fotografia": "image",
    "arquitetura": "image",
}

ARCHETYPE_VIDEO_OVERRIDE: dict[str, HeroMediaType] = {
    "BOLD_ENERGY": "video",
    "ZEN_PURE": "image",
    "LUXURY_ELITE": "image",
    "ENERGY_INFRA": "video",
    "TRUST_ELITE": "image",
}


def get_first(obj: Any, *names: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        for name in names:
            value = obj.get(name)
            if value not in (None, "", [], {}):
                return value
        return default
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def phase6_slug_token(value: Any) -> str:
    """Normalize a value to a phase-6 token (underscore-joined)."""
    from backend.utils.slug import slugify  # — M4 DRY
    return slugify(value, sep="_", collapse_sep=True)


def phase6_video_asset(facts: Any) -> dict[str, str]:
    candidates: list[Any] = []
    raw = get_first(facts, "videos", default=[])
    if isinstance(raw, list):
        candidates.extend(raw)
    media = get_first(facts, "media", default={})
    if isinstance(media, Mapping) and isinstance(media.get("videos"), list):
        candidates.extend(media["videos"])
    for item in candidates:
        if isinstance(item, str):
            url = item
            poster = ""
        elif isinstance(item, Mapping):
            url = str(item.get("url") or item.get("src") or item.get("video_url") or "")
            poster = str(item.get("thumbnail") or item.get("poster") or item.get("image") or "")
        else:
            continue
        if url.startswith(("http://", "https://")):
            return {"url": url, "poster": poster if poster.startswith(("http://", "https://")) else ""}
    return {}


def phase6_image_asset(facts: Any) -> str:
    sources: list[Any] = []
    media = get_first(facts, "media", default={})
    if isinstance(media, Mapping):
        for key in ("photos", "images"):
            if isinstance(media.get(key), list):
                sources.extend(media[key])
    raw = get_first(facts, "photos", "images", default=[])
    if isinstance(raw, list):
        sources.extend(raw)
    for item in sources:
        url = item if isinstance(item, str) else item.get("url") if isinstance(item, Mapping) else ""
        if str(url).startswith(("http://", "https://")):
            return str(url)
    return ""


def phase6_business_segment(facts: Any) -> str:
    business = get_first(facts, "business", default={})
    if not isinstance(business, Mapping):
        business = {}
    return str(
        business.get("segment")
        or business.get("segmento")
        or get_first(facts, "segmento", "segment", "nicho", default="")
        or ""
    ).strip()


def phase6_business_subniche(facts: Any) -> str:
    business = get_first(facts, "business", default={})
    if not isinstance(business, Mapping):
        business = {}
    return str(
        business.get("subniche")
        or business.get("sub_nicho")
        or get_first(facts, "subniche", "sub_nicho", default="")
        or ""
    ).strip()


def phase6_design_archetype(facts: Any) -> str:
    for key in ("design", "visual_dna", "visual_contract"):
        container = get_first(facts, key, default={})
        if not isinstance(container, Mapping):
            continue
        raw = container.get("archetype") or container.get("id") or container.get("name")
        if isinstance(raw, Mapping):
            raw = raw.get("archetype") or raw.get("id") or raw.get("name")
        normalized = phase6_slug_token(raw).upper()
        if normalized:
            return normalized
    segment = phase6_slug_token(phase6_business_segment(facts))
    if any(token in segment for token in ("energia", "solar", "eletrica", "fotovoltaica", "infraestrutura")):
        return "ENERGY_INFRA"
    if any(token in segment for token in ("academia", "fitness", "crossfit", "treino")):
        return "BOLD_ENERGY"
    if any(token in segment for token in ("nutric", "psicolog", "yoga", "spa", "estetica")):
        return "ZEN_PURE"
    if any(token in segment for token in ("restaurante", "pizzaria", "cafe", "gastronomia")):
        return "LUXURY_ELITE"
    return "TRUST_ELITE"


def phase6_should_use_video_hero(facts: Any, *, require_video_asset: bool = False) -> bool:
    if require_video_asset and not phase6_video_asset(facts):
        return False
    segment = phase6_slug_token(phase6_business_segment(facts))
    subniche = phase6_slug_token(phase6_business_subniche(facts))
    combined = "_".join(token for token in (segment, subniche) if token)
    for key in (combined, subniche, segment):
        if key in VIDEO_HERO_MATRIX:
            return VIDEO_HERO_MATRIX[key] == "video"
    archetype = phase6_design_archetype(facts)
    return ARCHETYPE_VIDEO_OVERRIDE.get(archetype, "image") == "video"


def sanitize_keyword_term(value: Any, *, limit: int = 60) -> str:
    clean = " ".join(str(value or "").split()).strip(" -–—:;,.")
    if not clean:
        return ""
    low = phase6_slug_token(clean).replace("_", " ")
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
    if len(clean) > limit:
        return ""
    if not any(ch.isalpha() for ch in clean):
        return ""
    return clean
