import sys, json
d = json.load(sys.stdin)
print("Inventory:", len(d["inventory"]))
for i in d["inventory"][:5]:
    print(f"  {i['nome']}: {i['status']} score={i['score_caio']} tier={i['tier']}")
print("Events:", len(d["events"]))
for e in d["events"][:3]:
    print(f"  [{e.get('origem','?')}] {e.get('mensagem','?')}")
