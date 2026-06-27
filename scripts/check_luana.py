import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
eng = create_engine(os.environ["DATABASE_URL"])
with eng.connect() as c:
    r = c.execute(text("""
        SELECT criado_em, direcao, substring(mensagem, 1, 100), id
        FROM interacoes
        WHERE lead_id IN (
            SELECT id FROM leads WHERE telefone LIKE '%98875-3688%'
        )
        AND criado_em >= '2026-06-26 20:52:00'
        ORDER BY criado_em ASC
    """))
    print('=== MSGS LUANA apos 20:52 ===')
    found = False
    for row in r.fetchall():
        found = True
        print(f'{row[0]} | {row[1]:7} | {row[3]} | {row[2]}')
    if not found:
        print('  NENHUMA MSG desde 20:52 - lead ABANDONADO')
    r = c.execute(text("""
        SELECT nome, sdr_stage, opt_out_pending, status
        FROM leads WHERE telefone LIKE '%98875-3688%'
    """))
    print('\n=== STATUS ATUAL ===')
    for row in r.fetchall():
        print(f'  {row}')