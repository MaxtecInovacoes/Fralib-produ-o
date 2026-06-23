import subprocess
sql = "SELECT nome, site_url FROM leads WHERE user_id = 2 AND site_url IS NOT NULL AND site_url != '' LIMIT 1"
r = subprocess.run(
    ["ssh", "root@187.77.37.72", "PGPASSWORD=fralib2024 psql -h localhost -p 5433 -U postgres -d fralib_db -c", sql],
    capture_output=True, text=True
)
print(r.stdout)