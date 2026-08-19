"""Enfileira reprocessamento do Curitiba Fitness diretamente no worker."""
import sys
sys.path.insert(0, '/app/backend')

import os
os.environ['DATABASE_URL'] = 'postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db'

from sqlalchemy import create_engine, text
from backend.core.job_queue import enqueue

LEAD_ID = "b5db65cd-e856-487a-9fac-5f5d6caaa62f"
TENANT_ID = 2

db_url = "postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db"
engine = create_engine(db_url)

with engine.connect() as conn:
    row = conn.execute(
        text("SELECT nome, segmento, cidade, status FROM leads WHERE id=:i"),
        {"i": LEAD_ID},
    ).fetchone()
    print("LEAD:", dict(row._mapping) if row else "NOT FOUND")
    if not row:
        sys.exit(1)
    segmento = row.segmento or ""
    cidade = row.cidade or ""
    conn.execute(
        text("UPDATE leads SET status='capturado', processado=false WHERE id=:id"),
        {"id": LEAD_ID},
    )
    conn.commit()
    print("status -> capturado")

try:
    job = enqueue(
        None,
        tipo="pipeline_lead",
        payload={
            "_lead_id_existente": LEAD_ID,
            "segmento": segmento,
            "cidade": cidade,
            "quantidade": 1,
            "_forcar_renovacao": True,
        },
        tenant_id=TENANT_ID,
        max_attempts=3,
        priority=1,
    )
    print("JOB_ID:", job)
except Exception as e:
    print("ENQUEUE ERROR:", e)
    import traceback
    traceback.print_exc()
