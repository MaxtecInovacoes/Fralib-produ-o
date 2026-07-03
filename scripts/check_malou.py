"""Check Lavanderia Malou lead status."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT id, lead_id, tenant_id, status, criado_em, locked_by
        FROM lead_inventory
        WHERE criado_em > NOW() - INTERVAL '30 minutes'
        AND status NOT IN ('discarded', 'raw')
        ORDER BY criado_em DESC LIMIT 10
    """)).fetchall()
    print('LEAD_INVENTORY recentes:')
    for row in r: print(' ', row)
    print('---')
    r2 = c.execute(text("""
        SELECT id, nome, sdr_stage, status, criado_em
        FROM leads
        WHERE nome ILIKE '%malou%' OR nome ILIKE '%lavanderia%' OR nome ILIKE '%manioca%'
        ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    print('LEADS table com malou/lavanderia:')
    for row in r2: print(' ', row)
