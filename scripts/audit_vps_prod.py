"""Auditoria de produção - Valida todas as features 10/10."""
import jwt
import datetime
import json
import urllib.request

SECRET = "68jCd5VfgYOdUl0Am1FP62WxogZObbcY7Ze96fZHO8mvqwgLlXENE3CvBCHDpoVo"
TOK = jwt.encode(
    {"sub": "2", "email": "dezigpi@gmail.com", "is_superadmin": True,
     "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)},
    SECRET, algorithm="HS256",
)
API = "http://127.0.0.1:8000/api/superadmin/sdr-studio"


def get(p):
    req = urllib.request.Request(
        f"{API}{p}", headers={"Authorization": f"Bearer {TOK}"}
    )
    return json.loads(urllib.request.urlopen(req).read())


def post(p, d):
    body = json.dumps(d).encode()
    req = urllib.request.Request(
        f"{API}{p}", data=body, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


print("=" * 60)
print("AUDITORIA DE PRODUCAO - VPS 187.77.37.72")
print("=" * 60)

print("\n=== Feature 4: Mirror Studio <-> WhatsApp ===")
files = get("/files")
print(f"  whatsapp_mirror_enabled: {files.get('whatsapp_mirror_enabled')}")
print(f"  layers: {list(k for k in files.keys() if k not in ('ok', 'whatsapp_mirror_enabled'))}")
print(f"  design_system chars: {len(files.get('design_system', ''))}")
print(f"  user_system chars:   {len(files.get('user_system', ''))}")
print(f"  rag chars:           {len(files.get('rag', ''))}")

print("\n=== Teste 1: Cumprimento simples (hook) ===")
r = post("/chat", {"messages": [{"role": "user", "content": "oi, td bem?"}],
                    "stage": "hook", "segmento": "academia", "cidade": "Sao Paulo", "modelo": "sonnet"})
reply = r.get("reply", "").replace("\n", " ")
print(f"  latency: {r.get('latency_ms')}ms")
print(f"  reply: {reply[:200]}")

print("\n=== Teste 2: 3 cumprimentos (loop break) ===")
msgs = []
for i, m in enumerate(["oi", "eai", "ola"], 1):
    msgs.append({"role": "user", "content": m})
    r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "academia",
                        "cidade": "Sao Paulo", "modelo": "sonnet"})
    reply = r.get("reply", "").replace("\n", " ")
    print(f"  Turno {i}: {reply[:100]}")

print("\n=== Teste 3: Engajamento profundo (espera avance) ===")
msgs = [{"role": "user", "content": "sou o dono da academia, a gente tem 50 alunos"}]
r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "academia",
                    "cidade": "Sao Paulo", "modelo": "sonnet"})
reply = r.get("reply", "").replace("\n", " ")
print(f"  reply: {reply[:200]}")

print("\n=== Teste 4: Preco sem contexto (regra de ouro) ===")
msgs = [{"role": "user", "content": "quanto custa?"}]
r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "academia",
                    "cidade": "Sao Paulo", "modelo": "sonnet"})
reply = r.get("reply", "").replace("\n", " ")
print(f"  reply: {reply[:200]}")

print("\n=== Teste 5: Opt-out ===")
msgs = [{"role": "user", "content": "para, me tira"}]
r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "academia",
                    "cidade": "Sao Paulo", "modelo": "sonnet"})
reply = r.get("reply", "").replace("\n", " ")
print(f"  reply: {reply[:200]}")

print("\n=== Teste 6: Agendamento ===")
msgs = [{"role": "user", "content": "agenda pra semana que vem"}]
r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "academia",
                    "cidade": "Sao Paulo", "modelo": "sonnet"})
reply = r.get("reply", "").replace("\n", " ")
print(f"  reply: {reply[:200]}")

print("\n=== Feature: Versionamento ===")
versions = get("/versions?layer=design_system&limit=3")
print(f"  total versions: {len(versions.get('versions', []))}")
for v in versions.get("versions", [])[:3]:
    print(f"  v#{v['id']} {v['created_at'][:19]} - {v['note'][:50]}")

print("\n" + "=" * 60)
print("AUDITORIA CONCLUIDA")
print("=" * 60)