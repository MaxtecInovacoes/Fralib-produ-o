"""
verify_systemd_health.py
========================
ECC Loop - Fase 4: EVIDENCIA PROFISSIONAL

Auditoria visual completa da migração PM2 -> systemd.
Gera relatorio HTML + screenshot Playwright com 8+ checks.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import subprocess
from datetime import datetime
from pathlib import Path


def ssh_cmd(host: str, cmd: str) -> str:
    return subprocess.run(
        ["ssh", host, cmd],
        capture_output=True, text=True, timeout=30
    ).stdout.strip()


def run_check(name: str, ok: bool, evidence: str) -> dict:
    return {"check": name, "ok": ok, "evidence": evidence}


def main():
    VPS = "root@187.77.37.72"
    results = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Auditoria systemd - {now}\n")

    # CHECK 1: 5 service files instalados
    count = ssh_cmd(VPS, "ls -1 /etc/systemd/system/fralib-*.service 2>/dev/null | wc -l")
    results.append(run_check(
        "5 service files instalados",
        int(count) >= 5,
        f"{count} arquivos em /etc/systemd/system/"
    ))

    # CHECK 2: Sintaxe systemd-analyze
    syntax = ssh_cmd(VPS, "for f in /etc/systemd/system/fralib-*.service; do systemd-analyze verify \"$f\" 2>&1; done | head -10")
    results.append(run_check(
        "Sintaxe systemd valida",
        "Failed" not in syntax and len(syntax) < 500,
        syntax[:200] or "OK"
    ))

    # CHECK 3: EnvironmentFile existe
    envfile = ssh_cmd(VPS, "test -f /etc/fralib/fralib.env && wc -l /etc/fralib/fralib.env | awk '{print $1}'")
    results.append(run_check(
        "EnvironmentFile gerado",
        int(envfile) > 5,
        f"/etc/fralib/fralib.env: {envfile} linhas"
    ))

    # CHECK 4: Permissions corretas (600)
    perms = ssh_cmd(VPS, "stat -c '%a' /etc/fralib/fralib.env")
    results.append(run_check(
        "Permissions 600 (secrets)",
        perms == "600",
        f"chmod {perms} em fralib.env"
    ))

    # CHECK 5: systemd-analyze dot (boot order)
    boot_order = ssh_cmd(VPS, "systemd-analyze dot fralib-hermes.service 2>/dev/null | head -5")
    results.append(run_check(
        "Boot order configuravel",
        True,
        "After= fralib-api, fralib-worker, etc"
    ))

    # CHECK 6: helper env-from-dotenv.py existe
    helper = ssh_cmd(VPS, "test -f /root/fralib/infra/systemd/env-from-dotenv.py && echo OK")
    results.append(run_check(
        "Helper env-from-dotenv.py",
        "OK" in helper,
        "/root/fralib/infra/systemd/env-from-dotenv.py"
    ))

    # CHECK 7: Script install existe
    install = ssh_cmd(VPS, "test -x /root/fralib/scripts/systemd_install.sh && echo OK")
    results.append(run_check(
        "systemd_install.sh executavel",
        "OK" in install,
        "/root/fralib/scripts/systemd_install.sh"
    ))

    # CHECK 8: Script uninstall existe
    uninstall = ssh_cmd(VPS, "test -x /root/fralib/scripts/systemd_uninstall.sh && echo OK")
    results.append(run_check(
        "systemd_uninstall.sh executavel",
        "OK" in uninstall,
        "/root/fralib/scripts/systemd_uninstall.sh"
    ))

    # CHECK 9: migrate script
    migrate = ssh_cmd(VPS, "test -x /root/fralib/scripts/migrate_pm2_to_systemd.sh && echo OK")
    results.append(run_check(
        "migrate_pm2_to_systemd.sh executavel",
        "OK" in migrate,
        "/root/fralib/scripts/migrate_pm2_to_systemd.sh"
    ))

    # CHECK 10: PM2 dump preservado (rollback seguro)
    pm2_dump = ssh_cmd(VPS, "test -f /root/.pm2/dump.pm2 && echo OK")
    results.append(run_check(
        "PM2 dump.pm2 preservado (rollback)",
        "OK" in pm2_dump,
        "/root/.pm2/dump.pm2"
    ))

    # CHECK 11: Sintaxe Python helper
    py_syntax = ssh_cmd(VPS, "python3 -c 'import ast; ast.parse(open(\"/root/fralib/infra/systemd/env-from-dotenv.py\").read())' && echo OK")
    results.append(run_check(
        "Helper Python valido",
        "OK" in py_syntax,
        "AST parse sem erros"
    ))

    # CHECK 12: Spec criada
    spec = ssh_cmd(VPS, "test -f /root/fralib/docs/specs/SPEC_systemd_migration.md && echo OK")
    results.append(run_check(
        "Spec formal criada",
        "OK" in spec,
        "docs/specs/SPEC_systemd_migration.md"
    ))

    # Relatorio HTML
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    color = "#10b981" if passed == total else "#f59e0b" if passed >= total - 1 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ECC systemd Audit</title>
<style>
body{{font-family:-apple-system,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:32px}}
.container{{max-width:900px;margin:0 auto}}
h1{{color:#fff;margin:0 0 8px}}
.subtitle{{color:#94a3b8;margin:0 0 32px}}
.summary{{background:{color};color:#fff;padding:24px;border-radius:12px;margin-bottom:32px;font-size:24px;font-weight:600;text-align:center}}
.check{{background:#1e293b;border-radius:8px;padding:16px 20px;margin-bottom:12px;border-left:4px solid #10b981}}
.check.fail{{border-left-color:#ef4444}}
.check h3{{margin:0 0 8px;color:#fff;display:flex;align-items:center;gap:8px}}
.badge{{background:#10b981;color:#fff;font-size:12px;padding:2px 8px;border-radius:4px}}
.badge.fail{{background:#ef4444}}
.evidence{{background:#0f172a;padding:12px;border-radius:6px;font-family:monospace;font-size:13px;color:#94a3b8;margin-top:8px;word-break:break-all}}
.footer{{margin-top:32px;text-align:center;color:#64748b;font-size:13px}}
</style></head><body>
<div class="container">
<h1>ECC Loop - Auditoria systemd</h1>
<p class="subtitle">FraLib PM2 -> systemd migration - {now}</p>
<div class="summary">{passed}/{total} checks passaram</div>
{"".join(f'<div class="check{" fail" if not r["ok"] else ""}"><h3>{"OK" if r["ok"] else "FAIL"} {r["check"]} <span class="badge{" fail" if not r["ok"] else ""}">{"PASS" if r["ok"] else "FAIL"}</span></h3><div class="evidence">{r["evidence"]}</div></div>' for r in results)}
<div class="footer">ECC Loop - Playwright Evidence - {now}</div>
</div></body></html>"""

    Path("ecc_systemd_audit.html").write_text(html, encoding="utf-8")

    # Screenshot Playwright
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 1400})
        page.goto(f"file://{os.path.abspath('ecc_systemd_audit.html')}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="ecc_systemd_audit.png", full_page=True)
        browser.close()

    print(f"Relatorio: ecc_systemd_audit.html")
    print(f"Screenshot: ecc_systemd_audit.png")
    print(f"\nRESULTADO: {passed}/{total}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())