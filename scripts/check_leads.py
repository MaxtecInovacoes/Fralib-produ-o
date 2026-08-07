import psycopg2
conn = psycopg2.connect(host="postgres", port=5432, dbname="fralib_db", user="fralib_user", password="fralib_dev_password")
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
for t in cur.fetchall():
    print(t[0])
cur.execute("SELECT id, nome, status FROM leads LIMIT 5")
for l in cur.fetchall():
    print(l)
cur.execute("SELECT id, tipo, status FROM jobs WHERE status IN ('queued','running','failed') ORDER BY id DESC LIMIT 5")
for j in cur.fetchall():
    print(j)
conn.close()
