#!/usr/bin/env python3
"""Trigger multiple production ticks and check results."""
import urllib.request, json, ssl, time

ctx = ssl.create_default_context()
base = "http://localhost:8001"

# Login
data = json.dumps({"email": "dezigpi@gmail.com", "password": "admin123"}).encode()
req = urllib.request.Request(base + "/api/auth/login", data=data, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, context=ctx) as r:
    token = json.loads(r.read())["access_token"]
h = {"Authorization": "Bearer " + token}

# Trigger 10 production ticks (one per approved lead)
for i in range(10):
    req2 = urllib.request.Request(base + "/api/lead-supply/production/tick", data=json.dumps({}).encode(), headers=dict(h, **{"Content-Type": "application/json"}), method="POST")
    try:
        with urllib.request.urlopen(req2, context=ctx) as r:
            result = json.loads(r.read())
        print(f"Tick {i+1}: {result.get('nome', '?')} (job: {result.get('job_id', '?')[:12]}...)")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Tick {i+1}: HTTP {e.code}: {body[:200]}")
    time.sleep(1)

# Wait for worker to process
print("\nAguardando worker processar (10s)...")
time.sleep(10)

# Check pipeline status
req3 = urllib.request.Request(base + "/api/pipeline/status", headers=h)
with urllib.request.urlopen(req3, context=ctx) as r:
    pipe = json.loads(r.read())
print("\n=== PIPELINE ===")
print(f"totalSites: {pipe.get('totalSites')}")
print(f"totalEnviados: {pipe.get('totalEnviados')}")
print(f"ultimo_erro: {pipe.get('ultimo_erro')}")

# Check inventory again
req4 = urllib.request.Request(base + "/api/lead-supply/status", headers=h)
with urllib.request.urlopen(req4, context=ctx) as r:
    status = json.loads(r.read())
print("\n=== INVENTORY DEPOIS ===")
produced = [i for i in status.get("inventory", []) if i.get("status") == "produced"]
print(f"Produced: {len(produced)}")
for inv in produced:
    print(f"  {inv.get('nome', '?')[:40]} | {inv.get('status')} | site: {inv.get('url_site', 'sem site')}")
