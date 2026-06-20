"""Collect a Hermes operational snapshot from the database/runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (str(BACKEND), str(BACKEND / "core"), str(BACKEND / "services")):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env")
except Exception:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Hermes watchdog snapshot")
    parser.add_argument("--record", action="store_true", help="Append diagnostics as incidents")
    parser.add_argument("--json", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    from database import SessionLocal
    from services.hermes_watchdog import collect_snapshot, run_scan

    db = SessionLocal()
    try:
        result = run_scan(db) if args.record else collect_snapshot(db)
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
