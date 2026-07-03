"""Atomic file writes — write→fsync→rename + lock per arquivo.

Garante que crash entre open() e json.dump() NAO corrompe o arquivo original.
Substitui `open(path, "w")` + `json.dump()` direto que deixa o arquivo truncado
em caso de OOM kill / power loss / KeyboardInterrupt.

Funciona em:
  - POSIX (Linux/Mac): usa fcntl.flock
  - Windows: usa msvcrt locking
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Set


# Lock global por path (threading.Lock) — usado como fallback quando SO lock nao funciona
# No Windows, os.replace falha com PermissionError quando 2 threads tentam renomear
# arquivos temporarios ao mesmo tempo, entao usamos um lock por path pra serializar.
_PATH_LOCKS: Dict[str, threading.Lock] = {}
_PATH_LOCKS_MUTEX = threading.Lock()


def _get_path_lock(path: str) -> threading.Lock:
    """Retorna (ou cria) um threading.Lock por path."""
    with _PATH_LOCKS_MUTEX:
        lock = _PATH_LOCKS.get(path)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[path] = lock
        return lock


@contextmanager
def file_lock(path: str):
    """Lock por arquivo (per-process; suficiente pra workers do mesmo tenant).

    Combina: threading.Lock (cross-platform) + fcntl.flock (POSIX) / msvcrt (Windows).

    Yields o file descriptor aberto (caller NAO precisa fechar — contextmanager cuida).
    """
    # Primeiro acquire o threading.Lock por path (cross-platform, sempre funciona)
    path_lock = _get_path_lock(path)
    path_lock.acquire()
    try:
        lock_path = path + ".lock"
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        try:
            if sys.platform == "win32":
                try:
                    import msvcrt  # type: ignore
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                except (ImportError, OSError):
                    pass
            else:
                try:
                    import fcntl  # type: ignore
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (ImportError, OSError):
                    pass
            yield fd
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
    finally:
        path_lock.release()


def _atomic_write_bytes(path: str, data: bytes) -> None:
    """Escreve `data` em `path` atomicamente.

    Algoritmo:
      1. Escreve em arquivo temporario no mesmo diretorio (rename atomico exige mesmo FS)
      2. fsync() pra forcar dados no disco
      3. os.replace() (atomico no mesmo FS) sobre o path final
      4. Remove o temp file em caso de erro
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=directory, prefix=".tmp_", suffix=os.path.basename(path)
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: str, data: Dict[str, Any], *, indent: int = 2) -> None:
    """Escreve JSON atomicamente. Se crash entre open() e rename(), arquivo original intacto.

    Usage:
        atomic_write_json("/path/memoria.json", {"key": "value"})
    """
    payload = json.dumps(data, indent=indent, ensure_ascii=False).encode("utf-8")
    with file_lock(path):
        _atomic_write_bytes(path, payload)
