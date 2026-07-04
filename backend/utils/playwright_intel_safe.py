"""Async-safe wrapper for Playwright Intel search.

Playwright Sync API nao pode ser rodada em thread com asyncio loop compartilhado
(mesmo com ThreadPoolExecutor). Solucao: executar buscar_inteligencia_mercado
em subprocess Python ISOLADO via script file (sem -c), eliminando qualquer
interferencia de event loop.

O subprocess imprime logs em stdout ANTES do JSON final. Para extrair o JSON
de forma confiavel, usamos marcador [JSON_BEGIN]/[JSON_END].
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
import os
import sys
import traceback

# Garante que backend.* seja importavel no subprocess
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_PARENT = os.path.dirname(_THIS_DIR)
if _BACKEND_PARENT not in sys.path:
    sys.path.insert(0, _BACKEND_PARENT)

try:
    import backend.utils.playwright_intel as _pi  # noqa
except Exception:
    sys.path.insert(0, ".")
    import backend.utils.playwright_intel as _pi  # noqa

_BEGIN = "[JSON_BEGIN]"
_END = "[JSON_END]"

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
        # Logs do helper vao pro stdout via print, antes do marcador
        sys.stdout.write(_BEGIN + json.dumps({"ok": True, "intel": intel, "insights": insights}) + _END)
    except Exception as exc:
        sys.stdout.write(_BEGIN + json.dumps({
            "ok": False,
            "error": str(exc)[:500],
        }) + _END)
'''


def _extract_json(stdout: str) -> dict[str, Any] | None:
    """Extrai JSON delimitado por [JSON_BEGIN]/[JSON_END]."""
    start = stdout.rfind("[JSON_BEGIN]")
    end = stdout.rfind("[JSON_END]")
    if start < 0 or end < 0 or end <= start:
        return None
    body = stdout[start + len("[JSON_BEGIN]"):end]
    try:
        return json.loads(body)
    except Exception:
        return None


def buscar_inteligencia_mercado_safe(
    *,
    nicho: str,
    cidade: str,
    nome_negocio: str = "",
    concorrentes_urls: list[str] | None = None,
    tenant_id: int | None = None,
    timeout_seconds: int = 75,
) -> dict[str, Any]:
    """Chama buscar_inteligencia_mercado num subprocess Python isolado."""
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
        if proc.returncode != 0 and not proc.stdout:
            return {
                "ok": False,
                "intel": {},
                "insights": "",
                "error": (proc.stderr or "")[-300:] or "subprocess falhou (rc != 0)",
            }
        out = proc.stdout or ""
        result = _extract_json(out)
        if result is None:
            return {
                "ok": False,
                "intel": {},
                "insights": "",
                "error": "subprocess nao retornou JSON delimitado (rc=%d)" % proc.returncode,
            }
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
