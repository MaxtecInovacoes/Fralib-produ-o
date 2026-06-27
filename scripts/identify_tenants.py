"""Identifica tenants correspondentes aos números dos prints."""
import sys
import os
sys.path.insert(0, "/root/fralib/backend")
sys.path.insert(0, "/root/fralib")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:fralib2024@localhost:5433/fralib_db")

from sqlalchemy import create_engine, text

phones = [
    ("+55 11 95604-8592", "Nutricionista Jaque (opt-out loop)"),
    ("Rafael Victor Nutricionista", "Rafael (3 msgs mídia)"),
    ("DoctorFit Saúde", "DoctorFit (3 msgs gatekeeper)"),
    ("+55 41 9953-8159", "Curitiba Fitness (2 msgs retomar)"),
]

eng = create_engine(os.environ["DATABASE_URL"])
with eng.connect() as c:
    for tel_or_name, desc in phones:
        # tentar por telefone
        digits = ''.join(filter(str.isdigit, tel_or_name))
        r = c.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.user_id, l.sdr_stage,
                   u.email, u.plano
            FROM leads l
            LEFT JOIN users u ON u.id = l.user_id
            WHERE l.telefone LIKE :pattern
               OR l.whatsapp LIKE :pattern
               OR LOWER(l.nome) LIKE LOWER(:name)
            LIMIT 3
        """), {"pattern": f"%{digits[-11:]}%", "name": f"%{tel_or_name.split()[0]}%"})
        rows = r.fetchall()
        print(f"\n=== {desc} ===")
        if rows:
            for row in rows:
                print(f"  lead_id={row[0]} nome='{row[1]}' tel={row[2]} jid={row[3]} user_id={row[4]} stage={row[5]} email={row[6]} plano={row[7]}")
        else:
            print("  NAO ENCONTRADO")

    # Tambem: ultimas 20 duplicatas (interacoes com mesmo lead em segundos)
    print("\n=== DUPLICATAS ULTIMAS 24H ===")
    r = c.execute(text("""
        SELECT lead_id, COUNT(*) as cnt, MIN(criado_em) as primeira, MAX(criado_em) as ultima
        FROM interacoes
        WHERE criado_em > NOW() - INTERVAL '24 hours'
          AND direcao = 'saida'
        GROUP BY lead_id
        HAVING COUNT(*) >= 3
        ORDER BY cnt DESC
        LIMIT 10
    """))
    for row in r.fetchall():
        print(f"  lead={row[0]} count={row[1]} primeira={row[2]} ultima={row[3]}")