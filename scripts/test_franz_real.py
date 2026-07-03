"""Test SDR simulator end-to-end with real auth."""
import json
import sys
import os
import time
import urllib.request

# Add backend to path
sys.path.insert(0, '/root/fralib/backend')

# Import jwt directly to avoid auth_endpoints dependency
import jwt
from backend.core.jwt_config import get_jwt_secret, ALGORITHM
from backend.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
r = db.execute(text("SELECT id, email FROM users WHERE id = 2")).fetchone()
print('user 2:', r)

# Real format from auth_endpoints: create_access_token({'sub': str(uid), 'email': email})
now = int(time.time())
payload = {
    'sub': str(r[0]),
    'email': r[1],
    'iat': now,
    'exp': now + 86400,  # 24h like real auth
}
token = jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)
print('token len:', len(token))

# 2. Call simulator endpoint
def call_simulate(message, history=None):
    body = {
        'tenant_id': 2,
        'message': message,
        'history': history or [],
    }
    req = urllib.request.Request(
        'http://localhost:8000/api/admin/simulate',
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())

# Test 1: quanto custa
print('\n=== TEST 1: "quanto custa?" ===')
r1 = call_simulate('quanto custa?')
print('reply:', r1.get('response'))
print('intent:', r1.get('intent'))
print('contains biblioteca?', 'biblioteca' in r1.get('response', '').lower())
print('contains livro?', 'livro' in r1.get('response', '').lower())
print('contains livraria?', 'livraria' in r1.get('response', '').lower())
print('contains R$ 1499?', '1499' in r1.get('response', ''))
print('contains R$ 1.499?', '1.499' in r1.get('response', ''))
print('contains site?', 'site' in r1.get('response', '').lower())
print('latency:', r1.get('latency_ms'))

# Test 2: oi (inicial)
print('\n=== TEST 2: "oi" (inicial) ===')
r2 = call_simulate('oi')
print('reply:', r2.get('response'))
print('intent:', r2.get('intent'))
print('contains biblioteca?', 'biblioteca' in r2.get('response', '').lower())
print('contains site?', 'site' in r2.get('response', '').lower())
print('latency:', r2.get('latency_ms'))

# Test 3: o que voces fazem
print('\n=== TEST 3: "o que voces fazem?" ===')
r3 = call_simulate('o que voces fazem?')
print('reply:', r3.get('response'))
print('intent:', r3.get('intent'))
print('contains biblioteca?', 'biblioteca' in r3.get('response', '').lower())
print('contains site?', 'site' in r3.get('response', '').lower())
print('latency:', r3.get('latency_ms'))

db.close()
