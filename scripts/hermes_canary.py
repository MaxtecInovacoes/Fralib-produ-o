"""Hermes canary runner.

This script is safe for cron/PM2 scheduling. It runs the existing dry-run smoke
outside the request path and can append an incident if the canary fails.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
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


def _run_smoke() -> dict:
    cmd = [sys.executable, str(ROOT / "pipeline.py"), "smoke", "--dry-run"]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=int(os.getenv("HERMES_CANARY_TIMEOUT_SECONDS", "120")),
    )
    return {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def _record_failure(evidence: dict) -> int:
    from database import SessionLocal
    from services.hermes_watchdog import record_incident

    db = SessionLocal()
    try:
        return record_incident(
            db,
            {
                "severity": "SEV1",
                "incident_type": "canary_smoke_failed",
                "title": "Hermes canary smoke failed",
                "recommended_action": "Inspect smoke output, deploy hook and PM2 state before accepting new traffic.",
                "evidence": evidence,
            },
            source="hermes_canary",
        )
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes safe canary checks")
    parser.add_argument("--record", action="store_true", help="Append incident if canary fails")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    if args.record and os.getenv("FRALIB_ENV", "").strip().lower() != "prod":
        print("Hermes canary --record is blocked outside FRALIB_ENV=prod")
        return 2

    smoke = _run_smoke()
    output = {
        "ok": smoke["returncode"] == 0,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "smoke": smoke,
        "recorded_incident_id": None,
    }
    if not output["ok"] and args.record:
        output["recorded_incident_id"] = _record_failure(smoke)

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"ok={output['ok']} smoke_returncode={smoke['returncode']}")
        if output["recorded_incident_id"]:
            print(f"recorded_incident_id={output['recorded_incident_id']}")
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
