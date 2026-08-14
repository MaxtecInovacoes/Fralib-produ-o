"""
Theo Managed Agent Loop — Orquestrador agentic para briefing estratégico.

Padrão Managed Agent: loop iterativo com tool_use onde o Claude busca
ativamente dados de mercado, concorrentes e reviews antes de gerar
o briefing. Garante briefing rico e verificado.

Fluxo:
  1. Recebe dados do lead (Hunter)
  2. Claude busca: concorrentes, reviews, keywords, site do lead
  3. Gera briefing AIDA completo usando dados reais
  4. Verifica completude com verify_briefing
  5. Retorna briefing rico em markdown
"""
import json
import os
import re
import sys
import time
import requests
from dataclasses import dataclass, field
from typing import Optional, List

from backend.agents.theo_tools import THEO_TOOLS, execute_tool


# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════

MAX_ITERATIONS = 6
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 6000


# ══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════

THEO_AGENT_SYSTEM = """Você é Theo, estrategista senior de marketing digital e copywriter especialista em negócios locais da FraLib.

## Sua Missão
Criar briefings estratégicos RICOS e ESPECÍFICOS que guiam o Arquiteto Mestre e o Liam a gerar sites que convertem. Seu briefing é a fundação de tudo.

## Processo OBRIGATÓRIO (siga esta ordem)

1. **get_market_keywords** — Buscar keywords reais do Google Suggest para o nicho/cidade
2. **search_competitors** — Encontrar concorrentes com presença digital
3. **analyze_competitor_site** — Analisar 1-2 concorrentes (copy, CTAs, estrutura)
4. **get_google_reviews_summary** — Analisar reviews do lead (temas, sentimento)
5. **scrape_lead_site** — Se o lead tem site, analisar o que ele já tem
6. **Gerar briefing** usando TODOS os dados coletados
7. **verify_briefing** — Verificar completude. Se falhar, corrigir.

## Regras do Briefing

- Estrutura AIDA obrigatória (Atenção → Interesse → Desejo → Ação)
- Keywords reais do mercado DEVEM aparecer nas sugestões de copy
- Insights de concorrentes DEVEM informar diferenciação
- Reviews do lead DEVEM informar prova social e pontos fortes
- NUNCA genérico — cada briefing é único para aquele negócio
- NUNCA mencionar preços, valores ou mensalidades
- NUNCA definir cores, CSS, fontes ou design (isso é do Arquiteto)
- Foco em: copy, estrutura AIDA, CTAs, prova social, diferenciação

## Output Final

Quando verify_briefing retornar ok:true, responda com o briefing em markdown:

```markdown
# Briefing Estratégico: [Nome do Negócio]

## Modo Visual: [DARK/LIGHT]

## 1. HIERARQUIA SEO
- H1: [sugestão com keyword + cidade]
- H2s: [por seção]

## 2. KEYWORDS DO MERCADO
- Transacionais: [lista]
- Locais: [lista]
- Informacionais: [lista]

## 3. ANÁLISE COMPETITIVA
- Concorrentes: [quem são, o que fazem bem]
- Oportunidade: [o que ninguém faz]
- Diferenciação: [como se destacar]

## 4. PROVA SOCIAL
- Temas positivos dos reviews: [lista]
- Frase-chave dos clientes: [citação real]
- Sentimento geral: [positivo/misto]

## 5. ESTRUTURA AIDA
### ATENÇÃO (Hero)
- Headline: [sugestão específica]
- Subheadline: [proposta de valor]

### INTERESSE (Problema/Solução)
- Dor do cliente: [específica do nicho]
- Solução: [como o negócio resolve]

### DESEJO (Serviços + Social Proof)
- Serviços destaque: [lista]
- Prova: [reviews, números]

### AÇÃO (CTA)
- CTA principal: [texto WhatsApp]
- CTAs secundários: [lista]

## 6. SEÇÕES RECOMENDADAS
[lista ordenada com justificativa]

## 7. GUARDRAILS
- Proibido: preços, lorem ipsum, dados inventados
- Obrigatório: WhatsApp CTA, LGPD, dados reais

## 8. SCHEMA.ORG
- Tipo: [LocalBusiness/Restaurant/etc]
```

Retorne APENAS o markdown do briefing, sem JSON wrapper."""


# ══════════════════════════════════════════════════════════════════
# AGENT LOOP
# ══════════════════════════════════════════════════════════════════

@dataclass
class TheoAgentOutput:
    briefing: str = ""
    tools_used: List[str] = field(default_factory=list)
    iterations: int = 0
    verified: bool = False
    error: str = ""


def _resolve_anthropic():
    """Resolve API key e base URL."""
    try:
        from backend.services.ia_manager import pick_key
        result = pick_key("anthropic")
        if result:
            api_key, base_url, key_id = result
            return api_key, base_url, key_id
    except Exception:
        pass
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return api_key, "https://api.anthropic.com", None


def theo_agent_loop(
    nome: str,
    segmento: str,
    cidade: str,
    rating: float = 0,
    reviews: list = None,
    site_url: str = "",
    dados_hunter: dict = None,
) -> TheoAgentOutput:
    """
    Loop agentic do Theo.

    Busca ativamente dados de mercado e gera briefing verificado.
    """
    api_key, base_url, key_id = _resolve_anthropic()
    if not api_key:
        return TheoAgentOutput(error="API key não encontrada")

    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "anthropic-beta": "prompt-caching-2024-07-31",
    }

    dados_hunter = dados_hunter or {}
    reviews = reviews or dados_hunter.get("reviews", [])

    user_prompt = f"""## Lead para Briefing
- Nome: {nome}
- Segmento: {segmento}
- Cidade: {cidade}
- Rating: {rating}/5
- Reviews disponíveis: {len(reviews)}
- Site do lead: {site_url or "Não informado"}
- Telefone: {dados_hunter.get('telefone', '')}
- Endereço: {dados_hunter.get('endereco', '')}
- Serviços: {', '.join((dados_hunter.get('servicos') or [])[:6])}

---
Siga seu processo OBRIGATÓRIO: busque keywords, concorrentes, reviews, e gere o briefing verificado."""

    messages = [{"role": "user", "content": user_prompt}]
    tools_used = []

    context = {
        "reviews": reviews,
        "dados_hunter": dados_hunter,
    }

    print(f"[TheoAgent] Iniciando loop para {nome} ({segmento}, {cidade})")

    for iteration in range(MAX_ITERATIONS):
        payload = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.4,
            "system": [{"type": "text", "text": THEO_AGENT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            "tools": THEO_TOOLS,
            "messages": messages,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code != 200:
                print(f"[TheoAgent] API error {response.status_code}: {response.text[:200]}", flush=True)
                break
            data = response.json()
        except Exception as e:
            print(f"[TheoAgent] Request error: {e}", flush=True)
            break

        stop_reason = data.get("stop_reason", "")
        content_blocks = data.get("content", [])

        messages.append({"role": "assistant", "content": content_blocks})

        if stop_reason == "end_turn":
            print(f"[TheoAgent] end_turn na iteração {iteration + 1}, {len(tools_used)} tools")
            return _parse_briefing_response(content_blocks, tools_used, iteration + 1)

        if stop_reason == "tool_use":
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block["input"]
                    tool_id = block["id"]

                    print(f"[TheoAgent] Tool: {tool_name}", flush=True)
                    tools_used.append(tool_name)

                    result = execute_tool(tool_name, tool_input, context)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        print(f"[TheoAgent] Stop reason inesperado: {stop_reason}", flush=True)
        break

    print(f"[TheoAgent] Fallback após {MAX_ITERATIONS} iterações", flush=True)
    return TheoAgentOutput(tools_used=tools_used, iterations=MAX_ITERATIONS, error="Loop excedeu iterações")


def _parse_briefing_response(content_blocks: list, tools_used: list, iterations: int) -> TheoAgentOutput:
    """Extrai briefing markdown do output final."""
    text_content = ""
    for block in content_blocks:
        if block.get("type") == "text":
            text_content += block.get("text", "")

    # Limpar markdown code blocks se houver
    briefing = text_content.strip()
    if briefing.startswith("```markdown"):
        briefing = briefing[len("```markdown"):].strip()
    if briefing.startswith("```"):
        briefing = briefing[3:].strip()
    if briefing.endswith("```"):
        briefing = briefing[:-3].strip()

    verified = "verify_briefing" in tools_used
    print(f"[TheoAgent] Briefing: {len(briefing)} chars, verified={verified}")

    return TheoAgentOutput(
        briefing=briefing,
        tools_used=tools_used,
        iterations=iterations,
        verified=verified,
    )


# ══════════════════════════════════════════════════════════════════
# WRAPPER — Drop-in para gerar_briefing_estrategico
# ══════════════════════════════════════════════════════════════════

def gerar_briefing_estrategico_agent(input_data) -> str:
    """
    Drop-in replacement para gerar_briefing_estrategico usando Managed Agent.
    Retorna briefing markdown — mesma interface do original.
    """
    nome = input_data.nome if hasattr(input_data, "nome") else str(input_data)
    cidade = input_data.cidade if hasattr(input_data, "cidade") else ""
    segmento = input_data.segmento if hasattr(input_data, "segmento") else ""
    rating = input_data.rating if hasattr(input_data, "rating") else 0

    # Extrair dados extras se disponíveis
    dados_hunter = {}
    reviews = []
    site_url = ""
    if hasattr(input_data, "dados_hunter"):
        dados_hunter = input_data.dados_hunter or {}
        reviews = dados_hunter.get("reviews", [])
    if hasattr(input_data, "site_url"):
        site_url = input_data.site_url or ""

    result = theo_agent_loop(
        nome=nome,
        segmento=segmento,
        cidade=cidade,
        rating=rating,
        reviews=reviews,
        site_url=site_url,
        dados_hunter=dados_hunter,
    )

    if result.error or not result.briefing:
        print(f"[TheoAgent] Falhou ({result.error}), fallback para single-shot")
        from theo import gerar_briefing_estrategico
        return gerar_briefing_estrategico(input_data)

    print(f"[TheoAgent] Sucesso: {result.iterations} iterações, {len(result.tools_used)} tools")
    return result.briefing
