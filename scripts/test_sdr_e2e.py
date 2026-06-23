"""Teste end-to-end do bug do hook-loop via Studio."""
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


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API}{path}", data=body, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


print("=== TESTE 1: Lead so cumprimenta (3x) - DEVE AVANCAR apos 3 turnos ===")
msgs = []
for i, m in enumerate(["oi", "eai", "ola"], 1):
    msgs.append({"role": "user", "content": m})
    r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "academia", "cidade": "Sao Paulo", "modelo": "haiku"})
    reply = r.get("reply", "")[:120].replace("\n", " ")
    print(f"  Turno {i}: '{m}' -> reply: {reply}")

print()
print("=== TESTE 2: Lead cumprimenta e depois engaja ===")
msgs2 = []
for m in ["oi", "sou o dono da academia, a gente atende 50 alunos"]:
    msgs2.append({"role": "user", "content": m})
    r = post("/chat", {"messages": msgs2, "stage": "hook", "segmento": "academia", "cidade": "Sao Paulo", "modelo": "haiku"})
    reply = r.get("reply", "")[:120].replace("\n", " ")
    print(f"  '{m[:40]}' -> {reply}")

print()
print("=== TESTE 3: Opt-out imediato ===")
msgs3 = [{"role": "user", "content": "para, me tira da lista"}]
r = post("/chat", {"messages": msgs3, "stage": "hook", "segmento": "academia", "cidade": "Sao Paulo", "modelo": "haiku"})
reply = r.get("reply", "")[:120].replace("\n", " ")
print(f"  'para, me tira' -> {reply}")

print()
print("=== TESTE 4: Preco sem contexto (regra de ouro) ===")
msgs4 = [{"role": "user", "content": "quanto custa?"}]
r = post("/chat", {"messages": msgs4, "stage": "hook", "segmento": "academia", "cidade": "Sao Paulo", "modelo": "haiku"})
reply = r.get("reply", "")[:150].replace("\n", " ")
print(f"  'quanto custa?' -> {reply}")