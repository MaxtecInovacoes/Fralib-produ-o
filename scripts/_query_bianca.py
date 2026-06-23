import subprocess
sql = "SELECT id, user_id, nome, segmento, sdr_stage, status FROM leads WHERE nome ILIKE '%bianca%' ORDER BY id DESC LIMIT 5"
r = subprocess.run(
    ["ssh", "root@187.77.37.72", "PGPASSWORD=fralib2024 psql -h localhost -p 5433 -U postgres -d fralib_db -c", sql],
    capture_output=True, text=True
)
print(r.stdout)
print(r.stderr)