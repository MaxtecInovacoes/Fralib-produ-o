"""Root cause analysis for pipeline failures."""
import sys
sys.path.insert(0, "/app")
from backend.core.database import SessionLocal
from backend.core.db_imports import text

db = SessionLocal()

# Check leads
leads = db.execute(text("SELECT COUNT(*) FROM leads")).fetchone()
print(f"Total leads: {leads[0]}")

# lead_inventory
inv = db.execute(text("SELECT COUNT(*) FROM lead_inventory")).fetchone()
print(f"lead_inventory: {inv[0]}")

# tenants
print("\n=== Tenants ===")
tenants = db.execute(text("SELECT id, nome, slug FROM tenants")).fetchall()
for t in tenants:
    print(f"  id={t[0]}, nome={t[1]}, slug={t[2]}")

# Hunter jobs (completed - these work)
print("\n=== Hunter jobs ===")
rows = db.execute(text("SELECT id, tipo, status, payload FROM jobs WHERE tipo='lead_supply_hunter' ORDER BY id DESC LIMIT 3")).fetchall()
for r in rows:
    payload = r[3] or {}
    print(f"id={r[0]} | {r[1]} | {r[2]}")
    print(f"  keys: {list(payload.keys())[:10]}")
    print(f"  seg={payload.get('segmento')} | city={payload.get('cidade')}")

# Lead supply config
print("\n=== lead_supply_config ===")
try:
    cols = [d[0] for d in db.execute(text("SELECT * FROM lead_supply_config LIMIT 0")).cursor.description]
    rows = db.execute(text("SELECT * FROM lead_supply_config LIMIT 3")).fetchall()
    for r in rows:
        d = dict(zip(cols, r))
        print(f"  {d}")
except Exception as e:
    print(f"  Error: {e}")

# Lead config per tenant
print("\n=== lead_config ===")
try:
    rows = db.execute(text("SELECT * FROM lead_config LIMIT 3")).fetchall()
    if rows:
        cols = [d[0] for d in db.execute(text("SELECT * FROM lead_config LIMIT 0")).cursor.description]
        for r in rows:
            d = dict(zip(cols, r))
            print(f"  {d}")
    else:
        print("  No rows")
except Exception as e:
    print(f"  Error: {e}")

db.close()
