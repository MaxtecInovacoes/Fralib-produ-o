#!/usr/bin/env python3
"""Check inventory and pipeline status."""
import subprocess, json

# Get container names
result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
containers = result.stdout.strip().split("\n")
print("Containers:", containers)

# Find postgres container
pg = [c for c in containers if "postgres" in c.lower()]
print("Postgres container:", pg)

if pg:
    # Check inventory
    r = subprocess.run([
        "docker", "exec", pg[0],
        "psql", "-U", "fralib_user", "-d", "fralib",
        "-c", "SELECT id, nome, status, score_caio, tier FROM lead_inventory ORDER BY criado_em DESC LIMIT 10;"
    ], capture_output=True, text=True)
    print("\n=== INVENTORY ===")
    print(r.stdout)
    if r.stderr:
        print("ERR:", r.stderr[:200])

    # Check jobs
    r2 = subprocess.run([
        "docker", "exec", pg[0],
        "psql", "-U", "fralib_user", "-d", "fralib",
        "-c", "SELECT job_id, tipo, status, payload FROM jobs WHERE tipo LIKE '%hunter%' ORDER BY job_id DESC LIMIT 5;"
    ], capture_output=True, text=True)
    print("\n=== JOBS ===")
    print(r2.stdout)

    # Check leads
    r3 = subprocess.run([
        "docker", "exec", pg[0],
        "psql", "-U", "fralib_user", "-d", "fralib",
        "-c", "SELECT id, nome, status, score, tier, sdr_stage FROM leads ORDER BY criado_em DESC LIMIT 10;"
    ], capture_output=True, text=True)
    print("\n=== LEADS ===")
    print(r3.stdout)
