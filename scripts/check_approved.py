"""Check approved leads recent."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT lead_id, tenant_id, status, criado_em
        FROM lead_inventory
        WHERE status='approved'
        AND criado_em > NOW() - INTERVAL '10 minutes'
        ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    print('LEADS APROVADOS ultimas 10min:')
    for row in r: print(' ', row)
    print('---')
    r2 = c.execute(text("""
        SELECT id, tipo, status, left(last_error, 200), criado_em, concluido_em
        FROM jobs WHERE tipo='pipeline_lead' ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    print('ULTIMOS pipeline_lead:')
    for row in r2: print(' ', row)
