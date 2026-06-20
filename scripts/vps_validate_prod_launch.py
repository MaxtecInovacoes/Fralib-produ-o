#!/usr/bin/env python3
"""Validate live production blockers before FraLib real sales."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _redis_ping() -> tuple[bool, str]:
    try:
        out = subprocess.check_output(["redis-cli", "ping"], text=True, stderr=subprocess.STDOUT, timeout=5)
        return out.strip() == "PONG", out.strip()
    except Exception as exc:
        return False, str(exc)


def _get_json(url: str) -> tuple[bool, dict | str]:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            data = response.read().decode("utf-8", errors="replace")
        return True, json.loads(data)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return False, str(exc)


def _local_base_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _check(name: str, ok: bool, detail: str, failures: list[str]) -> None:
    print(f"{'OK' if ok else 'FAIL'} {name}: {detail}")
    if not ok:
        failures.append(name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FraLib production sales blockers")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Local API URL on VPS")
    parser.add_argument("--allow-remote-read", action="store_true", help="Allow read-only checks against a remote URL")
    parser.add_argument("--smoke", action="store_true", help="Run python3 pipeline.py smoke --dry-run")
    args = parser.parse_args()

    if not args.allow_remote_read and not _local_base_url(args.base_url):
        print("Remote base-url blocked; use --allow-remote-read for explicit read-only remote validation")
        return 2

    values = _env()
    failures: list[str] = []

    _check("FRALIB_ENV", values.get("FRALIB_ENV") == "prod", values.get("FRALIB_ENV", "missing"), failures)
    _check("APP_URL", values.get("APP_URL", "").startswith("https://"), values.get("APP_URL", "missing"), failures)
    token = values.get("MERCADOPAGO_ACCESS_TOKEN", "")
    _check("MERCADOPAGO_ACCESS_TOKEN", token.startswith("APP_USR"), "set" if token else "missing", failures)
    secret = values.get("MERCADOPAGO_WEBHOOK_SECRET", "")
    _check("MERCADOPAGO_WEBHOOK_SECRET", len(secret) >= 32, "set" if secret else "missing", failures)
    redis_ok, redis_detail = _redis_ping()
    _check("Redis", redis_ok, redis_detail, failures)

    ok, version = _get_json(f"{args.base_url.rstrip('/')}/health")
    _check("api/version", ok and isinstance(version, dict) and version.get("status") == "ok", str(version), failures)

    ok, pricing = _get_json(f"{args.base_url.rstrip('/')}/api/credits/pricing")
    plans = pricing.get("plans", []) if isinstance(pricing, dict) else []
    plan_amounts = {item.get("plano"): item.get("valor") for item in plans if isinstance(item, dict)}
    pricing_ok = (
        ok
        and isinstance(pricing, dict)
        and pricing.get("provider") == "mercadopago"
        and pricing.get("payment_methods") == ["pix", "credit_card", "debit_card"]
        and plan_amounts.get("starter") == 97.0
        and plan_amounts.get("pro") == 197.0
        and plan_amounts.get("agency") == 497.0
    )
    _check("pricing", pricing_ok, str({"provider": pricing.get("provider") if isinstance(pricing, dict) else None, "plans": plan_amounts}), failures)

    if args.smoke:
        proc = subprocess.run([sys.executable, "pipeline.py", "smoke", "--dry-run"], cwd=ROOT)
        _check("smoke", proc.returncode == 0, f"exit={proc.returncode}", failures)

    if failures:
        print("status: BLOQUEADO PARA VENDA REAL")
        return 1
    print("status: LIBERADO TECNICAMENTE PARA COBRANCA REAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
