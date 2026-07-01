"""
Blog Analytics Endpoints — Superadmin Dashboard
Retorna métricas e estatísticas do blog automático.
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from backend.core.database import engine
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/superadmin", tags=['blog-analytics'])

# Paths do blog
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
BLOG_DIR = FRONTEND_DIR / "blog"
POSTS_DIR = BLOG_DIR / "posts"


def _get_blog_stats() -> dict:
    """Coleta estatísticas do blog."""
    stats = {
        "total_posts": 0,
        "posts_by_category": {},
        "recent_posts": [],
        "last_generated": None,
        "oldest_post": None,
        "avg_size_kb": 0,
        "categories": ["marketing", "ia", "vendas", "freelancer", "tech", "negócios"],
    }

    if not POSTS_DIR.exists():
        return stats

    posts = sorted(POSTS_DIR.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
    stats["total_posts"] = len(posts)

    sizes = []
    for post_file in posts:
        try:
            content = post_file.read_text(encoding="utf-8")

            # Extrair categoria
            cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
            category = "unknown"
            if cat_match:
                cat_text = cat_match.group(1).lower()
                for c in stats["categories"]:
                    if c in cat_text or cat_text in c:
                        category = c
                        break

            # Extrair data
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)

            # Extrair título
            title_match = re.search(r'<title>([^<]+) — Blog FraLib</title>', content)

            sizes.append(post_file.stat().st_size / 1024)

            post_data = {
                "slug": post_file.stem,
                "title": title_match.group(1) if title_match else post_file.stem,
                "category": category,
                "date": date_match.group(1) if date_match else None,
                "size_kb": round(post_file.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(post_file.stat().st_mtime).isoformat(),
            }

            stats["posts_by_category"][category] = stats["posts_by_category"].get(category, 0) + 1

            if len(stats["recent_posts"]) < 10:
                stats["recent_posts"].append(post_data)

        except Exception:
            continue

    if posts:
        oldest = sorted(posts, key=lambda f: f.stat().st_mtime)[0]
        stats["oldest_post"] = datetime.fromtimestamp(oldest.stat().st_mtime).isoformat()
        stats["last_generated"] = datetime.fromtimestamp(posts[0].stat().st_mtime).isoformat()

    if sizes:
        stats["avg_size_kb"] = round(sum(sizes) / len(sizes), 1)

    return stats


def _get_trending_topics() -> dict:
    """Retorna topics trending configurados no sistema."""
    trending = [
        {"topic": "Automação com IA para PMEs", "category": "ia", "used": False},
        {"topic": "WhatsApp Business API 2026", "category": "vendas", "used": False},
        {"topic": "Gerador de sites com IA", "category": "tech", "used": False},
        {"topic": "SDR de IA: o vendedor que nunca dorme", "category": "ia", "used": False},
        {"topic": "Google Maps como máquina de leads", "category": "marketing", "used": False},
        {"topic": "Como cobrar R$1.500 por site em 2026", "category": "freelancer", "used": False},
        {"topic": "Prospecção B2B que funciona sem LinkedIn", "category": "vendas", "used": False},
        {"topic": "Site que vende: 7 erros que freelancers cometem", "category": "marketing", "used": False},
        {"topic": "Como automatizar 100% do funil de vendas", "category": "ia", "used": False},
        {"topic": "FraLib OS: o case que mudou a prospecção no Brasil", "category": "tech", "used": False},
    ]

    # Marcar quais já foram usados
    if POSTS_DIR.exists():
        used_slugs = [f.stem for f in POSTS_DIR.glob("*.html")]
        for topic in trending:
            slug = re.sub(r'[^a-z0-9]', '-', topic["topic"].lower())[:80]
            if slug in used_slugs or any(slug in s for s in used_slugs):
                topic["used"] = True

    return {
        "total_topics": len(trending),
        "used_topics": sum(1 for t in trending if t["used"]),
        "pending_topics": sum(1 for t in trending if not t["used"]),
        "topics": trending,
    }


def _get_hype_topics() -> list:
    """Topics de HYPE global para adaptar ao FraLib."""
    return [
        {"topic": "DeepSeek e a revolução da IA open source", "hype": "DeepSeek", "category": "ia"},
        {"topic": "GPT-5: o que mudou para profissionais", "hype": "GPT-5", "category": "ia"},
        {"topic": "Agentes de IA autônomos no trabalho", "hype": "AI Agents", "category": "ia"},
        {"topic": "Canto da Billie Eilish no Grammy 2026", "hype": "Billie Eilish", "category": "hype"},
        {"topic": "O futuro do trabalho remoto pós-IA", "hype": "Trabalho remoto", "category": "tech"},
        {"topic": "Micro SaaS: tendência ou bolha?", "hype": "Micro SaaS", "category": "negócios"},
        {"topic": "Pixel 10 e a câmera que pensa sozinha", "hype": "Pixel 10", "category": "hype"},
        {"topic": "Robô humanoide da Figure nos EUA", "hype": "Figure AI", "category": "tech"},
        {"topic": "Criptomoedas em 2026: vale a pena?", "hype": "Bitcoin", "category": "negócios"},
        {"topic": "Automação de tarefas com Cursor AI", "hype": "Cursor AI", "category": "ia"},
    ]


def _get_blog_articles_from_db() -> list:
    """Busca artigos do banco de dados."""
    articles = []
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT slug, titulo, meta_description, keywords, gerado_em, topic, filepath
                FROM blog_articles
                ORDER BY gerado_em DESC
                LIMIT 50
            """))
            for row in result:
                articles.append({
                    "slug": row.slug,
                    "titulo": row.titulo,
                    "meta": row.meta_description,
                    "keywords": json.loads(row.keywords) if row.keywords else [],
                    "gerado_em": row.gerado_em.isoformat() if row.gerado_em else None,
                    "topic": row.topic,
                })
    except Exception:
        pass
    return articles


@router.get("/blog-analytics")
async def get_blog_analytics(user: dict = Depends(get_current_user)):
    """Retorna analytics completo do blog para o superadmin."""
    # Verificar se é superadmin
    if not user.get("is_superadmin") and user.get("role") != "superadmin":
        raise HTTPException(403, "Acesso restrito ao superadmin")

    stats = _get_blog_stats()
    trending = _get_trending_topics()
    hype = _get_hype_topics()
    articles_db = _get_blog_articles_from_db()

    # Calcular saúde do sistema
    health = {
        "status": "unknown",
        "last_run": stats["last_generated"],
        "posts_today": 0,
        "posts_this_week": 0,
    }

    if stats["last_generated"]:
        last_date = datetime.fromisoformat(stats["last_generated"])
        now = datetime.now()

        if last_date.date() == now.date():
            health["status"] = "healthy"
            health["posts_today"] = stats["total_posts"] - (stats["posts_by_category"].get("today", 0))
        elif (now - last_date).days <= 1:
            health["status"] = "degraded"
        else:
            health["status"] = "inactive"

    # Posts da semana
    week_ago = datetime.now() - timedelta(days=7)
    for post in stats["recent_posts"]:
        if post.get("date"):
            try:
                post_date = datetime.fromisoformat(post["date"])
                if post_date >= week_ago:
                    health["posts_this_week"] += 1
            except Exception:
                pass

    return {
        "ok": True,
        "stats": stats,
        "trending": trending,
        "hype_topics": hype,
        "articles_db": articles_db,
        "health": health,
        "generated_at": datetime.now().isoformat(),
    }


@router.post("/blog-generate")
async def trigger_blog_generation(
    count: int = 3,
    user: dict = Depends(get_current_user)
):
    """Dispara geração de posts manualmente."""
    if not user.get("is_superadmin") and user.get("role") != "superadmin":
        raise HTTPException(403, "Acesso restrito ao superadmin")

    # Importar e rodar o script
    import subprocess
    import sys

    script_path = Path(__file__).parent.parent.parent / "scripts" / "cron_blog_automation.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        return {
            "ok": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao executar script: {str(e)}")


@router.get("/blog-rankings")
async def get_blog_rankings(user: dict = Depends(get_current_user)):
    """Retorna rankings e posição do blog (simulado - integrar com analytics real)."""
    if not user.get("is_superadmin") and user.get("role") != "superadmin":
        raise HTTPException(403, "Acesso restrito ao superadmin")

    # Simular dados de ranking (em produção, integrar com Google Search Console)
    stats = _get_blog_stats()

    return {
        "ok": True,
        "site_url": "https://seunegociofralib.site",
        "blog_url": "https://seunegociofralib.site/blog/",
        "total_indexed": stats["total_posts"],
        "impressions_30d": 0,  # Integração Google Search Console pendente
        "clicks_30d": 0,
        "avg_position": 0,
        "top_pages": [],
        "top_queries": [],
        "note": "Integre com Google Search Console para dados reais",
    }
