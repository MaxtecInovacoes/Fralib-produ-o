#!/usr/bin/env python3
"""Fix leads status para user_id=2 e diagnostica o admin."""
import subprocess

VPS = "root@104.243.41.166"
CONTAINER = "52bc220171c8_fralib-postgres-1"
DB_USER = "fralib_user"
DB_NAME = "fralib_db"

def psql(query):
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-c", query],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else r.stderr

# 1. Check current state
print("=== LEADS DO USER 2 ===")
out = psql("SELECT id, nome, status, score, sdr_stage, tier FROM leads WHERE user_id = 2 ORDER BY criado_em DESC LIMIT 15;")
print(out)

# 2. Fix status: leads em 'pendente' sem site -> mantem pendente
# Leads com site_url -> concluido
print("\n=== FIX STATUS ===")
out = psql("""UPDATE leads SET status = CASE 
    WHEN url_site IS NOT NULL AND url_site != '' THEN 'concluido' 
    WHEN score >= 50 THEN 'qualificado'
    WHEN sdr_stage = 'pendente_wpp' THEN 'pendente'
    ELSE status 
END, 
atualizado_em = NOW()::text 
WHERE user_id = 2;""")
print(out)

# 3. Verify
print("\n=== APOS FIX ===")
out = psql("SELECT id, nome, status, score, sdr_stage, tier FROM leads WHERE user_id = 2 ORDER BY criado_em DESC LIMIT 15;")
print(out)

# 4. Check lead_inventory
print("\n=== LEAD_INVENTORY ===")
out = psql("SELECT id, nome, status, score_caio, tier, tenant_id FROM lead_inventory ORDER BY criado_em DESC LIMIT 20;")
print(out)

# 5. Check lead_supply_config
print("\n=== LEAD_SUPPLY_CONFIG ===")
out = psql("SELECT * FROM lead_supply_config;")
print(out)

# 6. Jobs count
print("\n=== JOBS POR STATUS ===")
out = psql("SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY 2 DESC;")
print(out)
