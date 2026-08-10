"""Direct diagnostic on VPS container — check llm_budget_ledger state."""
import sys
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/backend/core')

from backend.core.database import engine
from sqlalchemy import text

# Schema
print('=== llm_budget_ledger schema ===')
r = engine.connect().execute(text("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'llm_budget_ledger'
    ORDER BY ordinal_position
"""))
for row in r.fetchall():
    print(f'  {row[0]}: {row[1]} nullable={row[2]} default={row[3]}')

# Constraints
print()
print('=== Constraints ===')
r = engine.connect().execute(text("""
    SELECT conname, contype, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    WHERE conrelid = 'llm_budget_ledger'::regclass
"""))
rows = r.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]}: type={row[1]} def={row[2]}')
else:
    print('  No constraints found')

# Total rows
print()
print('=== Total rows ===')
r = engine.connect().execute(text('SELECT COUNT(*) FROM llm_budget_ledger'))
print(f'  {r.scalar()}')

# Recent rows
print()
print('=== Last 5 rows ===')
r = engine.connect().execute(text("""
    SELECT id, tenant_id, job_id, run_id, phase, agent, provider, model,
           input_tokens, output_tokens, cost_usd, status, created_at
    FROM llm_budget_ledger
    ORDER BY id DESC LIMIT 5
"""))
rows = r.fetchall()
if rows:
    for row in rows:
        print(f'  id={row[0]} tenant={row[1]} job={row[2]} run={row[3]} phase={row[4]} agent={row[5]} provider={row[6]} model={row[7]} in={row[8]} out={row[9]} cost={row[10]} status={row[11]} created={row[12]}')
else:
    print('  (empty)')

# Test direct INSERT with NULL values (simulating what _registrar_llm_budget does)
print()
print('=== Test INSERT with NULL tenant_id/run_id ===')
try:
    engine.connect().execute(text("""
        INSERT INTO llm_budget_ledger
            (tenant_id, run_id, phase, agent, provider, model,
             input_tokens, output_tokens, cost_usd, status)
        VALUES (:t, :r, :p, :a, :pr, :m, :i, :o, :c, :s)
    """), {"t": None, "r": None, "p": None, "a": "test_null", "pr": "test",
           "m": "test-model", "i": 1, "o": 1, "c": 0.001, "s": "success"})
    engine.connect().commit()
    r = engine.connect().execute(text("SELECT COUNT(*) FROM llm_budget_ledger WHERE agent = 'test_null'"))
    print(f'  Rows with test_null: {r.scalar()}')
except Exception as e:
    print(f'  FAILED: {e}')

# Test INSERT with actual values
print()
print('=== Test INSERT with real values ===')
try:
    engine.connect().execute(text("""
        INSERT INTO llm_budget_ledger
            (tenant_id, run_id, phase, agent, provider, model,
             input_tokens, output_tokens, cost_usd, status)
        VALUES (:t, :r, :p, :a, :pr, :m, :i, :o, :c, :s)
    """), {"t": 2, "r": "test-real-123", "p": "test", "a": "test_real",
           "pr": "anthropic", "m": "claude-test", "i": 100, "o": 50, "c": 0.01, "s": "success"})
    engine.connect().commit()
    r = engine.connect().execute(text("SELECT COUNT(*) FROM llm_budget_ledger WHERE run_id = 'test-real-123'"))
    print(f'  Rows with test-real-123: {r.scalar()}')
except Exception as e:
    print(f'  FAILED: {e}')

# Check if there's a separate schema or search_path
print()
print('=== Search path ===')
r = engine.connect().execute(text('SHOW search_path'))
print(f'  {r.scalar()}')

print()
print('=== Current schema ===')
r = engine.connect().execute(text('SELECT current_schema()'))
print(f'  {r.scalar()}')

# List all tables
print()
print('=== All tables ===')
r = engine.connect().execute(text("""
    SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename
"""))
for row in r.fetchall():
    print(f'  {row[0]}')
