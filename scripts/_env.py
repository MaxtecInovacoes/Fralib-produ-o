"""Standard environment loading for FraLib scripts.

Canônico para B4 do plano DRY (codex/dry-refactor).

Substitui o padrão hardcoded 'load_dotenv(\"/root/fralib/.env\")' que
quebra em dev (Windows/macOS) e em qualquer path não-canônico.
"""
from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
    """Load .env from project root and backend/.env if present.

    Idempotent — safe to call multiple times.
    """
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "backend" / ".env")
