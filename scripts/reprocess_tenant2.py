#!/usr/bin/env python3
import json
import os
import sys
import psycopg2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _env import load_env  # noqa: E402  — B4 DRY
load_env()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute("SELECT id, status FROM lead_inventory WHERE tenant_id = 2 AND status IN ('quality_hold', 'discarded', 'error_retry')")
leads = cur.fetchall()
print(f"Found {len(leads)} stuck leads")

cur.execute("UPDATE lead_inventory SET status = 'raw', caio_motivo = NULL, erro = NULL, locked_by = NULL, locked_until = NULL WHERE tenant_id = 2 AND status = 'quality_hold'")
reset = cur.rowcount
print(f"Reset {reset} quality_hold leads to raw")

caio_count = 0
for row in leads:
    inv_id = row[0]
    payload = json.dumps({'inventory_id': inv_id, 'force_retry': True})
    cur.execute("INSERT INTO jobs (tipo, tenant_id, payload, status, criado_em) VALUES (%s, %s, %s, %s, NOW())", ('lead_supply_caio', 2, payload, 'pending'))
    caio_count += 1

conn.commit()
print(f"Created {caio_count} Caio jobs")

cur.execute("SELECT status, COUNT(*) FROM lead_inventory WHERE tenant_id = 2 GROUP BY status ORDER BY status")
print("Tenant 2 status after reprocess:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
print("Done!")