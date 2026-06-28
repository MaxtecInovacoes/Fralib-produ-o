#!/usr/bin/env python3
"""
Monitor de rankeamento de palavras-chave.
Integra com Google Search Console API.
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("Instale: pip install requests", file=sys.stderr)
    sys.exit(1)


BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
SITE_URL = "https://seunegociofralib.site"

# Google Search Console API
GSC_API = "https://www.googleapis.com/webmasters/v3"
GSC_PROPERTY = "sc-domain:seunegociofralib.site"

# Palavras-chave alvo
TARGET_KEYWORDS = [
    # Primarias (alto volume)
    "fra lib", "fralib os", "fra lib os", "automao com ia",
    "ia para vendas", "sdr de ia", "site com ia", "whatsapp business api",
    "gerador de sites", "prospects no google maps", "marketing para freelancers",
    # Long tail (baixa competicao)
    "como automatizar vendas com ia", "como criar site sem programar",
    "como prospectar clientes no whatsapp", "ferramenta de automao para pmes",
    "fra lib vale a pena", "fra lib preo", "fra lib tutorial",
    # Marca
    "fra lib login", "fra blog", "fra lib brasil",
    # Categorias
    "sdr com ia funciona", "crm com ia", "automao de marketing",
    "chatbot para whatsapp", "como vender mais",
]


def fetch_gsc_data() -> Optional[Dict]:
    """Busca dados reais do Google Search Console."""

    access_token = os.environ.get("GOOGLE_SEARCH_CONSOLE_TOKEN")
    if not access_token:
        return None

    # Ultimos 28 dias
    end = datetime.now() - timedelta(days=3)
    start = end - timedelta(days=28)

    try:
        # Query search analytics
        resp = requests.post(
            f"{GSC_API}/sites/{GSC_PROPERTY}/searchAnalytics/query",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "startDate": start.strftime("%Y-%m-%d"),
                "endDate": end.strftime("%Y-%m-%d"),
                "dimensions": ["query", "page"],
                "rowLimit": 1000,
            },
            timeout=30,
        )

        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  GSC error: {e}", file=sys.stderr)

    return None


def get_keyword_position(keyword: str) -> Dict:
    """Simula/calcula posicao da keyword."""

    # Dados mockados para demonstracao
    # (substituir por dados reais do GSC)
    return {
        "keyword": keyword,
        "position": None,
        "impressions": 0,
        "clicks": 0,
        "ctr": 0,
        "change": 0,
        "page": None,
    }


def analyze_keyword_opportunities(gsc_data: Optional[Dict]) -> List[Dict]:
    """Analisa oportunidades de keywords."""

    opportunities = []

    if gsc_data and "rows" in gsc_data:
        # Dados reais
        for row in gsc_data["rows"][:30]:
            query = row["keys"][0]
            page = row["keys"][1] if len(row["keys"]) > 1 else ""
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0)
            position = row.get("position", 100)

            if impressions < 5:
                continue

            opportunities.append({
                "keyword": query,
                "page": page.replace(SITE_URL, ""),
                "impressions": impressions,
                "clicks": clicks,
                "ctr": round(ctr * 100, 2),
                "position": round(position, 1),
                "opportunity": "HIGH" if position < 20 and impressions > 100 else "MEDIUM" if position < 50 else "LOW",
            })
    else:
        # Fallback: monitora as keywords alvo
        for kw in TARGET_KEYWORDS[:20]:
            opp = get_keyword_position(kw)
            opp["opportunity"] = "UNKNOWN"
            opportunities.append(opp)

    return sorted(opportunities, key=lambda x: x.get("impressions", 0), reverse=True)


def generate_report(opportunities: List[Dict]) -> Dict:
    """Gera relatorio de rankeamento."""

    # Calcula metricas
    total_impressions = sum(o.get("impressions", 0) for o in opportunities)
    total_clicks = sum(o.get("clicks", 0) for o in opportunities)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_position = sum(o.get("position", 0) for o in opportunities if o.get("position")) / max(1, len([o for o in opportunities if o.get("position")]))

    # Top keywords
    top_keywords = sorted(opportunities, key=lambda x: x.get("clicks", 0), reverse=True)[:10]

    # Keywords em alta (top 20)
    top20_keywords = [o for o in opportunities if o.get("position") and o.get("position") <= 20]

    # Oportunidades
    quick_wins = [o for o in opportunities if 20 < (o.get("position") or 100) <= 30 and o.get("impressions", 0) > 50]

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_keywords_tracked": len(TARGET_KEYWORDS),
            "keywords_with_impressions": len([o for o in opportunities if o.get("impressions", 0) > 0]),
            "top_20_keywords": len(top20_keywords),
            "total_impressions_28d": total_impressions,
            "total_clicks_28d": total_clicks,
            "avg_ctr": round(avg_ctr, 2),
            "avg_position": round(avg_position, 1),
            "quick_wins_count": len(quick_wins),
        },
        "top_keywords": top_keywords,
        "top_20": top20_keywords,
        "quick_wins": quick_wins[:10],
        "opportunities": opportunities,
    }


def render_html_report(report: Dict) -> str:
    """Renderiza HTML do relatorio."""

    summary = report["summary"]

    keywords_rows = "\n".join([
        f"""
        <tr>
          <td><strong>{k['keyword']}</strong></td>
          <td><a href="{k['page']}" target="_blank" style="color:#00FFB3">{k['page'][:50]}</a></td>
          <td>{k['impressions']:,}</td>
          <td>{k['clicks']:,}</td>
          <td>{k['ctr']}%</td>
          <td><span class="pos pos-{'top' if k['position'] <= 10 else 'mid' if k['position'] <= 30 else 'low'}">{k['position']}</span></td>
          <td><span class="opp opp-{k['opportunity'].lower()}">{k['opportunity']}</span></td>
        </tr>"""
        for k in report["top_keywords"][:30]
    ])

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Monitor de Rankeamento — FraLib OS</title>
<meta name="robots" content="noindex, nofollow">
<style>
:root{{--bg:#0a0714;--card:#12121a;--hover:#1c1c28;--border:rgba(147,51,234,0.12);--border-md:rgba(147,51,234,0.25);--text:#f0f0f5;--muted:#8888a0;--dim:#44445a;--purple:#9333ea;--cyan:#00FFB3;--gold:#FFB800;--green:#22c55e;--red:#ef4444}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:40px 24px;max-width:1400px;margin:0 auto}}
h1{{font-family:'Press Start 2P',monospace;font-size:18px;color:var(--cyan);margin-bottom:8px;line-height:1.6}}
h2{{font-family:'Press Start 2P',monospace;font-size:12px;color:var(--purple);margin:32px 0 16px;letter-spacing:1px}}
.subtitle{{color:var(--muted);font-size:14px;margin-bottom:24px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:32px}}
.stat{{background:var(--card);border:1px solid var(--border);padding:16px}}
.stat-lbl{{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;font-family:'JetBrains Mono',monospace;margin-bottom:6px}}
.stat-val{{font-family:'Press Start 2P',monospace;font-size:20px;color:var(--cyan)}}
.stat-val.gold{{color:var(--gold)}}.stat-val.green{{color:var(--green)}}.stat-val.purple{{color:var(--purple)}}
.section{{background:var(--card);border:1px solid var(--border);padding:24px;margin-bottom:20px}}
.section-title{{font-family:'Press Start 2P',monospace;font-size:11px;margin-bottom:16px;letter-spacing:1px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border)}}
th{{font-size:10px;color:var(--dim);text-transform:uppercase;font-family:'JetBrains Mono',monospace;font-weight:500;letter-spacing:.5px}}
tr:hover td{{background:var(--hover)}}
.pos{{display:inline-block;padding:2px 8px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;min-width:36px;text-align:center}}
.pos-top{{background:rgba(34,197,94,0.15);color:var(--green)}}
.pos-mid{{background:rgba(245,158,11,0.15);color:var(--gold)}}
.pos-low{{background:rgba(239,68,68,0.15);color:var(--red)}}
.opp{{display:inline-block;padding:2px 8px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:.5px}}
.opp-high{{background:rgba(34,197,94,0.15);color:var(--green)}}
.opp-medium{{background:rgba(245,158,11,0.15);color:var(--gold)}}
.opp-low{{background:rgba(239,68,68,0.15);color:var(--red)}}
.opp-unknown{{background:rgba(68,68,90,0.2);color:var(--muted)}}
.btn{{display:inline-block;padding:8px 16px;background:var(--hover);border:1px solid var(--border-md);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;text-decoration:none;cursor:pointer}}
.btn:hover{{border-color:var(--cyan);color:var(--cyan)}}
.last-update{{color:var(--dim);font-size:11px;font-family:'JetBrains Mono',monospace}}
</style>
</head>
<body>

<h1>MONITOR DE RANKEAMENTO</h1>
<p class="subtitle">Acompanhamento de palavras-chave no Google Search Console</p>
<p class="last-update">Última atualização: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>

<div class="stats">
  <div class="stat">
    <div class="stat-lbl">KEYWORDS MONITORADAS</div>
    <div class="stat-val">{summary['total_keywords_tracked']}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">TOP 20</div>
    <div class="stat-val green">{summary['top_20_keywords']}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">IMPRESSÕES (28d)</div>
    <div class="stat-val gold">{summary['total_impressions_28d']:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">CLICS (28d)</div>
    <div class="stat-val green">{summary['total_clicks_28d']:,}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">CTR MÉDIO</div>
    <div class="stat-val purple">{summary['avg_ctr']}%</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">POSIÇÃO MÉDIA</div>
    <div class="stat-val">{summary['avg_position']}</div>
  </div>
  <div class="stat">
    <div class="stat-lbl">QUICK WINS</div>
    <div class="stat-val gold">{summary['quick_wins_count']}</div>
  </div>
</div>

<div class="section">
  <h2 class="section-title">Top Keywords por Cliques</h2>
  <table>
    <thead>
      <tr>
        <th>Keyword</th>
        <th>Página</th>
        <th>Impressões</th>
        <th>Clicks</th>
        <th>CTR</th>
        <th>Posição</th>
        <th>Oportunidade</th>
      </tr>
    </thead>
    <tbody>
      {keywords_rows}
    </tbody>
  </table>
</div>

</body>
</html>"""


def main() -> int:
    """Executa monitor de rankeamento."""

    print(f"[{datetime.now()}] Iniciando monitor de rankeamento...")

    # Busca dados do GSC
    gsc_data = fetch_gsc_data()
    if gsc_data:
        print(f"  [OK] Dados GSC: {len(gsc_data.get('rows', []))} keywords")
    else:
        print("  [INFO] GSC não conectado - usando modo demo")

    # Analisa oportunidades
    opportunities = analyze_keyword_opportunities(gsc_data)

    # Gera relatorio
    report = generate_report(opportunities)

    # Salva JSON
    json_file = BLOG_DIR / "rank-tracker.json"
    json_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [OK] {json_file}")

    # Gera HTML
    html = render_html_report(report)
    html_file = BLOG_DIR / "rank-tracker.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"  [OK] {html_file}")

    # Resumo
    summary = report["summary"]
    print(f"\n  RESUMO:")
    print(f"    Keywords monitoradas: {summary['total_keywords_tracked']}")
    print(f"    Top 20: {summary['top_20_keywords']}")
    print(f"    Impressões 28d: {summary['total_impressions_28d']:,}")
    print(f"    Clicks 28d: {summary['total_clicks_28d']:,}")
    print(f"    CTR médio: {summary['avg_ctr']}%")
    print(f"    Quick wins: {summary['quick_wins_count']}")

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
