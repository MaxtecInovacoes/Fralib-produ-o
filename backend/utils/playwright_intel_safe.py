"""Async-safe wrapper for Playwright Intel search.

Playwright Sync API nao pode ser chamada de uma thread que seja a mesma do
asyncio loop (mesmo com ThreadPoolExecutor). Este modulo cria um subprocess
isolado que faz a busca e retorna o resultado via JSON, eliminando a
interferencia do event loop.
"""

from __future__ import annotations

import json
import subprocess
import sys
import os
from typing import Any


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

    Retorna dict com chaves: insights, intel, error.
    NUNCA levanta exception — sempre retorna dict (error pode estar setado).
    """
    payload = {
        "nicho": nicho,
        "cidade": cidade,
        "nome_negocio": nome_negocio,
        "concorrentes_urls": concorrentes_urls or [],
        "tenant_id": tenant_id,
    }
    code = (
        "import sys, json, traceback;"
        "sys.path.insert(0, '.');"
        "from backend.utils.playwright_intel import buscar_inteligencia_mercado, formatar_inteligencia_para_arquiteto;"
        "p = json.loads(sys.stdin.read());"
        "try:"
        "  intel = buscar_inteligencia_mercado(p['nicho'], p['cidade'], p['nome_negocio'], p['concorrentes_urls'], p['tenant_id']);"
        "  insights = formatar_inteligencia_para_arquiteto(intel);"
        "  sys.stdout.write(json.dumps({'ok': True, 'intel': intel, 'insights': insights}));"
        "except Exception as e:"
        "  sys.stdout.write(json.dumps({'ok': False, 'error': str(e)[:500]}));"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd="/root/fralib" if os.path.isdir("/root/fralib") else os.getcwd(),
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "intel": {},
                "insights": "",
                "error": (proc.stderr or "")[-300:] or "subprocess falhou",
            }
        if not proc.stdout.strip():
            return {"ok": False, "intel": {}, "insights": "", "error": "subprocess sem stdout"}
        result = json.loads(proc.stdout)
        if not result.get("ok"):
            return {"ok": False, "intel": {}, "insights": "",
                    "error": result.get("error", "subprocess retornou ok=False")}
        return {
            "ok": True,
            "intel": result.get("intel", {}),
            "insights": result.get("insights", ""),
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "intel": {}, "insights": "", "error": "timeout no subprocess"}
    except Exception as exc:
        return {"ok": False, "intel": {}, "insights": "", "error": str(exc)[:300]}
