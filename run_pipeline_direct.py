"""Run pipeline directly for an existing qualified lead."""
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Load .env before importing backend modules
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.agents.manager.states import (
    PipelineState,
    STATE_QUALIFYING,
    STATE_DESIGNING,
    STATE_BUILDING,
    STATE_VALIDATING,
    STATE_PUBLISHING,
    STATE_OUTREACH,
    STATE_DONE,
    STATE_FAILED,
)
from backend.agents.manager.agent import run_pipeline
from backend.core.database import SessionLocal


LEAD_ID = "f07b88e1-66fc-420e-b645-f0a3065e4653"
TENANT_ID = 2
SEGMENTO = "academia"
CIDADE = "São Paulo"


def fetch_lead(db: Session, lead_id: str) -> dict:
    row = db.execute(
        text("""
        SELECT id, nome, segmento, cidade, status, url_site, site_url,
               tenant_id, email, telefone, endereco
        FROM leads
        WHERE id = :lid
        LIMIT 1
        """),
        {"lid": lead_id},
    ).fetchone()
    if not row:
        raise SystemExit(f"Lead {lead_id} not found")
    cols = [c[0] for c in row._metadata.keys()]
    return dict(zip(cols, row))


def fetch_jobs_column_names(db: Session) -> list[str]:
    cols = db.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'jobs' AND table_schema = 'public'
        ORDER BY ordinal_position
    """)).fetchall()
    return [c[0] for c in cols]


def main() -> None:
    print(f"[run] Initializing pipeline for lead={LEAD_ID} tenant={TENANT_ID}")
    db = SessionLocal()
    try:
        # Show jobs table columns for diagnostics
        job_cols = fetch_jobs_column_names(db)
        print(f"[run] jobs columns: {job_cols}")

        # Fetch lead
        lead = fetch_lead(db, LEAD_ID)
        print(f"[run] Lead found: {lead.get('nome')} | status={lead.get('status')} | tenant={lead.get('tenant_id')}")

        # Build lead_data dict
        lead_data = {
            "id": lead["id"],
            "nome": lead.get("nome", ""),
            "segmento": lead.get("segmento") or SEGMENTO,
            "cidade": lead.get("cidade") or CIDADE,
            "status": lead.get("status", ""),
            "url_site": lead.get("url_site") or lead.get("site_url") or "",
            "email": lead.get("email") or "",
            "telefone": lead.get("telefone") or "",
            "endereco": lead.get("endereco") or "",
        }

        state = PipelineState(
            tenant_id=TENANT_ID,
            lead_id=str(LEAD_ID),
            segmento=lead_data["segmento"],
            cidade=lead_data["cidade"],
            lead_data=lead_data,
            estado_manual="running",
        )
        print(f"[run] PipelineState created. Starting FSM...")

        result = run_pipeline(state)
        print(f"[run] Pipeline finished.")
        print(f"  final_state: {result.current_state}")
        print(f"  run_id: {result.run_id}")
        print(f"  error: {result.error or '(none)'}")
        print(f"  history: {result.history}")
        print(f"  deploy_url: {result.deploy_url or '(none)'}")
        print(f"  deploy_path: {result.deploy_path or '(none)'}")

        # Check jobs for this run_id
        if result.run_id:
            rows = db.execute(
                text("SELECT id, tipo, status, attempts FROM jobs WHERE run_id = :rid ORDER BY id"),
                {"rid": result.run_id},
            ).fetchall()
            print(f"[run] jobs for run_id={result.run_id}: {len(rows)}")
            for row in rows:
                print(f"  job id={row[0]} tipo={row[1]} status={row[2]} attempts={row[3]}")

    except Exception as exc:
        print(f"[run] EXCEPTION: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
