"""Enfileira pipeline_lead para Arena Gym Fitness e monitora execucao."""
import sys, os
from pathlib import Path

# Carregar .env ANTES de importar backend
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(str(env_path))
    print(f"[env] Carregado: {env_path}")
else:
    print(f"[env] NAO encontrado: {env_path}")
    sys.exit(1)

# Verificar DATABASE_URL
db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('[env] ERRO: DATABASE_URL nao definido no .env')
    sys.exit(1)
print(f'[env] DATABASE_URL={db_url[:60]}...')

sys.path.insert(0, 'C:/fralib')
sys.path.insert(0, 'C:/fralib/backend')
sys.path.insert(0, 'C:/fralib/backend/core')

from backend.core.database import inicializar_database, SessionLocal, engine
from backend.core.job_queue import enqueue
from sqlalchemy import text
import json, time

inicializar_database()

LEAD_ID = '38ffd3fb-c9a0-498c-9abc-c8a4e8f24853'

# Verificar lead
with engine.connect() as conn:
    r = conn.execute(text("SELECT id, nome, status, url_site FROM leads WHERE id = :lid"), {"lid": LEAD_ID})
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
        "lead_id": LEAD_ID,
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
    print("Aguardando worker processar (90s)...")
    time.sleep(90)

    # Checar status do job
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, tipo, status, attempts, erro FROM jobs WHERE id = :jid"), {"jid": job_id})
        row = r.fetchone()
        if row:
            print(f"Job: tipo={row[1]} status={row[2]} attempts={row[3]} erro={row[4]}")

    # Checar lead final
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, nome, status, url_site, atualizado_em FROM leads WHERE id = :lid"), {"lid": LEAD_ID})
        row = r.fetchone()
        if row:
            print(f"Lead final: {row[1]} | status={row[2]} | url_site={row[3]} | atualizado={row[4]}")
else:
    print("Job ja existia (idempotency)")
