"""Teste manual: enfileira production_tick pra 5 leads com erro."""
from backend.core.database import engine, SessionLocal
from sqlalchemy import text
from backend.services.lead_supply_engine import lead_supply_engine as supply

db = SessionLocal()
supply.ensure_schema(db)
result = db.execute(text("""
    UPDATE lead_inventory
    SET status='approved', erro=NULL, locked_by=NULL, locked_until=NULL, atualizado_em=NOW()
    WHERE status IN ('error_retry','failed','discarded')
    AND id IN (SELECT id FROM lead_inventory WHERE status IN ('error_retry','failed','discarded') LIMIT 5)
    RETURNING lead_id, tenant_id
"""))
rows = result.fetchall()
db.commit()
print('reprocessed:', len(rows))
for r in rows[:5]: print(' ', r)
tenants = set([r[1] for r in rows])
for t in tenants:
    supply.enqueue_production_tick(db, t, delay_seconds=1, reason='manual-test-after-fix')
print('enqueued for tenants:', tenants)
db.close()
