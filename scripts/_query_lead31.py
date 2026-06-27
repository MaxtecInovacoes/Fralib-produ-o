# -*- coding: utf-8 -*-
import os
import sys
import psycopg2

os.environ['PGCLIENTENCODING'] = 'UTF8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    # Conectar usando parâmetros separados em vez de DSN (evita decodificação do DSN como UTF-8)
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="fralib_db",
        user="postgres",
        password="fralib2024",
    )
    cur = conn.cursor()

    def run(label, sql, params=None):
        print()
        print("=" * 100)
        print(label)
        print("=" * 100)
        cur.execute(sql, params or ())
        if cur.description:
            cols = [d[0] for d in cur.description]
            print(" | ".join(cols))
            print("-" * 100)
            rows = cur.fetchall()
            if not rows:
                print("(sem resultados)")
            for row in rows:
                print(" | ".join(str(c)[:80] if c is not None else "NULL" for c in row))
            return rows
        return None

    # 1) leads com user_id=31, score=80 ou carolina/ragugnetti
    run(
        "QUERY 1: leads.user_id=31 OR score=80 OR nome LIKE '%carolina%' OR '%ragugnetti%'",
        """
        SELECT id, user_id, nome, cidade, segmento, score, tier, status,
               criado_em, site_url, url_site
        FROM leads
        WHERE user_id = 31
           OR score = 80
           OR LOWER(nome) LIKE %s
           OR LOWER(nome) LIKE %s
        ORDER BY criado_em DESC
        """,
        ('%carolina%', '%ragugnetti%'),
    )

    # 2) contagem por user_id (pra ver se 31 tem muitos)
    run(
        "QUERY 2: contagem de leads por user_id (top 10)",
        """
        SELECT user_id, COUNT(*) AS total, MAX(criado_em) AS ultimo
        FROM leads
        GROUP BY user_id
        ORDER BY total DESC
        LIMIT 10
        """,
    )

    # 3) ultimos 10 leads no total (contexto)
    run(
        "QUERY 3: ultimos 10 leads (contexto geral)",
        """
        SELECT id, user_id, nome, score, tier, status, criado_em
        FROM leads
        ORDER BY criado_em DESC
        LIMIT 10
        """,
    )

    # 4) estrutura da tabela leads
    run(
        "QUERY 4: estrutura tabela leads",
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'leads'
        ORDER BY ordinal_position
        """,
    )

    # 5) tabelas de auditoria/ledger/historico
    run(
        "QUERY 5: tabelas com ledger/audit/log/histor/agent",
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
          AND (table_name ILIKE '%ledger%'
               OR table_name ILIKE '%audit%'
               OR table_name ILIKE '%log%'
               OR table_name ILIKE '%approval%'
               OR table_name ILIKE '%histor%'
               OR table_name ILIKE '%agent%'
               OR table_name ILIKE '%pipeline%')
        ORDER BY table_name
        """,
    )

    cur.close()
    conn.close()
    print()
    print("OK - conexao encerrada limpa")

except Exception as e:
    import traceback
    print("ERRO:", type(e).__name__, "-", e)
    traceback.print_exc()