"""Site Screenshot Helper.

Captura screenshot do site gerado (hero) via Playwright para anexar
a mensagens WhatsApp. Solucao pro problema de "muitas pessoas nao
clicam em link" - o Franz manda o PRINT do site pronto + URL.

URL padrao dos sites: https://seunegociofralib.site/sites/{user_id}/{slug}
(ou similar). Configuravel via env APP_URL.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Diretorio onde salvamos screenshots
SCREENSHOT_DIR = Path("/tmp/fralib_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def build_site_url(user_id: int, slug: str, base_url: str = "") -> str:
    """Constroi URL do site do lead.

    Args:
        user_id: tenant id.
        slug: slug do site (ex: 'academia-4fitness').
        base_url: base da app (default: env APP_URL).

    Returns:
        URL completa (ex: https://seunegociofralib.site/sites/2/academia-4fitness/).
    """
    base = base_url or os.getenv("APP_URL") or os.getenv("FRALIB_PUBLIC_URL") or "https://seunegociofralib.site"
    return f"{base.rstrip('/')}/sites/{user_id}/{slug}/"


def capture_site_screenshot(url: str, lead_id: str = "", viewport_width: int = 1280, viewport_height: int = 720) -> Optional[str]:
    """Captura screenshot do site via Playwright.

    Args:
        url: URL completa do site.
        lead_id: ID do lead (usado pro nome do arquivo).
        viewport_width: largura do viewport.
        viewport_height: altura do viewport.

    Returns:
        Path do arquivo PNG salvo, ou None se falhar.
    """
    if not url or not url.startswith("http"):
        logger.warning(f"[screenshot] URL invalida: {url}")
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("[screenshot] Playwright nao instalado")
        return None

    filename = f"site_{lead_id or 'unknown'}_{int(__import__('time').time())}.png"
    filepath = SCREENSHOT_DIR / filename

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                ignore_https_errors=True,
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Espera 2s pra JS carregar (SPA)
            page.wait_for_timeout(2000)
            page.screenshot(path=str(filepath), full_page=False)
            browser.close()
        logger.info(f"[screenshot] Salvo: {filepath} ({filepath.stat().st_size} bytes)")
        return str(filepath)
    except Exception as e:
        logger.warning(f"[screenshot] Falha ao capturar {url}: {e}")
        return None


def get_site_url_from_memory(memory) -> str:
    """Extrai a URL do site do lead, com fallback para construcao por tenant.

    Args:
        memory: LeadMemory.

    Returns:
        URL completa do site. Vazio se nao conseguir construir.
    """
    url = getattr(memory, "site_url", None)
    if url and str(url).strip():
        return str(url).strip()
    # Fallback: tenta construir a partir do slug
    slug = getattr(memory, "site_slug", None) or getattr(memory, "slug", None)
    if not slug:
        # Fallback 2: tenta extrair do nome
        nome = getattr(memory, "nome", "") or ""
        if nome:
            slug = nome.lower().replace(" ", "-").replace("/", "-")
    user_id = getattr(memory, "user_id", 0) or 0
    if slug and user_id:
        return build_site_url(user_id, slug)
    return ""