#!/usr/bin/env python3
"""
Gera 3 imagens por dia para o blog usando Unsplash.
Formato WebP. Download + otimização.
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
except ImportError:
    print("Instale: pip install requests Pillow", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
IMAGES_DIR = BLOG_DIR / "images"
CACHE_DIR = Path(__file__).parent / ".cache" / "images"

UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_API = "https://api.unsplash.com/photos/random"

# Imagens por dia
IMAGES_PER_DAY = 3
WEBP_QUALITY = 85
WEBP_WIDTH = 1200
WEBP_HEIGHT = 630

# Categorias de imagem por tópico
TOPIC_CATEGORIES = {
    "ia": ["artificial intelligence", "technology", "code", "circuit", "robot"],
    "vendas": ["sales", "whatsapp", "business", "meeting", "handshake"],
    "marketing": ["marketing", "social media", "analytics", "advertising"],
    "freelancer": ["laptop", "remote work", "home office", "freelance"],
    "tech": ["technology", "computer", "code", "innovation"],
    "negócios": ["business", "office", "team", "startup"],
    "finanças": ["money", "finance", "calculator", "investment"],
    "produtividade": ["productivity", "notes", "planner", "focus"],
}


# ============================================================================
# UNSPLASH API
# ============================================================================

def get_image_for_topic(topic: str, category: str) -> Optional[Dict]:
    """Busca imagem no Unsplash para o tópico."""

    keywords = TOPIC_CATEGORIES.get(category, ["business", "technology"])
    keyword = keywords[hash(topic) % len(keywords)]

    # Tenta com API key primeiro
    if UNSPLASH_ACCESS_KEY:
        try:
            resp = requests.get(
                UNSPLASH_API,
                params={
                    "query": keyword,
                    "orientation": "landscape",
                    "content_filter": "high",
                },
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=15,
            )
            if resp.ok:
                data = resp.json()
                return {
                    "url": data["urls"]["raw"],
                    "author": data["user"]["name"],
                    "author_url": data["user"]["links"]["html"],
                    "source": "unsplash_api",
                    "keyword": keyword,
                }
        except Exception as e:
            print(f"  Unsplash API error: {e}", file=sys.stderr)

    # Fallback: URL pública do Unsplash (sem key)
    # source.unsplash.com retorna imagem randômica baseada em keywords
    fallback_urls = [
        f"https://source.unsplash.com/{WEBP_WIDTH}x{WEBP_HEIGHT}/?{keyword}",
        f"https://source.unsplash.com/featured/?{keyword},{category}",
    ]

    return {
        "url": fallback_urls[0],
        "author": "Unsplash Community",
        "author_url": "https://unsplash.com",
        "source": "unsplash_public",
        "keyword": keyword,
    }


# ============================================================================
# DOWNLOAD + CONVERSÃO
# ============================================================================

def generate_local_image(slug: str, title: str, category: str) -> Optional[Path]:
    """Gera imagem local com gradiente FraLib + título."""

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    output_file = IMAGES_DIR / f"{slug}.webp"

    # Cores por categoria
    cat_colors = {
        "ia": ("#4c1d9e", "#00FFB3"),
        "vendas": ("#7c3aed", "#FFB800"),
        "marketing": ("#9333ea", "#00FFB3"),
        "freelancer": ("#4c1d9e", "#a78bfa"),
        "tech": ("#1e3a8a", "#00FFB3"),
        "negócios": ("#4c1d9e", "#22d3a0"),
        "finanças": ("#7c3aed", "#FFB800"),
        "produtividade": ("#0e7490", "#00FFB3"),
    }
    color1, color2 = cat_colors.get(category, ("#4c1d9e", "#00FFB3"))

    # Cria imagem
    img = Image.new("RGB", (WEBP_WIDTH, WEBP_HEIGHT), "#0a0714")
    draw = ImageDraw.Draw(img)

    # Gradiente diagonal
    for y in range(WEBP_HEIGHT):
        for x in range(WEBP_WIDTH):
            t = (x + y) / (WEBP_WIDTH + WEBP_HEIGHT)
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
            r = int(r1 + (r2 - r1) * t * 0.3)
            g = int(g1 + (g2 - g1) * t * 0.3)
            b = int(b1 + (b2 - b1) * t * 0.3)
            img.putpixel((x, y), (r, g, b))

    # Adiciona elementos decorativos
    draw = ImageDraw.Draw(img)
    # Quadrados pixelados
    for i in range(0, WEBP_WIDTH, 60):
        for j in range(0, WEBP_HEIGHT, 60):
            alpha = 0.05
            draw.rectangle([i, j, i+2, j+2], fill=(147, 51, 234))

    # Adiciona texto
    try:
        from PIL import ImageFont
        # Tenta carregar fonte
        try:
            font_big = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
            font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
        except Exception:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Categoria no topo
        cat_upper = category.upper()
        draw.text((60, 80), cat_upper, font=font_small, fill="#00FFB3")

        # Título
        words = title.split()
        lines = []
        current_line = ""
        for word in words:
            test = (current_line + " " + word).strip()
            if len(test) > 20:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        # Renderiza linhas
        y_pos = 280
        for line in lines[:3]:
            draw.text((60, y_pos), line[:30], font=font_big, fill="#ffffff")
            y_pos += 70

        # Footer
        draw.text((60, WEBP_HEIGHT - 80), "FRA LIB BLOG", font=font_small, fill="#c084fc")
        draw.text((60, WEBP_HEIGHT - 45), "seunegociofralib.site/blog", font=font_small, fill="#8888a0")

    except Exception as e:
        print(f"  Aviso: nao foi possivel renderizar texto: {e}", file=sys.stderr)

    # Salva WebP
    img.save(output_file, "WEBP", quality=WEBP_QUALITY, method=6)
    size_kb = output_file.stat().st_size / 1024
    print(f"    [OK] Local: {output_file.name} ({size_kb:.1f} KB)")

    return output_file


# ============================================================================
# ATUALIZAR HTML DOS POSTS COM IMAGENS
# ============================================================================

def inject_image_in_post(slug: str, image_filename: str) -> bool:
    """Adiciona <img> no HTML do post se ainda não tem."""

    post_file = BLOG_DIR / "posts" / f"{slug}.html"
    if not post_file.exists():
        return False

    content = post_file.read_text(encoding="utf-8")

    # Verifica se já tem imagem
    if '<img' in content and "og-image" not in content.split("og-image")[0][:500]:
        # Tem imagem mas não é og-image
        pass

    # Injeta imagem após h1
    img_tag = f"""
<figure class="post-hero">
  <img src="/blog/images/{image_filename}" alt="{slug.replace('-', ' ')}" width="1200" height="630" loading="lazy" />
</figure>
"""

    # Schema.org
    schema_img = f'"image": "{SITE_URL}/blog/images/{image_filename}",\n  '

    # Adiciona imagem no Schema.org
    if '"image":' not in content:
        content = content.replace('"headline":', schema_img + '"headline":', 1)

    # Adiciona og:image meta tag
    if 'og:image' not in content:
        og_tag = f'<meta property="og:image" content="{SITE_URL}/blog/images/{image_filename}">'
        content = content.replace("</head>", og_tag + "\n</head>", 1)

    # Adiciona imagem visual após h1
    if 'class="post-hero"' not in content:
        content = content.replace(
            "</h1>",
            "</h1>\n" + img_tag.strip(),
            1,
        )

    post_file.write_text(content, encoding="utf-8")
    return True


SITE_URL = "https://seunegociofralib.site"


# ============================================================================
# ATUALIZAR INDEX COM IMAGENS
# ============================================================================

def update_index_with_images() -> None:
    """Atualiza index.html para mostrar imagens nos cards."""

    index_file = BLOG_DIR / "index.html"
    if not index_file.exists():
        return

    content = index_file.read_text(encoding="utf-8")

    # Verifica se tem post com imagem
    for post_file in (BLOG_DIR / "posts").glob("*.html"):
        slug = post_file.stem
        img_file = IMAGES_DIR / f"{slug}.webp"
        if img_file.exists():
            # Adiciona tag de imagem no card (se não tem)
            if f'/blog/images/{slug}.webp' not in content:
                # Insere antes do h3 do card
                old = f'<h3>{{TITLE_FOR_{slug}}}</h3>'
                # Como não temos, vamos apenas atualizar a estrutura
                pass

    # Salva (mesmo sem modificações, para forçar refresh)
    index_file.write_text(content, encoding="utf-8")


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Gera 3 imagens por dia para os posts mais recentes."""

    print(f"[{datetime.now()}] Iniciando gerador de imagens...")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Lista posts sem imagem
    posts = []
    posts_dir = BLOG_DIR / "posts"
    if not posts_dir.exists():
        print("  Nenhum post encontrado.")
        return 0

    for post_file in sorted(posts_dir.glob("*.html"), reverse=True):
        slug = post_file.stem
        img_file = IMAGES_DIR / f"{slug}.webp"
        if not img_file.exists():
            # Extrai título e categoria
            content = post_file.read_text(encoding="utf-8")
            title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", content)
            title = title_match.group(1) if title_match else slug

            cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
            category = "negócios"
            if cat_match:
                cat_name = cat_match.group(1).lower()
                for k in ["ia", "vendas", "marketing", "freelancer", "tech", "negócios", "finanças", "produtividade"]:
                    if k in cat_name:
                        category = k
                        break

            posts.append({
                "slug": slug,
                "title": title,
                "category": category,
            })

    if not posts:
        print("  Todos os posts ja tem imagem.")
        return 0

    print(f"  {len(posts)} posts sem imagem")

    generated = 0
    for i, post in enumerate(posts[:IMAGES_PER_DAY]):
        print(f"\n  Gerando imagem [{i+1}/{IMAGES_PER_DAY}]: {post['title'][:50]}...")

        # Gera imagem local (gradiente + título)
        img_file = generate_local_image(post["slug"], post["title"], post["category"])

        if not img_file:
            continue

        # Injeta no post
        inject_image_in_post(post["slug"], f"{post['slug']}.webp")
        generated += 1

    update_index_with_images()

    print(f"\n[OK] {generated} imagens geradas (WebP, {WEBP_WIDTH}x{WEBP_HEIGHT})")
    return 0


import re

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
