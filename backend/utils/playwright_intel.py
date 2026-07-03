"""
Inteligencia de mercado LOCAL (substitui Jina).

Usa Playwright/Chromium que JA ESTA RODANDO no worker
(chrome-headless-shell) pra fazer scraping Google Search sem
custo de API externa.

DECISAO 2026-07-03: Playwright eh o entry point PRINCIPAL.
Jina foi REMOVIDO do sistema (usuario nao quer mais).

Vantagens:
- $0 de custo (sem API key, sem saldo)
- Mesma maquina (sem latencia de rede)
- Cache 48h - segunda chamada instant
- Sem dependencia externa

Quando falha, falha fechado (sem fallback). Erro claro
no log pra voce saber que precisa investigar.
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import re
from typing import List, Dict, Optional


ENABLED = os.getenv("PLAYWRIGHT_INTEL_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
TIMEOUT = int(os.getenv("PLAYWRIGHT_INTEL_TIMEOUT", "20"))
MAX_URLS = int(os.getenv("PLAYWRIGHT_INTEL_MAX_URLS", "2"))
CACHE_TTL = 48 * 3600  # 48 horas
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agents",
    "jina_cache",  # mesmo dir pra nao criar pasta nova
)

EXCLUIR_DOMINIOS = [
    "google", "facebook", "instagram", "youtube", "linkedin", "twitter",
    "maps.google", "play.google", "support.google", "accounts.google",
    "smartfit", "bodytech", "bluefit", "mcdonalds", "starbucks",
    "yelp", "tripadvisor", "ifood", "rappi", "reclameaqui",
    "guiamais", "apontador", "telelistas", "solutudo",
]


def _cache_path(scope: str, nicho: str, cidade: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.md5(
        (scope + "::" + nicho.lower() + "::" + cidade.lower() + "::v3").encode()
    ).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"intel_{key}.json")


def _normalizar_nicho(nicho: str) -> str:
    """Normaliza nicho pra chave canonica (mesma logica que Jina usava)."""
    raw = (nicho or "").strip().lower()
    compact = re.sub(r"\s+", " ", raw)
    ascii_key = (
        compact.replace("á", "a").replace("à", "a").replace("â", "a").replace("ã", "a")
        .replace("é", "e").replace("ê", "e").replace("í", "i")
        .replace("ó", "o").replace("ô", "o").replace("õ", "o")
        .replace("ú", "u").replace("ç", "c")
    )
    aliases = (
        ("nutricion", "nutricionista"),
        ("academia", "academia"),
        ("crossfit", "crossfit"),
        ("barbear", "barbearia"),
        ("salao", "salao"),
        ("beleza", "salao"),
        ("estetic", "estetica"),
        ("clinica", "clinica"),
        ("advog", "advocacia"),
        ("jurid", "advocacia"),
        ("restaurante", "restaurante"),
        ("pizzaria", "pizzaria"),
        ("hamburg", "hamburgueria"),
        ("dent", "dentista"),
        ("odont", "dentista"),
        ("pet", "pet"),
        ("pilates", "pilates"),
        ("contabil", "contabilidade"),
        ("imobili", "imobiliaria"),
        ("escola", "escola"),
        ("mecanic", "mecanica"),
    )
    for needle, canonical in aliases:
        if needle in ascii_key:
            return canonical
    return compact.rstrip("s") or "negocio local"


def _buscar_google_playwright(nicho: str, cidade: str) -> List[str]:
    """Busca Google Search via Playwright/Chromium local. Retorna ate MAX_URLS URLs."""
    if not ENABLED:
        raise RuntimeError("Playwright intel DESABILITADO (PLAYWRIGHT_INTEL_ENABLED=0)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(f"Playwright nao instalado: {exc}")

    query = f"melhor {nicho} {cidade} site oficial"
    urls = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
            )
            page = context.new_page()
            search_url = f"https://www.google.com/search?q={query}&hl=pt-BR&num=10"
            page.goto(search_url, timeout=TIMEOUT * 1000, wait_until="domcontentloaded")
            links = page.locator("a[href]").all()
            for link in links[:40]:
                try:
                    href = link.get_attribute("href") or ""
                    if not href.startswith("http"):
                        continue
                    if any(ex in href.lower() for ex in EXCLUIR_DOMINIOS):
                        continue
                    if ".google." in href.lower():
                        continue
                    if href in urls:
                        continue
                    urls.append(href)
                    if len(urls) >= MAX_URLS:
                        break
                except Exception:
                    continue
            browser.close()
    except Exception as e:
        raise RuntimeError(f"Playwright search falhou: {e}")

    return urls


def _ler_url_playwright(url: str) -> Optional[str]:
    """Le URL via Playwright. Retorna texto limpo (sem scripts/styles)."""
    if not ENABLED:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, timeout=TIMEOUT * 1000, wait_until="domcontentloaded")
            text = page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script, style, noscript, iframe, svg');
                    scripts.forEach(s => s.remove());
                    return document.body ? document.body.innerText : '';
                }
            """)
            browser.close()
            return text[:5000] if text else None
    except Exception as e:
        print(f"[Playwright Intel] Erro lendo {url}: {e}")
        return None


def _analisar_com_llm(conteudo: str, nicho: str, cidade: str, nome_negocio: str) -> Optional[Dict]:
    """Usa Haiku pra extrair palavras-poder e padroes do conteudo."""
    try:
        from llm_direct import call_claude
    except Exception as e:
        print(f"[Playwright Intel] llm_direct nao disponivel: {e}")
        return None

    prompt = f"""Analise este site de {nicho} em {cidade} (concorrente de {nome_negocio}) e extraia APENAS este JSON:

{{
  "palavras_poder": ["termo1", "termo2", "termo3", "termo4", "termo5"],
  "frases_padrao": ["frase 1", "frase 2", "frase 3"],
  "servicos_comuns": ["servico 1", "servico 2", "servico 3"],
  "diferenciais_observados": ["diferencial 1", "diferencial 2"],
  "tom_de_voz": "formal|casual|jovem|premium",
  "publico_alvo": "descricao curta"
}}

Apenas o JSON, sem explicacoes. Responda em portugues.

CONTEUDO:
{conteudo[:3500]}"""

    try:
        from backend.agents.llm_agent_config import get_model_for_agent
        model = get_model_for_agent("intel_analyzer", default="haiku")
    except Exception:
        model = "haiku"

    try:
        response = call_claude(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=800,
            temperature=0.3,
        )
        text = response.get("text", "") if isinstance(response, dict) else str(response)
        # Limpa markdown se vier
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text).strip()
        # Extrai JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"[Playwright Intel] LLM analise falhou: {e}")
        return None


def _consolidar(resultados: List[Dict], nicho: str, cidade: str, nome_negocio: str) -> Dict:
    """Consolida resultados de multiplas URLs."""
    palavras_poder = []
    frases = []
    servicos = []
    diferenciais = []
    tons = []
    publicos = []

    for r in resultados:
        palavras_poder.extend(r.get("palavras_poder", []))
        frases.extend(r.get("frases_padrao", []))
        servicos.extend(r.get("servicos_comuns", []))
        diferenciais.extend(r.get("diferenciais_observados", []))
        if r.get("tom_de_voz"):
            tons.append(r["tom_de_voz"])
        if r.get("publico_alvo"):
            publicos.append(r["publico_alvo"])

    return {
        "palavras_poder": list(dict.fromkeys(palavras_poder))[:15],
        "frases_padrao": list(dict.fromkeys(frases))[:8],
        "servicos_comuns": list(dict.fromkeys(servicos))[:8],
        "diferenciais_observados": list(dict.fromkeys(diferenciais))[:5],
        "tom_de_voz_mercado": max(set(tons), key=tons.count) if tons else "casual",
        "publico_alvo_mercado": publicos[0] if publicos else "",
        "nicho": nicho,
        "cidade": cidade,
        "fonte_urls": [r.get("url_fonte") for r in resultados if r.get("url_fonte")],
    }


def buscar_inteligencia_mercado(
    nicho: str,
    cidade: str,
    nome_negocio: str,
    concorrentes_urls: list = None,
    tenant_id: int | str | None = None,
) -> Dict:
    """
    Entry point principal. Retorna dict estruturado de inteligencia de mercado.
    FAIL-CLOSED: se Playwright falhar, sobe RuntimeError (sem fallback).
    """
    nicho_original = nicho
    nicho = _normalizar_nicho(nicho)
    scope = str(tenant_id or "global").strip().lower()

    # Cache 48h
    cache_file = _cache_path(scope, nicho, cidade)
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < CACHE_TTL:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            print(f"[Playwright Intel] Cache HIT: {nicho} em {cidade}")
            return cached
        except Exception:
            pass

    print(f"[Playwright Intel] Buscando para {nicho} em {cidade} (Playwright local)")

    # URLs de prioridade
    urls_analisar = []
    if concorrentes_urls:
        urls_analisar = [u for u in concorrentes_urls[:MAX_URLS] if u and u.startswith("http")]

    # Se nao tem URLs de concorrentes, busca via Google local
    if not urls_analisar:
        urls_analisar = _buscar_google_playwright(nicho, cidade)

    if not urls_analisar:
        raise RuntimeError(
            f"Playwright Intel: nenhuma URL encontrada para {nicho_original} em {cidade}. "
            f"Google pode ter bloqueado."
        )

    # Ler e analisar cada URL
    resultados = []
    for url in urls_analisar[:MAX_URLS]:
        print(f"[Playwright Intel] Lendo: {url}")
        text = _ler_url_playwright(url)
        if text and len(text) > 200:
            analise = _analisar_com_llm(text, nicho, cidade, nome_negocio)
            if analise:
                analise["url_fonte"] = url
                resultados.append(analise)

    if not resultados:
        raise RuntimeError(
            f"Playwright Intel: nenhuma URL renderizou conteudo util para {nicho_original}"
        )

    intelligence = _consolidar(resultados, nicho, cidade, nome_negocio)

    # Salva cache
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(intelligence, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    print(
        f"[Playwright Intel] OK: {len(intelligence.get('palavras_poder', []))} palavras-poder, "
        f"{len(intelligence.get('servicos_comuns', []))} servicos"
    )
    return intelligence


def formatar_inteligencia_para_arquiteto(intel: Dict) -> str:
    """Formata dict de inteligencia em string para o Arquiteto usar."""
    if not intel:
        return ""
    partes = []
    if intel.get("palavras_poder"):
        partes.append("PALAVRAS-PODER DO MERCADO: " + ", ".join(intel["palavras_poder"]))
    if intel.get("frases_padrao"):
        partes.append("FRASES PADRAO: " + " | ".join(intel["frases_padrao"]))
    if intel.get("servicos_comuns"):
        partes.append("SERVICOS COMUNS: " + ", ".join(intel["servicos_comuns"]))
    if intel.get("diferenciais_observados"):
        partes.append("DIFERENCIAIS: " + ", ".join(intel["diferenciais_observados"]))
    if intel.get("tom_de_voz_mercado"):
        partes.append(f"TOM DE VOZ DO MERCADO: {intel['tom_de_voz_mercado']}")
    if intel.get("publico_alvo_mercado"):
        partes.append(f"PUBLICO-ALVO DO MERCADO: {intel['publico_alvo_mercado']}")
    return "\n".join(partes)