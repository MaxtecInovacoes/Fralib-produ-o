import os, sys
sys.path.insert(0, "/root/fralib")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")
from backend.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
# trava todos os outros approved por 1h - forca waleska a ser a proxima
db.execute(text("""
    UPDATE lead_inventory
    SET locked_until = NOW() + INTERVAL '1 hour'
    WHERE tenant_id = 2
      AND status = 'approved'
      AND LOWER(nome) NOT LIKE '%waleska%'
      AND id != '257a862460e74fe798ba0bf629e5b247'
"""))
db.commit()
print("outros leads travados; waleska sera a unica disponivel")
db.close()