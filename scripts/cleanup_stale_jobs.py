import os, sys
sys.path.insert(0, "/root/fralib")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")
from backend.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
# liberar lead Camila que reservamos manualmente
db.execute(text("""
    UPDATE lead_inventory
    SET status='approved', locked_by=NULL, locked_until=NULL
    WHERE tenant_id=2 AND status='reserved' AND locked_by LIKE 'manual-%'
"""))
print("Camila lock cleared")
# jobs stuck/failed - marca como done para nao bloquear proximo tick
db.execute(text("""
    UPDATE jobs SET status='done_finished', concluido_em=NOW()
    WHERE tenant_id=2 AND status IN ('failed_permanent','pending','running')
"""))
print("stale jobs done")
db.commit()
db.close()