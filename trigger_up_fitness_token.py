"""Generate JWT for user and trigger Up Fitness reprocessamento."""
import jwt
import datetime
import requests
import os

SECRET = "4114d477bfc53269bb171f2578916bc0829841e58268c742037966273445846a"
ALGORITHM = "HS256"
USER_ID = 2
EMAIL = "dezigpi@gmail.com"
LEAD_ID = "daec64f7-3239-4c05-abc2-60b7e45f34ea"
BASE = "http://localhost:8001"

# Read JWT config to confirm algorithm and payload shape
import sys
sys.path.insert(0, '/opt/fralib')
from backend.core.jwt_config import create_access_token  # noqa

payload = {
    "sub": str(USER_ID),
    "email": EMAIL,
    "tenant_id": USER_ID,
    "nome": "FRANZ DOUGLAS CAPELETO",
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
    "iat": datetime.datetime.now(datetime.timezone.utc),
}
token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
print(f"TOKEN: {token[:50]}...")

# Trigger reprocessar
resp = requests.post(
    f"{BASE}/api/v1/pipeline/reprocessar/{LEAD_ID}",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    json={"forcar_renovacao": True},
    timeout=10,
)
print(f"REPROCESSAR STATUS: {resp.status_code}")
print(f"REPROCESSAR BODY: {resp.text[:500]}")
