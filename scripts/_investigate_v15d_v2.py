"""Sprint 12.17: Investigar tela preta - captura visual + DOM."""
import asyncio
import sys
from pathlib import Path

HERMES_VENV = Path(r"C:/Users/JESUS TE AMA/AppData/Local/hermes/hermes-agent/venv")
sys.path.insert(0, str(HERMES_VENV / "Lib" / "site-packages"))

from playwright.async_api import async_playwright


async def main():
    site_url = "https://seunegociofralib.site/sites/2/barbearia-fio-nobre-v15h/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Capture network
        responses = []
        page.on("response", lambda r: responses.append((r.status, r.url[:100])))

        # Capture console + errors
        console = []
        errors = []
        page.on("console", lambda m: console.append((m.type, m.text[:200])))
        page.on("pageerror", lambda e: errors.append(str(e)[:300]))

        print(f"=== Navegando para {site_url}")
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=30000)
        print(f"HTTP: {response.status}")

        # Wait 1s and capture state
        await page.wait_for_timeout(1500)
        root_html = await page.evaluate("document.getElementById('root')?.outerHTML?.substring(0, 2000) || 'EMPTY'")
        print(f"\n[1.5s] Root innerHTML (first 2KB):")
        print(root_html)

        # Screenshot at 1.5s
        shot1 = Path("C:/fralib/.tmp/site_v15d_1500ms.png")
        await page.screenshot(path=str(shot1), full_page=True)

        # Wait 5s
        await page.wait_for_timeout(3500)
        root_html2 = await page.evaluate("document.getElementById('root')?.innerHTML?.length || 0")
        print(f"\n[5s] Root innerHTML length: {root_html2}")

        # Get all visible text
        all_text = await page.evaluate("document.body.innerText?.substring(0, 2000) || 'EMPTY'")
        print(f"\n[5s] All visible text:")
        print(all_text)

        # Screenshot at 5s
        shot2 = Path("C:/fralib/.tmp/site_v15d_5000ms.png")
        await page.screenshot(path=str(shot2), full_page=True)

        # Errors?
        print(f"\n=== Console messages: {len(console)}")
        for t, m in console[-10:]:
            print(f"  [{t}] {m}")
        print(f"\n=== Page errors: {len(errors)}")
        for e in errors[:5]:
            print(f"  {e}")
        print(f"\n=== Network responses: {len(responses)}")
        for status, url in responses:
            print(f"  [{status}] {url}")

        await browser.close()


asyncio.run(main())
