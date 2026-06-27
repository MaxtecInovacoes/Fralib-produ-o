import os
import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
from sqlalchemy import create_engine, text
eng = create_engine(os.environ['DATABASE_URL'])
with eng.connect() as c:
    # Ver user 52
    r = c.execute(text("SELECT id, email, plano, status FROM users WHERE id IN (51, 52)"))
    for row in r.fetchall():
        print(f'  {row}')

    # Top 5 users por msgs enviadas em 24h
    print()
    print('Top 5 users por msgs saida em 24h:')
    r = c.execute(text("""
        SELECT user_id, COUNT(*) as total
        FROM interacoes
        WHERE direcao = 'saida' AND criado_em > (CURRENT_TIMESTAMP - INTERVAL '24 hours')
        GROUP BY user_id ORDER BY total DESC LIMIT 5
    """))
    for row in r.fetchall():
        print(f'  user_id={row[0]}: {row[1]} msgs')

    # Top 5 tenants
    print()
    print('Tenants com mais saidas em 24h:')
    r = c.execute(text("""
        SELECT l.user_id, u.email, COUNT(*) as total
        FROM interacoes i
        JOIN leads l ON l.id = i.lead_id
        JOIN users u ON u.id = l.user_id
        WHERE i.direcao = 'saida' AND i.criado_em > (CURRENT_TIMESTAMP - INTERVAL '24 hours')
        GROUP BY l.user_id, u.email ORDER BY total DESC LIMIT 10
    """))
    for row in r.fetchall():
        print(f'  user_id={row[0]} ({row[1]}): {row[2]} msgs')