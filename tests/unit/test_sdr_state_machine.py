"""Testes para state_machine.py e intent_classifier.py."""

import pytest
from backend.agents.sdr_langgraph.state_machine import (
    ConversationState,
    Intent,
    decide_transition,
    detect_loop,
)
from backend.agents.sdr_langgraph.intent_classifier import (
    classify_intent,
    IntentResult,
)


class TestConversationState:
    def test_all_states_exist(self):
        assert ConversationState.IDLE.value == "idle"
        assert ConversationState.WAITING_RESPONSE.value == "waiting_response"
        assert ConversationState.ENGAGED.value == "engaged"
        assert ConversationState.OBJECTING.value == "objecting"
        assert ConversationState.BUYING.value == "buying"
        assert ConversationState.SCHEDULED.value == "scheduled"
        assert ConversationState.OPT_OUT.value == "opt_out"
        assert ConversationState.HANDED_OFF.value == "handed_off"
        assert ConversationState.CLOSED_WON.value == "won"
        assert ConversationState.CLOSED_LOST.value == "lost"


class TestIntent:
    def test_all_intents_exist(self):
        assert Intent.GREETING.value == "greeting"
        assert Intent.ACKNOWLEDGMENT.value == "acknowledgment"
        assert Intent.ENGAGEMENT.value == "engagement"
        assert Intent.QUESTION.value == "question"
        assert Intent.OBJECTION.value == "objection"
        assert Intent.BUYING_INTENT.value == "buying_intent"
        assert Intent.SCHEDULE.value == "schedule"
        assert Intent.OPT_OUT.value == "opt_out"
        assert Intent.GATEKEEPER.value == "gatekeeper"
        assert Intent.OFF_TOPIC.value == "off_topic"
        assert Intent.UNKNOWN.value == "unknown"


class TestDecideTransition:
    def test_idle_to_greeting(self):
        """Idle + greeting = waiting_response (bot mandou msg, esperando resposta)."""
        decision = decide_transition(
            current_state=ConversationState.IDLE,
            intent=Intent.GREETING,
            suggested_stage=None,
            turn_count=1,
        )
        assert decision.new_state == ConversationState.WAITING_RESPONSE
        assert decision.should_advance is True

    def test_opt_out_always_stays(self):
        """Opt-out + qualquer intent = opt-out."""
        decision = decide_transition(
            current_state=ConversationState.OPT_OUT,
            intent=Intent.GREETING,
            suggested_stage=None,
            turn_count=1,
        )
        assert decision.new_state == ConversationState.OPT_OUT

    def test_objection_sets_state(self):
        """Objection intent = objecting state."""
        decision = decide_transition(
            current_state=ConversationState.ENGAGED,
            intent=Intent.OBJECTION,
            suggested_stage=None,
            turn_count=2,
        )
        assert decision.new_state == ConversationState.OBJECTING

    def test_buying_intent_sets_state(self):
        """Buying intent = buying state."""
        decision = decide_transition(
            current_state=ConversationState.ENGAGED,
            intent=Intent.BUYING_INTENT,
            suggested_stage=None,
            turn_count=2,
        )
        assert decision.new_state == ConversationState.BUYING


class TestDetectLoop:
    def test_no_loop_early_turns(self):
        for turn in range(1, 3):
            assert detect_loop(turn, ConversationState.IDLE) is False

    def test_loop_after_3_idle(self):
        assert detect_loop(3, ConversationState.IDLE) is True
        assert detect_loop(5, ConversationState.IDLE) is True

    def test_loop_waiting_response(self):
        assert detect_loop(4, ConversationState.WAITING_RESPONSE) is True

    def test_no_loop_engaged(self):
        for turn in range(1, 6):
            assert detect_loop(turn, ConversationState.ENGAGED) is False

    def test_no_loop_objecting(self):
        for turn in range(1, 6):
            assert detect_loop(turn, ConversationState.OBJECTING) is False


class TestClassifyIntent:
    def test_greeting(self):
        for msg in ["oi", "ola", "boa noite"]:
            result = classify_intent(msg)
            assert result.intent == Intent.GREETING, f"Falhou para: {msg}"

    def test_opt_out(self):
        for msg in ["nao quero mais", "para de me mandar"]:
            result = classify_intent(msg)
            assert result.intent == Intent.OPT_OUT, f"Falhou para: {msg}"

    def test_question(self):
        result = classify_intent("qual o preco?")
        assert result.intent == Intent.QUESTION

    def test_question_with_how(self):
        result = classify_intent("como funciona?")
        assert result.intent == Intent.QUESTION

    def test_objection_preco(self):
        result = classify_intent("quanto custa?")
        assert result.intent == Intent.OBJECTION

    def test_objection_caro(self):
        result = classify_intent("muito caro")
        assert result.intent == Intent.OBJECTION

    def test_buying_intent(self):
        result = classify_intent("quero comprar")
        assert result.intent == Intent.BUYING_INTENT

    def test_gatekeeper(self):
        result = classify_intent("nao sou o dono")
        assert result.intent == Intent.GATEKEEPER

    def test_empty_message(self):
        result = classify_intent("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    def test_long_message(self):
        result = classify_intent(
            "Ola! Vi seu site e achei muito interessante. "
            "Gostaria de saber mais detalhes sobre o servico."
        )
        assert result.intent in [Intent.ENGAGEMENT, Intent.QUESTION, Intent.GREETING]


class TestIntentResult:
    def test_default_values(self):
        result = IntentResult(intent=Intent.GREETING, confidence=0.8)
        assert result.signals == []
        assert result.raw_text == ""

    def test_all_fields(self):
        result = IntentResult(
            intent=Intent.QUESTION,
            confidence=0.9,
            signals=["?"],
            raw_text="qual o preco?",
        )
        assert result.intent == Intent.QUESTION
        assert result.confidence == 0.9
        assert "?" in result.signals
        assert result.raw_text == "qual o preco?"
