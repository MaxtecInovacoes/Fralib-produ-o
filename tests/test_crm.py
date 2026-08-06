#!/usr/bin/env python3
"""Test CRM endpoint as tenant 2 user."""
import urllib.request, json, ssl

ctx = ssl.create_default_context()

# Login
req = urllib.request.Request(
    "http://localhost:8001/api/auth/login",
    data=json.dumps({"email": "dezigpi@gmail.com", "password": "admin123"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, context=ctx) as r:
    login = json.loads(r.read())

token = login.get("access_token", "")
print("Token:", token[:20], "...")

headers = {"Authorization": "Bearer " + token}

# Auth/me
req2 = urllib.request.Request("http://localhost:8001/api/auth/me", headers=headers)
with urllib.request.urlopen(req2, context=ctx) as r:
    me = json.loads(r.read())
print("Auth/me:", me)

# CRM
req3 = urllib.request.Request("http://localhost:8001/api/dashboard/crm", headers=headers)
with urllib.request.urlopen(req3, context=ctx) as r:
    crm = json.loads(r.read())
print("\nCRM keys:", list(crm.keys()))
for k, v in crm.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)} leads")
        for lead in v[:2]:
            print(f"    - {lead.get('nome','?')} | status={lead.get('status','?')} | score={lead.get('score','?')} | tenant={lead.get('tenant_id','?')}")
    else:
        print(f"  {k}: {v}")

# Pipeline status
req4 = urllib.request.Request("http://localhost:8001/api/pipeline/status", headers=headers)
with urllib.request.urlopen(req4, context=ctx) as r:
    pipe = json.loads(r.read())
print("\nPipeline:", pipe)
