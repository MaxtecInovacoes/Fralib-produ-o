import os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:fralib2024@localhost:5433/fralib_db")
import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
from backend.services.outbound_queue import get_recent_sent_count, can_send_now
from backend.core.database import engine
from sqlalchemy import text

# Limpar msgs de teste
with engine.connect() as c:
    c.execute(text("DELETE FROM outbound_queue WHERE source='test'"))
    c.commit()

# Verificar q esta zerado
with engine.connect() as c:
    pending = c.execute(text("SELECT COUNT(*) FROM outbound_queue WHERE status='pending'")).scalar()
print(f"Pending: {pending}")
print(f"Recent sent (10min): {get_recent_sent_count(engine, 1)}")
can, wait = can_send_now(engine, 1)
print(f"Can send now: {can}, wait_sec={wait}")

# Inserir 1 msg como 'sent' e ver se bloqueia
with engine.connect() as c:
    c.execute(text("""
        INSERT INTO outbound_queue
        (tenant_id, lead_id, phone, message, source, status, priority, scheduled_at, sent_at)
        VALUES (1, 'L1', '5511', 'teste 1', 'test', 'sent', 5, NOW(), NOW() - INTERVAL '1 minute')
    """))
    c.commit()

print()
print(f"Apos 1 msg sent 1min atras:")
print(f"  Recent sent: {get_recent_sent_count(engine, 1)}")
can, wait = can_send_now(engine, 1)
print(f"  Can send: {can}, wait_sec={wait}")

# 2a msg
with engine.connect() as c:
    c.execute(text("""
        INSERT INTO outbound_queue
        (tenant_id, lead_id, phone, message, source, status, priority, scheduled_at, sent_at)
        VALUES (1, 'L2', '5512', 'teste 2', 'test', 'sent', 5, NOW(), NOW() - INTERVAL '30 second')
    """))
    c.commit()

print()
print(f"Apos 2 msgs sent:")
print(f"  Recent sent: {get_recent_sent_count(engine, 1)}")
can, wait = can_send_now(engine, 1)
print(f"  Can send: {can}, wait_sec={wait}")
print(f"  Esperado: can=False (atingiu limite), wait ~540s (10min - 30s)")
