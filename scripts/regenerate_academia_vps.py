"""Re-enfileira job de rebuild para o lead academia-pipeline-teste."""
import os
import sys
import uuid

sys.path.insert(0, "/root/fralib")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")
from backend.core.database import SessionLocal
from backend.core.job_queue import enqueue
from sqlalchemy import text

LEAD_ID = "test-tenant2-academia-20260622193321"
TENANT_ID = 2

db = SessionLocal()
try:
    # Limpa jobs pendentes para esse lead (se houver)
    db.execute(text("""
        DELETE FROM jobs
        WHERE tenant_id = :tid
        AND (payload->>'lead_id' = :lid OR payload->>'_lead_id_existente' = :lid)
        AND status IN ('pending', 'running')
    """), {"tid": TENANT_ID, "lid": LEAD_ID})

    # Limpa html_gerado e url_site
    db.execute(text("""
        UPDATE leads
        SET status = 'novo', pipeline_stage = 'novo', html_gerado = NULL, url_site = NULL
        WHERE id = :lid
    """), {"lid": LEAD_ID})
    db.commit()

    # Enfileira pipeline_lead
    run_id = uuid.uuid4().hex[:12]
    payload = {
        "lead_id": LEAD_ID,
        "tenant_id": TENANT_ID,
        "_run_id": run_id,
        "_forcar_renovacao": True,
        "reason": "ecc-loop-regenerate-2025-06-23",
    }
    job_id = enqueue(
        db,
        tipo="pipeline_lead",
        payload=payload,
        tenant_id=TENANT_ID,
        max_attempts=1,
        idempotency_key=f"ecc-regenerate-{LEAD_ID}-{uuid.uuid4().hex[:6]}",
        delay_seconds=1,
        priority=1,
        run_id=run_id,
    )
    print(f"Job enqueued: {job_id} (run_id={run_id})")
    db.commit()
except Exception as e:
    print(f"ERRO: {e}")
    db.rollback()
    raise
finally:
    db.close()
