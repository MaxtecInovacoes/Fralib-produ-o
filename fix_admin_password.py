"""Fix admin password hash - runs inside fralib-app container."""
import sys
sys.path.insert(0, '/app')
from backend.shared.password import hash_password, verify_password
from sqlalchemy import create_engine, text

PASSWORD = "1763kovQ123"
EMAIL = "dezigpi@gmail.com"

new_hash = hash_password(PASSWORD)
print(f"Generated hash: {new_hash}")
print(f"Hash length: {len(new_hash)}")
print(f"Verify test: {verify_password(PASSWORD, new_hash)}")

engine = create_engine("postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db")
with engine.connect() as conn:
    # Update
    result = conn.execute(
        text("UPDATE users SET password_hash=:h WHERE lower(email)=:e RETURNING id, length(password_hash)"),
        {"h": new_hash, "e": EMAIL}
    )
    conn.commit()
    row = result.fetchone()
    print(f"Updated user id={row[0]}, hash_length={row[1]}")

    # Verify login would work
    stored = conn.execute(
        text("SELECT password_hash FROM users WHERE lower(email)=:e"),
        {"e": EMAIL}
    ).fetchone()
    final_verify = verify_password(PASSWORD, stored[0])
    print(f"Final verify against DB: {final_verify}")
    print("FIXED!" if final_verify else "STILL BROKEN")
