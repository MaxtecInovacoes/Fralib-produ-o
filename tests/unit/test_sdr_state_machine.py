"""Testes para state_machine.py e intent_classifier.py.

Cobre:
- Transicoes de state validas e invalidas
- Classificacao de intent
- Matriz de decisao (state, intent) -> (new_state, stage)
"""

import pytest
from backend.agents.sdr_langgraph.state_machine import (
    ConversationState,
    Intent,
    StateDecision,
    decide_transition,
    detect_loop,
)
from backend.agents.sdr_langgraph.intent_classifier import (
    classify_intent,
    IntentResult,
)


# TESTES: state_machine.py

class TestConversationState:
    """Testes para ConversationState enum."""

    def test_all_states_exist(self):
        """Todos os estados devem existir."""
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
    """Testes para Intent enum."""

    def test_all_intents_exist(self):
        """Todos os intents devem existir."""
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
    """Testes para decide_transition()."""

    def test_idle_to_greeting(self):
        """Idle + greeting = engaged."""
        decision = decide_transition(
            current_state=ConversationState.IDLE,
            intent=Intent.GREETING,
            suggested_stage=None,
            turn_count=1,
        )
        assert decision.new_state == ConversationState.ENGAGED
        assert decision.should_advance is True

    def test_opt_out_always_stays(self):
        """Opt-out + qualquer intent = opt-out."""
        for intent in Intent:
            decision = decide_transition(
                current_state=ConversationState.OPT_OUT,
                intent=intent,
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
    """Testes para detect_loop()."""

    def test_no_loop_early_turns(self):
        """Turns 1-2 nao sao loop."""
        for turn in range(1, 3):
            assert detect_loop(turn, ConversationState.GREETING) is False

    def test_loop_after_3_greetings(self):
        """Apos turno 3 + greeting constante = loop."""
        assert detect_loop(3, ConversationState.GREETING) is True
        assert detect_loop(5, ConversationState.GREETING) is True

    def test_loop_only_greeting_acknowledgment(self):
        """Loop so detecta para GREETING e ACKNOWLEDGMENT."""
        assert detect_loop(4, ConversationState.ACKNOWLEDGMENT) is True
        assert detect_loop(4, ConversationState.ENGAGEMENT) is False


# TESTES: intent_classifier.py

class TestClassifyIntent:
    """Testes para classify_intent()."""

    def test_greeting(self):
        """Mensagens de saudacao sao classificadas."""
        for msg in ["oi", "ola", "boa noite"]:
            result = classify_intent(msg)
            assert result.intent == Intent.GREETING, f"Falhou para: {msg}"

    def test_opt_out(self):
        """Mensagens de opt-out sao classificadas."""
        for msg in ["nao quero mais", "para de me mandar"]:
            result = classify_intent(msg)
            assert result.intent == Intent.OPT_OUT, f"Falhou para: {msg}"

    def test_question(self):
        """Perguntas sao classificadas."""
        result = classify_intent("quanto custa?")
        assert result.intent == Intent.QUESTION

    def test_objection(self):
        """Objecoes sao classificadas."""
        result = classify_intent("muito caro")
        assert result.intent == Intent.OBJECTION

    def test_buying_intent(self):
        """Intencao de compra e classificada."""
        result = classify_intent("quero comprar")
        assert result.intent == Intent.BUYING_INTENT

    def test_gatekeeper(self):
        """Gatekeeper e classificado."""
        result = classify_intent("nao sou o dono")
        assert result.intent == Intent.GATEKEEPER

    def test_empty_message(self):
        """Msg vazia retorna UNKNOWN."""
        result = classify_intent("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    def test_long_message(self):
        """Msg longa com contexto = engagement."""
        result = classify_intent(
            "Ola! Vi seu site e achei muito interessante. "
            "Gostaria de saber mais detalhes sobre o servico."
        )
        assert result.intent in [Intent.ENGAGEMENT, Intent.QUESTION, Intent.GREETING]
