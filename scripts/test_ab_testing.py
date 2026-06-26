"""Testes do sistema de A/B testing + re-engajamento."""

import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from backend.services.ab_testing import (
    choose_variant,
    should_reengange,
    generate_reengagement_message,
    get_variant_report,
    find_abandoned_leads,
    VariantMetrics,
)


class TestVariantChoice(unittest.TestCase):
    """Escolha de variant baseada em performance."""

    def test_cold_start_returns_a_b_c_or_d(self):
        """Sem dados, retorna random entre A/B/C/D."""
        with patch("backend.services.ab_testing._load_variant_metrics", return_value={}):
            for _ in range(20):
                v = choose_variant(user_id=1)
                self.assertIn(v, ["A", "B", "C", "D"])

    def test_with_metrics_picks_best(self):
        """Com dados, escolhe variant com maior conversion_rate."""
        metrics = {
            "A": VariantMetrics(variant="A", sent=10, responses=5, conversions=2),  # 20%
            "B": VariantMetrics(variant="B", sent=10, responses=7, conversions=5),  # 50%
            "C": VariantMetrics(variant="C", sent=10, responses=3, conversions=0),  # 0%
        }
        with patch("backend.services.ab_testing._load_variant_metrics", return_value=metrics), \
             patch("backend.services.ab_testing.random") as mock_random:
            mock_random.random.return_value = 0.5  # nao exploration
            v = choose_variant(user_id=1)
            # B tem maior conversion_rate
            # Como random.random() = 0.5 > 0.10, nao e exploration
            # Escolhe B
            self.assertEqual(v, "B")

    def test_exploration_10_percent(self):
        """10% das vezes faz exploration (random)."""
        metrics = {
            "A": VariantMetrics(variant="A", sent=10, conversions=10),  # 100%
        }
        with patch("backend.services.ab_testing._load_variant_metrics", return_value=metrics), \
             patch("backend.services.ab_testing.random") as mock_random:
            mock_random.random.return_value = 0.05  # < 0.10 = exploration
            mock_random.choice.return_value = "X"
            v = choose_variant(user_id=1)
            # Como e < 0.10, faz exploration -> random.choice
            self.assertEqual(v, "X")


class TestReengagementDecision(unittest.TestCase):
    """Decisao de re-engajar lead."""

    def test_3_dias_nao_reengaje(self):
        """Menos de 7 dias = fresh, nao re-engaja."""
        self.assertFalse(should_reengange(3))

    def test_5_dias_nao_reengaje(self):
        self.assertFalse(should_reengange(5))

    def test_7_dias_reengaja(self):
        self.assertTrue(should_reengange(7))

    def test_15_dias_reengaja(self):
        self.assertTrue(should_reengange(15))

    def test_30_dias_reengaja(self):
        self.assertTrue(should_reengange(30))

    def test_45_dias_nao_reengaja(self):
        """Mais de 30 dias = muito frio, nao re-engaja (evita spam)."""
        self.assertFalse(should_reengange(45))


class TestReengagementMessage(unittest.TestCase):
    """Gera msg de re-engajamento personalizada (NUNCA template fixo)."""

    def test_msg_contem_nome(self):
        lead = {"nome": "Joao Silva", "segmento": "academia", "days_idle": 10, "last_lead_msg": "oi"}
        msg = generate_reengagement_message(lead)
        self.assertIn("Joao", msg)  # primeiro nome
        self.assertNotIn("Silva", msg)  # sobrenome NAO

    def test_msg_15_dias_e_diferente_de_7_dias(self):
        """Mensagens devem variar baseado em days_idle."""
        lead_7 = {"nome": "X", "segmento": "", "days_idle": 7, "last_lead_msg": ""}
        lead_15 = {"nome": "X", "segmento": "", "days_idle": 15, "last_lead_msg": ""}
        self.assertNotEqual(
            generate_reengagement_message(lead_7),
            generate_reengagement_message(lead_15),
            "Mensagens devem variar com tempo",
        )

    def test_msg_referencia_atleta_se_lead_mencionou(self):
        lead = {"nome": "Maria", "segmento": "academia", "days_idle": 10, "last_lead_msg": "Tenho interesse em atletas"}
        msg = generate_reengagement_message(lead)
        # Deve referenciar atletas
        self.assertTrue("atleta" in msg.lower() or "esport" in msg.lower())

    def test_msg_referencia_preco_se_lead_mencionou(self):
        lead = {"nome": "Maria", "segmento": "academia", "days_idle": 10, "last_lead_msg": "Qual o valor?"}
        msg = generate_reengagement_message(lead)
        # Deve referenciar preco/valor
        self.assertTrue("valor" in msg.lower() or "preço" in msg.lower() or "preco" in msg.lower())


class TestVariantReport(unittest.TestCase):
    """Relatorio de variants pra dashboard."""

    def test_report_vazio(self):
        with patch("backend.services.ab_testing._load_variant_metrics", return_value={}):
            r = get_variant_report(user_id=1)
            self.assertEqual(r["total_sent"], 0)
            self.assertEqual(r["total_conversions"], 0)
            self.assertIsNone(r["best_variant"])
            self.assertEqual(len(r["variants"]), 0)

    def test_report_com_dados(self):
        metrics = {
            "A": VariantMetrics(variant="A", sent=100, responses=40, conversions=5),
            "B": VariantMetrics(variant="B", sent=100, responses=60, conversions=15),
        }
        with patch("backend.services.ab_testing._load_variant_metrics", return_value=metrics):
            r = get_variant_report(user_id=1)
            self.assertEqual(r["total_sent"], 200)
            self.assertEqual(r["total_conversions"], 20)
            self.assertEqual(r["best_variant"], "B")
            # 20/200 = 10%
            self.assertEqual(r["total_conversion_rate"], 10.0)
            # Ordenado por conversion_rate desc
            self.assertEqual(r["variants"][0]["variant"], "B")


class TestFindAbandonedLeads(unittest.TestCase):
    """Encontrar leads parados."""

    def test_sem_leads(self):
        with patch("backend.core.database.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchall.return_value = []
            result = find_abandoned_leads(user_id=1, days_idle=7)
            self.assertEqual(result, [])

    def test_com_lead_abandonado(self):
        mock_row = ("lead-uuid", "Maria Nutricionista", "5511999", "nutricao", "followup1", None, 10, "oi")
        with patch("backend.core.database.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchall.return_value = [mock_row]
            result = find_abandoned_leads(user_id=1, days_idle=7)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["lead_id"], "lead-uuid")
            self.assertEqual(result[0]["days_idle"], 10)
            self.assertEqual(result[0]["segmento"], "nutricao")


if __name__ == "__main__":
    unittest.main(verbosity=2)