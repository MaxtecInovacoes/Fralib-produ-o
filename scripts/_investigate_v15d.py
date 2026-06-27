"""Sprint 12.17: Investigar tela preta no site v15d com Playwright."""
import asyncio
import json
import sys
from pathlib import Path

# Path setup for hermes venv
HERMES_VENV = Path(r"C:/Users/JESUS TE AMA/AppData/Local/hermes/hermes-agent/venv")
sys.path.insert(0, str(HERMES_VENV / "Lib" / "site-packages"))

from playwright.async_api import async_playwright


async def investigate():
    """Investiga tela preta no site via Playwright."""
    site_url = "https://seunegociofralib.site/sites/2/barbearia-fio-nobre-v15d/"

    # 1. Capturar console messages
    console_messages = []
    page_errors = []
    request_failures = []
    response_status = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text,
        }))
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("requestfailed", lambda req: request_failures.append({
            "url": req.url,
            "failure": req.failure,
        }))
        page.on("response", lambda r: response_status.update({r.url: r.status}))

        print(f"[1] Navegando para {site_url}")
        try:
            response = await page.goto(site_url, wait_until="networkidle", timeout=30000)
            print(f"   HTTP status: {response.status if response else 'NO RESPONSE'}")
        except Exception as e:
            print(f"   Navigation error: {e}")
            return

        # 2. Aguardar React montar (5s)
        await page.wait_for_timeout(5000)

        # 3. Capturar screenshot
        screenshot_path = Path("C:/fralib/.tmp/site_v15d_screenshot.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"[2] Screenshot salvo: {screenshot_path}")

        # 4. Verificar se root tem conteúdo
        root_html = await page.evaluate("document.getElementById('root')?.innerHTML?.length || 0")
        body_html = await page.evaluate("document.body?.innerText?.length || 0")
        bg_color = await page.evaluate("getComputedStyle(document.body).backgroundColor")
        print(f"[3] Root innerHTML length: {root_html}")
        print(f"   Body innerText length: {body_html}")
        print(f"   Body background: {bg_color}")

        # 5. Verificar se há conteúdo visível
        visible_text = await page.evaluate("""
            (() => {
                const all = document.querySelectorAll('h1, h2, h3, p, button, a, nav, section, header');
                const visible = [];
                for (const el of all) {
                    const style = getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && el.innerText?.trim()) {
                        visible.push({
                            tag: el.tagName,
                            text: el.innerText.substring(0, 80),
                            color: style.color,
                            bg: style.backgroundColor,
                        });
                    }
                }
                return visible.slice(0, 20);
            })()
        """)
        print(f"[4] Elementos visíveis: {len(visible_text)}")
        for v in visible_text[:10]:
            print(f"   {v['tag']}: {v['text'][:60]}")

        # 6. Verificar CSS carregado
        css_loaded = await page.evaluate("""
            (() => {
                const sheets = Array.from(document.styleSheets);
                return sheets.map(s => ({
                    href: s.href,
                    rulesCount: (() => {
                        try { return s.cssRules?.length || 0; }
                        catch(e) { return 'CORS'; }
                    })()
                }));
            })()
        """)
        print(f"[5] Stylesheets carregadas: {len(css_loaded)}")
        for css in css_loaded:
            print(f"   {css['href'][-60:]}: {css['rulesCount']} rules")

        # 7. Checar erros
        print(f"\n[6] Console messages: {len(console_messages)}")
        for m in console_messages[-10:]:
            print(f"   [{m['type']}] {m['text'][:150]}")
        print(f"\n[7] Page errors: {len(page_errors)}")
        for e in page_errors[:5]:
            print(f"   {e[:200]}")
        print(f"\n[8] Request failures: {len(request_failures)}")
        for r in request_failures[:5]:
            print(f"   {r['url']}: {r['failure']}")

        await browser.close()

    # 8. Salvar relatório
    report = {
        "url": site_url,
        "root_html_length": root_html,
        "body_text_length": body_html,
        "bg_color": bg_color,
        "visible_elements": visible_text,
        "css_sheets": css_loaded,
        "console_messages": console_messages,
        "page_errors": page_errors,
        "request_failures": request_failures,
    }
    report_path = Path("C:/fralib/.tmp/site_v15d_report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[9] Report salvo: {report_path}")


if __name__ == "__main__":
    asyncio.run(investigate())
