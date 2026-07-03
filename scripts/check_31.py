"""Check tenant 31 leads."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT lead_id, tenant_id, status, locked_by, locked_until, criado_em
        FROM lead_inventory
        WHERE tenant_id=31 AND criado_em > NOW() - INTERVAL '15 minutes'
        ORDER BY criado_em DESC LIMIT 10
    """)).fetchall()
    print('LEADS tenant=31 15min:')
    for row in r: print(' ', row)
    print('---')
    r2 = c.execute(text("""
        SELECT id, tipo, status, payload
        FROM jobs WHERE tenant_id=31 AND criado_em > NOW() - INTERVAL '15 minutes'
        AND tipo IN ('lead_production_tick', 'pipeline_lead')
        ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    print('JOBS tenant=31:')
    for row in r2: print(' ', row)
