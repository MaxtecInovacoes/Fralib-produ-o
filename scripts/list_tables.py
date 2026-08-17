from backend.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    tables = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).fetchall()
    for t in tables:
        print(t[0])
finally:
    db.close()
