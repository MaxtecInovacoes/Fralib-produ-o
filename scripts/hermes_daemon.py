"""Long-running Hermes watchdog daemon for PM2.

The daemon is deliberately conservative:
- every cycle records read-only diagnostics as append-only incidents;
- dry-run smoke canary runs only every N cycles;
- it can run only Guard-approved, allowlisted remediation playbooks.
"""

from __future__ import annotations

import os
import argparse
import subprocess
import sys
import time
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


INTERVAL_SECONDS = max(30, int(os.getenv("HERMES_WATCHDOG_INTERVAL_SECONDS", "300")))
CANARY_EVERY_CYCLES = max(1, int(os.getenv("HERMES_CANARY_EVERY_CYCLES", "12")))
SMOKE_TIMEOUT_SECONDS = max(60, int(os.getenv("HERMES_CANARY_TIMEOUT_SECONDS", "180")))
AUTO_REMEDIATE = os.getenv("HERMES_AUTOREMEDIATE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _log(message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{stamp}] [hermes] {message}", flush=True)


def _run_scan() -> int:
    from database import SessionLocal
    from services.hermes_watchdog import run_scan

    db = SessionLocal()
    try:
        result = run_scan(db, auto_remediate=AUTO_REMEDIATE)
        ids = result.get("recorded_incident_ids") or []
        remediation = result.get("remediation_results") or []
        _log(
            "scan ok "
            f"diagnostics={len(result.get('snapshot', {}).get('diagnostics', []))} "
            f"recorded={ids} remediation={remediation}"
        )
        scan_count = len(ids)
    finally:
        db.close()

    # ── Key healthcheck: detecta chave morta e auto-limpa / reprocessa ──
    try:
        from backend.services.key_healthcheck import run_healthcheck_cycle
        sys.path.insert(0, str(ROOT / "backend"))
        cycle = run_healthcheck_cycle()
        _log(
            "key_healthcheck "
            f"key_ok={cycle.get('key_ok')} "
            f"status={cycle.get('status_code')} "
            f"action={cycle.get('action')} "
            f"alerts_cleaned={cycle.get('alerts_cleaned', 0)} "
            f"jobs_reopened={cycle.get('jobs_reopened', 0)}"
        )
    except Exception as e:
        _log(f"key_healthcheck erro (nao bloqueia scan): {e}")

    return scan_count


def _run_canary() -> None:
    from database import SessionLocal
    from services.hermes_watchdog import record_incident

    cmd = [sys.executable, str(ROOT / "pipeline.py"), "smoke", "--dry-run"]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=SMOKE_TIMEOUT_SECONDS,
    )
    if result.returncode == 0:
        _log("canary ok")
        return

    evidence = {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    db = SessionLocal()
    try:
        incident_id = record_incident(
            db,
            {
                "severity": "SEV1",
                "incident_type": "canary_smoke_failed",
                "title": "Hermes scheduled canary smoke failed",
                "recommended_action": "Inspect smoke output, deploy hook and PM2 state before accepting new traffic.",
                "evidence": evidence,
            },
            source="hermes_daemon",
        )
        _log(f"canary failed incident_id={incident_id}")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes watchdog daemon")
    parser.add_argument("--once", action="store_true", help="Run one scan cycle and exit")
    parser.add_argument("--skip-canary", action="store_true", help="Do not run smoke canary in --once mode")
    args = parser.parse_args()

    if args.once:
        _run_scan()
        if not args.skip_canary:
            _run_canary()
        return 0

    _log(
        "starting "
        f"interval={INTERVAL_SECONDS}s "
        f"canary_every={CANARY_EVERY_CYCLES} cycles "
        f"auto_remediate={AUTO_REMEDIATE}"
    )
    cycle = 0
    while True:
        cycle += 1
        try:
            _run_scan()
            if cycle % CANARY_EVERY_CYCLES == 0:
                _run_canary()
        except Exception as exc:
            _log(f"cycle error: {exc}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
