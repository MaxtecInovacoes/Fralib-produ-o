#!/usr/bin/env python3
"""Check jobs table and fix lead_supply queries."""
import subprocess

C = "52bc220171c8_fralib-postgres-1"

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:300]

# Check jobs table
print("=== JOBS columns ===")
out = psql("SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs' ORDER BY ordinal_position;")
print(out)

# Check lead_supply_events columns
print("=== EVENTS columns ===")
out = psql("SELECT column_name FROM information_schema.columns WHERE table_name = 'lead_supply_events' ORDER BY ordinal_position;")
print(out)
