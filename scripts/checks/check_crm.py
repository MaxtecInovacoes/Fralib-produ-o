import sys, json

# Read all lines from stdin
data = json.load(sys.stdin)

# 1. Auth/me
print("=== AUTH ===")
print("user:", data.get("email"))

# 2. CRM
print("\n=== CRM ===")
print("fila:", len(data.get("fila", [])))
