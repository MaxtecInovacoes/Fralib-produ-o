"""Testes do fix do bug opt_out indevido.

Bug: LangGraph+Sonnet marcava msgs como opt_out quando o lead apenas
qualificava o atendimento (ex: "Nao atendo somente atletas").
Ver https://github.com/user/fralib/issues/bug-carolina-2026-06-25

Fix: opt_out so via regex EXPLICITO. LLM nunca pode classificar como opt_out.
"""

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from agents.sdr_langgraph.intent_classifier import (
    classify_intent,
    Intent,
)


class TestOptOutExplicit(unittest.TestCase):
    """Apenas pedido EXPLÍCITO de sair = opt_out."""

    def test_me_tira_do_contato(self):
        r = classify_intent("Me tira do contato")
        self.assertEqual(r.intent, Intent.OPT_OUT)

    def test_para_de_me_mandar(self):
        r = classify_intent("Para de me mandar mensagem")
        self.assertEqual(r.intent, Intent.OPT_OUT)

    def test_remover(self):
        r = classify_intent("Por favor remover meu numero")
        self.assertEqual(r.intent, Intent.OPT_OUT)

    def test_sair_curto(self):
        r = classify_intent("sair")
        self.assertEqual(r.intent, Intent.OPT_OUT)

    def test_nao_quero_curto(self):
        r = classify_intent("Nao quero mais")
        self.assertEqual(r.intent, Intent.OPT_OUT)


class TestOptOutNOTMatched(unittest.TestCase):
    """Mensagens ambiguas NAO devem ser opt_out (era o bug)."""

    def test_carolina_rasteira_atleta(self):
        """Bug original: LangGraph marcava isso como opt_out."""
        msg = "Nao atendo somente atletas, atendo bastante pessoas que de exercitam por Hobby mesmo"
        r = classify_intent(msg)
        self.assertNotEqual(r.intent, Intent.OPT_OUT, f"BUG REGRESSAO: {msg[:50]}")

    def test_nao_sou_dono(self):
        """Gatekeeper, NAO opt_out."""
        r = classify_intent("Nao sou o dono, mas posso te passar o contato dele")
        self.assertNotEqual(r.intent, Intent.OPT_OUT)

    def test_nao_quero_agora(self):
        """Mensagem de objecao/engajamento, nao opt_out."""
        r = classify_intent("Nao quero comprar agora, talvez no futuro")
        self.assertNotEqual(r.intent, Intent.OPT_OUT)

    def test_nao_atendo_mas_pode_falar(self):
        """Lead engajando mas quer ajustar publico - NAO opt_out."""
        msg = "Nao atendo esse segmento mas pode me explicar melhor"
        r = classify_intent(msg)
        self.assertNotEqual(r.intent, Intent.OPT_OUT)

    def test_nao_tenho_interesse_mas_obrigado(self):
        """Polidez, nao opt_out."""
        r = classify_intent("Nao tenho interesse mas obrigado pelo contato")
        self.assertNotEqual(r.intent, Intent.OPT_OUT)


if __name__ == "__main__":
    unittest.main(verbosity=2)