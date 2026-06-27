"""Lista modelos disponiveis no proxy kpalabz."""

import os
import sys
import requests

env_file = '/root/fralib/.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

API_KEY = os.environ["ANTHROPIC_API_KEY"]
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1")

r = requests.get(
    f"{BASE_URL}/models",
    headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01"},
    timeout=30,
)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:3000]}")
