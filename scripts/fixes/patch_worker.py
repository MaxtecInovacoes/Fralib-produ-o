#!/usr/bin/env python3
"""Patch worker.py on VPS: wrap _run_pipeline_job in try/except to prevent stuck jobs."""
import subprocess, sys

# Read current worker.py
r = subprocess.run(
    ["ssh", "-o", "StrictHostKeyChecking=no", "root@104.243.41.166", "cat /opt/fralib/worker.py"],
    capture_output=True, text=True, timeout=15
)
if r.returncode != 0:
    print("ERROR reading worker.py:", r.stderr[:200])
    sys.exit(1)

content = r.stdout
print(f"Current worker.py: {len(content)} bytes")

# The fix: add a try/except wrapper around the entire _run_pipeline_job function
# Find the function start and the next function start
func_start_marker = "def _run_pipeline_job(db, job) -> bool:"
next_func_marker = "\ndef run_one() -> bool:"

if func_start_marker not in content:
    print("ERROR: _run_pipeline_job not found")
    sys.exit(1)

idx_start = content.index(func_start_marker)
idx_end = content.index(next_func_marker)

old_func = content[idx_start:idx_end]

# New function with try/except wrapper
new_func = '''def _run_pipeline_job(db, job) -> bool:
    """pipeline_lead: roda o Manager e fecha o loop de inventario."""
    job_id = job["id"]
    try:
'''

# Indent the entire original function body by 4 spaces
lines = old_func.split('\n')
# Skip the def line, indent everything else
indented = '\n'.join(
    '    ' + line if line.strip() else line 
    for line in lines[1:]  # skip "def ..." line
)

# Add the except clause at the end
new_func += indented + '''
    except Exception as exc:
        logger.exception("Job %s (pipeline_lead) CRASHED: %s", job_id, exc)
        try:
            job_queue.mark_failure(db, job_id, error=str(exc)[:1000], retriable=True)
        except Exception:
            pass
    return True
'''

new_content = content[:idx_start] + new_func + '\n\n\n' + content[idx_end:]

print(f"New worker.py: {len(new_content)} bytes")

# Write patched version locally
with open(r"C:\fralib\scripts\fixes\worker_patched.py", "w", encoding="utf-8") as f:
    f.write(new_content)

# Deploy: copy to VPS
r2 = subprocess.run(
    ["scp", r"C:\fralib\scripts\fixes\worker_patched.py", 
     "root@104.243.41.166:/opt/fralib/worker.py"],
    capture_output=True, text=True, timeout=10
)
print(f"SCP: {r2.returncode} - {r2.stderr[:100] if r2.stderr else 'OK'}")

# Restart worker container
r3 = subprocess.run(
    ["ssh", "-o", "StrictHostKeyChecking=no", "root@104.243.41.166",
     "docker compose -f /opt/fralib/docker-compose.prod.yml restart worker"],
    capture_output=True, text=True, timeout=20
)
print(f"Worker restart: {r3.returncode}")
print(r3.stdout[:200])
if r3.stderr:
    print("ERR:", r3.stderr[:200])

# Verify worker is running
import time
time.sleep(3)
r4 = subprocess.run(
    ["ssh", "-o", "StrictHostKeyChecking=no", "root@104.243.41.166",
     "docker ps --filter name=fralib-worker --format '{{.Names}} {{.Status}}'"],
    capture_output=True, text=True, timeout=10
)
print(f"Worker: {r4.stdout.strip()}")
