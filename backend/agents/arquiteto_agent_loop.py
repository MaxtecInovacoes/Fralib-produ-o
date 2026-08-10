"""
Arquiteto Mestre Managed Agent Loop — Orquestrador agentic para geração de PRD.

Padrão Managed Agent: loop iterativo com tool_use onde o Claude busca
ativamente cada recurso (keywords, design system, animações, SEO, open design)
e verifica completude antes de entregar.

Fluxo:
  1. Recebe dados brutos (Hunter, Jina, Caio)
  2. Claude decide quais tools chamar (get_keyword_research, get_design_system, etc)
  3. Executa tools, alimenta resultados de volta
  4. Claude gera PRD completo usando TODOS os dados coletados
  5. Chama verify_prd para garantir que nada foi ignorado
  6. Se verify falha → corrige e re-verifica
  7. Retorna PRD estruturado
"""
import json
import os
import re
import sys
import time
import requests
from dataclasses import dataclass, field
from typing import Optional, List, Dict

sys.path.insert(0, os.path.dirname(__file__))
from arquiteto_tools import ARQUITETO_TOOLS, execute_tool
from design_context import get_design_context, get_hero_style
from designer_prd import DesignerPRD
from llm_direct import call_claude, _registrar_uso_completo

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════

MAX_ITERATIONS = 8
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192
THINKING_BUDGET = 4000


# ══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════

ARQUITETO_AGENT_SYSTEM = """Você é o Arquiteto Mestre e Diretor de Arte da FraLib. Você gera PRDs (Product Requirement Documents) completos para sites de negócios locais.

## Seu Processo OBRIGATÓRIO (siga esta ordem)

1. **get_keyword_research** — Buscar keywords reais com volume para o segmento/cidade
2. **get_design_system** — Buscar tokens OKLch, tipografia e animação do design system
3. **get_animation_profile** — Buscar perfil de animação específico do nicho
4. **get_seo_context** — Buscar schema.org, H1 template, FAQ do nicho
5. **get_open_design_reference** — Buscar referência criativa de design system real
6. **get_craft_rules** — Buscar regras anti-slop e craft
7. **get_jina_insights** — Extrair FAQ, keywords e value props dos insights Jina
8. **Gerar o PRD** usando TODOS os dados coletados
9. **verify_prd** — Verificar se o PRD usou tudo. Se falhar, CORRIGIR e re-verificar.

## Regras ABSOLUTAS

- NUNCA gere o PRD sem antes chamar as tools. Cada tool traz dados que DEVEM estar no output.
- Cores vêm EXCLUSIVAMENTE do get_design_system (tokens OKLch). NUNCA inventar cores.
- Keywords do get_keyword_research DEVEM aparecer em seo_keywords e no copy (H1, subtítulos).
- Animações do get_animation_profile DEVEM definir o campo animations[].
- FAQ do get_seo_context + get_jina_insights DEVEM popular faq_questions[].
- Se verify_prd retornar ok:false, CORRIJA os issues e chame verify_prd novamente.
- NUNCA invente dados (reviews, telefones, endereços). Use apenas o que foi fornecido.
- NUNCA mencione preços/valores.
- Copy deve ser ESPECÍFICO para o negócio — sem frases genéricas intercambiáveis.

## Seções Dinâmicas

O número de seções NÃO é fixo. Baseie-se nos dados disponíveis:
- Sem reviews → omitir seção depoimentos
- Negócio com cardápio → adicionar seção cardápio
- Negócio com equipe → adicionar seção equipe
- Negócio com portfólio → adicionar seção portfólio
- Mínimo: hero, sobre, servicos, contato (4)
- Máximo: 9 seções

## Layouts Disponíveis

- hero: hero-split | hero-center | hero-fullscreen | hero-diagonal
- sobre: sobre-timeline | sobre-grid | sobre-cards
- servicos: services-cards | services-accordion | services-grid-icons | services-list
- depoimentos: reviews-masonry | reviews-carousel | reviews-grid
- faq: services-accordion
- localizacao: location-split | location-full | location-card
- contato: contact-minimal | contact-split | contact-card

## Output Final

Quando tiver TODOS os dados e verify_prd retornar ok:true, responda com JSON EXATO:

```json
{
  "business_name": "nome exato",
  "segmento": "segmento",
  "cidade": "cidade",
  "address": "endereço completo",
  "phone": "telefone",
  "reviews_rating": 4.5,
  "reviews_count": 120,
  "reviews_list": [...reviews reais...],
  "color_palette": {
    "primary": "token --fg",
    "secondary": "token --surface",
    "accent": "token --accent",
    "background": "token --bg",
    "text": "token --fg",
    "surface": "token --surface",
    "muted": "token --muted",
    "border": "token --border",
    "tokens_oklch": {"--bg":"...", "--surface":"...", "--fg":"...", "--accent":"...", "--muted":"...", "--border":"..."},
    "hero_style": {...},
    "reasoning": "justificativa"
  },
  "typography": {"heading": "Font", "body": "Font"},
  "animation_theme": "energetico|elegante|vibrante",
  "animations": [...lista de animações...],
  "instrucao_criativa_para_dev": "instrução detalhada 2-3 parágrafos",
  "sections": [...seções com layout_type e copy...],
  "seo_keywords": [...keywords reais com volume...],
  "faq_questions": [...perguntas FAQ...],
  "value_props": [...propostas de valor...],
  "schema_org_types": ["LocalBusiness"],
  "dark_mode": true/false,
  "photos": [...urls...],
  "logo_url": null,
  "hours": {},
  "google_maps_embed": "",
  "components_21dev": ["whatsapp-sticky-cta"],
  "anti_patterns": ["precos visiveis"],
  "layout_type": "corporate|brutalist|editorial|organic|minimal"
}
```

RESTRIÇÃO: O destino é HTML/Tailwind ESTÁTICO. PROIBIDO React, Vue, JSX, npm."""


# ══════════════════════════════════════════════════════════════════
# GRUPOS DE CAMPOS PRD (4 chamadas LLM parciais)
# ══════════════════════════════════════════════════════════════════

_GRUPOS_CAMPOS_PRD = [
    ["business_name", "segmento", "cidade", "color_palette", "typography", "dark_mode", "layout_type"],
    ["sections", "animations", "instrucao_criativa_para_dev", "anti_patterns", "schema_org_types"],
    ["seo_keywords", "faq_questions", "value_props", "competitor_analysis"],
    ["photos", "reviews_list", "reviews_rating", "reviews_count", "phone", "address",
     "hours", "google_maps_embed", "components_21dev", "geo"],
]


# ══════════════════════════════════════════════════════════════════
# CHUNKED LLM CALLS
# ══════════════════════════════════════════════════════════════════

def _build_shared_context(
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
    craft_ctx: str,
    autocritica_ctx: str,
    tool_results: dict,
) -> str:
    """Monta o contexto compartilhado (mesmo para todas as 4 chamadas parciais)."""
    endereco_rule = (
        "ADDRESS CAPTURED: use the complete address exactly as provided."
        if endereco
        else "ADDRESS NOT CAPTURED: do not invent street/neighborhood; mention only the city when needed."
    )

    tool_results_fmt = "\n".join(
        f"## {name}\n{result[:800] if result else '(empty)'}"
        for name, result in tool_results.items()
    )

    return f"""BUSINESS: {nome} | CITY: {cidade} | SEGMENT: {segmento}
PHONE: {telefone} | ADDRESS: {endereco}
RATING: {rating}/5 ({total_av} avaliacoes) | TIER: {caio_tier}
MODE: {"DARK" if dark_mode else "LIGHT"}
{endereco_rule}

JINA INSIGHTS:
{jina_insights[:3000] if jina_insights else "(nenhum)"}

CREATIVE DIRECTION: {instrucao_criativa[:500]}
{reviews_intel_ctx}

SEO CONTEXT:
{seo_ctx}
{faq_seo_fmt}

KEYWORD RESEARCH:
{keyword_research}

REAL REVIEWS:
{reviews_fmt}

{tool_results_fmt}

CRAFT RULES:
{craft_ctx}

AUTOCRITICA CONTEXT:
{autocritica_ctx}

Real phone: {telefone}
Specific copy for {nome}, never generic."""


def _callar_bloco_arquiteto(
    shared_context: str,
    campos_grupo: list,
) -> dict | None:
    """Faz uma chamada LLM para um subconjunto de campos do PRD.

    Returns dict com os campos preenchidos ou None se falhar.
    Qualquer falha propaga RuntimeError — sem fallback.
    """
    campos_str = ", ".join(campos_grupo)
    campos_set = set(campos_grupo)

    prompt = (
        f"{shared_context}\n\n"
        f"Generate ONLY these PRD fields: {campos_str}\n\n"
        f"Return JSON with EXACTLY these keys: {campos_str}\n"
        f"Omit keys you cannot fill — do NOT invent data.\n"
        f"Rules: colors from design system tokens, keywords from research, "
        f"copy specific to the business, no generic phrases."
    )

    system_prompt = (
        f"{ARQUITETO_AGENT_SYSTEM}\n\n"
        f"TASK: Generate only these fields: {campos_str}\n"
        f"Return JSON with only those keys."
    )

    resp = call_claude(
        system=system_prompt,
        user=prompt,
        model="sonnet",
        max_tokens=4096,
        temperature=0.3,
        agent_name="arquiteto_mestre",
    )

    # Mudança 3: Tracking do Arquiteto em pipeline_traces + llm_budget_ledger
    try:
        _registrar_uso_completo(
            model_id="sonnet",
            input_tokens=len(system_prompt) // 4 + len(prompt) // 4,
            output_tokens=len(resp) // 4,
            agent_name="arquiteto_mestre_bloco",
            provider="anthropic",
        )
    except Exception:
        pass

    resp = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", resp)

    prd_partial = {}
    try:
        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', resp, re.DOTALL)
        if code_block:
            json_str = code_block.group(1)
        else:
            json_str = _extract_largest_json(resp)
        if json_str:
            prd_partial = json.loads(json_str)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[ArquitetoAgent] JSON parse error grupo [{campos_str}]: {e}", flush=True)
        raise RuntimeError(f"Falha ao parsear JSON do grupo [{campos_str}]: {e}")

    # Filtrar apenas campos do grupo
    filtered = {k: v for k, v in prd_partial.items() if k in campos_set}
    if not filtered:
        raise RuntimeError(f"LLM retornou JSON vazio para grupo [{campos_str}]")

    return filtered


def _merge_prd_partials(partials: list[dict]) -> dict:
    """Merge de 4 dicts parciais em um PRD completo."""
    merged = {}
    for partial in partials:
        merged.update(partial)
    return merged


@dataclass
class ArquitetoAgentOutput:
    prd_data: dict = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    iterations: int = 0
    verified: bool = False
    error: str = ""


def _resolve_anthropic():
    """Resolve API key e base URL."""
    try:
        sys.path.insert(0, '/root/fralib/backend')
        sys.path.insert(0, '/root/fralib/backend/services')
        from ia_manager import pick_key
        result = pick_key("anthropic")
        if result:
            api_key, base_url, key_id = result
            return api_key, base_url, key_id
    except Exception as e:
        print(f"[arquiteto_agent_loop] pick_key falhou: {e}")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return api_key, "https://api.anthropic.com", None


def arquiteto_agent_loop(
    dados_hunter: dict,
    cidade: str,
    segmento: str,
    jina_insights: str = "",
    caio_tier: str = "STANDARD",
    caio_score: int = 0,
    dark_mode: bool = False,
    keyword_research: str = "",
) -> ArquitetoAgentOutput:
    """
    Gera DesignerPRD via 4 chamadas LLM parciais (chunking).

    Substitui o tool-use loop por chamadas diretas a _callar_bloco_arquiteto(),
    uma por grupo de campos. Cada chamada recebe contexto compartilhado completo.
    Resultado: mais rápido, sem 529s, tracking completo.
    """
    # ── Extrair campos de dados_hunter ─────────────────────────────
    nome = dados_hunter.get("nome", "") or dados_hunter.get("business_name", "")
    telefone = dados_hunter.get("telefone", "") or dados_hunter.get("phone", "")
    endereco = dados_hunter.get("endereco", "") or dados_hunter.get("address", "")
    rating = dados_hunter.get("rating", 0.0) or dados_hunter.get("reviews_rating", 0.0)
    total_av = dados_hunter.get("total_av", 0) or dados_hunter.get("reviews_count", 0)

    # ── Formatar reviews ────────────────────────────────────────────
    reviews_raw = dados_hunter.get("reviews_list", []) or []
    if reviews_raw:
        reviews_fmt = "\n".join(
            f"- {r.get('text', r.get('review', ''))[:200]} "
            f"(★{r.get('rating', r.get('stars', ''))})"
            for r in reviews_raw[:10]
        )
        reviews_intel_ctx = f"\nREVIEWS INTEL: {len(reviews_raw)} reviews capturados, rating médio {rating}/5."
    else:
        reviews_fmt = "(sem reviews)"
        reviews_intel_ctx = "(sem reviews)"

    # ── SEO + FAQ context ───────────────────────────────────────────
    faq_list = dados_hunter.get("faq_questions", []) or []
    faq_seo_fmt = "\n".join(f"Q: {q.get('pergunta', q.get('question', ''))}\nA: {q.get('resposta', q.get('answer', ''))}" for q in faq_list[:5]) if faq_list else "(sem FAQ)"
    seo_ctx = f"Segmento: {segmento} | Cidade: {cidade} | Keywords: {keyword_research[:500] if keyword_research else '(nenhuma)'}"

    # ── Craft rules + autocritica ───────────────────────────────────
    try:
        from craft_rules import get_craft_rules, get_autocritica
        craft_ctx = get_craft_rules()
        autocritica_ctx = get_autocritica()
    except Exception:
        craft_ctx = ""
        autocritica_ctx = ""

    # ── Instrução criativa ──────────────────────────────────────────
    instrucao_criativa = (
        dados_hunter.get("instrucao_criativa_para_dev", "")
        or dados_hunter.get("instrucao_criativa", "")
        or ""
    )

    # ── Tool results (vazio aqui — tools são chamadas pelo managed agent antigo,
    #       mas mantemos o slot para compatibilidade) ────────────────
    tool_results = dados_hunter.get("tool_results", {}) or {}

    # ── Montar contexto compartilhado ──────────────────────────────
    shared = _build_shared_context(
        nome=nome,
        cidade=cidade,
        segmento=segmento,
        telefone=telefone,
        endereco=endereco,
        rating=rating,
        total_av=total_av,
        caio_tier=caio_tier,
        dark_mode=dark_mode,
        jina_insights=jina_insights,
        instrucao_criativa=instrucao_criativa,
        reviews_fmt=reviews_fmt,
        reviews_intel_ctx=reviews_intel_ctx,
        seo_ctx=seo_ctx,
        faq_seo_fmt=faq_seo_fmt,
        keyword_research=keyword_research,
        craft_ctx=craft_ctx,
        autocritica_ctx=autocritica_ctx,
        tool_results=tool_results,
    )
    print(f"[ArquitetoAgent] Chunked PRD para {nome} ({segmento}, {cidade}) — 4 blocos")

    # Executar 4 chamadas parciais (uma por grupo de campos)
    partials = []
    for grupo_idx, grupo_fields in enumerate(_GRUPOS_CAMPOS_PRD):
        grupo_nome = f"grupo_{grupo_idx + 1}"
        print(f"[ArquitetoAgent] Gerando {grupo_nome}: {', '.join(grupo_fields)}")
        partial = _callar_bloco_arquiteto(
            shared,
            grupo_fields,
        )
        if partial:
            partials.append(partial)
        else:
            print(f"[ArquitetoAgent] AVISO: {grupo_nome} retornou vazio")

    if not partials:
        return ArquitetoAgentOutput(error="Todos os blocos falharam")

    # Merge dos 4 parciais em um DesignerPRD completo
    merged = _merge_prd_partials(partials)
    total_sections = len(merged.get("sections", []))
    print(f"[ArquitetoAgent] PRD merge OK — {total_sections} seções, {len(partials)} blocos")

    return ArquitetoAgentOutput(
        prd_data=merged,
        tools_used=[f"chunk_bloco_{i + 1}" for i in range(len(partials))],
        iterations=len(partials),
        verified=len(partials) == 4,
    )


# ══════════════════════════════════════════════════════════════════
# PARSE RESPONSE
# ══════════════════════════════════════════════════════════════════

def _parse_prd_response(
    content_blocks: list,
    tools_used: list,
    iterations: int,
    dados_hunter: dict,
    cidade: str,
    segmento: str,
    dark_mode: bool,
) -> ArquitetoAgentOutput:
    """Extrai PRD JSON do output final do Claude."""
    text_content = ""
    for block in content_blocks:
        if block.get("type") == "text":
            text_content += block.get("text", "")

    # Extrair JSON
    prd_data = {}
    try:
        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_content, re.DOTALL)
        if code_block:
            json_str = code_block.group(1)
        else:
            # Buscar maior JSON no texto
            json_str = _extract_largest_json(text_content)

        if json_str:
            prd_data = json.loads(json_str)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[ArquitetoAgent] JSON parse error: {e}", flush=True)

    if not prd_data:
        return ArquitetoAgentOutput(tools_used=tools_used, iterations=iterations, error="Não conseguiu extrair JSON do output")

    # Enriquecer com dados obrigatórios que podem ter sido omitidos
    prd_data = _enrich_prd(prd_data, dados_hunter, cidade, segmento, dark_mode)

    verified = "verify_prd" in tools_used
    print(f"[ArquitetoAgent] PRD extraído: {len(prd_data.get('sections', []))} seções, verified={verified}")

    return ArquitetoAgentOutput(
        prd_data=prd_data,
        tools_used=tools_used,
        iterations=iterations,
        verified=verified,
    )


def _extract_largest_json(text: str) -> str:
    """Extrai o maior bloco JSON válido do texto."""
    text = text.replace(" ", " ").replace(" ", " ")
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
    candidates = []
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        j = i
        while j < len(text):
            ch = text[j]
            if esc:
                esc = False
                j += 1
                continue
            if ch == "\\" and in_str:
                esc = True
                j += 1
                continue
            if ch == '"':
                in_str = not in_str
                j += 1
                continue
            if in_str:
                j += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[i:j + 1])
                    break
            j += 1
        i += 1
    if not candidates:
        return ""
    return max(candidates, key=len)


def _enrich_prd(prd: dict, dados_hunter: dict, cidade: str, segmento: str, dark_mode: bool) -> dict:
    """Garante campos obrigatórios no PRD usando dados do Hunter."""
    prd.setdefault("business_name", dados_hunter.get("nome", ""))
    prd.setdefault("segmento", segmento)
    prd.setdefault("cidade", cidade)
    prd.setdefault("address", dados_hunter.get("endereco", ""))
    prd.setdefault("phone", dados_hunter.get("telefone", ""))
    prd.setdefault("reviews_rating", float(dados_hunter.get("rating", 0)))
    prd.setdefault("reviews_count", int(dados_hunter.get("total_avaliacoes", 0)))
    prd.setdefault("reviews_list", dados_hunter.get("reviews") or [])
    prd["_raw_reviews"] = dados_hunter.get("reviews") or []
    prd.setdefault("photos", dados_hunter.get("fotos") or [])
    prd.setdefault("logo_url", dados_hunter.get("logo_url"))
    prd.setdefault("hours", dados_hunter.get("horarios") or {})
    prd.setdefault("dark_mode", dark_mode)
    prd.setdefault("google_maps_embed", "")
    prd.setdefault("components_21dev", ["whatsapp-sticky-cta"])
    prd.setdefault("anti_patterns", ["precos visiveis"])
    prd.setdefault("schema_org_types", ["LocalBusiness"])

    # Geo
    lat = dados_hunter.get("lat") or dados_hunter.get("latitude")
    lng = dados_hunter.get("lng") or dados_hunter.get("longitude") or dados_hunter.get("lon")
    if lat is not None and lng is not None:
        try:
            prd.setdefault("geo", {"lat": float(lat), "lng": float(lng)})
        except (TypeError, ValueError):
            pass

    # Design tokens override (fonte de verdade)
    if not prd.get("color_palette", {}).get("tokens_oklch"):
        design = get_design_context(segmento, dados_hunter.get("nome", ""), prd.get("tier", "STANDARD"), dark_mode)
        tokens = design["tokens"]
        prd["color_palette"] = {
            "primary": tokens["--fg"],
            "secondary": tokens["--surface"],
            "accent": tokens["--accent"],
            "background": tokens["--bg"],
            "text": tokens["--fg"],
            "surface": tokens["--surface"],
            "muted": tokens["--muted"],
            "border": tokens["--border"],
            "tokens_oklch": tokens,
            "hero_style": get_hero_style(design["dir_key"]),
            "reasoning": f"OKLch determinístico. Direção={design['dir_nome']}",
        }
        prd["typography"] = {"heading": design["font_heading"], "body": design["font_body"]}

    return prd


# ══════════════════════════════════════════════════════════════════
# WRAPPER — Drop-in replacement para gerar_arquiteto_mestre_prd
# ══════════════════════════════════════════════════════════════════

def gerar_arquiteto_mestre_prd_agent(
    dados_hunter: dict,
    cidade: str,
    segmento: str,
    jina_insights: str = "",
    caio_tier: str = "STANDARD",
    caio_score: int = 0,
    caio_motivo: str = "",
    briefing_theo: str = "",
    dark_mode: bool = False,
    keyword_research: str = "",
) -> DesignerPRD:
    """
    Drop-in replacement para gerar_arquiteto_mestre_prd usando Managed Agent.
    Retorna DesignerPRD validado — mesma interface do original.
    """
    result = arquiteto_agent_loop(
        dados_hunter=dados_hunter,
        cidade=cidade,
        segmento=segmento,
        jina_insights=jina_insights,
        caio_tier=caio_tier,
        caio_score=caio_score,
        dark_mode=dark_mode,
        keyword_research=keyword_research,
    )

    if result.error or not result.prd_data:
        print(f"[ArquitetoAgent] Falhou ({result.error}), fallback para single-shot")
        from arquiteto_mestre import gerar_arquiteto_mestre_prd
        return gerar_arquiteto_mestre_prd(
            dados_hunter=dados_hunter,
            cidade=cidade,
            segmento=segmento,
            jina_insights=jina_insights,
            caio_tier=caio_tier,
            caio_score=caio_score,
            caio_motivo=caio_motivo,
            briefing_theo=briefing_theo,
            dark_mode=dark_mode,
            keyword_research=keyword_research,
        )

    print(f"[ArquitetoAgent] Sucesso: {result.iterations} iterações, {len(result.tools_used)} tools, verified={result.verified}")
    return DesignerPRD(**result.prd_data)
