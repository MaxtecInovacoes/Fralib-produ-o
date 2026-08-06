import re

# Fix 1: Remove 'criado_em != """' from pipeline_endpoints.py
with open('/opt/fralib/backend/endpoints/pipeline_endpoints.py', 'r') as f:
    content = f.read()

old = "AND criado_em IS NOT NULL AND criado_em != ''"
new = "AND criado_em IS NOT NULL"
if old in content:
    content = content.replace(old, new)
    with open('/opt/fralib/backend/endpoints/pipeline_endpoints.py', 'w') as f:
        f.write(content)
    print('FIX 1 OK: removido criado_em != "" de pipeline_endpoints.py')
else:
    print('FIX 1: padrao nao encontrado, verificar')

# Fix 2: leads.id VARCHAR -> INTEGER (via ALTER TABLE SQL)
# This is done via SQL, not Python
print('FIX 2: sera feito via ALTER TABLE SQL')
