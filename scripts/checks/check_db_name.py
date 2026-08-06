#!/usr/bin/env python3
import subprocess

pg = "52bc220171c8_fralib-postgres-1"

# List databases
r = subprocess.run(["docker", "exec", pg, "psql", "-U", "fralib_user", "-l"], capture_output=True, text=True)
print("=== DATABASES ===")
print(r.stdout)
if r.stderr:
    print("ERR:", r.stderr[:200])
