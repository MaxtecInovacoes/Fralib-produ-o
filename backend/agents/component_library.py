"""Deterministic premium section components for generated sites.

These components are the guardrail between creative intent and final HTML.
The LLM can propose composition, but the final hero can be normalized into a
pre-validated component with known spacing, contrast, motion hooks and mobile
behavior.
"""


import hashlib
import html
import re
from typing import Any


HERO_COMPONENT_BY_ARCHETYPE = {
    "BOLD_ENERGY": ["HeroBoldCampaign01", "HeroBoldPoster02", "HeroBoldSplit03"],
    "LUXURY_ELITE": ["HeroLuxuryImageLed01", "HeroLuxuryOverlay02", "HeroLuxuryGallery03"],
    "ZEN_PURE": ["HeroZenCalmCollage01", "HeroZenImageFloat02", "HeroZenEditorial03"],
    "TRUST_ELITE": ["HeroTrustSplitProof01", "HeroTrustAuthority02", "HeroTrustEditorial03"],
    "MODERN_TECH": ["HeroTechDepthGrid01", "HeroTechInterface02", "HeroTechSignal03"],
}


def build_component_contracts(facts: dict[str, Any]) -> dict[str, Any]:
    archetype = _archetype_from_facts(facts)
    hero_id = _hero_component_id(archetype, facts)
    return {
        "version": 1,
        "hero": {
            "component_id": hero_id,
            "archetype": archetype,
            "locked": True,
            "slots_required": [
                "headline",
                "subheadline",
                "primary_cta",
                "proof_chip",
                "dominant_visual",
                "motion_hooks",
            ],
            "visual_guarantees": [
                "responsive 16:9 media surface",
                "data-parallax or deterministic depth layer",
                "Ken Burns-compatible media class",
                "CTA hover microinteraction",
                "readable contrast by archetype",
                "mobile-first stacking",
            ],
        },
        "footer": {
            "component_id": "FooterLocalTrust01",
            "locked": True,
            "visual_guarantees": ["navigation", "contact", "address_or_city", "trust_note"],
        },
    }


def render_deterministic_hero(facts: dict[str, Any]) -> str:
    contract = build_component_contracts(facts)["hero"]
    component_id = contract["component_id"]
    archetype = contract["archetype"]
    name = _first(facts, "business_name", "nome", default="Negócio local")
    city = _first(facts, "cidade", "city", default="")
    segment = _first(facts, "segmento", "nicho", default="negócio local")
    address = _first(facts, "address", "endereco", default="")
    phone = _first(facts, "phone", "telefone", default="")
    rating = str(_first(facts, "rating", "reviews_rating", default="")).strip()
    reviews = str(_first(facts, "reviews_count", "total_avaliacoes", default="")).strip()
    photo = _first_photo(facts)
    cta_href = _whatsapp_link(phone) or "#contato"
    headline = _headline_for(archetype, name, segment, city)
    subheadline = _subheadline_for(archetype, segment, city, address)
    proof = _proof_label(rating, reviews, city)
    surface = _media_surface(photo, name, segment, archetype)
    return f"""
<!-- SECTION:hero -->
<section id="hero" class="fralib-deterministic-hero fralib-hero-{_slug(archetype)} fralib-hero-component-{_slug(component_id)}" data-component-id="{_e(component_id)}" data-palette-id="{_e(_palette_id(facts))}" data-reveal>
  <div class="fralib-hero-bg" data-parallax aria-hidden="true"></div>
  <nav class="fralib-hero-nav" aria-label="Topo">
    <strong>{_e(name)}</strong>
    <span>{_e(city or segment)}</span>
  </nav>
  <div class="fralib-hero-shell">
    <div class="fralib-hero-copy">
      <p class="fralib-hero-kicker">{_e(_kicker_for(archetype, city, segment))}</p>
      <h1 class="fralib-hero-title mask-reveal">{headline}</h1>
      <p class="fralib-hero-subtitle" data-reveal>{_e(subheadline)}</p>
      <div class="fralib-hero-actions" data-reveal>
        <a class="fralib-hero-primary magnetic-btn" href="{_e(cta_href)}">{_e(_cta_for(phone))}</a>
        <a class="fralib-hero-secondary" href="#localizacao">Ver localização</a>
      </div>
      <span class="fralib-proof-chip fralib-hero-proof" data-reveal>{_e(proof)}</span>
    </div>
    {surface}
  </div>
</section>
<!-- /SECTION:hero -->
""".strip()


def replace_hero_with_component(body: str, facts: dict[str, Any]) -> str:
    hero = render_deterministic_hero(facts)
    match = re.search(r"(?is)<!--\s*SECTION:hero\s*-->.*?<!--\s*/SECTION:hero\s*-->", body or "")
    if match:
        return body[: match.start()] + hero + body[match.end() :]
    match = re.search(r"(?is)<section\b[^>]*(?:id|data-section)=['\"]?hero['\"]?[^>]*>.*?</section>", body or "")
    if match:
        return body[: match.start()] + hero + body[match.end() :]
    match = re.search(r"(?is)<section\b.*?</section>", body or "")
    if match:
        return body[: match.start()] + hero + body[match.end() :]
    return hero + "\n" + (body or "")


def _headline_for(archetype: str, name: str, segment: str, city: str) -> str:
    name_safe = _e(name)
    segment_safe = _e(_segment_label(segment))
    city_safe = _e(city)
    if archetype == "BOLD_ENERGY":
        return f'<span>{name_safe}</span><span class="fralib-outline-word">FORTE</span>'
    if archetype == "ZEN_PURE":
        return f'<span>{name_safe}</span><span class="fralib-accent-word">com calma</span>'
    if archetype == "LUXURY_ELITE":
        return f'<span>{name_safe}</span><span class="fralib-accent-word">em {city_safe}</span>' if city else f"<span>{name_safe}</span>"
    if archetype == "MODERN_TECH":
        return f'<span>{name_safe}</span><span class="fralib-accent-word">precisão digital</span>'
    return f'<span>{name_safe}</span><span class="fralib-accent-word">{segment_safe}</span>'


def _subheadline_for(archetype: str, segment: str, city: str, address: str) -> str:
    place = city or address or "sua região"
    segment_label = _segment_label(segment)
    if archetype == "BOLD_ENERGY":
        return f"Presença intensa, prova local e chamada direta para quem busca {segment_label} em {place}."
    if archetype == "ZEN_PURE":
        return f"Uma primeira leitura leve, clara e confiável para decidir sobre {segment_label} em {place}."
    if archetype == "LUXURY_ELITE":
        return f"Atmosfera, detalhe e endereço visível para apresentar {segment_label} com presença em {place}."
    if archetype == "MODERN_TECH":
        return f"Clareza, ritmo e confiança local para transformar interesse em contato qualificado em {place}."
    return f"Informação essencial, prova pública e contato fácil para escolher {segment_label} em {place}."


def _media_surface(photo: str, name: str, segment: str, archetype: str) -> str:
    if photo:
        return f"""
    <figure class="fralib-hero-media" data-reveal>
      <img src="{_e(photo)}" alt="{_e(name)}: imagem editorial relacionada a {_e(segment)}" loading="eager" decoding="async" data-parallax>
      <figcaption>Imagem editorial do contexto do negócio</figcaption>
    </figure>""".rstrip()
    return f"""
    <div class="fralib-hero-media fralib-hero-abstract" data-reveal data-parallax aria-label="Composição visual de {_e(segment)}">
      <span></span><span></span><span></span>
    </div>""".rstrip()


def _kicker_for(archetype: str, city: str, segment: str) -> str:
    if archetype == "BOLD_ENERGY":
        return f"Campanha local em {city}" if city else "Campanha local"
    if archetype == "ZEN_PURE":
        return "Decisão clara"
    if archetype == "LUXURY_ELITE":
        return "Presença local"
    if archetype == "MODERN_TECH":
        return "Sistema de confiança"
    return f"{_segment_label(segment)} verificado"


def _cta_for(phone: str) -> str:
    return "Chamar no WhatsApp" if phone else "Ver contato"


def _proof_label(rating: str, reviews: str, city: str) -> str:
    parts = []
    if rating:
        parts.append(f"{rating} avaliação")
    if reviews:
        parts.append(f"{reviews} reviews")
    if city:
        parts.append(city)
    return " · ".join(parts) if parts else "Dados públicos verificados"


def _first_photo(facts: dict[str, Any]) -> str:
    for item in facts.get("photos") or []:
        if isinstance(item, str) and item.startswith(("http://", "https://")):
            return item
        if isinstance(item, dict):
            url = item.get("url") or item.get("src") or item.get("regular")
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                return url
    return ""


def _first(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _archetype_from_facts(facts: dict[str, Any]) -> str:
    visual_dna = facts.get("visual_dna") if isinstance(facts.get("visual_dna"), dict) else {}
    archetype = visual_dna.get("archetype")
    if isinstance(archetype, dict):
        value = archetype.get("archetype") or archetype.get("id")
    else:
        value = archetype
    value = str(value or "").upper()
    if value:
        return value
    segment = _normalize(str(facts.get("segmento") or ""))
    if any(token in segment for token in ("academia", "fitness", "crossfit", "treino")):
        return "BOLD_ENERGY"
    if any(token in segment for token in ("nutric", "psicolog", "yoga", "spa", "estetica")):
        return "ZEN_PURE"
    if any(token in segment for token in ("software", "tech", "ia", "saas", "app")):
        return "MODERN_TECH"
    if any(token in segment for token in ("restaurante", "pizzaria", "cafe", "imobiliaria", "joia")):
        return "LUXURY_ELITE"
    return "TRUST_ELITE"


def _hero_component_id(archetype: str, facts: dict[str, Any]) -> str:
    pool = HERO_COMPONENT_BY_ARCHETYPE.get(archetype, HERO_COMPONENT_BY_ARCHETYPE["TRUST_ELITE"])
    visual_dna = facts.get("visual_dna") if isinstance(facts.get("visual_dna"), dict) else {}
    seed = str(visual_dna.get("visual_seed") or facts.get("visual_seed") or facts.get("business_name") or "")
    digest = hashlib.sha256(f"{archetype}:{seed}:hero".encode("utf-8")).hexdigest()
    return pool[int(digest[:8], 16) % len(pool)]


def _palette_id(facts: dict[str, Any]) -> str:
    visual_dna = facts.get("visual_dna") if isinstance(facts.get("visual_dna"), dict) else {}
    return str(visual_dna.get("palette_id") or "")


def _segment_label(segment: str) -> str:
    return re.sub(r"\s+", " ", str(segment or "negócio local")).strip()


def _whatsapp_link(phone: str) -> str:
    digits = re.sub(r"\D+", "", str(phone or ""))
    if not digits:
        return ""
    if not digits.startswith("55"):
        digits = "55" + digits
    return "https://wa.me/" + digits


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "default"


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


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)
