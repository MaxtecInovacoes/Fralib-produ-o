#!/usr/bin/env python3
"""Trigger production tick and check results."""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
base = "http://localhost:8001"

# Login
data = json.dumps({"email": "dezigpi@gmail.com", "password": "admin123"}).encode()
req = urllib.request.Request(base + "/api/auth/login", data=data, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, context=ctx) as r:
    token = json.loads(r.read())["access_token"]
print("Login OK, token:", token[:20], "...")

h = {"Authorization": "Bearer " + token}

# 1. Check inventory
req2 = urllib.request.Request(base + "/api/lead-supply/status", headers=h)
with urllib.request.urlopen(req2, context=ctx) as r:
    status = json.loads(r.read())
print("\n=== CONFIG ===")
print("Ativo:", status.get("config", {}).get("ativo"))
print("Producao pausada:", status.get("config", {}).get("producao_pausada"))

print("\n=== INVENTORY ===")
for inv in status.get("inventory", []):
    print(f"  {inv.get('nome', '?')[:40]:40s} | {inv.get('status', '?'):12s} | score={inv.get('score_caio', '?')} | tier={inv.get('tier', '?')}")

# 2. Trigger production tick
print("\n=== DISPARANDO PRODUCAO ===")
req3 = urllib.request.Request(base + "/api/lead-supply/production/tick", data=json.dumps({}).encode(), headers=dict(h, **{"Content-Type": "application/json"}), method="POST")
try:
    with urllib.request.urlopen(req3, context=ctx) as r:
        result = json.loads(r.read())
    print("Result:", json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:500]}")

# 3. Check jobs after tick
import time
time.sleep(3)

req4 = urllib.request.Request(base + "/api/pipeline/status", headers=h)
with urllib.request.urlopen(req4, context=ctx) as r:
    pipe = json.loads(r.read())
print("\n=== PIPELINE STATUS ===")
print(json.dumps(pipe, indent=2, ensure_ascii=False))
