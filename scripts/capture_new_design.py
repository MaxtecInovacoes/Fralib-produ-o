#!/usr/bin/env python3
"""Script para capturar screenshots da nova landing2_v3.html e benchmark pages."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

screenshots_dir = Path("screenshots")
new_design_dir = screenshots_dir / "new_design"
benchmark_dir = screenshots_dir / "benchmark_landing_pages"

new_design_dir.mkdir(parents=True, exist_ok=True)
benchmark_dir.mkdir(parents=True, exist_ok=True)

pages_to_capture = [
    {
        "name": "landing2_v3_simple",
        "url": "file:///C:/fralib/frontend/landing2_v3_simple.html",
        "devices": ["desktop"],
        "full_page": True,
    },
    {"name": "linear", "url": "https://linear.app", "devices": ["desktop"], "full_page": False},
    {"name": "vercel", "url": "https://vercel.com", "devices": ["desktop"], "full_page": False},
    {"name": "framer", "url": "https://framer.com", "devices": ["desktop"], "full_page": False},
]


async def capture_screenshot(page, name: str, device: str, full_page: bool) -> Path:
    if device == "mobile":
        await page.set_viewport_size({"width": 375, "height": 812})
    else:
        await page.set_viewport_size({"width": 1280, "height": 720})

    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1000)

    target_dir = new_design_dir if name.startswith("landing2") else benchmark_dir
    filepath = target_dir / f"{name}_{device}.png"

    await page.screenshot(path=str(filepath), full_page=full_page, type="jpeg", quality=90)
    print(f"  Saved: {filepath}")
    return filepath


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for config in pages_to_capture:
                print(f"\nCapturing {config['name']}...")
                for device in config["devices"]:
                    page = await browser.new_page()
                    try:
                        await page.goto(config["url"], wait_until="networkidle")
                        try:
                            await page.click("text=Accept all", timeout=3000)
                        except Exception:
                            pass
                        await capture_screenshot(page, config["name"], device, config["full_page"])
                    except Exception as e:
                        print(f"  Error on {config['name']} {device}: {e}")
                    finally:
                        await page.close()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())