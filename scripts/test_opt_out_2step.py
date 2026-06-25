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
    """Step 1: primeira vez - Franz deve PERGUNTAR, NAO marcar opt_out."""

    def test_step1_nao_marca_opt_out(self):
        """Lead disse algo ambiguo - Franz NAO pode marcar opt_out ainda."""
        mem = LeadMemory(lead_id="L1", user_id=1, telefone="5511")
        mem.opt_out_pending = False

        result = node_opt_out(_make_state(mem))

        # NAO pode ter marcado opt_out ainda
        self.assertFalse(mem.deal_status == "opt_out")
        self.assertNotEqual(mem.stage, "opt_out")
        # DEVE ter marcado pending
        self.assertTrue(mem.opt_out_pending, "Franz deve marcar pending")
        # DEVE ter feito a pergunta
        self.assertIn("sim", result["outgoing_message"].lower())
        self.assertIn("continua", result["outgoing_message"].lower())
        # Stage deve ser opt_out_pending (especial, nao opt_out ainda)
        self.assertEqual(result["next_stage"], "opt_out_pending")

    def test_step1_com_carolina_atleta(self):
        """Bug original: 'Nao atendo somente atletas' - NAO marcar opt_out."""
        mem = LeadMemory(lead_id="L2", user_id=1, telefone="5511")

        # Step 1: lead mandou msg de qualificacao
        result = node_opt_out(_make_state(mem, "Nao atendo somente atletas"))

        # Confirmado: pending, nao opt_out
        self.assertTrue(mem.opt_out_pending)
        self.assertNotEqual(mem.deal_status, "opt_out")
        # Mensagem de confirmacao
        self.assertIn("sim", result["outgoing_message"].lower())


class TestOptOutStep2Confirm(unittest.TestCase):
    """Step 2: lead responde 'sim' - AGORA sim marca opt_out."""

    def test_step2_sim_confirma(self):
        mem = LeadMemory(lead_id="L3", user_id=1, telefone="5511")
        mem.opt_out_pending = True  # ja perguntou antes

        result = node_opt_out(_make_state(mem, "sim"))

        self.assertEqual(mem.deal_status, "opt_out")
        self.assertEqual(mem.stage, "opt_out")
        self.assertIn("remover", result["outgoing_message"].lower())

    def test_step2_yes_confirma(self):
        mem = LeadMemory(lead_id="L4", user_id=1, telefone="5511")
        mem.opt_out_pending = True

        result = node_opt_out(_make_state(mem, "yes quero parar"))

        self.assertEqual(mem.deal_status, "opt_out")

    def test_step2_pode_parar_confirma(self):
        mem = LeadMemory(lead_id="L5", user_id=1, telefone="5511")
        mem.opt_out_pending = True

        result = node_opt_out(_make_state(mem, "pode parar"))

        self.assertEqual(mem.deal_status, "opt_out")


class TestOptOutStep2Cancel(unittest.TestCase):
    """Step 2: lead responde 'nao/continua' - VOLTA pro funil, nao opt_out."""

    def test_step2_nao_cancela(self):
        """Bug fix PRINCIPAL: lead diz 'nao' e Franz volta pro funil."""
        mem = LeadMemory(lead_id="L6", user_id=1, telefone="5511")
        mem.opt_out_pending = True

        result = node_opt_out(_make_state(mem, "nao"))

        # NAO marcou opt_out
        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertNotEqual(mem.stage, "opt_out")
        # Cancelou pending
        self.assertFalse(mem.opt_out_pending)
        # Voltou pro funil (qualify)
        self.assertEqual(result["next_stage"], "qualify")
        # Mandou msg de continuidade
        self.assertIn("conta", result["outgoing_message"].lower() or "foco" in result["outgoing_message"].lower())

    def test_step2_continua_cancela(self):
        mem = LeadMemory(lead_id="L7", user_id=1, telefone="5511")
        mem.opt_out_pending = True

        result = node_opt_out(_make_state(mem, "continua"))

        self.assertNotEqual(mem.deal_status, "opt_out")
        self.assertEqual(result["next_stage"], "qualify")

    def test_step2_seguir_cancela(self):
        mem = LeadMemory(lead_id="L8", user_id=1, telefone="5511")
        mem.opt_out_pending = True

        result = node_opt_out(_make_state(mem, "quero seguir"))

        self.assertNotEqual(mem.deal_status, "opt_out")


class TestOptOutStep2Unclear(unittest.TestCase):
    """Step 2: lead responde ambiguo - Franz re-pergunta."""

    def test_step2_resposta_invalida(self):
        mem = LeadMemory(lead_id="L9", user_id=1, telefone="5511")
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