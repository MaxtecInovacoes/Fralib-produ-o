#!/usr/bin/env python3
"""Sync scores/tier from inventory to leads + test endpoints."""
import subprocess

C = "52bc220171c8_fralib-postgres-1"

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:200]

# Sync score/tier from best matching inventory item (by nome)
print("=== SYNC SCORES ===")
out = psql("""
UPDATE leads l
SET score = i_max.max_score,
    tier = i_max.max_tier
FROM (
    SELECT l2.id as lead_id, MAX(i.score_caio) as max_score, MAX(i.tier) as max_tier
    FROM leads l2
    JOIN lead_inventory i ON LOWER(i.nome) = LOWER(l2.nome) AND i.tenant_id = l2.user_id
    WHERE l2.user_id = 2
    GROUP BY l2.id
) i_max
WHERE l.id = i_max.lead_id;
""")
print(out)

# Verify
print("\n=== LEADS COM SCORE ===")
out = psql("SELECT id, nome, status, score, tier, sdr_stage FROM leads WHERE user_id = 2 ORDER BY score DESC LIMIT 15;")
print(out)
