"""Check job 156782 final state."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT id, status, left(last_error, 250), concluido_em, criado_em, last_phase
        FROM jobs WHERE id=156782
    """)).fetchall()
    print('JOB 156782:')
    for row in r: print(' ', row)
    print('---')
    r2 = c.execute(text("""
        SELECT id, status, left(last_error, 200), criado_em, concluido_em
        FROM jobs WHERE tipo='pipeline_lead' AND criado_em > NOW() - INTERVAL '5 minutes'
        ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    print('PIPELINE_LEAD ultimas 5min:')
    for row in r2: print(' ', row)
