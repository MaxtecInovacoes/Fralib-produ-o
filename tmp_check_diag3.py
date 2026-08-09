"""Root cause analysis v2 — check what tables exist, then gather data."""
import sys
sys.path.insert(0, "/app")
from backend.core.database import SessionLocal
from backend.core.db_imports import text

db = SessionLocal()

# List all tables
tables = db.execute(text("""
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
""")).fetchall()
print("=== Tables ===")
for t in tables:
    print(f"  {t[0]}")

# Check if there's a tenants-like table or tenant_id comes from somewhere else
print("\n=== Job payloads (first pipeline_lead) ===")
rows = db.execute(text("""
    SELECT id, tipo, status, attempts, payload
    FROM jobs
    WHERE tipo = 'pipeline_lead'
    ORDER BY id ASC
    LIMIT 2
""")).fetchall()
for r in rows:
    import json
    payload = r[4] or {}
    print(f"id={r[0]} | tipo={r[1]} | status={r[2]} | attempts={r[3]}")
    print(f"  payload keys: {list(payload.keys())}")
    print(f"  payload: {json.dumps(payload, ensure_ascii=False)[:500]}")
    print()

print("\n=== Recent failed pipeline jobs ===")
rows = db.execute(text("""
    SELECT id, tipo, status, attempts, last_error, last_phase, payload
    FROM jobs
    WHERE tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
    ORDER BY id DESC
    LIMIT 10
""")).fetchall()
for r in rows:
    import json
    payload = r[6] or {}
    print(f"id={r[0]} | {r[1]} | {r[2]} | att={r[3]} | phase={r[5]}")
    print(f"  error: {(r[4] or '')[:120]}")
    print(f"  keys: {list(payload.keys())[:8]}")
    print(f"  seg={payload.get('segmento')} | city={payload.get('cidade')} | lead_data={'yes' if payload.get('lead_data') else 'NO'}")
    print()

print("\n=== Lead IDs in DB ===")
rows = db.execute(text("SELECT id, nome, segmento, cidade FROM leads ORDER BY id")).fetchall()
for r in rows:
    print(f"  id={r[0]} | nome={r[1][:40] if r[1] else 'None'} | seg={r[2]} | city={r[3]}")

print("\n=== lead_supply_config (if exists) ===")
try:
    rows = db.execute(text("SELECT * FROM lead_supply_config LIMIT 3")).fetchall()
    if rows:
        cols = [d[0] for d in db.execute(text("SELECT * FROM lead_supply_config LIMIT 0")).cursor.description]
        for r in rows:
            d = dict(zip(cols, r))
            print(f"  {d}")
    else:
        print("  No rows")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== lead_config (if exists) ===")
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

print("\n=== lead_inventory (first 5) ===")
try:
    rows = db.execute(text("SELECT * FROM lead_inventory LIMIT 5")).fetchall()
    if rows:
        cols = [d[0] for d in db.execute(text("SELECT * FROM lead_inventory LIMIT 0")).cursor.description]
        for r in rows:
            d = dict(zip(cols, r))
            # Truncate long values
            for k, v in d.items():
                if isinstance(v, str) and len(v) > 80:
                    d[k] = v[:80] + "..."
            print(f"  {d}")
    else:
        print("  No rows")
except Exception as e:
    print(f"  Error: {e}")

db.close()
