"""Show full SDR settings for user 2."""
from backend.core.database import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
r = db.execute(text("""
    SELECT user_id, config_key, config_value
    FROM user_configs
    WHERE user_id = 2 AND config_key = 'sdr_settings_v1'
""")).fetchone()
print('user 2 SDR settings:')
print(json.dumps(json.loads(r[2]), indent=2, ensure_ascii=False))
print('---')
r2 = db.execute(text("""
    SELECT user_id, config_key, config_value
    FROM user_configs WHERE user_id = 1 LIMIT 5
""")).fetchall()
print('user 1 (superadmin?) configs:')
for row in r2: print(' ', row[1], '=', row[2][:200])
db.close()
