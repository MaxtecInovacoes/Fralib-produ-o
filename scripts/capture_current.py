"""Captura screenshots do landing2 atual para comparacao."""

from playwright.sync_api import sync_playwright
from pathlib import Path


def capture_screenshots():
    """Capture full page screenshots of the current landing2."""
    screenshots_dir = Path("screenshots/before_redesign")
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Try multiple possible URLs
        urls_to_try = [
            "https://seunegociofralib.site/landing2",
            "https://seunegociofralib.site/",
            "http://localhost:8000/landing2.html",
        ]

        loaded = False
        for url in urls_to_try:
            try:
                print(f"Trying: {url}")
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if response and response.status < 400:
                    print(f"Loaded: {url}")
                    loaded = True
                    break
            except Exception as e:
                print(f"  Failed: {e}")

        if not loaded:
            print("Could not load landing2 from any URL")
            # Try local file
            local_path = Path("frontend/landing2.html").resolve()
            if local_path.exists():
                page.goto(f"file://{local_path}", wait_until="domcontentloaded")
                print(f"Loaded local file: {local_path}")
            else:
                print("No local file found")
                browser.close()
                return

        page.wait_for_timeout(3000)

        # Above the fold
        page.screenshot(path=screenshots_dir / "01_above_fold.png")
        print("Captured: 01_above_fold.png")

        # Scroll progressively and capture each section
        scroll_positions = [
            (0, "01_hero"),
            (800, "02_hero_bottom"),
            (1600, "03_social_proof"),
            (2400, "04_problema"),
            (3200, "05_como_funciona"),
            (4000, "06_exemplos"),
            (4800, "07_produto"),
            (5600, "08_funcionalidades"),
            (6400, "09_stack"),
            (7200, "10_cinco_fontes"),
            (8000, "11_para_quem"),
            (8800, "12_timeline"),
            (9600, "13_planos"),
            (10400, "14_quem_por_tras"),
            (11200, "15_faq"),
            (12000, "16_beta_form"),
            (12800, "17_video_demo"),
            (13600, "18_depoimentos"),
            (14400, "19_comparacao"),
            (15200, "20_cta_final"),
        ]

        for y, name in scroll_positions:
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(800)
            page.screenshot(path=screenshots_dir / f"{name}.png")
            print(f"Captured: {name}.png at y={y}")

        # Full page
        try:
            page.screenshot(path=screenshots_dir / "FULL_PAGE.png", full_page=True)
            print("Captured: FULL_PAGE.png")
        except Exception as e:
            print(f"Full page capture failed: {e}")

        browser.close()
        print(f"\nScreenshots saved in: {screenshots_dir}")


if __name__ == "__main__":
    capture_screenshots()