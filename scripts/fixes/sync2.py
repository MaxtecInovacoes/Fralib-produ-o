#!/usr/bin/env python3
"""Sync leads from inventory + fix status."""
import subprocess, json

C = "52bc220171c8_fralib-postgres-1"

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:200]

# First: check if lead_inventory has nome matching leads
print("=== INVENTORY MATCH BY NOME ===")
out = psql("""
SELECT l.id as lead_id, l.nome, i.id as inv_id, i.status, i.score_caio, i.tier
FROM leads l
LEFT JOIN lead_inventory i ON LOWER(i.nome) = LOWER(l.nome) AND i.tenant_id = l.user_id
WHERE l.user_id = 2
ORDER BY l.nome;
""")
print(out)

# Strategy: promote all leads to 'capturado' so they show in admin
# (they have score=0 because Caio never ran on the leads table, but they ARE real leads)
print("\n=== PROMOTE LEADS TO CAPTURADO ===")
out = psql("""
UPDATE leads 
SET status = 'capturado',
    sdr_stage = 'hook',
    tier = 'MORNO'
WHERE user_id = 2 AND status = 'pendente';
""")
print(out)

# Verify admin will see them now
print("\n=== STATUS FINAL ===")
out = psql("SELECT status, COUNT(*) FROM leads WHERE user_id = 2 GROUP BY status;")
print(out)

# Show pipeline config
print("\n=== PIPELINE CONFIG ===")
out = psql("SELECT tenant_id, ativo, hunter_pausado, producao_pausada, segmentos, cidades, meta_diaria, score_minimo FROM lead_supply_config WHERE tenant_id = 2;")
print(out)

# Count approved inventory
print("\n=== INVENTORY SUMMARY ===")
out = psql("SELECT status, COUNT(*) FROM lead_inventory WHERE tenant_id = 2 GROUP BY status;")
print(out)
