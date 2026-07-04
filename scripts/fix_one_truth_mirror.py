"""
Fix One-Truth Mirror — corrige divergencias entre fontes canonicas e espelhos.

Fontes canonicas:
  - users.plano   (canonico)
  - leads.status  (canonico)

Espelhos que devem espelhar a fonte:
  - users.plan    (espelha users.plano)
  - leads.pipeline_stage (espelha leads.status)

Uso:
  python scripts/fix_one_truth_mirror.py           # dry-run (default)
  python scripts/fix_one_truth_mirror.py --apply    # aplica correcoes
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
sys.path.insert(0, str(ROOT / "scripts"))


from _db_rows import rows as _rows  # noqa: E402  — canônico T1 (DRY)


def audit_mirrors(conn) -> dict[str, Any]:
    """Retorna divergencias entre fonte canonica e espelho (read-only)."""
    return {
        "users_plan_divergence": _rows(
            conn,
            """
            SELECT id, email, plano, plan
            FROM users
            WHERE COALESCE(plano, '') <> COALESCE(plan, '')
            LIMIT 200
            """,
        ),
        "leads_stage_divergence": _rows(
            conn,
            """
            SELECT id, user_id, status, pipeline_stage
            FROM leads
            WHERE COALESCE(status, '') <> COALESCE(pipeline_stage, '')
              AND status IS NOT NULL
            LIMIT 200
            """,
        ),
    }


def build_fix_plan(audit: dict[str, Any]) -> dict[str, Any]:
    """Gera plano de correcao a partir do audit (read-only)."""
    plan: dict[str, Any] = {
        "users.plan_fix": [],
        "leads.pipeline_stage_fix": [],
        "dry_run": True,
    }

    for row in audit.get("users_plan_divergence", []):
        if "error" not in row:
            plan["users.plan_fix"].append({
                "id": row["id"],
                "email": row["email"],
                "from_plan": row.get("plan"),
                "to_plano": row["plano"],
            })

    for row in audit.get("leads_stage_divergence", []):
        if "error" not in row:
            plan["leads.pipeline_stage_fix"].append({
                "id": row["id"],
                "user_id": row["user_id"],
                "from_pipeline_stage": row.get("pipeline_stage"),
                "to_status": row["status"],
            })

    return plan


def apply_fixes(conn, plan: dict[str, Any]) -> dict[str, Any]:
    """Aplica as correcoes do plano (soh com --apply)."""
    result = {"users_plan_updated": 0, "leads_stage_updated": 0, "errors": []}

    for item in plan.get("users.plan_fix", []):
        try:
            conn.execute(
                text("UPDATE users SET plan=:to_plan WHERE id=:id"),
                {"to_plan": item["to_plano"], "id": item["id"]},
            )
            result["users_plan_updated"] += 1
        except Exception as exc:
            result["errors"].append(f"users.id={item['id']}: {exc}")

    for item in plan.get("leads.pipeline_stage_fix", []):
        try:
            conn.execute(
                text("UPDATE leads SET pipeline_stage=:to_status WHERE id=:id"),
                {"to_status": item["to_status"], "id": item["id"]},
            )
            result["leads_stage_updated"] += 1
        except Exception as exc:
            result["errors"].append(f"leads.id={item['id']}: {exc}")

    conn.commit()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix one-truth mirror divergences (canonico: plano/status)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar correcoes. Sem esta flag roda em dry-run.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
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
        audit = audit_mirrors(conn)
        plan = build_fix_plan(audit)

        if args.json:
            output = dict(plan)
            output["dry_run"] = not args.apply
            if args.apply:
                result = apply_fixes(conn, plan)
                output["apply_result"] = result
            print(json.dumps(output, ensure_ascii=False, default=str, indent=2))
        else:
            n_users = len(plan["users.plan_fix"])
            n_leads = len(plan["leads.pipeline_stage_fix"])
            mode = "DRY-RUN" if not args.apply else "APLICANDO"
            print(f"[fix_one_truth_mirror] Modo: {mode}")
            print(f"  users.plan diverge: {n_users} registro(s)")
            for item in plan["users.plan_fix"]:
                print(
                    f"    id={item['id']} email={item['email']} "
                    f"plan='{item['from_plan']}' -> plano='{item['to_plano']}'"
                )
            print(f"  leads.pipeline_stage diverge: {n_leads} registro(s)")
            for item in plan["leads.pipeline_stage_fix"]:
                print(
                    f"    id={item['id']} user_id={item['user_id']} "
                    f"stage='{item['from_pipeline_stage']}' -> status='{item['to_status']}'"
                )

            if args.apply:
                result = apply_fixes(conn, plan)
                print(f"[fix_one_truth_mirror] Aplicado:")
                print(f"  users.plan atualizados: {result['users_plan_updated']}")
                print(f"  leads.pipeline_stage atualizados: {result['leads_stage_updated']}")
                if result["errors"]:
                    print(f"  ERROS: {result['errors']}")
            else:
                print("[fix_one_truth_mirror] Use --apply para aplicar.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
