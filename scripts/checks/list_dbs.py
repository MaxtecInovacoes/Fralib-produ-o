#!/usr/bin/env python3
import subprocess

pg = "52bc220171c8_fralib-postgres-1"

r = subprocess.run(["docker", "exec", pg, "psql", "-U", "fralib_user", "-l"], capture_output=True, text=True)
print("=== DATABASES ===")
print(r.stdout)
if r.stderr:
    print("ERR:", r.stderr[:300])

# Also check env vars from compose
r2 = subprocess.run(["docker", "exec", pg, "env"], capture_output=True, text=True)
for line in r2.stdout.split("\n"):
    if "DB" in line.upper() or "POSTGRES" in line.upper() or "DATABASE" in line.upper():
        print("ENV:", line)
