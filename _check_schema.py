"""Check table schemas."""
import sys
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/backend/core')
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    for table in ['pipeline_traces', 'llm_budget_ledger']:
        cols = c.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}' ORDER BY ordinal_position")).fetchall()
        print(f"{table} columns:")
        for col in cols:
            print(f"  {col[0]} ({col[1]})")
        print()
