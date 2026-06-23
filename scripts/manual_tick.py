import os, sys
sys.path.insert(0, "/root/fralib")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")
from backend.core.database import SessionLocal
from backend.services.lead_supply_providers.maps import run_production_tick
db = SessionLocal()
result = run_production_tick(db, {"reason": "manual-waleska", "_run_id": "waleska-manual"}, 2)
print("RESULT:", result)
db.close()