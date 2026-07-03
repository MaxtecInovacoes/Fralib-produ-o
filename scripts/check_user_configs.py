"""Check user_configs for SDR settings."""
from backend.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
r = db.execute(text("""
    SELECT column_name FROM information_schema.columns WHERE table_name='user_configs' ORDER BY ordinal_position
""")).fetchall()
print('user_configs cols:', [r_[0] for r_ in r])
print('---')
r2 = db.execute(text("""
    SELECT user_id, config_key, length(config_value) as len, left(config_value, 250) as sample
    FROM user_configs
    WHERE config_key ILIKE '%sdr%' OR config_key ILIKE '%prompt%' OR config_key ILIKE '%rag%' OR config_key ILIKE '%system%' OR config_key ILIKE '%franz%' OR config_key ILIKE '%custom%'
    ORDER BY user_id, config_key LIMIT 30
""")).fetchall()
print('user_configs relevantes:')
for row in r2: print(' ', row)
print('---')
r3 = db.execute(text("""
    SELECT user_id, COUNT(*) FROM user_configs GROUP BY user_id ORDER BY user_id LIMIT 10
""")).fetchall()
print('user_configs count por user:')
for row in r3: print(' ', row)
db.close()
