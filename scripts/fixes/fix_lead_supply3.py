#!/usr/bin/env python3
"""Clean patch for lead_supply_endpoints SQL fixes."""
import subprocess, re

filepath = "/opt/fralib/backend/endpoints/lead_supply_endpoints.py"

# Read from VPS
r = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat", filepath],
    capture_output=True, text=True
)
content = r.stdout

# Fix 1: Config SELECT - remove 'id', keep string intact
# Original: "SELECT id, segmentos, cidades, meta_diaria, score_minimo,\n            estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada,\n            criado_em, atualizado_em\n        FROM lead_supply_config..."
content = content.replace(
    "SELECT id, segmentos, cidades, meta_diaria, score_minimo,\n            estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada,\n            criado_em, atualizado_em\n        FROM lead_supply_config",
    "SELECT segmentos, cidades, meta_diaria, score_minimo,\n            estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada,\n            provider, falhas_consecutivas, criado_em, atualizado_em\n        FROM lead_supply_config"
)

# Fix 2: Events SELECT - use AS aliases for renamed columns
content = content.replace(
    "SELECT id, tipo, evento, nivel, mensagem, origem, payload, criado_em\n        FROM lead_supply_events",
    "SELECT id, source AS origem, level AS nivel, message AS mensagem, payload, criado_em\n        FROM lead_supply_events"
)

# Write back
p = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat > " + filepath],
    input=content, text=True, capture_output=True
)
if p.returncode == 0:
    print("Patched OK")
    # Verify syntax
    p2 = subprocess.run(
        ["ssh", "root@104.243.41.166", "python3", "-c", "import py_compile; py_compile.compile('" + filepath + "', doraise=True); print('Syntax OK')"],
        capture_output=True, text=True
    )
    print(p2.stdout.strip())
    if p2.returncode != 0:
        print("SYNTAX ERROR:", p2.stderr[:300])
else:
    print("Write error:", p.stderr[:200])
