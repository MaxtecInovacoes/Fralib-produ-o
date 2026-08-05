"""
service_manager.py
==================
Camada de abstracao para gerenciar servicos do FraLib.

Detecta automaticamente se o servico roda em systemd OU PM2.
Todas as operacoes (start, stop, restart, status, logs) funcionam
independentemente do gerenciador.

Uso:
    from backend.services.service_manager import ServiceManager, list_services

    mgr = ServiceManager()
    mgr.restart("fralib-api")  # detecta se eh systemd ou PM2

    for svc in list_services():
        print(svc.name, svc.status, svc.runtime)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Lista canonica de servicos do FraLib
FRA_SERVICES = [
    "fralib-api",          # era: fralib (PM2)
    "fralib-worker",       # era: fralib-worker
    "fralib-franz",        # era: fralib-franz-worker
    "fralib-wpp-listener", # era: fralib-wpp-listener
    "fralib-hermes",       # era: fralib-hermes-watchdog
]

# Mapeamento PM2 legacy -> systemd novo (para retrocompatibilidade)
PM2_TO_SYSTEMD = {
    "fralib": "fralib-api",
    "fralib-worker": "fralib-worker",
    "fralib-franz-worker": "fralib-franz",
    "fralib-wpp-listener": "fralib-wpp-listener",
    "fralib-hermes-watchdog": "fralib-hermes",
}

SYSTEMD_TO_PM2 = {v: k for k, v in PM2_TO_SYSTEMD.items()}

# Servicos que rodam em docker/standalone (nao sao gerenciados por systemd/PM2)
EXTERNAL_SERVICES = {
    "whatsmeow": "systemd whatsmeow.service (porta 3001, gerenciado separado)",
    "meowhats": "alias legacy do whatsmeow",
}


@dataclass
class ServiceInfo:
    """Info de um servico."""
    name: str
    runtime: Literal["systemd", "pm2", "external", "unknown"]
    status: str  # "active", "online", "running", "stopped", "failed", etc
    pid: int | None = None
    uptime_seconds: int | None = None
    memory_mb: float | None = None
    cpu_percent: float | None = None
    restarts: int = 0
    last_error: str | None = None
    raw: dict = field(default_factory=dict)


class ServiceManager:
    """Gerencia servicos com auto-detect."""

    def __init__(self):
        self.has_systemd = shutil.which("systemctl") is not None
        self.has_pm2 = shutil.which("pm2") is not None

    def resolve(self, name: str) -> tuple[str, str]:
        """Resolve nome de servico -> (runtime, nome nativo).

        Args:
            name: pode ser nome PM2 antigo ("fralib") OU systemd novo ("fralib-api")

        Returns:
            (runtime, native_name) - ex: ("systemd", "fralib-api") ou ("pm2", "fralib")
        """
        # Detectar pelo sufixo ou mapeamento
        canonical = PM2_TO_SYSTEMD.get(name, name)

        # Priorizar systemd se instalado
        if self.has_systemd and self._systemd_unit_exists(canonical):
            return ("systemd", canonical)

        # Fallback PM2 se existir
        pm2_name = SYSTEMD_TO_PM2.get(name, name)
        if self.has_pm2 and self._pm2_process_exists(pm2_name):
            return ("pm2", pm2_name)

        # Default: assumir systemd (preferido)
        return ("systemd", canonical)

    def _systemd_unit_exists(self, name: str) -> bool:
        """Verifica se .service existe em /etc/systemd/system/."""
        try:
            result = subprocess.run(
                ["systemctl", "list-unit-files", f"{name}.service", "--no-legend"],
                capture_output=True, text=True, timeout=5
            )
            return name in result.stdout
        except Exception:
            return False

    def _pm2_process_exists(self, name: str) -> bool:
        """Verifica se processo PM2 existe."""
        try:
            result = subprocess.run(
                ["pm2", "jlist"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return False
            procs = json.loads(result.stdout or "[]")
            return any(p.get("name") == name for p in procs)
        except Exception:
            return False

    def status(self, name: str) -> ServiceInfo:
        """Retorna status de um servico."""
        runtime, native = self.resolve(name)
        if runtime == "systemd":
            return self._systemd_status(native)
        elif runtime == "pm2":
            return self._pm2_status(native)
        else:
            return ServiceInfo(name=name, runtime="unknown", status="not_found")

    def _systemd_status(self, name: str) -> ServiceInfo:
        """Coleta status de servico systemd."""
        try:
            result = subprocess.run(
                ["systemctl", "show", name,
                 "--property=ActiveState,SubState,MainPID,MemoryCurrent,CPUUsageNSec,RestartCount,NRestarts"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return ServiceInfo(name=name, runtime="systemd", status="not_found",
                                   last_error=result.stderr[:200])

            props = {}
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k] = v

            active = props.get("ActiveState", "unknown")
            pid = int(props.get("MainPID", "0")) if props.get("MainPID", "").isdigit() else None
            mem_bytes = props.get("MemoryCurrent", "0")
            mem_mb = float(mem_bytes) / 1024 / 1024 if mem_bytes.isdigit() else None
            restarts = int(props.get("RestartCount", "0")) if props.get("RestartCount", "").isdigit() else 0

            return ServiceInfo(
                name=name,
                runtime="systemd",
                status=active,
                pid=pid,
                memory_mb=mem_mb,
                restarts=restarts,
                raw=props,
            )
        except Exception as e:
            return ServiceInfo(name=name, runtime="systemd", status="error", last_error=str(e))

    def _pm2_status(self, name: str) -> ServiceInfo:
        """Coleta status de processo PM2."""
        try:
            result = subprocess.run(
                ["pm2", "jlist"], capture_output=True, text=True, timeout=5
            )
            procs = json.loads(result.stdout or "[]")
            for p in procs:
                if p.get("name") == name:
                    env = p.get("pm2_env", {})
                    monit = p.get("monit", {})
                    return ServiceInfo(
                        name=name,
                        runtime="pm2",
                        status=env.get("status", "unknown"),
                        pid=p.get("pid"),
                        memory_mb=monit.get("memory", 0) / 1024 / 1024 if monit.get("memory") else None,
                        cpu_percent=monit.get("cpu"),
                        restarts=env.get("restart_count", 0),
                        uptime_seconds=env.get("pm2_uptime"),
                        raw=p,
                    )
            return ServiceInfo(name=name, runtime="pm2", status="not_found")
        except Exception as e:
            return ServiceInfo(name=name, runtime="pm2", status="error", last_error=str(e))

    def restart(self, name: str) -> tuple[bool, str]:
        """Reinicia um servico (auto-detect)."""
        runtime, native = self.resolve(name)
        if runtime == "systemd":
            result = subprocess.run(
                ["systemctl", "restart", native],
                capture_output=True, text=True, timeout=30
            )
            return (result.returncode == 0, result.stderr or "OK")
        elif runtime == "pm2":
            result = subprocess.run(
                ["pm2", "restart", native],
                capture_output=True, text=True, timeout=30
            )
            return (result.returncode == 0, result.stderr or "OK")
        return (False, f"Servico nao encontrado: {name}")

    def logs(self, name: str, lines: int = 100) -> str:
        """Retorna ultimas N linhas de log."""
        runtime, native = self.resolve(name)
        if runtime == "systemd":
            result = subprocess.run(
                ["journalctl", "-u", native, "-n", str(lines), "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout
        elif runtime == "pm2":
            log_path = Path.home() / ".pm2" / "logs" / f"{native}-out.log"
            error_log = Path.home() / ".pm2" / "logs" / f"{native}-error.log"
            out = ""
            if error_log.exists():
                out += f"=== ERROR LOG ===\n{self._tail(error_log, lines)}\n\n"
            if log_path.exists():
                out += f"=== OUTPUT LOG ===\n{self._tail(log_path, lines)}"
            return out or "Logs nao encontrados"
        return ""

    def _tail(self, path: Path, n: int) -> str:
        """Ultimas N linhas de um arquivo."""
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                return "".join(f.readlines()[-n:])
        except Exception as e:
            return f"<erro lendo {path}: {e}>"

    def summary(self) -> dict:
        """Resumo geral: runtime ativo + servicos."""
        primary = "systemd" if self.has_systemd else "pm2" if self.has_pm2 else "none"
        return {
            "primary_runtime": primary,
            "has_systemd": self.has_systemd,
            "has_pm2": self.has_pm2,
            "services": [self._svc_to_dict(self.status(s)) for s in FRA_SERVICES],
            "external": EXTERNAL_SERVICES,
        }

    def _svc_to_dict(self, svc: ServiceInfo) -> dict:
        return {
            "name": svc.name,
            "runtime": svc.runtime,
            "status": svc.status,
            "pid": svc.pid,
            "memory_mb": svc.memory_mb,
            "cpu_percent": svc.cpu_percent,
            "uptime_seconds": svc.uptime_seconds,
            "restarts": svc.restarts,
            "last_error": svc.last_error,
        }


# Singleton
_manager: ServiceManager | None = None


def get_manager() -> ServiceManager:
    """Retorna singleton do ServiceManager."""
    global _manager
    if _manager is None:
        _manager = ServiceManager()
    return _manager


def list_services() -> list[ServiceInfo]:
    """Retorna status de todos os servicos FraLib."""
    mgr = get_manager()
    return [mgr.status(s) for s in FRA_SERVICES]


def detect_runtime() -> str:
    """Retorna o runtime primario: systemd, pm2 ou none."""
    mgr = get_manager()
    if mgr.has_systemd and any(
        mgr._systemd_unit_exists(s) for s in FRA_SERVICES
    ):
        return "systemd"
    if mgr.has_pm2:
        return "pm2"
    return "none"


if __name__ == "__main__":
    # CLI: python -m backend.services.service_manager status
    import sys
    mgr = get_manager()
    if len(sys.argv) < 2:
        print(json.dumps(mgr.summary(), indent=2, default=str))
    else:
        cmd = sys.argv[1]
        if cmd == "status":
            name = sys.argv[2] if len(sys.argv) > 2 else FRA_SERVICES[0]
            info = mgr.status(name)
            print(json.dumps(mgr._svc_to_dict(info), indent=2))
        elif cmd == "logs":
            name = sys.argv[2] if len(sys.argv) > 2 else FRA_SERVICES[0]
            lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            print(mgr.logs(name, lines))
        elif cmd == "restart":
            name = sys.argv[2] if len(sys.argv) > 2 else FRA_SERVICES[0]
            ok, msg = mgr.restart(name)
            print(f"{'OK' if ok else 'FAIL'}: {msg}")
        else:
            print(f"Comandos: status [name], logs [name] [N], restart [name]")