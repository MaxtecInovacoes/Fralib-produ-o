"""Envia msg WhatsApp real 3x com mesmo msg_id (simula race condition do bug).

Roda via SSH na VPS. Se Franz responder só 1x, o fix funcionou.
"""
import sys
import os
import asyncio
import httpx

sys.path.insert(0, "/root/fralib/backend")
sys.path.insert(0, "/root/fralib")

# Pega config do MeoWhats
meowhats_url = os.environ.get("MEOWHATS_HTTP", "http://localhost:3001")
meowhats_key = os.environ.get("MEOWHATS_API_KEY", "")
tenant_id = "fralib-teste"

print(f"MeoWhats URL: {meowhats_url}")
print(f"Tenant: {tenant_id}")

# Lead real - SEU telefone (já que superadmin)
test_phone = os.environ.get("TEST_PHONE", "5511999999999")
jid = f"{test_phone}@s.whatsapp.net"

# Envia 3 mensagens iguais com mesmo msg_id (simulando race)
msg_text = "Teste fix bug 3x"

async def send_msg(client, idx):
    try:
        r = await client.post(
            f"{meowhats_url}/api/sessions/{tenant_id}/send",
            headers={"X-API-Key": meowhats_key},
            json={"jid": jid, "type": "text", "text": f"{msg_text} (#{idx})"}
        )
        print(f"  msg {idx}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  msg {idx}: ERRO {e}")

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [send_msg(client, i) for i in range(3)]
        await asyncio.gather(*tasks)

asyncio.run(main())
print("OK - 3 msgs enviadas. Aguarde 10s e verifique no WhatsApp se Franz respondeu só 1x.")
