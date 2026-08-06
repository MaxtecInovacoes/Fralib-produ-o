#!/usr/bin/env python3
import subprocess
from passlib.hash import bcrypt

C = "52bc220171c8_fralib-postgres-1"
NEW_HASH = bcrypt.hash("admin123")

def psql(q):
    r = subprocess.run(
        ["docker", "exec", C, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", q],
        capture_output=True, text=True
    )
    return r.stdout if r.returncode == 0 else "ERR: " + r.stderr[:300]

# Set password hash
print("Setting password...")
print(psql(f"UPDATE users SET password_hash = '{NEW_HASH}', senha_hash = '{NEW_HASH}' WHERE id = 2;"))
print("Verifying:")
print(psql("SELECT id, email, LEFT(password_hash, 30) as hash FROM users WHERE id = 2;"))
