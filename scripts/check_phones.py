import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
from _env import load_env  # noqa: E402  — B4 DRY
load_env()
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print('=== USUARIOS COM TELEFONE ===')
    rows = conn.execute(text("""
        SELECT u.id, u.email, u.nome, COALESCE(u.telefone, '') as tel, u.plano, u.criado_em::date
        FROM users u
        WHERE COALESCE(u.telefone, '') != ''
        ORDER BY u.criado_em DESC
        LIMIT 20
    """)).fetchall()
    for r in rows:
        print('  #' + str(r[0]) + ' | ' + str(r[1])[:35] + ' | ' + str(r[3]) + ' | ' + str(r[4]))

    print()
    print('=== TOTAL COM TELEFONE ===')
    row = conn.execute(text("""
        SELECT COUNT(*) FROM users WHERE COALESCE(telefone, '') != ''
    """)).fetchone()
    print('  Total:', row[0])

    print()
    print('=== ULTIMOS 5 CADASTRADOS (com ou sem tel) ===')
    rows = conn.execute(text("""
        SELECT id, email, COALESCE(telefone, '') as tel, criado_em::date
        FROM users ORDER BY criado_em DESC LIMIT 5
    """)).fetchall()
    for r in rows:
        print('  #' + str(r[0]) + ' | ' + str(r[1]) + ' | tel=' + str(r[2]))