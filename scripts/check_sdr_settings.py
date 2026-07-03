"""Check SDR settings storage."""
from backend.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
r = db.execute(text("""
    SELECT column_name FROM information_schema.columns WHERE table_name='app_settings' ORDER BY ordinal_position
""")).fetchall()
print('app_settings cols:', [r_[0] for r_ in r])
r2 = db.execute(text("""
    SELECT * FROM app_settings ORDER BY 1 LIMIT 5
""")).fetchall()
print('TODOS app_settings:')
for row in r2: print(' ', row[:5], '...len=', len(str(row)))
db.close()
