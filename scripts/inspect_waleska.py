import os, sys
sys.path.insert(0, "/root/fralib")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")
from backend.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
rows = db.execute(text("""
    SELECT id, nome, segmento, cidade, endereco, whatsapp, telefone,
           rating, reviews_count, website, dados
    FROM lead_inventory
    WHERE tenant_id=2
    AND (LOWER(nome) LIKE '%waleska%' OR LOWER(nome) LIKE '%integrativa%' OR LOWER(nome) LIKE '%ortomolecula%')
    ORDER BY id DESC LIMIT 5
""")).fetchall()
for r in rows:
    print("=" * 60)
    print(f"id: {r[0]}")
    print(f"nome: {r[1]}")
    print(f"segmento: {r[2]}")
    print(f"cidade: {r[3]}")
    print(f"endereco: {r[4]}")
    print(f"whatsapp: {r[5]} tel: {r[6]}")
    print(f"rating: {r[7]} reviews: {r[8]}")
    print(f"site: {r[9]}")
    print(f"dados: {r[10]}")
db.close()