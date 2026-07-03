"""Refine COMMERCIAL_POLICY mention: add explicit 12x calculation."""
import os
from backend.core.database import SessionLocal
from sqlalchemy import text
import json

os.environ.setdefault('FRALIB_SDR_PROMPTS_FROM_MD', '1')

# Adicionar regra explicita no custom_knowledge dos 2 tenants
ADICIONAL = """

QUANDO LEAD FALAR 'TA CARO' (objecao de preco):
- SEMPRE responda com o parcelamento: 'Em 12x fica R$ 124,92/mes. Sem juros.'
- Reforce: 'E so paga DEPOIS de aprovar o site final.'
- Adicione: 'O site ja esta pronto. E so ajustar e colocar no ar.'
- Se o lead hesitar ainda, ofereca follow-up em 24h.

CALCULOS MEMORIZAR:
- R$ 1.499 / 12 = R$ 124,92/mes (sem juros)
- R$ 1.499 Pix a vista: 5% desconto = R$ 1.424,05
- R$ 1.299 (follow-up 24h): R$ 108,25/mes
- R$ 999 (follow-up 72h): R$ 83,25/mes"""

TENANT_IDS = [2, 31]

db = SessionLocal()
for tid in TENANT_IDS:
    r = db.execute(text("""
        SELECT config_value FROM user_configs
        WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
    """), {'uid': tid}).fetchone()
    if not r:
        print(f'user {tid}: sem settings, skip')
        continue
    s = json.loads(r[0])
    old_ck = s.get('custom_knowledge', '')
    if 'QUANDO LEAD FALAR' not in old_ck:
        s['custom_knowledge'] = old_ck + ADICIONAL
    else:
        # ja tem, nao duplica
        continue
    new_raw = json.dumps(s, ensure_ascii=False)
    db.execute(text("""
        UPDATE user_configs
        SET config_value = :v, updated_at = NOW()
        WHERE user_id = :uid AND config_key = 'sdr_settings_v1'
    """), {'v': new_raw, 'uid': tid})
    print(f'user {tid}: appended {len(ADICIONAL)} chars to custom_knowledge')
db.commit()
db.close()
