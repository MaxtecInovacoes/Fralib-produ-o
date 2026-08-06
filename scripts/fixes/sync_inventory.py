#!/usr/bin/env python3
"""Sync leads status from inventory and verify CRM."""
import subprocess

C = "52bc220171c8_fralib-postgres-1"

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:200]

# Check if score column has actual data or if it's always 0
print("=== SCORE REAL DOS LEADS ===")
out = psql("SELECT id, nome, score, url_site FROM leads WHERE user_id = 2;")
print(out)

# The real issue: score is 0 for ALL leads. This means Caio never wrote scores.
# But inventory has real scores. Let's sync score from inventory where possible.
print("\n=== SYNC SCORE/TIER FROM INVENTORY ===")
out = psql("""
UPDATE leads l
SET 
    score = COALESCE(i.score_caio, l.score),
    tier = COALESCE(i.tier, l.tier),
    status = CASE 
        WHEN l.url_site IS NOT NULL AND l.url_site != '' THEN 'concluido'
        WHEN i.status = 'approved' THEN 'qualificado'
        WHEN i.status = 'raw' AND i.score_caio >= 45 THEN 'capturado'
        WHEN i.status = 'raw' THEN 'pendente'
        WHEN i.status IN ('error_retry', 'reserved') THEN 'pendente'
        ELSE l.status
    END,
    sdr_stage = CASE 
        WHEN l.url_site IS NOT NULL AND l.url_site != '' THEN 'concluido'
        WHEN i.score_caio >= 80 THEN 'hook'
        WHEN i.score_caio >= 50 THEN 'intro'
        ELSE 'pendente_wpp'
    END
FROM lead_inventory i
WHERE l.id = i.id AND l.user_id = 2;
""")
print(out)

# Verify
print("\n=== APOS SYNC ===")
out = psql("SELECT id, nome, status, score, tier, sdr_stage FROM leads WHERE user_id = 2 ORDER BY score DESC LIMIT 15;")
print(out)

# Final status counts
print("\n=== STATUS COUNTS ===")
out = psql("SELECT status, COUNT(*) as qtd FROM leads WHERE user_id = 2 GROUP BY status ORDER BY qtd DESC;")
print(out)

# Test CRM endpoint
print("\n=== TESTING /api/dashboard/crm ===")
r = subprocess.run(
    ["ssh", "root@104.243.41.166", "curl", "-s", "-H", "Authorization: Bearer", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIyIiwiZW1haWwiOiJkZXppZ3BpQGdtYWlsLmNvbSIsImV4cCI6MTc4NjEzNDI0N30.QY6VT0M1AHTumreEGoFJqCQ6HeOXkjOddB0ByvtkPok", "http://localhost:8001/api/dashboard/crm"],
    capture_output=True, text=True
)
print(r.stdout[:1000])
