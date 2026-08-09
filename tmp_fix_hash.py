import subprocess
import bcrypt

pw = b'fralib2024'
h = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12))
hash_str = h.decode()

print(f'Generated hash: {hash_str}')
print(f'Hash length: {len(hash_str)}')

# Write SQL to file to avoid shell expansion of $ signs
sql_file = '/tmp/fix_hash.sql'
with open(sql_file, 'w') as f:
    f.write(f"UPDATE users SET password_hash='{hash_str}' WHERE email='admin@seunegociofralib.site';\n")
    f.write("SELECT id, email, LENGTH(password_hash) as hash_len FROM users WHERE email='admin@seunegociofralib.site';\n")

# Execute SQL via psql using file
result = subprocess.run([
    'docker', 'exec', '-i', '52bc220171c8_fralib-postgres-1',
    'psql', '-U', 'fralib_user', '-d', 'fralib_db', '-f', sql_file
], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print(f'STDERR: {result.stderr}')
