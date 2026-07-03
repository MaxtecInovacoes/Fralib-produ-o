"""Find good test lead."""
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text("""
        SELECT l.id, l.nome, l.cidade, l.segmento, l.telefone
        FROM leads l
        WHERE l.telefone IS NOT NULL AND l.telefone != ''
        ORDER BY l.criado_em DESC LIMIT 5
    """)).fetchall()
    print('LEADS recentes com telefone:')
    for row in r: print(' ', row)
