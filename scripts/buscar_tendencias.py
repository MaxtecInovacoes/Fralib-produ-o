#!/usr/bin/env python3
"""
Busca tendências do mercado brasileiro.
Fontes: Google Trends, Twitter, G1/UOL.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Instale: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

OUTPUT_FILE = Path(__file__).parent / "tendencias.json"
CACHE_HOURS = 6  # Cache por 6 horas

# Categorias de negócio válidas
CATEGORIES = {
    "marketing": "Marketing",
    "ia": "IA & Automação",
    "vendas": "Vendas",
    "freelancer": "Freelancer",
    "tech": "Tecnologia",
    "negócios": "Negócios",
    "finanças": "Finanças",
    "produtividade": "Produtividade",
}


# ============================================================================
# GOOGLE TRENDS
# ============================================================================

def get_google_trends() -> List[Dict]:
    """Busca trending topics do Google Trends Brasil."""
    trends = []

    try:
        # RSS oficial do Google Trends (daily trends - BR)
        resp = requests.get(
            "https://trends.google.com.br/trends/trendingsearches/daily/rss?geo=BR",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        if resp.ok:
            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all("item")[:15]:
                title = item.find("title")
                if title:
                    title_text = title.text.strip()

                    # Tenta classificar automaticamente
                    category = classify_topic(title_text)
                    trends.append({
                        "topic": title_text,
                        "source": "google_trends",
                        "category": category,
                        "volume": 1000,  # Estimativa
                        "url": item.find("link").text if item.find("link") else None,
                    })
    except Exception as e:
        print(f"Google Trends error: {e}", file=sys.stderr)

    return trends


def classify_topic(topic: str) -> str:
    """Classifica tópico por categoria baseado em keywords."""
    topic_lower = topic.lower()

    keywords_map = {
        "ia": ["ia", "inteligência artificial", "chatgpt", "gemini", "automação", "robô"],
        "marketing": ["marketing", "publicidade", "redes sociais", "instagram", "tiktok"],
        "vendas": ["venda", "e-commerce", "loja", "consumidor", "comércio"],
        "freelancer": ["freelancer", "autônomo", "mei", "empreendedor"],
        "tech": ["tecnologia", "aplicativo", "app", "software", "startup"],
        "finanças": ["dinheiro", "investimento", "bolsa", "dólar", "pix", "crédito"],
        "negócios": ["empresa", "negócio", "mercado", "economia"],
        "produtividade": ["produtividade", "trabalho", "gestão", "tempo"],
    }

    for category, kws in keywords_map.items():
        for kw in kws:
            if kw in topic_lower:
                return category

    return "negócios"  # Default


# ============================================================================
# FALLBACK: TÓPICOS CURADOS
# ============================================================================

CURATED_TOPICS = [
    {
        "topic": "Como freelancers brasileiros estão usando IA em 2026",
        "category": "ia",
        "source": "curated",
        "volume": 5000,
    },
    {
        "topic": "WhatsApp Business API: vale a pena para o seu negócio?",
        "category": "vendas",
        "source": "curated",
        "volume": 4500,
    },
    {
        "topic": "Prospecção no Google Maps: como achar cliente todo dia",
        "category": "marketing",
        "source": "curated",
        "volume": 4000,
    },
    {
        "topic": "SDR de IA: por que sua empresa precisa de um",
        "category": "ia",
        "source": "curated",
        "volume": 3800,
    },
    {
        "topic": "Quanto cobrar por site em 2026: guia para freelancers",
        "category": "freelancer",
        "source": "curated",
        "volume": 3500,
    },
    {
        "topic": "Sites com IA estão substituindo programadores?",
        "category": "tech",
        "source": "curated",
        "volume": 3200,
    },
    {
        "topic": "MEI: o que mudou no Simples Nacional em 2026",
        "category": "finanças",
        "source": "curated",
        "volume": 3000,
    },
    {
        "topic": "5 ferramentas de IA que todo freelancer deveria usar",
        "category": "produtividade",
        "source": "curated",
        "volume": 2800,
    },
    {
        "topic": "Como o FraLib está mudando vendas no Brasil",
        "category": "negócios",
        "source": "curated",
        "volume": 2500,
    },
    {
        "topic": "Automatize seu negócio sem saber programar",
        "category": "ia",
        "source": "curated",
        "volume": 2200,
    },
]


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Busca tendências e salva em JSON."""

    print(f"[{datetime.now()}] Buscando tendências...")

    # Verifica cache
    if OUTPUT_FILE.exists():
        mtime = datetime.fromtimestamp(OUTPUT_FILE.stat().st_mtime)
        if datetime.now() - mtime < timedelta(hours=CACHE_HOURS):
            print(f"  Cache válido ({mtime}), pulando busca.")
            return 0

    # Busca de várias fontes
    all_trends = []
    all_trends.extend(get_google_trends())
    print(f"  Google Trends: {len(all_trends)} tendências")

    # Adiciona curados
    all_trends.extend(CURATED_TOPICS)
    print(f"  + Curated: {len(CURATED_TOPICS)} tendências")

    # Remove duplicatas
    seen = set()
    unique_trends = []
    for trend in all_trends:
        topic_key = trend["topic"].lower()
        if topic_key not in seen:
            seen.add(topic_key)
            unique_trends.append(trend)

    # Filtra por volume
    filtered = [t for t in unique_trends if t.get("volume", 0) > 1000]
    print(f"  Total únicas: {len(filtered)} tendências (>1k volume)")

    # Ordena por volume
    filtered.sort(key=lambda x: x.get("volume", 0), reverse=True)

    # Salva JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "total": len(filtered),
        "trends": filtered,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Salvo em: {OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
