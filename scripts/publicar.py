#!/usr/bin/env python3
"""
Publicador estático: atualiza index.html e sitemap.xml.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
INDEX_FILE = BLOG_DIR / "index.html"
SITEMAP_FILE = BLOG_DIR.parent / "sitemap.xml"

SITE_URL = "https://seunegociofralib.site"

CATEGORIES = {
    "marketing": {"name": "Marketing", "color": "#9333ea"},
    "ia": {"name": "IA & Automação", "color": "#00FFB3"},
    "vendas": {"name": "Vendas", "color": "#FFB800"},
    "freelancer": {"name": "Freelancer", "color": "#7c3aed"},
    "tech": {"name": "Tecnologia", "color": "#c084fc"},
    "negócios": {"name": "Negócios", "color": "#22d3a0"},
    "finanças": {"name": "Finanças", "color": "#FF6B6B"},
    "produtividade": {"name": "Produtividade", "color": "#4ECDC4"},
}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:80]


def load_all_posts() -> List[Dict]:
    """Carrega todos os posts do diretório."""
    posts = []
    if not POSTS_DIR.exists():
        return posts

    for post_file in sorted(POSTS_DIR.glob("*.html"), reverse=True):
        try:
            content = post_file.read_text(encoding="utf-8")
            slug = post_file.stem

            # Extrai metadados
            title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", content)
            title = title_match.group(1) if title_match else slug.replace("-", " ").title()

            desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
            excerpt = desc_match.group(1) if desc_match else title

            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", post_file.name + " " + content[:5000])
            date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

            cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
            cat_name = cat_match.group(1) if cat_match else "Negócios"
            category = next((k for k, v in CATEGORIES.items() if v["name"] == cat_name), "negócios")

            read_match = re.search(r"(\d+) min de leitura", content)
            read_time = read_match.group(1) if read_match else "3"

            posts.append({
                "slug": slug,
                "title": title,
                "excerpt": excerpt,
                "date": date,
                "read_time": read_time,
                "category": category,
            })
        except Exception as e:
            print(f"  Erro ao ler {post_file.name}: {e}", file=sys.stderr)

    return posts


def update_index(posts: List[Dict]) -> None:
    """Atualiza index.html com lista de posts."""

    posts_html = "\n".join([
        f'''        <a href="/blog/posts/{p['slug']}.html" class="post-card">
          <div class="post-tag" style="background:{CATEGORIES.get(p['category'], CATEGORIES['negócios'])['color']}22;color:{CATEGORIES.get(p['category'], CATEGORIES['negócios'])['color']};border:1px solid {CATEGORIES.get(p['category'], CATEGORIES['negócios'])['color']}55">
            {CATEGORIES.get(p['category'], CATEGORIES['negócios'])['name']}
          </div>
          <h3>{p['title']}</h3>
          <p class="post-excerpt">{p['excerpt']}</p>
          <div class="post-meta">
            <span>{p['date']}</span>
            <span>·</span>
            <span>{p['read_time']} min</span>
          </div>
        </a>'''
        for p in posts[:30]
    ])

    count = len(posts)

    index_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blog FraLib — Tendências, Dicas e Cases</title>
<meta name="description" content="Blog do FraLib OS. Tendências, dicas e cases para vender mais usando IA, WhatsApp e automação.">
<meta name="keywords" content="blog marketing digital, blog freelancer, blog vendas, blog ia, blog fralib">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE_URL}/blog/">

<meta property="og:title" content="Blog FraLib — Tendências, Dicas e Cases">
<meta property="og:description" content="Tendências, dicas e cases para vender mais.">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}/blog/">
<meta property="og:image" content="{SITE_URL}/images/og-blog-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Blog FraLib">
<meta name="twitter:description" content="Tendências, dicas e cases para vender mais.">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Blog",
  "name": "Blog FraLib",
  "description": "Tendências, dicas e cases para vender mais com IA e automação.",
  "url": "{SITE_URL}/blog/",
  "publisher": {{
    "@type": "Organization",
    "name": "FraLib OS",
    "logo": {{
      "@type": "ImageObject",
      "url": "{SITE_URL}/images/Logo%20FraLib.png"
    }}
  }}
}}
</script>

<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '1022692323751129');
fbq('track', 'PageView');
</script>

<link rel="stylesheet" href="/design-system.css">
<style>
:root{{--fl-bg:#0a0714;--fl-bg-card:#12121a;--fl-bg-hover:#1c1c28;--fl-border:rgba(147,51,234,0.12);--fl-text:#f0f0f5;--fl-text-muted:#8888a0;--fl-text-dim:#44445a;--fl-purple:#9333ea;--fl-purple-300:#c084fc;--cyan:#00FFB3;--gold:#FFB800}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:var(--fl-bg);color:var(--fl-text);line-height:1.7;min-height:100vh}}
nav{{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;justify-content:space-between;align-items:center;padding:14px 32px;background:rgba(6,6,8,0.95);backdrop-filter:blur(20px);border-bottom:1px solid var(--fl-border)}}
.nav-brand{{font-family:'Press Start 2P',monospace;font-size:14px;color:var(--cyan);text-decoration:none}}
.nav-cta{{padding:10px 18px;background:#FACC15;color:#000;font-family:'Press Start 2P',monospace;font-size:8px;text-decoration:none;box-shadow:inset -2px -2px 0 #A16207,inset 2px 2px 0 #FDE68A,0 3px 0 #713F12;letter-spacing:0.5px}}
header.hero{{padding:140px 24px 60px;text-align:center;background:linear-gradient(180deg,rgba(147,51,234,0.08) 0%,transparent 100%);border-bottom:1px solid var(--fl-border)}}
h1{{font-family:'Press Start 2P',monospace;font-size:clamp(14px,2.5vw,22px);line-height:1.6;margin-bottom:20px;max-width:680px;margin-left:auto;margin-right:auto}}
header.hero p{{color:var(--fl-text-muted);font-size:16px;max-width:580px;margin:0 auto 28px;line-height:1.6}}
.hero-cta{{display:inline-block;background:#FACC15;color:#000;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:10px;text-decoration:none;letter-spacing:1px;box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12}}
.hero-cta:hover{{background:#FDE047}}
.container{{max-width:1140px;margin:0 auto;padding:60px 24px}}
.posts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}}
.post-card{{background:var(--fl-bg-card);border:1px solid var(--fl-border);padding:24px;text-decoration:none;color:var(--fl-text);transition:all 220ms ease;display:flex;flex-direction:column;gap:12px;min-height:220px}}
.post-card:hover{{border-color:rgba(147,51,234,0.5);transform:translateY(-2px);background:var(--fl-bg-hover)}}
.post-tag{{display:inline-block;padding:4px 10px;font-size:10px;font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;width:fit-content;text-transform:uppercase}}
.post-card h3{{font-size:17px;font-weight:700;line-height:1.4;color:var(--fl-text);margin:4px 0}}
.post-excerpt{{font-size:13px;color:var(--fl-text-muted);line-height:1.5;flex:1}}
.post-meta{{font-size:11px;color:var(--fl-text-dim);font-family:'JetBrains Mono',monospace;padding-top:12px;border-top:1px solid var(--fl-border);display:flex;gap:6px}}
.empty{{text-align:center;padding:80px 20px;color:var(--fl-text-muted)}}
.empty h2{{font-family:'Press Start 2P',monospace;font-size:12px;color:var(--fl-text);margin-bottom:16px}}
.stats{{display:flex;justify-content:center;gap:32px;padding:32px 24px;background:var(--fl-bg-card);border-top:1px solid var(--fl-border);border-bottom:1px solid var(--fl-border);margin:40px 0;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--fl-text-muted)}}
.stat strong{{display:block;color:var(--cyan);font-size:24px;font-family:'Press Start 2P',monospace;margin-bottom:4px}}
footer{{background:linear-gradient(180deg,var(--fl-bg) 0%,#060410 100%);border-top:1px solid var(--fl-border);padding:40px 24px;text-align:center;color:var(--fl-text-muted);font-size:13px}}
footer a{{color:var(--cyan);text-decoration:none;margin:0 12px}}
@media(max-width:768px){{.posts-grid{{grid-template-columns:1fr}}nav{{padding:10px 18px}}}}
</style>
</head>
<body>
<nav>
  <a href="/" class="nav-brand">FRA LIB</a>
  <a href="/login?signup=1&utm_source=blog_index" class="nav-cta">TESTAR GRÁTIS</a>
</nav>

<header class="hero">
  <h1>BLOG FRA LIB</h1>
  <p>Tendências, dicas e cases reais sobre IA, vendas e marketing digital. Atualizado toda semana. Tom humano, sem enrolação.</p>
  <a href="/login?signup=1&utm_source=blog_hero" class="hero-cta">TESTA 7 DIAS GRÁTIS →</a>
</header>

<div class="stats">
  <div class="stat">
    <strong>{count}</strong>
    posts publicados
  </div>
  <div class="stat">
    <strong>1x</strong>
    novo post por dia
  </div>
  <div class="stat">
    <strong>100%</strong>
    escrito com tom humano
  </div>
</div>

<div class="container">
  {('<div class="posts-grid">' + chr(10) + posts_html + chr(10) + '</div>') if posts else '<div class="empty"><h2>EM BREVE</h2><p>Os primeiros posts estão sendo escritos. Volta aqui amanhã!</p></div>'}
</div>

<footer>
  <p>© 2026 FraLib OS. <a href="/">Home</a> · <a href="/blog/">Blog</a> · <a href="/blog/rss.xml">RSS</a> · <a href="/login?signup=1&utm_source=blog_footer">Testar Grátis</a></p>
</footer>
</body>
</html>"""

    INDEX_FILE.write_text(index_html, encoding="utf-8")
    print(f"  Index atualizado: {INDEX_FILE} ({count} posts)")


def update_sitemap(posts: List[Dict]) -> None:
    """Atualiza sitemap.xml com URLs dos posts."""

    if not SITEMAP_FILE.exists():
        return

    # Lê sitemap existente
    content = SITEMAP_FILE.read_text(encoding="utf-8")

    # Adiciona URLs do blog (se não existirem)
    new_urls = []
    for post in posts:
        url = f"{SITE_URL}/blog/posts/{post['slug']}.html"
        if url not in content:
            url_xml = f"""  <url>
    <loc>{url}</loc>
    <lastmod>{post['date']}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>"""
            new_urls.append(url_xml)

    if new_urls:
        # Inserir antes de </urlset>
        content = content.replace("</urlset>", "\n".join(new_urls) + "\n</urlset>")
        SITEMAP_FILE.write_text(content, encoding="utf-8")
        print(f"  Sitemap: {len(new_urls)} URLs adicionadas")


def create_rss_feed(posts: List[Dict]) -> None:
    """Cria feed RSS para o blog."""

    rss_file = BLOG_DIR / "rss.xml"

    items = "\n".join([
        f"""    <item>
      <title>{p['title']}</title>
      <link>{SITE_URL}/blog/posts/{p['slug']}.html</link>
      <description>{p['excerpt']}</description>
      <pubDate>{p['date']}</pubDate>
      <guid isPermaLink="true">{SITE_URL}/blog/posts/{p['slug']}.html</guid>
    </item>"""
        for p in posts[:20]
    ])

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Blog FraLib</title>
    <link>{SITE_URL}/blog/</link>
    <description>Tendências, dicas e cases sobre IA, vendas e marketing digital.</description>
    <language>pt-BR</language>
    <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
{items}
  </channel>
</rss>"""

    rss_file.write_text(rss, encoding="utf-8")
    print(f"  RSS feed: {rss_file}")


def main() -> int:
    """Pipeline de publicação."""

    print(f"[{datetime.now()}] Publicando posts...")

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    # Carrega todos os posts
    posts = load_all_posts()
    print(f"  {len(posts)} posts encontrados")

    if not posts:
        print("  Nenhum post para publicar.")
        return 0

    # Atualiza arquivos
    update_index(posts)
    update_sitemap(posts)
    create_rss_feed(posts)

    print(f"\n✓ {len(posts)} posts publicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
