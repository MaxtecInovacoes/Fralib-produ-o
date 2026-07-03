"""Check jobs after tick 156643."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT id, tipo, status, left(last_error, 200), criado_em
        FROM jobs WHERE id >= 156643 ORDER BY id DESC LIMIT 5
    """)).fetchall()
    print('JOBS apos tick 156643:')
    for row in r: print(' ', row)
    print('---')
    r2 = c.execute(text("""
        SELECT id, tipo, status, left(last_error, 300), criado_em, concluido_em
        FROM jobs WHERE tipo='pipeline_lead' AND criado_em > NOW() - INTERVAL '10 minutes'
        ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    print('PIPELINE_LEAD ultimas 10min:')
    for row in r2: print(' ', row)
