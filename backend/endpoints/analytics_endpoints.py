"""
FraLib Analytics Endpoints - UTM Tracking, KPIs, Funil de Conversão

Este módulo implementa:
- UTM parameter tracking
- Event collection
- Funnel analytics
- KPI calculations
- Cohort analysis
- Lead scoring
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
import logging
import json
import random

from fastapi import APIRouter, Depends, HTTPException, Request
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.database import get_db
from backend.core.access_control import require_superadmin

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/analytics', tags=['analytics'])

# Fontes UTM para seed
SOURCES = ['facebook', 'instagram', 'google', 'tiktok', 'youtube', 'direct']
MEDIUMS = ['cpc', 'post', 'story', 'email', 'referral']
CAMPAIGNS = [
    'nutricionista_mae_solo', 'advogado_iniciante', 'dentista_pequeno_negocio',
    'fisioterapeuta_local', 'psicologo_consultorio', 'arquiteto_portfolio',
    'contador_mei', 'fotografo_eventos'
]


# ============================================================
# UTM PARAMETER TRACKING
# ============================================================

@router.post("/events")
async def track_events(request: Request, db: Session = Depends(get_db)):
    """
    Recebe eventos de analytics do frontend e armazena.
    """
    try:
        body = await request.json()
        session_id = body.get('session_id')
        events = body.get('events', [])

        if not session_id or not events:
            return {"ok": False, "error": "session_id and events required"}

        for event in events:
            # Salvar evento na tabela analytics_events
            db.execute(text("""
                INSERT INTO analytics_events (
                    session_id, event_name, event_data, utm_source,
                    utm_medium, utm_campaign, utm_content, utm_term,
                    url, referrer, user_agent, created_at::timestamp
                ) VALUES (
                    :session_id, :event_name, :event_data,
                    :utm_source, :utm_medium, :utm_campaign, :utm_content, :utm_term,
                    :url, :referrer, :user_agent, NOW()
                )
            """), {
                "session_id": session_id,
                "event_name": event.get('event_name'),
                "event_data": json.dumps(event.get('data', {})),
                "utm_source": event.get('data', {}).get('utm', {}).get('utm_source'),
                "utm_medium": event.get('data', {}).get('utm', {}).get('utm_medium'),
                "utm_campaign": event.get('data', {}).get('utm', {}).get('utm_campaign'),
                "utm_content": event.get('data', {}).get('utm', {}).get('utm_content'),
                "utm_term": event.get('data', {}).get('utm', {}).get('utm_term'),
                "url": event.get('data', {}).get('url'),
                "referrer": event.get('data', {}).get('referrer'),
                "user_agent": event.get('data', {}).get('user_agent'),
            })

        db.commit()
        return {"ok": True, "count": len(events)}

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error tracking events: {e}")
        db.rollback()
        return {"ok": False, "error": str(e)}


@router.get("/utm")
async def get_utm_analytics(
    period: str = "7d",
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna métricas de UTM: leads por source, medium, campaign.
    """
    period_days = {
        "24h": 1, "7d": 7, "30d": 30, "90d": 90
    }.get(period, 7)

    try:
        # Leads por utm_source
        by_source = db.execute(text(f"""
            SELECT
                COALESCE(utm_source, 'direct') as source,
                COUNT(*) as total_leads,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(CASE WHEN status = 'trial' THEN 1 END) as trials,
                COUNT(CASE WHEN status IN ('pro', 'ilimitado', 'agency') THEN 1 END) as pagantes
            FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
            GROUP BY COALESCE(utm_source, 'direct')
            ORDER BY total_leads DESC
        """)).fetchall()

        # Leads por utm_medium
        by_medium = db.execute(text(f"""
            SELECT
                COALESCE(utm_medium, 'none') as medium,
                COUNT(*) as total_leads,
                COUNT(CASE WHEN status = 'trial' THEN 1 END) as trials
            FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
            GROUP BY COALESCE(utm_medium, 'none')
            ORDER BY total_leads DESC
        """)).fetchall()

        # Leads por utm_campaign
        by_campaign = db.execute(text(f"""
            SELECT
                COALESCE(utm_campaign, 'none') as campaign,
                utm_source,
                COUNT(*) as total_leads,
                COUNT(CASE WHEN status = 'trial' THEN 1 END) as trials,
                COUNT(CASE WHEN status IN ('pro', 'ilimitado', 'agency') THEN 1 END) as pagantes
            FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
            GROUP BY COALESCE(utm_campaign, 'none'), utm_source
            ORDER BY total_leads DESC
            LIMIT 50
        """)).fetchall()

        return {
            "ok": True,
            "period": period,
            "by_source": [
                {
                    "source": row[0],
                    "total_leads": row[1],
                    "unique_users": row[2],
                    "trials": row[3],
                    "pagantes": row[4],
                    "conversion_rate": round(row[4] / row[1] * 100, 2) if row[1] > 0 else 0
                }
                for row in by_source
            ],
            "by_medium": [
                {
                    "medium": row[0],
                    "total_leads": row[1],
                    "trials": row[2],
                    "conversion_rate": round(row[2] / row[1] * 100, 2) if row[1] > 0 else 0
                }
                for row in by_medium
            ],
            "by_campaign": [
                {
                    "campaign": row[0],
                    "source": row[1],
                    "total_leads": row[2],
                    "trials": row[3],
                    "pagantes": row[4],
                    "conversion_rate": round(row[4] / row[2] * 100, 2) if row[2] > 0 else 0
                }
                for row in by_campaign
            ]
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error fetching UTM analytics: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# FUNNEL DE CONVERSÃO
# ============================================================

@router.get("/funnel")
async def get_funnel_analytics(
    period: str = "30d",
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna o funil de conversão completo.
    """
    period_days = {
        "7d": 7, "30d": 30, "90d": 90, "all": 9999
    }.get(period, 30)

    # Se período é "all" (9999), sem filtro; senão, filtrar últimos N dias
    if period_days >= 9999:
        date_filter = "TRUE"
        date_params = {}
    else:
        date_filter = f"created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'"
        date_params = {}

    try:
        # Contar visitantes (page_views)
        visitors = db.execute(text(f"""
            SELECT COUNT(DISTINCT session_id)
            FROM analytics_events
            WHERE event_name = 'page_view' AND {date_filter}
        """), date_params).scalar() or 0

        # Contar leads (usuários criados)
        leads = db.execute(text(f"""
            SELECT COUNT(*) FROM users WHERE {date_filter}
        """), date_params).scalar() or 0

        # Contar trials
        trials = db.execute(text(f"""
            SELECT COUNT(*) FROM users
            WHERE plano = 'trial' AND {date_filter}
        """), date_params).scalar() or 0

        # Contar pagantes
        pagantes = db.execute(text(f"""
            SELECT COUNT(*) FROM users
            WHERE plano IN ('pro', 'ilimitado', 'agency', 'starter') AND {date_filter}
        """), date_params).scalar() or 0

        # Contar retidos (usuários que usaram nos últimos 30 dias)
        retidos = db.execute(text("""
            SELECT COUNT(*) FROM users
            WHERE ultimo_acesso::timestamp >= NOW() - INTERVAL '30 days'
            AND plano IN ('pro', 'ilimitado', 'agency', 'starter')
        """)).scalar() or 0

        # Calcular taxas
        visitantes_to_leads = round(leads / visitors * 100, 2) if visitors > 0 else 0
        leads_to_trials = round(trials / leads * 100, 2) if leads > 0 else 0
        trials_to_pagantes = round(pagantes / trials * 100, 2) if trials > 0 else 0
        pagantes_to_retidos = round(retidos / pagantes * 100, 2) if pagantes > 0 else 0

        return {
            "ok": True,
            "period": period,
            "funnel": {
                "visitantes": {"count": visitors, "rate": 100},
                "leads": {"count": leads, "rate": visitantes_to_leads},
                "trials": {"count": trials, "rate": leads_to_trials},
                "pagantes": {"count": pagantes, "rate": trials_to_pagantes},
                "retidos": {"count": retidos, "rate": pagantes_to_retidos}
            },
            "conversion_rates": {
                "visitor_to_lead": visitantes_to_leads,
                "lead_to_trial": leads_to_trials,
                "trial_to_pago": trials_to_pagantes,
                "pago_to_retained": pagantes_to_retidos
            },
            "metrics": {
                "overall_conversion": round(pagantes / visitors * 100, 4) if visitors > 0 else 0,
                "total_conversions": pagantes
            }
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error fetching funnel analytics: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# KPIs
# ============================================================

@router.get("/kpi")
async def get_kpi_analytics(
    period: str = "30d",
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna KPIs principais: CPL, CAC, LTV, ROAS, CTR, Bounce Rate.
    """
    period_days = {
        "7d": 7, "30d": 30, "90d": 90
    }.get(period, 30)

    try:
        # Totais de usuários
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
        trials = db.execute(text("SELECT COUNT(*) FROM users WHERE plano = 'trial'")).scalar() or 0
        pagantes = db.execute(text("""
            SELECT COUNT(*) FROM users
            WHERE plano IN ('pro', 'ilimitado', 'agency', 'starter')
        """)).scalar() or 0

        # Novos usuários no período
        new_users = db.execute(text(f"""
            SELECT COUNT(*) FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
        """)).scalar() or 0

        # Calcular MRR estimado (R$97 por usuário pago)
        mrr = pagantes * 97

        # Obter gastos com ads (mock - viria de API de anúncios)
        ad_spend = db.execute(text(f"""
            SELECT COALESCE(SUM(cost), 0) FROM ad_spend
            WHERE date >= NOW() - INTERVAL '{int(period_days)} days'
        """)).scalar() or 0

        # Se não houver dados de ads, usar valor placeholder
        if ad_spend == 0:
            ad_spend = new_users * 15  # CPL estimado de R$15

        # CPL = Gasto Ads / Total Leads
        cpl = round(ad_spend / new_users, 2) if new_users > 0 else 0

        # CAC = Gasto Ads / Total Clientes
        cac = round(ad_spend / pagantes, 2) if pagantes > 0 else 0

        # LTV = ARPU * Lifespan (assumindo ARPU de R$97, lifespan de 12 meses)
        arpu = 97
        lifespan_months = 12
        ltv = arpu * lifespan_months

        # ROAS = Receita / Gasto Ads (receita = MRR)
        roas = round(mrr / ad_spend, 2) if ad_spend > 0 else 0

        # Page views e cliques
        page_views = db.execute(text(f"""
            SELECT COUNT(*) FROM analytics_events
            WHERE event_name = 'page_view'
            AND created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
        """)).scalar() or 0

        clicks = db.execute(text(f"""
            SELECT COUNT(*) FROM analytics_events
            WHERE event_name = 'click'
            AND created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
        """)).scalar() or 0

        # CTR = Cliques / Impressões
        ctr = round(clicks / page_views * 100, 2) if page_views > 0 else 0

        # Bounce Rate = Sessoes com apenas 1 page view / Total sessoes
        sessions = db.execute(text(f"""
            SELECT COUNT(DISTINCT session_id) FROM analytics_events
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
        """)).scalar() or 0

        single_page_sessions = db.execute(text(f"""
            SELECT COUNT(*) FROM (
                SELECT session_id, COUNT(*) as views
                FROM analytics_events
                WHERE event_name = 'page_view'
                AND created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
                GROUP BY session_id
                HAVING COUNT(*) = 1
            ) t
        """)).scalar() or 0

        bounce_rate = round(single_page_sessions / sessions * 100, 2) if sessions > 0 else 0

        # Taxa de conversão trial
        trial_rate = round(trials / total_users * 100, 2) if total_users > 0 else 0

        return {
            "ok": True,
            "period": period,
            "overview": {
                "total_leads": total_users,
                "total_trials": trials,
                "total_pagantes": pagantes,
                "mrr": mrr,
                "new_leads_period": new_users
            },
            "kpis": {
                "cpl": cpl,  # Custo por Lead
                "cac": cac,  # Custo de Aquisição de Cliente
                "ltv": ltv,  # Lifetime Value
                "roas": roas,  # Return on Ad Spend
                "bounce_rate": bounce_rate,
                "ctr": ctr,  # Click Through Rate
                "trial_conversion_rate": trial_rate,
                "paid_conversion_rate": round(pagantes / trials * 100, 2) if trials > 0 else 0
            },
            "period_stats": {
                "ad_spend": ad_spend,
                "page_views": page_views,
                "clicks": clicks,
                "sessions": sessions
            }
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error fetching KPI analytics: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# COHORT ANALYSIS
# ============================================================

@router.get("/cohorts")
async def get_cohort_analysis(
    period: str = "90d",
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna análise de cohorts - conversão ao longo do tempo.
    """
    try:
        # Cohorts diários - novos usuários e conversão por dia
        cohort_data = db.execute(text(f"""
            SELECT
                DATE(created_at::timestamp) as cohort_date,
                COUNT(*) as new_users,
                COUNT(CASE WHEN plano IN ('pro', 'ilimitado', 'agency', 'starter') THEN 1 END) as converted
            FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
            GROUP BY DATE(created_at::timestamp)
            ORDER BY cohort_date DESC
            LIMIT 90
        """.replace(':days', str({"7d": 7, "30d": 30, "90d": 90}.get(period, 90))))).fetchall()

        # Calcular taxa de conversão por cohort
        cohorts = []
        for row in cohort_data:
            converted = row[1] or 0
            new_users = row[2] or 0
            conversion_rate = round(converted / new_users * 100, 2) if new_users > 0 else 0

            cohorts.append({
                "date": str(row[0]),
                "new_users": new_users,
                "converted": converted,
                "conversion_rate": conversion_rate
            })

        # Retention por cohort semanal
        retention_data = db.execute(text("""
            SELECT
                DATE_TRUNC('week', created_at::timestamp) as week,
                COUNT(*) as total_users,
                COUNT(CASE WHEN ultimo_acesso::timestamp >= NOW() - INTERVAL '7 days' THEN 1 END) as week1,
                COUNT(CASE WHEN ultimo_acesso::timestamp >= NOW() - INTERVAL '14 days' THEN 1 END) as week2,
                COUNT(CASE WHEN ultimo_acesso::timestamp >= NOW() - INTERVAL '30 days' THEN 1 END) as month1
            FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(period_days)} days'
            GROUP BY DATE_TRUNC('week', created_at::timestamp)
            ORDER BY week DESC
        """.replace(':days', str({"7d": 7, "30d": 30, "90d": 90}.get(period, 90))))).fetchall()

        retention = []
        for row in retention_data:
            total = row[1] or 0
            retention.append({
                "week": str(row[0]),
                "total_users": total,
                "retention_week1": round(row[2] / total * 100, 2) if total > 0 else 0,
                "retention_week2": round(row[3] / total * 100, 2) if total > 0 else 0,
                "retention_month1": round(row[4] / total * 100, 2) if total > 0 else 0
            })

        return {
            "ok": True,
            "period": period,
            "daily_cohorts": cohorts,
            "weekly_retention": retention
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error fetching cohort analytics: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# LEAD SCORE
# ============================================================

@router.get("/lead-score")
async def get_lead_score_analytics(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna distribuição de lead scores e análise.
    """
    try:
        # Distribuição de leads por status/score
        status_dist = db.execute(text("""
            SELECT
                plano as status,
                COUNT(*) as count,
                AVG(COALESCE(sites_prontos, 0)) as avg_sites,
                AVG(COALESCE(total_leads, 0)) as avg_leads
            FROM users
            GROUP BY plano
            ORDER BY count DESC
        """)).fetchall()

        # Leads por source (UTM)
        source_dist = db.execute(text("""
            SELECT
                COALESCE(utm_source, 'direct') as source,
                COUNT(*) as total,
                COUNT(CASE WHEN plano IN ('pro', 'ilimitado', 'agency', 'starter') THEN 1 END) as converted
            FROM users
            GROUP BY COALESCE(utm_source, 'direct')
            ORDER BY total DESC
        """)).fetchall()

        # Score médio por source
        avg_score_by_source = []
        for row in source_dist:
            source = row[0]
            total = row[1] or 0
            converted = row[2] or 0
            score = round(converted / total * 100, 2) if total > 0 else 0

            # Classificar: quente (>30%), morno (10-30%), frio (<10%)
            classification = "hot" if score > 30 else ("warm" if score > 10 else "cold")

            avg_score_by_source.append({
                "source": source,
                "total_leads": total,
                "converted": converted,
                "score": score,
                "classification": classification
            })

        return {
            "ok": True,
            "status_distribution": [
                {
                    "status": row[0],
                    "count": row[1],
                    "avg_sites": round(row[2], 2) if row[2] else 0,
                    "avg_leads": round(row[3], 2) if row[3] else 0
                }
                for row in status_dist
            ],
            "source_performance": avg_score_by_source,
            "summary": {
                "hot_sources": [s for s in avg_score_by_source if s["classification"] == "hot"],
                "warm_sources": [s for s in avg_score_by_source if s["classification"] == "warm"],
                "cold_sources": [s for s in avg_score_by_source if s["classification"] == "cold"]
            }
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error fetching lead score analytics: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# DASHBOARD GROWTH ANALYTICS (resumo para superadmin)
# ============================================================

@router.get("/growth-dashboard")
async def get_growth_dashboard(
    period: str = "30d",
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna dados consolidados para o dashboard de Growth Analytics.
    """
    try:
        # Obter dados do funil
        funnel_data = await get_funnel_analytics(period, db)

        # Obter KPIs
        kpi_data = await get_kpi_analytics(period, db)

        # Obter UTM data
        utm_data = await get_utm_analytics(period, db)

        # Obter cohorts
        cohort_data = await get_cohort_analysis(period, db)

        # Obter lead scores
        score_data = await get_lead_score_analytics(db)

        # Timeline de leads (últimos 30 dias)
        days_num = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        timeline = db.execute(text(f"""
            SELECT
                DATE(created_at::timestamp) as date,
                COUNT(*) as new_leads,
                COUNT(CASE WHEN plano IN ('pro', 'ilimitado', 'agency', 'starter') THEN 1 END) as new_paid
            FROM users
            WHERE created_at::timestamp >= NOW() - INTERVAL '{int(days_num)} days'
            GROUP BY DATE(created_at::timestamp)
            ORDER BY date DESC
        """)).fetchall()

        return {
            "ok": True,
            "period": period,
            "funnel": funnel_data.get("funnel", {}),
            "kpis": kpi_data.get("kpis", {}),
            "overview": kpi_data.get("overview", {}),
            "utm": {
                "by_source": utm_data.get("by_source", [])[:10],
                "by_medium": utm_data.get("by_medium", [])
            },
            "cohorts": cohort_data.get("daily_cohorts", [])[:30],
            "retention": cohort_data.get("weekly_retention", []),
            "lead_scores": score_data.get("source_performance", []),
            "timeline": [
                {
                    "date": str(row[0]),
                    "new_leads": row[1],
                    "new_paid": row[2]
                }
                for row in timeline
            ]
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error fetching growth dashboard: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/seed")
async def seed_demo_data(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Popula dados de exemplo para testar o analytics.
    """
    try:
        # Criar tabelas se não existirem
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                event_name VARCHAR(100) NOT NULL,
                event_data TEXT,
                utm_source VARCHAR(100),
                utm_medium VARCHAR(100),
                utm_campaign VARCHAR(100),
                utm_content VARCHAR(100),
                utm_term VARCHAR(100),
                url TEXT,
                referrer TEXT,
                user_agent TEXT,
                created_at::timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events(session_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_event ON analytics_events(event_name)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_date ON analytics_events(created_at::timestamp)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_utm ON analytics_events(utm_source, utm_campaign)"))

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ad_spend (
                id SERIAL PRIMARY KEY,
                date DATE,
                source VARCHAR(100),
                campaign VARCHAR(100),
                cost FLOAT DEFAULT 0,
                platform VARCHAR(50),
                created_at::timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_spend_date ON ad_spend(date, source)"))

        # Inserir eventos de analytics
        event_count = 0
        for i in range(500):
            days_ago = random.randint(0, 30)
            created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))

            source = random.choice(SOURCES)
            medium = random.choice(MEDIUMS)
            campaign = random.choice(CAMPAIGNS) if random.random() > 0.3 else None

            event_name = random.choice([
                'page_view', 'page_view', 'page_view', 'page_view',
                'click', 'click', 'form_submit', 'scroll_depth'
            ])

            db.execute(text("""
                INSERT INTO analytics_events
                (session_id, event_name, utm_source, utm_medium, utm_campaign, url, created_at::timestamp)
                VALUES (:session_id, :event_name, :utm_source, :utm_medium, :utm_campaign, :url, :created_at::timestamp)
            """), {
                'session_id': f'session_{random.randint(10000, 99999)}',
                'event_name': event_name,
                'utm_source': source,
                'utm_medium': medium,
                'utm_campaign': campaign,
                'url': 'https://seunegociofralib.site/',
                'created_at': created_at
            })
            event_count += 1

        # Inserir gastos com ads
        spend_count = 0
        for days_ago in range(30, 0, -1):
            date = datetime.now().date() - timedelta(days=days_ago)
            for source in ['facebook', 'google', 'instagram', 'tiktok']:
                cost = random.uniform(100, 500) if source in ['facebook', 'google'] else random.uniform(20, 150)
                campaign = random.choice(CAMPAIGNS)

                db.execute(text("""
                    INSERT INTO ad_spend (date, source, campaign, cost, platform)
                    VALUES (:date, :source, :campaign, :cost, :platform)
                """), {
                    'date': date,
                    'source': source,
                    'campaign': campaign,
                    'cost': round(cost, 2),
                    'platform': source
                })
                spend_count += 1

        db.commit()

        return {
            "ok": True,
            "message": "Dados de exemplo criados com sucesso!",
            "events_created": event_count,
            "ad_spend_created": spend_count
        }

    except Exception as e:
        try: db.rollback()
        except: pass
        logger.error(f"Error seeding demo data: {e}")
        db.rollback()
        return {"ok": False, "error": str(e)}
