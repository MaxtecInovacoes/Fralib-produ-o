"""Async-safe wrapper for Playwright Intel search.

Playwright Sync API conflita com asyncio loop do worker/Python 3.13.
Solucao: multiprocessing com context='spawn' cria processo 100% isolado
(sem loop, sem cache de event loop, sem heranca de estado).

O processo-filho recebe o payload via arquivo temporario (stdin nao eh
herdado com spawn), executa buscar_inteligencia_mercado, e escreve o
resultado em outro arquivo temp.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import tempfile
import traceback
from typing import Any


def _playwright_runner(payload_path: str, result_path: str) -> None:
    """Executado no processo-filho (spawn) — contexto 100% limpo."""
    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        nicho = payload.get("nicho", "")
        cidade = payload.get("cidade", "")
        nome_negocio = payload.get("nome_negocio", "") or ""
        concorrentes_urls = payload.get("concorrentes_urls") or []
        tenant_id = payload.get("tenant_id")

        # Importacao tardia para evitar qualquer inicializacao async prematura
        try:
            import backend.utils.playwright_intel as _pi
        except Exception:
            # Fallback: adicionar cwd ao path
            _cwd = os.getcwd()
            if _cwd not in sys.path:
                sys.path.insert(0, _cwd)
            import importlib
            _pi = importlib.import_module("backend.utils.playwright_intel")

        intel = _pi.buscar_inteligencia_mercado(
            nicho,
            cidade,
            nome_negocio,
            concorrentes_urls,
            tenant_id,
        )
        insights = _pi.formatar_inteligencia_para_arquiteto(intel)

        result = {"ok": True, "intel": intel, "insights": insights, "error": None}
    except Exception as exc:
        result = {
            "ok": False,
            "intel": {},
            "insights": "",
            "error": f"{type(exc).__name__}: {exc}",
        }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)


def buscar_inteligencia_mercado_safe(
    *,
    nicho: str,
    cidade: str,
    nome_negocio: str = "",
    concorrentes_urls: list[str] | None = None,
    tenant_id: int | None = None,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    """Executa buscar_inteligencia_mercado num processo isolado (spawn)."""
    payload = {
        "nicho": nicho,
        "cidade": cidade,
        "nome_negocio": nome_negocio,
        "concorrentes_urls": concorrentes_urls or [],
        "tenant_id": tenant_id,
    }

    payload_path = None
    result_path = None

    try:
        # Criar arquivos temp no diretorio de trabalho
        work_dir = "/root/fralib" if os.path.isdir("/root/fralib") else os.getcwd()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="pw_payload_", dir=work_dir, delete=False,
        ) as pf:
            json.dump(payload, pf)
            payload_path = pf.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="pw_result_", dir=work_dir, delete=False,
        ) as rf:
            result_path = rf.name

        # multiprocessing spawn = processo completamente limpo
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_playwright_runner, args=(payload_path, result_path))
        proc.start()
        proc.join(timeout=timeout_seconds)

        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            return {
                "ok": False, "intel": {}, "insights": "",
                "error": "timeout no subprocess (Playwright)",
            }

        if proc.exitcode != 0:
            return {
                "ok": False, "intel": {}, "insights": "",
                "error": f"subprocess saiu com rc={proc.exitcode}",
            }

        if not os.path.exists(result_path):
            return {
                "ok": False, "intel": {}, "insights": "",
                "error": "result file not created",
            }

        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        if not result.get("ok"):
            return {
                "ok": False, "intel": {}, "insights": "",
                "error": result.get("error", "subprocess retornou ok=False"),
            }

        return {
            "ok": True,
            "intel": result.get("intel", {}),
            "insights": result.get("insights", ""),
            "error": None,
        }

    except mp.TimeoutError:
        return {"ok": False, "intel": {}, "insights": "", "error": "timeout no subprocess"}
    except Exception as exc:
        return {"ok": False, "intel": {}, "insights": "", "error": str(exc)[:300]}
    finally:
        for _p in (payload_path, result_path):
            if _p and os.path.exists(_p):
                try:
                    os.unlink(_p)
                except Exception:
                    pass
