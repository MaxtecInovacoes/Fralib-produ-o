import os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:fralib2024@localhost:5433/fralib_db")
import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
from backend.core.database import engine
from sqlalchemy import text
from datetime import datetime, timedelta

# Limpar
with engine.connect() as c:
    c.execute(text("DELETE FROM outbound_queue WHERE source='test'"))
    c.commit()

# Inserir 2 msgs sent (uma 1min atras, outra 30s atras)
with engine.connect() as c:
    c.execute(text("""
        INSERT INTO outbound_queue
        (tenant_id, lead_id, phone, message, source, status, priority, scheduled_at, sent_at)
        VALUES
        (1, 'L1', '5511', 'teste 1', 'test', 'sent', 5, NOW(), NOW() - INTERVAL '1 minute'),
        (1, 'L2', '5512', 'teste 2', 'test', 'sent', 5, NOW(), NOW() - INTERVAL '30 second')
    """))
    c.commit()

# Pega o last_sent e calcula
with engine.connect() as c:
    r = c.execute(text("""
        SELECT sent_at, NOW() as agora, EXTRACT(EPOCH FROM (NOW() - sent_at))::int as secs_ago
        FROM outbound_queue
        WHERE tenant_id = 1 AND status = 'sent'
        ORDER BY sent_at DESC LIMIT 1
    """))
    for row in r.fetchall():
        last_sent = row[0]
        agora = row[1]
        secs_ago = row[2]
        print(f"  last_sent={last_sent}")
        print(f"  agora={agora}")
        print(f"  secs_ago={secs_ago}")
        print(f"  type(last_sent)={type(last_sent).__name__}")
        print(f"  last_sent.tzinfo={last_sent.tzinfo if hasattr(last_sent, 'tzinfo') else 'no attribute'}")
        print(f"  agora.tzinfo={agora.tzinfo if hasattr(agora, 'tzinfo') else 'no attribute'}")

        # Fazer o calculo manualmente
        diff = (agora - last_sent).total_seconds()
        print(f"  diff = {diff}s")
        print(f"  expected wait = 600 - 30 = 570s")
        print(f"  actual wait (now 600-30=570, mas com 11369/60=189min)")

    c.execute(text("DELETE FROM outbound_queue WHERE source='test'"))
    c.commit()
