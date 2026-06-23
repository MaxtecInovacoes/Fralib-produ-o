import os, sys
sys.path.insert(0, "/root/fralib")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")
from backend.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
# libera a waleska e reseta
db.execute(text("UPDATE lead_inventory SET status='approved', locked_by=NULL, locked_until=NULL WHERE tenant_id=2 AND LOWER(nome) LIKE '%waleska%'"))
db.commit()
# cria tick para a waleska diretamente
import uuid
from backend.core.job_queue import job_queue
payload = {
    "reason": "manual-waleska-reprocess",
    "_run_id": uuid.uuid4().hex[:12],
    "_lead_id_existente": None,
    "_inventory_id": "257a862460e74fe798ba0bf629e5b247",
    "_forcar_renovacao": True,
    "_cold_run": True,
    "_prompt_agent_flow": True,
}
job_id = job_queue.enqueue(
    db,
    tipo="lead_production_tick",
    payload=payload,
    tenant_id=2,
    max_attempts=1,
    idempotency_key=f"manual-waleska-{uuid.uuid4().hex[:6]}",
    delay_seconds=1,
    priority=1,
    run_id=payload["_run_id"],
)
print(f"TICK enqueued: {job_id}")
db.close()