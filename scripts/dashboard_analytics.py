"""
Dashboard rápido: extrai os números importantes dos dados de tracking existentes.

Uso: python scripts/dashboard_analytics.py [--dias=7]

Saída: tabela formatada com os KPIs principais de comportamento da landing.
"""

import argparse
import sys
from pathlib import Path

# Adicionar backend ao path
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from sqlalchemy import text  # noqa: E402

from core.database import SessionLocal  # noqa: E402


def fmt(n):
    if n is None:
        return "—"
    if isinstance(n, float):
        return f"{n:.2f}"
    return f"{n:,}".replace(",", ".")


def pct(num, denom):
    if not denom:
        return "—"
    return f"{(num / denom * 100):.1f}%"


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dias", type=int, default=7, help="Janela em dias (default 7)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print(f"\n{'=' * 70}")
        print(f"  DASHBOARD DE ANALYTICS — FraLib Landing")
        print(f"  Período: últimos {args.dias} dias")
        print(f"{'=' * 70}\n")

        # ============================================================
        # 1. VISÃO GERAL
        # ============================================================
        row = db.execute(text(f"""
            WITH s AS (
                SELECT session_id, BOOL_OR(evento = 'bounce') AS bounce
                FROM landing_analytics
                WHERE criado_em >= NOW() - INTERVAL '{args.dias} days'
                GROUP BY session_id
            )
            SELECT
                COUNT(*) AS total_sessoes,
                COUNT(*) FILTER (WHERE bounce) AS bounces
            FROM s
        """)).fetchone()

        total_sessoes, total_bounces = row
        print("📊 VISÃO GERAL")
        print(f"   Total de sessões:        {fmt(total_sessoes)}")
        print(f"   Bounces:                 {fmt(total_bounces)}")
        print(f"   Bounce rate:             {pct(total_bounces, total_sessoes)}")
        print()

        # ============================================================
        # 2. SCROLL DEPTH
        # ============================================================
        rows = db.execute(text(f"""
            SELECT
                SPLIT_PART(valor_extra, '|', 1)::INT AS depth,
                COUNT(DISTINCT session_id) AS usuarios
            FROM landing_analytics
            WHERE evento = 'scroll_depth'
              AND criado_em >= NOW() - INTERVAL '{args.dias} days'
              AND valor_extra ~ '^[0-9]+\\|'
            GROUP BY depth
            ORDER BY depth
        """)).fetchall()

        print("📜 SCROLL DEPTH (% dos visitantes que alcançam)")
        if rows:
            max_users = max(r[1] for r in rows)
            for depth, users in rows:
                bar = "█" * int(users / max_users * 30) if max_users else ""
                print(f"   {depth:>3}%  {fmt(users):>6} sessões  {pct(users, total_sessoes):>6}  {bar}")
        else:
            print("   (sem dados de scroll_depth ainda)")
        print()

        # ============================================================
        # 3. FUNIL DE CONVERSÃO
        # ============================================================
        row = db.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE evento = 'view')                  AS visit,
                COUNT(*) FILTER (WHERE evento = 'funnel_scroll_25')      AS scroll_25,
                COUNT(*) FILTER (WHERE evento = 'funnel_scroll_50')      AS scroll_50,
                COUNT(*) FILTER (WHERE evento = 'funnel_cta_clicked')    AS cta_clicked,
                COUNT(*) FILTER (WHERE evento = 'funnel_form_submitted') AS form_submitted,
                COUNT(DISTINCT session_id) AS sessoes
            FROM landing_analytics
            WHERE criado_em >= NOW() - INTERVAL '{args.dias} days'
        """)).fetchone()

        visit, scroll25, scroll50, cta, form, sessoes = row
        print("🔻 FUNIL DE CONVERSÃO")
        if sessoes:
            print(f"   Visitantes únicos:       {fmt(sessoes)}")
            print(f"   ↓ 25% scroll:           {fmt(scroll25)}  {pct(scroll25, sessoes)}")
            print(f"   ↓ 50% scroll:           {fmt(scroll50)}  {pct(scroll50, sessoes)}")
            print(f"   ↓ Clicaram CTA:         {fmt(cta)}  {pct(cta, sessoes)}")
            print(f"   ↓ Form enviado:         {fmt(form)}  {pct(form, sessoes)}")
            print()
            print(f"   💡 CONVERSÃO TOTAL:      {pct(form, sessoes)} (visit → form)")
            print(f"   💡 TAXA DE CTA:          {pct(cta, sessoes)} (visit → click CTA)")
        else:
            print("   (sem dados de funil ainda)")
        print()

        # ============================================================
        # 4. CTAS MAIS CLICADOS
        # ============================================================
        rows = db.execute(text(f"""
            SELECT evento, COUNT(*) AS clicks, COUNT(DISTINCT session_id) AS users
            FROM landing_analytics
            WHERE evento LIKE 'click\\_%' ESCAPE '\\'
              AND criado_em >= NOW() - INTERVAL '{args.dias} days'
            GROUP BY evento
            ORDER BY clicks DESC
            LIMIT 10
        """)).fetchall()

        print("🎯 TOP CTAs (mais clicados)")
        if rows:
            total_clicks = sum(r[1] for r in rows)
            for evento, clicks, users in rows:
                print(f"   {evento:<28} {fmt(clicks):>6} cliques  ({fmt(users)} usuários)")
        else:
            print("   (sem cliques registrados ainda)")
        print()

        # ============================================================
        # 5. EXIT POR SEÇÃO (onde os usuários saem)
        # ============================================================
        rows = db.execute(text(f"""
            SELECT valor_extra, COUNT(*) AS exits
            FROM landing_analytics
            WHERE evento = 'exit_section'
              AND criado_em >= NOW() - INTERVAL '{args.dias} days'
            GROUP BY valor_extra
            ORDER BY exits DESC
            LIMIT 10
        """)).fetchall()

        print("🚪 ONDE OS USUÁRIOS SAEM (top 10 seções de exit)")
        if rows:
            total_exits = sum(r[1] for r in rows)
            for secao, exits in rows:
                pct_exit = (exits / total_exits * 100) if total_exits else 0
                bar = "█" * int(pct_exit / 2)
                print(f"   {str(secao):<20} {fmt(exits):>5} exits  {pct_exit:>5.1f}%  {bar}")
        else:
            print("   (sem dados de exit_section ainda)")
        print()

        # ============================================================
        # 6. TEMPO DE PERMANÊNCIA
        # ============================================================
        row = db.execute(text(f"""
            SELECT
                AVG(valor_extra::INT) AS media,
                MIN(valor_extra::INT) AS minimo,
                MAX(valor_extra::INT) AS maximo,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_extra::INT) AS mediana
            FROM landing_analytics
            WHERE evento = 'time_spent'
              AND criado_em >= NOW() - INTERVAL '{args.dias} days'
              AND valor_extra ~ '^[0-9]+$'
        """)).fetchone()

        print("⏱️  TEMPO DE PERMANÊNCIA (segundos)")
        if row and row[0]:
            media, minimo, maximo, mediana = row
            print(f"   Média:   {fmt(media)}s ({fmt(media / 60)} min)")
            print(f"   Mediana: {fmt(mediana)}s")
            print(f"   Min/Max: {fmt(minimo)}s / {fmt(maximo)}s")
        else:
            print("   (sem dados de time_spent ainda)")
        print()

        # ============================================================
        # 7. SEÇÕES MAIS VISTAS
        # ============================================================
        rows = db.execute(text(f"""
            SELECT valor_extra, COUNT(*) AS views, COUNT(DISTINCT session_id) AS users
            FROM landing_analytics
            WHERE evento = 'section_view'
              AND criado_em >= NOW() - INTERVAL '{args.dias} days'
            GROUP BY valor_extra
            ORDER BY views DESC
            LIMIT 10
        """)).fetchall()

        print("👁️  SEÇÕES MAIS VISTAS")
        if rows:
            for secao, views, users in rows:
                print(f"   {str(secao):<22} {fmt(views):>5} views  ({fmt(users)} usuários únicos)")
        else:
            print("   (sem dados de section_view ainda)")
        print()

        # ============================================================
        # 8. CONVERSÕES DO META PIXEL
        # ============================================================
        print("💰 EVENTOS DE CONVERSÃO (Meta Pixel)")
        conversions = {
            "Lead": "visit → interesse (signup/CTA)",
            "Contact": "whatsapp clicado",
            "InitiateCheckout": "plano clicado",
            "CompleteRegistration": "form beta enviado",
        }
        for event, desc in conversions.items():
            row = db.execute(text(f"""
                SELECT COUNT(*) FROM landing_analytics
                WHERE evento LIKE '%fbq%' OR valor_extra LIKE :ev
            """), {"ev": f"%{event}%"}).fetchone()
            # Como o Meta Pixel não vai pro banco, usamos os eventos do tracker como proxy
        # Usar eventos do tracker como proxy
        for evento_tracker, desc in [
            ("click_signup", "Lead (signup)"),
            ("click_whatsapp", "Contact (whatsapp)"),
            ("click_plano_trial", "InitiateCheckout (trial)"),
            ("click_plano_starter", "InitiateCheckout (starter)"),
            ("click_plano_pro", "InitiateCheckout (pro)"),
            ("convert_beta_registration", "CompleteRegistration (beta)"),
        ]:
            row = db.execute(text(f"""
                SELECT COUNT(DISTINCT session_id) FROM landing_analytics
                WHERE evento = :ev
                  AND criado_em >= NOW() - INTERVAL '{args.dias} days'
            """), {"ev": evento_tracker}).fetchone()
            count = row[0] if row else 0
            print(f"   {desc:<35} {fmt(count):>5} conversões")
        print()

        print(f"{'=' * 70}\n")

    finally:
        db.close()


if __name__ == "__main__":
    run()
