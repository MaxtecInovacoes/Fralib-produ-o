"""
Theo Agent Tools — Ferramentas para o Theo Managed Agent.

O Theo busca ativamente dados de mercado, concorrentes e reviews
antes de gerar o briefing estratégico. Garante que o briefing
seja rico em dados reais, não genérico.
"""
import json
import os
import re
import requests
import urllib.request
import urllib.parse

# ══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ══════════════════════════════════════════════════════════════════

THEO_TOOLS = [
    {
        "name": "scrape_lead_site",
        "description": "Scrape o site do lead (se existir) via Jina Reader para entender o que ele já tem online. Retorna conteúdo markdown do site.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL do site do lead para analisar"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "search_competitors",
        "description": "Pesquisa concorrentes do nicho na cidade via Google/Jina. Retorna URLs e snippets dos top 5 concorrentes com presença digital.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento do negócio"},
                "cidade": {"type": "string", "description": "Cidade do negócio"}
            },
            "required": ["segmento", "cidade"]
        }
    },
    {
        "name": "analyze_competitor_site",
        "description": "Analisa um site concorrente específico via Jina Reader. Extrai: estrutura, copy, CTAs, diferenciais, pontos fracos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL do concorrente para analisar"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "get_google_reviews_summary",
        "description": "Retorna resumo dos reviews do Google do lead: temas positivos, reclamações comuns, sentimento geral. Usa dados do Hunter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reviews": {"type": "array", "items": {"type": "object"}, "description": "Lista de reviews do Hunter"}
            },
            "required": ["reviews"]
        }
    },
    {
        "name": "get_market_keywords",
        "description": "Busca termos reais do Google Suggest para o nicho/cidade. Identifica intenção de busca (transacional, informacional, local).",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento"},
                "cidade": {"type": "string", "description": "Cidade"}
            },
            "required": ["segmento", "cidade"]
        }
    },
    {
        "name": "verify_briefing",
        "description": "Verifica completude do briefing: tem AIDA, tem keywords, tem copy sugerida, tem guardrails, tem schema.org. Use SEMPRE antes de finalizar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "briefing": {"type": "string", "description": "Briefing gerado para verificar"}
            },
            "required": ["briefing"]
        }
    },
]

# ══════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ══════════════════════════════════════════════════════════════════

def execute_tool(tool_name: str, tool_input: dict, context: dict = None) -> str:
    try:
        if tool_name == "scrape_lead_site":
            return _tool_scrape_lead_site(tool_input)
        elif tool_name == "search_competitors":
            return _tool_search_competitors(tool_input)
        elif tool_name == "analyze_competitor_site":
            return _tool_analyze_competitor_site(tool_input)
        elif tool_name == "get_google_reviews_summary":
            return _tool_get_google_reviews_summary(tool_input, context)
        elif tool_name == "get_market_keywords":
            return _tool_get_market_keywords(tool_input)
        elif tool_name == "verify_briefing":
            return _tool_verify_briefing(tool_input)
        else:
            return json.dumps({"error": f"Tool desconhecida: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

# ── scrape_lead_site ──────────────────────────────────────────────

def _tool_scrape_lead_site(tool_input: dict) -> str:
    """Scrape site do lead via Jina Reader."""
    url = tool_input.get("url", "")
    if not url or not url.startswith("http"):
        return json.dumps({"content": "", "note": "URL inválida ou não fornecida"})

    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"X-Return-Format": "markdown", "X-Timeout": "15"}
        jina_key = os.getenv("JINA_API_KEY")
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"
        resp = requests.get(jina_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            content = resp.text[:3000]
            return json.dumps({"content": content, "url": url, "chars": len(content)}, ensure_ascii=False)
        return json.dumps({"content": "", "error": f"Status {resp.status_code}"})
    except Exception as e:
        return json.dumps({"content": "", "error": str(e)})

# ── search_competitors ────────────────────────────────────────────

def _tool_search_competitors(tool_input: dict) -> str:
    """Pesquisa concorrentes via Google/Jina."""
    segmento = tool_input.get("segmento", "")
    cidade = tool_input.get("cidade", "")
    query = f"{segmento} {cidade} site"

    EXCLUIR = [
        "google", "facebook", "instagram", "youtube", "linkedin", "twitter",
        "smartfit", "bodytech", "bluefit", "mcdonalds", "starbucks",
        "wix.com", "wordpress.com", "blogspot", "squarespace",
        "maps", "wikipedia", "amazon", "mercadolivre", "ifood",
    ]

    try:
        search_url = "https://r.jina.ai/https://www.google.com/search?q=" + requests.utils.quote(query)
        headers = {"X-Return-Format": "markdown", "X-Timeout": "15"}
        jina_key = os.getenv("JINA_API_KEY")
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"
        resp = requests.get(search_url, headers=headers, timeout=20)

        sites = []
        if resp.status_code == 200:
            for line in resp.text.split("\n"):
                if "http" in line:
                    url_match = re.search(r"https?://[^\s\)\"\x27]+", line)
                    if url_match:
                        url = url_match.group(0).rstrip(".,)")
                        url_lower = url.lower()
                        if not any(exc in url_lower for exc in EXCLUIR):
                            if url not in sites and len(url) > 15:
                                sites.append(url)
                                if len(sites) >= 5:
                                    break

        return json.dumps({"competitors": sites, "query": query, "total": len(sites)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"competitors": [], "error": str(e)})

# ── analyze_competitor_site ───────────────────────────────────────

def _tool_analyze_competitor_site(tool_input: dict) -> str:
    """Analisa site concorrente via Jina."""
    url = tool_input.get("url", "")
    if not url:
        return json.dumps({"error": "URL vazia"})

    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"X-Return-Format": "markdown", "X-Timeout": "15"}
        jina_key = os.getenv("JINA_API_KEY")
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"
        resp = requests.get(jina_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            content = resp.text[:2500]
            return json.dumps({"content": content, "url": url}, ensure_ascii=False)
        return json.dumps({"content": "", "error": f"Status {resp.status_code}", "url": url})
    except Exception as e:
        return json.dumps({"content": "", "error": str(e), "url": url})

# ── get_google_reviews_summary ────────────────────────────────────

def _tool_get_google_reviews_summary(tool_input: dict, context: dict = None) -> str:
    """Analisa reviews do Google do lead."""
    reviews = tool_input.get("reviews", []) or (context or {}).get("reviews", [])

    if not reviews:
        return json.dumps({"summary": "Sem reviews disponíveis", "sentiment": "neutral", "themes": []})

    positivos = []
    negativos = []
    temas = []

    for r in reviews[:10]:
        texto = r.get("texto", r.get("text", ""))
        rating = r.get("rating", r.get("nota", 5))
        if rating >= 4:
            positivos.append(texto[:100])
        else:
            negativos.append(texto[:100])

    # Extrair temas simples
    all_text = " ".join(r.get("texto", r.get("text", "")) for r in reviews[:10]).lower()
    tema_keywords = {
        "atendimento": ["atendimento", "atendeu", "recepção", "educado", "simpático"],
        "qualidade": ["qualidade", "excelente", "ótimo", "bom", "profissional"],
        "preço": ["preço", "valor", "caro", "barato", "custo"],
        "ambiente": ["ambiente", "espaço", "limpo", "organizado", "confortável"],
        "localização": ["localização", "perto", "fácil", "acesso", "estacionamento"],
        "rapidez": ["rápido", "demora", "espera", "pontual", "agilidade"],
    }
    for tema, keywords in tema_keywords.items():
        if any(kw in all_text for kw in keywords):
            temas.append(tema)

    sentiment = "positive" if len(positivos) > len(negativos) else "mixed" if negativos else "positive"

    return json.dumps({
        "total_reviews": len(reviews),
        "sentiment": sentiment,
        "themes": temas,
        "top_positive": positivos[:3],
        "top_negative": negativos[:2],
        "insight": f"Clientes destacam: {', '.join(temas[:3])}" if temas else "Reviews genéricos sem tema dominante"
    }, ensure_ascii=False)

# ── get_market_keywords ───────────────────────────────────────────

def _tool_get_market_keywords(tool_input: dict) -> str:
    """Busca keywords reais do Google Suggest."""
    segmento = tool_input.get("segmento", "")
    cidade = tool_input.get("cidade", "")

    queries = [
        f"{segmento} {cidade}",
        f"melhor {segmento} {cidade}",
        f"{segmento} perto de mim",
    ]

    all_terms = []
    for q in queries:
        try:
            encoded = urllib.parse.quote(q)
            url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={encoded}&hl=pt-BR"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                terms = [s for s in (data[1] if len(data) > 1 else []) if isinstance(s, str)]
                all_terms.extend(terms[:5])
        except Exception:
            pass

    # Classificar intenção
    transactional = [t for t in all_terms if any(w in t.lower() for w in ["preço", "valor", "agendar", "contratar", "melhor", "perto"])]
    informational = [t for t in all_terms if any(w in t.lower() for w in ["como", "o que", "qual", "dicas", "benefícios"])]
    local = [t for t in all_terms if cidade.lower() in t.lower()]

    return json.dumps({
        "all_terms": list(dict.fromkeys(all_terms))[:15],
        "transactional": transactional[:5],
        "informational": informational[:5],
        "local": local[:5],
        "total": len(set(all_terms)),
    }, ensure_ascii=False)

# ── verify_briefing ───────────────────────────────────────────────

def _tool_verify_briefing(tool_input: dict) -> str:
    """Verifica completude do briefing estratégico."""
    briefing = tool_input.get("briefing", "")
    issues = []
    warnings = []

    # Must have AIDA structure
    aida_sections = ["atencao", "atenção", "interesse", "desejo", "acao", "ação", "hero", "problema", "solucao"]
    aida_found = sum(1 for s in aida_sections if s in briefing.lower())
    if aida_found < 3:
        issues.append("Estrutura AIDA incompleta. Deve ter Atenção (Hero), Interesse, Desejo, Ação.")

    # Must have keywords/SEO
    if "keyword" not in briefing.lower() and "seo" not in briefing.lower() and "palavra" not in briefing.lower():
        issues.append("Sem menção a keywords/SEO. Briefing deve incluir termos de busca reais.")

    # Must have copy suggestions
    if "headline" not in briefing.lower() and "h1" not in briefing.lower() and "título" not in briefing.lower():
        warnings.append("Sem sugestão de headline/H1. Incluir copy sugerida.")

    # Must have CTA
    if "cta" not in briefing.lower() and "whatsapp" not in briefing.lower():
        issues.append("Sem CTA definido. Deve ter CTA WhatsApp.")

    # Must have guardrails
    if "preço" not in briefing.lower() and "preco" not in briefing.lower() and "guardrail" not in briefing.lower():
        warnings.append("Sem guardrails explícitos (proibição de preços).")

    # Length check
    if len(briefing) < 500:
        issues.append(f"Briefing muito curto ({len(briefing)} chars). Mínimo 1000 chars para ser útil.")
    elif len(briefing) < 1000:
        warnings.append("Briefing curto. Considerar expandir com mais detalhes de copy e estrutura.")

    # Must mention the business specifics
    if "secao" not in briefing.lower() and "seção" not in briefing.lower() and "section" not in briefing.lower():
        warnings.append("Sem definição de seções do site.")

    ok = len(issues) == 0
    return json.dumps({
        "ok": ok,
        "issues": issues,
        "warnings": warnings,
        "briefing_length": len(briefing),
        "suggestion": "Corrija os issues antes de finalizar." if not ok else "Briefing completo."
    }, ensure_ascii=False)
