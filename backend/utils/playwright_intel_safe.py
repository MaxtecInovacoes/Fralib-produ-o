"""Async-safe wrapper for Playwright Intel search.

Playwright Sync API nao pode ser rodada em thread com asyncio loop compartilhado
(mesmo com ThreadPoolExecutor). Solução: executar buscar_inteligencia_mercado
em subprocess Python ISOLADO via script file (sem -c), eliminando qualquer
interferencia de event loop.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any


_RUNNER_TEMPLATE = '''"""Auto-generated runner for Playwright Intel (safe-mode subprocess)."""
import json
import sys
import traceback

try:
    import backend.utils.playwright_intel as _pi  # noqa
except Exception:
    sys.path.insert(0, ".")
    import backend.utils.playwright_intel as _pi  # noqa

if __name__ == "__main__":
    payload = json.loads(sys.stdin.read())
    try:
        intel = _pi.buscar_inteligencia_mercado(
            payload.get("nicho", ""),
            payload.get("cidade", ""),
            payload.get("nome_negocio", "") or "",
            payload.get("concorrentes_urls") or [],
            payload.get("tenant_id"),
        )
        insights = _pi.formatar_inteligencia_para_arquiteto(intel)
        sys.stdout.write(json.dumps({"ok": True, "intel": intel, "insights": insights}))
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "ok": False,
            "error": str(exc)[:500],
            "tb": traceback.format_exc()[:500],
        }))
'''


def buscar_inteligencia_mercado_safe(
    *,
    nicho: str,
    cidade: str,
    nome_negocio: str = "",
    concorrentes_urls: list[str] | None = None,
    tenant_id: int | None = None,
    timeout_seconds: int = 75,
) -> dict[str, Any]:
    """Chama buscar_inteligencia_mercado num subprocess Python isolado.

    Escreve o runner em arquivo .py (evita problemas de parsing do -c).
    Retorna dict com chaves: insights, intel, error.
    NUNCA levanta exception — sempre retorna dict.
    """
    payload = {
        "nicho": nicho,
        "cidade": cidade,
        "nome_negocio": nome_negocio,
        "concorrentes_urls": concorrentes_urls or [],
        "tenant_id": tenant_id,
    }
    work_dir = "/root/fralib" if os.path.isdir("/root/fralib") else os.getcwd()
    runner_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix="playwright_runner_", dir=work_dir, delete=False,
        ) as f:
            f.write(_RUNNER_TEMPLATE)
            runner_path = f.name
        try:
            proc = subprocess.run(
                [sys.executable, runner_path],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=work_dir,
            )
        finally:
            try:
                if runner_path and os.path.exists(runner_path):
                    os.unlink(runner_path)
            except Exception:
                pass
        if proc.returncode != 0:
            return {
                "ok": False,
                "intel": {},
                "insights": "",
                "error": (proc.stderr or "")[-300:] or "subprocess falhou",
            }
        out = (proc.stdout or "").strip()
        if not out:
            return {
                "ok": False,
                "intel": {},
                "insights": "",
                "error": "subprocess sem stdout",
            }
        result = json.loads(out)
        if not result.get("ok"):
            return {
                "ok": False,
                "intel": {},
                "insights": "",
                "error": result.get("error", "subprocess retornou ok=False"),
            }
        return {
            "ok": True,
            "intel": result.get("intel", {}),
            "insights": result.get("insights", ""),
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False, "intel": {}, "insights": "",
            "error": "timeout no subprocess",
        }
    except Exception as exc:
        return {
            "ok": False, "intel": {}, "insights": "",
            "error": str(exc)[:300],
        }
