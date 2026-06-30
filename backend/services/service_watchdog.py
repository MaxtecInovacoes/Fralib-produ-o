"""
service_watchdog.py
===================
Watchdog de servicos systemd FraLib.

A cada X segundos:
  1. Lista servicos systemd do FraLib
  2. Detecta os inativos (inactive, failed, dead)
  3. Tenta reiniciar automaticamente
  4. Loga tudo

Uso:
  python -m backend.services.service_watchdog [--interval=30]
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from datetime import datetime, timezone

logger = logging.getLogger("uvicorn.service_watchdog")

SERVICES_TO_WATCH = [
    "fralib-api.service",
    "fralib-worker.service",
    "fralib-hermes.service",
    "fralib-franz.service",
    "gosom-scraper.service",  # Scraper de leads
    # fralib-wpp-listener NAO reinicia (sockets persistentes)
    # fralib-dashboard NAO (menos critico)
]

# Estados problematicos que justificam restart
RESTART_STATES = {"inactive", "failed", "activating", "deactivating"}


def _is_active(unit: str) -> bool:
    """Verifica se servico esta ativo."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        state = result.stdout.strip()
        return state == "active"
    except Exception as e:
        logger.warning(f"[watchdog] erro ao verificar {unit}: {e}")
        return True  # Em duvida, nao reinicia


def _restart_service(unit: str) -> tuple[bool, str]:
    """Reinicia servico via systemctl."""
    try:
        result = subprocess.run(
            ["systemctl", "restart", unit],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return (result.returncode == 0, result.stderr.strip() or "ok")
    except Exception as e:
        return (False, str(e))


def _is_enabled(unit: str) -> bool:
    """Verifica se servico esta habilitado (boot start)."""
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        state = result.stdout.strip()
        return state == "enabled"
    except Exception:
        return False


def run_watchdog_cycle() -> dict:
    """Executa 1 ciclo do watchdog: verifica todos os servicos.

    Returns:
        dict com resumo do ciclo
    """
    checked = 0
    restarted = []
    reenabled = []
    already_ok = []

    for unit in SERVICES_TO_WATCH:
        checked += 1
        # Garante que esta habilitado (auto-start no boot)
        if not _is_enabled(unit):
            try:
                subprocess.run(
                    ["systemctl", "enable", unit],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                reenabled.append(unit)
            except Exception:
                pass

        # Verifica se esta rodando
        if _is_active(unit):
            already_ok.append(unit)
            continue

        # Inativo: tenta reiniciar
        ok, msg = _restart_service(unit)
        if ok:
            restarted.append(unit)
            logger.warning(
                f"[watchdog] SERVICO PARADO -> reiniciado: {unit}"
            )
        else:
            logger.error(
                f"[watchdog] SERVICO PARADO -> FALHA ao reiniciar: {unit} ({msg})"
            )

    return {
        "checked": checked,
        "already_ok": already_ok,
        "reenabled": reenabled,
        "restarted": restarted,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_loop(interval_seconds: int = 30):
    """Loop principal do watchdog.

    Args:
        interval_seconds: tempo entre checagens (default 30s)
    """
    logger.info(
        f"[watchdog] iniciando loop com intervalo {interval_seconds}s "
        f"em {len(SERVICES_TO_WATCH)} servicos"
    )
    while True:
        try:
            result = run_watchdog_cycle()
            if result["restarted"] or result["reenabled"]:
                logger.warning(
                    f"[watchdog] ciclo: {len(result['restarted'])} restarted, "
                    f"{len(result['reenabled'])} reenabled"
                )
        except Exception as e:
            logger.error(f"[watchdog] erro no ciclo: {e}")
        time.sleep(interval_seconds)


# ── CLI: roda 1 ciclo sob demanda ────────────────────────────────
if __name__ == "__main__":
    import json
    print(json.dumps(run_watchdog_cycle(), indent=2))