"""Check pipeline state on VPS - simple diagnostic."""
from backend.core.database import engine
from sqlalchemy import text

# Schema of pipeline_executions
print("=== pipeline_executions schema ===")
r = engine.connect().execute(text("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'pipeline_executions' ORDER BY ordinal_position
"""))
cols = [row[0] for row in r.fetchall()]
print(f"  Columns: {cols}")

# Recent jobs
print("\n=== Recent pipeline jobs ===")
r = engine.connect().execute(text("""
    SELECT id, tipo, status, created_at, next_retry_at
    FROM jobs WHERE tipo LIKE 'pipeline_%' ORDER BY id DESC LIMIT 10
"""))
for row in r.fetchall():
    print(f"  id={row[0]} tipo={row[1]} status={row[2]} created={row[3]}")

# Check sites dir via filesystem
print("\n=== SITES DIRS ===")
import os
for p in ["/opt/fralib/data/sites", "/app/data/sites", "/opt/fralib/sites"]:
    if os.path.exists(p):
        items = os.listdir(p)
        print(f"  {p}: {len(items)} items")
        for item in items[:10]:
            full = os.path.join(p, item)
            if os.path.isdir(full):
                sub = os.listdir(full)
                print(f"    {item}/ ({len(sub)})")
                for s in sub[:5]:
                    print(f"      {s}")
            else:
                print(f"    {item}")
    else:
        print(f"  {p}: NOT FOUND")
