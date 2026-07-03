#!/usr/bin/env python3
"""
Blog Automatizado FraLib OS v2.0
- Busca tendências do Google Trends Brasil
- Topics de HYPE global (IA, tech, cultura)
- Gera post otimizado para SEO com CTAs e links internos
- Salva como HTML em frontend/blog/posts/
- Atualiza index.html automaticamente

Cron: 0 8,14,20 * * * (3x/dia)
"""

import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from html import escape as _he  # P0 hotfix: XSS em interpolacoes HTML do blog

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
INDEX_FILE = BLOG_DIR / "index.html"
SITEMAP_FILE = BLOG_DIR.parent / "sitemap.xml"

SITE_URL = "https://seunegociofralib.site"
POSTS_PER_DAY = 2  # 2 posts/dia, mais longos (SEO profundo)

# ============================================================================
# FILTROS DE SEGURANCA - BLOQUEIO DE TOPICOS PROIBIDOS
# ============================================================================
# Topicos sobre crimes, violencia, policia sao BLOQUEADOS antes de gerar post.
# Outros temas (politica, financas, saude, etc) sao permitidos mas
# o LLM eh instruido a manter tom de negocio.

BLOCKED_KEYWORDS = [
    # Crimes
    "crime", "crimes", "homicidio", "homicidios", "assassinato", "assassinatos",
    "roubo", "roubos", "furto", "furtos", "latrocinio", "sequestro", "sequestros",
    # Violencia
    "violencia", "estupro", "estupros", "agressao", "agressoes", "espancamento",
    "tortura", "assassin",
    # Trafico / drogas
    "trafico", "trafico de drogas", "droga", "drogas", "narcotrafico",
    "cocaina", "crack", "maconha", "entorpecente",
    # Policia / prisao
    "policia", "pm militar", "preso", "presos", "presidio", "cadeia",
    "delegacia", "delegado", "bope", "choque", "rocam",
    # Terrorismo / armas
    "terrorismo", "atentado", "bomba", "explosivo", "arma de fogo",
    "massacre",
    # Politica partidaria (sensivel)
    "eleicao 2026", "campanha eleitoral", "partido politico",
    "bolsonaro", "lula", "pt partido", "pl partido",
    # Saude grave (nao somos fonte medica)
    "cancer metastase", "suicidio",
]

# Politica liberal: apenas bloqueio TOTAL se o topico FOR sobre crimes.
# Politica, financas, saude leve = permitido mas gera ângulo de negocio.

def is_topic_safe(text: str) -> bool:
    """Retorna True se o topico NAO eh sobre crime/violencia/politica proibida."""
    if not text:
        return False
    t = text.lower()
    # Bloqueia apenas se o topico FOR predominantemente sobre assunto proibido
    blocked_hits = sum(1 for kw in BLOCKED_KEYWORDS if kw in t)
    return blocked_hits == 0

# Categorias de negócio válidas
CATEGORIES = {
    "marketing": {"name": "Marketing", "color": "#9333ea"},
    "ia": {"name": "IA & Automação", "color": "#00FFB3"},
    "vendas": {"name": "Vendas", "color": "#FFB800"},
    "freelancer": {"name": "Freelancer", "color": "#7c3aed"},
    "tech": {"name": "Tecnologia", "color": "#c084fc"},
    "negócios": {"name": "Negócios", "color": "#22d3a0"},
    "hype": {"name": "🔥 Hype", "color": "#FF6B6B"},
}

# ============================================================================
# LINKS INTERNOS PARA INJEÇÃO AUTOMÁTICA
# ============================================================================

INTERNAL_LINKS = {
    "FraLib": {
        "url": "/planos",
        "text": "FraLib OS",
        "cta": "Testar grátis 7 dias"
    },
    "planos": {
        "url": "/planos",
        "text": "nossos planos",
        "cta": "Começar agora"
    },
    "trial": {
        "url": "/login?signup=1",
        "text": "trial grátis",
        "cta": "Criar conta grátis"
    },
    "whatsapp": {
        "url": "/docs/como-funciona.html#whatsapp",
        "text": "WhatsApp Business",
        "cta": "Automação WhatsApp"
    },
    "sites": {
        "url": "/docs/como-funciona.html#sites",
        "text": "criar sites",
        "cta": "Gerar site com IA"
    },
    "prospectar": {
        "url": "/docs/como-funciona.html#prospectar",
        "text": "prospectar clientes",
        "cta": "Automatizar prospecção"
    },
    "sdr": {
        "url": "/docs/sdr-bryan.html",
        "text": "SDR automático",
        "cta": "Conhecer o Franz"
    },
    "ia": {
        "url": "/docs/ia-generativa.html",
        "text": "IA para negócios",
        "cta": "IA que vende"
    },
}

# ============================================================================
# TENDÊNCIAS DO SETOR (curadas)
# ============================================================================

TRENDING_TOPICS = [
    {
        "topic": "Automação com IA para PMEs",
        "category": "ia",
        "keywords": ["automação", "ia", "pequenas empresas", "vendas"],
        "intent": "search",
        "angle": "Como IA substitui vendedor repetitivo"
    },
    {
        "topic": "WhatsApp Business API 2026",
        "category": "vendas",
        "keywords": ["whatsapp", "business", "api", "vendas", "automação"],
        "intent": "commercial",
        "angle": "Vender pelo WhatsApp sem mexer no celular"
    },
    {
        "topic": "Gerador de sites com IA",
        "category": "tech",
        "keywords": ["site", "ia", "gerador", "criar site", "automatizado"],
        "intent": "commercial",
        "angle": "Site profissional em 5 minutos, sem saber programar"
    },
    {
        "topic": "SDR de IA: o vendedor que nunca dorme",
        "category": "ia",
        "keywords": ["sdr", "ia", "whatsapp", "vendas automáticas", "follow-up"],
        "intent": "commercial",
        "angle": "Franz, o vendedor que prospecta 24/7 no WhatsApp"
    },
    {
        "topic": "Google Maps como máquina de leads",
        "category": "marketing",
        "keywords": ["google maps", "leads", "prospecção", "negócios locais"],
        "intent": "commercial",
        "angle": "Encontrar clientes sem site na sua região automaticamente"
    },
    {
        "topic": "Como cobrar R$1.500 por site em 2026",
        "category": "freelancer",
        "keywords": ["preço", "site", "freelancer", "tabela", " quanto cobrar"],
        "intent": "commercial",
        "angle": "Tabela de preços para freelancers de sites"
    },
    {
        "topic": "Prospecção B2B que funciona sem LinkedIn",
        "category": "vendas",
        "keywords": ["prospecção", "b2b", "whatsapp", "leads", "vendas b2b"],
        "intent": "commercial",
        "angle": "Abandonar LinkedIn e prospectar pelo WhatsApp"
    },
    {
        "topic": "Site que vende: 7 erros que freelancers cometem",
        "category": "marketing",
        "keywords": ["site", "erros", "freelancer", "vendas", "conversão"],
        "intent": "informational",
        "angle": "Site bonito que não vende - o que fazer diferente"
    },
    {
        "topic": "Como automatizar 100% do funil de vendas",
        "category": "ia",
        "keywords": ["automação", "funil", "vendas", "ia", "pipeline"],
        "intent": "commercial",
        "angle": "Do lead ao fechamento sem mover um dedo"
    },
    {
        "topic": "FraLib OS: o case que mudou a prospecção no Brasil",
        "category": "tech",
        "keywords": ["fralib", "prospecção", "ia", "case", "sucesso"],
        "intent": "informational",
        "angle": "História real de quem fatura R$10k/mês com site"
    },
    {
        "topic": "Quanto cobrar por gestão de WhatsApp em 2026",
        "category": "freelancer",
        "keywords": ["whatsapp", "gestão", "freelancer", "preço", "serviço"],
        "intent": "commercial",
        "angle": "Novo serviço digital que todo cliente precisa"
    },
    {
        "topic": "Marketing digital para freelancers: o que mudou",
        "category": "marketing",
        "keywords": ["marketing", "freelancer", "2026", "tendências", "digital"],
        "intent": "informational",
        "angle": "O que funciona agora para vender serviços digitais"
    },
]

# ============================================================================
# TOPICS DE HYPE GLOBAL (adaptar para FraLib)
# ============================================================================

HYPE_TOPICS = [
    # IA/Tech Hype
    {
        "topic": "DeepSeek: a IA open source que está mudando tudo",
        "hype": "DeepSeek",
        "category": "hype",
        "keywords": ["deepseek", "ia open source", "inteligência artificial", "2026"],
        "angle": "Como DeepSeek está barateando IA e o que isso significa pra vender sites",
        "fralib_hook": "A mesma IA que barateou o DeepSeek é usada no FraLib para criar sites automaticamente."
    },
    {
        "topic": "GPT-5 da OpenAI: o que mudou para profissionais",
        "hype": "GPT-5",
        "category": "hype",
        "keywords": ["gpt-5", "openai", "ia", "profissionais", "2026"],
        "angle": "IA generativa cada vez mais poderosa - como usar pra vender mais",
        "fralib_hook": "O FraLib já usa IA avançada para gerar sites. Com GPT-5, fica ainda melhor."
    },
    {
        "topic": "Agentes autônomos de IA: amigos ou inimigos do emprego?",
        "hype": "AI Agents",
        "category": "hype",
        "keywords": ["agentes ia", "automação", "emprego", "futuro"],
        "angle": "IA que trabalha sozinha - oportunidade pra freelancers",
        "fralib_hook": "O FraLib é um agente de IA que trabalha 24/7 vendendo sites pra você."
    },
    {
        "topic": "Cursor AI e a revolução da programação",
        "hype": "Cursor AI",
        "category": "hype",
        "keywords": ["cursor", "ia", "programação", "codigo"],
        "angle": "IA que programa sozinha - ainda vale aprender a codar?",
        "fralib_hook": "O FraLib cria sites sem código. O Cursor pode ajudar freelancer a entregar mais."
    },
    # Tech/Produtos Hype
    {
        "topic": "Pixel 10: Google copia Apple e muda fotografia mobile",
        "hype": "Pixel 10",
        "category": "hype",
        "keywords": ["pixel", "google", "smartphone", "fotografia"],
        "angle": "Novo celular tem câmera que edita fotos com IA - oportunidades pra negócios locais",
        "fralib_hook": "Negócios com site profissional têm 3x mais chance de aparecer no Google Maps."
    },
    {
        "topic": "Figure AI: robô humanoide entra no mercado de trabalho",
        "hype": "Figure AI",
        "category": "hype",
        "keywords": ["robô", "figure ai", "trabalho", "futuro"],
        "angle": "Robôs entrando no mercado - como se preparar com automação",
        "fralib_hook": "Automação não espera. Quem não se atualiza, perde clients para quem usa IA."
    },
    {
        "topic": "Apple Vision Pro 2: realidade mista no dia a dia",
        "hype": "Vision Pro 2",
        "category": "hype",
        "keywords": ["apple", "vision pro", "realidade mista", "vr"],
        "angle": "Nova tecnologia cria demanda por presença digital - seu cliente precisa de site",
        "fralib_hook": "Seus clientes vão precisar de site imersivo. O FraLib já cria."
    },
    # Negócios/Cultura Hype
    {
        "topic": "Micro SaaS: a nova febre do empreendedorismo digital",
        "hype": "Micro SaaS",
        "category": "hype",
        "keywords": ["micro saas", "software", "negócios", "renda passiva"],
        "angle": "Vender software como serviço - como começar do zero",
        "fralib_hook": "O FraLib ajuda a criar sua presença digital. Primeiro site, depois SaaS."
    },
    {
        "topic": "Trabalho remoto em 2026: vale a pena mesmo?",
        "hype": "Trabalho remoto",
        "category": "hype",
        "keywords": ["trabalho remoto", "home office", "produtividade", "freelancer"],
        "angle": "Modelo híbrido exige presença digital forte",
        "fralib_hook": "Freelancers remotos que têm site próprio fecham contratos 2x mais rápido."
    },
    {
        "topic": "Criptomoedas em 2026: recuperação ou nova queda?",
        "hype": "Bitcoin 2026",
        "category": "hype",
        "keywords": ["bitcoin", "criptomoeda", "investimento", "2026"],
        "angle": "Mercado instável - como criar renda previsível com serviços",
        "fralib_hook": "Em vez de investir em risco, invista em presença digital. Site que vende traz R$todo mês."
    },
]


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def slugify(text: str) -> str:
    """Converte texto para slug URL-friendly."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:80]


def has_post(slug: str) -> bool:
    """Verifica se já existe post com esse slug."""
    post_file = POSTS_DIR / f"{slug}.html"
    return post_file.exists()


def save_post(slug: str, html: str) -> Path:
    """Salva post no diretório."""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    post_file = POSTS_DIR / f"{slug}.html"
    post_file.write_text(html, encoding="utf-8")
    return post_file


# ============================================================================
# GOOGLE TRENDS REAL
# ============================================================================

def fetch_google_trends_br() -> List[Dict]:
    """Busca Google Trends Brasil via RSS oficial."""
    trends = []
    try:
        import requests
        # RSS oficial do Google Trends (BR)
        urls = [
            "https://trends.google.com.br/trends/trendingsearches/daily/rss?geo=BR",
            "https://trends.google.com.br/trends/trendingsearches/realtime/rss?geo=BR",
        ]
        for url in urls:
            try:
                resp = requests.get(
                    url,
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0 (FraLib Bot)"},
                )
                if resp.ok:
                    import re
                    items = re.findall(r"<title>([^<]+)</title>", resp.text)
                    for title in items[:10]:
                        # Google Trends BR pode misturar EN quando nao tem topico BR quente
                        # Filtrar apenas topicos com palavras PT ou nomes proprios comuns
                        if _is_pt_topic(title):
                            trends.append({
                                "topic": title,
                                "category": classify_topic(title),
                                "keywords": title.lower().split(),
                                "intent": "trending",
                                "source": "google_trends_br",
                            })
            except Exception:
                continue
    except Exception as e:
        print(f"  Google Trends error: {e}", file=sys.stderr)
    return trends


def _is_pt_topic(title: str) -> bool:
    """Detecta se topico eh em portugues (heuristica simples)."""
    t = title.lower()
    # Marcadores comuns PT
    pt_markers = ["ão", "ões", "ção", "ções", "á", "é", "í", "ó", "ú",
                  " de ", " da ", " do ", " com ", " para ", " brasil",
                  " brasileiro", " brasileira", " são ", " não ", " que "]
    # Marcadores comuns EN (excluir)
    en_markers = [" the ", " and ", " of ", " for ", " with ", " from ",
                  "is ", "are ", " an ", " a ", " ban ", " emergency"]
    pt_score = sum(1 for m in pt_markers if m in t)
    en_score = sum(1 for m in en_markers if m in t)
    return pt_score >= 1 and en_score == 0


def fetch_reddit_brazil() -> List[Dict]:
    """Top posts do dia de subreddits BR com foco em negocio/tech/marketing."""
    trends = []
    subreddits = ["brasil", "brdev", "empreendedorismo", "investimentos", "marketingdigital", "desabafos"]
    try:
        import requests
        for sub in subreddits:
            try:
                # .json endpoint do Reddit - pega top do dia
                url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=3"
                resp = requests.get(
                    url,
                    timeout=10,
                    headers={"User-Agent": "FraLib Blog Bot 1.0"},
                )
                if resp.ok:
                    data = resp.json()
                    for post in data.get("data", {}).get("children", []):
                        p = post.get("data", {})
                        title = p.get("title", "").strip()
                        # Reddit em PT ou aceita qualquer titulo de sub BR
                        if title and 20 < len(title) < 120:
                            trends.append({
                                "topic": title,
                                "category": classify_topic(title),
                                "keywords": title.lower().split()[:5],
                                "intent": "trending",
                                "source": f"reddit_{sub}",
                            })
            except Exception:
                continue
    except Exception as e:
        print(f"  Reddit error: {e}", file=sys.stderr)
    return trends


def fetch_hackernews() -> List[Dict]:
    """Top stories do Hacker News APENAS em PT ou com keywords BR (filtro rigoroso)."""
    trends = []
    try:
        import requests
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10,
            headers={"User-Agent": "FraLib Blog Bot 1.0"},
        )
        if resp.ok:
            story_ids = resp.json()[:15]  # top 15 (mais pq filtramos muito)
            for sid in story_ids:
                try:
                    s = requests.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        timeout=5,
                    ).json()
                    title = (s.get("title") or "").strip()
                    # FILTRO RIGOROSO: so aceita se for PT
                    if title and 20 < len(title) < 120 and not s.get("dead"):
                        if _is_pt_topic(title):
                            trends.append({
                                "topic": title,
                                "category": classify_topic(title),
                                "keywords": title.lower().split()[:5],
                                "intent": "trending",
                                "source": "hackernews",
                            })
                            if len(trends) >= 5:  # limite baixo pq HN raramente tem PT
                                break
                except Exception:
                    continue
    except Exception as e:
        print(f"  Hacker News error: {e}", file=sys.stderr)
    return trends


def deduplicate_trends(trends: List[Dict]) -> List[Dict]:
    """Remove duplicatas por topic (case-insensitive)."""
    seen = set()
    unique = []
    for t in trends:
        key = t["topic"].lower().strip()
        if key not in seen and is_topic_safe(key):
            seen.add(key)
            unique.append(t)
    return unique


def rank_for_fralib(trends: List[Dict]) -> List[Dict]:
    """Ranqueia trends por relevância pra FraLib (matches em KEYWORDS_BASE + nichos)."""
    fralib_keywords = {
        "marketing", "vender", "venda", "vendas", "site", "sites", "ia",
        "automacao", "cliente", "clientes", "whatsapp", "leads", "prospeccao",
        "freelancer", "negocio", "negocios", "empreendedor", "empreendedorismo",
        "renda", "digital", "tecnologia", "tech", "startup", "micro",
        "seo", "google", "agente", "agentes", "ia generativa", "renda extra",
        "renda recorrente", "automacao comercial", "loja", "lojas",
    }
    for t in trends:
        text = (t["topic"] + " " + " ".join(t.get("keywords", []))).lower()
        # Score = quantas palavras de fralib aparecem
        score = sum(1 for kw in fralib_keywords if kw in text)
        t["score"] = score
    # Sort por score desc, depois por source priority (google_trends > reddit > hn)
    source_prio = {"google_trends_br": 3, "reddit_brasil": 2, "reddit_brdev": 2, "hackernews": 1}
    trends.sort(key=lambda t: (t.get("score", 0), source_prio.get(t.get("source", ""), 0)), reverse=True)
    return trends


def fetch_all_trends() -> List[Dict]:
    """Combina 3 fontes, deduplica, filtra crimes, ranqueia pra FraLib."""
    print("  Buscando trends em 3 fontes...")
    all_trends = []
    all_trends.extend(fetch_google_trends_br())
    print(f"    Google Trends BR: {len(all_trends)} topics")
    all_trends.extend(fetch_reddit_brazil())
    print(f"    Reddit: {len(all_trends) - sum(1 for t in all_trends if t.get('source','').startswith('reddit'))} novos")
    all_trends.extend(fetch_hackernews())
    print(f"    Hacker News: {len(all_trends) - sum(1 for t in all_trends if t.get('source','') == 'hackernews')} novos")

    unique = deduplicate_trends(all_trends)
    print(f"  Total unicos: {len(unique)}")

    ranked = rank_for_fralib(unique)
    return ranked


def classify_topic(topic: str) -> str:
    """Classifica tópico automaticamente."""
    t = topic.lower()
    if any(k in t for k in ["ia", "inteligência", "chatgpt", "gemini", "automação", "robô"]):
        return "ia"
    if any(k in t for k in ["marketing", "publicidade", "redes", "instagram", "tiktok"]):
        return "marketing"
    if any(k in t for k in ["venda", "e-commerce", "loja", "consumidor", "whatsapp"]):
        return "vendas"
    if any(k in t for k in ["freelancer", "autônomo", "mei", "empreendedor"]):
        return "freelancer"
    if any(k in t for k in ["tecnologia", "aplicativo", "app", "software", "startup"]):
        return "tech"
    return "negócios"


# ============================================================================
# NOTIFICAÇÃO (Webhook Slack/Discord)
# ============================================================================

def notify_new_post(slug: str, topic: str, category: str) -> None:
    """Envia notificação webhook quando novo post sai."""
    webhook = os.environ.get("WEBHOOK_URL")
    if not webhook:
        return

    try:
        import requests
        cat_name = CATEGORIES.get(category, {}).get("name", category)
        url = f"{SITE_URL}/blog/posts/{slug}.html"

        # Slack/Discord format
        payload = {
            "text": f"📝 Novo post no blog: *{topic}*\n🏷️ {cat_name}\n🔗 {url}",
        }

        requests.post(webhook, json=payload, timeout=10)
    except Exception as e:
        print(f"  Webhook error: {e}", file=sys.stderr)


# ============================================================================
# DASHBOARD DE METRICAS
# ============================================================================

def save_dashboard() -> None:
    """Salva dashboard simples com métricas do blog."""
    dashboard = BLOG_DIR / "dashboard.json"
    posts = []
    if POSTS_DIR.exists():
        for f in sorted(POSTS_DIR.glob("*.html"), reverse=True):
            posts.append({
                "slug": f.stem,
                "date": f.stat().st_mtime,
                "size_kb": round(f.stat().st_size / 1024, 1),
            })

    import time
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_posts": len(posts),
        "latest": posts[:5],
        "categories": list(CATEGORIES.keys()),
    }
    dashboard.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  Dashboard: {dashboard} ({len(posts)} posts)")


# ============================================================================
# GERADOR DE POST
# ============================================================================

def generate_post_html(topic: str, category: str, keywords: List[str], slug: str) -> str:
    """Gera HTML do post otimizado para SEO."""

    cat = CATEGORIES.get(category, CATEGORIES["marketing"])
    now = datetime.now().strftime("%Y-%m-%d")

    # Tenta usar OpenRouter se disponível
    body = call_llm_for_content(topic, category, keywords)

    # Fallback se LLM não disponível
    if not body:
        body = generate_fallback_content(topic, category, keywords)

    # P0 hotfix: html.escape em TODAS as interpolacoes que vem de fonte externa
    # (topic/keywords/slug/cat.name). Google Trends, Reddit, Hacker News sao
    # fontes nao-confiaveis e podem injetar XSS.
    _t = _he(str(topic))
    _kw = _he(', '.join(keywords))
    _slug = _he(slug)
    _cat = _he(cat['name'])
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_t} — Blog FraLib</title>
<meta name="description" content="Tudo sobre {_t}. Como usar para vender mais com o FraLib.">
<meta name="keywords" content="{_kw}">
<link rel="canonical" href="{SITE_URL}/blog/posts/{_slug}.html">
<meta property="og:title" content="{_t}">
<meta property="og:description" content="Descubra como usar {_t} para vender mais.">
<meta property="og:type" content="article">
<meta property="article:published_time" content="{now}">
<meta property="article:section" content="{_cat}">
<meta property="article:tag" content="{_he(', '.join(keywords[:3]))}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{_t}",
  "datePublished": "{now}",
  "dateModified": "{now}",
  "author": {{
    "@type": "Person",
    "name": "Franz Douglas",
    "alternateName": "Franz",
    "url": "https://seunegociofralib.site/about/",
    "worksFor": {{"@type": "Organization", "name": "FraLib OS"}}
  }},
  "publisher": {{"@type": "Organization", "name": "FraLib OS", "logo": {{"@type": "ImageObject", "url": "{SITE_URL}/images/Logo%20FraLib.png"}}}},
  "mainEntityOfPage": "{SITE_URL}/blog/posts/{_slug}.html"
}}
</script>
<link rel="stylesheet" href="/design-system.css">
<style>
body{{font-family:'DM Sans',system-ui,sans-serif;background:#0a0714;color:#f0f0f5;line-height:1.7;max-width:780px;margin:0 auto;padding:100px 24px 60px}}
h1{{font-family:'Press Start 2P',monospace;font-size:18px;line-height:1.6;color:#f0f0f5;margin-bottom:24px}}
h2{{font-size:24px;font-weight:700;color:#c084fc;margin:32px 0 16px;padding-top:16px;border-top:1px solid rgba(147,51,234,0.12)}}
p{{margin-bottom:16px;color:#f0f0f5}}
a{{color:#00FFB3;text-decoration:none}}
a:hover{{text-decoration:underline}}
.tag{{display:inline-block;padding:4px 12px;background:rgba(147,51,234,0.15);color:#c084fc;font-size:11px;font-family:'JetBrains Mono',monospace;margin-right:6px;border-radius:0}}
.meta{{color:#8888a0;font-size:13px;margin-bottom:32px;padding-bottom:16px;border-bottom:1px solid rgba(147,51,234,0.12)}}
.cta-box{{background:rgba(0,255,179,0.08);border:1px solid #00FFB3;padding:24px;margin:32px 0;border-radius:0}}
.cta-box h3{{color:#00FFB3;font-family:'Press Start 2P',monospace;font-size:12px;margin-bottom:12px}}
.cta-button{{display:inline-block;background:#FACC15;color:#000;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:10px;text-decoration:none;box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12}}
.breadcrumb{{font-size:12px;color:#8888a0;margin-bottom:24px}}
.breadcrumb a{{color:#8888a0}}
</style>
</head>
<body>
<div class="breadcrumb">
  <a href="/">Home</a> / <a href="/blog/">Blog</a> / <span>{_t}</span>
</div>

<span class="tag">{_cat}</span>
<span class="tag">{now}</span>

<h1>{_t}</h1>

<div class="meta">
  Por <strong>Franz Douglas</strong> · {now} · {len(keywords)} min de leitura
</div>

{body}

<div class="cta-box">
  <h3>QUER APLICAR ISSO NO SEU NEGOCIO?</h3>
  <p style="margin-bottom:16px">O <strong>FraLib</strong> faz exatamente isso: acha cliente, faz site, vende no WPP. Voce so fica com o lucro.</p>
  <a href="/login?signup=1&utm_source=blog&utm_medium=organic&utm_campaign=post_{_slug}" class="cta-button">TESTA 7 DIAS GRATIS</a>
</div>

<p style="margin-top:48px;padding-top:24px;border-top:1px solid rgba(147,51,234,0.12);color:#8888a0;font-size:13px">
  <em>Franz Douglas escreve sobre tecnologia, marketing e negocios no blog do FraLib OS. Quer conversar? <a href="https://wa.me/" style="color:#00FFB3">Fala no WhatsApp</a>.</em>
</p>

</body>
</html>"""

    return html


def call_llm_for_content(topic: str, category: str, keywords: List[str]) -> Optional[str]:
    """Gera conteúdo via LLM (Claude Sonnet via kpalabz).

    Returns HTML do corpo do post (sem doctype, sem h1).
    """
    try:
        import requests
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1")

        if not api_key:
            return None

        prompt = f"""Voce eh Franz Douglas, copywriter senior brasileiro. Escreva um post de blog sobre: {topic}

CATEGORIA: {category}
KEYWORDS OBRIGATORIAS: {', '.join(keywords)}

REGRAS:
- Tom direto, levemente informal, inteligente
- Frases curtas, varianca de ritmo
- Sem emoji, sem clichê motivacional
- NAO comece paragrafo com "No mundo atual", "Hoje em dia", "Voce sabia que"
- NAO use "revolution", "game-changer", "next-level"
- Exemplos concretos, casos reais, numeros quando possivel

TAMANHO: 1500-2500 palavras no HTML de saida. NAO escreva menos que isso.

ESTRUTURA:
- 2 paragrafos de intro (max 200 palavras)
- 4-6 secoes H2 (cada uma com 250-400 palavras)
- H3 dentro dos H2s quando fizer sentido
- Listas (ul/ol) quando fizer sentido
- Conclusion com CTA sutil pro FraLib

CTAs FRALIB (CRITICO):
- Mencione FraLib 1-2 vezes NO MEIO do texto de forma NATURAL
- Use hyperlink inline: <a href="/planos">anchor variando</a>
- Exemplos de anchor: "plataforma de prospeccao automatizada", "ferramenta de automacao", "sistema como o FraLib"
- NAO pareca propaganda corporativa

LISTA NEGRA (rejeitar/reescrever se aparecer):
- Crimes, homicídios, violencia, policia, trafico, drogas
- Politica partidaria, eleicoes, candidatos

FORMATO DE SAIDA:
Retorne APENAS o HTML do corpo: <p>...</p><h2>...</h2><p>...</p>...
NAO inclua doctype, head, body, style, h1, title, meta.
Apenas tags semanticas: p, h2, h3, ul, ol, li, blockquote, a, strong, em."""

        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 8000,
                "temperature": 0.7,
            },
            timeout=120,
        )

        if resp.ok:
            content = resp.json()["choices"][0]["message"]["content"]
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```html"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)
    return None


def generate_fallback_content(topic: str, category: str, keywords: List[str]) -> str:
    """Conteúdo fallback caso LLM não disponível."""

    cat = CATEGORIES.get(category, CATEGORIES["marketing"])

    return f"""
<h2>O que é {topic}?</h2>
<p>{topic} está em alta no Brasil. Cada vez mais empresas e freelancers estão usando essa estratégia para crescer mais rápido, sem aumentar equipe.</p>

<p>A ideia central é simples: automatizar o trabalho repetitivo e focar no que realmente importa — fechar vendas e entregar resultado pro cliente.</p>

<h2>Por que isso importa agora?</h2>
<p>Em 2026, o mercado brasileiro de marketing digital e vendas online não para de crescer. Quem fica parado perde espaço pra quem usa tecnologia a favor.</p>

<p>Segundo dados do setor, empresas que adotam automação crescem <strong>3x mais rápido</strong> do que as que operam 100% manual. E o melhor: sem precisar contratar mais gente.</p>

<h2>Como aplicar no seu negócio</h2>
<p>Existem 3 caminhos pra começar com {topic.lower()}:</p>
<p><strong>1. Fazer sozinho:</strong> Pesquisar, testar, errar. Funciona, mas leva meses até você ter resultado consistente.</p>
<p><strong>2. Contratar agência:</strong> Caro (R$ 2.000-5.000/mês) e você fica dependendo de terceiro.</p>
<p><strong>3. Usar plataforma automatizada:</strong> Como o <strong>FraLib</strong>, que faz tudo sozinho: acha cliente, faz site e vende no WhatsApp. Você só recebe o dinheiro.</p>

<h2>O caso do FraLib</h2>
<p>O <strong>FraLib</strong> é uma plataforma brasileira que automatiza 3 etapas críticas do seu negócio:</p>
<p>→ <strong>Acha o cliente:</strong> Varre Google Maps e encontra negócios sem site na sua região.<br>
→ <strong>Faz o site:</strong> Cria site profissional automaticão, pronto pra vender.<br>
→ <strong>Vende no WPP:</strong> Envia no WhatsApp com follow-up automático até o cliente falar "quero".</p>

<p>Você não faz NADA. Configura 1x por mês. Todo dia sai cliente novo no seu WPP querendo comprar site.</p>

<h2>Conclusão</h2>
<p>{topic} não é mais tendência — é necessidade. Quem não se adapta agora vai perder espaço nos próximos 12 meses.</p>

<p>A boa notícia: você não precisa aprender a fazer tudo sozinho. Plataformas como o FraLib existem exatamente pra isso — automatizar o trabalho pesado e te deixar com o lucro.</p>
"""


# ============================================================================
# INDEX MANAGER
# ============================================================================

def update_index_file(posts: List[Dict]) -> None:
    """Atualiza index.html do blog com lista de posts."""

    posts_html = "\n".join([
        f'''        <a href="/blog/posts/{p['slug']}.html" class="post-card">
          <div class="post-card-tag" style="background:{CATEGORIES.get(p['category'], CATEGORIES['marketing'])['color']}22;color:{CATEGORIES.get(p['category'], CATEGORIES['marketing'])['color']}">{CATEGORIES.get(p['category'], CATEGORIES['marketing'])['name']}</div>
          <h3>{p['title']}</h3>
          <p>{p['excerpt']}</p>
          <div class="post-card-meta">{p['date']} · {p['read_time']} min</div>
        </a>'''
        for p in posts[:30]  # últimos 30 posts
    ])

    today = datetime.now().strftime("%d/%m/%Y")

    index_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blog FraLib — Tendências para Vender Mais</title>
<meta name="description" content="Blog do FraLib: notícias, tendências e dicas para vender mais com IA e WhatsApp.">
<link rel="canonical" href="{SITE_URL}/blog/">
<meta property="og:title" content="Blog FraLib">
<meta property="og:description" content="Tendências e dicas para vender mais com IA.">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}/blog/">
<link rel="stylesheet" href="/design-system.css">
<style>
:root{{--fl-bg:#0a0714;--fl-bg-card:#12121a;--fl-border:rgba(147,51,234,0.12);--fl-text:#f0f0f5;--fl-text-muted:#8888a0;--fl-purple:#9333ea;--fl-purple-300:#c084fc;--cyan:#00FFB3;--gold:#FFB800}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:var(--fl-bg);color:var(--fl-text);line-height:1.7}}
header{{padding:100px 24px 40px;text-align:center;background:linear-gradient(180deg,rgba(147,51,234,0.08),transparent)}}
h1{{font-family:'Press Start 2P',monospace;font-size:clamp(14px,2.5vw,22px);line-height:1.6;margin-bottom:16px}}
header p{{color:var(--fl-text-muted);font-size:16px;max-width:600px;margin:0 auto}}
.hero-cta{{display:inline-block;background:#FACC15;color:#000;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:10px;text-decoration:none;margin-top:24px;box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12}}
.container{{max-width:1140px;margin:0 auto;padding:60px 24px}}
.posts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}}
.post-card{{background:var(--fl-bg-card);border:1px solid var(--fl-border);padding:24px;text-decoration:none;color:var(--fl-text);transition:all 220ms ease;display:flex;flex-direction:column;gap:12px}}
.post-card:hover{{border-color:rgba(147,51,234,0.5);transform:translateY(-2px)}}
.post-card-tag{{display:inline-block;padding:4px 10px;font-size:10px;font-family:'JetBrains Mono',monospace;width:fit-content;letter-spacing:0.5px}}
.post-card h3{{font-size:16px;font-weight:700;line-height:1.4}}
.post-card p{{font-size:13px;color:var(--fl-text-muted);line-height:1.5;flex:1}}
.post-card-meta{{font-size:11px;color:var(--fl-text-muted);font-family:'JetBrains Mono',monospace;padding-top:12px;border-top:1px solid var(--fl-border)}}
.empty{{text-align:center;color:var(--fl-text-muted);padding:60px 20px}}
</style>
</head>
<body>
<header>
  <h1>BLOG FRA LIB</h1>
  <p>Tendências, dicas e cases para você vender mais com IA e WhatsApp. Atualizado todo dia.</p>
  <a href="/login?signup=1&utm_source=blog_index" class="hero-cta">TESTA 7 DIAS GRÁTIS</a>
</header>

<div class="container">
  {('<div class="posts-grid">' + chr(10) + posts_html + chr(10) + '</div>') if posts else '<div class="empty"><p>Em breve: primeiros posts sendo publicados.</p></div>'}
</div>

</body>
</html>"""

    INDEX_FILE.write_text(index_html, encoding="utf-8")


def update_sitemap(posts: List[Dict]) -> None:
    """Atualiza sitemap.xml com os novos posts."""

    sitemap_path = SITEMAP_FILE
    if not sitemap_path.exists():
        return

    # Append novos URLs (sistema simples — em produção, regenerar tudo)
    # Aqui só logamos — implementação completa faria parse do XML
    print(f"  Sitemap: {len(posts)} posts disponíveis")


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Pipeline principal: gera 3 posts por execução."""

    print(f"[{datetime.now()}] Iniciando blog automation...")

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    # Combina 3 fontes: Google Trends BR + Reddit + Hacker News
    # Filtrado por BLOCKED_KEYWORDS (seguranca) + ranqueado por relevancia FraLib
    all_topics = fetch_all_trends()
    print(f"  {len(all_topics)} trends rankeados (Google Trends + Reddit + Hacker News)")

    generated_posts = []

    for i, topic_data in enumerate(all_topics[:POSTS_PER_DAY]):
        topic = topic_data["topic"]
        category = topic_data["category"]
        keywords = topic_data["keywords"]
        slug = slugify(topic)

        if has_post(slug):
            print(f"  Skip (já existe): {slug}")
            continue

        print(f"  Gerando [{i+1}/{POSTS_PER_DAY}]: {topic}")

        try:
            html = generate_post_html(topic, category, keywords, slug)
            post_file = save_post(slug, html)

            # Extrai excerpt (primeiro parágrafo)
            excerpt_match = re.search(r'<p>([^<]+)</p>', html)
            excerpt = excerpt_match.group(1)[:160] if excerpt_match else ""

            generated_posts.append({
                "slug": slug,
                "topic": topic,
                "title": topic,
                "category": category,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "read_time": "4",
                "excerpt": excerpt + "...",
            })

            print(f"    ✓ Salvo: {post_file.name}")

        except Exception as e:
            print(f"    ✗ Erro: {e}", file=sys.stderr)

    # Carrega todos os posts existentes para o index
    print(f"\nAtualizando index.html...")
    all_posts = []
    if POSTS_DIR.exists():
        for post_file in sorted(POSTS_DIR.glob("*.html"), reverse=True)[:30]:
            slug = post_file.stem
            # Lê título do post
            content = post_file.read_text(encoding="utf-8")
            title_match = re.search(r'<title>([^<]+) — Blog FraLib</title>', content)
            title = title_match.group(1) if title_match else slug
            cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
            category = next((k for k, v in CATEGORIES.items() if v["name"] == cat_match.group(1)), "marketing") if cat_match else "marketing"
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
            date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

            excerpt_match = re.search(r'<p>([^<]{50,200})</p>', content)
            excerpt = (excerpt_match.group(1)[:160] + "...") if excerpt_match else ""

            all_posts.append({
                "slug": slug,
                "title": title,
                "category": category,
                "date": date,
                "read_time": "4",
                "excerpt": excerpt,
            })

    update_index_file(all_posts)
    update_sitemap(generated_posts)
    save_dashboard()

    # Notificação webhook (best-effort, nao quebra o flow)
    for post in generated_posts:
        try:
            notify_new_post(post["slug"], post.get("topic", post.get("title", "")), post.get("category", "marketing"))
        except Exception as e:
            print(f"  Notification error: {e}", file=sys.stderr)

    print(f"\n[OK] Concluido: {len(generated_posts)} posts novos, {len(all_posts)} total no blog")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
