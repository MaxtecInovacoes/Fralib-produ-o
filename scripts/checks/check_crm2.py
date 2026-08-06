import sys, json

data = json.load(sys.stdin)
print("Keys:", list(data.keys()))
for k, v in data.items():
    if isinstance(v, list):
        print(f"{k}: {len(v)} leads")
        if len(v) > 0:
            print(f"  Sample: id={v[0].get('id','?')}, nome={v[0].get('nome','?')}, status={v[0].get('status','?')}")
    else:
        print(f"{k}: {v}")
