import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print('=== STATUS DO DRIP ATUAL ===')
    rows = conn.execute(text("""
        SELECT status, COUNT(*)
        FROM outreach_attempts
        WHERE campaign = 'reativacao_drip_v1_2026_06_26'
        GROUP BY status
    """)).fetchall()
    for r in rows:
        print('  ' + str(r[0]) + ': ' + str(r[1]))

    print()
    print('=== USUARIOS QUE NUNCA RECEBERAM NENHUM STEP ===')
    rows = conn.execute(text("""
        SELECT u.id, u.email, u.nome, u.criado_em::date, u.plano
        FROM users u
        WHERE u.role != 'superadmin'
        AND u.email_confirmado = true
        AND u.id NOT IN (
            SELECT user_id FROM outreach_attempts
            WHERE campaign = 'reativacao_drip_v1_2026_06_26'
        )
        LIMIT 15
    """)).fetchall()
    for r in rows:
        print('  #' + str(r[0]) + ' | ' + str(r[1])[:35] + ' | ' + str(r[3]) + ' | ' + str(r[4]))

    print()
    print('=== TOTAL DE USUARIOS CONFIRMADOS ===')
    row = conn.execute(text("""
        SELECT COUNT(*) FROM users
        WHERE role != 'superadmin' AND email_confirmado = true
    """)).fetchone()
    print('  Total:', row[0])
