import os
import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
from sqlalchemy import create_engine, text
eng = create_engine(os.environ['DATABASE_URL'])
with eng.connect() as c:
    # 1. Listar tenants e ver qual ainda ta conectado
    print('=== Tenants ===')
    r = c.execute(text("SELECT id, email, plano, status FROM users WHERE id IN (1, 2, 51, 52) ORDER BY id"))
    for row in r.fetchall():
        print(f'  {row}')

    # 2. User 2 leads ativos
    print()
    print('=== User 2 leads ativos ===')
    r = c.execute(text("""
        SELECT id, nome, telefone, sdr_stage, status, opt_out_pending
        FROM leads WHERE user_id = 2 AND status = 'concluido'
        ORDER BY atualizado_em DESC LIMIT 10
    """))
    for row in r.fetchall():
        print(f'  {row}')

    # 3. User 52 leads ativos (pamela)
    print()
    print('=== User 52 leads ativos (pamela) ===')
    r = c.execute(text("""
        SELECT id, nome, telefone, sdr_stage, status
        FROM leads WHERE user_id = 52 AND status = 'concluido'
        ORDER BY atualizado_em DESC LIMIT 10
    """))
    for row in r.fetchall():
        print(f'  {row}')

    # 4. Msgs do user 2 nas ultimas 6h (manda hoje)
    print()
    print('=== User 2 msgs saida nas ultimas 6h (HOJE) ===')
    r = c.execute(text("""
        SELECT EXTRACT(HOUR FROM criado_em) as hora, COUNT(*) as total
        FROM interacoes
        WHERE direcao = 'saida'
          AND user_id = 2
          AND criado_em > (CURRENT_TIMESTAMP - INTERVAL '6 hours')
        GROUP BY hora ORDER BY hora DESC
    """))
    for row in r.fetchall():
        print(f'  {row}')

    # 5. Status wpp do user 2
    print()
    print('=== Tentou conectar user 2 ultimas msgs? ===')
    r = c.execute(text("""
        SELECT i.criado_em, i.direcao, substring(i.mensagem, 1, 80)
        FROM interacoes i
        WHERE i.user_id = 2
          AND i.criado_em > (CURRENT_TIMESTAMP - INTERVAL '2 hours')
        ORDER BY i.criado_em DESC LIMIT 15
    """))
    for row in r.fetchall():
        print(f'  {row}')