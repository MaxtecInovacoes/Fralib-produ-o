import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT u.id, u.email, u.nome,
               COALESCE(u.telefone, '') as telefone,
               COALESCE(u.nicho, '') as nicho,
               COALESCE(EXTRACT(DAY FROM (NOW() - u.criado_em))::int, 0) as dias_cadastro
        FROM users u
        WHERE u.id = ANY(:ids)
    """), {"ids": [50, 55, 53]}).fetchall()
    for r in rows:
        print('ID:', r[0], '| Email:', r[1], '| Nicho:', r[4], '| Dias:', r[5])