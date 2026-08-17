"""Destrava leads específicos na esteira do builder."""
import os
import sys
from pathlib import Path

_BASE_DIR = os.environ.get("FRALIB_BASE_DIR", str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, f"{_BASE_DIR}/backend")
from dotenv import load_dotenv
load_dotenv(f"{_BASE_DIR}/.env")

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])

LEADS = ("Force One", "Fitness Center")

with engine.connect() as c:
    check = c.execute(
        text(
            "SELECT id, tenant_id, nome, status, locked_by, locked_until, erro "
            "FROM lead_inventory "
            "WHERE lower(nome) = ANY(:nomes)"
        ),
        {"nomes": [n.lower() for n in LEADS]},
    ).fetchall()
    print(f"Leads encontrados: {len(check)}")
    for row in check:
        print(f"  id={row.id} tenant={row.tenant_id} nome='{row.nome}' status={row.status} locked_by={row.locked_by} erro={row.erro}")

    if not check:
        print("NENHUM lead encontrado com esses nomes — abortando para não afetar dados errados.")
        sys.exit(1)

    res = c.execute(
        text(
            "UPDATE lead_inventory "
            "SET status='approved', erro=NULL, locked_by=NULL, locked_until=NULL, atualizado_em=NOW() "
            "WHERE lower(nome) = ANY(:nomes)"
        ),
        {"nomes": [n.lower() for n in LEADS]},
    )
    c.commit()
    print(f"Linhas atualizadas: {res.rowcount}")

    confirm = c.execute(
        text(
            "SELECT id, tenant_id, nome, status, locked_by, locked_until, erro "
            "FROM lead_inventory "
            "WHERE lower(nome) = ANY(:nomes)"
        ),
        {"nomes": [n.lower() for n in LEADS]},
    ).fetchall()
    print("Estado pós-update:")
    for row in confirm:
        print(f"  id={row.id} tenant={row.tenant_id} nome='{row.nome}' status={row.status} locked_by={row.locked_by} erro={row.erro}")

print("OK")
