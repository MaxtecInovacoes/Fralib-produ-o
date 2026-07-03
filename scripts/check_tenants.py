"""Check lead_inventory and jobs for tenants 2/31/51."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT lead_id, status, left(erro, 100), locked_by, atualizado_em
        FROM lead_inventory
        WHERE tenant_id IN (31, 51, 2)
        AND status IN ('approved', 'processing', 'error_retry', 'failed', 'discarded')
        ORDER BY atualizado_em DESC LIMIT 10
    """)).fetchall()
    print('LEAD_INVENTORY 31/51/2:')
    for row in r: print(' ', row)
    print('---')
    r2 = c.execute(text("""
        SELECT tipo, status, COUNT(*) FROM jobs
        WHERE criado_em > NOW() - INTERVAL '5 minutes' AND tenant_id IN (31, 51, 2)
        GROUP BY tipo, status
    """)).fetchall()
    print('JOBS 31/51/2 ultimas 5min:')
    for row in r2: print(' ', row)
    print('---')
    r3 = c.execute(text("""
        SELECT tipo, status, COUNT(*) FROM jobs
        WHERE criado_em > NOW() - INTERVAL '15 minutes'
        GROUP BY tipo, status ORDER BY tipo
    """)).fetchall()
    print('TODOS JOBS ultimas 15min:')
    for row in r3: print(' ', row)
