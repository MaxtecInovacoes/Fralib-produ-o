#!/usr/bin/env python3
import subprocess

pg = "52bc220171c8_fralib-postgres-1"
db = "fralib_db"
common = ["docker", "exec", pg, "psql", "-U", "fralib_user", "-d", db, "-c"]

def query(sql, label):
    r = subprocess.run(common + [sql], capture_output=True, text=True)
    print(f"\n=== {label} ===")
    print(r.stdout[:1000])
    if r.stderr:
        print("ERR:", r.stderr[:300])

# Inventory
query("SELECT id, nome, status, score_caio, tier FROM lead_inventory ORDER BY criado_em DESC LIMIT 10;", "INVENTORY")

# Recent jobs
query("SELECT job_id, tipo, status, payload FROM jobs ORDER BY job_id DESC LIMIT 10;", "JOBS RECENTES")

# Leads
query("SELECT id, nome, status, score, tier, sdr_stage FROM leads ORDER BY criado_em DESC LIMIT 10;", "LEADS")

# Lead supply config
query("SELECT * FROM lead_supply_config;", "CONFIG")
