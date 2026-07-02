"""Testes unitários para o smoke test pós-deploy (Sprint 0.2).

Valida o script `tools/smoke_test.py` sem fazer chamadas de rede reais.
Mocka `httpx.AsyncClient` para responder de forma determinística.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Adicionar tools/ ao path para importar o módulo
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import smoke_test  # noqa: E402  (path manipulated acima)


logger = logging.getLogger(__name__)


def _run(coro: Any) -> Any:
    """Helper para rodar coroutine em testes síncronos."""
    return asyncio.run(coro)


# ── Fixtures & helpers ───────────────────────────────────────────────


@dataclass(frozen=True)
class _FakeResponse:
    """Mínimo compatível com httpx.Response para os checks do smoke."""

    status_code: int
    payload: dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def json(self) -> dict[str, Any]:
        return self.payload


def _make_async_client_mock(responses: list[_FakeResponse]) -> AsyncMock:
    """Cria um AsyncMock que devolve a próxima resposta da fila a cada get/post.

    Suporta tanto o uso como context manager (`async with AsyncClient(...) as c:`)
    quanto chamadas diretas em get/post.
    """
    queue = list(responses)
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    async def _next(*_args: Any, **_kwargs: Any) -> _FakeResponse:
        if not queue:
            raise AssertionError("Mock de AsyncClient ficou sem respostas")
        return queue.pop(0)

    client.get = AsyncMock(side_effect=_next)
    client.post = AsyncMock(side_effect=_next)
    return client


# ── 1. /api/health ────────────────────────────────────────────────────


@pytest.mark.unit
def test_smoke_health_endpoint_returns_200() -> None:
    """Health endpoint retorna 200 e marca como PASS."""
    health_ok = _FakeResponse(status_code=200, payload={"status": "ok"})
    db_ok = _FakeResponse(status_code=200, payload={"result": 1})
    login_ok = _FakeResponse(status_code=200, payload={"access_token": "x"})
    meow_ok = _FakeResponse(status_code=200, payload={"status": "ok"})
    llm_ok = _FakeResponse(status_code=200, payload={"content": [{"text": "ok"}]})

    client_mock = _make_async_client_mock([health_ok, db_ok, login_ok, meow_ok, llm_ok])

    with patch.object(smoke_test, "httpx") as httpx_mod:
        httpx_mod.AsyncClient.return_value = client_mock
        # MOCK também a parte de DB e LLM para não chamar rede
        with patch.object(smoke_test, "_check_db_select_1", return_value=True):
            with patch.object(
                smoke_test, "_check_llm_ping", new=AsyncMock(return_value=True)
            ):
                rc = smoke_test.run_smoke(env="dev", base_url="http://x", timeout=5.0)

    assert rc == 0, f"Esperava exit code 0, veio {rc}"


# ── 2. DB SELECT 1 ────────────────────────────────────────────────────


@pytest.mark.unit
def test_smoke_db_select_1() -> None:
    """DB SELECT 1 retorna 1 quando a conexão está saudável."""
    fake_pool = MagicMock()
    fake_conn = MagicMock()
    fake_result = MagicMock()
    fake_result.scalar.return_value = 1
    fake_conn.execute.return_value = fake_result

    fake_pool.connect.return_value.__enter__.return_value = fake_conn
    fake_pool.connect.return_value.__exit__.return_value = None

    with patch.object(smoke_test, "create_engine", return_value=fake_pool):
        out = smoke_test._check_db_select_1("postgresql://x")

    assert out is True


# ── 3. meowhats localhost:3001 ────────────────────────────────────────


@pytest.mark.unit
def test_smoke_meowhats_localhost_3001() -> None:
    """meowhats /health em localhost:3001 responde 200 via AsyncClient."""
    fake_response = _FakeResponse(status_code=200, payload={"status": "ok"})
    client_mock = _make_async_client_mock([fake_response])

    with patch.object(smoke_test, "httpx") as httpx_mod:
        httpx_mod.AsyncClient.return_value = client_mock
        result = _run(smoke_test._check_meowhats("http://127.0.0.1:3001", timeout=5.0))

    assert result is True


# ── 4. LLM Haiku ping ────────────────────────────────────────────────


@pytest.mark.unit
def test_smoke_llm_haiku_ok() -> None:
    """LLM ping com claude-haiku-4-5 recebe 'ok' como resposta."""
    fake_response = _FakeResponse(
        status_code=200,
        payload={"content": [{"type": "text", "text": "ok"}]},
    )
    client_mock = _make_async_client_mock([fake_response])

    with patch.object(smoke_test, "httpx") as httpx_mod:
        httpx_mod.AsyncClient.return_value = client_mock
        result = _run(smoke_test._check_llm_ping("test-key", model="claude-haiku-4-5"))

    assert result is True


# ── 5. Exit code success ─────────────────────────────────────────────


@pytest.mark.unit
def test_exit_code_success() -> None:
    """Todos os checks PASS → run_smoke devolve 0."""
    health_ok = _FakeResponse(status_code=200, payload={"status": "ok"})
    login_ok = _FakeResponse(status_code=200, payload={"access_token": "t"})
    meow_ok = _FakeResponse(status_code=200, payload={"status": "ok"})

    client_mock = _make_async_client_mock([health_ok, login_ok, meow_ok])

    with patch.object(smoke_test, "httpx") as httpx_mod:
        httpx_mod.AsyncClient.return_value = client_mock
        with patch.object(smoke_test, "_check_db_select_1", return_value=True):
            with patch.object(
                smoke_test, "_check_llm_ping", new=AsyncMock(return_value=True)
            ):
                rc = smoke_test.run_smoke(env="dev", base_url="http://x", timeout=5.0)

    assert rc == 0


# ── 6. Exit code failure ─────────────────────────────────────────────


@pytest.mark.unit
def test_exit_code_failure() -> None:
    """Algum check FAIL → run_smoke devolve 1."""
    health_fail = _FakeResponse(status_code=500, payload={"error": "boom"})
    login_ok = _FakeResponse(status_code=200, payload={"access_token": "t"})
    meow_ok = _FakeResponse(status_code=200, payload={"status": "ok"})

    client_mock = _make_async_client_mock([health_fail, login_ok, meow_ok])

    with patch.object(smoke_test, "httpx") as httpx_mod:
        httpx_mod.AsyncClient.return_value = client_mock
        with patch.object(smoke_test, "_check_db_select_1", return_value=True):
            with patch.object(
                smoke_test, "_check_llm_ping", new=AsyncMock(return_value=True)
            ):
                rc = smoke_test.run_smoke(env="dev", base_url="http://x", timeout=5.0)

    assert rc == 1


# ── Bonus: argparse parsing ──────────────────────────────────────────


@pytest.mark.unit
def test_argparse_defaults() -> None:
    """Parser CLI aceita apenas o subcomando env com defaults sensatos."""
    args = smoke_test.build_parser().parse_args(["dev"])
    assert args.env == "dev"
    assert args.timeout == 5.0
    assert args.base_url is None  # resolvido depois a partir de env


@pytest.mark.unit
def test_argparse_full() -> None:
    """Parser aceita --base-url e --timeout customizados."""
    args = smoke_test.build_parser().parse_args(
        ["staging", "--base-url", "http://x:9000", "--timeout", "10.5"]
    )
    assert args.env == "staging"
    assert args.base_url == "http://x:9000"
    assert args.timeout == 10.5
