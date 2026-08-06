#!/usr/bin/env python3
"""Check lead_supply_config columns and fix endpoint."""
import subprocess

C = "52bc220171c8_fralib-postgres-1"

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:300]

# Check columns
print("=== lead_supply_config columns ===")
out = psql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'lead_supply_config' ORDER BY ordinal_position;")
print(out)

print("=== lead_supply_events columns ===")
out = psql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'lead_supply_events' ORDER BY ordinal_position;")
print(out)

print("=== lead_inventory columns ===")
out = psql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'lead_inventory' ORDER BY ordinal_position;")
print(out)

# Check config data
print("=== config data ===")
out = psql("SELECT * FROM lead_supply_config LIMIT 1;")
print(out)
