"""Testes do sistema de fila outbound + rate limit."""

import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from backend.services.outbound_queue import (
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW_SEC,
    enqueue_outbound,
    get_pending_count,
    get_recent_sent_count,
    can_send_now,
    dequeue_and_send,
    cleanup_old_messages,
    schedule_next_batch,
    process_queue_once,
)


def _mock_engine_with_rows(rows):
    """Cria engine mock que retorna rows especificos em queries."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = rows
    mock_conn.execute.return_value.fetchone.return_value = (0,)
    mock_conn.execute.return_value.scalar.return_value = 0
    mock_conn.execute.return_value.rowcount = 0
    return mock_engine


class TestRateLimitConfig(unittest.TestCase):
    """Configuracao do rate limit."""

    def test_max_2_por_janela(self):
        """Max 2 msgs por janela de 10 min."""
        self.assertEqual(RATE_LIMIT_MAX, 2)
        self.assertEqual(RATE_LIMIT_WINDOW_SEC, 600)


class TestCanSendNow(unittest.TestCase):
    """can_send_now: verifica se pode enviar msg agora."""

    def test_pode_enviar_quando_nenhuma_enviada(self):
        """Se nenhuma msg foi enviada, pode enviar."""
        with patch("backend.services.outbound_queue.get_recent_sent_count", return_value=0):
            can, wait = can_send_now(MagicMock(), tenant_id=1)
        self.assertTrue(can)
        self.assertEqual(wait, 0)

    def test_nao_pode_enviar_se_atingiu_limite(self):
        """Se ja enviou 2 msgs, nao pode enviar mais."""
        with patch("backend.services.outbound_queue.get_recent_sent_count", return_value=2):
            mock_engine = MagicMock()
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            # Mock da query que pega sent_at
            mock_conn.execute.return_value.fetchone.return_value = (datetime.now(),)
            can, wait = can_send_now(mock_engine, tenant_id=1)
        self.assertFalse(can)
        self.assertGreater(wait, 0)
        self.assertLessEqual(wait, RATE_LIMIT_WINDOW_SEC)


class TestEnqueueOutbound(unittest.TestCase):
    """enqueue_outbound: adiciona msg na fila."""

    def test_enqueue_com_delay_zero(self):
        """Enqueue com delay=0 vai pra scheduled_at=agora."""
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (123,)

        with patch("backend.services.outbound_queue.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 26, 12, 0, 0)
            msg_id = enqueue_outbound(
                engine, tenant_id=1, lead_id="L1", phone="5511",
                message="ola", priority=5, delay_sec=0,
            )
        self.assertEqual(msg_id, 123)

    def test_enqueue_com_delay_5min(self):
        """Enqueue com delay=300s vai pra scheduled_at=agora+5min."""
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (456,)

        msg_id = enqueue_outbound(
            engine, tenant_id=1, lead_id="L1", phone="5511",
            message="ola", delay_sec=300,
        )
        self.assertEqual(msg_id, 456)


class TestDequeueAndSend(unittest.TestCase):
    """dequeue_and_send: pega 1 msg e envia."""

    def test_envia_com_sucesso(self):
        """Se sender retorna True, marca como 'sent'."""
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [(1, 1, "L1", "5511", "msg", "franz", 0)]
        # Mock 2: UPDATE para marcar como sending
        # Mock 3: UPDATE para marcar como sent

        sender = MagicMock(return_value=True)

        with patch("backend.services.outbound_queue.can_send_now", return_value=(True, 0)):
            result = dequeue_and_send(engine, sender)

        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)

    def test_bloqueia_se_rate_limit(self):
        """Se can_send_now retornar False, nao envia."""
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [(1, 1, "L1", "5511", "msg", "franz", 0)]

        sender = MagicMock(return_value=True)

        with patch("backend.services.outbound_queue.can_send_now", return_value=(False, 120)):
            result = dequeue_and_send(engine, sender)

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["waiting_sec"], 120)
        sender.assert_not_called()

    def test_sender_falha_marca_failed(self):
        """Se sender retorna False, marca como 'failed'."""
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [(1, 1, "L1", "5511", "msg", "franz", 0)]

        sender = MagicMock(return_value=False)

        with patch("backend.services.outbound_queue.can_send_now", return_value=(True, 0)):
            result = dequeue_and_send(engine, sender)

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["failed"], 1)

    def test_sender_explode_marca_failed(self):
        """Se sender joga exception, marca como 'failed'."""
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [(1, 1, "L1", "5511", "msg", "franz", 0)]

        sender = MagicMock(side_effect=Exception("timeout"))

        with patch("backend.services.outbound_queue.can_send_now", return_value=(True, 0)):
            result = dequeue_and_send(engine, sender)

        self.assertEqual(result["failed"], 1)


class TestGetPendingCount(unittest.TestCase):
    """get_pending_count: conta msgs pendentes."""

    def test_retorna_0_quando_vazio(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = 0
        self.assertEqual(get_pending_count(engine), 0)

    def test_retorna_5_quando_tem_5(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = 5
        self.assertEqual(get_pending_count(engine), 5)


class TestCleanupOldMessages(unittest.TestCase):
    """cleanup_old_messages: remove msgs antigas."""

    def test_remove_msgs_antigas(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.rowcount = 42
        deleted = cleanup_old_messages(engine, days=7)
        self.assertEqual(deleted, 42)


if __name__ == "__main__":
    unittest.main(verbosity=2)