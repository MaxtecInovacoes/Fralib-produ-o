#!/usr/bin/env python3
import subprocess

pg = "52bc220171c8_fralib-postgres-1"
common = ["docker", "exec", pg, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c"]

def query(sql, label):
    r = subprocess.run(common + [sql], capture_output=True, text=True)
    print(f"\n=== {label} ===")
    print(r.stdout[:1500])
    if r.stderr:
        print("ERR:", r.stderr[:300])

# Jobs schema
query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'jobs' ORDER BY ordinal_position;", "JOBS SCHEMA")

# Recent jobs with run_id
query("SELECT run_id, tipo, status, payload FROM jobs ORDER BY run_id DESC LIMIT 10;", "JOBS RECENTES")

# Production/inventory jobs
query("SELECT run_id, tipo, status, payload FROM jobs WHERE tipo LIKE '%produc%' OR tipo LIKE '%tick%' OR tipo LIKE '%site%' ORDER BY run_id DESC LIMIT 10;", "PRODUCTION JOBS")
