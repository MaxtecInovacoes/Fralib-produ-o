#!/usr/bin/env python3
"""
Auto-post em redes sociais (Multi-Tenant).
LinkedIn + Twitter + Facebook + Instagram com os posts do blog FraLib.

Uso:
  python auto_post_social.py --project fralib
  python auto_post_social.py --project energia_solar
  python auto_post_social.py --all    # roda todos os projetos ativos

Instagram usa Graph API v18+ (Content Publishing API):
- Requer conta Instagram Business/Creator conectada a uma Página do Facebook.
- Requer permissões: instagram_basic, instagram_content_publish, pages_show_list.
- Postagem é assíncrona em 2 chamadas: container -> publish.
"""

import os
import sys
import re
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Constantes
SCRIPTS_DIR = Path(__file__).parent
FRALIB_DIR = SCRIPTS_DIR.parent
PROJECTS_DIR = FRALIB_DIR / "projects"

# Defaults (para compatibilidade --project optional)
BLOG_DIR = FRALIB_DIR / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
SITE_URL = "https://seunegociofralib.site"
SITE_NAME = "FraLib OS"

# Variáveis de contexto do projeto (setadas por load_project_config)
current_posts_dir = None
current_assets_dir = None


def load_project_config(project_slug: str) -> bool:
    """Carrega config.env de um projeto específico."""
    global current_posts_dir, current_assets_dir, SITE_URL, SITE_NAME

    config_file = PROJECTS_DIR / project_slug / "config.env"

    if not config_file.exists():
        print(f"  ✗ Projeto não encontrado: {project_slug}")
        print(f"    Procurei em: {config_file}")
        return False

    # Carrega variáveis do config.env
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                if key and value:
                    os.environ[key] = value

    # Sobrescreve caminhos se definidos no config
    content_dir = os.environ.get('CONTENT_DIR')
    if content_dir:
        current_posts_dir = Path(content_dir) / 'posts'
        current_assets_dir = Path(content_dir) / 'assets'
    else:
        current_posts_dir = PROJECTS_DIR / project_slug / 'content' / 'posts'
        current_assets_dir = PROJECTS_DIR / project_slug / 'content' / 'assets'

    # Sobrescreve SITE_URL se definido no config do projeto
    project_name = os.environ.get('PROJECT_NAME', '')
    if project_name:
        SITE_NAME = project_name

    print(f"  ✓ Config carregado: {project_slug}")
    print(f"    Posts: {current_posts_dir}")
    print(f"    Assets: {current_assets_dir}")
    return True


def get_all_projects() -> List[str]:
    """Lista todos os projetos com config.env."""
    if not PROJECTS_DIR.exists():
        return []

    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir() and (item / "config.env").exists():
            projects.append(item.name)

    return projects


def main() -> int:
    """Executa auto-post em redes sociais."""

    # Parse argumentos
    parser = argparse.ArgumentParser(description="Auto-post em redes sociais")
    parser.add_argument('--project', type=str, help='Slug do projeto (ex: fralib, energia_solar)')
    parser.add_argument('--all', action='store_true', help='Roda todos os projetos ativos')
    args = parser.parse_args()

    # determina projetos
    if args.all:
        projects = get_all_projects()
        print(f"[{datetime.now()}] Auto-post em TODOS os projetos: {', '.join(projects)}")
    elif args.project:
        projects = [args.project]
        print(f"[{datetime.now()}] Auto-post para projeto: {args.project}")
    else:
        # modo legado: usa .env global
        projects = []
        print(f"[{datetime.now()}] Modo legado: usando .env global (sem projeto)")

    # Executa para cada projeto
    for project_slug in projects:
        print(f"\n=== Projeto: {project_slug} ===")

        if not load_project_config(project_slug):
            continue

        # Sobrescreve caminhos se definidos no config
        content_dir = os.environ.get('CONTENT_DIR')
        if content_dir:
            project_posts_dir = Path(content_dir) / 'posts'
            project_assets_dir = Path(content_dir) / 'assets'
        else:
            project_posts_dir = PROJECTS_DIR / project_slug / 'content' / 'posts'
            project_assets_dir = PROJECTS_DIR / project_slug / 'content' / 'assets'

        # Gera posts (lógica existente)
        result = run_auto_post(project_posts_dir, project_assets_dir)
        if result != 0:
            print(f"  ✗ Erro no projeto {project_slug}")

    if not projects:
        # modo legado
        result = run_auto_post(POSTS_DIR, BLOG_DIR / "images")
        return result

    print(f"\n[{datetime.now()}] Todos os projetos processados.")
    return 0


def run_auto_post(posts_dir: Path, assets_dir: Path) -> int:
    """Lógica principal de auto-post (extraída para reuse)."""

    print(f"[{datetime.now()}] Iniciando auto-post em redes sociais...")


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


def post_to_instagram(content: str, image_url: str = "") -> bool:
    """
    Posta no Instagram Business/Creator via Content Publishing API.

    Fluxo (assíncrono em 2 chamadas):
      1. POST /{ig-user-id}/media  -> cria container com caption + image_url
      2. POST /{ig-user-id}/media_publish  -> publica o container

    Pré-requisitos:
      - Conta Instagram Business ou Creator (não pessoal)
      - Vinculada a uma Página do Facebook
      - App no Meta Developers com permissões:
        instagram_basic, instagram_content_publish, pages_show_list
      - Variáveis: INSTAGRAM_BUSINESS_ID + FACEBOOK_PAGE_TOKEN (Page Token
        vinculado à página que tem a conta IG conectada)
    """

    ig_user_id = os.environ.get("INSTAGRAM_BUSINESS_ID")
    access_token = os.environ.get("FACEBOOK_PAGE_TOKEN")

    if not ig_user_id or not access_token:
        print("  Instagram skip: faltam INSTAGRAM_BUSINESS_ID ou FACEBOOK_PAGE_TOKEN", file=sys.stderr)
        return False

    # IG exige image_url pública (HTTPS) ou mídia já hospedada no Meta.
    # Se não houver imagem, faz fallback para post sem mídia (texto corrido)
    # mas Instagram SEMPRE exige mídia em feed, então sem imagem abortamos
    # silenciosamente — Facebook continua recebendo o post.
    if not image_url or not image_url.startswith(("http://", "https://")):
        print("  Instagram skip: exige image_url pública (HTTPS)", file=sys.stderr)
        return False

    api_version = "v18.0"
    base = f"https://graph.facebook.com/{api_version}/{ig_user_id}"

    try:
        # 1) Criar container de mídia
        container_resp = requests.post(
            f"{base}/media",
            params={
                "image_url": image_url,
                "caption": content,
                "access_token": access_token,
            },
            timeout=30,
        )
        if not container_resp.ok:
            print(f"  Instagram container error {container_resp.status_code}: {container_resp.text[:200]}", file=sys.stderr)
            return False

        creation_id = container_resp.json().get("id")
        if not creation_id:
            print(f"  Instagram container sem id: {container_resp.text[:200]}", file=sys.stderr)
            return False

        # 2) Esperar o Meta processar (geralmente < 5s, mas pode demorar)
        #    Polling simples com timeout de 30s
        for attempt in range(6):
            time.sleep(3)
            status_resp = requests.get(
                f"{api_version}/{creation_id}",
                params={
                    "fields": "status_code",
                    "access_token": access_token,
                },
                timeout=15,
            )
            if not status_resp.ok:
                continue
            status = status_resp.json().get("status_code", "UNKNOWN")
            if status == "FINISHED":
                break
            if status in ("ERROR", "EXPIRED"):
                print(f"  Instagram container status: {status}", file=sys.stderr)
                return False
        else:
            print("  Instagram container timeout esperando processamento", file=sys.stderr)
            return False

        # 3) Publicar
        publish_resp = requests.post(
            f"{base}/media_publish",
            params={
                "creation_id": creation_id,
                "access_token": access_token,
            },
            timeout=30,
        )
        if not publish_resp.ok:
            print(f"  Instagram publish error {publish_resp.status_code}: {publish_resp.text[:200]}", file=sys.stderr)
            return False

        return True

    except Exception as e:
        print(f"  Instagram error: {e}", file=sys.stderr)
        return False


def get_post_data(slug: str) -> Optional[Dict]:
    """Carrega dados de um post do blog (usa contexto do projeto se disponível)."""

    # Usa posts_dir do contexto ou default
    posts_dir = current_posts_dir if current_posts_dir else POSTS_DIR
    assets_dir = current_assets_dir if current_assets_dir else (BLOG_DIR / "images")

    post_file = posts_dir / f"{slug}.html"
    if not post_file.exists():
        return None

    content = post_file.read_text(encoding="utf-8")

    title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", content)
    title = title_match.group(1) if title_match else slug

    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    excerpt = desc_match.group(1) if desc_match else title

    cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
    category = cat_match.group(1) if cat_match else "Blog"

    has_image = (assets_dir / f"{slug}.webp").exists()
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


def build_instagram_post(post: Dict) -> str:
    """Formata caption para Instagram (até 2200 chars; primeiras 125 sem truncar)."""

    return f"""📌 {post['title']}

{post['excerpt']}

A FraLib acha o cliente, faz o site e vende no WhatsApp. Você só fica com o lucro.

👉 Link na bio

#{post['category'].lower().replace(' ', '').replace('&', '').replace('í', 'i').replace('ç', 'c').replace('õ', 'o').replace('ã', 'a')} #marketing #vendas #freelancer #ia #automacao #negocios #empreendedorismo"""


def run_auto_post(posts_dir: Path = None, assets_dir: Path = None) -> int:
    """Lógica principal de auto-post (extraída para reuse com --project)."""
    global current_posts_dir, current_assets_dir

    # Se posts_dir/assets_dir foram passados, usa eles; senão usa globals ou defaults
    effective_posts_dir = posts_dir if posts_dir else (current_posts_dir or POSTS_DIR)
    effective_assets_dir = assets_dir if assets_dir else (current_assets_dir or BLOG_DIR / "images")

    print(f"[{datetime.now()}] Iniciando auto-post em redes sociais...")
    print(f"    Posts dir: {effective_posts_dir}")
    print(f"    Assets dir: {effective_assets_dir}")

    if not effective_posts_dir.exists():
        print(f"  Nenhum post encontrado em {effective_posts_dir}")
        return 0

    # Pega posts recentes
    recent_posts = sorted(effective_posts_dir.glob("*.html"), reverse=True)[:3]

    results = {"linkedin": [], "twitter": [], "facebook": [], "instagram": []}

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

        # Instagram (só tenta se o post tem imagem pública)
        if post["image_url"]:
            ig_content = build_instagram_post(post)
            if post_to_instagram(ig_content, post["image_url"]):
                results["instagram"].append(slug)
                print(f"    [OK] Instagram")
        else:
            print(f"    [--] Instagram (sem imagem)")

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
    print(f"    LinkedIn:  {len(results['linkedin'])} posts")
    print(f"    Twitter:   {len(results['twitter'])} posts")
    print(f"    Facebook:  {len(results['facebook'])} posts")
    print(f"    Instagram: {len(results['instagram'])} posts")

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
