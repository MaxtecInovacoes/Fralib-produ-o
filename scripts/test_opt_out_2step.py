"""Testes do 2-step opt_out: Franz pergunta confirmacao antes de parar.

Bug fix: Franz marcava opt_out direto na primeira negativa do lead.
Ex: Carolina Ragugnetti 'Nao atendo somente atletas' -> opt_out imediato.

Solucao: 2-step.
  Step 1: Franz pergunta "quer parar? sim/continua"
  Step 2: Lead responde. So 'sim' confirma opt_out.
          'continua' volta pro funil.
"""

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from agents.sdr_langgraph.agent import node_opt_out
from agents.sdr_langgraph.state import LeadMemory


def _make_state(memory: LeadMemory, incoming: str = "") -> dict:
    return {
        "memory": memory,
        "incoming_message": incoming,
        "is_outbound": False,
    }


class TestOptOutStep1(unittest.TestCase):
    """Step 1: SEMPRE pergunta confirmacao (independente do stage).

    Decisao do usuario: agente humanizado deve ser LIVRE.
    Se o LLM classificou como opt_out, Franz so pergunta confirmacao.
    Se lead disser 'nao/continua', volta pro funil normalmente.
    """

    def test_stage_hook_pergunta_confirmacao(self):
        """Mesmo em hook, Franz pergunta confirmacao uma vez."""
        mem = LeadMemory(lead_id="L1", user_id=1, telefone="5511")
        mem.stage = "hook"
        mem.opt_out_pending = False

        result = node_opt_out(_make_state(mem))

        self.assertTrue(mem.opt_out_pending, "Franz deve marcar pending")
        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertIn("sim", result["outgoing_message"].lower())
        self.assertIn("continua", result["outgoing_message"].lower())
        self.assertEqual(result["next_stage"], "opt_out_pending")

    def test_stage_pain_primeira_msg(self):
        """Stage avancado: ja teve conversa. Pergunta confirmacao."""
        mem = LeadMemory(lead_id="L2", user_id=1, telefone="5511")
        mem.stage = "pain"
        mem.opt_out_pending = False

        result = node_opt_out(_make_state(mem))

        self.assertTrue(mem.opt_out_pending)
        self.assertIn("sim", result["outgoing_message"].lower())

    def test_primeira_msg_com_carolina_atleta(self):
        """Bug original: 'Nao atendo somente atletas' - pergunta confirmacao."""
        mem = LeadMemory(lead_id="L3", user_id=1, telefone="5511")
        mem.stage = "qualify"

        result = node_opt_out(_make_state(mem, "Nao atendo somente atletas"))

        self.assertTrue(mem.opt_out_pending)
        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertIn("sim", result["outgoing_message"].lower())


class TestOptOutStep2Confirm(unittest.TestCase):
    """Step 2: lead responde 'sim' em stage avancado - AGORA sim marca opt_out."""

    def _make_pain_pending(self):
        mem = LeadMemory(lead_id="L3", user_id=1, telefone="5511")
        mem.stage = "pain"
        mem.opt_out_pending = True
        return mem

    def test_step2_sim_confirma(self):
        mem = self._make_pain_pending()
        result = node_opt_out(_make_state(mem, "sim"))

        self.assertEqual(mem.deal_status, "opt_out")
        self.assertEqual(mem.stage, "opt_out")
        self.assertIn("remover", result["outgoing_message"].lower())

    def test_step2_yes_confirma(self):
        mem = self._make_pain_pending()
        result = node_opt_out(_make_state(mem, "yes quero parar"))

        self.assertEqual(mem.deal_status, "opt_out")

    def test_step2_pode_parar_confirma(self):
        mem = self._make_pain_pending()
        result = node_opt_out(_make_state(mem, "pode parar"))

        self.assertEqual(mem.deal_status, "opt_out")


class TestOptOutStep2Cancel(unittest.TestCase):
    """Step 2: lead responde 'nao/continua' - VOLTA pro funil (deixa LLM responder)."""

    def _make_pain_pending(self):
        mem = LeadMemory(lead_id="L6", user_id=1, telefone="5511")
        mem.stage = "pain"
        mem.opt_out_pending = True
        return mem

    def test_step2_nao_cancela(self):
        """Bug fix PRINCIPAL: lead diz 'nao' e Franz volta pro funil."""
        mem = self._make_pain_pending()
        result = node_opt_out(_make_state(mem, "nao"))

        # NAO marcou opt_out
        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertNotEqual(mem.stage, "opt_out")
        # Cancelou pending
        self.assertFalse(mem.opt_out_pending)
        # Voltou pro stage original (pain)
        self.assertEqual(result["next_stage"], "pain")
        # Deixa LLM gerar resposta natural (outgoing vazio, should_send False)
        self.assertFalse(result["should_send"])

    def test_step2_continua_cancela(self):
        mem = self._make_pain_pending()
        result = node_opt_out(_make_state(mem, "continua"))

        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertEqual(result["next_stage"], "pain")
        self.assertFalse(result["should_send"])

    def test_step2_seguir_cancela(self):
        mem = self._make_pain_pending()
        result = node_opt_out(_make_state(mem, "quero seguir"))

        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertFalse(result["should_send"])


class TestOptOutStep2Unclear(unittest.TestCase):
    """Step 2: lead responde ambiguo em stage avancado - Franz re-pergunta."""

    def test_step2_resposta_invalida(self):
        mem = LeadMemory(lead_id="L9", user_id=1, telefone="5511")
        mem.stage = "pain"
        mem.opt_out_pending = True

        result = node_opt_out(_make_state(mem, "talvez"))

        # Continua pending
        self.assertTrue(mem.opt_out_pending)
        # Nao marcou opt_out
        self.assertNotEqual(mem.deal_status, "opt_out")
        # Re-perguntou
        self.assertIn("sim", result["outgoing_message"].lower())
        self.assertIn("continua", result["outgoing_message"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)