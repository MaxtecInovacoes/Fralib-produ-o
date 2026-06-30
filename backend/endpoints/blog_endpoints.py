"""
Blog Automático — Gera artigos SEO 3x/dia com trending topics.
Pesquisa hype do momento (IA, automação, renda extra) e gera conteúdo
que atrai visitantes e puxa pra venda dos planos FraLib.

Endpoints:
  POST /api/cron/blog-generate  — chamado por cron 3x/dia
  POST /api/blog/generate       — manual (superadmin)
  GET  /api/blog/articles       — lista artigos gerados
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from backend.core.database import engine
from llm_direct import call_claude

router = APIRouter(tags=['blog'])

CRON_SECRET = os.getenv('CRON_SECRET', '')
BLOG_DIR = Path('/var/www/fralib/blog')
BLOG_INDEX = BLOG_DIR / 'index.html'

# Keywords base que sempre devem aparecer nos artigos
KEYWORDS_BASE = [
    "vender sites", "negocios locais", "inteligencia artificial",
    "automacao", "renda extra", "freelancer", "WhatsApp vendas",
    "criar site com IA", "prospectar clientes", "SDR automatico"
]

# Temas trending que o sistema pesquisa (atualizar periodicamente)
TRENDING_TOPICS = [
    "Claude AI", "GPT-5", "DeepSeek", "Gemini 2", "automacao com IA 2026",
    "agentes autonomos", "vender servicos digitais", "micro SaaS",
    "no-code", "IA para pequenas empresas", "marketing digital IA",
    "chatbot WhatsApp", "landing page IA", "SEO automatico",
    "renda passiva digital", "freelancer IA", "sites one-page",
    "negocio local sem site", "Google Maps prospeccao",
    "IA generativa Brasil", "automacao vendas", "cold outreach IA"
]

INTERNAL_LINKS = {
    "vender sites": "/blog/como-vender-sites-para-negocios-locais.html",
    "quanto cobrar": "/blog/quanto-cobrar-por-site-de-restaurante.html",
    "SDR": "/docs/sdr-bryan.html",
    "WhatsApp": "/blog/whatsapp-vendas-automatizar-sem-banir.html",
    "pipeline": "/docs/pipeline.html",
    "planos": "/planos",
    "como funciona": "/docs/como-funciona.html",
    "negocios locais": "/blog/nicho-sites-negocios-locais-2026.html",
    "freelancer": "/blog/freelancer-sites-como-ganhar-5000-por-mes.html",
    "Google Maps": "/blog/encontrar-negocios-sem-site-google-maps.html",
    "criar site com IA": "/blog/criar-site-com-inteligencia-artificial.html",
    "FraLib": "/planos",
    "trial": "/planos",
}

ARTICLE_SYSTEM_PROMPT = """Voce e um copywriter SEO senior especializado em marketing digital e tecnologia.
Escreva artigos para o blog da FraLib OS — uma plataforma que automatiza vendas de sites para negocios locais usando IA.

REGRAS:
1. Titulo: H1 com keyword principal, max 60 chars, sem emojis
2. Meta description: 150-160 chars, com keyword, call-to-action sutil
3. Estrutura: H1 > intro (2 paragrafos) > H2 (3-5 secoes) > H3 dentro de H2s > CTA final
4. Tom: informativo, direto, sem enrolacao. Dados concretos > promessas vagas.
5. Tamanho: 1200-1800 palavras
6. Keywords: distribuir naturalmente no texto (keyword principal no H1, primeiro paragrafo, 1 H2, ultimo paragrafo)
7. NUNCA usar emojis no texto
8. NUNCA inventar estatisticas sem fonte
9. Sempre mencionar FraLib OS como solucao no contexto (1-2x no artigo, natural, nao forcado)
10. CTA final: convidar a testar gratis, link para /planos
11. Linguagem: portugues BR, informal-profissional, sem gírias excessivas
12. SEO: usar variações da keyword (sinonimos, long-tail) nos H2s
13. Atualidade: mencionar ano 2026, tendencias atuais, ferramentas reais

FORMATO DE SAIDA (JSON):
{
  "titulo": "...",
  "meta_description": "...",
  "slug": "...",
  "keywords": ["kw1", "kw2", "kw3"],
  "conteudo_html": "<h1>...</h1><p>...</p><h2>...</h2>..."
}

O conteudo_html deve ser APENAS o corpo do artigo (h1, p, h2, h3, ul, ol, blockquote).
NAO incluir html/head/body/style. Apenas tags de conteudo semantico."""


def _autorizar_cron(x_cron_secret: str):
    if not CRON_SECRET:
        raise HTTPException(500, 'CRON_SECRET nao configurado')
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(403, 'Cron secret invalido')


def _escolher_tema():
    """Escolhe tema baseado no dia/hora pra variar."""
    import hashlib
    seed = datetime.now().strftime("%Y%m%d%H")
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(TRENDING_TOPICS)
    topic = TRENDING_TOPICS[idx]
    # Combinar com keyword base
    kw_idx = int(hashlib.md5((seed + "kw").encode()).hexdigest(), 16) % len(KEYWORDS_BASE)
    keyword = KEYWORDS_BASE[kw_idx]
    return topic, keyword


def _injetar_links_internos(html):
    """Injeta hiperlinks internos automaticamente no conteudo."""
    for termo, url in INTERNAL_LINKS.items():
        # Só linkar primeira ocorrência, case-insensitive
        pattern = re.compile(r'(?<!["\'/])(' + re.escape(termo) + r')(?!["\'/])', re.IGNORECASE)
        match = pattern.search(html)
        if match:
            original = match.group(1)
            link = f'<a href="{url}" style="color:var(--fl-purple-400);text-decoration:underline">{original}</a>'
            html = html[:match.start()] + link + html[match.end():]
    return html


def _gerar_html_artigo(data):
    """Monta HTML completo do artigo com template do blog."""
    titulo = data["titulo"]
    meta = data["meta_description"]
    slug = data["slug"]
    keywords = data.get("keywords", [])
    conteudo = data["conteudo_html"]
    data_pub = datetime.now().strftime("%d %b %Y")
    url_canonical = f"https://seunegociofralib.site/blog/{slug}.html"

    # Injetar links internos
    conteudo = _injetar_links_internos(conteudo)

    # Calcular tempo de leitura
    word_count = len(re.findall(r'\w+', conteudo))
    read_time = max(3, word_count // 200)

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": titulo,
        "description": meta,
        "url": url_canonical,
        "datePublished": datetime.now().strftime("%Y-%m-%d"),
        "author": {"@type": "Organization", "name": "FraLib OS"},
        "publisher": {"@type": "Organization", "name": "FraLib OS", "url": "https://seunegociofralib.site"},
        "keywords": ", ".join(keywords)
    }, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo} | FraLib OS</title>
<meta name="description" content="{meta}">
<meta name="keywords" content="{', '.join(keywords)}">
<link rel="canonical" href="{url_canonical}">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{meta}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url_canonical}">
<meta property="og:site_name" content="FraLib OS">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/reading.css">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--fl-bg:#0a0714;--fl-bg-card:#12121a;--fl-bg-hover:#1c1c28;--fl-purple-600:#7c3aed;--fl-purple:#9333ea;--fl-purple-400:#a855f7;--fl-purple-300:#c084fc;--fl-border:rgba(147,51,234,0.12);--fl-text:#f0f0f5;--fl-text-muted:#8888a0;--fl-text-dim:#44445a;--fl-font-brand:'Press Start 2P',monospace;--fl-font-ui:'DM Sans',system-ui,sans-serif;--fl-font-mono:'JetBrains Mono',monospace;--fl-ease:cubic-bezier(0.22,1,0.36,1)}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--fl-font-ui);background:var(--fl-bg);color:var(--fl-text);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}}
nav{{position:fixed;top:0;left:0;right:0;z-index:1000;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:14px 32px;background:rgba(6,6,8,0.75);backdrop-filter:blur(20px);border-bottom:1px solid var(--fl-border)}}
.nav-brand{{display:flex;align-items:center;text-decoration:none}}
.nav-brand img{{height:36px;filter:drop-shadow(0 0 8px rgba(147,51,234,0.4))}}
.nav-links{{display:flex;gap:28px;align-items:center;justify-self:center}}
.nav-links a{{color:var(--fl-text-muted);text-decoration:none;font-size:13px;font-weight:500}}
.nav-links a:hover{{color:var(--fl-text)}}
.nav-cta{{padding:12px 24px;font-family:var(--fl-font-brand);font-size:9px;background:#FACC15;color:#000;text-decoration:none;box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12;letter-spacing:1px}}
.article-content{{max-width:780px;margin:0 auto;padding:100px 1.5rem 3rem;line-height:1.8}}
.article-content h1{{font-family:var(--fl-font-brand);font-size:clamp(10px,1.8vw,15px);line-height:2.2;margin-bottom:0.5rem}}
.article-content .article-meta{{color:var(--fl-text-dim);font-size:0.85rem;font-family:var(--fl-font-mono);margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid var(--fl-border)}}
.article-content h2{{font-size:1.4rem;font-weight:700;color:var(--fl-purple-400);margin-top:2.5rem;margin-bottom:1rem}}
.article-content h3{{font-size:1.1rem;font-weight:600;margin-top:1.5rem;margin-bottom:0.5rem}}
.article-content p{{margin-bottom:1.2rem}}
.article-content ul,.article-content ol{{margin-bottom:1.2rem;padding-left:1.5rem}}
.article-content li{{margin-bottom:0.4rem}}
.article-content strong{{color:var(--fl-purple-300)}}
.article-content blockquote{{border-left:3px solid var(--fl-purple-600);padding:1rem 1.5rem;margin:1.5rem 0;background:var(--fl-bg-card);border-radius:0 10px 10px 0}}
.article-content a{{color:var(--fl-purple-400);text-decoration:underline}}
.cta-box{{background:rgba(18,18,26,0.6);backdrop-filter:blur(16px);border:1px solid rgba(147,51,234,0.3);border-radius:14px;padding:2rem;margin:2.5rem 0;text-align:center}}
.cta-box h3{{color:var(--fl-purple-400);margin-bottom:0.5rem}}
.cta-box p{{color:var(--fl-text-muted);font-size:0.9rem;margin-bottom:1rem}}
.cta-box .btn{{display:inline-flex;padding:16px 32px;font-family:var(--fl-font-brand);font-size:11px;text-decoration:none;color:#000;background:#FACC15;box-shadow:inset -4px -4px 0 #A16207,inset 4px 4px 0 #FDE68A,0 6px 0 #713F12}}
#particles-canvas{{position:fixed;inset:0;z-index:0;pointer-events:none}}
@media(max-width:768px){{.nav-links{{display:none}}.article-content{{padding-top:80px}}}}
</style>
</head>
<body>
<canvas id="particles-canvas"></canvas>
<nav>
  <div style="justify-self:start"><a href="/" class="nav-brand"><img src="/images/Logo FraLib.png" alt="FraLib" height="36"></a></div>
  <div class="nav-links"><a href="/">Home</a><a href="/docs/">Docs</a><a href="/blog/">Blog</a><a href="/planos">Planos</a></div>
  <div style="justify-self:end;display:flex;align-items:center;gap:16px"><a href="/login" style="color:var(--fl-text-muted);text-decoration:none;font-size:12px;font-weight:600">ENTRAR</a><a href="/login?signup=1" class="nav-cta">CRIAR CONTA</a></div>
</nav>
<article class="article-content">
  <a href="/blog/" style="font-size:0.85rem;font-family:var(--fl-font-mono)">&larr; Voltar para o Blog</a>
  <h1>{titulo}</h1>
  <div class="article-meta"><span>{data_pub}</span> | <span>Leitura: {read_time} minutos</span></div>
  {conteudo}
  <div class="cta-box">
    <h3>Pronto para automatizar suas vendas?</h3>
    <p>Teste o FraLib OS gratis. Crie seu primeiro site com IA em 5 minutos.</p>
    <a href="/planos" class="btn">VER PLANOS</a>
  </div>
</article>
<script>
(function(){{const c=document.getElementById('particles-canvas');if(!c)return;const x=c.getContext('2d');let W,H,p=[];function r(){{W=c.width=innerWidth;H=c.height=innerHeight}}function rn(a,b){{return Math.random()*(b-a)+a}}function i(){{p=[];const n=Math.min(Math.floor((W*H)/14000),60);for(let j=0;j<n;j++)p.push({{x:rn(0,W),y:rn(0,H),vx:rn(-.12,.12),vy:rn(-.12,.12),s:rn(.6,1.4),a:rn(.15,.5)}})}}function d(){{x.clearRect(0,0,W,H);p.forEach(pt=>{{pt.x+=pt.vx;pt.y+=pt.vy;if(pt.x<0)pt.x=W;if(pt.x>W)pt.x=0;if(pt.y<0)pt.y=H;if(pt.y>H)pt.y=0;x.beginPath();x.arc(pt.x,pt.y,pt.s,0,Math.PI*2);x.fillStyle=`rgba(192,132,252,${{pt.a}})`;x.fill()}});requestAnimationFrame(d)}}addEventListener('resize',()=>{{r();i()}});r();i();d()}})();
</script>
</body>
</html>'''
    return html


def _atualizar_blog_index(slug, titulo, meta, read_time):
    """Adiciona novo artigo card ao blog/index.html."""
    if not BLOG_INDEX.exists():
        return

    index_html = BLOG_INDEX.read_text(encoding='utf-8')
    data_pub = datetime.now().strftime("%d %b %Y")

    new_card = f'''    <article class="article-card">
      <h2><a href="/blog/{slug}.html">{titulo}</a></h2>
      <p class="excerpt">{meta}</p>
      <span class="meta">{data_pub} · {read_time} min de leitura</span>
    </article>'''

    # Inserir após o primeiro article-card (topo da lista)
    insert_marker = '<div class="article-list">'
    if insert_marker in index_html:
        index_html = index_html.replace(
            insert_marker,
            insert_marker + '\n' + new_card,
            1
        )
        BLOG_INDEX.write_text(index_html, encoding='utf-8')
        print(f"[Blog] Index atualizado com: {slug}")


def _gerar_artigo(topic=None, keyword=None):
    """Gera um artigo completo e salva no blog."""
    if not topic or not keyword:
        topic, keyword = _escolher_tema()

    prompt = f"""Gere um artigo de blog sobre o tema: "{topic}"
Keyword principal SEO: "{keyword}"
Keywords secundarias para incluir naturalmente: {', '.join(KEYWORDS_BASE[:5])}

Contexto: O FraLib OS e uma plataforma que automatiza a venda de sites para negocios locais.
Ela prospecta negocios sem site no Google Maps, cria sites com 7 agentes de IA, e envia pelo WhatsApp com um SDR automatico (Franz).
Planos: Trial (gratis, 1 site), Starter (R$97/mes), Pro (R$197/mes), Ilimitado (R$497/mes).

O artigo deve conectar o tema trending ({topic}) com o universo de vender sites/automacao/IA.
Fale sobre tendencias atuais de 2026, mencione ferramentas reais (Claude, GPT, DeepSeek, etc).
Sempre puxe para a solucao FraLib de forma natural (nao forcada).

Retorne APENAS o JSON no formato especificado."""

    try:
        resposta = call_claude(
            system=ARTICLE_SYSTEM_PROMPT,
            user=prompt,
            model="sonnet",
            max_tokens=6000,
            temperature=0.7,
        )

        # Parse JSON da resposta
        json_match = re.search(r'\{[\s\S]*\}', resposta)
        if not json_match:
            print("[Blog] Erro: resposta sem JSON valido")
            return None

        data = json.loads(json_match.group())

        if not all(k in data for k in ('titulo', 'meta_description', 'slug', 'conteudo_html')):
            print("[Blog] Erro: JSON incompleto")
            return None

        # Sanitizar slug
        slug = re.sub(r'[^a-z0-9-]', '', data['slug'].lower().replace(' ', '-'))
        data['slug'] = slug

        # Gerar HTML completo
        html_final = _gerar_html_artigo(data)

        # Salvar arquivo
        BLOG_DIR.mkdir(parents=True, exist_ok=True)
        filepath = BLOG_DIR / f"{slug}.html"
        filepath.write_text(html_final, encoding='utf-8')

        # Atualizar index
        word_count = len(re.findall(r'\w+', data['conteudo_html']))
        read_time = max(3, word_count // 200)
        _atualizar_blog_index(slug, data['titulo'], data['meta_description'], read_time)

        print(f"[Blog] Artigo gerado: {slug}.html ({len(html_final):,} chars)")

        # Registrar no banco
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO blog_articles (slug, titulo, meta_description, keywords, gerado_em, topic, filepath)
                    VALUES (:slug, :titulo, :meta, :kw, NOW(), :topic, :fp)
                    ON CONFLICT (slug) DO UPDATE SET gerado_em = NOW()
                """), {
                    "slug": slug,
                    "titulo": data['titulo'],
                    "meta": data['meta_description'],
                    "kw": json.dumps(data.get('keywords', [])),
                    "topic": topic,
                    "fp": str(filepath),
                })
                conn.commit()
        except Exception as e:
            # Tabela pode não existir ainda — não bloquear
            print(f"[Blog] DB registro falhou (ok se tabela nao existe): {e}")

        return {
            "slug": slug,
            "titulo": data['titulo'],
            "url": f"/blog/{slug}.html",
            "keywords": data.get('keywords', []),
        }

    except Exception as e:
        print(f"[Blog] Erro ao gerar artigo: {e}")
        return None


# === ENDPOINTS ===

@router.post('/api/cron/blog-generate')
async def cron_blog_generate(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Gera 1 artigo automaticamente. Chamado por cron 3x/dia."""
    _autorizar_cron(x_cron_secret)
    result = _gerar_artigo()
    if result:
        return {"ok": True, "artigo": result}
    raise HTTPException(500, "Falha ao gerar artigo")


@router.post('/api/blog/generate')
async def manual_blog_generate(
    topic: str = None,
    keyword: str = None,
    x_cron_secret: str = Header(None, alias='X-Cron-Secret')
):
    """Gera artigo manualmente (superadmin). Aceita topic/keyword custom."""
    _autorizar_cron(x_cron_secret)
    result = _gerar_artigo(topic=topic, keyword=keyword)
    if result:
        return {"ok": True, "artigo": result}
    raise HTTPException(500, "Falha ao gerar artigo")


@router.get('/api/blog/articles')
async def list_blog_articles():
    """Lista artigos do blog (público, pra SEO sitemap)."""
    articles = []
    if BLOG_DIR.exists():
        for f in sorted(BLOG_DIR.glob('*.html'), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.name == 'index.html':
                continue
            articles.append({
                "slug": f.stem,
                "url": f"/blog/{f.name}",
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"articles": articles, "total": len(articles)}
