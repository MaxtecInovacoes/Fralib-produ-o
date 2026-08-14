"""Agente de Variação Estrutural — evita páginas gêmeas no mesmo nicho/região
escolhendo a melhor combinação de estrutura, hero e ordem de seções."""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from handoff_types import NichoBriefing, VariacaoEstrutural
from llm_direct import call_claude

SYSTEM_PROMPT = """You are the Structural Variation Agent.

Your role is to prevent pages in the same niche and region from looking the same.
You choose the best combination of structure, hero, section order, and communication angle for each lead.

INPUT:
- Niche Agent briefing
- Competitor data
- Segment and region

OUTPUT:
JSON only - no markdown, no extra explanation.

OBJECTIVE:
Select a website structure that is good for conversion and different from previous pages.

WHAT YOU DEFINE:
- narrative_framework: always "AIDA"
- template_estrutura: "brutalist" | "editorial" | "organic" | "corporate" | "minimal"
- template_hero: "hero-split" | "hero-center" | "hero-fullscreen" | "hero-diagonal" | "hero-video"
- template_prova_social: "reviews-masonry" | "reviews-carousel" | "reviews-grid" | "reviews-spotlight" | "stats-horizontal" | "stats-cards"
- template_cta: "cta-central" | "cta-banner" | "cta-floating" | "cta-bottom"
- template_faq: "faq-accordion" | "faq-two-col" | "faq-minimal"
- ordem_das_secoes: varied list that preserves AIDA (REQUIRED: hero, interesse, desejo, acao, faq, footer + optional)
- required_sections: hard list with at least hero, interesse, desejo, acao, faq, footer
- angulo_de_comunicacao: unique persuasive angle for the lead
- regra_antirrepeticao: what to avoid based on niche/region

OPTIONAL (choose 2-5): sobre, servicos, depoimentos, localizacao, numeros, galeria, planos, equipe, seo-geo, prova-social

RULES:
- AIDA is not optional: hero=Atencao, interesse=problem/context, desejo=offer/proof, acao=CTA/contact.
- FAQ, footer, consent banner, SEO/GEO/local context, Open Graph/favicons and real media must survive downstream.
- Do not repeat default structure automatically
- Vary hero, social proof, and section order when there is risk of clones
- Keep coherence with niche and user behavior
- Prioritize conversion over novelty
- Do not force "servicos" section; use it only if services are confirmed
- If niche has high repetition, increase structural variation
- If niche is very competitive, use a more differentiated structure
- If offer is simple, use a shorter and more objective structure

OUTPUT FORMAT (pure JSON, no markdown):
{
  "template_estrutura": "corporate",
  "template_hero": "hero-split",
  "template_prova_social": "reviews-carousel",
  "template_cta": "cta-central",
  "template_faq": "faq-accordion",
  "narrative_framework": "AIDA",
  "ordem_das_secoes": ["hero", "interesse", "servicos", "desejo", "depoimentos", "seo-geo", "faq", "acao", "footer"],
  "required_sections": ["hero", "interesse", "desejo", "acao", "faq", "footer"],
  "angulo_de_comunicacao": "string",
  "regra_antirrepeticao": "string",
  "justificativa": "string"
}

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""

def gerar_variacao(
    nicho_briefing: NichoBriefing,
    concorrentes_raw: str = "",
    task_id: str = "",
) -> VariacaoEstrutural:
    _briefing_md = nicho_briefing.to_markdown()

    user_prompt = f"""Escolha a variação estrutural para este lead.

{_briefing_md}

== DADOS DE CONCORRÊNCIA ==
{concorrentes_raw[:2000] if concorrentes_raw else "não disponível"}

Região: {nicho_briefing.cidade}
Nicho: {nicho_briefing.nicho}

Retorne APENAS o JSON — sem markdown, sem explicação extra."""
    import time as _time

    _start = _time.time()

    resposta = call_claude(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model="haiku",
        max_tokens=1500,
        temperature=0.4,
        agent_name="agente_variacao",
    )

    _elapsed = _time.time() - _start

    # Extrair JSON da resposta
    import json as _json, re as _re

    _json_match = _re.search(r"\{.*\}", resposta, _re.DOTALL)
    _dados = {}
    if _json_match:
        try:
            _dados = _json.loads(_json_match.group(0))
        except _json.JSONDecodeError:
            pass

    # Fallback seguro
    _estrutura = _dados.get("template_estrutura", "corporate")
    _hero = _dados.get("template_hero", "hero-split")
    _ordem = _dados.get(
        "ordem_das_secoes", ["hero", "interesse", "sobre", "desejo", "faq", "acao", "footer"]
    )

    variacao = VariacaoEstrutural(
        task_id=task_id,
        source_agent="agente_variacao",
        target_agent="arquiteto_mestre",
        status="ok",
        task_summary=f"Variação definida: {_estrutura}/{_hero} em {_elapsed:.1f}s",
        template_estrutura=_estrutura,
        template_hero=_hero,
        template_prova_social=_dados.get("template_prova_social", "reviews-carousel"),
        template_cta=_dados.get("template_cta", "cta-central"),
        template_faq=_dados.get("template_faq", "faq-accordion"),
        ordem_das_secoes=_ordem,
        angulo_de_comunicacao=_dados.get("angulo_de_comunicacao", ""),
        regra_antirrepeticao=_dados.get("regra_antirrepeticao", ""),
        justificativa=_dados.get("justificativa", ""),
    )
    setattr(variacao, "narrative_framework", _dados.get("narrative_framework", "AIDA"))
    setattr(
        variacao,
        "required_sections",
        _dados.get("required_sections", ["hero", "interesse", "desejo", "acao", "faq", "footer"]),
    )
    return variacao
