#!/usr/bin/env python3
import subprocess

C = "52bc220171c8_fralib-postgres-1"

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:300]

# Check users table columns
print("=== USERS columns ===")
print(psql("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position;"))

# Check the actual user
print("=== USER id=2 ===")
print(psql("SELECT id, email, tenant_id FROM users WHERE id = 2;"))

# Check if there's a password field
print("=== Password check ===")
print(psql("SELECT id, email, LEFT(senha_hash, 20) as hash_prefix FROM users WHERE id = 2;"))
