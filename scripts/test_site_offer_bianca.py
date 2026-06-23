"""Testa que o Franz agora oferece site proativamente na conversa da Bianca."""
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


def post(p, d):
    body = json.dumps(d).encode()
    req = urllib.request.Request(
        f"{API}{p}", data=body, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


print("=" * 60)
print("TESTE: Franz agora oferece site proativamente")
print("=" * 60)

msgs = []
turnos = [
    "oi, td bem?",
    "me chamo Jhenifer, sou assistente da Bianca",
    "a Bianca ja tem uma empresa que cuida disso",
    "no momento nao tem interesse, obrigada",
]

for i, msg in enumerate(turnos, 1):
    msgs.append({"role": "user", "content": msg})
    r = post("/chat", {"messages": msgs, "stage": "hook", "segmento": "nutricionista",
                        "cidade": "Curitiba", "modelo": "haiku"})
    reply = r.get("reply", "").replace("\n", " ")
    print(f"\n[Turno {i}] Lead: {msg}")
    print(f"  Franz: {reply[:400]}")

print("\n" + "=" * 60)
print("OBSERVACOES:")
print("- Turno 1: cumprimentou (loop break ou hook)")
print("- Turno 2: Franz deveria oferecer site proativamente")
print("- Turno 3: objection 'ja tem empresa' -> offer_in_objection(has_provider)")
print("- Turno 4: opt-out -> offer_after_optout_attempt (ultimo recurso)")