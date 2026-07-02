"""Testes Sprint 4.1 — stress test deterministico do race condition
outbound x inbound.

O fix das Sprints 1.2 + 1.5 adicionou 3 helpers no
``backend/services/outbound_queue.py``:

* ``_check_last_inbound_vs_outbound(engine, lead_id, tenant_id)`` — le
  ``interacoes`` e devolve ``True`` se ``last_inbound_at > last_outbound_at``.
* ``set_cooldown(lead_key)`` — grava Redis ``fralib:lead_cooldown:{lead_key}``
  com TTL 60s.
* ``increment_daily_count(tenant_id, lead_id)`` — incrementa
  ``fralib:outbound_daily:{tenant_id}:{lead_id}`` com TTL 24h.

Estes testes cobrem o contrato DETERMINISTICO do fix usando ``MagicMock``
para engines SQLAlchemy e Redis client (mesma convencao do
``tests/unit/test_franz_top3_bugs.py``).

Nenhum teste depende de Postgres ou Redis real.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── bootstrap path/env (mesmo padrao dos outros unit tests) ─────────────
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/test",
)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))


# ══════════════════════════════════════════════════════════════════════════
# Helpers — fake engine/connection que reconhecem queries especificas
# ══════════════════════════════════════════════════════════════════════════


class _FakeConn:
    """Conexao minimalista compativel com ``engine.connect()``.

    O parametro ``interacoes_row`` controla o que a query
    ``SELECT ... FROM interacoes WHERE lead_id=:lid AND user_id=:tid``
    devolve (a que ``_check_last_inbound_vs_outbound`` faz). Se for
    ``None``, devolve ``fetchone() = None``. Para os demais SQLs,
    devolve tuplas vazias (a coluna ``interacoes`` nao deve afetar
    o resto do fluxo).
    """

    def __init__(
        self,
        interacoes_row: tuple[datetime | None, datetime | None] | None = None,
    ) -> None:
        self.commits = 0
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self._interacoes_row = interacoes_row

    def execute(self, sql: Any, params: dict[str, Any] | None = None) -> MagicMock:
        stmt: str = getattr(sql, "text", None) or str(sql)
        self.executed.append((stmt, params or {}))
        result = MagicMock()

        # Query de interacoes (checagem last_inbound vs last_outbound).
        if "FROM interacoes" in stmt and "lead_id = :lid" in stmt:
            result.fetchone.return_value = self._interacoes_row
            result.fetchall.return_value = (
                [self._interacoes_row] if self._interacoes_row else []
            )
            result.scalar.return_value = 1 if self._interacoes_row else 0
            result.rowcount = 1 if self._interacoes_row else 0
            return result

        # Demais queries — comportamento neutro.
        result.fetchall.return_value = []
        result.fetchone.return_value = None
        result.scalar.return_value = 0
        result.rowcount = 0
        return result

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return False


class _FakeEngine:
    """Engine fake com ``.connect()`` que devolve uma ``_FakeConn``.

    ``connect_factory`` opcional permite injetar a conexao — util quando
    o teste precisa variar o resultado entre chamadas.
    """

    def __init__(
        self,
        interacoes_row: tuple[datetime | None, datetime | None] | None = None,
        conn: _FakeConn | None = None,
    ) -> None:
        self._interacoes_row = interacoes_row
        self._conn = conn

    def connect(self) -> _FakeConn:
        if self._conn is not None:
            return self._conn
        return _FakeConn(interacoes_row=self._interacoes_row)


def _now() -> datetime:
    return datetime(2026, 7, 2, 12, 0, 0)


# ══════════════════════════════════════════════════════════════════════════
# Tests — _check_last_inbound_vs_outbound (3 testes)
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCheckLastInboundVsOutbound:
    """Sprint 1.2 — Bug #3: helper deve retornar ``True`` quando
    ``last_inbound_at > last_outbound_at`` (lead respondeu apos o
    ultimo outbound). Em caso de erro, deve retornar ``False``
    (fail-open)."""

    def test_check_last_inbound_vs_outbound_returns_true_after_response(self) -> None:
        """last_inbound > last_outbound → retorna True."""
        from backend.services.outbound_queue import _check_last_inbound_vs_outbound

        last_outbound = _now() - timedelta(minutes=10)
        last_inbound = _now() - timedelta(minutes=2)
        engine = _FakeEngine(interacoes_row=(last_inbound, last_outbound))

        assert _check_last_inbound_vs_outbound(engine, "lead-x", 42) is True

    def test_check_last_inbound_vs_outbound_returns_false_when_no_outbound(self) -> None:
        """Sem outbound (last_outbound = None) e com inbound → True.
        Cobre tambem o caminho ``if not row: return False`` quando
        nao ha nenhuma interacao."""
        from backend.services.outbound_queue import _check_last_inbound_vs_outbound

        # Caso A: nenhuma interacao (fetchone = None) → fail-open False.
        engine_empty = _FakeEngine(interacoes_row=None)
        assert _check_last_inbound_vs_outbound(engine_empty, "lead-x", 42) is False

        # Caso B: so inbound, sem outbound → True (lead respondeu,
        # nunca houve outbound).
        engine_only_inbound = _FakeEngine(interacoes_row=(_now(), None))
        assert (
            _check_last_inbound_vs_outbound(engine_only_inbound, "lead-x", 42)
            is True
        )

    def test_check_last_inbound_vs_outbound_returns_false_on_db_error(self) -> None:
        """engine.connect() levanta Exception → False (fail-safe)."""
        from backend.services.outbound_queue import _check_last_inbound_vs_outbound

        engine = MagicMock()
        engine.connect.side_effect = Exception("simulated DB outage")

        # Nao pode levantar — tem que retornar False.
        result = _check_last_inbound_vs_outbound(engine, "lead-x", 42)
        assert result is False


# ══════════════════════════════════════════════════════════════════════════
# Tests — set_cooldown (2 testes)
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestSetCooldown:
    """Sprint 1.2 — Bug #3: ``set_cooldown`` deve gravar Redis
    ``fralib:lead_cooldown:{lead_key}`` com TTL 60s."""

    def test_set_cooldown_sets_redis_key_with_60s_ttl(self) -> None:
        """Com Redis up, chama ``setex(key, 60, '1')``."""
        from backend.services.outbound_queue import set_cooldown

        fake_redis = MagicMock()
        with patch(
            "backend.agents.sdr_langgraph.lead_lock.get_redis_client",
            return_value=fake_redis,
        ):
            set_cooldown("42:lead-x")

        fake_redis.setex.assert_called_once_with(
            "fralib:lead_cooldown:42:lead-x", 60, "1",
        )

    def test_set_cooldown_warns_and_returns_on_redis_offline(self) -> None:
        """get_redis_client retorna None → loga warning mas nao levanta."""
        from backend.services.outbound_queue import set_cooldown

        with patch(
            "backend.agents.sdr_langgraph.lead_lock.get_redis_client",
            return_value=None,
        ):
            # Nao pode levantar exception.
            set_cooldown("42:lead-x")


# ══════════════════════════════════════════════════════════════════════════
# Tests — increment_daily_count (1 teste)
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestIncrementDailyCount:
    """Sprint 1.2 — Bug #3: ``increment_daily_count`` deve chamar
    ``incr`` + ``expire(key, 86400)`` no Redis."""

    def test_increment_daily_uses_redis_incr_with_86400_ttl(self) -> None:
        """Com Redis up, chama ``incr`` + ``expire(key, 86400)``."""
        from backend.services.outbound_queue import increment_daily_count

        fake_redis = MagicMock()
        with patch(
            "backend.agents.sdr_langgraph.lead_lock.get_redis_client",
            return_value=fake_redis,
        ):
            increment_daily_count(42, "lead-x")

        expected_key = "fralib:outbound_daily:42:lead-x"
        fake_redis.incr.assert_called_once_with(expected_key)
        fake_redis.expire.assert_called_once_with(expected_key, 86400)


# ══════════════════════════════════════════════════════════════════════════
# Tests — dequeue_and_send com _check_last_inbound retornando True (1 teste)
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestDequeueSkipsWhenLeadResponded:
    """Sprint 4.1 — stress test deterministico: quando
    ``last_inbound_at > last_outbound_at`` (configurado via fake engine
    apontando para uma linha de ``interacoes``), o worker deve:

    1. NAO chamar ``sender_func``.
    2. Retornar ``skipped=1`` e ``sent=0``.
    3. Atualizar ``outbound_queue.status='skipped'`` via UPDATE.
    """

    def test_dequeue_and_send_skips_when_lead_responded(self) -> None:
        """Validacao ponta-a-ponta do fix."""
        from backend.services.outbound_queue import dequeue_and_send

        # Conexao que devolve 1 row em FOR UPDATE SKIP LOCKED (a pending
        # msg) e o par (last_inbound, last_outbound) na query de
        # interacoes.
        last_outbound = _now() - timedelta(minutes=10)
        last_inbound = _now() - timedelta(minutes=2)

        # Lista que a query FOR UPDATE SKIP LOCKED devolve:
        # (id, tenant_id, lead_id, phone, message, source, attempts)
        pending_rows: list[tuple[Any, ...]] = [
            (101, 42, "lead-x", "5511999999999", "msg-x", "franz", 1),
        ]

        # Build a fake connection que cobre AMBAS as queries:
        conn = _PendingAndInteracoesConn(
            pending_rows=pending_rows,
            interacoes_row=(last_inbound, last_outbound),
        )
        engine = _FakeEngine(conn=conn)

        sender_calls: list[tuple[Any, ...]] = []

        def fake_sender(phone: Any, message: Any, tenant_id: Any = None) -> bool:
            sender_calls.append((phone, message, tenant_id))
            return True

        result = dequeue_and_send(engine, fake_sender)

        # Sender NAO pode ter sido chamado.
        assert sender_calls == [], (
            f"sender NAO deveria ser chamado quando lead respondeu, "
            f"got {sender_calls}"
        )

        # Resultado deve indicar skip, nao envio.
        assert result.get("skipped") == 1, (
            f"skipped deveria ser 1, got {result}"
        )
        assert result.get("sent") == 0, (
            f"sent deveria ser 0, got {result}"
        )

        # E o UPDATE para status='skipped' deve ter sido executado.
        skipped_updates = [
            (stmt, params)
            for stmt, params in conn.executed
            if "UPDATE outbound_queue" in stmt and "'skipped'" in stmt
        ]
        assert len(skipped_updates) >= 1, (
            f"esperava UPDATE status='skipped' para outbound_queue, "
            f"got executed={conn.executed}"
        )
        # E o filtro WHERE id=:id AND status='pending' deve estar la.
        skipped_stmt, _ = skipped_updates[0]
        assert "status = 'pending'" in skipped_stmt
        assert "INTERVAL '60 minutes'" in skipped_stmt


class _PendingAndInteracoesConn(_FakeConn):
    """Conexao fake que devolve pending_rows na query de
    ``FOR UPDATE SKIP LOCKED`` e ``interacoes_row`` na query de
    ``interacoes``. Para os demais SQLs, comportamento neutro."""

    def __init__(
        self,
        pending_rows: list[tuple[Any, ...]],
        interacoes_row: tuple[datetime | None, datetime | None] | None,
    ) -> None:
        super().__init__(interacoes_row=interacoes_row)
        self._pending_rows = pending_rows

    def execute(self, sql: Any, params: dict[str, Any] | None = None) -> MagicMock:
        stmt: str = getattr(sql, "text", None) or str(sql)
        self.executed.append((stmt, params or {}))
        result = MagicMock()

        # Query de interacoes.
        if "FROM interacoes" in stmt and "lead_id = :lid" in stmt:
            result.fetchone.return_value = self._interacoes_row
            result.fetchall.return_value = (
                [self._interacoes_row] if self._interacoes_row else []
            )
            result.scalar.return_value = 1 if self._interacoes_row else 0
            result.rowcount = 1 if self._interacoes_row else 0
            return result

        # Query FOR UPDATE SKIP LOCKED do worker outbound.
        if "FOR UPDATE SKIP LOCKED" in stmt and "outbound_queue" in stmt:
            result.fetchall.return_value = list(self._pending_rows)
            result.fetchone.return_value = (
                self._pending_rows[0] if self._pending_rows else None
            )
            result.scalar.return_value = len(self._pending_rows)
            result.rowcount = len(self._pending_rows)
            return result

        # UPDATE/INSERT — sempre "afetam 1 linha".
        result.fetchall.return_value = []
        result.fetchone.return_value = None
        result.scalar.return_value = 0
        result.rowcount = 1
        return result
