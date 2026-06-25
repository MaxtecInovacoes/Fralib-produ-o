#!/usr/bin/env python3
"""Verifica se migration foi aplicada corretamente."""
import os
import sys
sys.path.insert(0, "/root/fralib/backend")
sys.path.insert(0, "/root/fralib")
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "postgresql://postgres:fralib2024@localhost:5433/fralib_db")
eng = create_engine(url)

with eng.connect() as c:
    r = c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='interacoes' AND column_name='dedup_key'"))
    print("dedup_key column exists:", r.fetchone() is not None)

    r = c.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='interacoes' AND indexname LIKE '%dedup%'"))
    print("dedup indexes:", [row[0] for row in r.fetchall()])

    r = c.execute(text("SELECT COUNT(*) FROM interacoes"))
    print("total interacoes:", r.scalar())
