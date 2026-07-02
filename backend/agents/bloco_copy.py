"""Bloco 2 — Copy por secao.
LLM call focada em escrever copy (h1, subtitulo, cta, body) para cada secao.
Retorno: Markdown parseado via markdown_prd_parser.

Fail-safe: retry com prompt simplificado se parse inicial falhar.
Se retry falhar, lança CopyGenerationError.
"""

import re as _re
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.pipeline_exceptions import CopyGenerationError
from llm_direct import call_claude
from markdown_prd_parser import parse_bloco2_with_fallback
from prompts_arquiteto import SYSTEM_COPY_SENIOR


def _formatar_reviews(top_3: list, reviews_insights: dict) -> tuple:
    """Retorna (reviews_fmt, reviews_intel_ctx)."""
    if top_3:
        reviews_fmt = "\n".join(
            [
                f'- "{r.get("text", r.get("texto", ""))}" — {r.get("author", r.get("autor", "Cliente"))}'
                for r in top_3
            ]
        )
    else:
        reviews_fmt = "NENHUM REVIEW DISPONIVEL"

    intel_ctx = ""
    if reviews_insights.get("total_reviews", 0) > 0:
        elogios = ", ".join(reviews_insights.get("elogios_resumo", [])[:3])
        reclamacoes = (
            ", ".join(reviews_insights.get("reclamacoes_resumo", [])[:2])
            or "nada relevante"
        )
        palavras = ", ".join(reviews_insights.get("palavras_frequentes", [])[:8])
        diferencial = reviews_insights.get("diferencial_detectado", "")
        intel_ctx = (
            f"\n=== INTELIGENCIA REVIEWS ({reviews_insights['total_reviews']} avaliacoes, nota {reviews_insights['nota_media']}/5) ===\n"
            f"Elogios: {elogios}\nReclamacoes: {reclamacoes}\n"
            f"Palavras citadas: {palavras}\nDiferencial: {diferencial}\n"
            f"REGRA: Use insights pra enriquecer hero, sobre e servicos. Evite mencionar reclamacoes.\n"
            f"=== FIM ===\n"
        )
    return reviews_fmt, intel_ctx


def _montar_prompt_bloco2(
    nome: str,
    cidade: str,
    segmento: str,
    telefone: str,
    endereco: str,
    rating: float,
    total_av: int,
    caio_tier: str,
    dark_mode: bool,
    jina_insights: str,
    instrucao_criativa: str,
    reviews_fmt: str,
    reviews_intel_ctx: str,
    seo_ctx: str,
    faq_seo_fmt: str,
    keyword_research: str,
    secoes_nomes: list,
    reviews_has: bool,
    intel_ctx: str,
    craft_ctx: str,
    autocritica_ctx: str,
    polo_resolvido: str = "",
) -> str:
    """Monta prompt compacto para Bloco 2 — copy."""
    endereco_rule = (
        "ADDRESS CAPTURED: use the complete address exactly as provided."
        if endereco
        else "ADDRESS NOT CAPTURED: do not invent street/neighborhood; mention only the city when needed and omit location section when there is no address."
    )
    # Sprint 12.x: injeta bloco de polo (copy defaults: tone/voice/cta)
    try:
        from polo_prompts import build_polo_prompt_block
        _polo_block = build_polo_prompt_block(
            nicho=segmento,
            subnicho="",
            include_copy=True,
            include_design_logic=False,
        )
    except Exception:
        _polo_block = ""

    # Etapa 4: injeta copy angle recomendado (StoryBrand, PAS, AIDA, etc)
    # + polo voice (vocabulario proprio, palavras proibidas, gatilhos)
    try:
        from copywriting.copy_angles import get_recommended_angle
        from copywriting.polo_voice import get_polo_voice
        _angle = get_recommended_angle(segmento, subnicho="", polo=polo_resolvido or "CLASSIC")
        _voice = get_polo_voice(polo_resolvido or "CLASSIC")
        _angle_block = f"""

COPY ANGLE (framework): {_angle.framework}
- Hook: {_angle.hook_template}
- Body: {_angle.body_template}
- CTA: {_angle.cta_template}
- Examples: {", ".join(_angle.public_examples[:2])}

VOICE CHECK (palavras para USAR): {", ".join(_voice.vocabulary[:8])}
VOICE CHECK (palavras para EVITAR): {", ".join(_voice.avoid_words[:5])}
TRIGGERS: {", ".join(_voice.mental_triggers[:4])}
"""
    except Exception:
        _angle_block = ""

    return f"""BUSINESS: {nome} | CITY: {cidade} | SEGMENT: {segmento}
PHONE: {telefone} | ADDRESS: {endereco}
RATING: {rating}/5 ({total_av} avaliacoes) | TIER: {caio_tier}
MODE: {"DARK" if dark_mode else "LIGHT"}
POLO: {polo_resolvido or "CLASSIC"}
{endereco_rule}

{_polo_block}
{_angle_block}

{jina_insights[:3000] if jina_insights else ""}

CREATIVE DIRECTION: {instrucao_criativa[:500]}
{intel_ctx}
{reviews_intel_ctx}

COPY RULES:
- All customer-facing copy MUST be in Brazilian Portuguese (pt-BR).
- NEVER use: "atendimento personalizado", "qualidade e compromisso", "resultados reais", "pronto para comecar", "os melhores profissionais"
- NEVER use emoji. If a visual icon is needed, the renderer may decide via SVG; copy never contains emoji.
- NEVER use "premium", "melhor", "top", "lider", "referencia", "moderna", "elite", "VIP" as public claims.
- Vary CTAs: Hero=urgency, Servicos=curiosity, Depoimentos=desire, Contato=scarcity.
- Geo-specific copy: if address exists, use street/neighborhood; if not, use only city and do not fake exact location.
- SOBRE: do not paste a review inside the text. Use only confirmed facts and a neutral synthesis; literal reviews stay only in depoimentos.
- SERVICOS: only confirmed Maps services. Reviews are NOT a service source. If there are no confirmed services, keep items empty and recommend omitting the section; consultation must stay in contato/sobre, never in a standalone banner.
- Never infer modality from words in reviews, keywords, or niche expectations. Example: a review mentioning dance, muay thai, or equipment does not confirm a service.
- Numbers/metrics: use only rating and review count; do not invent average hours, modalities, students, years, or results.
- If information is weak, prefer omitting the section or creating a compact contact block instead of filler.
- FAQ: use People Also Ask as questions when available.

REAL REVIEWS:
{reviews_fmt}

{seo_ctx}
{faq_seo_fmt}
{keyword_research}

SECTIONS: {", ".join(secoes_nomes)}
{"REVIEWS REAIS DISPONIVEIS — use-os." if reviews_has else "REVIEWS INDISPONIVEIS — depoimentos deve ter omitir:true"}

Return MARKDOWN with EXACTLY this format:

## hero
h1: titulo com cidade (8+ palavras, headline de VENDA, nao o nome do negocio)
subtitulo: subtitulo persuasivo
cta: texto do botao
eyebrow: tag acima do h1

## sobre
h2: titulo
body: texto curto e especifico
cta: texto do botao

## servicos
h2: titulo
body: texto curto e especifico
items: servicos reais confirmados, separados por ; (vazio se nao houver)
cta: texto do botao

## depoimentos
omitir: {"false" if reviews_has else "true"}
h2: titulo
body: texto com reviews reais

## faq
h2: titulo
body: perguntas e respostas curtas

## localizacao
h2: titulo
body: endereco real; se endereco estiver vazio, omitir:true
cta: texto do botao

## contato
h2: titulo
body: telefone real
cta: texto do botao

CRAFT RULES:
{craft_ctx}

{autocritica_ctx}

H1: 8+ words with benefit + city. Good example: "Treino funcional e nutricao integrada em Campina Grande do Sul". Bad example: "Nutrasport" (that is a name, NOT a headline).
Real phone: {telefone}
Specific copy for {nome}, never generic.
MARKDOWN ONLY. No JSON. No code blocks."""


def _texto_curto(value) -> str:
    return str(value or "").strip()


def _primeira_linha_review(review: dict) -> str:
    texto = _texto_curto(review.get("text") or review.get("texto"))
    autor = _texto_curto(review.get("author") or review.get("autor")) or "Cliente"
    if not texto:
        return ""
    texto = " ".join(texto.split())
    if len(texto) > 180:
        texto = texto[:177].rstrip() + "..."
    return f'"{texto}" - {autor}'




def executar_bloco_copy(
    nome: str,
    cidade: str,
    segmento: str,
    telefone: str,
    endereco: str,
    rating: float,
    total_av: int,
    caio_tier: str,
    dark_mode: bool,
    jina_insights: str,
    instrucao_criativa: str,
    reviews_raw: list,
    seo_ctx: str,
    faq_seo_fmt: str,
    keyword_research: str,
    secoes_nomes: list,
    intel_ctx: str,
    craft_ctx: str,
    autocritica_ctx: str,
) -> dict:
    """Executa Bloco 2 (copy) e retorna dict com sections + copy.

    Returns:
        dict com "sections" (lista de {name, copy, omitir})
    """
    from prompts_arquiteto import selecionar_top_reviews

    _reviews_sep = selecionar_top_reviews(reviews_raw)
    reviews_fmt, reviews_intel_ctx = _formatar_reviews(
        _reviews_sep["top_3"], _reviews_sep["insights"]
    )
    reviews_has = bool(reviews_raw)

    prompt = _montar_prompt_bloco2(
        nome,
        cidade,
        segmento,
        telefone,
        endereco,
        rating,
        total_av,
        caio_tier,
        dark_mode,
        jina_insights,
        instrucao_criativa,
        reviews_fmt,
        reviews_intel_ctx,
        seo_ctx,
        faq_seo_fmt,
        keyword_research,
        secoes_nomes,
        reviews_has,
        intel_ctx,
        craft_ctx,
        autocritica_ctx,
    )

    print(f"[BlocoCopy] Chamando LLM (copy) para {len(secoes_nomes)} secoes...")

    # Tentativa 1: sonnet
    try:
        resp = call_claude(
            system=SYSTEM_COPY_SENIOR,
            user=prompt,
            model="sonnet",
            max_tokens=3000,
            temperature=0.4,
            agent_name="arquiteto_mestre",
        )
    except Exception as e:
        raise CopyGenerationError(
            f"Copy generation failed for {nome} in {cidade}.",
            context={
                "nome": nome,
                "cidade": cidade,
                "segmento": segmento,
                "erro": str(e),
                "acao": "Corrigir LLM/conectividade; nao usar modelo alternativo automatico",
            },
        ) from e

    resp = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", resp)
    dados = parse_bloco2_with_fallback(resp)

    if dados and dados.get("sections"):
        sections = dados.get("sections", [])
        print(f"[BlocoCopy] OK: {len(sections)} secoes com copy")
        return {"sections": sections}

    print("[BlocoCopy] Parse falhou — tentando retry com prompt simplificado")
    # Retry: prompt mais simples ainda
    prompt_retry = (
        f"Gere MARKDOWN ESTRUTURADO para o site de: {nome} em {cidade} ({segmento}).\n"
        f"Telefone: {telefone} | Rating: {rating}/5 | Tier: {caio_tier}\n"
        f"Secoes: {', '.join(secoes_nomes)}\n"
        f"{'IMPORTANTE: use reviews reais' if reviews_has else 'depoimentos omitir:true'}\n\n"
        f"## hero\nh1: ...\nsubtitulo: ...\ncta: ...\neyebrow: ...\n\n"
        f"## sobre\nh2: ...\nbody: ...\ncta: ...\n\n"
        f"## servicos\nh2: ...\nbody: ...\nitems: ...\ncta: ...\n\n"
        f"## depoimentos\nomitir: {'false' if reviews_has else 'true'}\nh2: ...\nbody: ...\n\n"
        f"## faq\nh2: ...\nbody: ...\n\n"
        f"## localizacao\nh2: ...\nbody: ...\ncta: ...\n\n"
        f"## contato\nh2: ...\nbody: ...\ncta: ...\n"
        f"MARKDOWN APENAS, sem JSON, sem explicacao."
    )
    try:
        resp2 = call_claude(
            system=SYSTEM_COPY_SENIOR,
            user=prompt_retry,
            model="sonnet",
            max_tokens=1800,
            temperature=0.2,
            agent_name="arquiteto_mestre",
        )
    except Exception as e:
        raise CopyGenerationError(
            f"Copy retry failed for {nome} in {cidade}.",
            context={
                "nome": nome,
                "cidade": cidade,
                "segmento": segmento,
                "erro": str(e),
                "acao": "Corrigir LLM/conectividade; nao usar modelo alternativo automatico",
            },
        ) from e
    resp2 = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", resp2)
    dados2 = parse_bloco2_with_fallback(resp2)
    if dados2 and dados2.get("sections"):
        print(f"[BlocoCopy] Retry OK: {len(dados2['sections'])} secoes")
        return dados2

    # Parse falhou após retry
    raise CopyGenerationError(
        f"Copy parse failed for {nome} in {cidade} after retry.",
        context={
            "nome": nome,
            "cidade": cidade,
            "segmento": segmento,
            "acao": "Check LLM response format and retry",
        },
    )
