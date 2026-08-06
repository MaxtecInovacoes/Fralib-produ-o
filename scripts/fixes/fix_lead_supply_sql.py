"""Fix lead_supply_endpoints.py: correct SQL queries for real schema."""
import subprocess

filepath = "/opt/fralib/backend/endpoints/lead_supply_endpoints.py"

r = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat", filepath],
    capture_output=True, text=True
)
content = r.stdout

# Fix 1: Remove 'id' from config SELECT (table has no id column, PK is tenant_id)
old_config_select = (
    "SELECT id, segmentos, cidades, meta_diaria, score_minimo, "
    "estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada, "
    "criado_em, atualizado_em "
    "FROM lead_supply_config WHERE tenant_id = :uid LIMIT 1"
)
new_config_select = (
    "SELECT tenant_id, segmentos, cidades, meta_diaria, score_minimo, "
    "estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada, "
    "provider, falhas_consecutivas, criado_em, atualizado_em "
    "FROM lead_supply_config WHERE tenant_id = :uid LIMIT 1"
)

if old_config_select in content:
    content = content.replace(old_config_select, new_config_select)
    print("Fixed config SELECT")
else:
    print("Config SELECT not found exactly, searching...")
    # Try to find and replace the line with SELECT id
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "SELECT id, segmentos" in line and "lead_supply_config" in lines[i+3]:
            lines[i] = "        SELECT tenant_id, segmentos, cidades, meta_diaria, score_minimo, "
            lines[i+1] = "            estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada, "
            lines[i+2] = "            provider, falhas_consecutivas, criado_em, atualizado_em "
            print(f"Fixed at line {i+1}")
            break
    content = "\n".join(lines)

# Fix 2: Fix events SELECT (table has: id, tenant_id, source, level, message, payload, criado_em)
old_events = (
    "SELECT id, tipo, evento, nivel, mensagem, origem, payload, criado_em "
    "FROM lead_supply_events WHERE tenant_id = :uid "
    "ORDER BY criado_em DESC LIMIT 20"
)
new_events = (
    "SELECT id, source as origem, level as nivel, message as mensagem, payload, criado_em "
    "FROM lead_supply_events WHERE tenant_id = :uid "
    "ORDER BY criado_em DESC LIMIT 20"
)

if old_events in content:
    content = content.replace(old_events, new_events)
    print("Fixed events SELECT")
else:
    print("Events SELECT not found")

# Write back
p = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat > " + filepath],
    input=content, text=True, capture_output=True
)
if p.returncode == 0:
    print("Patched OK")
else:
    print("Write error:", p.stderr[:200])
