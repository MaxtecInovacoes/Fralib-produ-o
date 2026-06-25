"""Testes do aprendizado passivo do Franz.

Aprendizado por observacao: detecta sinais automaticamente (reclamacoes,
engajamento, opt-out cancelado) e cria lessons injetadas no proximo prompt.
Inspirado em Meta WhatsApp Business AI, Chatwoot AI, Respond.io.
"""

import sys
import unittest
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# Usar tmpdir pros testes nao poluirem memoria real
TEST_USER_ID = 99999

from agents.sdr_langgraph import learning


class TestLeadComplaintDetection(unittest.TestCase):
    """Detecta reclamacao do lead e cria lesson."""

    def test_voce_entendeu_errado(self):
        result = learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_complaint_1",
            lead_message="Voce entendeu errado, eu nao falei isso",
        )
        self.assertTrue(result["learned"])
        self.assertIn("misunderstanding", result["kinds"])

    def test_sua_ia_nao_entendeu(self):
        result = learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_complaint_2",
            lead_message="Sua IA nao entendeu muito moço",
        )
        self.assertTrue(result["learned"])
        self.assertIn("ai_blame", result["kinds"])

    def test_para_de_me_mandar(self):
        result = learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_complaint_3",
            lead_message="Para de me mandar mensagem",
        )
        self.assertTrue(result["learned"])
        self.assertIn("explicit_stop", result["kinds"])

    def test_chega_cansei(self):
        result = learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_complaint_4",
            lead_message="Chega, cansei desse atendimento",
        )
        self.assertTrue(result["learned"])
        self.assertIn("frustration", result["kinds"])

    def test_msg_normal_nao_lesson(self):
        """Msg de lead NORMAL nao deve virar lesson."""
        result = learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_normal",
            lead_message="Quanto custa o site?",
        )
        self.assertFalse(result["learned"])


class TestLeadEngagementDetection(unittest.TestCase):
    """Detecta engajamento positivo e replica abordagem."""

    def test_quero_ver(self):
        result = learning.record_lead_engagement(
            user_id=TEST_USER_ID,
            lead_id="L_eng_1",
            lead_message="Quero ver o site",
            previous_bot_message="Posso te mostrar como ficaria?",
        )
        self.assertTrue(result["learned"])
        self.assertIn("engagement", result["kinds"])

    def test_aceito(self):
        result = learning.record_lead_engagement(
            user_id=TEST_USER_ID,
            lead_id="L_eng_2",
            lead_message="Aceito, pode mandar",
        )
        self.assertTrue(result["learned"])
        self.assertIn("buying_signal", result["kinds"])

    def test_otimo(self):
        result = learning.record_lead_engagement(
            user_id=TEST_USER_ID,
            lead_id="L_eng_3",
            lead_message="Otimo, gostei!",
        )
        self.assertTrue(result["learned"])
        self.assertIn("praise", result["kinds"])

    def test_msg_neutra_nao_lesson(self):
        result = learning.record_lead_engagement(
            user_id=TEST_USER_ID,
            lead_id="L_neutra",
            lead_message="Quanto custa?",
        )
        self.assertFalse(result["learned"])


class TestOptOutCanceled(unittest.TestCase):
    """Detecta quando lead cancela opt_out e salva lesson."""

    def test_nao_cancela(self):
        result = learning.record_opt_out_canceled(
            user_id=TEST_USER_ID,
            lead_id="L_cancel_1",
            bot_question="Voce quer parar?",
            lead_response="nao",
        )
        self.assertTrue(result["learned"])
        self.assertEqual(result["lesson_key"], "opt_out_false_positive")

    def test_continua_cancela(self):
        result = learning.record_opt_out_canceled(
            user_id=TEST_USER_ID,
            lead_id="L_cancel_2",
            bot_question="Voce quer parar?",
            lead_response="continua, gostei do atendimento",
        )
        self.assertTrue(result["learned"])

    def test_sim_nao_cancela(self):
        """'sim' confirma, nao cancela."""
        result = learning.record_opt_out_canceled(
            user_id=TEST_USER_ID,
            lead_id="L_cancel_3",
            bot_question="Voce quer parar?",
            lead_response="sim, quero parar",
        )
        self.assertFalse(result["learned"])
        self.assertEqual(result["reason"], "not_cancel")


class TestLearningOverlay(unittest.TestCase):
    """Verifica que learning_overlay retorna as lessons certas."""

    def test_overlay_contem_complaint_e_engagement(self):
        # Forca adicao de 2 lessons
        learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_overlay_1",
            lead_message="Voce entendeu errado",
        )
        learning.record_lead_engagement(
            user_id=TEST_USER_ID,
            lead_id="L_overlay_2",
            lead_message="Quero ver",
            previous_bot_message="Posso mostrar",
        )

        overlay = learning.learning_overlay(TEST_USER_ID)

        # Overlay deve ter content
        self.assertIn("SDR LEARNING MEMORY", overlay)
        # Deve mencionar pelo menos uma das lessons
        self.assertTrue(
            "entendeu" in overlay.lower() or "quero ver" in overlay.lower(),
            f"Overlay missing both lessons: {overlay[:300]}",
        )


class TestLearningRealScenario(unittest.TestCase):
    """Cenário real do bug da Carolina Ragugnetti.

    Lead envia msg normal de qualificação ('nao atendo atletas').
    Depois envia msg de reclamacao ('sua IA nao entendeu').
    Verifica que lesson de complaint foi criada.
    """

    def test_carolina_full_flow(self):
        # Step 1: Lead classifica (Franz ainda vai classificar errado como opt_out por causa do LLM)
        # Aqui so testamos que a lesson de complaint foi criada depois

        # Step 2: Lead reclama
        result = learning.record_lead_complaint(
            user_id=TEST_USER_ID,
            lead_id="L_carolina",
            lead_message="Sua IA nao entendeu muito moço",
            previous_bot_message="Entendido! Vou remover seu contato",
            context="stage=intro; segmento=nutricao",
        )
        self.assertTrue(result["learned"])
        # Verifica que lesson de opt_out_false_positive tambem pode ser criada
        learning.record_opt_out_canceled(
            user_id=TEST_USER_ID,
            lead_id="L_carolina",
            bot_question="Voce quer parar?",
            lead_response="nao, continua",
        )

        # Overlay deve ter as lessons (procura pelo texto, nao pela chave)
        overlay = learning.learning_overlay(TEST_USER_ID)
        self.assertIn("opt_out", overlay.lower())
        self.assertIn("classificar", overlay.lower())
        # E a lesson de complaint
        self.assertIn("entendeu", overlay.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)