#!/usr/bin/env python3
"""
Blog Automatizado FraLib OS
- Busca tendências do Google Trends Brasil
- Gera post otimizado para SEO
- Salva como HTML em frontend/blog/posts/
- Atualiza index.html automaticamente

Cron: 0 8 * * * (todo dia 8h)
"""

import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
INDEX_FILE = BLOG_DIR / "index.html"
SITEMAP_FILE = BLOG_DIR.parent / "sitemap.xml"

SITE_URL = "https://seunegociofralib.site"
POSTS_PER_DAY = 3

# Categorias de negócio válidas
CATEGORIES = {
    "marketing": {"name": "Marketing", "color": "#9333ea"},
    "ia": {"name": "IA & Automação", "color": "#00FFB3"},
    "vendas": {"name": "Vendas", "color": "#FFB800"},
    "freelancer": {"name": "Freelancer", "color": "#7c3aed"},
    "tech": {"name": "Tecnologia", "color": "#c084fc"},
    "negócios": {"name": "Negócios", "color": "#22d3a0"},
}

# ============================================================================
# TENDÊNCIAS (simuladas - em produção, integra com Google Trends API)
# ============================================================================

TRENDING_TOPICS = [
    {
        "topic": "Automação com IA para PMEs",
        "category": "ia",
        "keywords": ["automação", "ia", "pequenas empresas", "pmarketing"],
        "intent": "search",
    },
    {
        "topic": "WhatsApp Business API 2024",
        "category": "vendas",
        "keywords": ["whatsapp", "business", "api", "vendas"],
        "intent": "commercial",
    },
    {
        "topic": "Gerador de sites com IA",
        "category": "tech",
        "keywords": ["site", "ia", "gerador", "criar site"],
        "intent": "commercial",
    },
    {
        "topic": "SDR de IA: o vendedor que nunca dorme",
        "category": "ia",
        "keywords": ["sdr", "ia", "whatsapp", "vendas automáticas"],
        "intent": "commercial",
    },
    {
        "topic": "Google Maps como máquina de leads",
        "category": "marketing",
        "keywords": ["google maps", "leads", "prospecção", "negócios locais"],
        "intent": "commercial",
    },
    {
        "topic": "Como cobrar R$1.500 por site em 2026",
        "category": "freelancer",
        "keywords": ["preço", "site", "freelancer", "tabela"],
        "intent": "commercial",
    },
    {
        "topic": "Prospecção B2B que funciona sem LinkedIn",
        "category": "vendas",
        "keywords": ["prospecção", "b2b", "whatsapp", "leads"],
        "intent": "commercial",
    },
    {
        "topic": "Site que vende: 7 erros que freelancers cometem",
        "category": "marketing",
        "keywords": ["site", "erros", "freelancer", "vendas"],
        "intent": "informational",
    },
    {
        "topic": "Como automatizar 100% do funil de vendas",
        "category": "ia",
        "keywords": ["automação", "funil", "vendas", "ia"],
        "intent": "commercial",
    },
    {
        "topic": "FraLib OS: o case que mudou a prospecção no Brasil",
        "category": "tech",
        "keywords": ["fralib", "prospecção", "ia", "case"],
        "intent": "informational",
    },
    {
        "topic": "Quanto cobrar por gestão de WhatsApp em 2026",
        "category": "freelancer",
        "keywords": ["whatsapp", "gestão", "freelancer", "preço"],
        "intent": "commercial",
    },
    {
        "topic": "Marketing digital para freelancers: o que mudou",
        "category": "marketing",
        "keywords": ["marketing", "freelancer", "2026", "tendências"],
        "intent": "informational",
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

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{topic} — Blog FraLib</title>
<meta name="description" content="Tudo sobre {topic}. Como usar para vender mais com o FraLib.">
<meta name="keywords" content="{', '.join(keywords)}">
<link rel="canonical" href="{SITE_URL}/blog/posts/{slug}.html">
<meta property="og:title" content="{topic}">
<meta property="og:description" content="Descubra como usar {topic} para vender mais.">
<meta property="og:type" content="article">
<meta property="article:published_time" content="{now}">
<meta property="article:section" content="{cat['name']}">
<meta property="article:tag" content="{', '.join(keywords[:3])}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{topic}",
  "datePublished": "{now}",
  "author": {{"@type": "Organization", "name": "FraLib OS"}},
  "publisher": {{"@type": "Organization", "name": "FraLib OS", "logo": {{"@type": "ImageObject", "url": "{SITE_URL}/images/Logo%20FraLib.png"}}}},
  "mainEntityOfPage": "{SITE_URL}/blog/posts/{slug}.html"
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
  <a href="/">Home</a> / <a href="/blog/">Blog</a> / <span>{topic}</span>
</div>

<span class="tag">{cat['name']}</span>
<span class="tag">{now}</span>

<h1>{topic}</h1>

<div class="meta">
  Por <strong>FraLib OS</strong> · {now} · {len(keywords)} min de leitura
</div>

{body}

<div class="cta-box">
  <h3>QUER APLICAR ISSO NO SEU NEGÓCIO?</h3>
  <p style="margin-bottom:16px">O <strong>FraLib</strong> faz exatamente isso: acha cliente, faz site, vende no WPP. Você só fica com o lucro.</p>
  <a href="/login?signup=1&utm_source=blog&utm_medium=organic&utm_campaign=post_{slug}" class="cta-button">TESTA 7 DIAS GRÁTIS</a>
</div>

<p style="margin-top:48px;padding-top:24px;border-top:1px solid rgba(147,51,234,0.12);color:#8888a0;font-size:13px">
  <em>Post gerado automaticamente pelo FraLib. Conteúdo educativo baseado em tendências do mercado.</em>
</p>

</body>
</html>"""

    return html


def call_llm_for_content(topic: str, category: str, keywords: List[str]) -> Optional[str]:
    """Tenta gerar conteúdo via LLM (kpalabz)."""
    try:
        import requests
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1")

        if not api_key:
            return None

        prompt = f"""Escreva um post de blog em português brasileiro sobre: {topic}

Estrutura:
- Introdução (1 parágrafo)
- 3-4 seções com h2 explicando o tema
- Conclusão com CTA para o FraLib

Tom: Conversa, direto, sem palavras Facebook rejeita.
Tamanho: 500-700 palavras.
Use as keywords: {', '.join(keywords)}
Mencione o FraLib na conclusão.

Retorne APENAS o HTML com h2 e p, sem doctype."""

        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2500,
            },
            timeout=60,
        )

        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"]
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

    generated_posts = []

    for i, topic_data in enumerate(TRENDING_TOPICS[:POSTS_PER_DAY]):
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

    print(f"\n[OK] Concluido: {len(generated_posts)} posts novos, {len(all_posts)} total no blog")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
