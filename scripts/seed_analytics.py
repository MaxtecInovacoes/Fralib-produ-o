"""
Script para popular dados de exemplo no analytics
Executar: python scripts/seed_analytics.py
"""

import sys
import os

# Carregar .env primeiro
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Usar o mesmo engine do database.py
from backend.core.database import engine
from sqlalchemy import text
import random
from datetime import datetime, timedelta

# Fontes UTM
SOURCES = ['facebook', 'instagram', 'google', 'tiktok', 'youtube', 'direct']
MEDIUMS = ['cpc', 'post', 'story', 'email', 'referral']
CAMPAIGNS = [
    'nutricionista_mae_solo',
    'advogado_iniciante',
    'dentista_pequeno_negocio',
    'fisioterapeuta_local',
    'psicologo_consultorio',
    'arquiteto_portfolio',
    'contador_mei',
    'fotografo_eventos'
]

def seed_analytics_events(count=1000):
    """Popula eventos de analytics"""
    print(f"[INFO] Inserindo {count} eventos de analytics...")

    with engine.connect() as conn:
        for i in range(count):
            days_ago = random.randint(0, 30)
            created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))

            source = random.choice(SOURCES)
            medium = random.choice(MEDIUMS)
            campaign = random.choice(CAMPAIGNS) if random.random() > 0.3 else None
            content = f"video_{random.randint(1, 5)}" if random.random() > 0.5 else None

            event_name = random.choice([
                'page_view', 'page_view', 'page_view', 'page_view',  # Mais page views
                'click', 'click',
                'form_submit',
                'scroll_depth',
                'tracked_click'
            ])

            conn.execute(text("""
                INSERT INTO analytics_events
                (session_id, event_name, utm_source, utm_medium, utm_campaign, utm_content, url, created_at)
                VALUES
                (:session_id, :event_name, :utm_source, :utm_medium, :utm_campaign, :utm_content, :url, :created_at)
            """), {
                'session_id': f'session_{random.randint(10000, 99999)}',
                'event_name': event_name,
                'utm_source': source,
                'utm_medium': medium,
                'utm_campaign': campaign,
                'utm_content': content,
                'url': 'https://seunegociofralib.site/',
                'created_at': created_at
            })

            if (i + 1) % 100 == 0:
                conn.commit()
                print(f"  [OK] {i + 1}/{count} eventos inseridos")

        conn.commit()

    print("[OK] Analytics events populados!")


def seed_ad_spend():
    """Popula gastos com ads"""
    print("[INFO] Inserindo dados de gastos com ads...")

    with engine.connect() as conn:
        # Inserir gastos para os últimos 30 dias
        for days_ago in range(30, 0, -1):
            date = datetime.now().date() - timedelta(days=days_ago)

            for source in ['facebook', 'google', 'instagram', 'tiktok']:
                # Facebook e Google gastam mais
                if source in ['facebook', 'google']:
                    cost = random.uniform(100, 500)
                else:
                    cost = random.uniform(20, 150)

                campaign = random.choice(CAMPAIGNS)

                conn.execute(text("""
                    INSERT INTO ad_spend (date, source, campaign, cost, platform)
                    VALUES (:date, :source, :campaign, :cost, :platform)
                    ON CONFLICT DO NOTHING
                """), {
                    'date': date,
                    'source': source,
                    'campaign': campaign,
                    'cost': round(cost, 2),
                    'platform': source
                })

        conn.commit()

    print("[OK] Ad spend populado!")


def seed_demo_leads_with_utm():
    """Simula leads com UTM (para fins de teste)"""
    print("[INFO] Simulando leads com UTM...")

    with engine.connect() as conn:
        # Verificar se a coluna utm_source existe na tabela users
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'utm_source'
        """)).fetchone()

        if not result:
            print("[WARN] Coluna utm_source nao existe na tabela users")
            print("       (Isso e normal - sera adicionada quando necessario)")
            return

        print("[OK] Coluna utm_source encontrada na tabela users")


if __name__ == '__main__':
    print("=" * 50)
    print("Seed de Analytics para FraLib")
    print("=" * 50)

    try:
        seed_analytics_events(500)
        seed_ad_spend()
        seed_demo_leads_with_utm()

        print("")
        print("=" * 50)
        print("SEED COMPLETO!")
        print("=" * 50)
        print("")
        print("[INFO] Acesse o Growth Analytics no superadmin para ver os dados.")
        print("       URL: http://localhost:3000/superadmin.html")
        print("       Aba: Growth Analytics")

    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
