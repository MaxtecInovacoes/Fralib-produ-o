from backend.core.database import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
try:
    # Lead inventory
    inv = db.execute(text("SELECT * FROM lead_inventory WHERE tenant_id=2 AND nome = :n"), {"n": "High Fitness Academia"}).fetchone()
    if inv:
        print("=== LEAD INVENTORY ===")
        for col in inv._fields:
            val = inv._mapping[col]
            if col == "dados" and val:
                val = json.dumps(json.loads(val), indent=2)[:1000]
            print(f"{col}: {val}")

    # List all tables
    tables = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).fetchall()
    print()
    print("=== ALL TABLES ===")
    for t in tables:
        print(f"  {t[0]}")

    # Check trace/event tables
    print()
    for tname in ["pipeline_traces", "pipeline_events", "event_log", "trace_logs", "span_logs"]:
        try:
            cnt = db.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar()
            print(f"{tname}: {cnt} rows")
            if cnt > 0:
                rows = db.execute(text(f"SELECT * FROM {tname} WHERE job_id=380")).fetchall()
                for r in rows:
                    print(f"  {r._mapping}")
        except Exception:
            pass
finally:
    db.close()
