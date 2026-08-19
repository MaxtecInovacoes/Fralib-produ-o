"""Dispara reprocessamento de lead via job_queue direto no worker."""
import sys
sys.path.insert(0, '/app/backend')

import os
import json

LEAD_ID = "b5db65cd-e856-487a-9fac-5f5d6caaa62f"  # Curitiba Fitness — concluido
TENANT_ID = 2

# Read lead info
from sqlalchemy import create_engine, text
db_url = os.environ.get("DATABASE_URL") or "postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db"
engine = create_engine(db_url)
with engine.connect() as conn:
    row = conn.execute(
        text("SELECT id, nome, user_id, status, segmento, cidade FROM leads WHERE id=:id"),
        {"id": LEAD_ID},
    ).fetchone()
    print("LEAD:", dict(row._mapping) if row else "NOT FOUND")
    if not row:
        sys.exit(1)

# Update lead status to capturado to allow reprocess
with engine.begin() as conn:
    conn.execute(
        text("UPDATE leads SET status='capturado', processado=false WHERE id=:id AND user_id=:uid"),
        {"id": LEAD_ID, "uid": TENANT_ID},
    )
    print("Lead marcado como capturado")

# Enqueue pipeline job
from backend.core.job_queue import enqueue
job_id = enqueue(
    None,  # db session — função interna lida
    tipo="pipeline_lead",
    payload={
        "segmento": row.segmento or "",
        "cidade": row.cidade or "",
        "quantidade": 1,
        "_lead_id_existente": LEAD_ID,
        "_forcar_renovacao": True,
    },
    tenant_id=TENANT_ID,
    max_attempts=3,
    priority=1,
)
print(f"JOB ENQUEUED: {job_id}")
print(f"Worker deve pegar em ~2s (WORKER_POLL_INTERVAL=2)")
