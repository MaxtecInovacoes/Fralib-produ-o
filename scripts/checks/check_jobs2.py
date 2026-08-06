#!/usr/bin/env python3
import subprocess, json

pg = "52bc220171c8_fralib-postgres-1"
common = ["docker", "exec", pg, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c"]

def query(sql, label):
    r = subprocess.run(common + [sql], capture_output=True, text=True)
    print(f"\n=== {label} ===")
    print(r.stdout[:2000])
    if r.stderr:
        print("ERR:", r.stderr[:300])

# Jobs schema
query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'jobs' ORDER BY ordinal_position;", "JOBS SCHEMA")

# Recent jobs
query("SELECT run_id, tipo, status, payload, criado_em FROM jobs ORDER BY run_id DESC LIMIT 15;", "JOBS RECENTES")

# Check pending/failed
query("SELECT tipo, status, COUNT(*) FROM jobs GROUP BY tipo, status ORDER BY tipo, status;", "JOBS POR STATUS")
