#!/usr/bin/env python3
"""Patch llm_tracking.py on VPS worker with debug prints."""
import subprocess

# Read file from container
result = subprocess.run(
    ['ssh', 'root@104.243.41.166',
     'docker', 'exec', 'fralib-worker-1', 'cat', '/app/backend/agents/llm_tracking.py'],
    capture_output=True, text=True
)
content = result.stdout

# Patch 1: Add ENTRY print at start of function
content = content.replace(
    'def _registrar_llm_budget(',
    'def _registrar_llm_budget_patched(',
    1
)

# Add debug print after function def and before try
content = content.replace(
    "def _registrar_llm_budget_patched(\n",
    "def _registrar_llm_budget_patched(\n"
)

# Let's find the exact text to replace - add entry print after the docstring, before try
old_try = "    try:\n        from backend.core.database import engine\n        from sqlalchemy import text"
new_try = "    print(f\"[BUDGET-DEBUG] ENTRY: modelo={modelo} in={input_tokens} out={output_tokens} agente={agente}\", flush=True)\n    try:\n        from backend.core.database import engine\n        from sqlalchemy import text"
content = content.replace(old_try, new_try, 1)

# Add debug print after custo calculation
old_custo = "        custo = _calcular_custo(modelo, usage)"
new_custo = "        custo = _calcular_custo(modelo, usage)\n        print(f\"[BUDGET-DEBUG] custo={custo}\", flush=True)"
content = content.replace(old_custo, new_custo, 1)

# Add debug print after context variables
old_context = """        # Get context from thread-local or tracker
        tenant_id = _get_tenant_context(tracker)"""
new_context = """        # Get context from thread-local or tracker
        print(f"[BUDGET-DEBUG] BEFORE ctx: tenant_id=?", flush=True)
        tenant_id = _get_tenant_context(tracker)
        print(f"[BUDGET-DEBUG] tenant_id={tenant_id} run_id={_get_run_context(tracker)} job_id={_get_job_context(tracker)}", flush=True)"""
content = content.replace(old_context, new_context, 1)

# Rename function back
content = content.replace("def _registrar_llm_budget_patched(", "def _registrar_llm_budget(")

# Write back
proc = subprocess.run(
    ['ssh', 'root@104.243.41.166',
     'docker', 'exec', '-i', 'fralib-worker-1', 'python3', '-c',
     f'import sys; sys.stdout.buffer.write(open("/dev/stdin","rb").read())'],
    input=content, capture_output=True
)
# Instead, pipe directly
proc = subprocess.Popen(
    ['ssh', 'root@104.243.41.166',
     'docker', 'exec', '-i', 'fralib-worker-1', 'tee', '/app/backend/agents/llm_tracking.py'],
    stdin=subprocess.PIPE
)
proc.communicate(input=content.encode('utf-8'))
print('Patched successfully')
