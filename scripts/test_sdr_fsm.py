"""Testes de regressão do bug do hook-loop.

Verifica que o sistema novo (Intent + FSM + Orchestrator) elimina o bug do
"lead cumprimenta 3x e o Franz fica travado em hook".

Rodar: cd C:/fralib && python -m pytest scripts/test_sdr_fsm.py -v
Ou: python scripts/test_sdr_fsm.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Adiciona backend ao path
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from agents.sdr_langgraph.intent_classifier import classify_intent, Intent
from agents.sdr_langgraph.state_machine import ConversationState, decide_transition, detect_loop
from agents.sdr_langgraph.orchestrator import orchestrate, OrchestratorDecision


class TestIntentClassifier(unittest.TestCase):
    """Verifica que o classificador acerta em casos comuns."""

    def test_greeting(self):
        for msg in ["oi", "boa noite", "tudo bem?", "eai", "olá"]:
            r = classify_intent(msg)
            self.assertIn(r.intent, (Intent.GREETING, Intent.ACKNOWLEDGMENT), f"{msg} -> {r.intent}")

    def test_opt_out(self):
        for msg in ["para", "me tira", "não quero mais", "chega"]:
            r = classify_intent(msg)
            self.assertEqual(r.intent, Intent.OPT_OUT, f"{msg} -> {r.intent}")

    def test_question_price(self):
        for msg in ["quanto custa?", "qual o valor?", "tem desconto?", "como funciona o pagamento?"]:
            r = classify_intent(msg)
            # question ou objection (preco) sao ambos corretos
            self.assertIn(r.intent, (Intent.QUESTION, Intent.OBJECTION), f"{msg} -> {r.intent}")

    def test_buying(self):
        for msg in ["quero fechar", "manda o link", "bora", "aceito"]:
            r = classify_intent(msg)
            self.assertEqual(r.intent, Intent.BUYING_INTENT, f"{msg} -> {r.intent}")

    def test_schedule(self):
        for msg in ["amanha", "semana que vem", "agendar"]:
            r = classify_intent(msg)
            self.assertEqual(r.intent, Intent.SCHEDULE, f"{msg} -> {r.intent}")

    def test_engagement_long(self):
        msg = "a gente atende bastante gente da regiao mas ta faltando aparecer no google"
        r = classify_intent(msg)
        self.assertEqual(r.intent, Intent.ENGAGEMENT, f"{msg} -> {r.intent}")


class TestStateMachine(unittest.TestCase):
    """Verifica que o FSM faz transicoes corretas."""

    def test_idle_greeting_keeps_waiting(self):
        # Lead cumprimenta pela 1a vez. Bot respondeu hook. Agora lead cumprimenta de volta.
        # BUG ANTIGO: stage-loop. NOVO: WAITING_RESPONSE, stage=hook.
        d = decide_transition(ConversationState.IDLE, Intent.GREETING, suggested_stage="hook")
        self.assertEqual(d.new_state, ConversationState.WAITING_RESPONSE)
        self.assertEqual(d.new_stage, "hook")
        # should_advance=False (nao avancou stage), mas state mudou
        self.assertFalse(d.should_advance)

    def test_opt_out_always_wins(self):
        # Opt-out em qualquer state vai pra OPT_OUT
        for state in [
            ConversationState.IDLE,
            ConversationState.WAITING_RESPONSE,
            ConversationState.ENGAGED,
            ConversationState.OBJECTING,
            ConversationState.BUYING,
        ]:
            d = decide_transition(state, Intent.OPT_OUT, suggested_stage="qualify")
            self.assertEqual(d.new_state, ConversationState.OPT_OUT)
            self.assertEqual(d.new_stage, "lost")

    def test_engagement_advances_to_qualify(self):
        # Lead engajou pela 1a vez
        d = decide_transition(ConversationState.IDLE, Intent.ENGAGEMENT, suggested_stage="hook")
        self.assertEqual(d.new_state, ConversationState.ENGAGED)
        self.assertEqual(d.new_stage, "qualify")

    def test_buying_intent_without_context_qualifies_first(self):
        # Lead quer comprar mas sem contexto. Regra de ouro: qualifica antes de revelar.
        d = decide_transition(ConversationState.IDLE, Intent.BUYING_INTENT, suggested_stage="hook")
        self.assertEqual(d.new_state, ConversationState.ENGAGED)
        self.assertEqual(d.new_stage, "qualify")

    def test_loop_detection(self):
        # Lead cumprimenta 3x em IDLE -> loop
        self.assertFalse(detect_loop(1, ConversationState.IDLE))
        self.assertFalse(detect_loop(2, ConversationState.IDLE))
        self.assertTrue(detect_loop(3, ConversationState.IDLE))
        self.assertTrue(detect_loop(5, ConversationState.WAITING_RESPONSE))

    def test_no_loop_when_advancing(self):
        # Lead engajou -> NAO em loop
        self.assertFalse(detect_loop(5, ConversationState.ENGAGED))


class TestOrchestratorRegressionHookLoop(unittest.TestCase):
    """O bug do hook-loop: lead manda 'boa noite' e fica travado em hook pra sempre."""

    def test_greeting_after_hook_keeps_waiting_but_marks_engagement(self):
        """Cenário: bot mandou hook, lead respondeu 'boa noite'. NOVO: nao loopar."""
        # turno 0: bot mandou hook. turno 1: lead mandou 'boa noite'.
        d = orchestrate(
            incoming_message="boa noite",
            current_state_str="waiting_response",  # bot mandou, esperando lead
            current_stage="hook",
            turn_count=1,
            suggested_stage="hook",  # LLM (corretamente) sugeriu hook de novo
        )
        # Antes (bug): stage nao avança, fica em hook. Próximo turno idem. Loop eterno.
        # Agora: state=waiting_response, stage=hook, should_advance=False (correto: nao avancou stage)
        # MAS in_loop=False (turn_count=1, ainda nao)
        self.assertEqual(d.state_after, ConversationState.WAITING_RESPONSE)
        self.assertEqual(d.stage_after, "hook")
        self.assertFalse(d.in_loop, "turn_count=1 nao deve detectar loop")
        self.assertEqual(d.intent, Intent.GREETING)

    def test_three_greetings_triggers_loop_break(self):
        """Cenário: lead mandou 'oi' 3x. NOVO: detectar loop e forçar qualify."""
        d = orchestrate(
            incoming_message="oi",
            current_state_str="waiting_response",
            current_stage="hook",
            turn_count=3,  # ja mandou 3 cumprimentos
            suggested_stage="hook",
        )
        # Detecta loop. Forca ENGAGED+qualify.
        self.assertTrue(d.in_loop, "turn_count=3 + WAITING_RESPONSE deve detectar loop")
        self.assertTrue(d.force_break_loop)
        # IMPORTANTE: o Composer deve usar isso pra fazer pergunta direta
        self.assertEqual(d.state_after, ConversationState.ENGAGED)
        self.assertEqual(d.stage_after, "qualify")
        self.assertTrue(d.should_advance)

    def test_engagement_after_greetings_advances(self):
        """Cenário: lead cumprimentou, depois engajou. NOVO: avança normalmente."""
        # turno 1: lead mandou 'oi'. turno 2: lead mandou 'a gente atende bastante gente'
        d = orchestrate(
            incoming_message="a gente atende bastante gente da regiao",
            current_state_str="waiting_response",
            current_stage="hook",
            turn_count=2,
            suggested_stage="hook",
        )
        self.assertEqual(d.intent, Intent.ENGAGEMENT)
        self.assertEqual(d.state_after, ConversationState.ENGAGED)
        self.assertEqual(d.stage_after, "qualify")

    def test_opt_out_immediately(self):
        """Cenário: lead manda 'para'. NOVO: vai pra OPT_OUT independente do state."""
        d = orchestrate(
            incoming_message="para, me tira",
            current_state_str="engaged",
            current_stage="qualify",
            turn_count=5,
            suggested_stage="pain",
        )
        self.assertEqual(d.state_after, ConversationState.OPT_OUT)
        self.assertEqual(d.stage_after, "lost")

    def test_price_question_without_context(self):
        """Cenário: lead pergunta preco logo de cara. NOVO: qualifica antes."""
        d = orchestrate(
            incoming_message="quanto custa?",
            current_state_str="idle",
            current_stage="hook",
            turn_count=1,
            suggested_stage="hook",
        )
        # intent deve ser QUESTION ou OBJECTION (preco)
        self.assertIn(d.intent, (Intent.QUESTION, Intent.OBJECTION))
        # Regra de ouro: nao revela preco sem qualify
        # - Se QUESTION: vai pra ENGAGED/qualify (lead curioso)
        # - Se OBJECTION: vai pra OBJECTING/qualify (lead com objecao de preco)
        self.assertIn(d.state_after, (ConversationState.ENGAGED, ConversationState.OBJECTING))
        self.assertEqual(d.stage_after, "qualify")

    def test_buying_after_qualification(self):
        """Cenário: lead ja qualificou e agora quer comprar. NOVO: vai pra BUYING/close."""
        d = orchestrate(
            incoming_message="quero fechar",
            current_state_str="engaged",
            current_stage="pain",
            turn_count=6,
            suggested_stage="pain",
        )
        self.assertEqual(d.intent, Intent.BUYING_INTENT)
        self.assertEqual(d.state_after, ConversationState.BUYING)
        self.assertEqual(d.stage_after, "close")

    def test_schedule(self):
        """Cenário: lead quer agendar."""
        d = orchestrate(
            incoming_message="agenda pra semana que vem",
            current_state_str="engaged",
            current_stage="pain",
            turn_count=4,
            suggested_stage="pain",
        )
        self.assertEqual(d.intent, Intent.SCHEDULE)
        self.assertEqual(d.state_after, ConversationState.SCHEDULED)
        self.assertEqual(d.stage_after, "scheduled")


class TestEndToEndScenarios(unittest.TestCase):
    """Cenarios completos: lead que so cumprimenta, lead que objeta, lead que compra."""

    def test_scenario_lead_only_greets_then_breaks(self):
        """Lead cumprimenta 3x. Sistema deve quebrar o loop no turno 3."""
        # Turno 1: lead cumprimenta (estado anterior: idle, stage hook)
        d1 = orchestrate("oi", "idle", "hook", turn_count=1, suggested_stage="hook")
        self.assertEqual(d1.state_after, ConversationState.WAITING_RESPONSE)

        # Turno 2: lead cumprimenta de novo. orchestrator atualizou turn_count pra 2
        d2 = orchestrate("eai", "waiting_response", "hook", turn_count=2, suggested_stage="hook")
        self.assertEqual(d2.state_after, ConversationState.WAITING_RESPONSE)
        self.assertFalse(d2.in_loop)

        # Turno 3: lead cumprimenta de novo. Loop detectado.
        d3 = orchestrate("olá", "waiting_response", "hook", turn_count=3, suggested_stage="hook")
        self.assertTrue(d3.in_loop)
        self.assertEqual(d3.state_after, ConversationState.ENGAGED)
        self.assertEqual(d3.stage_after, "qualify")

    def test_scenario_lead_smart_then_buys(self):
        """Lead engajado desde o turno 1. Compra no turno 3."""
        d1 = orchestrate("sou o dono da academia, a gente tem 50 alunos", "idle", "hook", turn_count=1, suggested_stage="hook")
        self.assertEqual(d1.state_after, ConversationState.ENGAGED)
        self.assertEqual(d1.stage_after, "qualify")

        d2 = orchestrate("tô percebendo que o instagram nao ta trazendo aluno novo", "engaged", "qualify", turn_count=2, suggested_stage="pain")
        self.assertEqual(d2.state_after, ConversationState.ENGAGED)
        # mantem-se ENGAGED; ainda nao foi pra pain mas ja tem dor

        d3 = orchestrate("quero fechar, manda o link", "engaged", "qualify", turn_count=3, suggested_stage="pain")
        self.assertEqual(d3.intent, Intent.BUYING_INTENT)
        self.assertEqual(d3.state_after, ConversationState.BUYING)
        self.assertEqual(d3.stage_after, "close")


class TestSlidingWindow(unittest.TestCase):
    """Verifica que build_history trunca em 30 msgs e gera summary."""

    def test_small_history_no_truncation(self):
        from whatsapp.sdr_reply_service import build_history
        rows = [("msg 1", "saida"), ("resp 1", "entrada"), ("msg 2", "saida")]
        h = build_history(rows, max_messages=30)
        # sem summary porque < 30
        self.assertEqual(len(h), 3)
        # todas as mensagens devem ter role valido
        for item in h:
            self.assertIn(item["role"], ("user", "assistant"))

    def test_large_history_truncated_with_summary(self):
        from whatsapp.sdr_reply_service import build_history
        # 50 mensagens -> deve truncar
        rows = [(f"msg {i}", "saida" if i % 2 == 0 else "entrada") for i in range(50)]
        h = build_history(rows, max_messages=30)
        # max 30 raw + 1 system (summary) = 31
        self.assertLessEqual(len(h), 31)
        # primeira deve ser system se tem summary
        if len(h) > 30:
            self.assertEqual(h[0]["role"], "system")
            self.assertIn("[Resumo", h[0]["content"])


class TestMemoryHook(unittest.TestCase):
    """Verifica que memory_hook carrega core/warm sem erros."""

    def test_inject_memory_no_crash(self):
        from agents.sdr_langgraph.memory_hook import inject_memory_for_franz
        from agents.sdr_langgraph.state import LeadMemory
        memory = LeadMemory(lead_id="test", user_id=2, telefone="5511999999999")
        # nao deve crashar mesmo sem warm memory populado
        try:
            inject_memory_for_franz(memory, "academia")
        except Exception as e:
            self.fail(f"inject_memory_for_franz should not crash: {e}")

    def test_extract_insight_objection(self):
        from agents.sdr_langgraph.memory_hook import _build_insight
        from agents.sdr_langgraph.state import LeadMemory
        memory = LeadMemory(lead_id="test", user_id=2, telefone="5511999999999", segmento="academia")
        insight = _build_insight(memory, "muito caro isso ai", "objection", "qualify")
        self.assertIsNotNone(insight)
        self.assertIn("academia", insight.lower())

    def test_extract_insight_empty_input(self):
        from agents.sdr_langgraph.memory_hook import _build_insight
        from agents.sdr_langgraph.state import LeadMemory
        memory = LeadMemory(lead_id="test", user_id=2, telefone="5511999999999")
        self.assertIsNone(_build_insight(memory, "", "greeting", "hook"))


class TestTurnTracing(unittest.TestCase):
    """Verifica que SDRTurnTrace cria spans corretamente."""

    def test_basic_trace(self):
        from agents.sdr_langgraph.turn_tracing import SDRTurnTrace
        t = SDRTurnTrace(lead_id="abc", lead_nome="Academia X", nicho="academia")
        self.assertEqual(t.lead_id, "abc")
        self.assertEqual(t.spans, [])
        self.assertEqual(t.total_input_tokens, 0)

    def test_span_lifecycle(self):
        from agents.sdr_langgraph.turn_tracing import SDRTurnTrace
        t = SDRTurnTrace(lead_id="abc", lead_nome="Academia X")
        s = t.start_span("intent_classifier")
        t.end_span(s, input_tokens=10, output_tokens=20, cost_usd=0.001)
        self.assertEqual(len(t.spans), 1)
        self.assertEqual(t.spans[0]["status"], "completed")
        self.assertEqual(t.total_input_tokens, 10)
        self.assertEqual(t.total_output_tokens, 20)
        self.assertAlmostEqual(t.custo_total_usd, 0.001)


if __name__ == "__main__":
    unittest.main(verbosity=2)