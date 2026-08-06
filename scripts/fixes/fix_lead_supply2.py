#!/usr/bin/env python3
"""Fix lead_supply_endpoints SQL queries to match real schema."""
import subprocess

filepath = "/opt/fralib/backend/endpoints/lead_supply_endpoints.py"

r = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat", filepath],
    capture_output=True, text=True
)
content = r.stdout

# Fix events query (line 139-141): correct column names
# Real schema: id, tenant_id, source, level, message, payload, criado_em
old_events = (
    "SELECT id, tipo, evento, nivel, mensagem, origem, payload, criado_em "
    "FROM lead_supply_events WHERE tenant_id = :uid "
    "ORDER BY criado_em DESC LIMIT 20"
)
new_events = (
    "SELECT id, source AS origem, level AS nivel, message AS mensagem, payload, criado_em "
    "FROM lead_supply_events WHERE tenant_id = :uid "
    "ORDER BY criado_em DESC LIMIT 20"
)
content = content.replace(old_events, new_events)

# Fix config query: add 'provider' and 'falhas_consecutivas' which exist in schema
# Already handled in previous patch - check line 100 area
if "SELECT tenant_id, segmentos" in content:
    print("Config SELECT already fixed")
else:
    # Fix the multi-line config select
    content = content.replace(
        "SELECT id, segmentos, cidades, meta_diaria, score_minimo",
        "SELECT tenant_id, segmentos, cidades, meta_diaria, score_minimo, provider, falhas_consecutivas"
    )

# Write back
p = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat > " + filepath],
    input=content, text=True, capture_output=True
)
if p.returncode == 0:
    print("Patched OK")
    # Verify the changes
    r2 = subprocess.run(
        ["ssh", "root@104.243.41.166", "grep", "-n", "SELECT", filepath],
        capture_output=True, text=True
    )
    print("\nAll SELECTs:")
    print(r2.stdout)
else:
    print("Write error:", p.stderr[:200])
