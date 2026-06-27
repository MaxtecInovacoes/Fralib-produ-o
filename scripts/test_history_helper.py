"""Testes do helper de contexto completo."""

import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from backend.whatsapp.history_helper import (
    get_full_history,
    get_context_with_summary,
    MAX_HISTORY,
    SUMMARY_THRESHOLD,
)


class TestGetFullHistory(unittest.TestCase):
    """Carrega contexto completo (ate 100 msgs)."""

    def test_vazio_retorna_lista_vazia(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        result = get_full_history(engine, "L1", 1)
        self.assertEqual(result, [])

    def test_carrega_ate_100_msgs(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        # Simula 50 mensagens
        rows = [
            (f"msg {i}", "saida" if i % 2 == 0 else "entrada", datetime.now() - timedelta(seconds=50 - i))
            for i in range(50)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        result = get_full_history(engine, "L1", 1)
        self.assertEqual(len(result), 50)

    def test_ordem_cronologica_crescente(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        # 3 msgs, ordem reversa (mais recente primeiro)
        rows = [
            ("msg 3 (recent)", "entrada", datetime.now()),
            ("msg 2 (middle)", "saida", datetime.now() - timedelta(seconds=10)),
            ("msg 1 (oldest)", "entrada", datetime.now() - timedelta(seconds=20)),
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        result = get_full_history(engine, "L1", 1)
        # Deve estar em ordem cronologica (oldest first)
        self.assertIn("msg 1 (oldest)", result[0]["content"])
        self.assertIn("msg 3 (recent)", result[-1]["content"])

    def test_role_correto(self):
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        # Daqui: row[0] = mais recente (depois reverter)
        # Apos reverse(): row[-1] vira primeiro = mais antigo
        rows = [
            ("lead respondeu (recent)", "entrada", datetime.now()),
            ("franz disse (oldest)", "saida", datetime.now() - timedelta(seconds=5)),
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        result = get_full_history(engine, "L1", 1)
        # Apos reverse: franz disse (saida=assistant) deve ser o primeiro
        self.assertEqual(result[0]["role"], "assistant")
        self.assertEqual(result[1]["role"], "user")


class TestGetContextWithSummary(unittest.TestCase):
    """Context com summary se > SUMMARY_THRESHOLD."""

    def test_poucas_msgs_sem_summary(self):
        engine = MagicMock()
        with patch("backend.whatsapp.history_helper.get_full_history") as mock:
            mock.return_value = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
            result = get_context_with_summary(engine, "L1", 1)
        # Sem summary, retorna direto
        self.assertEqual(len(result), 10)
        self.assertNotIn("system", result[0]["role"])

    def test_muitas_msgs_com_summary(self):
        engine = MagicMock()
        with patch("backend.whatsapp.history_helper.get_full_history") as mock, \
             patch("backend.whatsapp.sdr_reply_service._summarize_history") as mock_sum:
            mock.return_value = [{"role": "user", "content": f"msg {i}"} for i in range(50)]
            mock_sum.return_value = "Lead quer fazer site"
            result = get_context_with_summary(engine, "L1", 1)
        # Deve ter summary no topo + recentes
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]["role"], "system")
        self.assertIn("Lead quer fazer site", result[0]["content"])

    def test_summary_falha_retorna_recentes(self):
        engine = MagicMock()
        with patch("backend.whatsapp.history_helper.get_full_history") as mock, \
             patch("backend.whatsapp.sdr_reply_service._summarize_history") as mock_sum:
            mock.return_value = [{"role": "user", "content": f"msg {i}"} for i in range(50)]
            mock_sum.return_value = ""  # Falha
            result = get_context_with_summary(engine, "L1", 1)
        # Sem summary, retorna as recentes
        self.assertEqual(len(result), SUMMARY_THRESHOLD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
