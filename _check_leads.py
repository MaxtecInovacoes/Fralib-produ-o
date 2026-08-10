"""Check leads table schema + existing leads."""
import sys
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/backend/core')
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Schema
    cols = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='leads' ORDER BY ordinal_position")).fetchall()
    print("leads columns:")
    for col in cols:
        print(f"  {col[0]} ({col[1]})")

    # All columns
    all_cols = [c[0] for c in cols]
    select_cols = ', '.join([c for c in all_cols if c not in ('created_at', 'updated_at')])

    # Recent leads
    r = conn.execute(text(f"SELECT {select_cols} FROM leads ORDER BY id DESC LIMIT 10"))
    rows = r.fetchall()
    print(f"\nRecent leads ({len(rows)} found):")
    for row in rows:
        print(f"  {dict(zip([c[0] for c in cols], row))}")
