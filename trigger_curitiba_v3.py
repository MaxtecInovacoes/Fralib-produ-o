"""Check state and enqueue Curitiba Fitness reprocess."""
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
    state = conn.execute(text("SELECT * FROM pipeline_state WHERE tenant_id=:t"), {"t": TENANT_ID}).fetchone()
    print("PIPELINE_STATE:", dict(state._mapping) if state else "NO STATE")

    jobs = conn.execute(
        text("SELECT id, tipo, status, payload, created_at FROM jobs WHERE status IN ('pending','running','queued') ORDER BY created_at DESC LIMIT 10")
    ).fetchall()
    print("=== ACTIVE JOBS ===")
    for j in jobs or []:
        print(dict(j._mapping))
    if not jobs:
        print("NO ACTIVE JOBS")

    row = conn.execute(
        text("SELECT nome, segmento, cidade, status FROM leads WHERE id=:i"),
        {"i": LEAD_ID},
    ).fetchone()
    print("TARGET LEAD:", dict(row._mapping) if row else "NOT FOUND")
    if not row:
        sys.exit(1)

    segmento = row.segmento or ""
    cidade = row.cidade or ""
    conn.execute(
        text("UPDATE leads SET status='capturado', processado=false WHERE id=:id"),
        {"id": LEAD_ID},
    )
    conn.commit()
    print("Lead status -> capturado")

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
