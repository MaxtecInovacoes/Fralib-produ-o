#!/usr/bin/env python3
"""Fix dashboard CRM to show pending/captured leads in kanban."""
import subprocess

filepath = "/opt/fralib/backend/endpoints/dashboard_endpoints.py"

# Read file via ssh
r = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat", filepath],
    capture_output=True, text=True
)
if r.returncode != 0:
    print("ERR reading:", r.stderr[:200])
    exit(1)

content = r.stdout

# The fix: remove the skip filter for pendente/capturado
old_filter = """            if status in ('pendente', 'processando', 'capturado', 'erro'):
                continue"""

new_filter = """            if status in ('processando', 'erro'):
                continue
            elif status in ('pendente', 'capturado'):
                data['fila'].append(lead)"""

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print("Replaced filter block")
else:
    print("Filter block not found, trying alternative...")
    # Try multiline
    import re
    pattern = r"if status in \('pendente', 'processando', 'capturado', 'erro'\):\s+continue"
    content = re.sub(pattern, new_filter, content)
    print("Regex replacement done")

# Write back
patch = subprocess.run(
    ["ssh", "root@104.243.41.166", "cat > " + filepath],
    input=content, text=True, capture_output=True
)
if patch.returncode == 0:
    print("File patched OK")
else:
    print("Write error:", patch.stderr[:200])
