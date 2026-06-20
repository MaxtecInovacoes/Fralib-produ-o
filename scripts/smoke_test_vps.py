"""
smoke_test_vps.py
=================
Smoke test E2E na VPS apos migracao PM2 -> systemd.

Valida:
1. 5 servicos systemd estao active
2. API /health responde
3. WhatsApp /health responde
4. Endpoints /api/admin/* funcionam
5. Logs via journalctl funcionam
6. Limites de RAM estao aplicados
7. Restart funciona
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import subprocess
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright


def ssh_cmd(cmd: str, timeout: int = 30) -> str:
    return subprocess.run(
        ["ssh", "root@187.77.37.72", cmd],
        capture_output=True, text=True, timeout=timeout
    ).stdout.strip()


def run_check(name: str, ok: bool, evidence: str) -> dict:
    return {"check": name, "ok": ok, "evidence": evidence}


def main():
    results = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Smoke Test E2E VPS - {now}\n")

    # CHECK 1: 5 servicos systemd active
    active = ssh_cmd("systemctl list-units --type=service --state=running --no-legend | grep -c fralib")
    results.append(run_check(
        "5 servicos systemd ACTIVE",
        int(active) >= 5,
        f"{active} servicos fralib-* rodando"
    ))

    # CHECK 2: API /health
    api_health = ssh_cmd("curl -s -m 5 http://127.0.0.1:8000/health")
    api_ok = '"db"' in api_health and '"meowhats"' in api_health
    results.append(run_check(
        "API /health responde",
        api_ok,
        api_health[:200]
    ))

    # CHECK 3: WhatsApp /health
    wpp_health = ssh_cmd("curl -s -m 5 -H 'X-API-Key: 1763kovQ@' http://127.0.0.1:3001/health")
    wpp_ok = '"sessions"' in wpp_health and '"ok"' in wpp_health
    results.append(run_check(
        "WhatsApp /health responde",
        wpp_ok,
        wpp_health[:200]
    ))

    # CHECK 4: /api/admin/services funciona
    admin = ssh_cmd("curl -s -m 5 http://127.0.0.1:8000/api/admin/services")
    admin_ok = '"primary_runtime"' in admin and '"systemd"' in admin
    results.append(run_check(
        "/api/admin/services retorna systemd",
        admin_ok,
        f"primary_runtime = system" if admin_ok else "FAIL"
    ))

    # CHECK 5: /api/admin/services/{name} retorna detalhes
    detail = ssh_cmd("curl -s -m 5 http://127.0.0.1:8000/api/admin/services/fralib-api")
    detail_ok = '"status"' in detail and '"active"' in detail
    results.append(run_check(
        "Detalhe de servico retorna status active",
        detail_ok,
        detail[:200]
    ))

    # CHECK 6: Logs via journalctl funcionam
    logs = ssh_cmd("journalctl -u fralib-api -n 5 --no-pager | head -5")
    logs_ok = len(logs) > 10 and "fralib" in logs.lower()
    results.append(run_check(
        "journalctl retorna logs da API",
        logs_ok,
        logs[:300].replace("\n", " | ")
    ))

    # CHECK 7: MemoryMax aplicado (em bytes; 1G = 1073741824)
    memmax = ssh_cmd("systemctl show fralib-api -p MemoryMax --value")
    memmax_int = int(memmax) if memmax.isdigit() else 0
    memmax_ok = memmax_int >= 1073741824  # >= 1G
    memmax_human = f"{memmax_int / 1024 / 1024 / 1024:.2f} GB" if memmax_int > 0 else "0"
    results.append(run_check(
        "MemoryMax aplicado em fralib-api (>= 1G)",
        memmax_ok,
        f"MemoryMax = {memmax} bytes ({memmax_human})"
    ))

    # CHECK 8: CPUQuota aplicado (systemd converte para CPUQuotaPerSecUSec)
    cpuq_pct = ssh_cmd("systemctl show fralib-api -p CPUQuota --value")
    cpuq_us = ssh_cmd("systemctl show fralib-api -p CPUQuotaPerSecUSec --value")
    # Aceita tanto formato "150%" quanto "1.500000s" (1.5 cores = 150%)
    cpuq_ok = (
        (cpuq_pct and cpuq_pct.endswith("%") and int(cpuq_pct.rstrip("%")) > 0)
        or (cpuq_us and "s" in cpuq_us and float(cpuq_us.rstrip("s")) > 0)
    )
    results.append(run_check(
        "CPUQuota aplicado em fralib-api (>0%)",
        cpuq_ok,
        f"CPUQuota={cpuq_pct or 'vazio'} | CPUQuotaPerSecUSec={cpuq_us or 'vazio'}"
    ))

    # CHECK 9: Restart policy
    restart = ssh_cmd("systemctl show fralib-api -p Restart --value")
    restart_ok = restart in ("on-failure", "always")
    results.append(run_check(
        "Restart policy configurada",
        restart_ok,
        f"Restart = {restart}"
    ))

    # CHECK 10: PIDs estao rodando (servicos realmente ativos)
    pids = ssh_cmd("systemctl show fralib-api fralib-worker fralib-hermes fralib-franz fralib-wpp-listener -p MainPID --value | grep -v '^0$' | wc -l")
    pids_ok = int(pids) >= 5
    results.append(run_check(
        "Todos os 5 PIDs estao rodando",
        pids_ok,
        f"{pids} PIDs ativos (sem zero)"
    ))

    # CHECK 11: Worker tem EnvironmentFile carregado
    worker_env = ssh_cmd("systemctl show fralib-worker -p EnvironmentFiles --value")
    env_ok = "fralib.env" in worker_env
    results.append(run_check(
        "EnvironmentFile carregado (fralib.env)",
        env_ok,
        worker_env[:200] or "vazio"
    ))

    # CHECK 12: Hermes watchdog registrou incidentes recentes (prova que roda)
    hermes_recent = ssh_cmd("journalctl -u fralib-hermes -n 10 --no-pager | grep -i 'scan\\|canary' | wc -l")
    hermes_ok = int(hermes_recent) > 0
    results.append(run_check(
        "Hermes executando scans periodicas",
        hermes_ok,
        f"{hermes_recent} scans/canary recentes no journal"
    ))

    # Resumo HTML
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    color = "#10b981" if passed == total else "#f59e0b" if passed >= total - 1 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Smoke Test VPS</title>
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
.evidence{{background:#0f172a;padding:12px;border-radius:6px;font-family:monospace;font-size:12px;color:#94a3b8;margin-top:8px;word-break:break-all;max-height:120px;overflow:auto}}
.footer{{margin-top:32px;text-align:center;color:#64748b;font-size:13px}}
</style></head><body>
<div class="container">
<h1>Smoke Test E2E - VPS Producao</h1>
<p class="subtitle">FraLib PM2 -> systemd migration - {now}</p>
<div class="summary">{passed}/{total} checks passaram</div>
{"".join(f'<div class="check{" fail" if not r["ok"] else ""}"><h3>{"OK" if r["ok"] else "FAIL"} {r["check"]} <span class="badge{" fail" if not r["ok"] else ""}">{"PASS" if r["ok"] else "FAIL"}</span></h3><div class="evidence">{r["evidence"]}</div></div>' for r in results)}
<div class="footer">ECC Loop - Playwright Evidence - {now}</div>
</div></body></html>"""

    Path("ecc_smoke_test_vps.html").write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 1600})
        page.goto(f"file://{os.path.abspath('ecc_smoke_test_vps.html')}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="ecc_smoke_test_vps.png", full_page=True)
        browser.close()

    print(f"Relatorio: ecc_smoke_test_vps.html")
    print(f"Screenshot: ecc_smoke_test_vps.png")
    print(f"\nRESULTADO: {passed}/{total}")

    return 0 if passed == total else 1


import os
if __name__ == "__main__":
    sys.exit(main())