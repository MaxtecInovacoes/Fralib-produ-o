#!/usr/bin/env python3
"""
Reconcilia pagamentos Mercado Pago aprovados que nao chegaram via webhook.

Uso na VPS:
  python3 scripts/vps_reconcile_mercadopago_payments.py --hours 24 --dry-run
  python3 scripts/vps_reconcile_mercadopago_payments.py --hours 24 --apply
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "core"))
load_dotenv(ROOT / ".env")

from database import engine  # noqa: E402
from endpoints.credits_endpoints import (  # noqa: E402
    MERCADOPAGO_API_BASE,
    _mercadopago_headers,
    _parse_external_reference,
    _processar_evento_mercadopago,
)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _live_reconcile_allowed() -> bool:
    return os.getenv("FRALIB_ENV", "").strip().lower() == "prod"


def _search_recent_payments(hours: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    begin = end - timedelta(hours=hours)
    params = {
        "sort": "date_created",
        "criteria": "desc",
        "range": "date_created",
        "begin_date": _iso_z(begin),
        "end_date": _iso_z(end),
        "limit": 100,
    }
    response = requests.get(
        f"{MERCADOPAGO_API_BASE}/v1/payments/search",
        headers=_mercadopago_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("results") or []


def _load_fixture_payments(path: str) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if payload.get("id") or payload.get("payment_id"):
            payment = dict(payload)
            if "id" not in payment and payment.get("payment_id"):
                payment["id"] = payment["payment_id"]
            return [payment]
        return payload.get("results") or payload.get("payments") or []
    if isinstance(payload, list):
        return payload
    raise ValueError("fixture must be a list or object with results/payments")


def _already_processed(payment_id: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM mercadopago_events WHERE payment_id=:p AND processado=true LIMIT 1"),
            {"p": payment_id},
        ).fetchone()
    return bool(row)


def _record_reconcile_event(payment: dict, user_id: int | None, dry_run: bool) -> None:
    if dry_run:
        return
    payment_id = str(payment.get("id") or "")
    event_id = f"mp_reconcile_{payment_id}"
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO mercadopago_events (event_id, tipo, payment_id, processado, user_id, raw_payload, processado_em)
                VALUES (:e, 'manual_reconcile', :p, true, :u, :raw, NOW())
                ON CONFLICT (event_id) DO UPDATE
                SET processado=true, user_id=EXCLUDED.user_id, processado_em=NOW()
            """),
            {
                "e": event_id,
                "p": payment_id,
                "u": user_id,
                "raw": '{"source":"vps_reconcile_mercadopago_payments.py"}',
            },
        )
        conn.commit()


async def _run(args: argparse.Namespace) -> int:
    if args.fixture_json:
        if args.apply and not _live_reconcile_allowed():
            raise SystemExit("fixture --apply is blocked outside FRALIB_ENV=prod")
        payments = _load_fixture_payments(args.fixture_json)
    else:
        if not _live_reconcile_allowed():
            raise SystemExit(
                "Mercado Pago live reconcile is blocked outside FRALIB_ENV=prod; "
                "use --fixture-json for local dry-run harness checks."
            )
        payments = _search_recent_payments(args.hours)
    candidates = []
    for payment in payments:
        payment_id = str(payment.get("id") or "")
        status = (payment.get("status") or "").lower()
        external_reference = payment.get("external_reference") or ""
        user_id, plano = _parse_external_reference(external_reference)
        if status == "approved" and user_id and plano:
            candidates.append((payment, user_id, plano))

    print(f"pagamentos_encontrados={len(payments)} candidatos_fralib={len(candidates)} dry_run={args.dry_run}")
    applied = 0
    skipped = 0
    for payment, user_id, plano in candidates:
        payment_id = str(payment.get("id") or "")
        already_processed = False if args.fixture_json and args.dry_run else _already_processed(payment_id)
        if already_processed:
            print(f"skip ja_processado payment={payment_id} user={user_id} plano={plano}")
            skipped += 1
            continue
        print(f"{'would_apply' if args.dry_run else 'apply'} payment={payment_id} user={user_id} plano={plano}")
        if not args.dry_run:
            resolved_user_id = await _processar_evento_mercadopago(payment)
            _record_reconcile_event(payment, resolved_user_id, dry_run=False)
            applied += 1
    print(f"aplicados={applied} ignorados={skipped}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--fixture-json", default="", help="Local fixture for offline dry-run/harness checks")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
