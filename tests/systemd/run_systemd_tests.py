"""
run_systemd_tests.py
====================
Runner simples sem pytest (pytest estava travando).
Executa os testes manualmente e reporta.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import re
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYSTEMD_DIR = PROJECT_ROOT / "infra" / "systemd"
HELPER = SYSTEMD_DIR / "env-from-dotenv.py"

EXPECTED_SERVICES = [
    "fralib-api.service",
    "fralib-worker.service",
    "fralib-franz.service",
    "fralib-wpp-listener.service",
    "fralib-hermes.service",
]


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def assert_(self, condition, msg):
        if condition:
            self.passed += 1
            self.results.append(("PASS", msg))
            print(f"  [OK] {msg}")
        else:
            self.failed += 1
            self.results.append(("FAIL", msg))
            print(f"  [FAIL] {msg}")

    def section(self, name):
        print(f"\n=== {name} ===")


def test_service_files():
    runner = TestRunner()
    runner.section("SERVICE FILES EXISTEM")

    for svc in EXPECTED_SERVICES:
        path = SYSTEMD_DIR / svc
        runner.assert_(path.exists(), f"{svc} existe")

    runner.assert_((SYSTEMD_DIR / "env-from-dotenv.py").exists(), "env-from-dotenv.py existe")
    runner.assert_((SYSTEMD_DIR / "README.md").exists(), "README.md existe")

    runner.section("ESTRUTURA DOS SERVICES")
    for svc in EXPECTED_SERVICES:
        content = (SYSTEMD_DIR / svc).read_text(encoding="utf-8")
        runner.assert_("[Unit]" in content, f"{svc} tem [Unit]")
        runner.assert_("[Service]" in content, f"{svc} tem [Service]")
        runner.assert_("[Install]" in content, f"{svc} tem [Install]")

    runner.section("LIMITES DE RECURSOS")
    for svc in EXPECTED_SERVICES:
        content = (SYSTEMD_DIR / svc).read_text(encoding="utf-8")
        runner.assert_("MemoryMax=" in content, f"{svc} tem MemoryMax")
        runner.assert_("CPUQuota=" in content, f"{svc} tem CPUQuota")
        runner.assert_("Restart=" in content, f"{svc} tem Restart=")

    runner.section("SEGURANCA")
    for svc in EXPECTED_SERVICES:
        content = (SYSTEMD_DIR / svc).read_text(encoding="utf-8")
        runner.assert_("NoNewPrivileges=yes" in content, f"{svc} tem NoNewPrivileges=yes")
        runner.assert_("PrivateTmp=yes" in content, f"{svc} tem PrivateTmp=yes")

    runner.section("BOOT ORDER")
    hermes_content = (SYSTEMD_DIR / "fralib-hermes.service").read_text(encoding="utf-8")
    runner.assert_("After=" in hermes_content, "hermes tem After=")
    runner.assert_("fralib-api" in hermes_content, "hermes espera fralib-api")

    runner.section("PATHS CORRETOS")
    for svc in EXPECTED_SERVICES:
        content = (SYSTEMD_DIR / svc).read_text(encoding="utf-8")
        runner.assert_("/root/fralib" in content, f"{svc} usa /root/fralib")
        runner.assert_("/root/fralib/venv/bin/python3" in content, f"{svc} usa venv python")

    return runner


def test_env_helper():
    runner = TestRunner()
    runner.section("HELPER ENV-FROM-DOTENV.PY")

    runner.assert_(HELPER.exists(), "Helper existe")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Teste 1: simples
        env_file = tmp / "test.env"
        env_file.write_text("FOO=bar\n")
        out_file = tmp / "out.env"
        result = subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(out_file)],
            capture_output=True, text=True
        )
        runner.assert_(result.returncode == 0, "Helper exit 0 (simple)")
        if out_file.exists():
            out = out_file.read_text()
            runner.assert_('FOO="bar"' in out, "Output contem FOO=bar")

        # Teste 2: com aspas
        env_file = tmp / "test2.env"
        env_file.write_text('KEY="value with spaces"\n')
        out_file = tmp / "out2.env"
        result = subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(out_file)],
            capture_output=True, text=True
        )
        runner.assert_(result.returncode == 0, "Helper exit 0 (quotes)")
        if out_file.exists():
            out = out_file.read_text()
            runner.assert_('KEY="value with spaces"' in out, "Quotes preservadas")

        # Teste 3: ignora comentarios
        env_file = tmp / "test3.env"
        env_file.write_text("# comment\nFOO=bar\n# another\nBAZ=qux\n")
        out_file = tmp / "out3.env"
        result = subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(out_file)],
            capture_output=True, text=True
        )
        runner.assert_(result.returncode == 0, "Helper exit 0 (comments)")
        if out_file.exists():
            out = out_file.read_text()
            runner.assert_('FOO="bar"' in out and 'BAZ="qux"' in out, "Vars extraidas")
            runner.assert_("# comment" not in out, "Comentarios removidos")

        # Teste 4: erro com input inexistente
        result = subprocess.run(
            [sys.executable, str(HELPER), "/tmp/xyz_nonexistent_999.env", str(tmp / "err.env")],
            capture_output=True, text=True
        )
        runner.assert_(result.returncode != 0, "Erro com input inexistente")

    return runner


def test_scripts():
    runner = TestRunner()
    runner.section("SCRIPTS DE GESTAO")

    scripts = [
        ("scripts/systemd_install.sh", True),
        ("scripts/systemd_uninstall.sh", True),
        ("scripts/migrate_pm2_to_systemd.sh", True),
        ("scripts/verify_systemd_health.py", False),
    ]
    for rel, _ in scripts:
        path = PROJECT_ROOT / rel
        runner.assert_(path.exists(), f"{rel} existe")

    # Uninstall deve fazer rollback PM2
    uninstall = (PROJECT_ROOT / "scripts/systemd_uninstall.sh").read_text(encoding="utf-8")
    runner.assert_("pm2 resurrect" in uninstall, "uninstall faz rollback PM2")

    # Audit script tem 8+ checks
    audit = (PROJECT_ROOT / "scripts/verify_systemd_health.py").read_text(encoding="utf-8")
    check_count = audit.count('run_check(')
    runner.assert_(check_count >= 8, f"Audit tem {check_count} checks (min 8)")

    # Spec
    spec = PROJECT_ROOT / "docs" / "specs" / "SPEC_systemd_migration.md"
    runner.assert_(spec.exists(), "SPEC existe")
    if spec.exists():
        content = spec.read_text(encoding="utf-8")
        runner.assert_("CRITÉRIOS DE ACEITE" in content, "SPEC tem CRITÉRIOS DE ACEITE")
        runner.assert_("FORA DE ESCOPO" in content, "SPEC tem FORA DE ESCOPO")

    return runner


def main():
    print("=" * 60)
    print(" ECC LOOP - TESTES SYSTEMD")
    print("=" * 60)

    all_results = []

    print("\n[1/3] Service Files")
    r1 = test_service_files()
    all_results.extend(r1.results)

    print("\n[2/3] Env Helper")
    r2 = test_env_helper()
    all_results.extend(r2.results)

    print("\n[3/3] Scripts + Spec")
    r3 = test_scripts()
    all_results.extend(r3.results)

    total = len(all_results)
    passed = sum(1 for status, _ in all_results if status == "PASS")
    failed = total - passed

    print("\n" + "=" * 60)
    print(f" RESULTADO: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())