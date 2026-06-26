"""Testes do pre-processador de mensagens do WhatsApp.

Estrategia hibrida: regex + heuristica + LLM Haiku.

Testes cobrem:
- N1 (regex): opt-out, midia sem texto, ausencia
- N2 (heuristica): features detectam bot obvio
- N3 (LLM mockado): juiz final pra casos ambiguos
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from whatsapp.message_preprocessor import (
    classify_incoming_message,
    should_franz_respond,
    MessageType,
    _heuristic_features,
    _heuristic_bot_score,
)


class TestBotDetection(unittest.TestCase):
    """Detecta bots/assistentes virtuais que devem ser redirecionados."""

    def _mock_llm(self, tipo="BOT_ASSISTANT", confianca=0.95):
        """Mock do LLM pra evitar chamadas reais (lentidao/custo)."""
        return patch(
            "whatsapp.message_preprocessor._llm_classify_cached",
            return_value=(tipo, confianca, "mocked")
        )

    def test_monica_nutri_aline(self):
        """Msg da Monica (assistente da Nutri Aline) - print 5."""
        msg = (
            "Ola!! Seja bem vinda(o) [sparkles]\n\n"
            "Meu nome e Monica e sou a assistente da Nutri Aline!\n\n"
            "Meus horarios de atendimento sao de segunda a sexta: 9h as 12h e 14h as 17h.\n\n"
            "Em breve irei te responder"
        )
        with self._mock_llm("BOT_ASSISTANT", 0.95):
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
        with self._mock_llm("BOT_ASSISTANT", 0.92):
            r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT)
        self.assertEqual(r.action, "handoff")

    def test_tropa_da_nutri_canal_atendimento(self):
        """Bug do usuario: Nutri Nathalia - bot Tropa da Nutri."""
        msg = (
            "Ola! Seja bem-vindo(a) ap canal de atendimento da Tropa da Nutri\n\n"
            "E um prazer te receber por aqui!\n\n"
            "Em breve nossa equipe vai te responder com todas as informacoes que voce precisa."
        )
        with self._mock_llm("BOT_ASSISTANT", 0.88):
            r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT, f"got {r.msg_type}: {r.signals}")
        self.assertEqual(r.action, "handoff")

    def test_clinica_prazer_receber(self):
        """Outro padrao comum de bot."""
        msg = (
            "Ola! Seja bem-vindo a Clinica Saude Total. "
            "E um prazer te receber! Em breve nossa equipe entrara em contato."
        )
        with self._mock_llm("BOT_ASSISTANT", 0.9):
            r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT)

    def test_ap_canal_typo(self):
        """Typo comum: 'ap canal'."""
        msg = "Ola! Bem-vindo(a) ap canal de suporte da Empresa XYZ"
        with self._mock_llm("BOT_ASSISTANT", 0.85):
            r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT)

    def test_doctorfit_ausente(self):
        """Msg de recepcao fora do horario - print 1."""
        msg = (
            "Ola, que bom que entrou em contato conosco! "
            "Infelizmente a recepcao encontra-se fora do horario de atendimento, "
            "retornaremos o seu contato assim que possivel, "
            "obrigada pela compreensao [green heart]"
        )
        r = classify_incoming_message(msg)
        # Ausente detectado por regex (N1), sem precisar de LLM
        self.assertIn(r.msg_type, (MessageType.AUTO_AUSENTE, MessageType.BOT_ASSISTANT))
        self.assertEqual(r.action, "no_response")

    def test_heuristic_obvio_marca_bot_sem_llm(self):
        """Se heuristica tem MUITA certeza (>=0.6), NAO chama LLM."""
        # Mock de LLM NAO deve ser chamado
        with patch("whatsapp.message_preprocessor._llm_classify_cached") as mock_llm:
            msg = (
                "Ola! Meu nome e Bia e sou a assistente virtual da Clinica X. "
                "Em breve irei te responder!"
            )
            r = classify_incoming_message(msg)
            # Heuristica deveria pegar: self_intro + team_speaking + is_short
            # 0.6 + 0.4 + 0.1 = 1.1 -> cap 1.0
            self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT)
            mock_llm.assert_not_called()

    def test_heuristic_baixa_llm_juiz(self):
        """Se heuristica nao tem certeza, LLM decide."""
        msg = "Quanto custa o site?"
        # LLM mockado deve retornar LEAD_REAL
        with self._mock_llm("LEAD_REAL", 0.85):
            r = classify_incoming_message(msg)
        self.assertEqual(r.msg_type, MessageType.LEAD_REAL)
        self.assertEqual(r.action, "forward_to_franz")

    def test_fallback_quando_llm_falha(self):
        """Se LLM retorna confianca baixa, usa heuristica como backup."""
        msg = (
            "Ola! Minha equipe entrara em contato em breve. "
            "Prazer te receber no canal de atendimento."
        )
        # LLM mockado com baixa confianca (deve acionar fallback heuristico)
        with self._mock_llm("LEAD_REAL", 0.3):
            r = classify_incoming_message(msg)
        # Heuristica: team_speaking(0.4) + is_short(0.1) = 0.5 -> >=0.4 aciona fallback
        self.assertEqual(r.msg_type, MessageType.BOT_ASSISTANT)


class TestHeuristicFeatures(unittest.TestCase):
    """Testa features heuristicas individuais."""

    def test_features_self_intro(self):
        f = _heuristic_features("Meu nome e Monica, sou assistente")
        self.assertEqual(f["has_self_intro"], 1.0)

    def test_features_schedule(self):
        f = _heuristic_features("Horarios: 9h as 18h")
        self.assertEqual(f["has_schedule"], 1.0)

    def test_features_team_speaking(self):
        f = _heuristic_features("Nossa equipe vai te responder")
        self.assertEqual(f["has_team_speaking"], 1.0)

    def test_score_bot_obvio(self):
        """Msg com multiplas features de bot = score alto."""
        msg = "Meu nome e Bia. Nossa equipe entrara em contato. Horarios: 9h-17h."
        f = _heuristic_features(msg)
        score = _heuristic_bot_score(f)
        self.assertGreater(score, 0.7)

    def test_score_lead_normal(self):
        """Msg sem features de bot = score baixo."""
        msg = "Quanto custa o site? Vocês entregam em quantos dias?"
        f = _heuristic_features(msg)
        score = _heuristic_bot_score(f)
        self.assertLess(score, 0.3)


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