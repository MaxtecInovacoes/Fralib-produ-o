#!/usr/bin/env python3
"""Check pipeline job results and fix stuck jobs."""
import subprocess

pg = "52bc220171c8_fralib-postgres-1"
common = ["docker", "exec", pg, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c"]

def query(sql):
    r = subprocess.run(common + [sql], capture_output=True, text=True)
    print(r.stdout[:500])
    if r.stderr:
        print("ERR:", r.stderr[:200])

# 1. Pipeline lead status
query("SELECT id, tipo, status, worker_heartbeat, last_phase, criado_em, iniciado_em FROM jobs WHERE tipo = 'pipeline_lead' ORDER BY id DESC LIMIT 10;")

# 2. Reset stuck running
query("UPDATE jobs SET status='pending', worker_id=NULL, worker_heartbeat=NULL, iniciado_em=NULL WHERE status='running' AND worker_heartbeat < NOW() - INTERVAL '10 minutes';")

# 3. Check inventory status
query("SELECT status, COUNT(*) FROM lead_inventory GROUP BY status ORDER BY status;")

# 4. Check sites
print("\n=== SITES ON DISK ===")
r = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "root@104.243.41.166",
    "find /var/www/fralib/sites -name 'index.html' 2>/dev/null | head -10"],
    capture_output=True, text=True, timeout=10)
print(r.stdout[:300])
