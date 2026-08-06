#!/usr/bin/env python3
"""Check schema using file-based SQL."""
import subprocess

C = "52bc220171c8_fralib-postgres-1"

queries = [
    ("jobs columns", "SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs' ORDER BY ordinal_position;"),
    ("events columns", "SELECT column_name FROM information_schema.columns WHERE table_name = 'lead_supply_events' ORDER BY ordinal_position;"),
    ("config without id", "SELECT tenant_id, segmentos, cidades FROM lead_supply_config LIMIT 1;"),
    ("events sample", "SELECT * FROM lead_supply_events LIMIT 1;"),
]

for label, sql in queries:
    # Write SQL to temp file
    with open("/tmp/schema_check.sql", "w") as f:
        f.write(sql + "\n")
    r = subprocess.run(
        ["docker", "exec", "-i", C, "psql", "-U", "fralib_user", "-d", "fralib_db"],
        stdin=open("/tmp/schema_check.sql"), capture_output=True, text=True
    )
    out = r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:200]
    print(f"=== {label} ===")
    print(out)
