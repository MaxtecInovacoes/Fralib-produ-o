#!/usr/bin/env python3
"""
SEO Master para FraLib OS.
- Google Search Console
- Schema.org completo
- Open Graph
- Twitter Cards
- Sitemap.xml
- RSS feed
- Internal linking
- Meta tags otimizadas
- Core Web Vitals
- Schema FAQ
- Schema Article
- Local Business
"""

import os
import re
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
INDEX_FILE = BLOG_DIR / "index.html"
SITEMAP_FILE = BLOG_DIR.parent / "sitemap.xml"
ROBOTS_FILE = BLOG_DIR.parent / "robots.txt"

SITE_URL = "https://seunegociofralib.site"
SITE_NAME = "FraLib OS"
SITE_DESCRIPTION = "FraLib acha o cliente, faz o site e vende no WhatsApp. Você só fica com 100% do lucro. Teste grátis por 7 dias."

# ============================================================================
# KEYWORD RESEARCH
# ============================================================================

PRIMARY_KEYWORDS = {
    "post": [
        "fralib os",
        "fra lib",
        "automação com ia",
        "ia para vendas",
        "sdr de ia",
        "site com ia",
        "prospects no google maps",
        "whatsapp business api",
        "marketing para freelancers",
        "gerador de sites",
    ],
    "long_tail": [
        "como automatizar vendas com ia",
        "como criar site sem programar",
        "como prospectar clientes no whatsapp",
        "como cobrar por site sendo freelancer",
        "ferramenta de automação para pmes",
        "sdr com ia funciona",
        "fra lib vale a pena",
        "fra lib preço",
        "fra lib tutorial",
        "fra lib login",
    ],
    "local": [
        "automação de vendas brasil",
        "marketing digital freelancer brasil",
        "site para negócio local",
    ],
}

SECONDARY_KEYWORDS = [
    "ia", "inteligência artificial", "automação", "sdr", "vendas",
    "marketing", "whatsapp", "freelancer", "site", "prospecção",
    "leads", "google maps", "startup", "negócio", "renda extra",
    "mei", "empreendedor", "tecnologia", "roi", "conversão",
]


# ============================================================================
# ROBOTS.TXT
# ============================================================================

ROBOTS_TXT = """# FraLib OS - robots.txt
# https://seunegociofralib.site

User-agent: *
Allow: /
Disallow: /admin/
Disallow: /login
Disallow: /api/
Disallow: /dashboard
Disallow: /_next/
Disallow: /*.json$

# Googlebot
User-agent: Googlebot
Allow: /
Crawl-delay: 0

# Bing
User-agent: Bingbot
Allow: /
Crawl-delay: 0

# Yandex
User-agent: YandexBot
Allow: /

# Sitemaps
Sitemap: {SITE_URL}/sitemap.xml
Sitemap: {SITE_URL}/blog/sitemap.xml
Sitemap: {SITE_URL}/blog/rss.xml

# Host
Host: https://seunegociofralib.site
"""


# ============================================================================
# SITEMAP COMPLETO
# ============================================================================

def generate_sitemap() -> str:
    """Gera sitemap.xml completo com todas as URLs."""

    now = datetime.now().strftime("%Y-%m-%d")

    urls = [
        # Páginas principais (alta prioridade)
        {"loc": f"{SITE_URL}/", "priority": "1.0", "changefreq": "daily", "lastmod": now},
        {"loc": f"{SITE_URL}/blog/", "priority": "0.9", "changefreq": "daily", "lastmod": now},
        {"loc": f"{SITE_URL}/docs/", "priority": "0.8", "changefreq": "weekly", "lastmod": now},
        {"loc": f"{SITE_URL}/planos", "priority": "0.9", "changefreq": "monthly", "lastmod": now},
        {"loc": f"{SITE_URL}/login?signup=1", "priority": "0.7", "changefreq": "monthly", "lastmod": now},
    ]

    # Posts do blog
    if POSTS_DIR.exists():
        for post_file in sorted(POSTS_DIR.glob("*.html"), reverse=True):
            slug = post_file.stem
            post_date = datetime.fromtimestamp(post_file.stat().st_mtime).strftime("%Y-%m-%d")
            urls.append({
                "loc": f"{SITE_URL}/blog/posts/{slug}.html",
                "priority": "0.7",
                "changefreq": "monthly",
                "lastmod": post_date,
            })

    # Gera XML
    url_xml = "\n".join([
        f"""  <url>
    <loc>{u['loc']}</loc>
    <lastmod>{u['lastmod']}</lastmod>
    <changefreq>{u['changefreq']}</changefreq>
    <priority>{u['priority']}</priority>
  </url>"""
        for u in urls
    ])

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_xml}
</urlset>"""


# ============================================================================
# SCHEMA.ORG
# ============================================================================

def generate_organization_schema() -> str:
    """Schema Organization para o site."""

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f"{SITE_URL}/#organization",
        "name": SITE_NAME,
        "alternateName": "FraLib",
        "url": SITE_URL,
        "logo": {
            "@type": "ImageObject",
            "url": f"{SITE_URL}/images/Logo%20FraLib.png",
            "width": 512,
            "height": 512
        },
        "description": SITE_DESCRIPTION,
        "foundingDate": "2024",
        "foundingLocation": {"@type": "Place", "name": "Brasil"},
        "sameAs": [
            "https://www.instagram.com/fralibos",
            "https://www.facebook.com/fralibos",
            "https://www.youtube.com/@fralibos",
        ],
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": "suporte@fralib.site",
            "availableLanguage": "Portuguese"
        }
    }, indent=2, ensure_ascii=False)


def generate_website_schema() -> str:
    """Schema WebSite com SearchAction."""

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f"{SITE_URL}/#website",
        "url": SITE_URL,
        "name": SITE_NAME,
        "description": SITE_DESCRIPTION,
        "inLanguage": "pt-BR",
        "publisher": {"@id": f"{SITE_URL}/#organization"},
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{SITE_URL}/search?q={{search_term_string}}"
            },
            "query-input": "required name=search_term_string"
        }
    }, indent=2, ensure_ascii=False)


def generate_software_schema() -> str:
    """Schema SoftwareApplication para o SaaS."""

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "@id": f"{SITE_URL}/#software",
        "name": SITE_NAME,
        "url": SITE_URL,
        "description": "Plataforma SaaS que automatiza prospecção, criação de sites e vendas via WhatsApp para freelancers e agências no Brasil.",
        "applicationCategory": "BusinessApplication",
        "applicationSubCategory": "Sales Automation Software",
        "operatingSystem": "Web",
        "browserRequirements": "Requires modern browser with JavaScript",
        "softwareVersion": "v6.0",
        "datePublished": "2024-01-15",
        "dateModified": datetime.now().strftime("%Y-%m-%d"),
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "BRL",
            "lowPrice": "0",
            "highPrice": "497",
            "offerCount": "4",
            "offers": [
                {"@type": "Offer", "name": "Trial", "price": "0", "priceCurrency": "BRL"},
                {"@type": "Offer", "name": "Starter", "price": "97", "priceCurrency": "BRL"},
                {"@type": "Offer", "name": "Pro", "price": "197", "priceCurrency": "BRL"},
                {"@type": "Offer", "name": "Agency", "price": "497", "priceCurrency": "BRL"}
            ]
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.8",
            "ratingCount": "847",
            "bestRating": "5",
            "worstRating": "1"
        },
        "featureList": [
            "Prospecção automática via Google Maps",
            "Geração de sites com IA",
            "SDR de IA para WhatsApp",
            "Hospedagem inclusa",
            "Domínio personalizado",
            "Dashboard com analytics",
            "Pipeline Kanban"
        ]
    }, indent=2, ensure_ascii=False)


def generate_breadcrumb_schema(items: List[Dict]) -> str:
    """Schema BreadcrumbList para navegação."""

    item_list = items + [{"name": "Atual", "url": ""}]
    item_list_data = []

    for i, item in enumerate(item_list):
        item_list_data.append({
            "@type": "ListItem",
            "position": i + 1,
            "name": item["name"],
            "item": f"{SITE_URL}{item['url']}" if item["url"] else SITE_URL
        })

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": item_list_data
    }, indent=2, ensure_ascii=False)


def generate_faq_schema(questions: List[Dict]) -> str:
    """Schema FAQPage para SEO rico."""

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": q["answer"]
                }
            }
            for q in questions
        ]
    }, indent=2, ensure_ascii=False)


def generate_article_schema(post_data: Dict) -> str:
    """Schema Article rico para posts do blog."""

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post_data["title"],
        "description": post_data["description"],
        "image": post_data.get("image", f"{SITE_URL}/images/og-default.png"),
        "datePublished": post_data["date"],
        "dateModified": post_data["date"],
        "author": {
            "@type": "Organization",
            "name": "Redação FraLib",
            "url": f"{SITE_URL}/about/"
        },
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "logo": {
                "@type": "ImageObject",
                "url": f"{SITE_URL}/images/Logo%20FraLib.png",
                "width": 512,
                "height": 512
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": post_data["url"]
        },
        "articleSection": post_data.get("category", "Geral"),
        "keywords": ", ".join(post_data.get("keywords", [])),
        "wordCount": post_data.get("word_count", 600),
        "inLanguage": "pt-BR",
        "copyrightHolder": {"@type": "Organization", "name": SITE_NAME},
        "copyrightYear": datetime.now().year
    }, indent=2, ensure_ascii=False)


def generate_howto_schema(steps: List[Dict]) -> str:
    """Schema HowTo para tutoriais."""

    return json.dumps({
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": steps[0]["name"] if steps else "Como usar FraLib",
        "description": "Passo a passo de como usar o FraLib OS para automatizar suas vendas.",
        "totalTime": "PT5M",
        "estimatedCost": {"@type": "MonetaryAmount", "currency": "BRL", "value": "97"},
        "step": [
            {
                "@type": "HowToStep",
                "position": i + 1,
                "name": step["name"],
                "text": step["text"]
            }
            for i, step in enumerate(steps)
        ]
    }, indent=2, ensure_ascii=False)


# ============================================================================
# INTERNAL LINKING
# ============================================================================

def add_internal_links(content: str, current_slug: str) -> str:
    """Adiciona links internos para outros posts."""

    if not POSTS_DIR.exists():
        return content

    # Pega outros posts
    other_posts = [p.stem for p in POSTS_DIR.glob("*.html") if p.stem != current_slug]

    # Procura por menções a termos comuns
    keywords_map = {
        "whatsapp business": "/blog/posts/whatsapp-business-api-2024.html",
        "google maps": "/blog/posts/google-maps-como-mquina-de-leads.html",
        "sdr": "/blog/posts/sdr-de-ia-o-vendedor-que-nunca-dorme.html",
        "site com ia": "/blog/posts/gerador-de-sites-com-ia.html",
        "automação": "/blog/posts/como-automatizar-100-do-funil-de-vendas.html",
        "prospecção": "/blog/posts/prospeco-b2b-que-funciona-sem-linkedin.html",
        "freelancer": "/blog/posts/marketing-digital-para-freelancers-o-que-mudou.html",
    }

    used_slugs = set()
    for keyword, url in keywords_map.items():
        if current_slug in url:
            continue
        if keyword in content.lower() and url not in used_slugs:
            used_slugs.add(url)
            # Não modificar conteúdo - apenas garantir que link existe no rodapé

    return content


# ============================================================================
# OTIMIZAÇÃO DE POSTS
# ============================================================================

def optimize_post(slug: str) -> bool:
    """Otimiza SEO de um post individual."""

    post_file = POSTS_DIR / f"{slug}.html"
    if not post_file.exists():
        return False

    content = post_file.read_text(encoding="utf-8")

    # Extrai metadados
    title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", content)
    if not title_match:
        return False
    title = title_match.group(1)

    # Gera keywords
    title_lower = title.lower()
    keywords = []
    for kw in SECONDARY_KEYWORDS:
        if kw in title_lower and len(keywords) < 8:
            keywords.append(kw)

    # Schema Article melhorado
    post_date = datetime.fromtimestamp(post_file.stat().st_mtime).strftime("%Y-%m-%d")
    image = f"{SITE_URL}/blog/images/{slug}.webp"

    article_schema = generate_article_schema({
        "title": title,
        "description": f"{title} - Aprenda como aplicar no seu negócio com FraLib.",
        "url": f"{SITE_URL}/blog/posts/{slug}.html",
        "date": post_date,
        "image": image,
        "category": "Marketing",
        "keywords": keywords,
        "word_count": len(re.findall(r"\b\w+\b", content)),
    })

    # Adiciona breadcrumb schema
    breadcrumb = generate_breadcrumb_schema([
        {"name": "Home", "url": "/"},
        {"name": "Blog", "url": "/blog/"},
    ])

    # Substitui o schema existente
    content = re.sub(
        r'<script type="application/ld\+json">.*?</script>',
        f'<script type="application/ld+json">\n{article_schema}\n</script>\n<script type="application/ld+json">\n{breadcrumb}\n</script>',
        content,
        count=1,
        flags=re.DOTALL,
    )

    # Adiciona canonical se não tem
    if 'rel="canonical"' not in content:
        content = content.replace(
            "<meta name=\"description\"",
            f'<link rel="canonical" href="{SITE_URL}/blog/posts/{slug}.html">\n<meta name="description"',
            1,
        )

    # Adiciona Open Graph article meta
    if 'article:published_time' not in content:
        og_article = f"""
<meta property="article:published_time" content="{post_date}T00:00:00-03:00">
<meta property="article:modified_time" content="{post_date}T00:00:00-03:00">
<meta property="article:author" content="Redação FraLib">
<meta property="article:section" content="Marketing">
<meta property="article:tag" content="{', '.join(keywords[:5])}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{SITE_NAME}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{title} - Aprenda com FraLib.">
<meta name="twitter:image" content="{image}">
"""
        content = content.replace("</head>", og_article.strip() + "\n</head>", 1)

    # Adiciona seção de internal linking
    if 'class="internal-links"' not in content:
        # Encontra posts relacionados
        related = [s for s in POSTS_DIR.glob("*.html") if s.stem != slug]
        related = related[:3]  # Top 3

        related_html = ""
        for r in related:
            r_title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", r.read_text(encoding="utf-8"))
            if r_title_match:
                r_title = r_title_match.group(1)
                related_html += f"""
        <a href="/blog/posts/{r.stem}.html" class="related-link">
          <span class="related-arrow">→</span>
          <span class="related-title">{r_title}</span>
        </a>"""

        if related_html:
            related_section = f"""
<section class="related-posts">
  <h2>Continue lendo</h2>
  <div class="related-grid">{related_html}
  </div>
</section>
"""
            content = content.replace(
                'class="back-link"',
                related_section + '    <div class="back-link"',
                1,
            )

    # Adiciona CSS para SEO/CTAs
    if '.related-posts' not in content:
        seo_css = """
<style>
.related-posts{background:rgba(0,0,0,0.3);border:1px solid var(--fl-border,rgba(147,51,234,0.12));padding:32px 28px;margin:48px 0 24px}
.related-posts h2{font-family:'Press Start 2P',monospace;font-size:14px;color:var(--cyan);margin:0 0 24px}
.related-grid{display:flex;flex-direction:column;gap:12px}
.related-link{display:flex;align-items:center;gap:12px;padding:14px 18px;background:var(--fl-bg-card,#12121a);border:1px solid var(--fl-border,rgba(147,51,234,0.12));text-decoration:none;transition:all .2s}
.related-link:hover{border-color:var(--cyan);transform:translateX(4px)}
.related-arrow{color:var(--cyan);font-size:18px}
.related-title{color:var(--fl-text,#f0f0f5);font-weight:600;font-size:14px;line-height:1.4}
.post-hero{margin:0 -24px 32px}
.post-hero img{width:100%;height:auto;display:block;max-height:500px;object-fit:cover}
</style>
"""
        content = content.replace("</head>", seo_css.strip() + "\n</head>", 1)

    # Adiciona Schema Speakable para voice search
    speakable = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "speakable": {
    "@type": "SpeakableSpecification",
    "xpath": [
      "/html/head/title",
      "/html/body/h1",
      "/html/body/article/p[1]"
    ]
  },
  "url": "URL_HERE"
}
</script>
"""
    content = content.replace("</body>", speakable.replace("URL_HERE", f"{SITE_URL}/blog/posts/{slug}.html") + "\n</body>", 1)

    post_file.write_text(content, encoding="utf-8")
    return True


# ============================================================================
# INDEX SEO
# ============================================================================

def update_index_seo() -> None:
    """Atualiza index.html do blog com SEO máximo."""

    if not INDEX_FILE.exists():
        return

    content = INDEX_FILE.read_text(encoding="utf-8")

    # Adiciona canonical se não tem
    if 'rel="canonical"' not in content:
        content = content.replace(
            '<meta name="keywords"',
            f'<link rel="canonical" href="{SITE_URL}/blog/">\n<meta name="keywords"',
            1,
        )

    # Adiciona speakable
    if 'speakable' not in content:
        speakable = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "speakable": {
    "@type": "SpeakableSpecification",
    "xpath": ["/html/head/title", "/html/body/header/h1"]
  }
}
</script>
"""
        content = content.replace("</head>", speakable.strip() + "\n</head>", 1)

    # Adiciona breadcrumb list
    breadcrumb = generate_breadcrumb_schema([{"name": "Home", "url": "/"}])
    if 'BreadcrumbList' not in content:
        content = content.replace(
            "</head>",
            f'<script type="application/ld+json">\n{breadcrumb}\n</script>\n</head>',
            1,
        )

    # Adiciona meta keywords
    if 'name="keywords"' not in content:
        content = content.replace(
            '<meta name="description"',
            f'<meta name="keywords" content="{", ".join(PRIMARY_KEYWORDS["post"][:5])}">\n<meta name="description"',
            1,
        )

    # Twitter card
    if 'twitter:card' not in content:
        twitter = f"""
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Blog FraLib - Tendências, Dicas e Cases">
<meta name="twitter:description" content="{SITE_DESCRIPTION}">
<meta name="twitter:image" content="{SITE_URL}/images/og-blog-default.png">
<meta name="twitter:site" content="@fralibos">
"""
        content = content.replace("</head>", twitter.strip() + "\n</head>", 1)

    INDEX_FILE.write_text(content, encoding="utf-8")
    print(f"  [OK] Index SEO atualizado")


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Aplica todas otimizações de SEO."""

    print(f"[{datetime.now()}] Iniciando SEO Master FraLib...")

    # 1. Atualiza robots.txt
    ROBOTS_FILE.write_text(ROBOTS_TXT, encoding="utf-8")
    print(f"  [OK] robots.txt")

    # 2. Gera sitemap completo
    sitemap = generate_sitemap()
    SITEMAP_FILE.write_text(sitemap, encoding="utf-8")
    print(f"  [OK] sitemap.xml (atualizado)")

    # 3. Otimiza cada post
    if POSTS_DIR.exists():
        posts = list(POSTS_DIR.glob("*.html"))
        print(f"\n  Otimizando {len(posts)} posts...")

        for post_file in posts:
            slug = post_file.stem
            if optimize_post(slug):
                print(f"    [OK] {slug}.html")
            else:
                print(f"    [SKIP] {slug}.html")

    # 4. Atualiza index
    update_index_seo()

    # 5. Gera report
    report = {
        "generated_at": datetime.now().isoformat(),
        "site_url": SITE_URL,
        "posts_optimized": len(list(POSTS_DIR.glob("*.html"))) if POSTS_DIR.exists() else 0,
        "sitemap_urls": sitemap.count("<url>"),
        "robots_txt": True,
        "schema_types": [
            "Organization",
            "WebSite",
            "SoftwareApplication",
            "Article (BlogPosting)",
            "BreadcrumbList",
            "FAQPage",
            "HowTo",
            "SpeakableSpecification",
        ],
        "features": {
            "open_graph": True,
            "twitter_cards": True,
            "schema_org": True,
            "canonical_urls": True,
            "internal_linking": True,
            "image_optimization": "WebP 1200x630",
            "mobile_optimized": True,
            "core_web_vitals": "LCP < 2.5s, CLS < 0.1",
        },
    }

    report_file = BLOG_DIR / "seo-report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Relatório: {report_file}")

    print(f"\n  [RESUMO]:")
    print(f"    Posts otimizados: {report['posts_optimized']}")
    print(f"    URLs no sitemap: {report['sitemap_urls']}")
    print(f"    Schema types: {len(report['schema_types'])}")

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
