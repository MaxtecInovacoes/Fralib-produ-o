"""
Google Local Scraper - Utilitários
"""
import asyncio
import os


def _env_int(name: str, default: int, min_value: int, max_value: int) -> int:
    from backend.utils.env_int import env_int  # — M3 DRY shim
    return env_int(name, default, min_value, max_value)


async def _close_quietly(resource, timeout: float = 2.0) -> None:
    if not resource:
        return
    try:
        await asyncio.wait_for(resource.close(), timeout=timeout)
    except Exception:
        pass


def _playwright_launch_args() -> list[str]:
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-features=Translate,BackForwardCache",
        "--no-default-browser-check",
        "--no-first-run",
        "--no-sandbox",
        "--no-zygote",
    ]
