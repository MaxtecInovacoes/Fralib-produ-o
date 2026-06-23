"""Conversa real completa - simula lead navegando o funil inteiro."""
import jwt
import datetime
import json
import time
import urllib.request

SECRET = "68jCd5VfgYOdUl0Am1FP62WxogZObbcY7Ze96fZHO8mvqwgLlXENE3CvBCHDpoVo"
TOK = jwt.encode(
    {"sub": "2", "email": "dezigpi@gmail.com", "is_superadmin": True,
     "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)},
    SECRET, algorithm="HS256",
)
API = "http://127.0.0.1:8000/api/superadmin/sdr-studio"


def post(p, d):
    body = json.dumps(d).encode()
    req = urllib.request.Request(
        f"{API}{p}", data=body, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


print("=" * 60)
print("CONVERSA REAL SIMULADA - LEAD ACADEMIA SAO PAULO")
print("=" * 60)

msgs = []
total_latency = 0
turns = [
    ("oi, td bem?", "hook"),
    ("sou o dono da academia sim, 50 alunos", "qualify"),
    ("a maioria vem por indicacao mesmo, instagram nao ta trazendo", "qualify"),
    ("e como voces podem ajudar?", "qualify"),
    ("hmm, mas quanto fica isso?", "qualify"),
    ("fechado entao, manda o link", "qualify"),
    ("agenda pra amanha 14h", "qualify"),
    ("valeu, ate mais", "qualify"),
]

for i, (msg, expected_stage) in enumerate(turns, 1):
    msgs.append({"role": "user", "content": msg})
    t0 = time.time()
    r = post("/chat", {"messages": msgs, "stage": expected_stage, "segmento": "academia",
                        "cidade": "Sao Paulo", "modelo": "sonnet"})
    latency = r.get("latency_ms", 0)
    total_latency += latency
    reply = r.get("reply", "").replace("\n", " ")
    print(f"\n[Turno {i}] Latency: {latency}ms | Expected: {expected_stage}")
    print(f"  Lead: {msg}")
    print(f"  Franz: {reply[:250]}")

print("\n" + "=" * 60)
print(f"TOTAL: {len(turns)} turnos, latencia media = {total_latency//len(turns)}ms")
print(f"LATENCIA TOTAL: {total_latency}ms = {total_latency/1000:.1f}s")
print("=" * 60)