#!/usr/bin/env python3
"""
Limpeza diaria VPS FraLib.
Roda todo dia as 3h da manha via cron. Limpa:
- /tmp/node-compile-cache (Node recria quando precisa)
- /tmp/*.log e /tmp/*.jsonl com mais de 7 dias
- /var/log/fralib-*.log maiores que 100MB (trunca)
- Vacuum journal 7 dias
- go clean -cache (recria quando precisa)
- Remove imagens Docker dangling

Roda via: /root/fralib/venv/bin/python3 /root/fralib/scripts/cleanup_daily.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_PREFIX = "[cleanup_daily]"


def log(msg: str) -> None:
    print(f"{LOG_PREFIX} {datetime.now().isoformat()} {msg}", flush=True)


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as exc:
        return -1, "", str(exc)


def cleanup_tmp() -> None:
    """Limpa /tmp com mais de 7 dias. NAO apaga arquivos recentes (pode estar em uso)."""
    tmp = Path("/tmp")
    cutoff = datetime.now() - timedelta(days=7)
    freed = 0
    count = 0
    for f in tmp.iterdir():
        try:
            if not f.is_file():
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                size = f.stat().st_size
                f.unlink()
                freed += size
                count += 1
        except Exception as exc:
            log(f"  skip {f.name}: {exc}")
    log(f"  tmp: {count} arquivos, {freed // 1024 // 1024} MB liberados")


def cleanup_node_cache() -> None:
    """Apaga /tmp/node-compile-cache (Node recria)."""
    cache = Path("/tmp/node-compile-cache")
    if cache.exists():
        try:
            size = sum(f.stat().st_size for f in cache.rglob("*") if f.is_file())
            import shutil
            shutil.rmtree(cache)
            log(f"  node-compile-cache: {size // 1024 // 1024} MB liberados")
        except Exception as exc:
            log(f"  node-compile-cache skip: {exc}")


def truncate_big_logs() -> None:
    """Trunca logs do fralib-worker maiores que 100MB."""
    logs = [
        Path("/var/log/fralib-worker.log"),
        Path("/var/log/postgresql/postgresql-15-main.log"),
    ]
    for logf in logs:
        if logf.exists() and logf.stat().st_size > 100 * 1024 * 1024:
            old_size = logf.stat().st_size
            try:
                with open(logf, "w"):
                    pass
                log(f"  truncate {logf.name}: {old_size // 1024 // 1024} MB -> 0")
            except Exception as exc:
                log(f"  truncate {logf.name} skip: {exc}")


def vacuum_journal() -> None:
    """Vacuum systemd journal para 7 dias."""
    rc, _, _ = run(["journalctl", "--vacuum-time=7d"], timeout=60)
    if rc == 0:
        log("  journal: vacuum 7d OK")
    else:
        log(f"  journal: vacuum falhou (rc={rc})")


def go_clean() -> None:
    """Limpa cache do Go (reconstroi em build)."""
    # /root/go e o GOROOT do usuario que constroi whatsmeow
    go_pkg = Path("/root/go/pkg/mod/cache")
    if go_pkg.exists():
        try:
            size = sum(f.stat().st_size for f in go_pkg.rglob("*") if f.is_file())
            import shutil
            shutil.rmtree(go_pkg)
            log(f"  go cache: {size // 1024 // 1024} MB liberados")
        except Exception as exc:
            log(f"  go cache skip: {exc}")


def docker_dangling() -> None:
    """Remove Docker dangling images (sem tag)."""
    rc, out, _ = run(["docker", "image", "prune", "-f"], timeout=120)
    if rc == 0:
        # Extrai "Total reclaimed space" do output
        for line in out.split("\n"):
            if "reclaimed" in line.lower():
                log(f"  docker: {line.strip()}")
                return
        log("  docker: dangling images removidas")


def main() -> int:
    log("iniciando limpeza diaria")
    cleanup_node_cache()
    cleanup_tmp()
    truncate_big_logs()
    vacuum_journal()
    go_clean()
    docker_dangling()
    log("limpeza concluida")
    return 0


if __name__ == "__main__":
    sys.exit(main())