#!/usr/bin/env python3
"""
Google Analytics 4 + Google Search Console.
Tracker de tráfego real e rankeamento.
"""

import os
import json
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"

# Google Analytics 4
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "")
GA4_API = "https://analyticsdata.googleapis.com/v1beta"

# Google Search Console
GSC_API = "https://www.googleapis.com/webmasters/v3"
GSC_PROPERTY = "sc-domain:seunegociofralib.site"


def fetch_ga4_data(access_token: str, days: int = 7) -> dict:
    """Busca dados do Google Analytics 4."""

    if not GA4_PROPERTY_ID or not access_token:
        return {}

    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        resp = requests.post(
            f"{GA4_API}/properties/{GA4_PROPERTY_ID}:runReport",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "dateRanges": [{"startDate": start, "endDate": end}],
                "dimensions": [
                    {"name": "pagePath"},
                    {"name": "sessionDefaultChannelGroup"},
                    {"name": "deviceCategory"},
                    {"name": "country"},
                ],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "totalUsers"},
                    {"name": "screenPageViews"},
                    {"name": "averageSessionDuration"},
                    {"name": "bounceRate"},
                    {"name": "conversions"},
                ],
                "limit": 100,
            },
            timeout=30,
        )

        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  GA4 error: {e}", file=sys.stderr)

    return {}


def fetch_gsc_data(access_token: str, days: int = 28) -> dict:
    """Busca dados do Google Search Console."""

    if not access_token:
        return {}

    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    try:
        resp = requests.post(
            f"{GSC_API}/sites/{GSC_PROPERTY}/searchAnalytics/query",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "startDate": start,
                "endDate": end,
                "dimensions": ["query", "page", "date"],
                "rowLimit": 5000,
            },
            timeout=30,
        )

        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  GSC error: {e}", file=sys.stderr)

    return {}


def generate_setup_html() -> str:
    """Gera HTML de setup do Google Search Console + Analytics."""

    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Setup Google Analytics + Search Console — FraLib OS</title>
<style>
:root{--bg:#0a0714;--card:#12121a;--hover:#1c1c28;--border:rgba(147,51,234,0.12);--text:#f0f0f5;--muted:#8888a0;--dim:#44445a;--purple:#9333ea;--cyan:#00FFB3;--gold:#FFB800;--green:#22c55e}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:40px 24px;max-width:900px;margin:0 auto}
h1{font-family:'Press Start 2P',monospace;font-size:18px;color:var(--cyan);margin-bottom:8px;line-height:1.6}
h2{font-family:'Press Start 2P',monospace;font-size:13px;color:var(--purple);margin:32px 0 16px;letter-spacing:1px}
.subtitle{color:var(--muted);font-size:14px;margin-bottom:32px}
.step{background:var(--card);border:1px solid var(--border);padding:24px;margin-bottom:20px;position:relative}
.step-num{position:absolute;top:-12px;left:20px;background:var(--purple);color:#fff;font-family:'Press Start 2P',monospace;font-size:9px;padding:4px 12px;letter-spacing:1px}
.step h3{font-size:18px;font-weight:700;margin-bottom:8px;padding-left:60px}
.step p{color:var(--muted);margin:8px 0}
.code{background:#0a0714;border:1px solid var(--border);padding:16px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--cyan);overflow-x:auto;margin:12px 0}
.btn{display:inline-block;padding:10px 20px;background:#FACC15;color:#000;font-family:'Press Start 2P',monospace;font-size:10px;text-decoration:none;letter-spacing:1px;margin-right:8px;margin-top:8px}
.cta-checklist{list-style:none;padding:0;margin:16px 0}
.cta-checklist li{padding:8px 0;color:var(--muted);font-size:14px;padding-left:24px;position:relative}
.cta-checklist li::before{content:"☐";position:absolute;left:0;color:var(--cyan);font-size:18px}
.warning{background:rgba(245,158,11,0.08);border:1px solid var(--gold);padding:14px 18px;margin:16px 0;font-size:13px;color:var(--gold)}
.success{background:rgba(34,197,94,0.08);border:1px solid var(--green);padding:14px 18px;margin:16px 0;font-size:13px;color:var(--green)}
</style>
</head>
<body>

<h1>SETUP GOOGLE</h1>
<p class="subtitle">Configure Google Search Console + Google Analytics 4 para o FraLib OS</p>

<!-- GOOGLE SEARCH CONSOLE -->
<h2>🔍 Google Search Console</h2>

<div class="step">
  <span class="step-num">PASSO 1</span>
  <h3>Adicionar propriedade</h3>
  <p>Acesse <a href="https://search.google.com/search-console" target="_blank" style="color:var(--cyan)">Google Search Console</a> e adicione a URL:</p>
  <div class="code">https://seunegociofralib.site</div>
  <p>Escolha método de verificação: <strong>HTML tag</strong> ou <strong>DNS</strong></p>
</div>

<div class="step">
  <span class="step-num">PASSO 2</span>
  <h3>Verificar propriedade</h3>
  <p>Copie a meta tag de verificação e adicione ao <code>&lt;head&gt;</code> do site:</p>
  <div class="code">&lt;meta name="google-site-verification" content="SEU_CODIGO_AQUI" /&gt;</div>
  <p>Ou adicione um registro TXT no DNS:</p>
  <div class="code">TXT @ "google-site-verification=SEU_CODIGO"</div>
</div>

<div class="step">
  <span class="step-num">PASSO 3</span>
  <h3>Enviar sitemap</h3>
  <p>Após verificação, envie os sitemaps:</p>
  <div class="code">https://seunegociofralib.site/sitemap.xml
https://seunegociofralib.site/blog/sitemap.xml
https://seunegociofralib.site/blog/rss.xml</div>
  <p><strong>Importante:</strong> Atualize os sitemaps toda semana para indexar novos posts.</p>
</div>

<div class="step">
  <span class="step-num">PASSO 4</span>
  <h3>Solicitar indexação</h3>
  <p>Use "Inspeção de URL" no topo do Search Console para indexar páginas individuais rapidamente.</p>
  <p>Inspecione cada post novo após publicação.</p>
</div>

<div class="warning">
  ⚠ <strong>Tempo de indexação:</strong> Google pode levar 1-7 dias para indexar novas URLs. Continue publicando conteúdo de qualidade.
</div>

<!-- GOOGLE ANALYTICS 4 -->
<h2>📊 Google Analytics 4</h2>

<div class="step">
  <span class="step-num">PASSO 1</span>
  <h3>Criar propriedade GA4</h3>
  <p>Acesse <a href="https://analytics.google.com" target="_blank" style="color:var(--cyan)">Google Analytics</a> → Administrador → Criar propriedade</p>
  <ul class="cta-checklist">
    <li>Nome: FraLib OS</li>
    <li>URL: https://seunegociofralib.site</li>
    <li>Categoria: Negócios online</li>
    <li>Fuso: Brasil (GMT-3)</li>
  </ul>
</div>

<div class="step">
  <span class="step-num">PASSO 2</span>
  <h3>Instalar tag GA4</h3>
  <p>Copie o ID de medição (formato: G-XXXXXXXXXX) e adicione no <code>&lt;head&gt;</code> de todas as páginas:</p>
  <div class="code">&lt;!-- Google tag (gtag.js) --&gt;
&lt;script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"&gt;&lt;/script&gt;
&lt;script&gt;
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
&lt;/script&gt;</div>
</div>

<div class="step">
  <span class="step-num">PASSO 3</span>
  <h3>Configurar eventos de conversão</h3>
  <p>Eventos importantes para rastrear no FraLib:</p>
  <div class="code">// Quando usuário clica em "Testar grátis"
gtag('event', 'cta_click', {'location': 'hero'});

// Quando inicia trial
gtag('event', 'sign_up', {'method': 'trial'});

// Quando compra plano
gtag('event', 'purchase', {
  'transaction_id': 'XXX',
  'value': 97,
  'currency': 'BRL',
  'items': [{'id': 'starter', 'name': 'Starter', 'price': 97}]
});

// Quando completa onboarding
gtag('event', 'tutorial_complete');

// Quando gera primeiro site
gtag('event', 'site_generated', {'vertical': 'restaurant'});</div>
</div>

<div class="step">
  <span class="step-num">PASSO 4</span>
  <h3>Conectar API para SuperAdmin</h3>
  <p>Para puxar dados automaticamente, crie Service Account:</p>
  <ol>
    <li>Google Cloud Console → IAM & Admin → Service Accounts</li>
    <li>Criar conta: <code>ga4-fra-readonly@...</code></li>
    <li>Adicionar como Viewer na propriedade GA4</li>
    <li>Gerar chave JSON</li>
    <li>Adicionar ao <code>.env</code>:
      <div class="code">GA4_PROPERTY_ID=123456789
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/root/fralib/keys/ga4.json</div>
    </li>
  </ol>
</div>

<!-- ALERTAS -->
<h2>🚨 Alertas Configurados</h2>

<div class="success">
  <strong>Após configurar tudo, você terá:</strong>
  <ul style="margin-top:8px;padding-left:20px">
    <li>Tráfego orgânico em tempo real no SuperAdmin</li>
    <li>Ranking de palavras-chave atualizado diariamente</li>
    <li>Conversões rastreadas (signup, trial, purchase)</li>
    <li>Alertas de mudanças de ranking via webhook</li>
    <li>Relatórios automáticos de performance</li>
  </ul>
</div>

<h2>📈 Métricas para Acompanhar</h2>

<div class="code">
META 30 DIAS:
  • Tráfego orgânico: 100+ visitas/dia
  • Posts indexados: 100% (12/12)
  • Keywords top 10: 5+
  • CTR médio: > 3%
  • Conversão trial: > 15%
  • Bounce rate: < 60%

META 90 DIAS:
  • Tráfego orgânico: 1.000+ visitas/dia
  • Keywords top 10: 20+
  • Backlinks: 50+
  • Domain Authority: > 30
  • Conversão trial: > 25%
</div>

</body>
</html>"""


def render_dashboard(ga4_data: dict, gsc_data: dict) -> str:
    """Renderiza dashboard com dados reais."""

    # Parse GA4
    sessions = 0
    users = 0
    pageviews = 0
    avg_duration = 0
    bounce_rate = 0
    conversions = 0

    if ga4_data and "rows" in ga4_data:
        for row in ga4_data["rows"]:
            metrics = row.get("metricValues", [])
            sessions += int(metrics[0].get("value", 0))
            users += int(metrics[1].get("value", 0))
            pageviews += int(metrics[2].get("value", 0))
            avg_duration = float(metrics[3].get("value", 0))
            bounce_rate = float(metrics[4].get("value", 0)) * 100
            conversions += int(metrics[5].get("value", 0))

    # Parse GSC
    impressions = 0
    clicks = 0
    top_queries = []

    if gsc_data and "rows" in gsc_data:
        for row in gsc_data["rows"][:50]:
            clicks += int(row.get("clicks", 0))
            impressions += int(row.get("impressions", 0))
            if row.get("keys"):
                top_queries.append({
                    "query": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                })

    ctr = (clicks / impressions * 100) if impressions > 0 else 0

    queries_rows = "\n".join([
        f"""
        <tr>
          <td><strong>{q['query']}</strong></td>
          <td>{q['impressions']:,}</td>
          <td>{q['clicks']:,}</td>
          <td>{q['ctr']}%</td>
          <td><span class="pos pos-{'top' if q['position'] <= 10 else 'mid' if q['position'] <= 30 else 'low'}">{q['position']}</span></td>
        </tr>"""
        for q in sorted(top_queries, key=lambda x: x['clicks'], reverse=True)[:20]
    ])

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tráfego Real — FraLib OS</title>
<style>
:root{{--bg:#0a0714;--card:#12121a;--hover:#1c1c28;--border:rgba(147,51,234,0.12);--text:#f0f0f5;--muted:#8888a0;--dim:#44445a;--purple:#9333ea;--cyan:#00FFB3;--gold:#FFB800;--green:#22c55e}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:40px 24px;max-width:1200px;margin:0 auto}}
h1{{font-family:'Press Start 2P',monospace;font-size:18px;color:var(--cyan);margin-bottom:8px;line-height:1.6}}
h2{{font-family:'Press Start 2P',monospace;font-size:12px;color:var(--purple);margin:32px 0 16px;letter-spacing:1px}}
.subtitle{{color:var(--muted);font-size:14px;margin-bottom:32px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:32px}}
.stat{{background:var(--card);border:1px solid var(--border);padding:16px}}
.stat-lbl{{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;font-family:'JetBrains Mono',monospace;margin-bottom:6px}}
.stat-val{{font-family:'Press Start 2P',monospace;font-size:20px;color:var(--cyan)}}
.section{{background:var(--card);border:1px solid var(--border);padding:24px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border)}}
th{{font-size:10px;color:var(--dim);text-transform:uppercase;font-family:'JetBrains Mono',monospace;font-weight:500;letter-spacing:.5px}}
.pos{{display:inline-block;padding:2px 8px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;min-width:36px;text-align:center}}
.pos-top{{background:rgba(34,197,94,0.15);color:var(--green)}}
.pos-mid{{background:rgba(245,158,11,0.15);color:var(--gold)}}
.pos-low{{background:rgba(239,68,68,0.15);color:#ef4444}}
</style>
</head>
<body>

<h1>📊 TRÁFEGO REAL</h1>
<p class="subtitle">Google Analytics 4 + Search Console — últimos 7 dias</p>

<div class="stats">
  <div class="stat">
    <div class="stat-lbl">SESSÕES</div>
    <div class="stat-val">{sessions:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">USUÁRIOS</div>
    <div class="stat-val">{users:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">PAGEVIEWS</div>
    <div class="stat-val">{pageviews:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">BOUNCE</div>
    <div class="stat-val">{bounce_rate:.1f}%</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">CONVERSÕES</div>
    <div class="stat-val">{conversions:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">IMPRESSÕES GSC</div>
    <div class="stat-val">{impressions:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">CLICS GSC</div>
    <div class="stat-val">{clicks:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">CTR GSC</div>
    <div class="stat-val">{ctr:.1f}%</div>
  </div>
</div>

<div class="section">
  <h2>Top Keywords (Google Search)</h2>
  <table>
    <thead>
      <tr>
        <th>Query</th>
        <th>Impressões</th>
        <th>Clicks</th>
        <th>CTR</th>
        <th>Posição</th>
      </tr>
    </thead>
    <tbody>
      {queries_rows if queries_rows else '<tr><td colspan="5" style="text-align:center;color:var(--muted)">Conecte Google Search Console para ver dados</td></tr>'}
    </tbody>
  </table>
</div>

</body>
</html>"""


def main() -> int:
    """Gera dashboard de tráfego."""

    print(f"[{datetime.now()}] Gerando dashboard de tráfego...")

    access_token = os.environ.get("GOOGLE_SERVICE_ACCOUNT_TOKEN", "")

    # Busca dados
    ga4_data = fetch_ga4_data(access_token) if access_token else {}
    gsc_data = fetch_gsc_data(access_token) if access_token else {}

    # Gera HTML
    html = render_dashboard(ga4_data, gsc_data)
    output = BLOG_DIR / "traffic-dashboard.html"
    output.write_text(html, encoding="utf-8")
    print(f"  [OK] Dashboard: {output}")

    # Gera setup
    setup = generate_setup_html()
    setup_file = BLOG_DIR / "google-setup.html"
    setup_file.write_text(setup, encoding="utf-8")
    print(f"  [OK] Setup guide: {setup_file}")

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
