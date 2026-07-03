"""Force pipeline_lead on a valid lead_id from lead_inventory."""
from backend.core.database import SessionLocal, engine
from sqlalchemy import text
import json
import uuid

db = SessionLocal()
# Acha lead_inventory com lead_id NOT NULL
r = db.execute(text("""
    SELECT li.id, li.lead_id, li.tenant_id, l.nome, l.cidade, l.segmento, l.telefone
    FROM lead_inventory li
    LEFT JOIN leads l ON l.id = li.lead_id
    WHERE li.lead_id IS NOT NULL
    AND l.id IS NOT NULL
    ORDER BY li.criado_em DESC LIMIT 1
""")).fetchone()
print('found lead:', r)
if r:
    inv_id, lead_id, tenant_id, nome, cidade, segmento, telefone = r
    print(f'  inv={inv_id} lead={lead_id} tenant={tenant_id}')
    print(f'  nome={nome} cidade={cidade} segmento={segmento} tel={telefone}')
    # Enqueue pipeline_lead job direto
    job_id = db.execute(text("""
        INSERT INTO jobs (tipo, payload, tenant_id, status, max_attempts, criado_em)
        VALUES ('pipeline_lead', CAST(:payload AS jsonb), :tid, 'pending', 3, NOW())
        RETURNING id
    """), {
        'payload': json.dumps({
            'lead_id': lead_id,
            'inventory_id': inv_id,
            'tenant_id': tenant_id,
            'reason': 'manual-force-test-after-fix',
            '_run_id': str(uuid.uuid4()),
        }),
        'tid': tenant_id,
    }).fetchone()[0]
    db.commit()
    print(f'ENQUEUED pipeline_lead job_id={job_id}')

db.close()
