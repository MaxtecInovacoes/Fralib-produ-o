"""Visual archetypes for FraLib experience-driven site generation."""

from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any


ARCHETYPES: dict[str, dict[str, Any]] = {
    "BOLD_ENERGY": {
        "visual_voice": "brutal, atletico, cinematografico, confiante, sem polidez corporativa",
        "color_theory": "preto profundo, vermelho eletrico dominante em CTAs e cortes, branco quente para display",
        "typography": {
            "heading_scale": "condensed_impact_900",
            "heading_trait": "uppercase condensado, italico/obliquo em palavras de impacto, outline text como camada secundaria",
            "body_trait": "compacto, tenso, alto contraste, sem paragrafo longo",
        },
        "composition_laws": [
            "hero dark full-bleed com foto/texture ocupando o fundo e overlay dramatico",
            "headline display 84px+ no desktop com palavra solida + palavra outline atras ou abaixo",
            "usar diagonais, crop agressivo, z-index, negative margins e cards pretos flutuantes",
            "vermelho vivo em CTAs, highlights e barras curtas; nunca usar azul/corporativo",
            "uma secao manifesto com titulo quebrado em linhas curtas e imagem lateral com sombra profunda",
            "CTA com glow vermelho e estado hover fisico",
        ],
        "media_query_modifiers": [
            "dark cinematic gym photography",
            "red accent lighting",
            "high contrast athlete training",
            "moody professional photography",
            "dynamic action crop",
        ],
        "cta_policy": "botao principal com glow neon e linguagem direta",
        "section_disruption": "full-bleed dark impact band",
    },
    "TRUST_ELITE": {
        "visual_voice": "autoridade, precisao, confianca, premium discreto",
        "color_theory": "marinho, cinza profundo, off-white e acento sofisticado",
        "typography": {
            "heading_scale": "editorial_large",
            "heading_trait": "serif ou grotesk elegante",
            "body_trait": "leitura calma e objetiva",
        },
        "composition_laws": [
            "grid assimetrico com muita margem",
            "hierarquia tipografica clara e institucional",
            "prova social em bloco editorial, nao cards genericos",
            "CTA sobrio com sombra refinada",
        ],
        "media_query_modifiers": [
            "premium professional office",
            "editorial photography",
            "trust elegant",
            "minimal architecture",
        ],
        "cta_policy": "botao contido, alto contraste e acabamento premium",
        "section_disruption": "authority proof band with editorial contrast",
    },
    "ZEN_PURE": {
        "visual_voice": "calmo, humano, mineral, saude premium com presenca editorial",
        "color_theory": "teal mineral/eucalipto comprometido, coral humano em CTAs, off-white apenas como superficie controlada; nunca bege/creme como fundo padrao",
        "typography": {
            "heading_scale": "soft_display",
            "heading_trait": "display elegante sem agressividade",
            "body_trait": "leve, amplo e acolhedor",
        },
        "composition_laws": [
            "usar espaco negativo generoso sem virar pagina vazia ou hospitalar",
            "alternar full-bleed suave com blocos estreitos de leitura",
            "hero assimetrico com midia/camada mineral dominante e prova local perto da dobra",
            "camadas de teal/eucalipto, coral e luz natural em vez de cards brancos repetidos",
            "CTA com cor humana e linguagem de cuidado",
        ],
        "media_query_modifiers": [
            "wellness",
            "mineral teal editorial wellness",
            "calm natural light human care",
            "premium editorial photography",
            "soft organic",
        ],
        "cta_policy": "botao acolhedor com brilho suave e bordas organicas",
        "section_disruption": "soft organic image-led section",
    },
    "MODERN_TECH": {
        "visual_voice": "futurista, rapido, limpo, inteligente",
        "color_theory": "neon controlado, glassmorphism e gradientes frios",
        "typography": {
            "heading_scale": "geometric_display",
            "heading_trait": "sans geometrica com contraste forte",
            "body_trait": "preciso e escaneavel",
        },
        "composition_laws": [
            "usar glassmorphism e camadas translucidas",
            "hero com profundidade digital e textura de grid",
            "microinteracoes aparentes em cards e CTAs",
            "quebrar grid com painel flutuante",
        ],
        "media_query_modifiers": [
            "modern technology",
            "glassmorphism",
            "neon gradient",
            "clean interface",
        ],
        "cta_policy": "botao com glow azul/roxo e borda translucida",
        "section_disruption": "glass panel over gradient mesh",
    },
    "LUXURY_ELITE": {
        "visual_voice": "exclusivo, editorial, refinado, desejo silencioso",
        "color_theory": "preto/off-white, dourado discreto ou acento profundo",
        "typography": {
            "heading_scale": "luxury_editorial",
            "heading_trait": "serif fina ou contraste extremo",
            "body_trait": "poucas palavras e muito respiro",
        },
        "composition_laws": [
            "usar imagens full-bleed e composicao editorial",
            "reduzir elementos decorativos obvios",
            "usar contraste de escala entre titulo e corpo",
            "CTA raro, preciso e sofisticado",
        ],
        "media_query_modifiers": [
            "luxury minimal",
            "dramatic light",
            "refined texture",
            "editorial photography",
        ],
        "cta_policy": "botao minimal com halo refinado",
        "section_disruption": "full-bleed luxury editorial image",
    },
}


SEGMENT_ARCHETYPE: dict[str, str] = {
    "academia": "BOLD_ENERGY",
    "crossfit": "BOLD_ENERGY",
    "personal": "BOLD_ENERGY",
    "evento": "BOLD_ENERGY",
    "gaming": "BOLD_ENERGY",
    "advogado": "TRUST_ELITE",
    "advocacia": "TRUST_ELITE",
    "contador": "TRUST_ELITE",
    "contabilidade": "TRUST_ELITE",
    "imobiliaria": "TRUST_ELITE",
    "clinica": "TRUST_ELITE",
    "saude": "TRUST_ELITE",
    "dentista": "TRUST_ELITE",
    "odontologia": "TRUST_ELITE",
    "odonto": "TRUST_ELITE",
    "farmacia": "TRUST_ELITE",
    "otica": "TRUST_ELITE",
    "optica": "TRUST_ELITE",
    "oftalmologia": "TRUST_ELITE",
    "nutricionista": "ZEN_PURE",
    "psicologia": "ZEN_PURE",
    "psicologo": "ZEN_PURE",
    "spa": "ZEN_PURE",
    "yoga": "ZEN_PURE",
    "pilates": "ZEN_PURE",
    "estetica": "ZEN_PURE",
    "saas": "MODERN_TECH",
    "ia": "MODERN_TECH",
    "agencia": "MODERN_TECH",
    "software": "MODERN_TECH",
    "joias": "LUXURY_ELITE",
    "luxo": "LUXURY_ELITE",
    "gastronomia": "LUXURY_ELITE",
    "restaurante": "LUXURY_ELITE",
    "pizzaria": "LUXURY_ELITE",
    "cafe": "LUXURY_ELITE",
    "cafeteria": "LUXURY_ELITE",
    "bistro": "LUXURY_ELITE",
    "hamburgueria": "LUXURY_ELITE",
    "bar": "LUXURY_ELITE",
}


def normalize_segment(segmento: str) -> str:
    text = unicodedata.normalize("NFKD", (segmento or "").lower().strip())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def select_archetype(segmento: str, nome: str = "", dados_lead: dict | None = None) -> dict[str, Any]:
    """Return the visual archetype for a segment without using LLM."""
    seg = normalize_segment(segmento)
    haystack = normalize_segment(" ".join(str(v) for v in (seg, nome or "") if v))
    for key, archetype_id in SEGMENT_ARCHETYPE.items():
        normalized_key = normalize_segment(key)
        pattern = rf"(?:^|_){re.escape(normalized_key)}(?:_|$)"
        if re.search(pattern, haystack) or re.search(pattern, seg):
            data = deepcopy(ARCHETYPES[archetype_id])
            data["archetype"] = archetype_id
            return data
    data = deepcopy(ARCHETYPES["TRUST_ELITE"])
    data["archetype"] = "TRUST_ELITE"
    return data
