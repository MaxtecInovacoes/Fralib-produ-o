"""Check jobs after retry."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT tipo, status, COUNT(*) FROM jobs
        WHERE criado_em > NOW() - INTERVAL '5 minutes'
        GROUP BY tipo, status ORDER BY tipo, status
    """)).fetchall()
    print('JOBS ultimas 5min:')
    for row in r: print(' ', row)
    print('---PIPELINE_LEAD jobs 5min---')
    r2 = c.execute(text("""
        SELECT id, status, left(last_error, 200), concluido_em
        FROM jobs WHERE tipo='pipeline_lead' AND criado_em > NOW() - INTERVAL '5 minutes'
        ORDER BY criado_em DESC LIMIT 10
    """)).fetchall()
    for row in r2: print(' ', row)
    print('---PIPELINE_LEAD ultimos 15min---')
    r3 = c.execute(text("""
        SELECT id, status, left(last_error, 200), concluido_em, criado_em
        FROM jobs WHERE tipo='pipeline_lead' AND criado_em > NOW() - INTERVAL '15 minutes'
        ORDER BY criado_em DESC LIMIT 10
    """)).fetchall()
    for row in r3: print(' ', row)
