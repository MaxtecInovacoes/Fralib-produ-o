"""Dry-run first reconciliation for FraLib one-truth divergences."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "core"))


def _rows(conn, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {}).fetchall()]


def _sync_user_plan(conn, *, apply: bool) -> dict[str, Any]:
    rows = _rows(
        conn,
        """
        SELECT id, email, plano, plan
        FROM users
        WHERE COALESCE(plano, '') <> COALESCE(plan, '')
        ORDER BY id
        LIMIT 500
        """,
    )
    if apply and rows:
        conn.execute(
            text(
                """
                UPDATE users
                SET plan = plano, updated_at = COALESCE(updated_at, NOW())
                WHERE COALESCE(plano, '') <> COALESCE(plan, '')
                """
            )
        )
    return {"apply": apply, "count": len(rows), "rows": rows}


def _sync_lead_pipeline_stage(conn, *, apply: bool) -> dict[str, Any]:
    rows = _rows(
        conn,
        """
        SELECT id, user_id, nome, status, pipeline_stage
        FROM leads
        WHERE status='concluido'
          AND COALESCE(pipeline_stage, '') <> 'concluido'
        ORDER BY COALESCE(atualizado_em, criado_em) DESC
        LIMIT 500
        """,
    )
    if apply and rows:
        conn.execute(
            text(
                """
                UPDATE leads
                SET pipeline_stage='concluido', atualizado_em=NOW()
                WHERE status='concluido'
                  AND COALESCE(pipeline_stage, '') <> 'concluido'
                """
            )
        )
    return {"apply": apply, "count": len(rows), "rows": rows}


def run_reconcile(*, apply: bool, tenant_id: int | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "backend" / ".env")
    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine)
    report: dict[str, Any] = {"ok": True, "apply": bool(apply)}
    try:
        conn_ctx = engine.begin()
    except Exception as exc:
        return {
            "ok": False,
            "apply": bool(apply),
            "error": "database_unavailable",
            "detail": str(exc).splitlines()[0],
        }
    try:
        with conn_ctx as conn:
            report["users_plan_sync"] = _sync_user_plan(conn, apply=apply)
            report["leads_pipeline_stage_sync"] = _sync_lead_pipeline_stage(conn, apply=apply)
    except OperationalError as exc:
        return {
            "ok": False,
            "apply": bool(apply),
            "error": "database_unavailable",
            "detail": str(exc).splitlines()[0],
        }
    except Exception as exc:
        return {
            "ok": False,
            "apply": bool(apply),
            "error": "reconcile_failed",
            "detail": str(exc).splitlines()[0],
        }
    db = SessionLocal()
    try:
        from services import lead_supply_engine
        report["lead_inventory_locks"] = lead_supply_engine.reap_stale_inventory_locks(
            db,
            tenant_id=tenant_id,
            apply=apply,
            limit=500,
        )
    except OperationalError as exc:
        return {
            "ok": False,
            "apply": bool(apply),
            "error": "database_unavailable",
            "detail": str(exc).splitlines()[0],
        }
    finally:
        db.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile FraLib one-truth divergences")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    parser.add_argument("--tenant-id", type=int, default=None, help="Restrict inventory lock reaper to one tenant")
    args = parser.parse_args()
    report = run_reconcile(apply=args.apply, tenant_id=args.tenant_id)
    print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
