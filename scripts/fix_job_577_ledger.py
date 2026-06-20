#!/usr/bin/env python3
"""
Fix Job 577 Ledger - consolida llm_tokens_used e llm_cost_estimate do Job 577
a partir do llm_budget_ledger (fonte canonica).

Se jobs.llm_tokens_used ou jobs.llm_cost_estimate ja tiverem valor > 0,
usa COALESCE para nao sobrescrever.

Uso:
  python scripts/fix_job_577_ledger.py           # dry-run (default)
  python scripts/fix_job_577_ledger.py --apply    # aplica correcao
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "core"))

JOB_ID = 577


def _one(conn, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        rows = [dict(r._mapping) for r in conn.execute(text(sql), params or {}).fetchall()]
        return rows[0] if rows else {}
    except Exception as exc:
        return {"error": str(exc).splitlines()[0]}


def audit_job_577(conn):
    job = _one(
        conn,
        """SELECT id, run_id, tenant_id, status,
                  llm_tokens_used AS job_tokens,
                  llm_cost_estimate AS job_cost,
                  iniciado_em, concluido_em
           FROM jobs
           WHERE id = :job_id""",
        {"job_id": JOB_ID},
    )
    ledger = _one(
        conn,
        """SELECT
                  COUNT(*) AS total_calls,
                  COALESCE(SUM(input_tokens + output_tokens
                               + cache_read_tokens + cache_created_tokens), 0) AS ledger_tokens,
                  COALESCE(SUM(cost_usd), 0) AS ledger_cost
           FROM llm_budget_ledger
           WHERE job_id = :job_id
              OR run_id = (SELECT run_id FROM jobs WHERE id = :job_id)""",
        {"job_id": JOB_ID},
    )
    return {"job": job, "ledger": ledger}


def build_fix_plan(audit):
    job = audit.get("job", {})
    ledger = audit.get("ledger", {})

    if "error" in job:
        return {"action": "skip", "reason": job["error"]}

    if not job:
        return {"action": "skip", "reason": f"Job {JOB_ID} nao encontrado"}

    ledger_tokens = int(ledger.get("ledger_tokens") or 0)
    ledger_cost = float(ledger.get("ledger_cost") or 0.0)
    current_tokens = float(job.get("job_tokens") or 0)
    current_cost = float(job.get("job_cost") or 0.0)

    tokens_need_fix = ledger_tokens > 0 and (
        current_tokens == 0 or current_tokens != ledger_tokens
    )
    cost_need_fix = ledger_cost > 0 and (
        current_cost == 0.0 or abs(current_cost - ledger_cost) > 0.0001
    )

    if not tokens_need_fix and not cost_need_fix:
        return {
            "action": "noop",
            "job_id": JOB_ID,
            "job_tokens": current_tokens,
            "job_cost": current_cost,
            "ledger_tokens": ledger_tokens,
            "ledger_cost": ledger_cost,
        }

    return {
        "action": "update",
        "job_id": JOB_ID,
        "current_tokens": current_tokens,
        "current_cost": current_cost,
        "ledger_tokens": ledger_tokens,
        "ledger_cost": ledger_cost,
        "updates": {
            "llm_tokens_used": str(ledger_tokens),
            "llm_cost_estimate": f"{ledger_cost:.6f}",
        },
    }


def apply_fix(conn, plan):
    if plan.get("action") in ("skip", "noop"):
        return {"updated": 0, "errors": []}

    result = {"updated": 0, "errors": []}
    try:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET llm_tokens_used = COALESCE(NULLIF(llm_tokens_used, 0), :ledger_tokens),
                    llm_cost_estimate = COALESCE(NULLIF(llm_cost_estimate, 0.0), :ledger_cost)
                WHERE id = :job_id
                  AND (llm_tokens_used IS NULL OR llm_tokens_used = 0
                       OR llm_cost_estimate IS NULL OR llm_cost_estimate = 0.0)
                """
            ),
            {
                "ledger_tokens": plan["ledger_tokens"],
                "ledger_cost": plan["ledger_cost"],
                "job_id": JOB_ID,
            },
        )
        conn.commit()
        result["updated"] = 1
    except Exception as exc:
        result["errors"].append(str(exc))

    return result

def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Consolidar Job {JOB_ID} llm_tokens/llm_cost do ledger canonico"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Aplicar correcao. Sem esta flag roda em dry-run.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Saida JSON em vez de texto legivel.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "backend" / ".env")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL nao definido.", file=sys.stderr)
        return 1

    engine = create_engine(DATABASE_URL)
    try:
        conn_ctx = engine.connect()
    except Exception as exc:
        print(f"ERRO: Falha ao conectar ao DB: {exc}", file=sys.stderr)
        return 1

    with conn_ctx as conn:
        audit = audit_job_577(conn)
        plan = build_fix_plan(audit)

        if args.json:
            output = dict(plan)
            output["dry_run"] = not args.apply
            if args.apply and plan.get("action") == "update":
                output["apply_result"] = apply_fix(conn, plan)
            print(json.dumps(output, ensure_ascii=False, default=str, indent=2))
        else:
            action = plan.get("action", "unknown")
            mode = "DRY-RUN" if not args.apply else "APLICANDO"
            print(f"[fix_job_577_ledger] Modo: {mode} | Job {JOB_ID} | acao: {action}")

            if action == "skip":
                print(f"  Motivo: {plan.get('reason')}")
            elif action == "noop":
                print(
                    "  Sem diferenca: job_tokens=" + str(plan.get("job_tokens")) + " "
                    "job_cost=" + str(plan.get("job_cost")) + " vs "
                    "ledger_tokens=" + str(plan.get("ledger_tokens")) + " "
                    "ledger_cost=" + str(plan.get("ledger_cost"))
                )
            elif action == "update":
                print(
                    "  current: tokens=" + str(plan.get("current_tokens")) + " "
                    "cost=" + str(plan.get("current_cost"))
                )
                print(
                    "  ledger:  tokens=" + str(plan.get("ledger_tokens")) + " "
                    "cost=" + str(plan.get("ledger_cost"))
                )
                print("  updates: " + str(plan.get("updates")))
                if args.apply:
                    result = apply_fix(conn, plan)
                    print("  Linhas atualizadas: " + str(result["updated"]))
                    if result["errors"]:
                        print("  ERROS: " + str(result["errors"]))
            if not args.apply and action == "update":
                print("[fix_job_577_ledger] Use --apply para aplicar.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
