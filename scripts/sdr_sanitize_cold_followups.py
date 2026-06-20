"""Dry-run/apply cold follow-up cleanup for the SDR queue."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "core"))

from database import SessionLocal  # noqa: E402
from services.sdr_gateway import sanitize_cold_followups  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitize cold SDR follow-ups without outbound history.")
    parser.add_argument("--tenant-id", type=int, default=None, help="Optional tenant/user id scope.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = sanitize_cold_followups(db, args.tenant_id, apply=args.apply)
    finally:
        db.close()

    mode = "apply" if args.apply else "dry-run"
    print(
        f"sdr cold followups {mode}: matched={result['matched']} updated={result['updated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
