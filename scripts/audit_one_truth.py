"""Audit canonical FraLib state without mutating data.

This reports places where legacy or duplicated state can disagree with the
chosen canonical sources:
- jobs for execution queue
- pipeline_failures for final failures
- lead_inventory for supply inventory
- leads.status for produced-site outcome
- users.plano for billing plan
- llm_budget_ledger for LLM cost/tokens
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "core"))
sys.path.insert(0, str(ROOT / "scripts"))


from _db_rows import rows as _rows  # noqa: E402  — canônico T1 (DRY)


def _one(conn, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = _rows(conn, sql, params)
    return rows[0] if rows else {}


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='public' AND table_name=:table
            """
        ),
        {"table": table},
    ).fetchone()
    return bool(row)


def _scan_legacy_pipeline_queue_usage() -> dict[str, Any]:
    patterns = [
        re.compile(r"\bFROM\s+pipeline_queue\b", re.IGNORECASE),
        re.compile(r"\bJOIN\s+pipeline_queue\b", re.IGNORECASE),
        re.compile(r"\bINSERT\s+INTO\s+pipeline_queue\b", re.IGNORECASE),
        re.compile(r"\bUPDATE\s+pipeline_queue\b", re.IGNORECASE),
        re.compile(r"\bDELETE\s+FROM\s+pipeline_queue\b", re.IGNORECASE),
    ]
    allowed_files = {
        "scripts/audit_one_truth.py",
        "scripts/reconcile_one_truth.py",
        "scripts/reset_runtime.py",
        "scripts/reset_controlled_test.py",
        "backend/core/database.py",
        "backend/services/hermes_watchdog.py",
    }
    findings: list[dict[str, Any]] = []
    for base in ("backend", "server.py", "worker.py", "scripts"):
        root = ROOT / base
        files = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            try:
                text_value = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for line_no, line in enumerate(text_value.splitlines(), start=1):
                if any(pattern.search(line) for pattern in patterns):
                    findings.append(
                        {
                            "file": rel,
                            "line": line_no,
                            "allowed_legacy": rel in allowed_files,
                            "text": line.strip()[:220],
                        }
                    )
    return {
        "findings": findings,
        "live_findings": [f for f in findings if not f["allowed_legacy"]],
    }


def run_audit() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "backend" / ".env")
    engine = create_engine(os.environ["DATABASE_URL"])
    report: dict[str, Any] = {
        "ok": True,
        "mode": "read_only",
        "source": "one_truth_audit",
        "code_usage": {
            "pipeline_queue": _scan_legacy_pipeline_queue_usage(),
        },
    }
    try:
        conn_ctx = engine.connect()
    except Exception as exc:
        report.update(
            {
                "ok": False,
                "error": "database_unavailable",
                "detail": str(exc).splitlines()[0],
            }
        )
        report["summary"] = {
            "pipeline_queue_live_code_usages": len(
                report["code_usage"]["pipeline_queue"]["live_findings"]
            )
        }
        return report
    with conn_ctx as conn:
        report["jobs"] = {
            "active": _rows(
                conn,
                """
                SELECT id, tipo, status, tenant_id, last_phase, worker_id,
                       worker_heartbeat, criado_em, iniciado_em
                FROM jobs
                WHERE status IN ('pending', 'running', 'failed_retriable')
                ORDER BY id DESC
                LIMIT 50
                """,
            ),
            "by_type_status": _rows(
                conn,
                """
                SELECT tipo, status, COUNT(*) AS total
                FROM jobs
                GROUP BY tipo, status
                ORDER BY total DESC, tipo, status
                """,
            ),
        }
        report["legacy_pipeline_queue"] = (
            {
                "exists": True,
                "rows_by_status": _rows(
                    conn,
                    """
                    SELECT status, COUNT(*) AS total
                    FROM pipeline_queue
                    GROUP BY status
                    ORDER BY total DESC, status
                    """,
                ),
                "live_rows": _rows(
                    conn,
                    """
                    SELECT id, user_id, segmento, cidade, status, criado_em, iniciado_em, erro
                    FROM pipeline_queue
                    WHERE status IN ('pending', 'running', 'pendente', 'em_andamento')
                    ORDER BY id DESC
                    LIMIT 50
                    """,
                ),
            }
            if _table_exists(conn, "pipeline_queue")
            else {"exists": False}
        )
        report["pipeline_state_divergence"] = _rows(
            conn,
            """
            WITH active_jobs AS (
                SELECT tenant_id, COUNT(*) AS active_jobs
                FROM jobs
                WHERE tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                  AND status IN ('pending', 'running', 'failed_retriable')
                GROUP BY tenant_id
            )
            SELECT ps.tenant_id, ps.rodando, ps.pausado,
                   COALESCE(aj.active_jobs, 0) AS active_jobs,
                   ps.updated_at
            FROM pipeline_state ps
            LEFT JOIN active_jobs aj ON aj.tenant_id = ps.tenant_id
            WHERE COALESCE(ps.rodando, false) <> (COALESCE(aj.active_jobs, 0) > 0)
            ORDER BY ps.tenant_id
            """,
        )
        report["lead_inventory"] = {
            "stale_locks": _rows(
                conn,
                """
                SELECT li.id, li.tenant_id, li.status, li.lead_id, li.locked_by,
                       li.locked_until, l.status AS lead_status, LEFT(COALESCE(li.erro,''), 240) AS erro
                FROM lead_inventory li
                LEFT JOIN leads l ON l.id = li.lead_id AND l.user_id = li.tenant_id
                WHERE li.status IN ('reserved', 'in_production', 'processing')
                  AND li.locked_until IS NOT NULL
                  AND li.locked_until < NOW()
                ORDER BY li.locked_until ASC
                LIMIT 100
                """,
            ),
            "status_counts": _rows(
                conn,
                """
                SELECT tenant_id, status, COUNT(*) AS total
                FROM lead_inventory
                GROUP BY tenant_id, status
                ORDER BY tenant_id, status
                """,
            ),
        }
        report["leads_status_divergence"] = _rows(
            conn,
            """
            SELECT status, pipeline_stage, COUNT(*) AS total
            FROM leads
            WHERE (status='concluido' AND COALESCE(pipeline_stage,'') <> 'concluido')
               OR (COALESCE(status,'') <> 'concluido' AND pipeline_stage='concluido')
            GROUP BY status, pipeline_stage
            ORDER BY total DESC, status, pipeline_stage
            """,
        )
        report["plan_divergence"] = _rows(
            conn,
            """
            SELECT id, email, plano, plan, status, plano_pago
            FROM users
            WHERE COALESCE(plano, '') <> COALESCE(plan, '')
            ORDER BY id
            LIMIT 100
            """,
        )
        report["llm_ledger_gaps"] = {
            "jobs_with_tokens_zero_but_ledger": _rows(
                conn,
                """
                SELECT j.id, j.run_id, j.tenant_id, j.status, j.llm_tokens_used,
                       j.llm_cost_estimate,
                       COALESCE(SUM(l.input_tokens + l.output_tokens
                                    + l.cache_read_tokens + l.cache_created_tokens), 0) AS ledger_tokens,
                       COALESCE(SUM(l.cost_usd), 0) AS ledger_cost
                FROM jobs j
                JOIN llm_budget_ledger l
                  ON l.job_id = j.id OR (j.run_id IS NOT NULL AND l.run_id = j.run_id)
                GROUP BY j.id, j.run_id, j.tenant_id, j.status, j.llm_tokens_used, j.llm_cost_estimate
                HAVING COALESCE(j.llm_tokens_used, 0) = 0
                   AND COALESCE(SUM(l.input_tokens + l.output_tokens
                                    + l.cache_read_tokens + l.cache_created_tokens), 0) > 0
                ORDER BY j.id DESC
                LIMIT 100
                """,
            ),
            "token_usage_zero_recent": _rows(
                conn,
                """
                SELECT id, tenant_id, run_id, lead_nome, nicho, total_input_tokens,
                       total_output_tokens, custo_total_usd, created_at
                FROM pipeline_token_usage
                WHERE created_at > NOW() - INTERVAL '7 days'
                  AND COALESCE(total_input_tokens, 0) = 0
                  AND COALESCE(total_output_tokens, 0) = 0
                ORDER BY id DESC
                LIMIT 100
                """,
            ),
        }
        report["summary"] = {
            "pipeline_queue_live_code_usages": len(
                report["code_usage"]["pipeline_queue"]["live_findings"]
            ),
            "active_jobs": len([r for r in report["jobs"]["active"] if "error" not in r]),
            "legacy_queue_live": len(
                [
                    r
                    for r in report["legacy_pipeline_queue"].get("live_rows", [])
                    if "error" not in r
                ]
            ),
            "pipeline_state_divergences": len(
                [r for r in report["pipeline_state_divergence"] if "error" not in r]
            ),
            "stale_inventory_locks": len(
                [r for r in report["lead_inventory"]["stale_locks"] if "error" not in r]
            ),
            "plan_divergences": len([r for r in report["plan_divergence"] if "error" not in r]),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit FraLib one-truth contract")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    report = run_audit()
    print(json.dumps(report, ensure_ascii=False, default=str, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
