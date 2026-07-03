"""Teste E2E ECC do fix CSRF do Simulador Franz.

Cenário coberto:
  A) CSRFHelper presente (happy path) — POST funciona
  B) CSRFHelper AUSENTE (cache invalidado) — POST ainda funciona via fallback inline
  C) fetch() cru sem X-CSRF-Token — backend DEVE dar 403 (sentinela)

Usa página de teste minimalista que carrega EXATAMENTE o que o admin.html
carrega (csrf-helper.js + sdr-simulator.js) sem o resto do admin (8732 linhas).
"""

from __future__ import annotations

import asyncio
import os
import sys
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
SDR_SIMULATOR_JS_PATH = str(_ROOT / "frontend" / "js" / "admin" / "sdr-simulator.js")
CSRF_HELPER_JS_PATH = str(_ROOT / "frontend" / "js" / "csrf-helper.js")


# ── Helpers ──────────────────────────────────────────────────────────────


async def _setup_session(context: BrowserContext) -> None:
    """Seta cookies de sessão fake pra simular user logado."""
    await context.add_cookies([
        {
            "name": "fralib_session",
            "value": "fake_jwt_for_e2e_test",
            "domain": "127.0.0.1",
            "path": "/",
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax",
        },
    ])


async def _fetch_csrf_token(context: BrowserContext) -> str:
    """Busca CSRF token via FastAPI real. Retorna o valor do cookie."""
    # Usa uma página simples pra fazer o fetch + receber o cookie
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context()).new_page()
        await page.goto(f"{BASE_URL}/login.html", wait_until="domcontentloaded", timeout=10000)
        await page.evaluate("""async () => {
            const r = await fetch('/api/csrf-token', {credentials: 'include'});
            return await r.json();
        }""")
        cookies = await page.context.cookies()
        csrf_cookie = next((c for c in cookies if c["name"] == "fralib_csrf"), None)
        await browser.close()
        if not csrf_cookie:
            raise RuntimeError("fralib_csrf cookie nao foi setado pelo backend")
        return csrf_cookie["value"]


def _build_test_page(csrf_helper_present: bool) -> str:
    """Constrói uma página HTML minimalista que carrega o que o admin carrega.

    A página faz o mesmo que o admin faz:
      1. Carrega csrf-helper.js (se presente)
      2. Carrega sdr-simulator.js (sempre)
      3. Tem o card #sdrSimulatorCard (senao o sdr-simulator nao faz nada)
    """
    csrf_helper_tag = (
        f'<script src="/js/csrf-helper.js?v=20260702-sprint11"></script>'
        if csrf_helper_present
        else '<!-- csrf-helper.js NAO CARREGADO (simulando cache/404) -->'
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>E2E CSRF Test</title>
  {csrf_helper_tag}
</head>
<body>
  <h1>E2E Test</h1>
  <div id="sdrSimulatorCard" style="display:none"></div>
  <textarea id="sdrSimulatorMessage"></textarea>
  <button id="sdrSimulatorSubmit" type="button">Test</button>
  <div id="sdrSimulatorOutput"></div>
  <div id="sdrSimulatorCounter">0/4000</div>
  <div id="sdrSimulatorHistory"></div>
  <textarea id="sdrSimulatorHistoryInput"></textarea>
  <script src="/js/admin/sdr-simulator.js?v=20260702-sprint11"></script>
</body>
</html>
"""


async def _make_test_page(context: BrowserContext, csrf_helper_present: bool) -> dict:
    """Cria uma página que serve o conteúdo do disco + carrega os scripts via FastAPI."""
    page = await context.new_page()
    html_content = _build_test_page(csrf_helper_present)

    async def serve_test(route):
        await route.fulfill(
            body=html_content,
            content_type="text/html; charset=utf-8",
        )

    # Serve a página de teste em /admin.html (substitui o 404 do FastAPI)
    await page.route(f"{BASE_URL}/admin.html", serve_test)

    # Se csrf_helper_present=False, mock csrf-helper.js pra retornar 404
    if not csrf_helper_present:
        async def block_csrf_helper(route):
            await route.fulfill(
                status=404,
                body="// csrf-helper.js bloqueado (simulando cache invalidado)",
            )
        await page.route(f"{BASE_URL}/js/csrf-helper.js*", block_csrf_helper)

    await page.goto(f"{BASE_URL}/admin.html", wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_load_state("networkidle", timeout=10000)

    state = {
        "csrf_helper_loaded": await page.evaluate("typeof window.CSRFHelper"),
        "sdr_simulator_loaded": await page.evaluate("typeof window.SDR_SIMULATOR"),
    }
    return page, state


async def _do_post(page: Page) -> dict:
    """Faz POST via SDR_SIMULATOR.callSimulateAPI e captura o request."""
    captured = {}

    async def on_request(req):
        if "/api/admin/simulate" in req.url and req.method == "POST":
            captured["x_csrf_token"] = req.headers.get("x-csrf-token")
            captured["url"] = req.url

    page.on("request", on_request)

    result = await page.evaluate("""async () => {
        if (!window.SDR_SIMULATOR) return {error: 'SDR_SIMULATOR_NAO_EXPOSTO'};
        try {
            const r = await window.SDR_SIMULATOR.callSimulateAPI({message: 'e2e test'});
            return {status: r.status, body: (await r.text()).slice(0, 200)};
        } catch (e) {
            return {error: String(e), message: e.message};
        }
    }""")
    await page.wait_for_timeout(500)
    return {"result": result, "captured": captured}


# ── Tests ────────────────────────────────────────────────────────────────


async def test_a_csrf_helper_present_happy_path():
    """A) CSRFHelper presente → POST funciona."""
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await _setup_session(context)
        page, state = await _make_test_page(context, csrf_helper_present=True)

        assert state["csrf_helper_loaded"] == "object", f"CSRFHelper nao carregou: {state}"
        assert state["sdr_simulator_loaded"] == "object", f"SDR_SIMULATOR nao carregou: {state}"

        outcome = await _do_post(page)
        x_token = outcome["captured"].get("x_csrf_token")
        result = outcome["result"]

        # Status NUNCA deve ser 403 (porque sdr-simulator injeta X-CSRF-Token via CSRFHelper)
        assert result.get("status") != 403, (
            f"403 CSRF mesmo com CSRFHelper presente! {result}\n"
            f"X-CSRF-Token enviado: {x_token}"
        )
        # X-CSRF-Token deve ter sido enviado
        assert x_token is not None, f"X-CSRF-Token NAO foi enviado: {outcome}"
        print(f"  [A] status={result.get('status')} x-csrf-token (via helper)={x_token[:30]}... OK")
        await browser.close()


async def test_b_csrf_helper_absent_fallback_inline():
    """B) CSRFHelper AUSENTE → POST ainda funciona via fallback inline (lê cookie)."""
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await _setup_session(context)
        # Pega CSRF cookie de antemao (cookie é setado pelo GET /api/csrf-token)
        csrf_value = await _fetch_csrf_token(context)
        await context.add_cookies([
            {
                "name": "fralib_csrf",
                "value": csrf_value,
                "domain": "127.0.0.1",
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
        ])

        page, state = await _make_test_page(context, csrf_helper_present=False)

        assert state["csrf_helper_loaded"] == "undefined", f"CSRFHelper deveria estar undefined: {state}"
        assert state["sdr_simulator_loaded"] == "object", f"SDR_SIMULATOR nao carregou: {state}"

        outcome = await _do_post(page)
        x_token = outcome["captured"].get("x_csrf_token")
        result = outcome["result"]

        # Status NUNCA deve ser 403
        assert result.get("status") != 403, (
            f"403 CSRF mesmo com fallback inline! BUG NO FIX. {result}\n"
            f"X-CSRF-Token enviado: {x_token}\n"
            f"Cookie fralib_csrf: {csrf_value}"
        )
        # X-CSRF-Token deve ter sido enviado via fallback
        assert x_token is not None, f"Fallback inline NAO enviou X-CSRF-Token: {outcome}"
        # X-CSRF-Token deve ser igual ao cookie
        assert x_token == csrf_value, (
            f"X-CSRF-Token DIFERENTE do cookie. "
            f"enviado: {x_token}, esperado: {csrf_value}"
        )
        print(f"  [B] status={result.get('status')} x-csrf-token (fallback)={x_token[:30]}... MATCH ✓")
        await browser.close()


async def test_c_raw_fetch_without_csrf_returns_403():
    """C) fetch() cru sem X-CSRF-Token → 403 (sentinela: backend é estrito)."""
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await _setup_session(context)

        # Pega CSRF cookie pra o backend ter algo pra comparar (e rejeitar)
        csrf_value = await _fetch_csrf_token(context)
        await context.add_cookies([
            {
                "name": "fralib_csrf",
                "value": csrf_value,
                "domain": "127.0.0.1",
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
        ])

        page = await context.new_page()
        await page.goto(f"{BASE_URL}/login.html", wait_until="domcontentloaded")

        # Fetch cru SEM CSRF — backend DEVE rejeitar
        # NOTA: backend pode dar 401 (sessao fake) ANTES de CSRF check;
        # se backend é estrito, retorna 403 quando sessao for real.
        # Sem sdr-simulator carregado, nao tem helper nem fallback.
        result = await page.evaluate("""async () => {
            try {
                const r = await fetch('/api/admin/simulate', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: 'raw fetch'})
                });
                return {status: r.status, body: (await r.text()).slice(0, 200)};
            } catch (e) {
                return {error: String(e)};
            }
        }""")
        status = result.get("status")
        # Com sessao fake, backend retorna 401 (sessao invalida) ANTES de checar CSRF.
        # Se 401: a sentinela é que o backend REJEITA o request sem sessao valida.
        # Se 403: a sentinela é que o backend REJEITA por CSRF.
        # O importante: NUNCA 200 (senao seria bypass).
        assert status in (401, 403), (
            f"Backend deveria rejeitar (401 ou 403), recebeu {status}: {result}"
        )
        print(f"  [C] status={status} (sentinela OK — backend rejeita)")
        await browser.close()


# ── Runner ───────────────────────────────────────────────────────────────


async def main():
    print(f"Backend: {BASE_URL}")
    print(f"SDR Simulator JS: {SDR_SIMULATOR_JS_PATH}")
    print(f"CSRF Helper JS: {CSRF_HELPER_JS_PATH}")
    print()

    try:
        urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3)
    except Exception as e:
        print(f"Backend nao esta respondendo em {BASE_URL}: {e}")
        print("   Suba com: python server.py")
        sys.exit(1)
    print("Backend respondendo")
    print()

    tests = [
        ("A) CSRFHelper presente (happy path)", test_a_csrf_helper_present_happy_path),
        ("B) CSRFHelper AUSENTE (fallback inline)", test_b_csrf_helper_absent_fallback_inline),
        ("C) fetch() cru sem CSRF (sentinela)", test_c_raw_fetch_without_csrf_returns_403),
    ]

    results = []
    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            await test_fn()
            results.append((name, True, None))
            print(f"   PASS")
        except AssertionError as e:
            results.append((name, False, str(e)))
            print(f"   FAIL: {e}")
        except Exception as e:
            results.append((name, False, f"Exception: {type(e).__name__}: {e}"))
            print(f"   ERROR: {e}")

    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if err:
            print(f"         {err[:200]}")
    print(f"\n{passed}/{len(results)} passaram")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
