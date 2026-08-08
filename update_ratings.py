"""Script para atualizar ratings dos leads do tenant 2."""

from backend.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    result = db.execute(text("""
        UPDATE lead_inventory SET
            rating = CASE nome
                WHEN 'Academia Iron Gym' THEN 4.5
                WHEN 'Start Academia' THEN 4.2
                WHEN 'Nova Imperio Gym' THEN 4.0
                WHEN 'Aquaflex Jardim Paulista' THEN 4.3
                WHEN 'Exclusiva Fitness - Academia Feminina' THEN 4.1
                WHEN 'Arena Gym Fitness' THEN 3.8
                WHEN 'High Fitness Academia' THEN 4.4
                WHEN 'Legacy Centro de Treinamento' THEN 4.0
                WHEN 'Academia Ph.D Sports' THEN 4.6
                ELSE 4.0
            END,
            reviews_count = CASE nome
                WHEN 'Academia Iron Gym' THEN 75
                WHEN 'Start Academia' THEN 90
                WHEN 'Nova Imperio Gym' THEN 90
                WHEN 'Aquaflex Jardim Paulista' THEN 90
                WHEN 'Exclusiva Fitness - Academia Feminina' THEN 90
                WHEN 'Arena Gym Fitness' THEN 10
                WHEN 'High Fitness Academia' THEN 45
                WHEN 'Legacy Centro de Treinamento' THEN 30
                WHEN 'Academia Ph.D Sports' THEN 120
                ELSE 20
            END,
            status = 'raw',
            atualizado_em = NOW()
        WHERE tenant_id = 2
    """))
    db.commit()
    print(f"Atualizados {result.rowcount} leads")

    # Verificar
    rows = db.execute(text("""
        SELECT nome, rating, reviews_count, status FROM lead_inventory
        WHERE tenant_id = 2 ORDER BY nome
    """)).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]}⭐ ({r[2]} reviews) - {r[3]}")
finally:
    db.close()
