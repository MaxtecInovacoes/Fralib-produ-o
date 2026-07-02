"""Smoke test pós-deploy (Sprint 0.2).

Verifica, em <30s, que os endpoints críticos e provedores externos do Fralib
estão respondendo após um deploy. Uso:

    python tools/smoke_test.py dev
    python tools/smoke_test.py staging --base-url http://api.staging:8000
    python tools/smoke_test.py production --timeout 10

Exit code 0 se TODOS os checks passarem; 1 caso contrário (CI-friendly).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx
from sqlalchemy import create_engine, text

logger = logging.getLogger("smoke_test")


# ── Configuração ──────────────────────────────────────────────────────


_DEFAULT_BASE_URLS: dict[str, str] = {
    "dev": "http://127.0.0.1:8000",
    "staging": os.getenv("STAGING_BASE_URL", "http://127.0.0.1:8000"),
    "production": os.getenv("PROD_BASE_URL", "http://127.0.0.1:8000"),
}

_DEFAULT_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/fralib")
_DEFAULT_MEOWHATS_URL = os.getenv("MEOWHATS_URL", "http://127.0.0.1:3001")
_DEFAULT_LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_DEFAULT_LLM_MODEL = "claude-haiku-4-5"

# Credenciais dummy para /api/auth/login (a maioria dos endpoints
# de smoke test não exige credencial válida; só validamos que
# o endpoint responde e devolve um JSON bem-formado).
_DUMMY_EMAIL = "smoke@fralib.local"
_DUMMY_PASSWORD = "smoke-test-dummy"


# ── Dataclasses de resultado ──────────────────────────────────────────


@dataclass(frozen=True)
class CheckResult:
    """Resultado de um check individual."""

    endpoint: str
    latency_ms: float
    status: str  # 'PASS' | 'FAIL'
    error: str = ""


# ── Helpers HTTP / DB / LLM ───────────────────────────────────────────


async def _http_get(
    client: httpx.AsyncClient, url: str, timeout: float
) -> tuple[httpx.Response | None, float, str]:
    """GET com medição de latência. Devolve (response, latency_ms, error)."""
    start = time.perf_counter()
    try:
        resp = await client.get(url, timeout=timeout)
        latency = (time.perf_counter() - start) * 1000.0
        return resp, latency, ""
    except Exception as exc:  # noqa: BLE001
        latency = (time.perf_counter() - start) * 1000.0
        return None, latency, f"{type(exc).__name__}: {exc}"


async def _http_post(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[httpx.Response | None, float, str]:
    """POST com medição de latência."""
    start = time.perf_counter()
    try:
        resp = await client.post(url, json=payload, timeout=timeout)
        latency = (time.perf_counter() - start) * 1000.0
        return resp, latency, ""
    except Exception as exc:  # noqa: BLE001
        latency = (time.perf_counter() - start) * 1000.0
        return None, latency, f"{type(exc).__name__}: {exc}"


def _check_db_select_1(db_url: str) -> bool:
    """DB ping: SELECT 1. Retorna True se a query retornar 1."""
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            row = conn.execute(text("SELECT 1")).scalar()
        return row == 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB check falhou: %s", exc)
        return False


async def _check_meowhats(base_url: str, timeout: float) -> bool:
    """GET /health no meowhats (porta 3001 por padrão)."""
    url = f"{base_url.rstrip('/')}/health"
    async with httpx.AsyncClient() as client:
        resp, _latency, err = await _http_get(client, url, timeout)
    if err or resp is None:
        logger.warning("meowhats /health falhou: %s", err)
        return False
    return resp.status_code == 200


async def _check_llm_ping(api_key: str, model: str, timeout: float = 10.0) -> bool:
    """LLM ping: manda 'ok' para o modelo e checa se volta 'ok'."""
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY ausente; pulando LLM check")
        return False

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "ok"}],
    }
    async with httpx.AsyncClient() as client:
        resp, _latency, err = await _http_post(client, url, payload, timeout)
    if err or resp is None:
        logger.warning("LLM ping falhou: %s", err)
        return False
    if resp.status_code != 200:
        return False
    try:
        data = resp.json()
        content_blocks = data.get("content", [])
        text = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        ).strip().lower()
        return "ok" in text
    except Exception:  # noqa: BLE001
        return False


# ── Checks principais ────────────────────────────────────────────────


async def _check_health(client: httpx.AsyncClient, base_url: str, timeout: float) -> CheckResult:
    resp, latency, err = await _http_get(client, f"{base_url}/api/health", timeout)
    if err:
        return CheckResult("GET /api/health", latency, "FAIL", err)
    assert resp is not None
    ok = resp.status_code == 200
    return CheckResult(
        "GET /api/health",
        latency,
        "PASS" if ok else "FAIL",
        "" if ok else f"status={resp.status_code}",
    )


async def _check_login(client: httpx.AsyncClient, base_url: str, timeout: float) -> CheckResult:
    resp, latency, err = await _http_post(
        client,
        f"{base_url}/api/auth/login",
        {"email": _DUMMY_EMAIL, "password": _DUMMY_PASSWORD},
        timeout,
    )
    if err:
        return CheckResult("POST /api/auth/login", latency, "FAIL", err)
    assert resp is not None
    # Aceita 200 (login OK) OU 401/422 (credencial dummy rejeitada — endpoint está vivo)
    ok = resp.status_code in (200, 401, 422)
    return CheckResult(
        "POST /api/auth/login",
        latency,
        "PASS" if ok else "FAIL",
        "" if ok else f"status={resp.status_code}",
    )


async def _check_meowhats_endpoint(
    client: httpx.AsyncClient, base_url: str, timeout: float
) -> CheckResult:
    url = f"{_DEFAULT_MEOWHATS_URL.rstrip('/')}/health"
    resp, latency, err = await _http_get(client, url, timeout)
    if err:
        return CheckResult("GET meowhats:3001/health", latency, "FAIL", err)
    assert resp is not None
    ok = resp.status_code == 200
    return CheckResult(
        "GET meowhats:3001/health",
        latency,
        "PASS" if ok else "FAIL",
        "" if ok else f"status={resp.status_code}",
    )


# ── Orquestrador ─────────────────────────────────────────────────────


async def _run_all_checks(
    base_url: str,
    timeout: float,
    db_url: str,
    llm_api_key: str,
    llm_model: str,
    meowhats_url: str,
) -> list[CheckResult]:
    """Roda todos os checks em paralelo e devolve os CheckResult."""
    results: list[CheckResult] = []

    async with httpx.AsyncClient() as client:
        health_task = asyncio.create_task(_check_health(client, base_url, timeout))
        login_task = asyncio.create_task(_check_login(client, base_url, timeout))
        meow_task = asyncio.create_task(
            _check_meowhats_endpoint(client, meowhats_url, timeout)
        )
        results.extend(await asyncio.gather(health_task, login_task, meow_task))

    # DB e LLM rodam fora do client compartilhado (SQLAlchemy + Anthropic)
    db_start = time.perf_counter()
    db_ok = _check_db_select_1(db_url)
    db_latency = (time.perf_counter() - db_start) * 1000.0
    results.append(
        CheckResult(
            "DB SELECT 1",
            db_latency,
            "PASS" if db_ok else "FAIL",
            "" if db_ok else "query returned non-1 or exception",
        )
    )

    llm_start = time.perf_counter()
    llm_ok = await _check_llm_ping(llm_api_key, llm_model, timeout=min(timeout, 10.0))
    llm_latency = (time.perf_counter() - llm_start) * 1000.0
    results.append(
        CheckResult(
            f"LLM {llm_model}",
            llm_latency,
            "PASS" if llm_ok else "FAIL",
            "" if llm_ok else "no 'ok' in response or auth/timeout",
        )
    )

    return results


def _print_table(results: list[CheckResult]) -> None:
    """Imprime tabela formatada com endpoint | latência | status | erro."""
    headers = ("ENDPOINT", "LATÊNCIA (ms)", "STATUS", "ERRO")
    rows: list[tuple[str, str, str, str]] = [
        (r.endpoint, f"{r.latency_ms:7.1f}", r.status, r.error) for r in results
    ]

    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(4)
    ]

    def _fmt(cells: tuple[str, str, str, str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    logger.info("%s", _fmt(headers))
    logger.info("%s", sep)
    for row in rows:
        logger.info("%s", _fmt(row))

    passed = sum(1 for r in results if r.status == "PASS")
    total = len(results)
    logger.info("%s", sep)
    logger.info("Resultado: %d/%d PASS", passed, total)


def run_smoke(
    env: str,
    base_url: str | None,
    timeout: float,
    *,
    db_url: str = _DEFAULT_DB_URL,
    llm_api_key: str = _DEFAULT_LLM_API_KEY,
    llm_model: str = _DEFAULT_LLM_MODEL,
    meowhats_url: str = _DEFAULT_MEOWHATS_URL,
) -> int:
    """Entry point síncrono. Retorna exit code (0 ok, 1 falha)."""
    resolved_base = base_url or _DEFAULT_BASE_URLS.get(env, _DEFAULT_BASE_URLS["dev"])
    logger.info(
        "Smoke test — env=%s base=%s timeout=%.1fs",
        env,
        resolved_base,
        timeout,
    )

    try:
        results = asyncio.run(
            asyncio.wait_for(
                _run_all_checks(
                    resolved_base,
                    timeout,
                    db_url,
                    llm_api_key,
                    llm_model,
                    meowhats_url,
                ),
                timeout=30.0,
            )
        )
    except asyncio.TimeoutError:
        logger.error("Timeout global de 30s atingido — abortando")
        return 1

    _print_table(results)
    return 0 if all(r.status == "PASS" for r in results) else 1


# ── CLI ──────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smoke_test",
        description="Smoke test pós-deploy do Fralib (Sprint 0.2).",
    )
    parser.add_argument(
        "env",
        choices=("dev", "staging", "production"),
        help="Ambiente alvo (define a base URL default).",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override da base URL (default: derivado de env)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout por endpoint em segundos (default: 5.0)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args = build_parser().parse_args(argv)
    return run_smoke(env=args.env, base_url=args.base_url, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
