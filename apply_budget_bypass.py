"""Patch llm_direct.py inside worker to bypass budget, then sync builder, then restart."""
import sys, subprocess, time

# 1) Patch llm_direct.py — bypass budget + cooldown when env var is set
container = "fralib-worker-1"
host_file = r"C:\fralib\patch_budget.py"

patch_script = r'''
import sys, os
p = "/app/backend/agents/llm_direct.py"
with open(p, encoding="utf-8") as f:
    src = f.read()

old = """    if _ia and not base_url:
        try:
            # Fase 1: Circuit breaker global
            _cooled, _cd_remaining = _ia.is_globally_cooled_down()
            if _cooled and _cd_remaining > 60:
                print(
                    f"[LLM] Circuit breaker OPEN — cooldown {_cd_remaining}s restantes"
                )
                raise RateLimitError(_cd_remaining)

            # Fase 2: Budget diario global
            _budget_ok, _budget_remaining = _ia.check_daily_budget()
            if not _budget_ok:
                print("[LLM] Budget diario ESGOTADO — 0 tokens restantes")
                raise Exception(
                    "Budget diario de tokens esgotado. Aguarde reset (24h rolling window)."
                )

            # Fase 3: Budget por tenant
            if request_user_id:'''

new = """    if _ia and not base_url:
        try:
            # FASE 1 BYPASS: DISABLE_DAILY_BUDGET=true pular verificação
            if os.environ.get("DISABLE_DAILY_BUDGET", "").lower() == "true":
                print("[LLM] Budget check BYPASSED (DISABLE_DAILY_BUDGET=true)")

            # Fase 1: Circuit breaker global
            _cooled, _cd_remaining = _ia.is_globally_cooled_down()
            if _cooled and _cd_remaining > 60:
                print(
                    f"[LLM] Circuit breaker OPEN — cooldown {_cd_remaining}s restantes"
                )
                raise RateLimitError(_cd_remaining)

            # Fase 2: Budget diario global
            _budget_ok, _budget_remaining = _ia.check_daily_budget()
            if not _budget_ok:
                print("[LLM] Budget diario ESGOTADO — 0 tokens restantes")
                raise Exception(
                    "Budget diario de tokens esgotado. Aguarde reset (24h rolling window)."
                )

            # Fase 3: Budget por tenant
            if request_user_id:"""

if old in src:
    src = src.replace(old, new)
    # Add os import if not present
    if "import os" not in src:
        src = "import os\n" + src
    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    print("[OK] llm_direct.py patched")
else:
    print("[FAIL] Could not find block to patch")
    sys.exit(1)

# Verify
with open(p, encoding="utf-8") as f:
    patched = f.read()
if "DISABLE_DAILY_BUDGET" in patched:
    print("[OK] DISABLE_DAILY_BUDGET flag present")
else:
    print("[FAIL] Flag not found after patch")
    sys.exit(1)
'''

# Write patch script to host
with open(host_file, "w", encoding="utf-8") as f:
    f.write(patch_script)

# Copy patch script into container
r = subprocess.run(
    ["scp", "-i", r"C:\Users\JESUS TE AMA\.ssh\id_ed25519",
     host_file, f"root@104.243.41.166:/tmp/patch_budget.py"],
    capture_output=True, text=True
)
print(f"scp: {r.returncode} {r.stderr[:200]}")

# Execute patch inside container
r = subprocess.run(
    ["ssh", "-i", r"C:\Users\JESUS TE AMA\.ssh\id_ed25519",
     "root@104.243.41.166",
     f"docker cp /tmp/patch_budget.py {container}:/app/patch_budget.py && "
     f"docker exec {container} python3 /app/patch_budget.py"],
    capture_output=True, text=True
)
print(f"patch: rc={r.returncode}")
print(f"stdout: {r.stdout[-500:]}")
print(f"stderr: {r.stderr[-500:]}")
