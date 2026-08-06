#!/usr/bin/env python3
"""Fix CRM dashboard filter to show pending/captured leads."""
import subprocess

filepath = "/opt/fralib/backend/endpoints/dashboard_endpoints.py"

# Read via ssh
r = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat", filepath],
    capture_output=True, text=True
)
content = r.stdout

# Fix: let pendente/capturado leads show in kanban
old = """            if status in ('pendente', 'processando', 'capturado', 'erro'):
                continue"""

new = """            if status in ('processando', 'erro'):
                continue
            elif status in ('pendente', 'capturado'):
                data['fila'].append(lead)"""

if old in content:
    content = content.replace(old, new)
    print("Replaced filter")
else:
    print("Pattern not found")
    # Show the relevant lines
    for i, line in enumerate(content.split("\n")):
        if "processando" in line or ("pendente" in line and "skip" not in line.lower()):
            print(f"  L{i+1}: {line.rstrip()}")
    exit(1)

# Write back via ssh
p = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat > " + filepath],
    input=content, text=True, capture_output=True
)
if p.returncode == 0:
    print("Patched OK")
else:
    print("Write error:", p.stderr[:200])
