"""Testes para o modulo state_machine.py (FSM SDR).

Testa:
- Transicoes (state, intent) -> new_state
- Override OPT_OUT sempre terminal
- Override BUYING_INTENT com contexto
- detect_loop()
- StateDecision fields
"""
import pytest

from backend.agents.sdr_langgraph.state_machine import (
    ConversationState,
    Intent,
    decide_transition,
    detect_loop,
)


class TestOptOutOverride:
    """OPT_OUT vai direto, independente do state."""

    @pytest.mark.parametrize("state", [
        ConversationState.IDLE,
        ConversationState.WAITING_RESPONSE,
        ConversationState.ENGAGED,
        ConversationState.OBJECTING,
        ConversationState.BUYING,
        ConversationState.SCHEDULED,
    ])
    def test_opt_out_sempre_terminal(self, state):
        result = decide_transition(state, Intent.OPT_OUT)
        assert result.new_state == ConversationState.OPT_OUT
        assert result.new_stage == "lost"
        assert result.confidence == 1.0


class TestBuyingIntentOverride:
    """BUYING_INTENT com contexto adequado."""

    def test_buying_depois_de_engaged(self):
        result = decide_transition(ConversationState.ENGAGED, Intent.BUYING_INTENT)
        assert result.new_state == ConversationState.BUYING
        assert result.new_stage == "close"
        assert result.confidence == 0.9

    def test_buying_depois_de_objecting(self):
        result = decide_transition(ConversationState.OBJECTING, Intent.BUYING_INTENT)
        assert result.new_state == ConversationState.BUYING
        assert result.new_stage == "close"
        assert result.confidence == 0.85

    def test_buying_em_idle_qualifica_antes(self):
        result = decide_transition(ConversationState.IDLE, Intent.BUYING_INTENT)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "qualify"
        assert result.confidence == 0.8

    def test_buying_em_waiting_qualifica_antes(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.BUYING_INTENT)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "qualify"
        assert result.confidence == 0.8


class TestMatrizTransicoes:
    """Testa transicoes da matriz (state, intent) -> new_state."""

    def test_idle_greeting_vai_waiting_response(self):
        result = decide_transition(ConversationState.IDLE, Intent.GREETING)
        assert result.new_state == ConversationState.WAITING_RESPONSE
        assert result.should_advance is False

    def test_idle_engagement_vai_engaged(self):
        result = decide_transition(ConversationState.IDLE, Intent.ENGAGEMENT)
        assert result.new_state == ConversationState.ENGAGED

    def test_idle_question_vai_engaged(self):
        result = decide_transition(ConversationState.IDLE, Intent.QUESTION)
        assert result.new_state == ConversationState.ENGAGED

    def test_idle_objection_vai_objecting(self):
        result = decide_transition(ConversationState.IDLE, Intent.OBJECTION)
        assert result.new_state == ConversationState.OBJECTING

    def test_idle_buying_vai_buying(self):
        result = decide_transition(ConversationState.IDLE, Intent.BUYING_INTENT)
        # Override tratado antes da matriz
        assert result.new_state == ConversationState.ENGAGED

    def test_waiting_response_greeting_LoopBugFix(self):
        """Bugfix: greeting em waiting_response NAO loopa - mantem hook."""
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.GREETING)
        assert result.new_state == ConversationState.WAITING_RESPONSE
        assert result.new_stage == "hook"

    def test_waiting_response_acknowledgment_mantem_hook(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.ACKNOWLEDGMENT)
        assert result.new_state == ConversationState.WAITING_RESPONSE
        assert result.new_stage == "hook"

    def test_waiting_response_engagement_vai_engaged(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.ENGAGEMENT)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "qualify"

    def test_waiting_response_question_vai_engaged(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.QUESTION)
        assert result.new_state == ConversationState.ENGAGED

    def test_waiting_response_objection_vai_objecting(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.OBJECTION)
        assert result.new_state == ConversationState.OBJECTING

    def test_waiting_response_schedule_vai_scheduled(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.SCHEDULE)
        assert result.new_state == ConversationState.SCHEDULED
        assert result.new_stage == "scheduled"

    def test_waiting_response_gatekeeper_vai_engaged(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.GATEKEEPER)
        assert result.new_state == ConversationState.ENGAGED

    def test_waiting_response_off_topic_mantem_waiting(self):
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.OFF_TOPIC)
        assert result.new_state == ConversationState.WAITING_RESPONSE

    def test_engaged_greeting_avanca_qualify(self):
        result = decide_transition(ConversationState.ENGAGED, Intent.GREETING)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "qualify"

    def test_engaged_more_engagement_vai_pain(self):
        result = decide_transition(ConversationState.ENGAGED, Intent.ENGAGEMENT)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "pain"

    def test_engaged_objection_vai_objecting(self):
        result = decide_transition(ConversationState.ENGAGED, Intent.OBJECTION)
        assert result.new_state == ConversationState.OBJECTING

    def test_objecting_engagement_volta_engaged_amplify(self):
        result = decide_transition(ConversationState.OBJECTING, Intent.ENGAGEMENT)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "amplify"

    def test_objecting_question_avanca_amplify(self):
        result = decide_transition(ConversationState.OBJECTING, Intent.QUESTION)
        assert result.new_state == ConversationState.ENGAGED
        assert result.new_stage == "amplify"

    def test_buying_objection_volta_objecting(self):
        result = decide_transition(ConversationState.BUYING, Intent.OBJECTION)
        assert result.new_state == ConversationState.OBJECTING

    def test_buying_question_fica_buying_close(self):
        result = decide_transition(ConversationState.BUYING, Intent.QUESTION)
        assert result.new_state == ConversationState.BUYING


class TestGreetingLoopPrevention:
    """Testa fix do loop: greeting com turn_count >= 2 em IDLE/WAITING_RESPONSE."""

    def test_greeting_idle_turn0_nao_previne_loop(self):
        """turn_count < 3, sem fix de loop."""
        result = decide_transition(ConversationState.IDLE, Intent.GREETING, turn_count=0)
        assert result.new_state == ConversationState.WAITING_RESPONSE

    def test_greeting_waiting_turn2_nao_previne_loop(self):
        """turn_count = 2, ainda nao dispara fix."""
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.GREETING, turn_count=2)
        assert result.should_advance is False

    def test_greeting_idle_turn3_previne_loop(self):
        """turn_count >= 3: lead so cumprimentou, nao avanca stage."""
        result = decide_transition(ConversationState.IDLE, Intent.GREETING, turn_count=3)
        assert result.new_state == ConversationState.WAITING_RESPONSE
        assert result.should_advance is False
        assert "3x" in result.reasoning

    def test_greeting_waiting_turn5_previne_loop(self):
        """turn_count alto: lead nao engajou."""
        result = decide_transition(ConversationState.WAITING_RESPONSE, Intent.GREETING, turn_count=5)
        assert result.should_advance is False


class TestDetectLoop:
    """Testa deteccao de loop."""

    def test_turn_count_menor_3_nao_detecta_loop(self):
        assert detect_loop(0, ConversationState.IDLE) is False
        assert detect_loop(1, ConversationState.WAITING_RESPONSE) is False
        assert detect_loop(2, ConversationState.ENGAGED) is False

    def test_detecta_loop_em_idle(self):
        assert detect_loop(3, ConversationState.IDLE) is True

    def test_detecta_loop_em_waiting_response(self):
        assert detect_loop(5, ConversationState.WAITING_RESPONSE) is True

    def test_nao_detecta_loop_em_engaged(self):
        assert detect_loop(10, ConversationState.ENGAGED) is False

    def test_nao_detecta_loop_em_buying(self):
        assert detect_loop(10, ConversationState.BUYING) is False


class TestStateDecisionFields:
    """Verifica que StateDecision tem todos os campos."""

    def test_decision_tem_intent(self):
        result = decide_transition(ConversationState.IDLE, Intent.GREETING)
        assert result.intent == Intent.GREETING

    def test_decision_tem_confidence(self):
        result = decide_transition(ConversationState.IDLE, Intent.GREETING)
        assert 0 <= result.confidence <= 1.0

    def test_decision_tem_reasoning(self):
        result = decide_transition(ConversationState.IDLE, Intent.GREETING)
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0

    def test_decision_tem_should_advance(self):
        result = decide_transition(ConversationState.IDLE, Intent.GREETING)
        assert isinstance(result.should_advance, bool)


class TestUnknownIntent:
    """Intent nao mapeado: mantem state atual."""

    def test_unknown_em_idle(self):
        result = decide_transition(ConversationState.IDLE, Intent.UNKNOWN)
        assert result.new_state == ConversationState.IDLE
        assert result.confidence == 0.3

    def test_unknown_em_engaged(self):
        result = decide_transition(ConversationState.ENGAGED, Intent.UNKNOWN)
        assert result.new_state == ConversationState.ENGAGED
        assert result.confidence == 0.3
