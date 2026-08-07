#!/usr/bin/env python3
"""Deploy wandb/openui Python service on VPS."""
import subprocess
import sys

VPS_HOST = "root@100.124.56.36"
SERVICE_NAME = "fralib-openui"
WORKDIR = "/opt/fralib/openui-service-wandb/backend"
VENV_PATH = f"{WORKDIR}/.venv"
ENV_FILE = f"{WORKDIR}/.env"

def ssh(cmd: str) -> str:
    """Run command on VPS via SSH."""
    result = subprocess.run(
        ["ssh", "-i", "/root/.ssh/id_ed25519", "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=10", VPS_HOST, cmd],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"ERROR running: {cmd}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def main():
    print("=== Step 1: Read .env from VPS ===")
    env_content = ssh(f"cat {ENV_FILE}")
    print(f"Current .env ({len(env_content)} bytes)")

    print("\n=== Step 2: Sync API key from main .env ===")
    ssh(f"""grep "^ANTHROPIC_API_KEY=" /opt/fralib/.env >> {ENV_FILE}""")
    ssh(f"""grep "^DEPLOYFLOW_API_KEY=" /opt/fralib/.env >> {ENV_FILE}""")

    print("\n=== Step 3: Create Python venv ===")
    ssh(f"cd {WORKDIR} && python3 -m venv .venv")

    print("\n=== Step 4: Install dependencies ===")
    ssh(f"{VENV_PATH}/bin/pip install --quiet --upgrade pip setuptools wheel")
    ssh(f"{VENV_PATH}/bin/pip install --quiet litellm[proxy]>=1.40.20 fastapi uvicorn tiktoken")
    ssh(f"{VENV_PATH}/bin/pip install --quiet -e {WORKDIR} --no-deps 2>/dev/null || true")

    print("\n=== Step 5: Verify uvicorn exists ===")
    ssh(f"{VENV_PATH}/bin/uvicorn --version")

    print("\n=== Step 6: Create systemd unit ===")
    unit_content = """[Unit]
Description=FraLib OpenUI Python Service (wandb/openui + LiteLLM)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={workdir}
ExecStart={venv}/bin/uvicorn openui.main:app --host 0.0.0.0 --port 7878
Restart=always
RestartSec=5
EnvironmentFile={envfile}
Environment=LITELLM_MASTER_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
Environment=OPENUI_MAX_TOKENS=64000
Environment=OPENUI_ENVIRONMENT=production
Environment=NODE_ENV=production
Environment=OPENAI_COMPATIBLE_ENDPOINT=https://deployflow.com.br/api/public/v1
Environment=OPENAI_COMPATIBLE_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
""".format(workdir=WORKDIR, venv=VENV_PATH, envfile=ENV_FILE)

    ssh(f"""cat > /etc/systemd/system/{SERVICE_NAME}.service << 'UNITEOF'
{unit_content}
UNITEOF""")

    print("\n=== Step 7: Reload systemd + start service ===")
    ssh("systemctl daemon-reload")
    ssh(f"systemctl enable {SERVICE_NAME}")
    ssh(f"systemctl restart {SERVICE_NAME}")

    print("\n=== Step 8: Wait for service to be ready ===")
    import time
    for i in range(15):
        time.sleep(2)
        try:
            result = ssh("curl -s -o /dev/null -w '%{http_code}' http://localhost:7878/v1/models 2>/dev/null")
            if result == "200":
                print(f"OK - OpenUI responding on attempt {i+1}")
                break
        except SystemExit:
            pass
        print(f"  attempt {i+1}: not ready yet...")
    else:
        print("WARNING: service may not be fully ready yet")

    print("\n=== Step 9: Verify service status ===")
    status = ssh(f"systemctl is-active {SERVICE_NAME}")
    print(f"Service status: {status}")

    print("\n=== Step 10: Test /v1/models ===")
    models = ssh("curl -s http://localhost:7878/v1/models 2>/dev/null | head -c 500")
    print(f"Models response (first 500 chars): {models}")

    print("\n=== DONE ===")

if __name__ == "__main__":
    main()
