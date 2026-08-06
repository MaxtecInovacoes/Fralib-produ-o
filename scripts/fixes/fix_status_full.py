#!/usr/bin/env python3
"""Fix completo: status dos leads + ativar pipeline."""
import subprocess

CONTAINER = "52bc220171c8_fralib-postgres-1"

def psql(query):
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", query],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:300]

# 1. Fix leads status baseado no inventory + dados existentes
print("=== 1. FIX LEADS STATUS ===")
# Leads com score > 0 -> qualificado, resto mantem pendente
# sdr_stage: pendente_wpp para quem tem score > 0
out = psql("""
UPDATE leads 
SET 
    status = CASE 
        WHEN url_site IS NOT NULL AND url_site != '' THEN 'concluido'
        WHEN score >= 50 THEN 'qualificado'
        WHEN score > 0 THEN 'capturado'
        ELSE status 
    END,
    sdr_stage = CASE 
        WHEN score >= 50 AND sdr_stage = 'pendente_wpp' THEN 'intro'
        WHEN sdr_stage = 'pendente_wpp' AND score > 0 THEN 'hook'
        ELSE sdr_stage 
    END,
    tier = CASE 
        WHEN score >= 80 AND tier IS NULL THEN 'QUENTE'
        WHEN score >= 50 AND tier IS NULL THEN 'MORNO'
        WHEN score < 50 AND tier IS NULL THEN 'FRIO'
        ELSE tier 
    END,
    atualizado_em = NOW()
WHERE user_id = 2;
""")
print(out)

# 2. Verify
print("\n=== 2. LEADS APOS FIX ===")
out = psql("SELECT id, nome, status, score, tier, sdr_stage FROM leads WHERE user_id = 2 ORDER BY criado_em DESC LIMIT 15;")
print(out)

# 3. Ativar pipeline para user 2
print("\n=== 3. ATIVAR PIPELINE ===")
out = psql("""
UPDATE lead_supply_config 
SET ativo = true, producao_pausada = false, hunter_pausado = false,
    atualizado_em = NOW()
WHERE tenant_id = 2;
""")
print(out)

# 4. Liberar leads error_retry do inventory
print("\n=== 4. FIX INVENTORY (error_retry -> approved para scores altos) ===")
out = psql("""
UPDATE lead_inventory 
SET status = CASE 
    WHEN score_caio >= 70 THEN 'approved'
    WHEN score_caio >= 45 THEN 'raw'
    ELSE 'discarded'
END
WHERE tenant_id = 2 AND status = 'error_retry';
""")
print(out)

# 5. Stats finais
print("\n=== 5. STATUS FINAL ===")
out = psql("""
SELECT 
    l.status, COUNT(*) as qtd, 
    COALESCE(AVG(l.score), 0) as score_medio
FROM leads l 
WHERE l.user_id = 2 
GROUP BY l.status 
ORDER BY qtd DESC;
""")
print(out)

out = psql("SELECT status, COUNT(*) FROM lead_inventory WHERE tenant_id = 2 GROUP BY status ORDER BY 2 DESC;")
print("Inventory:", out)

out = psql("SELECT ativo, hunter_pausado, producao_pausada FROM lead_supply_config WHERE tenant_id = 2;")
print("Pipeline config:", out)
