"""
Blog Analytics Endpoints — Superadmin Dashboard
Retorna métricas e estatísticas do blog automático.
"""
import json
import os
import re
import requests
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

    # Calcular saude do sistema baseado em mtime dos arquivos
    health = {
        "status": "unknown",
        "last_run": None,
        "posts_today": 0,
        "posts_this_week": 0,
        "posts_this_month": 0,
    }

    if POSTS_DIR.exists():
        all_posts = list(POSTS_DIR.glob("*.html"))
        if all_posts:
            last_mtime = max(f.stat().st_mtime for f in all_posts)
            health["last_run"] = datetime.fromtimestamp(last_mtime).isoformat()

            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start.replace(day=1)

            for f in all_posts:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime >= today_start:
                    health["posts_today"] += 1
                    health["posts_this_week"] += 1
                    health["posts_this_month"] += 1
                elif mtime >= week_start:
                    health["posts_this_week"] += 1
                    health["posts_this_month"] += 1
                elif mtime >= month_start:
                    health["posts_this_month"] += 1

            last_date = datetime.fromtimestamp(last_mtime)
            today_date = now.date()
            last_run_date = last_date.date()

            if last_run_date == today_date:
                health["status"] = "healthy"
            elif (now.date() - last_run_date).days <= 1:
                health["status"] = "degraded"
            else:
                health["status"] = "inactive"
        else:
            health["status"] = "inactive"

    return {
        "ok": True,
        "stats": stats,
        "trending": trending,
        "hype_topics": hype,
        "articles_db": articles_db,
        "health": health,
        "generated_at": datetime.now().isoformat(),
    }


# ============================================================================
# NOVOS ENDPOINTS — Painel Blog no Superadmin
# ============================================================================

# Subset de BLOCKED_KEYWORDS usado no scoring
_QUALITY_BLOCKED = [
    "crime", "crimes", "homicidio", "assassinato", "roubo", "furto",
    "violencia", "estupro", "trafico", "drogas", "policia", "preso",
    "eleicao 2026", "campanha eleitoral",
]


def _require_superadmin(user: dict) -> None:
    """Garante que user eh superadmin."""
    if not user.get("is_superadmin") and user.get("role") != "superadmin":
        raise HTTPException(403, "Acesso restrito ao superadmin")


@router.get("/blog-quality")
async def get_blog_quality(user: dict = Depends(get_current_user)):
    """Calcula score 0-100 para cada um dos ultimos 30 posts.

    Verifica: word_count, links /planos, Franz Douglas no schema.org,
    ausencia de footer AI, presenca de BLOCKED_KEYWORDS.
    """
    _require_superadmin(user)

    if not POSTS_DIR.exists():
        return {"ok": True, "posts": [], "avg_score": 0, "checked": 0}

    posts = []
    for post_file in sorted(POSTS_DIR.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)[:30]:
        try:
            content = post_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Extrair body (entre </h1> e <div class="cta-box">)
        body_match = re.search(r'</h1>(.*?)<div class="cta-box">', content, re.DOTALL)
        body = body_match.group(1) if body_match else content

        word_count = len(re.findall(r'\w+', body))
        plan_links = len(re.findall(r'<a\s+href="/planos"', body, re.IGNORECASE))
        has_franz = '"name": "Franz Douglas"' in content or "Franz Douglas" in content
        has_ai_footer = bool(re.search(r'(gerado automaticamente|gerado por IA|powered by AI)', content, re.I))
        body_lower = body.lower()
        blocked_hits = [kw for kw in _QUALITY_BLOCKED if kw in body_lower]

        # Score 0-100
        score = 100
        issues = []
        if word_count < 800:
            score -= 30
            issues.append(f"pouco conteudo ({word_count} palavras)")
        elif word_count < 1200:
            score -= 15
            issues.append(f"conteudo curto ({word_count} palavras)")
        if plan_links < 2:
            score -= 20
            issues.append(f"poucos links /planos ({plan_links})")
        if not has_franz:
            score -= 20
            issues.append("autor Franz Douglas ausente")
        if has_ai_footer:
            score -= 15
            issues.append("footer 'gerado por IA' presente")
        if blocked_hits:
            score -= 50
            issues.append(f"BLOCKED: {', '.join(blocked_hits)}")

        posts.append({
            "slug": post_file.stem,
            "word_count": word_count,
            "plan_links": plan_links,
            "has_franz": has_franz,
            "has_ai_footer": has_ai_footer,
            "blocked_hits": blocked_hits,
            "score": max(0, score),
            "issues": issues,
        })

    avg_score = round(sum(p["score"] for p in posts) / len(posts), 1) if posts else 0
    return {"ok": True, "posts": posts, "avg_score": avg_score, "checked": len(posts)}


@router.get("/blog-llm-stats")
async def get_blog_llm_stats(user: dict = Depends(get_current_user)):
    """Le .cron_history.jsonl e retorna stats por fonte, latencia, custo."""
    _require_superadmin(user)

    history_file = BLOG_DIR / ".cron_history.jsonl"
    if not history_file.exists():
        return {
            "ok": True,
            "note": "Sem historico ainda (.cron_history.jsonl nao existe)",
            "total_runs": 0,
            "by_source": {},
            "totals": {"success": 0, "fail": 0, "success_rate": 0, "avg_latency_ms": 0, "last_run": None},
            "cost_estimate_usd": 0,
            "tokens": {"in": 0, "out": 0},
        }

    runs = []
    with history_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    by_source = {}
    total_success = 0
    total_fail = 0
    latencies = []
    total_in = 0
    total_out = 0

    for run in runs:
        for s in run.get("sources", []):
            src = s.get("source", "unknown")
            if src not in by_source:
                by_source[src] = {"posts": 0, "successes": 0, "failures": 0, "success_rate": 0}
            by_source[src]["posts"] += s.get("posts", 0)
            by_source[src]["successes"] += s.get("successes", 0)
            by_source[src]["failures"] += s.get("failures", 0)
        total_success += run.get("sucessos", 0)
        total_fail += run.get("falhas", 0)
        latencies.append(run.get("latency_total_ms", 0))
        total_in += run.get("input_tokens_est", 0)
        total_out += run.get("output_tokens_est", 0)

    # Calcular success_rate por source
    for src, s in by_source.items():
        total = s["successes"] + s["failures"]
        s["success_rate"] = round(s["successes"] / max(total, 1) * 100, 1)

    # Custo estimado (Claude Sonnet 4)
    cost_in = (total_in / 1_000_000) * 3.0
    cost_out = (total_out / 1_000_000) * 15.0

    total_attempts = total_success + total_fail
    return {
        "ok": True,
        "total_runs": len(runs),
        "by_source": by_source,
        "totals": {
            "success": total_success,
            "fail": total_fail,
            "success_rate": round(total_success / max(total_attempts, 1) * 100, 1),
            "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
            "last_run": runs[-1].get("ts") if runs else None,
        },
        "cost_estimate_usd": round(cost_in + cost_out, 4),
        "tokens": {"in": total_in, "out": total_out},
    }


@router.get("/blog-attribution")
async def get_blog_attribution(user: dict = Depends(get_current_user)):
    """Cruza analytics_events com leads por utm_campaign."""
    _require_superadmin(user)

    out = {"by_post": [], "totals": {"views": 0, "leads": 0, "conversions": 0}, "error": None}

    if not POSTS_DIR.exists():
        return out

    try:
        with engine.connect() as conn:
            # Views por post (analytics_events.url LIKE /blog/posts/%)
            views_rows = conn.execute(text("""
                SELECT url, COUNT(*) as views, COUNT(DISTINCT COALESCE(session_id, ip_address, '')) as sessions
                FROM analytics_events
                WHERE (url LIKE '/blog/posts/%' OR url LIKE '/blog/%')
                  AND event_type = 'page_view'
                  AND created_at >= NOW() - INTERVAL '90 days'
                GROUP BY url
                ORDER BY views DESC
                LIMIT 30
            """)).fetchall()

            # Leads por utm_campaign=post_<slug>
            leads_rows = conn.execute(text("""
                SELECT utm_campaign,
                       COUNT(*) as leads,
                       COUNT(*) FILTER (WHERE status IN ('converted','paid','client')) as conversions
                FROM leads
                WHERE utm_campaign LIKE 'post_%'
                  AND created_at >= NOW() - INTERVAL '90 days'
                GROUP BY utm_campaign
            """)).fetchall()

            leads_map = {r.utm_campaign: {"leads": r.leads, "conversions": r.conversions} for r in leads_rows}

            for v in views_rows or []:
                url = v.url
                # Extrair slug do URL
                slug = url.split("/")[-1].replace(".html", "")
                if not slug or slug == "blog":
                    continue
                utm = f"post_{slug}"
                stats = leads_map.get(utm, {"leads": 0, "conversions": 0})
                out["by_post"].append({
                    "slug": slug,
                    "url": url,
                    "views": v.views,
                    "sessions": v.sessions or v.views,
                    "leads": stats["leads"],
                    "conversions": stats["conversions"],
                    "lead_rate": round(stats["leads"] / max(v.views, 1) * 100, 2),
                })
                out["totals"]["views"] += v.views
                out["totals"]["leads"] += stats["leads"]
                out["totals"]["conversions"] += stats["conversions"]
    except Exception as e:
        out["error"] = str(e)

    # Se nao tem dados de analytics_events, gera ranking pelos posts existentes
    # baseado em URLs reais (util para o painel nao ficar vazio)
    if not out["by_post"]:
        for post_file in sorted(POSTS_DIR.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)[:15]:
            slug = post_file.stem
            out["by_post"].append({
                "slug": slug,
                "url": f"/blog/posts/{slug}.html",
                "views": 0,
                "sessions": 0,
                "leads": 0,
                "conversions": 0,
                "lead_rate": 0,
                "note": "Aguardando coleta de analytics_events",
            })

    return out


# ============================================================================
# PAUSE / RESUME
# ============================================================================

PAUSE_FILE = BLOG_DIR / ".paused"


@router.post("/blog-pause")
async def pause_blog(user: dict = Depends(get_current_user)):
    """Pausa a geracao automatica do blog (cria sentinel .paused)."""
    _require_superadmin(user)
    PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAUSE_FILE.write_text(json.dumps({
        "paused_at": datetime.now().isoformat(),
        "paused_by": user.get("email", "unknown"),
    }), encoding="utf-8")
    return {"ok": True, "paused": True, "paused_at": datetime.now().isoformat()}


@router.post("/blog-resume")
async def resume_blog(user: dict = Depends(get_current_user)):
    """Retoma a geracao automatica do blog (remove sentinel .paused)."""
    _require_superadmin(user)
    if PAUSE_FILE.exists():
        PAUSE_FILE.unlink()
    return {"ok": True, "paused": False}


@router.get("/blog-pause-status")
async def blog_pause_status(user: dict = Depends(get_current_user)):
    """Retorna status atual de pausa."""
    _require_superadmin(user)
    is_paused = PAUSE_FILE.exists()
    info = None
    if is_paused:
        try:
            info = json.loads(PAUSE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"paused": is_paused, "info": info}


# ============================================================================
# GOOGLE SEARCH CONSOLE (extensao do /blog-rankings)
# ============================================================================

GSC_API_KEY = os.getenv("GSC_API_KEY", "")
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "https://seunegociofralib.site/")


@router.get("/blog-rankings")
async def get_blog_rankings(user: dict = Depends(get_current_user)):
    """Rankings de busca do blog (Google Search Console real ou fallback)."""
    _require_superadmin(user)

    stats = _get_blog_stats()
    base = {
        "ok": True,
        "site_url": GSC_SITE_URL,
        "blog_url": GSC_SITE_URL + "blog/",
        "total_indexed": stats["total_posts"],
        "source": "fallback",
    }

    if not GSC_API_KEY:
        return {
            **base,
            "impressions_30d": 0,
            "clicks_30d": 0,
            "avg_position": 0,
            "top_pages": [],
            "top_queries": [],
            "note": "GSC_API_KEY nao configurado - adicione ao .env para dados reais",
        }

    try:
        from urllib.parse import quote
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(GSC_SITE_URL, safe='')}/searchAnalytics/query"
        headers = {"Authorization": f"Bearer {GSC_API_KEY}", "Content-Type": "application/json"}
        body = {
            "startDate": start_date, "endDate": end_date,
            "dimensions": ["page"], "rowLimit": 25,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        if not resp.ok:
            return {**base, "source": "gsc_error", "note": f"GSC HTTP {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        rows = data.get("rows", [])
        top_pages = [{
            "page": r["keys"][0],
            "clicks": r["clicks"],
            "impressions": r["impressions"],
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
        } for r in rows]

        body["dimensions"] = ["query"]
        resp2 = requests.post(url, headers=headers, json=body, timeout=15)
        top_queries = []
        if resp2.ok:
            top_queries = [{
                "query": r["keys"][0],
                "clicks": r["clicks"], "impressions": r["impressions"],
                "position": round(r["position"], 1),
            } for r in resp2.json().get("rows", [])[:20]]

        return {
            **base,
            "source": "google_search_console",
            "impressions_30d": sum(p["impressions"] for p in top_pages),
            "clicks_30d": sum(p["clicks"] for p in top_pages),
            "avg_position": round(sum(p["position"] for p in top_pages) / max(len(top_pages), 1), 1),
            "top_pages": top_pages,
            "top_queries": top_queries,
        }
    except Exception as e:
        return {**base, "source": "gsc_error", "note": str(e)}
