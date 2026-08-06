#!/usr/bin/env python3
"""Watchdog: reset stuck running jobs every 60s."""
import subprocess, time, sys

pg = "52bc220171c8_fralib-postgres-1"
SQL_RESET = "UPDATE jobs SET status='pending', worker_id=NULL, worker_heartbeat=NULL, iniciado_em=NULL WHERE status='running' AND worker_heartbeat < NOW() - INTERVAL '10 minutes';"

count = 0
while True:
    r = subprocess.run(
        ["docker", "exec", pg, "psql", "-U", "fralib_user", "-d", "fralib_db", "-c", SQL_RESET],
        capture_output=True, text=True, timeout=10
    )
    if r.returncode == 0 and "UPDATE 0" not in r.stdout:
        count += 1
        print(f"[{time.strftime('%H:%M:%S')}] Reset stuck jobs (total resets: {count})")
        print(r.stdout[:200])
    time.sleep(60)
