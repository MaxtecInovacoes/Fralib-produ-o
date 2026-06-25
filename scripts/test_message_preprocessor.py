"""Testes do pre-processador de mensagens do WhatsApp."""

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from whatsapp.message_preprocessor import (
    classify_incoming_message,
    should_franz_respond,
    MessageType,
)


class TestBotDetection(unittest.TestCase):
    """Detecta bots/assistentes virtuais que devem ser redirecionados."""

    def test_monica_nutri_aline(self):
        """Msg da Monica (assistente da Nutri Aline) - print 5."""
        msg = (
            "Ola!! Seja bem vinda(o) [sparkles]\n\n"
            "Meu nome e Monica e sou a assistente da Nutri Aline!\n\n"
            "Meus horarios de atendimento sao de segunda a sexta: 9h as 12h e 14h as 17h.\n\n"
            "Em breve irei te responder"
        )
        r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT, f"got {r.msg_type}: {r.signals}")
        self.assertGreater(r.confidence, 0.7)
        self.assertEqual(r.action, "handoff")

    def test_curitiba_fitness_welcome(self):
        """Msg automatica de boas-vindas - print 3."""
        msg = (
            "Ola! Seja Bem-vindo a Academia Curitiba Fitness. "
            "Em alguns minutos a nossa equipe entrara em contato. "
            "Por favor, nos informe seu nome e em que podemos ajudar."
        )
        r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT)
        self.assertEqual(r.action, "handoff")

    def test_doctorfit_ausente(self):
        """Msg de recepcao fora do horario - print 1."""
        msg = (
            "Ola, que bom que entrou em contato conosco! "
            "Infelizmente a recepcao encontra-se fora do horario de atendimento, "
            "retornaremos o seu contato assim que possivel, "
            "obrigada pela compreensao [green heart]"
        )
        r = classify_incoming_message(msg)
        self.assertIn(r.msg_type, (MessageType.AUTO_AUSENTE, MessageType.BOT_ASSISTANT))
        self.assertEqual(r.action, "no_response")


class TestMidiaSemTexto(unittest.TestCase):
    """Detecta mídia sem texto."""

    def test_midia_placeholder(self):
        for placeholder in ["[mídia]", "[midia]", "[imagem]", "[audio]", "[vídeo]"]:
            r = classify_incoming_message(placeholder)
            self.assertEqual(r.msg_type, MessageType.MIDIA_SEM_TEXTO, f"placeholder={placeholder}")

    def test_empty(self):
        r = classify_incoming_message("")
        self.assertEqual(r.msg_type, MessageType.MIDIA_SEM_TEXTO)
        r = classify_incoming_message(None)
        self.assertEqual(r.msg_type, MessageType.MIDIA_SEM_TEXTO)


class TestOptOutDetection(unittest.TestCase):
    """Detecta opt-out claro (msg curta e explicita)."""

    def test_nao_quero_mais_receber(self):
        r = classify_incoming_message("Nao quero mais receber contato")
        self.assertEqual(r.msg_type, MessageType.OPT_OUT)
        self.assertEqual(r.action, "no_response")

    def test_me_tira_do_contato(self):
        r = classify_incoming_message("Me tira do contato")
        self.assertEqual(r.msg_type, MessageType.OPT_OUT)

    def test_pare_de_me_mandar(self):
        r = classify_incoming_message("Pare de me mandar mensagens")
        self.assertEqual(r.msg_type, MessageType.OPT_OUT)

    def test_parar_curto(self):
        r = classify_incoming_message("parar")
        self.assertEqual(r.msg_type, MessageType.OPT_OUT)


class TestMsgRealLead(unittest.TestCase):
    """Mensagens normais de lead DEVEM ir pro Franz."""

    def test_saudacao_simples(self):
        r = classify_incoming_message("Oi, tudo bem?")
        self.assertEqual(r.msg_type, MessageType.LEAD_REAL)
        self.assertEqual(r.action, "forward_to_franz")

    def test_pergunta_sobre_servico(self):
        r = classify_incoming_message("Quanto custa o site?")
        self.assertEqual(r.msg_type, MessageType.LEAD_REAL)
        self.assertEqual(r.action, "forward_to_franz")

    def test_interesse_compra(self):
        r = classify_incoming_message("Tenho interesse, pode mandar mais informacoes?")
        self.assertEqual(r.msg_type, MessageType.LEAD_REAL)
        self.assertEqual(r.action, "forward_to_franz")

    def test_msg_engagement_longa(self):
        """Msg real de lead com +30 palavras (como a Jaqueline)."""
        msg = (
            "Jaque Vieira Vicente Nutricionista agradecemos seu contato, "
            "me envie o seu objetivo dentro da Nutricao para eu entender "
            "como consigo te ajudar"
        )
        r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.LEAD_REAL)
        self.assertEqual(r.action, "forward_to_franz")


class TestHelper(unittest.TestCase):
    """Testa o helper should_franz_respond."""

    def test_lead_real_franz_responde(self):
        should, auto = should_franz_respond("Oi, tudo bem?")
        self.assertTrue(should)
        self.assertIsNone(auto)

    def test_bot_franz_nao_responde_com_auto(self):
        should, auto = should_franz_respond(
            "Meu nome e Monica e sou assistente. Horarios: 9h-17h"
        )
        self.assertFalse(should)
        self.assertIsNotNone(auto)
        self.assertIn("responsavel", auto.lower())

    def test_ausente_franz_nao_responde(self):
        should, auto = should_franz_respond(
            "Estamos fora do horario. Retornaremos o contato."
        )
        self.assertFalse(should)
        self.assertIsNone(auto)  # silencio


if __name__ == "__main__":
    unittest.main(verbosity=2)