#!/usr/bin/env python3
"""Trigger production tick via API."""
import urllib.request, json, ssl

ctx = ssl.create_default_context()

# Login
req = urllib.request.Request(
    "http://localhost:8001/api/auth/login",
    data=json.dumps({"email": "dezigpi@gmail.com", "password": "***"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, context=ctx) as r:
    token = json.loads(r.read()).get("access_token", "")
print("Token:", token[:20], "...")

headers = {"Authorization": "***", "Content-Type": "application/json"}

# Trigger production tick
req2 = urllib.request.Request(
    "http://localhost:8001/api/lead-supply/production/tick",
    data=json.dumps({}).encode(),
    headers=headers,
    method="POST"
)
try:
    with urllib.request.urlopen(req2, context=ctx) as r:
        result = json.loads(r.read())
    print("\n=== PRODUCTION TICK ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body}")
