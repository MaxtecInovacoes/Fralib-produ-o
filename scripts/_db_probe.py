# -*- coding: utf-8 -*-
"""Tenta multiplas estrategias de conexao."""
import ctypes, sys, traceback
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

libpq_path = r"C:\Users\JESUS TE AMA\AppData\Local\Programs\Python\Python312\Lib\site-packages\psycopg2_binary.libs\libpq-59fb91041b8033400b68b6f333423fb2.dll"
libpq = ctypes.CDLL(libpq_path)
PGconn = ctypes.c_void_p
libpq.PQconnectdb.restype = PGconn
libpq.PQstatus.argtypes = [PGconn]; libpq.PQstatus.restype = ctypes.c_int
libpq.PQerrorMessage.argtypes = [PGconn]; libpq.PQerrorMessage.restype = ctypes.c_char_p
libpq.PQfinish.argtypes = [PGconn]

candidates = [
    b"host=127.0.0.1 port=5432 dbname=fralib_db user=postgres password=fralib2024 connect_timeout=5",
    b"host=127.0.0.1 port=5432 dbname=fralib_db user=postgres password= connect_timeout=5",
    b"host=127.0.0.1 port=5432 dbname=fralib_db user=postgres connect_timeout=5",
    b"host=127.0.0.1 port=5432 dbname=postgres user=postgres password=fralib2024 connect_timeout=5",
    b"host=127.0.0.1 port=5432 dbname=postgres user=postgres connect_timeout=5",
    b"host=localhost port=5432 dbname=postgres user=fralib password=fralib2024 connect_timeout=5",
    b"host=localhost port=5432 dbname=fralib_db user=fralib password=fralib2024 connect_timeout=5",
    b"host=localhost port=5432 dbname=postgres user=admin password=fralib2024 connect_timeout=5",
    b"host=localhost port=5432 dbname=fralib_db user=admin password=fralib2024 connect_timeout=5",
]

for cinfo in candidates:
    conn = libpq.PQconnectdb(cinfo)
    status = libpq.PQstatus(conn)
    err = libpq.PQerrorMessage(conn) or b""
    err_s = err.decode("utf-8", errors="replace").split("\n")[0]
    print(f"[status={status}] {cinfo.decode()[:90]} -> {err_s[:120]}")
    if status == 0:
        print(">>> CONECTOU!")
        libpq.PQfinish(conn)
        sys.exit(0)
    libpq.PQfinish(conn)