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

    def test_decorator_wraps_node(self):
        from agents.sdr_langgraph.turn_tracing import sdr_traced, get_active_trace
        from agents.sdr_langgraph.state import SDRState
        @sdr_traced("test_node")
        def fake_node(state):
            return {"ok": True}
        state = {"lead_id": "test_lead", "memory": None}
        # cria trace
        from agents.sdr_langgraph.turn_tracing import start_turn_trace
        start_turn_trace("test_lead", "Lead X", "academia")
        result = fake_node(state)
        self.assertEqual(result.get("ok"), True)
        trace = get_active_trace("test_lead")
        self.assertIsNotNone(trace)
        self.assertEqual(len(trace.spans), 1)
        self.assertEqual(trace.spans[0]["nome"], "test_node")
        from agents.sdr_langgraph.turn_tracing import end_turn_trace
        end_turn_trace("test_lead")


class TestQualityJudge(unittest.TestCase):
    """Verifica que o LLM-as-judge classifica resposta corretamente."""

    def test_heuristic_good_reply(self):
        from agents.sdr_langgraph.quality_judge import _heuristic_evaluate
        score = _heuristic_evaluate("oi", "Oi! Tudo bem? Voce e academia mesmo?", 3)
        self.assertGreaterEqual(score.score, 3)
        self.assertTrue(score.should_send)

    def test_heuristic_bad_reply(self):
        from agents.sdr_langgraph.quality_judge import _heuristic_evaluate
        # Resposta com 3 perguntas e JSON cru (puxa 2 pontos)
        reply = '{"reply": "Ola? Tudo bem? Como vai? Posso ajudar?"}'
        score = _heuristic_evaluate("oi", reply, 3)
        self.assertLess(score.score, 5)
        self.assertIn("markdown_json_cru", score.issues)
        self.assertIn("multiplas_perguntas", score.issues)

    def test_evaluate_reply_uses_heuristic_when_disabled(self):
        from agents.sdr_langgraph.quality_judge import evaluate_reply
        q = evaluate_reply("oi", "Opa, tudo bem?", enable_llm=False)
        self.assertIsNotNone(q)
        self.assertGreaterEqual(q.score, 1)
        self.assertLessEqual(q.score, 5)

    def test_empty_reply_blocks(self):
        from agents.sdr_langgraph.quality_judge import evaluate_reply
        q = evaluate_reply("oi", "", enable_llm=False)
        self.assertFalse(q.should_send)
        self.assertEqual(q.score, 0)


class TestStreaming(unittest.TestCase):
    """Verifica que o modulo de streaming expoe API correta."""

    def test_sse_format(self):
        from agents.sdr_langgraph.streaming import sse_format
        result = sse_format("hello world", event="message")
        self.assertIn("event: message", result)
        self.assertIn("data: hello world", result)

    def test_stream_module_importable(self):
        from agents.sdr_langgraph.streaming import stream_franz_reply
        self.assertTrue(callable(stream_franz_reply))


class TestSiteOffer(unittest.TestCase):
    """Verifica que o helper de oferta de site gera texto correto."""

    def test_proactive_with_site_url(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import offer_proactive
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.fralib.com.br/site/abc")
        text = offer_proactive(memory, segmento="academia")
        self.assertIsNotNone(text)
        self.assertIn("demonstracao", text.lower())
        self.assertIn("https://demo.fralib.com.br/site/abc", text)
        # remover acentos antes de procurar
        from unicodedata import normalize
        text_normalized = normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
        self.assertIn("copia", text_normalized)
        self.assertIn("navegador", text_normalized)

    def test_proactive_without_site_url(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import offer_proactive
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999")
        text = offer_proactive(memory)
        self.assertIsNone(text)

    def test_in_objection_has_provider(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import offer_in_objection
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x")
        text = offer_in_objection(memory, objection_type="has_provider")
        self.assertIn("demonstracao", text.lower())
        self.assertIn("sem compromisso", text.lower())

    def test_to_gatekeeper_offers_for_decisor(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import offer_to_gatekeeper
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x")
        text = offer_to_gatekeeper(memory, decisor_name_hint="dono")
        self.assertIn("demonstracao", text.lower())
        self.assertIn("dono", text.lower())
        self.assertIn("2 min", text.lower())

    def test_should_offer_proactive_when_lead_engaged(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import should_offer_site, increment_offer_count
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x", conversation_state="engaged")
        self.assertTrue(should_offer_site(memory, intent="engagement", turn_count=2))
        increment_offer_count(memory)
        self.assertEqual(memory.site_offer_count, 1)
        increment_offer_count(memory)
        self.assertEqual(memory.site_offer_count, 2)
        self.assertFalse(should_offer_site(memory, intent="engagement", turn_count=3), "max 2 ofertas")

    def test_should_not_offer_when_opt_out(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import should_offer_site
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x", conversation_state="opt_out")
        self.assertFalse(should_offer_site(memory, intent="engagement"))

    def test_should_offer_at_hook_with_greeting_loop(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import should_offer_site
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x", conversation_state="waiting_response")
        # turno 1: nao oferece
        self.assertFalse(should_offer_site(memory, intent="greeting", turn_count=1))
        # turno 3 (loop): oferece proativamente
        self.assertTrue(should_offer_site(memory, intent="greeting", turn_count=3))

    def test_should_offer_for_objection(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import should_offer_site
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x", conversation_state="engaged")
        self.assertTrue(should_offer_site(memory, intent="objection", turn_count=3))

    def test_should_offer_for_gatekeeper(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_offer import should_offer_site
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="5511999999999", site_url="https://demo.x", conversation_state="engaged")
        self.assertTrue(should_offer_site(memory, intent="gatekeeper", turn_count=1))


class TestSiteScreenshot(unittest.TestCase):
    """Verifica o helper de screenshot."""

    def test_build_site_url(self):
        from agents.sdr_langgraph.site_screenshot import build_site_url
        url = build_site_url(2, "academia-4fitness", "https://app.example.com")
        self.assertEqual(url, "https://app.example.com/sites/2/academia-4fitness/")

    def test_build_site_url_default_base(self):
        from agents.sdr_langgraph.site_screenshot import build_site_url
        url = build_site_url(2, "academia")
        # deve usar env APP_URL ou fallback
        self.assertIn("/sites/2/academia", url)

    def test_get_site_url_from_memory_uses_site_url_field(self):
        from agents.sdr_langgraph.state import LeadMemory
        from agents.sdr_langgraph.site_screenshot import get_site_url_from_memory
        memory = LeadMemory(lead_id="abc", user_id=2, telefone="x", site_url="https://direct.com")
        self.assertEqual(get_site_url_from_memory(memory), "https://direct.com")

    def test_capture_returns_none_on_bad_url(self):
        from agents.sdr_langgraph.site_screenshot import capture_site_screenshot
        result = capture_site_screenshot("", lead_id="x")
        self.assertIsNone(result)
        result = capture_site_screenshot("not-a-url", lead_id="x")
        self.assertIsNone(result)


class TestSimplifyLanguage(unittest.TestCase):
    """Verifica que _simplify_language reescreve jargoes com tom simples."""

    def test_optimizar_vira_melhorar(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Vamos otimizar sua presenca digital.")
        self.assertIn("melhorar", out)
        self.assertNotIn("otimizar", out)

    def test_solucao_vira_coisa(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Temos a solucao perfeita para voce.")
        self.assertIn("coisa", out)
        self.assertNotIn("soluc", out)

    def test_captacao_vira_atrair(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Como voces captam clientes hoje?")
        self.assertIn("atraem", out.lower())

    def test_call_vira_conversa(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Vamos agendar uma call amanha?")
        # "agendar uma call" -> "marcar um bate-papo"
        self.assertIn("bate-papo", out)
        self.assertNotIn("call", out.lower())

    def test_gostaria_vira_quer(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Voce gostaria de mais informacoes?")
        # "gostaria de [verbo/info]" -> "quer"
        self.assertIn("quer", out)
        self.assertNotIn("gostaria", out)

    def test_gostaria_sozinho_vira_queria(self):
        from agents.sdr_langgraph.agent import _simplify_language
        # sem "de" depois -> "queria" soa melhor em pt-BR
        out = _simplify_language("Eu gostaria de saber o preco.")
        # "gostaria de" -> "quer" (forma prioritaria)
        self.assertNotIn("gostaria", out)

    def test_quer_de_colapsa(self):
        from agents.sdr_langgraph.agent import _simplify_language
        # garante que o glitch "quer de marcar" nao acontece
        out = _simplify_language("Voce gostaria de agendar uma call amanha?")
        self.assertNotIn("quer de", out)
        self.assertIn("bate-papo", out)

    def test_digital_vira_online(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Sua presenca digital e importante.")
        self.assertIn("online", out)
        self.assertNotIn("digital", out)

    def test_preserva_lead_e_link(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("O lead pode ver o link do site.")
        # "lead" e "link" sao termos do dominio, NAO trocar
        self.assertIn("lead", out)
        self.assertIn("link", out)

    def test_resposta_curta_nao_alterada(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Oi!")
        self.assertEqual(out, "Oi!")

    def test_frase_complexa_completa(self):
        from agents.sdr_langgraph.agent import _simplify_language
        out = _simplify_language("Vamos otimizar sua captacao digital com solucoes personalizadas para maximizar conversoes.")
        # deve ter: melhorar, atrat, online, coisa
        for keyword in ["melhorar", "atra", "online", "coisa"]:
            self.assertIn(keyword, out.lower(), f"Faltando: {keyword}")


if __name__ == "__main__":
    unittest.main(verbosity=2)