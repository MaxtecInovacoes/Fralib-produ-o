"""
Bryan Agent Tools — Ferramentas disponíveis para o Bryan Managed Agent.

Cada tool é uma função que executa uma ação e retorna dados para o agent loop.
O Claude decide quais tools usar baseado no contexto da conversa.
"""
import json
import os
import re
from datetime import datetime
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "")
_engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


# ══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (schema para a API do Claude)
# ══════════════════════════════════════════════════════════════════

BRYAN_TOOLS = [
    {
        "name": "check_lead_history",
        "description": "Busca histórico completo de interações com o lead (mensagens enviadas/recebidas, stages anteriores). Use SEMPRE antes de responder para não repetir mensagens ou contradizer o que já foi dito.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "ID do lead no banco"}
            },
            "required": ["lead_id"]
        }
    },
    {
        "name": "web_search_lead",
        "description": "Pesquisa informações sobre a empresa do lead na internet (Google). Use quando precisa personalizar a abordagem com dados reais da empresa (serviços, preços, diferenciais, redes sociais).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca (ex: 'Academia Iron Gym Campina Grande do Sul')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_knowledge",
        "description": "Lê padrões de sucesso do knowledge store (o que funciona pra converter leads por segmento, objeções comuns e como lidar, variantes A/B que performam melhor). Use para basear sua estratégia em dados reais.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["winning_patterns", "objection_handling", "segment_insights", "ab_results"],
                    "description": "Qual knowledge base consultar"
                },
                "segment": {"type": "string", "description": "Segmento do lead (ex: 'academia', 'restaurante')"}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "verify_message",
        "description": "Auto-verifica a qualidade da mensagem antes de enviar. Checa: guardrails (não mencionar preço antes do stage certo, não ser longo demais), coerência com histórico, tom adequado ao stage. Use SEMPRE antes de finalizar a resposta.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Mensagem que pretende enviar"},
                "stage": {"type": "string", "description": "Stage atual do lead (hook, qualify, pain, amplify, proof, offer, close)"},
                "lead_segment": {"type": "string", "description": "Segmento do lead"}
            },
            "required": ["message", "stage"]
        }
    },
]


# ══════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ══════════════════════════════════════════════════════════════════

def execute_tool(tool_name: str, tool_input: dict, context: dict = None) -> str:
    """Executa uma tool e retorna o resultado como string."""
    try:
        if tool_name == "check_lead_history":
            return _tool_check_lead_history(tool_input, context)
        elif tool_name == "web_search_lead":
            return _tool_web_search_lead(tool_input)
        elif tool_name == "read_knowledge":
            return _tool_read_knowledge(tool_input)
        elif tool_name == "verify_message":
            return _tool_verify_message(tool_input)
        else:
            return json.dumps({"error": f"Tool desconhecida: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── check_lead_history ─────────────────────────────────────────────

def _tool_check_lead_history(tool_input: dict, context: dict = None) -> str:
    """Busca últimas interações do lead no banco."""
    lead_id = tool_input.get("lead_id")
    user_id = context.get("user_id") if context else None

    if not _engine or not lead_id:
        return json.dumps({"error": "DB não configurado ou lead_id ausente"})

    with _engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT mensagem, direcao, criado_em
            FROM interacoes
            WHERE lead_id = :lid
            ORDER BY criado_em DESC
            LIMIT 20
        """), {"lid": lead_id}).fetchall()

    if not rows:
        return json.dumps({"history": [], "note": "Nenhuma interação anterior encontrada"})

    history = []
    for r in rows:
        history.append({
            "msg": r[0][:200] if r[0] else "",
            "dir": r[1],  # entrada, saida, saida_humano
            "when": str(r[2])[:16] if r[2] else ""
        })

    history.reverse()  # cronológico
    return json.dumps({"history": history, "total": len(history)}, ensure_ascii=False)


# ── web_search_lead ────────────────────────────────────────────────

def _tool_web_search_lead(tool_input: dict) -> str:
    """Pesquisa empresa no Google via Playwright (custo zero)."""
    query = tool_input.get("query", "")
    if not query:
        return json.dumps({"error": "query vazia"})

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"https://www.google.com/search?q={query}&hl=pt-BR", timeout=15000)
            page.wait_for_timeout(2000)

            # Extrair snippets dos resultados
            results = []
            items = page.query_selector_all("div.g")[:5]
            for item in items:
                title_el = item.query_selector("h3")
                snippet_el = item.query_selector("div[data-sncf]") or item.query_selector("span.st") or item.query_selector("div.VwiC3b")
                link_el = item.query_selector("a")
                title = title_el.inner_text() if title_el else ""
                snippet = snippet_el.inner_text() if snippet_el else ""
                link = link_el.get_attribute("href") if link_el else ""
                if title:
                    results.append({"title": title, "snippet": snippet[:200], "url": link})

            browser.close()
            return json.dumps({"results": results, "query": query}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Web search falhou: {str(e)}", "query": query})


# ── read_knowledge ─────────────────────────────────────────────────

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "bryan_knowledge")

def _tool_read_knowledge(tool_input: dict) -> str:
    """Lê knowledge base do Bryan."""
    topic = tool_input.get("topic", "")
    segment = tool_input.get("segment", "").lower()

    file_map = {
        "winning_patterns": "winning_patterns.md",
        "objection_handling": "objection_handling.md",
        "segment_insights": "segment_insights.json",
        "ab_results": "ab_results.json",
    }

    filename = file_map.get(topic)
    if not filename:
        return json.dumps({"error": f"Topic desconhecido: {topic}"})

    filepath = os.path.join(KNOWLEDGE_DIR, filename)
    if not os.path.exists(filepath):
        return json.dumps({"content": "", "note": f"Knowledge '{topic}' ainda não existe. Será criado após primeiros resultados."})

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Se é JSON e tem segmento, filtrar
    if filename.endswith(".json") and segment:
        try:
            data = json.loads(content)
            if segment in data:
                return json.dumps({"content": data[segment], "segment": segment}, ensure_ascii=False)
            return json.dumps({"content": data, "note": f"Segmento '{segment}' não encontrado, retornando tudo"}, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

    # Retornar conteúdo bruto (limitado a 2000 chars)
    return json.dumps({"content": content[:2000], "topic": topic}, ensure_ascii=False)


# ── verify_message ─────────────────────────────────────────────────

def _tool_verify_message(tool_input: dict) -> str:
    """Auto-verifica qualidade da mensagem antes de enviar."""
    message = tool_input.get("message", "")
    stage = tool_input.get("stage", "")
    segment = tool_input.get("lead_segment", "")

    issues = []

    # G1: Tamanho
    if len(message) > 500:
        issues.append("Mensagem muito longa (>500 chars). SDR WhatsApp deve ser curto e direto.")
    if len(message) < 10:
        issues.append("Mensagem muito curta (<10 chars). Parece incompleta.")

    # G2: Preço antes do stage certo
    price_pattern = r'R\$|reais|valor|preço|investimento|mensalidade|plano'
    if re.search(price_pattern, message, re.IGNORECASE) and stage in ('hook', 'qualify', 'pain'):
        issues.append(f"Mencionou preço/valor no stage '{stage}'. Só mencionar preço a partir do stage 'offer'.")

    # G3: Emoji spam
    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', message))
    if emoji_count > 3:
        issues.append(f"Muitos emojis ({emoji_count}). Máximo 2-3 por mensagem pra parecer natural.")

    # G4: Formalidade excessiva
    formal_patterns = ['prezado', 'estimado', 'venho por meio', 'gostaríamos', 'informamos']
    for p in formal_patterns:
        if p in message.lower():
            issues.append(f"Tom muito formal ('{p}'). Bryan fala como amigo, não como empresa.")
            break

    # G5: Pedido de reunião/ligação cedo demais
    meeting_pattern = r'reuni[aã]o|liga[çc][aã]o|agendar|marcar.*hor[aá]rio|call'
    if re.search(meeting_pattern, message, re.IGNORECASE) and stage in ('hook', 'qualify'):
        issues.append(f"Pediu reunião/ligação no stage '{stage}'. Muito cedo — só após 'proof'.")

    # G6: Não parecer bot
    bot_patterns = ['como posso ajudar', 'estou à disposição', 'não hesite em', 'fico no aguardo']
    for p in bot_patterns:
        if p in message.lower():
            issues.append(f"Frase genérica de bot ('{p}'). Ser mais específico e humano.")
            break

    if issues:
        return json.dumps({"ok": False, "issues": issues, "suggestion": "Reescreva corrigindo os problemas acima."}, ensure_ascii=False)

    return json.dumps({"ok": True, "note": "Mensagem aprovada nos guardrails."}, ensure_ascii=False)
