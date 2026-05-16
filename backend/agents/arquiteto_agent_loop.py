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
# AGENT LOOP
# ══════════════════════════════════════════════════════════════════

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
    except Exception:
        pass
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
    Loop agentic do Arquiteto Mestre.

    O Claude busca ativamente cada recurso via tools, gera o PRD,
    e verifica completude antes de entregar.
    """
    api_key, base_url, key_id = _resolve_anthropic()
    if not api_key:
        return ArquitetoAgentOutput(error="API key não encontrada")

    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "anthropic-beta": "prompt-caching-2024-07-31",
    }

    # Contexto inicial — dados brutos do negócio
    nome = dados_hunter.get("nome", "")
    reviews = dados_hunter.get("reviews") or []
    fotos = dados_hunter.get("fotos") or []

    user_prompt = f"""## Dados do Negócio (Hunter)
- Nome: {nome}
- Segmento: {segmento}
- Cidade: {cidade}
- Tier: {caio_tier} (score={caio_score})
- Rating: {dados_hunter.get('rating', 0)}/5 ({dados_hunter.get('total_avaliacoes', 0)} avaliações)
- Telefone: {dados_hunter.get('telefone', '')}
- Endereço: {dados_hunter.get('endereco', '')}
- Fotos disponíveis: {len(fotos)}
- Reviews disponíveis: {len(reviews)}
- Serviços: {', '.join((dados_hunter.get('servicos') or [])[:8])}
- Horários: {json.dumps(dados_hunter.get('horarios') or {}, ensure_ascii=False)[:200]}
- Dark mode: {dark_mode}

## Reviews Reais
{chr(10).join([f'- "{r.get("texto", r.get("text", ""))}" — {r.get("autor", r.get("author", "Cliente"))}' for r in reviews[:8]]) if reviews else "NENHUM REVIEW — seção depoimentos deve ser omitida."}

## Jina Insights Disponíveis
{"SIM — chame get_jina_insights para extrair dados estruturados." if jina_insights else "NÃO DISPONÍVEL."}

---
Siga seu processo OBRIGATÓRIO: chame as tools na ordem, colete todos os dados, gere o PRD, e verifique com verify_prd antes de finalizar."""

    messages = [{"role": "user", "content": user_prompt}]
    tools_used = []

    # Context passado para as tools
    context = {
        "keyword_research": keyword_research,
        "jina_insights": jina_insights,
        "dados_hunter": dados_hunter,
        "dark_mode": dark_mode,
    }

    print(f"[ArquitetoAgent] Iniciando loop para {nome} ({segmento}, {cidade})")

    for iteration in range(MAX_ITERATIONS):
        payload = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3,
            "system": [{"type": "text", "text": ARQUITETO_AGENT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            "tools": ARQUITETO_TOOLS,
            "messages": messages,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=180)
            if response.status_code != 200:
                print(f"[ArquitetoAgent] API error {response.status_code}: {response.text[:200]}", flush=True)
                break
            data = response.json()
        except Exception as e:
            print(f"[ArquitetoAgent] Request error: {e}", flush=True)
            break

        stop_reason = data.get("stop_reason", "")
        content_blocks = data.get("content", [])

        messages.append({"role": "assistant", "content": content_blocks})

        # end_turn → extrair PRD final
        if stop_reason == "end_turn":
            print(f"[ArquitetoAgent] end_turn na iteração {iteration + 1}, {len(tools_used)} tools usadas")
            return _parse_prd_response(content_blocks, tools_used, iteration + 1, dados_hunter, cidade, segmento, dark_mode)

        # tool_use → executar tools
        if stop_reason == "tool_use":
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block["input"]
                    tool_id = block["id"]

                    print(f"[ArquitetoAgent] Tool: {tool_name}", flush=True)
                    tools_used.append(tool_name)

                    result = execute_tool(tool_name, tool_input, context)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        print(f"[ArquitetoAgent] Stop reason inesperado: {stop_reason}", flush=True)
        break

    print(f"[ArquitetoAgent] Fallback após {MAX_ITERATIONS} iterações", flush=True)
    return ArquitetoAgentOutput(tools_used=tools_used, iterations=MAX_ITERATIONS, error="Loop excedeu iterações")


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
