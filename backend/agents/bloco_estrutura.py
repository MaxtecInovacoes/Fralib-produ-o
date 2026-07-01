"""Bloco 1 — Estrutura + Layout.
LLM call focada em definir layout_type, direcao criativa e lista de secoes.
Retorno: Markdown parseado via markdown_prd_parser.

Fail-fast: parse_bloco1_with_fallback tenta JSON→Markdown→JSON,
mas se resultar vazio, lança EstruturaInvalidaError.
"""

import re as _re
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.pipeline_exceptions import EstruturaInvalidaError
from llm_direct import call_claude
from markdown_prd_parser import parse_bloco1_with_fallback
from prompts_arquiteto import (
    SYSTEM_DESIGN_DIRECTOR,
    _buscar_google_suggest,
    _garantir_secoes_obrigatorias,
)
from visual_archetypes import archetype_prompt


def _montar_prompt_bloco1(
    nome: str,
    cidade: str,
    segmento: str,
    caio_tier: str,
    caio_score: int,
    rating: float,
    total_av: int,
    inteligencia: dict,
    sub_nicho_ctx: str,
    design_ctx: str,
    craft_ctx: str,
    design_dict: dict,
    nicho_ref: str,
    variacao_ref: str,
) -> str:
    """Monta prompt compacto para Bloco 1 — estrutura + layout."""

    suggest_terms = _buscar_google_suggest(segmento, cidade)
    suggest_fmt = ", ".join(suggest_terms[:5]) if suggest_terms else ""

    intel = inteligencia or {}
    _intel_lines = []
    if intel.get("concorrencia", {}).get("padroes_mercado"):
        pm = intel["concorrencia"]["padroes_mercado"]
        _intel_lines.append(f"Tema dominante: {pm.get('tema_dominante', 'N/A')}")
        _intel_lines.append(
            f"CTAs encontrados: {', '.join(pm.get('ctas_encontrados', [])[:3])}"
        )
    if intel.get("reviews_insights", {}).get("palavras_frequentes"):
        _intel_lines.append(
            f"Palavras frequentes: {', '.join(intel['reviews_insights']['palavras_frequentes'][:6])}"
        )
    if intel.get("servicos_reais"):
        _intel_lines.append(
            f"Servicos confirmados: {', '.join(s['titulo'] for s in intel['servicos_reais'][:4])}"
        )
    _intel_ctx = "\n".join(_intel_lines)

    tokens = design_dict.get("tokens", {})

    layout_line = "layout_type: (brutalist/editorial/organic/corporate/minimal)"
    academia_rules = (
        "\nACADEMIA/FITNESS:\n"
        "- Escolha a direcao pelo lead e pelos dados, sem forcar dark/red/athletic em todo caso.\n"
        "- Se nao houver servicos confirmados, nao crie secao visual de servicos; integre uma nota curta no contato/sobre.\n"
        "- Movimento deve enriquecer o layout escolhido, nao trocar a identidade por template agressivo.\n"
    )

    return f"""BUSINESS: {nome} | CITY: {cidade} | SEGMENT: {segmento}
TIER: {caio_tier} (score={caio_score}) | RATING: {rating}/5 ({total_av} avaliacoes)

{_intel_ctx}
{sub_nicho_ctx}

{design_ctx}
{craft_ctx}
{nicho_ref}
{variacao_ref}

CSS TOKENS:
  --bg: {tokens.get("--bg", "")}  --surface: {tokens.get("--surface", "")}
  --fg: {tokens.get("--fg", "")}  --muted: {tokens.get("--muted", "")}
  --border: {tokens.get("--border", "")}  --accent: {tokens.get("--accent", "")}
TYPOGRAPHY: heading={design_dict.get("font_heading", "Inter")} body={design_dict.get("font_body", "Inter")}

Google Suggest: {suggest_fmt}

{archetype_prompt(segmento, nome)}

Return MARKDOWN in this exact format:

business_name: {nome}
{layout_line}

## INSTRUCAO CRIATIVA
Write a compact but strong brief with 5 named blocks:
BRAND DNA: emotional energy, local positioning, and promise WITHOUT inventing facts.
COMPOSICAO: editorial rhythm, typographic scale, asymmetry, density, and how to avoid predictable layout.
MOTION: Lenis scroll, mask reveal, line reveal, 80-120ms stagger, light parallax, power3.out easing, 0.6-0.95s duration.
MIDIA: how to use received photos as visual narrative without claiming they show the real space when unproven.
ANTI-PATTERNS: 5 specific prohibitions to avoid AI-template feel.
End with CSS VARS CONFIRMADAS and cite the received tokens.

## SECOES
Choose 5-8 sections. REQUIRED: hero, sobre, contato.
SERVICOS: include only when real services are confirmed; otherwise, do not use a fallback banner.
OPTIONAL (2-5): sobre, depoimentos, faq, localizacao, numeros, galeria, planos, equipe, cta-final, antes-depois, parceiros.
Format: - nome_secao | layout_type

AVAILABLE LAYOUTS:
- hero: hero-split, hero-center, hero-fullscreen, hero-diagonal, hero-video
- sobre: sobre-timeline, sobre-grid, sobre-cards, sobre-story
- servicos: services-cards, services-accordion, services-grid-icons, services-list, services-bento
- depoimentos: reviews-masonry, reviews-carousel, reviews-grid, reviews-spotlight
- faq: faq-accordion, faq-two-col, faq-minimal
- localizacao: location-split, location-full, location-card
- contato: contact-minimal, contact-split, contact-card
- footer: footer-3col, footer-2col, footer-centered, footer-darkbar
- numeros: stats-horizontal, stats-cards, stats-big
- galeria: gallery-masonry, gallery-grid, gallery-carousel

RULES:
- Real reviews and rating > 4.0? Include depoimentos
- 4+ photos? Include galeria
- Has hours? Include localizacao
- Has FAQ? Include faq
- NEVER repeat layout_type in consecutive sections
- Variable order - not always hero->sobre->servicos
- Footer: treat as brand closure with real contact/address/hours; never detached footer
- No visible prices
- WhatsApp CTA is mandatory in every section
- All customer-facing copy MUST be in Brazilian Portuguese (pt-BR)

NICHO {segmento}:
  Restaurante/Bar: hero-fullscreen + foto, depoimentos ANTES de servicos se rating>4.5
  Saude: hero-split + foto, sobre LOGO apos hero
  Academia: variar hero-fullscreen/diagonal/video. NAO sempre fullscreen.
  Academia: evitar visual bege/clean/WordPress; preferir athletic editorial, contraste alto, display condensado, imagem dominante.
  Sem servicos confirmados: nao usar banner de fallback de servicos; resolva no contato.
  Salao/Estetica: hero-diagonal + galeria antes/depois
  Servico urgente (encanador): contato ANTES de servicos
{academia_rules}

MARKDOWN ONLY. No JSON. No code blocks."""


def _is_academia(segmento: str) -> bool:
    return (segmento or "").strip().lower() in {"academia", "fitness"}


def _force_academia_direction(dados: dict, segmento: str) -> dict:
    """Keep facts safe without forcing a visual identity for academia."""
    if not _is_academia(segmento):
        return dados

    instrucao = dados.get("instrucao_criativa_para_dev") or ""
    if "ACADEMIA/FITNESS FACTUAL DIRECTION" not in instrucao:
        dados["instrucao_criativa_para_dev"] = (
            instrucao.rstrip()
            + "\nACADEMIA/FITNESS FACTUAL DIRECTION: preservar fatos, nao inventar modalidades, "
            "nao transformar atributos operacionais em servicos e adicionar motion sobre o layout escolhido."
        ).strip()
    return dados


def executar_bloco_estrutura(
    nome: str,
    cidade: str,
    segmento: str,
    caio_tier: str,
    caio_score: int,
    rating: float,
    total_av: int,
    inteligencia: dict,
    sub_nicho_ctx: str,
    design_ctx: str,
    craft_ctx: str,
    design_dict: dict,
    nicho_ref: str,
    variacao_ref: str,
) -> dict:
    """Executa Bloco 1 (estrutura + layout) e retorna dict parseado.

    Returns:
        dict com layout_type, instrucao_criativa_para_dev, sections (lista)
    """
    prompt = _montar_prompt_bloco1(
        nome,
        cidade,
        segmento,
        caio_tier,
        caio_score,
        rating,
        total_av,
        inteligencia,
        sub_nicho_ctx,
        design_ctx,
        craft_ctx,
        design_dict,
        nicho_ref,
        variacao_ref,
    )

    print(f"[BlocoEstrutura] Chamando LLM (estrutura) para {nome}...")
    try:
        resp = call_claude(
            system=SYSTEM_DESIGN_DIRECTOR,
            user=prompt,
            model="sonnet",
            max_tokens=2000,
            temperature=0.5,
            agent_name="arquiteto_mestre",
        )
    except Exception as e:
        raise EstruturaInvalidaError(
            f"Estrutura LLM failed for {nome} in {cidade}.",
            context={
                "nome": nome,
                "cidade": cidade,
                "segmento": segmento,
                "erro": str(e),
                "acao": "Corrigir LLM/conectividade; nao usar modelo alternativo automatico",
            },
        ) from e

    resp = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", resp)
    dados = parse_bloco1_with_fallback(resp)

    if dados and dados.get("sections"):
        sections = _garantir_secoes_obrigatorias(dados.get("sections", []))
        dados["sections"] = sections
        dados = _force_academia_direction(dados, segmento)
        layout_type = dados.get("layout_type", "corporate")
        if segmento and segmento.lower() in ("academia", "fitness") and layout_type in ("corporate", "minimal"):
            layout_type = "editorial"
        instrucao = dados.get(
            "instrucao_criativa_para_dev", f"Site premium para {nome} em {cidade}."
        )
        print(f"[BlocoEstrutura] OK: {len(sections)} secoes, layout={layout_type}")
        return {
            "layout_type": layout_type,
            "instrucao_criativa_para_dev": instrucao,
            "sections": sections,
        }

    print("[BlocoEstrutura] Parse falhou — fail-fast")
    raise EstruturaInvalidaError(
        f"Estrutura generation failed for {nome} in {cidade}.",
        context={
            "nome": nome,
            "cidade": cidade,
            "segmento": segmento,
            "acao": "Check LLM response format and retry",
        },
    )
