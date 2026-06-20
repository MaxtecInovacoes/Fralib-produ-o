#!/usr/bin/env python3
"""Enqueue and watch a controlled FraLib pipeline run on production.

This script is intentionally small: it does not create leads, does not call
Hunter directly and does not send WhatsApp by default. It only enqueues the
official ``pipeline_lead`` job for a lead that already belongs to the tenant.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (BACKEND, BACKEND / "core", BACKEND / "services"):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env")
except Exception:
    pass


CONFIRM_TOKEN = "RUN_CONTROLLED_PIPELINE"
FRANZ_ENV_TOKEN = "FRALIB_ALLOW_CONTROLLED_FRANZ"


class ControlledRunError(RuntimeError):
    pass


def build_payload(
    lead: dict[str, Any],
    *,
    run_id: str,
    skip_franz_outreach: bool = True,
    force_renewal: bool = True,
) -> dict[str, Any]:
    payload = {
        "segmento": lead.get("segmento") or "",
        "cidade": lead.get("cidade") or "",
        "quantidade": 1,
        "score_minimo": 0,
        "_lead_id_existente": str(lead["id"]),
        "_forcar_renovacao": bool(force_renewal),
        "_cold_run": bool(force_renewal),
        "_prompt_agent_flow": True,
        "_controlled_test": True,
        "_run_id": run_id,
    }
    if skip_franz_outreach:
        payload["_skip_franz_outreach"] = True
    return payload


def ensure_franz_allowed(allow_franz_outreach: bool, env: dict[str, str] | None = None) -> bool:
    env = env or os.environ
    if not allow_franz_outreach:
        return True
    if env.get(FRANZ_ENV_TOKEN) != "1":
        raise ControlledRunError(
            f"--allow-franz-outreach requires {FRANZ_ENV_TOKEN}=1; blocked to avoid WhatsApp by accident"
        )
    return False


def require_confirmation(confirm: str | None, *, dry_run: bool) -> None:
    if dry_run:
        return
    if confirm != CONFIRM_TOKEN:
        raise ControlledRunError(f"use --confirm {CONFIRM_TOKEN} to enqueue a production controlled run")


def _database_session():
    from database import SessionLocal

    return SessionLocal()


def _load_lead(db, tenant_id: int, lead_id: str) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, user_id, nome, segmento, cidade, status, site_url, url_site
            FROM leads
            WHERE id=:lead_id AND user_id=:tenant_id
            """
        ),
        {"lead_id": lead_id, "tenant_id": tenant_id},
    ).fetchone()
    if not row:
        raise ControlledRunError(f"lead {lead_id} not found for tenant {tenant_id}")
    return dict(row._mapping)


def _open_pipeline_count(db, tenant_id: int) -> int:
    return int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE tenant_id=:tenant_id
                  AND tipo IN ('pipeline_lead','pipeline_multiplos','pipeline_main')
                  AND status IN ('pending','running','failed_retriable')
                """
            ),
            {"tenant_id": tenant_id},
        ).scalar()
        or 0
    )


def enqueue_controlled_run(args: argparse.Namespace) -> dict[str, Any]:
    require_confirmation(args.confirm, dry_run=args.dry_run)
    skip_franz = ensure_franz_allowed(args.allow_franz_outreach)
    run_id = args.run_id or f"ctrl-{uuid.uuid4().hex[:12]}"

    db = _database_session()
    try:
        lead = _load_lead(db, args.tenant_id, args.lead_id)
        open_count = _open_pipeline_count(db, args.tenant_id)
        if open_count and not args.allow_existing_pipeline:
            raise ControlledRunError(
                f"tenant {args.tenant_id} already has {open_count} open pipeline job(s); "
                "use --allow-existing-pipeline only when intentionally testing queue contention"
            )
        payload = build_payload(
            lead,
            run_id=run_id,
            skip_franz_outreach=skip_franz,
            force_renewal=not args.no_force_renewal,
        )
        evidence = {
            "tenant_id": args.tenant_id,
            "lead": {
                "id": lead["id"],
                "nome": lead.get("nome"),
                "segmento": lead.get("segmento"),
                "cidade": lead.get("cidade"),
                "status": lead.get("status"),
                "site_url": lead.get("site_url") or lead.get("url_site"),
            },
            "payload": payload,
            "dry_run": bool(args.dry_run),
            "job_id": None,
        }
        if args.dry_run:
            return evidence

        import job_queue

        job_id = job_queue.enqueue(
            db,
            tipo="pipeline_lead",
            payload=payload,
            tenant_id=args.tenant_id,
            max_attempts=1,
            idempotency_key=f"controlled-pipeline-{args.tenant_id}-{args.lead_id}-{run_id}",
            priority=1,
            run_id=run_id,
        )
        if not job_id:
            raise ControlledRunError("job not enqueued because idempotency key already exists")
        evidence["job_id"] = job_id
        return evidence
    finally:
        db.close()


def _job_snapshot(db, job_id: int) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, tipo, tenant_id, status, attempts, max_attempts, last_phase,
                   last_error, run_id, criado_em, iniciado_em, concluido_em
            FROM jobs
            WHERE id=:job_id
            """
        ),
        {"job_id": job_id},
    ).fetchone()
    if not row:
        raise ControlledRunError(f"job {job_id} not found")
    return dict(row._mapping)


def wait_for_job(job_id: int, *, timeout_seconds: int, interval_seconds: int) -> int:
    deadline = time.monotonic() + timeout_seconds
    last_status = ""
    db = _database_session()
    try:
        while True:
            snap = _job_snapshot(db, job_id)
            status = str(snap.get("status") or "")
            phase = snap.get("last_phase") or "-"
            if status != last_status:
                print(json.dumps({"job_id": job_id, "status": status, "phase": phase}, default=str, ensure_ascii=False))
                last_status = status
            if status == "completed":
                print(json.dumps({"ok": True, "job": snap}, default=str, ensure_ascii=False, indent=2))
                return 0
            if status in {"failed_permanent", "failed_retriable"}:
                print(json.dumps({"ok": False, "job": snap}, default=str, ensure_ascii=False, indent=2))
                return 1
            if time.monotonic() >= deadline:
                print(json.dumps({"ok": False, "timeout": timeout_seconds, "job": snap}, default=str, ensure_ascii=False, indent=2))
                return 124
            time.sleep(interval_seconds)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="FraLib controlled production pipeline runner")
    parser.add_argument("--tenant-id", type=int, required=True)
    parser.add_argument("--lead-id", required=True)
    parser.add_argument("--confirm")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--allow-existing-pipeline", action="store_true")
    parser.add_argument("--allow-franz-outreach", action="store_true")
    parser.add_argument("--no-force-renewal", action="store_true")
    args = parser.parse_args()

    try:
        evidence = enqueue_controlled_run(args)
        print(json.dumps(evidence, default=str, ensure_ascii=False, indent=2))
        if args.wait and evidence.get("job_id"):
            return wait_for_job(
                int(evidence["job_id"]),
                timeout_seconds=max(30, args.timeout_seconds),
                interval_seconds=max(5, args.interval_seconds),
            )
        return 0
    except ControlledRunError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
