"""Enfileira pipeline_lead para Arena Gym Fitness e monitora execucao."""
import sys, os
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/backend/core')

from backend.core.database import inicializar_database, SessionLocal, engine
from backend.core.job_queue import enqueue
from sqlalchemy import text
import json, time

inicializar_database()

# Verificar lead
with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT id, nome, status, url_site FROM leads
        WHERE id = '38ffd3fb-c9a0-498c-9abc-c8a4e8f24853'
    """))
    row = r.fetchone()
    if row:
        print(f"Lead: {row[1]} | status={row[2]} | url_site={row[3]}")
    else:
        print("Lead NAO encontrado!")
        sys.exit(1)

# Enfileirar job
db = SessionLocal()
job_id = enqueue(
    db,
    tipo="pipeline_lead",
    payload={
        "lead_id": "38ffd3fb-c9a0-498c-9abc-c8a4e8f24853",
        "tenant_id": 2,
        "segmento": "academia",
        "cidade": "Campina Grande Do Sul",
    },
    tenant_id=2,
    max_attempts=3,
    idempotency_key="pipeline-arena-gym-smoke",
    run_id="smoke-arena-real",
)
db.close()

if job_id:
    print(f"Job enfileirado: job_id={job_id}")
    print("Aguardando worker processar (60s)...")
    time.sleep(60)

    # Checar status do job
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT id, tipo, status, attempts, erro, payload
            FROM jobs WHERE id = :jid
        """), {"jid": job_id})
        row = r.fetchone()
        if row:
            print(f"\nJob status: tipo={row[1]} status={row[2]} attempts={row[3]}")
            print(f"Erro: {row[4]}")
            payload = json.loads(row[5]) if row[5] else {}
            print(f"Payload: {json.dumps(payload, indent=2)[:500]}")

    # Checar leads
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT id, nome, status, url_site, atualizado_em
            FROM leads WHERE id = '38ffd3fb-c9a0-498c-9abc-c8a4e8f24853'
        """))
        row = r.fetchone()
        if row:
            print(f"\nLead apos pipeline: {row[1]} | status={row[2]} | url_site={row[3]}")
            print(f"Atualizado em: {row[4]}")
else:
    print("Job ja existia (idempotency). Verificando status...")
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT id, tipo, status, attempts, erro, created_at
            FROM jobs
            WHERE idempotency_key = 'pipeline-arena-gym-smoke'
            ORDER BY id DESC LIMIT 1
        """))
        row = r.fetchone()
        if row:
            print(f"Job existente: id={row[0]} tipo={row[1]} status={row[2]} attempts={row[3]} erro={row[4]} created={row[5]}")

# Checar diretorio de sites
import os
for path in ['/opt/fralib/data/sites', '/app/data/sites', 'sites', '/opt/fralib/sites']:
    if os.path.exists(path):
        items = os.listdir(path)
        print(f"\n{path}: {len(items)} items")
        for item in items[:5]:
            full = os.path.join(path, item)
            if os.path.isdir(full):
                sub = os.listdir(full)
                print(f"  {item}/ ({len(sub)} items)")
                for s in sub[:3]:
                    print(f"    {s}")
            else:
                print(f"  {item}")
    else:
        print(f"\n{path}: NOT FOUND")
