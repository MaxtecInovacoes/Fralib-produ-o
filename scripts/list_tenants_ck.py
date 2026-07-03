"""List all tenants with their custom_knowledge."""
from backend.core.database import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
r = db.execute(text("""
    SELECT user_id, config_value
    FROM user_configs
    WHERE config_key = 'sdr_settings_v1'
    ORDER BY user_id
""")).fetchall()
print('TENANTS com SDR settings:')
for row in r:
    uid, raw = row
    try:
        s = json.loads(raw)
        ck = s.get('custom_knowledge', '')
        pers = s.get('personality', '')
        name = s.get('agent_name', '')
        ck_preview = (ck[:60] + '...') if len(ck) > 60 else ck
        print(f'  user {uid}: name={name!r} ck_len={len(ck)} personality_len={len(pers)}')
        if ck_preview:
            print(f'    custom_knowledge: {ck_preview!r}')
    except Exception as e:
        print(f'  user {uid}: parse err {e}')
db.close()
