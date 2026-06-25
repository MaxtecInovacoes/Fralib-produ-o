"""Script Playwright para análise de landing pages top."""

import re
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def analyze_landing_page(page, url, name):
    """Analyze a landing page and capture key elements."""
    print(f"[{name}] Navegando para {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    # Screenshots
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    try:
        page.screenshot(path=screenshots_dir / f"{name}_full.png", full_page=True)
    except Exception:
        pass

    analysis = {
        "name": name,
        "url": url,
        "headline": None,
        "subheadline": None,
        "ctas": [],
        "pricing_position": None,
        "nav_ctas": [],
    }

    # Headline
    try:
        h1 = page.locator("h1").first
        if h1.count() > 0:
            analysis["headline"] = h1.inner_text().strip()[:200]
    except Exception:
        pass

    # Subheadline
    try:
        h2 = page.locator("h2").first
        if h2.count() > 0:
            analysis["subheadline"] = h2.inner_text().strip()[:200]
    except Exception:
        pass

    # CTAs (buttons + anchor links with action text)
    cta_pattern = re.compile(
        r"get started|sign up|deploy|start free|try free|book demo|contact sales|talk to sales|comecar|assinar|testar gratis",
        re.IGNORECASE,
    )
    try:
        buttons = page.locator("a, button").filter(has_text=cta_pattern)
        for i in range(min(buttons.count(), 8)):
            btn = buttons.nth(i)
            try:
                box = btn.bounding_box()
                text = btn.inner_text().strip()[:80]
                if text:
                    analysis["ctas"].append({
                        "text": text,
                        "y_position": box["y"] if box else None,
                        "x_position": box["x"] if box else None,
                        "visible": btn.is_visible(),
                    })
            except Exception:
                continue
    except Exception:
        pass

    # Pricing link position
    try:
        pricing_link = page.locator("a").filter(has_text=re.compile(r"pricing|plans|planos|prices", re.IGNORECASE)).first
        if pricing_link.count() > 0:
            box = pricing_link.bounding_box()
            analysis["pricing_position"] = {
                "text": pricing_link.inner_text().strip()[:50],
                "in_nav": box["y"] < 100 if box else None,
                "in_body": box["y"] >= 100 if box else None,
            }
    except Exception:
        pass

    # Nav CTAs (top right area)
    try:
        nav_buttons = page.locator("nav a, nav button, header a, header button").filter(
            has_text=cta_pattern
        )
        for i in range(min(nav_buttons.count(), 4)):
            btn = nav_buttons.nth(i)
            try:
                box = btn.bounding_box()
                text = btn.inner_text().strip()[:50]
                if text:
                    analysis["nav_ctas"].append({
                        "text": text,
                        "x": box["x"] if box else None,
                        "y": box["y"] if box else None,
                    })
            except Exception:
                continue
    except Exception:
        pass

    print(f"[{name}] Headline: {analysis['headline']!r}")
    print(f"[{name}] CTAs: {len(analysis['ctas'])} | Nav CTAs: {len(analysis['nav_ctas'])}")
    print(f"[{name}] Pricing: {analysis['pricing_position']}")
    return analysis


def main():
    pages = [
        ("linear", "https://linear.app"),
        ("vercel", "https://vercel.com"),
        ("framer", "https://www.framer.com"),
        ("cal", "https://www.cal.com"),
        ("stripe", "https://www.stripe.com"),
        ("supabase", "https://supabase.com"),
    ]

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        for name, url in pages:
            try:
                result = analyze_landing_page(page, url, name)
                results.append(result)
            except Exception as e:
                print(f"[{name}] ERRO: {e}")

        browser.close()

    with open("landing_pages_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nAnalisadas {len(results)} paginas. Screenshots em 'screenshots/'")
    print("Analise salva em 'landing_pages_analysis.json'")


if __name__ == "__main__":
    main()
