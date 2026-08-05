#!/usr/bin/env python3
"""Restart OpenUI and verify."""
import subprocess, time
subprocess.run(["systemctl", "restart", "fralib-openui"], check=True)
time.sleep(3)
r = subprocess.run(["curl", "-s", "http://localhost:3333/health"], capture_output=True, text=True)
print(f"Health: {r.stdout}")
r2 = subprocess.run(["systemctl", "is-active", "fralib-openui"], capture_output=True, text=True)
print(f"Active: {r2.stdout.strip()}")