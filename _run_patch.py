import subprocess, sys

p = '/app/backend/agents/llm_tracking.py'
with open(p) as f:
    content = f.read()

# Patch 1: Add ENTRY print
old1 = "    try:\n        from backend.core.database import engine\n        from sqlalchemy import text"
new1 = '    print(f"[BUDGET-DEBUG] ENTRY: {modelo} in={input_tokens} out={output_tokens} agente={agente}", flush=True)\n    try:\n        from backend.core.database import engine\n        from sqlalchemy import text'
content = content.replace(old1, new1, 1)

# Patch 2: Add custo print
old2 = "        custo = _calcular_custo(modelo, usage)"
new2 = "        custo = _calcular_custo(modelo, usage)\n        print(f'[BUDGET-DEBUG] custo={custo}', flush=True)"
content = content.replace(old2, new2, 1)

# Patch 3: Add context print
old3 = """        # Get context from thread-local or tracker
        tenant_id = _get_tenant_context(tracker)"""
new3 = """        # Get context from thread-local or tracker
        print('[BUDGET-DEBUG] BEFORE ctx', flush=True)
        tenant_id = _get_tenant_context(tracker)
        print(f'[BUDGET-DEBUG] ctx: tenant={tenant_id} run={_get_run_context(tracker)} job={_get_job_context(tracker)}', flush=True)"""
content = content.replace(old3, new3, 1)

with open(p, 'w') as f:
    f.write(content)
print('PATCHED')
