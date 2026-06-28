#!/usr/bin/env python3
"""
Auto-post em redes sociais.
LinkedIn + Twitter com os posts do blog FraLib.
"""

import os
import json
import sys
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
SITE_URL = "https://seunegociofralib.site"
SITE_NAME = "FraLib OS"


def post_to_linkedin(content: str, image_url: str = "") -> bool:
    """Posta no LinkedIn (via API oficial)."""

    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        return False

    # LinkedIn API
    try:
        # Primeiro, faz upload da imagem (se houver)
        media_urn = None
        if image_url:
            register_resp = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": "urn:li:person:YOUR_PERSON_ID",
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }
                        ]
                    }
                },
                timeout=30,
            )
            if register_resp.ok:
                media_urn = register_resp.json().get("value", {}).get("asset")

        # Cria o post
        post_data = {
            "author": "urn:li:person:YOUR_PERSON_ID",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE" if media_urn else "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        if media_urn:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {"status": "READY", "description": {"text": ""}, "media": media_urn}
            ]

        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=post_data,
            timeout=30,
        )
        return resp.ok
    except Exception as e:
        print(f"  LinkedIn error: {e}", file=sys.stderr)
        return False


def post_to_twitter(content: str, image_url: str = "") -> bool:
    """Posta no Twitter/X via API v2."""

    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        return False

    try:
        # Upload de imagem (se houver)
        media_id = None
        if image_url:
            upload_resp = requests.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                auth=(api_key, api_secret),
                data={"media_data": requests.get(image_url).content},
                timeout=30,
            )
            if upload_resp.ok:
                media_id = upload_resp.json()["media_id_string"]

        # Posta tweet
        post_data = {"text": content}
        if media_id:
            post_data["media"] = {"media_ids": [media_id]}

        resp = requests.post(
            "https://api.twitter.com/2/tweets",
            auth=(access_token, access_secret),
            json=post_data,
            timeout=30,
        )
        return resp.ok
    except Exception as e:
        print(f"  Twitter error: {e}", file=sys.stderr)
        return False


def post_to_facebook(content: str, image_url: str = "") -> bool:
    """Posta no Facebook via Graph API."""

    page_token = os.environ.get("FACEBOOK_PAGE_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")

    if not page_token or not page_id:
        return False

    try:
        post_data = {"message": content, "access_token": page_token}
        if image_url:
            post_data["link"] = image_url

        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{page_id}/feed",
            data=post_data,
            timeout=30,
        )
        return resp.ok
    except Exception as e:
        print(f"  Facebook error: {e}", file=sys.stderr)
        return False


def get_post_data(slug: str) -> Optional[Dict]:
    """Carrega dados de um post do blog."""

    post_file = POSTS_DIR / f"{slug}.html"
    if not post_file.exists():
        return None

    content = post_file.read_text(encoding="utf-8")

    title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", content)
    title = title_match.group(1) if title_match else slug

    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    excerpt = desc_match.group(1) if desc_match else title

    cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
    category = cat_match.group(1) if cat_match else "Blog"

    has_image = (BLOG_DIR / "images" / f"{slug}.webp").exists()
    image_url = f"{SITE_URL}/blog/images/{slug}.webp" if has_image else ""

    return {
        "slug": slug,
        "title": title,
        "excerpt": excerpt,
        "category": category,
        "image_url": image_url,
        "url": f"{SITE_URL}/blog/posts/{slug}.html",
    }


def build_linkedin_post(post: Dict) -> str:
    """Formata post para LinkedIn."""

    # LinkedIn aceita ate 3000 caracteres
    return f"""🚀 {post['title']}

{post['excerpt']}

A gente sabe que a maioria dos freelancers faz prospecção, criação de site e vendas manualmente — e isso come 80% do tempo.

E se existisse uma ferramenta que fizesse tudo isso sozinha, todo dia, sem você fazer nada?

A FraLib acha o cliente, faz o site e vende no WhatsApp. Você só fica com o lucro.

📖 Ler completo: {post['url']}

#marketing #vendas #freelancer #ia #automacao #{post['category'].lower().replace(' ', '').replace('&', '').replace('í', 'i').replace('ç', 'c').replace('õ', 'o').replace('ã', 'a')}"""


def build_twitter_post(post: Dict) -> str:
    """Formata post para Twitter (max 280 chars)."""

    # Twitter max 280
    short_title = post['title'][:80]
    return f"{short_title}\n\n{post['url']}"


def build_facebook_post(post: Dict) -> str:
    """Formata post para Facebook."""

    return f"""📌 {post['title']}

{post['excerpt']}

A FraLib acha o cliente, faz o site e vende no WhatsApp. Você só fica com o lucro.

👉 Ler: {post['url']}"""


def main() -> int:
    """Executa auto-post em redes sociais."""

    print(f"[{datetime.now()}] Iniciando auto-post em redes sociais...")

    if not POSTS_DIR.exists():
        print("  Nenhum post encontrado")
        return 0

    # Pega posts recentes
    recent_posts = sorted(POSTS_DIR.glob("*.html"), reverse=True)[:3]

    results = {"linkedin": [], "twitter": [], "facebook": []}

    for post_file in recent_posts:
        slug = post_file.stem
        post = get_post_data(slug)
        if not post:
            continue

        print(f"  Processando: {post['title'][:50]}")

        # LinkedIn
        li_content = build_linkedin_post(post)
        if post_to_linkedin(li_content, post["image_url"]):
            results["linkedin"].append(slug)
            print(f"    [OK] LinkedIn")

        # Twitter
        tw_content = build_twitter_post(post)
        if post_to_twitter(tw_content, post["image_url"]):
            results["twitter"].append(slug)
            print(f"    [OK] Twitter")

        # Facebook
        fb_content = build_facebook_post(post)
        if post_to_facebook(fb_content, post["image_url"]):
            results["facebook"].append(slug)
            print(f"    [OK] Facebook")

    # Log
    log_file = BLOG_DIR / "social-log.json"
    log_entry = {
        "executed_at": datetime.now().isoformat(),
        "results": results,
    }

    logs = []
    if log_file.exists():
        logs = json.loads(log_file.read_text(encoding="utf-8"))
    logs.append(log_entry)
    log_file.write_text(json.dumps(logs[-30:], indent=2, ensure_ascii=False), encoding="utf-8")

    # Resumo
    print(f"\n  RESUMO:")
    print(f"    LinkedIn: {len(results['linkedin'])} posts")
    print(f"    Twitter:  {len(results['twitter'])} posts")
    print(f"    Facebook: {len(results['facebook'])} posts")

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
