#!/usr/bin/env python3
"""Teste end-to-end do espelho Studio -> WhatsApp."""
import jwt, datetime, json, urllib.request, urllib.error, time, sys

SECRET = "68jCd5VfgYOdUl0Am1FP62WxogZObbcY7Ze96fZHO8mvqwgLlXENE3CvBCHDpoVo"
TOK = jwt.encode(
    {
        "sub": "2",
        "email": "dezigpi@gmail.com",
        "is_superadmin": True,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    },
    SECRET,
    algorithm="HS256",
)
print(f"Token gerado: {TOK[:30]}...")

API = "http://127.0.0.1:8000/api/superadmin/sdr-studio"


def get(path):
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {TOK}"})
    return json.loads(urllib.request.urlopen(req).read())


def put(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        method="PUT",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req).read().decode()


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


# 1. Status atual
print("\n=== 1. STATUS DO ESPELHO ===")
files = get("/files")
print(f"  whatsapp_mirror_enabled: {files.get('whatsapp_mirror_enabled')}")
print(f"  layers: {[k for k in files.keys() if k not in ('ok','whatsapp_mirror_enabled')]}")

# 2. Save com regra de teste
print("\n=== 2. INJETANDO REGRA DE TESTE NO USER_SYSTEM ===")
content = files["user_system"]
marker = "# === STAGE: hook ==="
test_marker = "[TESTE-MIRROR-OK]"
new = content.replace(
    marker,
    marker
    + f"\n\n### CUSTOM TEST RULE: Termine a primeira mensagem do stage hook com a frase {test_marker} exatamente assim.",
    1,
)
result = put("/files/user_system", {"content": new, "note": "teste end-to-end"})
print(f"  PUT result: {result[:200]}")

# 3. Chat com stage hook
print("\n=== 3. CHAT DE TESTE (deve refletir a regra) ===")
time.sleep(2)  # margem para I/O
chat = post(
    "/chat",
    {
        "messages": [{"role": "user", "content": "oi, td bem?"}],
        "stage": "hook",
        "segmento": "academia",
        "cidade": "Sao Paulo",
        "modelo": "sonnet",
    },
)
reply = chat.get("reply", "")
print(f"  model: {chat.get('model')}")
print(f"  latency: {chat.get('latency_ms')}ms")
print(f"  reply: {reply[:300]}")
print(f"  contains {test_marker}: {test_marker in reply}")

# 4. Reverter
print("\n=== 4. REVERTENDO (backup que foi salvo) ===")
# Pega a primeira versao salva (auto-backup antes do PUT)
versions = get("/versions?layer=user_system&limit=1")
v = versions["versions"][0] if versions["versions"] else None
if v:
    post(f"/versions/{v['id']}/restore", {})
    print(f"  Restaurado v#{v['id']} (autor: {v['created_by']}, nota: {v['note']})")
else:
    print("  Nenhuma versao para restaurar (PUT falhou?)")

# 5. Validar reversao
files2 = get("/files")
print(f"\n=== 5. VALIDACAO POS-REVERSAO ===")
print(f"  contains {test_marker} ainda: {test_marker in files2.get('user_system', '')}")
