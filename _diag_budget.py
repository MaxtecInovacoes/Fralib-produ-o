"""Diagnóstico: por que llm_budget_ledger está vazio?
Roda NO VPS via docker exec, testando _registrar_llm_budget diretamente.
"""
import sys, os, traceback

# MESMO path do worker
for p in ['/app/backend', '/app/backend/core', '/app/backend/endpoints',
          '/app/backend/services', '/app/backend/agents', '/app/backend/utils']:
    sys.path.insert(0, p)

from backend.core.database import inicializar_database, engine
from sqlalchemy import text

inicializar_database()

# Test 1: INSERT direto (bypass Python)
print("=== TEST 1: INSERT direto ===")
try:
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO llm_budget_ledger
                (tenant_id, run_id, phase, agent, provider, model,
                 input_tokens, output_tokens, cost_usd, status)
            VALUES (:t, :r, :p, :a, :pr, :m, :i, :o, :c, :s)
        """), {"t": 2, "r": "diag-direct", "p": "test",
               "a": "diag_agent", "pr": "anthropic", "m": "claude-test",
               "i": 100, "o": 50, "c": 0.001, "s": "success"})
        conn.commit()
    r = engine.connect().execute(text("SELECT COUNT(*) FROM llm_budget_ledger WHERE run_id = 'diag-direct'"))
    print(f"  INSERT direto: {r.scalar()} rows")
except Exception as e:
    print(f"  INSERT direto FAILED: {e}")
    traceback.print_exc()

# Test 2: _registrar_llm_budget with verbose error capture
print("\n=== TEST 2: _registrar_llm_budget com traceback completo ===")
try:
    from backend.agents.llm_tracking import _registrar_llm_budget
    print("  Import OK")
except Exception as e:
    print(f"  Import FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# Monkey-patch para capturar o erro real
_original_registrar = _registrar_llm_budget

def _patched_registrar(*args, **kwargs):
    try:
        return _original_registrar(*args, **kwargs)
    except Exception as e:
        print(f"  EXCEPTION CAPTURADA: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None

import backend.agents.llm_tracking as lt
lt._registrar_llm_budget = _patched_registrar

# Agora importar o helper que usa _registrar_llm_budget
from backend.agents.llm_direct import _registrar_uso_completo

print("  Chamando _registrar_uso_completo...")
_registrar_uso_completo(
    model_id="claude-diagnostic",
    input_tokens=10,
    output_tokens=20,
    agent_name="diag_test",
    provider="anthropic",
    latency_ms=100,
    cache_read=5,
    cache_creation=0,
)
print("  _registrar_uso_completo retornou (verifique output acima)")

# Test 3: verificar se algo foi gravado
print("\n=== TEST 3: Verificar llm_budget_ledger ===")
r = engine.connect().execute(text("SELECT run_id, agent, model, input_tokens, output_tokens, cost_usd FROM llm_budget_ledger WHERE run_id IN ('diag-direct', 'smoke-2340') ORDER BY id DESC"))
rows = r.fetchall()
if rows:
    for row in rows:
        print(f"  ledger: run_id={row[0]} agent={row[1]} model={row[2]} in={row[3]} out={row[4]} cost={row[5]}")
else:
    print("  (vazio)")

# Test 4: mostrar schema da tabela
print("\n=== TEST 4: Schema de llm_budget_ledger ===")
r = engine.connect().execute(text("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'llm_budget_ledger'
    ORDER BY ordinal_position
"""))
for row in r.fetchall():
    print(f"  {row[0]}: {row[1]} (nullable={row[2]})")

# Test 5: último erro no Postgres (se houver)
print("\n=== TEST 5: Últimos erros Postgres ===")
try:
    r = engine.connect().execute(text("""
        SELECT statement_timestamp, severity, message_text
        FROM pg_stat_activity
        WHERE state = 'idle in transaction (aborted)'
           OR state LIKE '%%error%%'
        LIMIT 5
    """))
    rows = r.fetchall()
    if rows:
        for row in rows:
            print(f"  {row}")
    else:
        print("  (nenhuma transação abortada)")
except Exception as e:
    print(f"  (não disponível: {e})")

print("\n=== FIM DO DIAGNÓSTICO ===")
