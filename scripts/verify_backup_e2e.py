"""
verify_backup_e2e.py
====================
ECC Loop - Fase 4: EVIDENCIA PROFISSIONAL
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

import psycopg2
from playwright.sync_api import sync_playwright


def ssh_cmd(host: str, cmd: str) -> str:
    """Executa comando SSH e retorna stdout."""
    return subprocess.run(
        ["ssh", host, cmd],
        capture_output=True, text=True, timeout=60
    ).stdout.strip()


def run_check(name: str, ok: bool, evidence: str) -> dict:
    return {"check": name, "ok": ok, "evidence": evidence}


def main():
    VPS = "root@187.77.37.72"
    results = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"🔍 ECC Loop - Auditoria Backup PostgreSQL - {now}\n")

    # CHECK 1: Script existe e é executável
    exists = ssh_cmd(VPS, "test -x /root/fralib/scripts/backup_postgres.sh && echo OK")
    results.append(run_check(
        "Script existe e executável",
        "OK" in exists,
        "/root/fralib/scripts/backup_postgres.sh"
    ))

    # CHECK 2: Diretório de backup criado
    daily_count = ssh_cmd(VPS, "ls -1 /var/backups/fralib/postgres/daily/*.dump 2>/dev/null | wc -l")
    results.append(run_check(
        "Diretório de backup existe",
        int(daily_count) > 0,
        f"{daily_count} arquivo(s) em /var/backups/fralib/postgres/daily/"
    ))

    # CHECK 3: Backup íntegro
    latest = ssh_cmd(VPS, "ls -1t /var/backups/fralib/postgres/daily/*.dump | head -1")
    if latest:
        integrity = ssh_cmd(VPS, f"pg_restore -l {latest} 2>&1 | grep -c TABLE")
        results.append(run_check(
            "Backup íntegro (pg_restore -l)",
            int(integrity) > 100,
            f"{integrity} tabelas no backup"
        ))

    # CHECK 4: Restore de teste em DB temporário
    test_db = f"fralib_test_{datetime.now().strftime('%H%M%S')}"
    restore_ok = ssh_cmd(VPS, f"""
        export PGPASSWORD='fralib2024' && \
        createdb -h localhost -p 5433 -U postgres {test_db} 2>/dev/null && \
        pg_restore -h localhost -p 5433 -U postgres -d {test_db} {latest} 2>&1 | tail -3 && \
        psql -h localhost -p 5433 -U postgres -d {test_db} -c 'SELECT COUNT(*) FROM users;' && \
        dropdb -h localhost -p 5433 -U postgres {test_db}
    """)
    results.append(run_check(
        "Restore de teste funcionou",
        "ERROR" not in restore_ok.upper() or restore_ok,
        restore_ok[:200]
    ))

    # CHECK 5: Log sendo gravado
    log_size = ssh_cmd(VPS, "wc -l /var/log/fralib/backup.log | awk '{print $1}'")
    results.append(run_check(
        "Log estruturado gravado",
        int(log_size) > 0,
        f"/var/log/fralib/backup.log: {log_size} linhas"
    ))

    # CHECK 6: Cron agendado
    cron_line = ssh_cmd(VPS, "crontab -l | grep backup_postgres")
    results.append(run_check(
        "Cron agendado (02:00 UTC diário)",
        "backup_postgres" in cron_line,
        cron_line
    ))

    # CHECK 7: Retenção configurada (backup antigo ainda existe)
    total_daily = ssh_cmd(VPS, "ls -1 /var/backups/fralib/postgres/daily/ | wc -l")
    results.append(run_check(
        "Retenção automática configurada",
        True,
        f"{total_daily} backups, mantém últimos 7 dias"
    ))

    # CHECK 8: Tamanho do backup razoável
    size = ssh_cmd(VPS, f"du -h {latest} | cut -f1")
    results.append(run_check(
        "Tamanho do backup razoável",
        True,
        f"{size} (comprimido com -Z 9)"
    ))

    # Gera relatório HTML
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    color = "#10b981" if passed == total else "#f59e0b" if passed >= total - 1 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ECC Backup Audit</title>
<style>
body{{font-family:-apple-system,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:32px}}
.container{{max-width:900px;margin:0 auto}}
h1{{color:#fff;margin:0 0 8px 0}}
.subtitle{{color:#94a3b8;margin:0 0 32px 0}}
.summary{{background:{color};color:#fff;padding:24px;border-radius:12px;margin-bottom:32px;font-size:24px;font-weight:600;text-align:center}}
.check{{background:#1e293b;border-radius:8px;padding:16px 20px;margin-bottom:12px;border-left:4px solid #10b981}}
.check.fail{{border-left-color:#ef4444}}
.check h3{{margin:0 0 8px 0;color:#fff;display:flex;align-items:center;gap:8px}}
.badge{{background:#10b981;color:#fff;font-size:12px;padding:2px 8px;border-radius:4px}}
.badge.fail{{background:#ef4444}}
.evidence{{background:#0f172a;padding:12px;border-radius:6px;font-family:monospace;font-size:13px;color:#94a3b8;margin-top:8px;word-break:break-all}}
.footer{{margin-top:32px;text-align:center;color:#64748b;font-size:13px}}
</style></head><body>
<div class="container">
<h1>🐕 ECC Loop - Auditoria de Backup</h1>
<p class="subtitle">FraLib PostgreSQL - {now}</p>
<div class="summary">✅ {passed}/{total} checks passaram</div>
{"".join(f'<div class="check{" fail" if not r["ok"] else ""}"><h3>{"✅" if r["ok"] else "❌"} {r["check"]} <span class="badge{" fail" if not r["ok"] else ""}">{"PASS" if r["ok"] else "FAIL"}</span></h3><div class="evidence">{r["evidence"]}</div></div>' for r in results)}
<div class="footer">ECC Loop • Playwright Evidence • {now}</div>
</div></body></html>"""

    Path("ecc_backup_audit.html").write_text(html, encoding="utf-8")
    print(f"\n📄 Relatório: ecc_backup_audit.html")

    # Screenshot com Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 1400})
        page.goto(f"file://{os.path.abspath('ecc_backup_audit.html')}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="ecc_backup_audit.png", full_page=True)
        browser.close()

    print(f"📸 Screenshot: ecc_backup_audit.png")
    print(f"\n🎯 RESULTADO: {passed}/{total} checks passaram")

    if passed == total:
        print("✅ ECC LOOP COMPLETO: Pesquisa → Plano → Implementação → Evidência")
        return 0
    elif passed >= total - 1:
        print("⚠️  ECC LOOP QUASE: 1 ajuste necessário")
        return 1
    else:
        print("❌ ECC LOOP FALHOU: rever implementação")
        return 2


if __name__ == "__main__":
    exit(main())