"""Debug: test _registrar_llm_budget directly."""
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

from backend.core.database import inicializar_database, engine
from sqlalchemy import text

inicializar_database()

# Direct INSERT test
with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO llm_budget_ledger
            (tenant_id, run_id, agent, provider, model, input_tokens, output_tokens, cost_usd, status)
        VALUES (:t, :r, :a, :p, :m, :i, :o, :c, :s)
    """), {"t": 2, "r": "test-manual", "a": "test_agent", "p": "anthropic",
           "m": "claude-test", "i": 100, "o": 50, "c": 0.001, "s": "success"})
    conn.commit()
    r = conn.execute(text("SELECT COUNT(*) FROM llm_budget_ledger WHERE run_id = 'test-manual'"))
    print(f"Direct INSERT count: {r.scalar()}")

# Now test _registrar_llm_budget
from backend.agents.llm_tracking import _registrar_llm_budget
from backend.agents.token_tracker import TokenTracker, set_tracker

tracker = TokenTracker(run_id="test-budget", lead_nome="test", nicho="test")
set_tracker(tracker)

print("Calling _registrar_llm_budget...")
try:
    _registrar_llm_budget("claude-test-2", 10, 20, agente="test", provider="anthropic",
                          cache_read=5, cache_created=0)
    print("_registrar_llm_budget: no exception")
except Exception as e:
    print(f"_registrar_llm_budget EXCEPTION: {e}")

r2 = conn.execute(text("SELECT COUNT(*) FROM llm_budget_ledger WHERE run_id = 'test-budget'"))
print(f"After _registrar_llm_budget count: {r2.scalar()}")

# Show all rows
r3 = conn.execute(text("SELECT run_id, agent, model, input_tokens, output_tokens, cost_usd FROM llm_budget_ledger ORDER BY id DESC LIMIT 5"))
for row in r3.fetchall():
    print(f"  ledger: run_id={row[0]} agent={row[1]} model={row[2]} in={row[3]} out={row[4]} cost={row[5]}")
