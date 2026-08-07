import psycopg2, requests, json

# Connect to DB
conn = psycopg2.connect(host="postgres", port=5432, dbname="fralib_db", user="fralib_user", password="fralib_dev_password")
cur = conn.cursor()

# Find a lead with status not finalized
cur.execute("SELECT id, nome, segmento, cidade, status FROM leads ORDER BY created_at DESC LIMIT 5")
leads = cur.fetchall()
print("=== Leads ===")
for l in leads:
    print(l)

# Find jobs
cur.execute("SELECT id, tipo, status, attempts, last_error FROM jobs WHERE status IN ('queued','running','failed') ORDER BY id DESC LIMIT 5")
jobs = cur.fetchall()
print("=== Jobs ===")
for j in jobs:
    print(j)

conn.close()

# Try to trigger pipeline via API (superadmin)
# First get auth token
login = requests.post("http://localhost:8000/api/auth/login", json={"email": "test@test.com", "password": "test"})
if login.status_code == 200:
    token = login.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if leads:
        lead_id = leads[0][0]
        print(f"\n=== Triggering reprocess for lead {lead_id} ===")
        r = requests.post(f"http://localhost:8000/api/pipeline/reprocessar/{lead_id}", headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
else:
    print(f"Login failed: {login.status_code} {login.text[:200]}")
