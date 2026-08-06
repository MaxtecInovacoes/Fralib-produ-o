import re

with open('/opt/fralib/backend/endpoints/provider_alerts_endpoints.py', 'r') as f:
    content = f.read()

# Fix: CAST leads.id to TEXT for UUID comparison
content = content.replace(
    "LEFT JOIN leads l          ON l.id = a.lead_id",
    "LEFT JOIN leads l          ON l.id::text = a.lead_id::text"
)

with open('/opt/fralib/backend/endpoints/provider_alerts_endpoints.py', 'w') as f:
    f.write(content)
print('FIX 2 OK: CAST leads.id em provider_alerts_endpoints.py')
