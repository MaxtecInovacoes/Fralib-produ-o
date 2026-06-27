# -*- coding: utf-8 -*-
"""Conecta via libpq via ctypes (workaround para bug do psycopg2 com paths não-ASCII)."""
import os
import sys
import ctypes
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

libpq_path = r"C:\Users\JESUS TE AMA\AppData\Local\Programs\Python\Python312\Lib\site-packages\psycopg2_binary.libs\libpq-59fb91041b8033400b68b6f333423fb2.dll"
libpq = ctypes.CDLL(libpq_path)

# Tipos
PGconn = ctypes.c_void_p
PGresult = ctypes.c_void_p

libpq.PQconnectdb.argtypes = [ctypes.c_char_p]
libpq.PQconnectdb.restype = PGconn

libpq.PQstatus.argtypes = [PGconn]
libpq.PQstatus.restype = ctypes.c_int

libpq.PQerrorMessage.argtypes = [PGconn]
libpq.PQerrorMessage.restype = ctypes.c_char_p

libpq.PQexec.argtypes = [PGconn, ctypes.c_char_p]
libpq.PQexec.restype = PGresult

libpq.PQresultStatus.argtypes = [PGresult]
libpq.PQresultStatus.restype = ctypes.c_int

libpq.PQntuples.argtypes = [PGresult]
libpq.PQntuples.restype = ctypes.c_int

libpq.PQnfields.argtypes = [PGresult]
libpq.PQnfields.restype = ctypes.c_int

libpq.PQgetvalue.argtypes = [PGresult, ctypes.c_int, ctypes.c_int]
libpq.PQgetvalue.restype = ctypes.c_char_p

libpq.PQfname.argtypes = [PGresult, ctypes.c_int]
libpq.PQfname.restype = ctypes.c_char_p

libpq.PQclear.argtypes = [PGresult]
libpq.PQclear.restype = None

libpq.PQfinish.argtypes = [PGconn]
libpq.PQfinish.restype = None

# Conectar
conninfo = b"host=localhost port=5432 dbname=fralib_db user=postgres password=fralib2024 connect_timeout=5"
pgconn = libpq.PQconnectdb(conninfo)
if not pgconn:
    print("PQconnectdb retornou None")
    sys.exit(1)

status = libpq.PQstatus(pgconn)
err = libpq.PQerrorMessage(pgconn) or b""
err_str = err.decode("utf-8", errors="replace") if err else ""
print(f"status={status} (0=OK) err={err_str[:300]}")

if status != 0:
    print("Conexao falhou")
    libpq.PQfinish(pgconn)
    sys.exit(1)


def run(label, sql):
    print()
    print("=" * 80)
    print(label)
    print("=" * 80)
    res = libpq.PQexec(pgconn, sql.encode("utf-8"))
    rstatus = libpq.PQresultStatus(res)
    if rstatus != 1:  # PGRES_TUPLES_OK = 1, PGRES_COMMAND_OK = 2 (for DDL)
        err_msg = libpq.PQerrorMessage(pgconn) or b""
        print(f"ERRO status={rstatus}: {err_msg.decode('utf-8', errors='replace')[:300]}")
        libpq.PQclear(res)
        return
    ntuples = libpq.PQntuples(res)
    nfields = libpq.PQnfields(res)
    cols = [libpq.PQfname(res, i).decode("utf-8", errors="replace") for i in range(nfields)]
    print(" | ".join(cols))
    print("-" * 80)
    if ntuples == 0:
        print("(sem resultados)")
    for i in range(ntuples):
        vals = [libpq.PQgetvalue(res, i, j).decode("utf-8", errors="replace")[:80] for j in range(nfields)]
        print(" | ".join(vals))
    libpq.PQclear(res)


run(
    "Q1: leads.user_id=31 OR score=80 OR nome~carolina/ragugnetti",
    """SELECT id, user_id, nome, cidade, score, tier, status, criado_em
       FROM leads
       WHERE user_id = 31
          OR score = 80
          OR LOWER(nome) LIKE '%carolina%'
          OR LOWER(nome) LIKE '%ragugnetti%'
       ORDER BY criado_em DESC""",
)

run(
    "Q2: contagem por user_id (top 10)",
    """SELECT user_id, COUNT(*) AS total, MAX(criado_em) AS ultimo
       FROM leads GROUP BY user_id ORDER BY total DESC LIMIT 10""",
)

run(
    "Q3: ultimos 10 leads (contexto geral)",
    """SELECT id, user_id, nome, score, tier, status, criado_em
       FROM leads ORDER BY criado_em DESC LIMIT 10""",
)

run(
    "Q4: estrutura tabela leads",
    """SELECT column_name, data_type FROM information_schema.columns
       WHERE table_name='leads' ORDER BY ordinal_position""",
)

run(
    "Q5: tabelas ledger/audit/log",
    """SELECT table_name FROM information_schema.tables
       WHERE table_schema='public'
         AND (table_name ILIKE '%ledger%' OR table_name ILIKE '%audit%'
              OR table_name ILIKE '%log%' OR table_name ILIKE '%histor%'
              OR table_name ILIKE '%agent%' OR table_name ILIKE '%pipeline%')
       ORDER BY table_name""",
)

libpq.PQfinish(pgconn)
print()
print("OK")