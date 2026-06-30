#!/usr/bin/env python3
"""
Testes para Lead Supply Sync
============================
Valida que o sistema de prospecção está configurado e funcionando.

Uso:
    python3 /root/fralib/scripts/test_lead_supply_sync.py
"""
import os
import sys
import subprocess
import json

# Cores
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

tests_passed = 0
tests_failed = 0
tests_results = []


def test(name: str, condition: bool, details: str = "") -> None:
    global tests_passed, tests_failed
    status = f"{GREEN}PASS{RESET}" if condition else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    if details:
        print(f"         {details}")
    tests_results.append((name, condition))
    if condition:
        tests_passed += 1
    else:
        tests_failed += 1


def run_command(cmd: str, shell: bool = True) -> tuple[int, str, str]:
    """Executa comando shell e retorna (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def main():
    global tests_passed, tests_failed
    tests_passed = 0
    tests_failed = 0
    tests_results.clear()

    print("\n" + "=" * 60)
    print(" Lead Supply Sync - Testes de Validacao")
    print("=" * 60)

    # Test 1: GOSOM_ENABLED=1 configurado
    print("\n[1] Verificando GOSOM_ENABLED...")
    # Check shell environment
    gosom_enabled = os.getenv("GOSOM_ENABLED", "0")
    gosom_enabled_check = gosom_enabled.lower() in {"1", "true", "yes", "on"}

    # Also check .env file directly
    env_file = "/root/fralib/.env"
    env_gosom = "0"
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith("GOSOM_ENABLED="):
                    env_gosom = line.strip().split("=", 1)[1].strip()
                    break

    gosom_enabled_check = gosom_enabled_check or env_gosom.lower() in {"1", "true", "yes", "on"}
    test(
        "GOSOM_ENABLED configurado",
        gosom_enabled_check,
        f"env={gosom_enabled}, .env={env_gosom}"
    )

    # Test 2: GOSOM rodando (pgrep)
    print("\n[2] Verificando GOSOM rodando...")
    rc, stdout, _ = run_command("pgrep -f gosom-scraper || pgrep -f google-maps-scraper || pgrep -f 'gosom'")
    gosom_running = rc == 0
    test(
        "GOSOM processo rodando (pgrep)",
        gosom_running,
        f"pgrep output: {stdout or 'nenhum processo encontrado'}"
    )

    # Test 3: GOSOM API respondendo (curl)
    print("\n[3] Verificando GOSOM API...")
    rc, stdout, stderr = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:8085/api/v1/jobs --max-time 5")
    gosom_api_ok = rc == 0 and stdout in {"200", "201"}
    test(
        "GOSOM API respondendo (curl)",
        gosom_api_ok,
        f"HTTP status: {stdout}, stderr: {stderr or 'ok'}"
    )

    # Test 4: Watchdog timer ativo
    print("\n[4] Verificando Watchdog timer...")
    watchdog_files = [
        "/root/fralib/backend/services/lead_supply_watchdog.sh",
        "/root/fralib/scripts/lead_supply_watchdog.sh",
        "/root/fralib/backend/services/lead_supply_watchdog.py",
        "/root/fralib/scripts/lead_supply_diagnose.py",
    ]
    watchdog_exists = any(os.path.exists(f) for f in watchdog_files)
    test(
        "Watchdog timer arquivos existem",
        watchdog_exists,
        f"Arquivos verificados: {', '.join(watchdog_files)}"
    )

    # Test 5: Pipeline sincroniza lead_supply_config
    print("\n[5] Verificando sincronizacao lead_supply_config...")
    pipeline_file = "/root/fralib/backend/endpoints/pipeline_start_endpoints.py"
    pipeline_sync_ok = False
    if os.path.exists(pipeline_file):
        with open(pipeline_file, "r") as f:
            content = f.read()
        # Verifica se existe chamada para lead_supply_storage ou save_config
        pipeline_sync_ok = (
            "lead_supply_storage" in content
            and "save_config" in content
            and "lead_supply_config" in content
        )
    test(
        "Pipeline sincroniza lead_supply_config",
        pipeline_sync_ok,
        f"Arquivo: {pipeline_file}"
    )

    # Test 6: Payload usa 'fastmode' nao 'fast_mode'
    print("\n[6] Verificando payload fastmode (nao fast_mode)...")
    gosom_file = "/root/fralib/backend/utils/google_maps_gosom.py"
    payload_check = "PASS"
    payload_details = ""
    if os.path.exists(gosom_file):
        with open(gosom_file, "r") as f:
            content = f.read()

        # Verifica se usa 'fastmode' (correto)
        has_fastmode = '"fastmode"' in content or "'fastmode'" in content
        # Verifica se usa 'fast_mode' (incorreto)
        has_fast_mode_wrong = '"fast_mode"' in content or "'fast_mode'" in content

        if has_fast_mode_wrong and not has_fastmode:
            payload_check = "FAIL"
            payload_details = "Usa 'fast_mode' (incorreto) - deve ser 'fastmode'"
        elif has_fastmode and not has_fast_mode_wrong:
            payload_check = "PASS"
            payload_details = "Usa 'fastmode' (correto)"
        elif has_fastmode and has_fast_mode_wrong:
            payload_check = "WARN"
            payload_details = "Usa ambos - verificar qual e usado no payload"
        else:
            payload_check = "WARN"
            payload_details = "Nenhum fastmode/fast_mode encontrado no arquivo"

    fastmode_ok = payload_check == "PASS"
    test(
        "Payload usa 'fastmode' (nao 'fast_mode')",
        fastmode_ok,
        payload_details
    )

    # Resumo
    print("\n" + "=" * 60)
    print(" RESUMO")
    print("=" * 60)
    print(f"  {GREEN}Passed: {tests_passed}{RESET}")
    print(f"  {RED}Failed: {tests_failed}{RESET}")
    print("=" * 60)

    if tests_failed == 0:
        print(f"\n{GREEN}Todos os testes passaram!{RESET}\n")
        return 0
    else:
        print(f"\n{RED}Alguns testes falharam. Verifique acima.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
