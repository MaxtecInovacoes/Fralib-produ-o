"""Force reprocess a specific lead that has good data."""
from backend.core.database import SessionLocal, engine
from sqlalchemy import text
from backend.services.lead_supply_engine import lead_supply_engine as supply

db = SessionLocal()
# Pega 1 lead com status=approved e lead_id NOT NULL
r = db.execute(text("""
    SELECT id, lead_id, tenant_id, status
    FROM lead_inventory
    WHERE status='approved' AND lead_id IS NOT NULL
    ORDER BY criado_em DESC LIMIT 1
""")).fetchone()
print('found:', r)
if r:
    inv_id, lead_id, tenant_id, status = r
    print(f'force reprocess inv={inv_id} lead={lead_id} tenant={tenant_id}')
    # Marca como error_retry pra reprocessar
    db.execute(text("""
        UPDATE lead_inventory
        SET status='approved', erro=NULL, locked_by=NULL, locked_until=NULL, atualizado_em=NOW()
        WHERE id=:id
    """), {'id': inv_id})
    db.commit()
    tick_id = supply.enqueue_production_tick(db, tenant_id, delay_seconds=1, reason='force-reprocess-test')
    print('enqueued tick:', tick_id)
db.close()
