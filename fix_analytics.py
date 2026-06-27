"""
Script para substituir INTERVAL ':days days' por f-string INTERVAL '{int(var)} days'
"""
import re

with open('backend/endpoints/analytics_endpoints.py', 'r') as f:
    content = f.read()

# Para cada função, encontra a variável correta
function_var_map = {
    'get_utm_analytics': 'period_days',
    'get_funnel_analytics': 'period_days',
    'get_kpi_analytics': 'period_days',
    'get_growth_dashboard': 'days_num',
    'get_timeline': 'days',
    'get_cohort': 'period_days',
}

# Estratégia: encontrar cada bloco de query com .replace(':days', str(period_days))
# e substituir por f-string

# Padrão: linhas com .replace(':days', str(period_days)) dentro de db.execute
pattern = r"(\"\"\"[\s\S]*?INTERVAL) ':days days'([\s\S]*?)\"\"\"\.replace\(':days', str\(([^)]+)\)\)\)"
matches = list(re.finditer(pattern, content))

print(f"Encontrados {len(matches)} blocos para substituir")

for m in matches:
    var = m.group(3)
    new = m.group(1) + " '{int(" + var + ")} days'" + m.group(2) + 'f\"\"\"'
    content = content[:m.start()] + new + content[m.end():]

with open('backend/endpoints/analytics_endpoints.py', 'w') as f:
    f.write(content)
print('OK')
