#!/usr/bin/env python3
"""Script para capturar screenshot da landing2 migrada."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

screenshots_dir = Path("screenshots/new_design")
screenshots_dir.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 720})
            await page.goto(
                "file:///C:/fralib/frontend/landing2.html", wait_until="networkidle"
            )
            await page.wait_for_timeout(1000)

            filepath = screenshots_dir / "landing2_migrated_desktop.png"
            await page.screenshot(
                path=str(filepath), full_page=True, type="jpeg", quality=90
            )
            print(f"Saved: {filepath}")

            # Mobile
            await page.set_viewport_size({"width": 375, "height": 812})
            await page.wait_for_timeout(500)
            filepath = screenshots_dir / "landing2_migrated_mobile.png"
            await page.screenshot(
                path=str(filepath), full_page=True, type="jpeg", quality=90
            )
            print(f"Saved: {filepath}")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())