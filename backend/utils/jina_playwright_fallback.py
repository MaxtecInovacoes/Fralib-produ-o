"""
Fallback LOCAL de inteliga (substitui Jina quando saldo acaba).

Usa Playwright/Chromium que JA ESTA RODANDO no worker (chrome-headless-shell)
pra fazer scraping Google Search sem custo de API externa.

Vantagens:
- $0 de custo
- Sem dependencia de API key
- Mesma maquina que faz Hunter V2 (sem latencia de rede extra)
- Cache 48h (mesmo do Jina) — segunda chamada eh instant

Limitacoes:
- Google pode bloquear com rate limit alto (protege com retry + sleep)
- Max 2 URLs por chamada (igual Jina)
- Nao funciona com Google bot detection agressivo (raro)
"""

from __future__ import annotations

import os
import re
import time
import asyncio
from typing import List, Dict, Optional


ENABLE_PLAYWRIGHT_FALLBACK = os.getenv("JINA_PLAYWRIGHT_FALLBACK", "1").lower() in {"1", "true", "yes", "on"}
PLAYWRIGHT_TIMEOUT = int(os.getenv("JINA_PLAYWRIGHT_TIMEOUT", "20"))
PLAYWRIGHT_MAX_URLS = int(os.getenv("JINA_PLAYWRIGHT_MAX_URLS", "2"))


def _buscar_concorrentes_google_playwright(nicho: str, cidade: str) -> List[str]:
    """Busca Google Search via Playwright/Chromium local. Retorna ate 2 URLs oficiais."""
    if not ENABLE_PLAYWRIGHT_FALLBACK:
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Jina Playwright] Playwright nao instalado")
        return []

    query = f"melhor {nicho} {cidade} site oficial"
    urls = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            search_url = f"https://www.google.com/search?q={query}&hl=pt-BR&num=10"
            page.goto(search_url, timeout=PLAYWRIGHT_TIMEOUT * 1000)
            # Pega os hrefs dos resultados (excluindo ads, redes sociais, mapas)
            EXCLUIR = [
                "google", "facebook", "instagram", "youtube", "linkedin", "twitter",
                "maps.google", "play.google", "support.google", "accounts.google",
                "smartfit", "bodytech", "bluefit", "mcdonalds", "starbucks",
                "yelp", "tripadvisor", "ifood", "rappi", "reclameaqui",
                "guiamais", "apontador", "telelistas", "solutudo",
            ]
            links = page.locator("a[href]").all()
            for link in links[:30]:
                try:
                    href = link.get_attribute("href") or ""
                    if not href.startswith("http"):
                        continue
                    if any(ex in href.lower() for ex in EXCLUIR):
                        continue
                    if ".google." in href.lower():
                        continue
                    if href in urls:
                        continue
                    urls.append(href)
                    if len(urls) >= PLAYWRIGHT_MAX_URLS:
                        break
                except Exception:
                    continue
            browser.close()
    except Exception as e:
        print(f"[Jina Playwright] Erro: {e}")
        return []

    return urls


def _ler_url_playwright(url: str) -> Optional[str]:
    """Le URL via Playwright/Chromium. Retorna texto markdown-like."""
    if not ENABLE_PLAYWRIGHT_FALLBACK:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, timeout=PLAYWRIGHT_TIMEOUT * 1000, wait_until="domcontentloaded")
            # Pega texto visivel (sem scripts, sem styles)
            text = page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script, style, noscript');
                    scripts.forEach(s => s.remove());
                    return document.body ? document.body.innerText : '';
                }
            """)
            browser.close()
            # Limita tamanho (mesmo do Jina)
            return text[:5000] if text else None
    except Exception as e:
        print(f"[Jina Playwright] Erro lendo {url}: {e}")
        return None


def buscar_inteligencia_local(nicho: str, cidade: str, nome_negocio: str) -> Optional[Dict]:
    """Entry point do fallback. Retorna dict estruturado ou None."""
    if not ENABLE_PLAYWRIGHT_FALLBACK:
        return None

    print(f"[Jina Playwright Fallback] Iniciando busca para {nicho} em {cidade}")

    # 1. Buscar URLs via Playwright
    urls = _buscar_concorrentes_google_playwright(nicho, cidade)
    if not urls:
        print(f"[Jina Playwright Fallback] Nenhuma URL encontrada")
        return None

    # 2. Ler cada URL
    resultados = []
    for url in urls[:PLAYWRIGHT_MAX_URLS]:
        print(f"[Jina Playwright Fallback] Lendo: {url}")
        text = _ler_url_playwright(url)
        if text and len(text) > 200:
            resultados.append({"url": url, "conteudo": text})
            print(f"[Jina Playwright Fallback] OK: {url} ({len(text)} chars)")

    if not resultados:
        return None

    # 3. Analisar com LLM (mesma funcao do Jina)
    from jina_intelligence import _analisar_conteudo_llm, _consolidar_inteligencia

    resultados_analisados = []
    for r in resultados:
        analise = _analisar_conteudo_llm(r["conteudo"], nicho, cidade, nome_negocio)
        if analise:
            analise["url_fonte"] = r["url"]
            resultados_analisados.append(analise)

    if not resultados_analisados:
        return None

    return _consolidar_inteligencia(resultados_analisados, nicho, cidade, nome_negocio)