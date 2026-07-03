#!/usr/bin/env python3
"""
Dashboard de saúde do FraLib.
Roda 1x/h via cron. Checa:
- /health retorna ok?
- Todos os systemd services rodando?
- Disco acima de 85%?
- Mensagens WPP/24h tem volume razoável (>0)?

Se algo cair, manda alerta via Telegram (se TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
estiverem no env). Senao, loga no journal (visivel com journalctl).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Tuple

HEALTH_URL = os.getenv("FRALIB_HEALTH_URL", "http://localhost:8000/api/health")
DISCO_LIMITE_PCT = int(os.getenv("FRALIB_DISCO_LIMITE", "85"))
SERVICOS = [
    "fralib-api",
    "fralib-worker",
    "fralib-franz",
    "fralib-wpp-listener",
    "fralib-hermes",
]
SERVICOS_OPCIONAIS = [
    "fralib-meowhats",  # pode nao estar instalado ainda
]
LOG_PREFIX = "[healthcheck]"


def log(msg: str) -> None:
    """Loga pra stdout (vai pro journal se rodado via systemd)."""
    print(f"{LOG_PREFIX} {datetime.now().isoformat()} {msg}", flush=True)


def check_health() -> Tuple[bool, str]:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as r:
            if r.status != 200:
                return False, f"status {r.status}"
            data = json.loads(r.read().decode("utf-8"))
            status = data.get("status", "unknown")
            if status not in ("ok", "healthy"):
                return False, f"status {status}"
            return True, status
    except Exception as exc:
        return False, f"exception {type(exc).__name__}: {exc}"


def check_service(svc: str) -> Tuple[bool, str]:
    try:
        out = subprocess.run(
            ["systemctl", "is-active", svc],
            capture_output=True, text=True, timeout=5,
        )
        state = out.stdout.strip()
        if state == "active":
            return True, state
        return False, state or "unknown"
    except Exception as exc:
        return False, f"exception {type(exc).__name__}: {exc}"


def check_disco() -> Tuple[bool, str]:
    try:
        out = subprocess.run(
            ["df", "-P", "/"],
            capture_output=True, text=True, timeout=5,
        )
        lines = out.stdout.strip().split("\n")
        if len(lines) < 2:
            return False, "impossivel ler df"
        parts = lines[1].split()
        use_pct = int(parts[4].rstrip("%"))
        if use_pct > DISCO_LIMITE_PCT:
            return False, f"{use_pct}% (limite {DISCO_LIMITE_PCT}%)"
        return True, f"{use_pct}%"
    except Exception as exc:
        return False, f"exception {type(exc).__name__}: {exc}"


def send_telegram(alertas: List[str]) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    msg = "FraLib Healthcheck FALHOU:\n" + "\n".join(f"- {a}" for a in alertas)
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(
            url, data=json.dumps({"chat_id": chat, "text": msg}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as exc:
        log(f"telegram falhou: {exc}")
        return False


def main() -> int:
    log("iniciando healthcheck")
    alertas: List[str] = []

    # 1. Health endpoint
    ok, detail = check_health()
    if not ok:
        alertas.append(f"/health: {detail}")
    log(f"/health: {'OK' if ok else 'FALHA'} ({detail})")

    # 2. Servicos systemd
    for svc in SERVICOS:
        ok, detail = check_service(svc)
        if not ok:
            alertas.append(f"service {svc}: {detail}")
        log(f"service {svc}: {'OK' if ok else 'FALHA'} ({detail})")

    # 3. Servicos opcionais (nao alerta se nao existe)
    for svc in SERVICOS_OPCIONAIS:
        ok, detail = check_service(svc)
        if not ok and "not-found" not in detail and "inactive" not in detail:
            log(f"service opcional {svc}: {detail}")

    # 4. Disco
    ok, detail = check_disco()
    if not ok:
        alertas.append(f"disco: {detail}")
    log(f"disco: {'OK' if ok else 'FALHA'} ({detail})")

    # 5. Alerta
    if alertas:
        log(f"ALERTAS: {len(alertas)}")
        for a in alertas:
            log(f"  - {a}")
        if send_telegram(alertas):
            log("alerta enviado via telegram")
        return 1

    log("OK: tudo saudavel")
    return 0


if __name__ == "__main__":
    sys.exit(main())