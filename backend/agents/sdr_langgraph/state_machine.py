"""SDR State Machine.

Arquitetura nova (substitui stage-driven loop por conversation state + intent):

- State (FSM): representa o ESTADO REAL da conversa. Não é funil linear.
  Estados: IDLE, WAITING_RESPONSE, ENGAGED, OBJECTING, BUYING, OPT_OUT, HANDED_OFF.
- Intent: o que o lead QUIS DIZER nesta mensagem. Vem do IntentClassifier.
- Stage: legado (franz.md). Mantido só pra UI / Kanban. Decisões sao state-driven.

Regra de ouro: o sistema decide transicao com base em (state, intent), nunca em stage sozinho.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ConversationState(str, Enum):
    """Estados da conversa. Nao sao lineares como o stage antigo."""
    IDLE = "idle"               # conversa acabou de comecar
    WAITING_RESPONSE = "waiting_response"  # bot mandou msg, lead ainda nao respondeu
    ENGAGED = "engaged"          # lead respondeu com conteudo util (pergunta, info)
    OBJECTING = "objecting"      # lead levantou objecao
    BUYING = "buying"            # lead pediu preco, link, demonstrou interesse de compra
    SCHEDULED = "scheduled"      # lead pediu pra voltar depois
    OPT_OUT = "opt_out"          # lead pediu pra parar
    HANDED_OFF = "handed_off"    # humano assumiu
    CLOSED_WON = "won"           # venda concluida
    CLOSED_LOST = "lost"         # lead descartado


class Intent(str, Enum):
    """O que o lead QUIS dizer. Classificado pelo IntentClassifier."""
    GREETING = "greeting"                 # "oi", "boa noite", "tudo bem"
    ACKNOWLEDGMENT = "acknowledgment"     # "ok", "hm", "entendi"
    ENGAGEMENT = "engagement"             # respondeu uma pergunta, deu info
    QUESTION = "question"                 # fez uma pergunta (preco, como funciona)
    OBJECTION = "objection"               # objecao (caro, nao confio, nao preciso)
    BUYING_INTENT = "buying_intent"       # "quero", "manda o link", "fecha"
    SCHEDULE = "schedule"                 # "depois", "amanha", "semana que vem"
    OPT_OUT = "opt_out"                   # "para", "nao quero", "me tira"
    GATEKEEPER = "gatekeeper"             # "nao sou o dono", "ele nao esta"
    OFF_TOPIC = "off_topic"               # msg fora do assunto
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StateDecision:
    """Resultado da decisao: novo state, novo stage (legado), intent, reasoning."""
    new_state: ConversationState
    new_stage: str  # stage legado pra UI (kanban)
    intent: Intent
    confidence: float
    reasoning: str
    should_advance: bool  # se o sistema considera que houve "progresso" real


# Matriz (state, intent) -> (new_state, new_stage, reasoning)
# Prioridade: intent > state. Se intent == OPT_OUT, vai pra OPT_OUT sempre.
_TRANSITIONS: dict[tuple[ConversationState, Intent], tuple[ConversationState, str, str]] = {
    # === IDLE (conversa recem-comecada, lead nunca respondeu) ===
    (ConversationState.IDLE, Intent.GREETING):
        (ConversationState.WAITING_RESPONSE, "hook", "lead cumprimentou; aguardar engajamento"),
    (ConversationState.IDLE, Intent.ENGAGEMENT):
        (ConversationState.ENGAGED, "qualify", "lead ja engajou; ir pra qualify"),
    (ConversationState.IDLE, Intent.QUESTION):
        (ConversationState.ENGAGED, "qualify", "lead perguntou; sinal de engajamento -> qualify"),
    (ConversationState.IDLE, Intent.OBJECTION):
        (ConversationState.OBJECTING, "qualify", "lead objecao logo de cara; tentar qualify"),
    (ConversationState.IDLE, Intent.BUYING_INTENT):
        (ConversationState.BUYING, "close", "lead quer comprar direto"),
    (ConversationState.IDLE, Intent.OPT_OUT):
        (ConversationState.OPT_OUT, "lost", "opt-out imediato"),

    # === WAITING_RESPONSE (bot mandou, lead respondeu com algo) ===
    (ConversationState.WAITING_RESPONSE, Intent.GREETING):
        # BUG FIX: se lead so cumprimentou de volta (ex: "boa noite" depois de hook),
        # NAO fica em loop. Mantem stage, mas marca que ele respondeu.
        (ConversationState.WAITING_RESPONSE, "hook", "lead respondeu com greeting; manter hook e fazer pergunta de engajamento"),
    (ConversationState.WAITING_RESPONSE, Intent.ACKNOWLEDGMENT):
        (ConversationState.WAITING_RESPONSE, "hook", "lead disse ok/hm; insistir com pergunta concreta"),
    (ConversationState.WAITING_RESPONSE, Intent.ENGAGEMENT):
        (ConversationState.ENGAGED, "qualify", "lead respondeu com conteudo -> qualify"),
    (ConversationState.WAITING_RESPONSE, Intent.QUESTION):
        (ConversationState.ENGAGED, "qualify", "lead fez pergunta -> qualify"),
    (ConversationState.WAITING_RESPONSE, Intent.OBJECTION):
        (ConversationState.OBJECTING, "qualify", "objecao -> tentar qualify depois"),
    (ConversationState.WAITING_RESPONSE, Intent.BUYING_INTENT):
        (ConversationState.BUYING, "close", "lead quer comprar -> close"),
    (ConversationState.WAITING_RESPONSE, Intent.SCHEDULE):
        (ConversationState.SCHEDULED, "scheduled", "lead quer agendar"),
    (ConversationState.WAITING_RESPONSE, Intent.OPT_OUT):
        (ConversationState.OPT_OUT, "lost", "opt-out"),
    (ConversationState.WAITING_RESPONSE, Intent.GATEKEEPER):
        (ConversationState.ENGAGED, "qualify", "gatekeeper -> tentar pegar decisor"),
    (ConversationState.WAITING_RESPONSE, Intent.OFF_TOPIC):
        (ConversationState.WAITING_RESPONSE, "hook", "lead fugiu do assunto; voltar pro contexto"),

    # === ENGAGED (lead ja engajou, qualificando) ===
    (ConversationState.ENGAGED, Intent.GREETING):
        (ConversationState.ENGAGED, "qualify", "lead cumprimentou; avancar pra pain"),
    (ConversationState.ENGAGED, Intent.ENGAGEMENT):
        (ConversationState.ENGAGED, "pain", "lead deu mais info -> pain"),
    (ConversationState.ENGAGED, Intent.QUESTION):
        (ConversationState.ENGAGED, "pain", "lead perguntou algo -> responder e ir pra pain"),
    (ConversationState.ENGAGED, Intent.OBJECTION):
        (ConversationState.OBJECTING, "pain", "objecao -> tratar"),
    (ConversationState.ENGAGED, Intent.BUYING_INTENT):
        (ConversationState.BUYING, "close", "lead quer -> close"),
    (ConversationState.ENGAGED, Intent.SCHEDULE):
        (ConversationState.SCHEDULED, "scheduled", "lead quer agendar"),
    (ConversationState.ENGAGED, Intent.OPT_OUT):
        (ConversationState.OPT_OUT, "lost", "opt-out"),

    # === OBJECTING (lead com objecao) ===
    (ConversationState.OBJECTING, Intent.OBJECTION):
        (ConversationState.OBJECTING, "pain", "objecao persistindo; insistir"),
    (ConversationState.OBJECTING, Intent.ENGAGEMENT):
        (ConversationState.ENGAGED, "amplify", "lead aceitou discutir; amplify"),
    (ConversationState.OBJECTING, Intent.QUESTION):
        (ConversationState.ENGAGED, "amplify", "lead quer saber mais; amplify"),
    (ConversationState.OBJECTING, Intent.BUYING_INTENT):
        (ConversationState.BUYING, "close", "objecao resolvida -> close"),
    (ConversationState.OBJECTING, Intent.OPT_OUT):
        (ConversationState.OPT_OUT, "lost", "opt-out"),

    # === BUYING (lead quer comprar) ===
    (ConversationState.BUYING, Intent.OBJECTION):
        (ConversationState.OBJECTING, "close", "objecao tardia; tratar"),
    (ConversationState.BUYING, Intent.QUESTION):
        (ConversationState.BUYING, "close", "lead ainda perguntando; responder e fechar"),
    (ConversationState.BUYING, Intent.OPT_OUT):
        (ConversationState.OPT_OUT, "lost", "opt-out"),

    # === SCHEDULED / OPT_OUT / HANDED_OFF / CLOSED_* sao terminais (sem transicao) ===
}


def decide_transition(
    current_state: ConversationState,
    intent: Intent,
    suggested_stage: Optional[str] = None,
    turn_count: int = 0,
) -> StateDecision:
    """Decide novo (state, stage) baseado em (state, intent).

    Args:
        current_state: estado atual da FSM.
        intent: o que o lead quis dizer (ja classificado).
        suggested_stage: stage que o LLM sugeriu (legado). Usado apenas pra logging.
        turn_count: quantos turnos se passaram (ajuda em casos ambiguos).

    Returns:
        StateDecision com new_state, new_stage, reasoning.
    """
    # Override 1: intents terminais vao direto, independente do state.
    if intent == Intent.OPT_OUT:
        return StateDecision(
            new_state=ConversationState.OPT_OUT,
            new_stage="lost",
            intent=intent,
            confidence=1.0,
            reasoning="opt-out detectado; encerrar conversa",
            should_advance=False,
        )
    if intent == Intent.BUYING_INTENT:
        # Se ja engajou (ja qualificou/pain/amplify/tease/proof), lead ta pronto pra comprar
        if current_state == ConversationState.ENGAGED:
            return StateDecision(
                new_state=ConversationState.BUYING,
                new_stage="close",
                intent=intent,
                confidence=0.9,
                reasoning="lead engajado pediu compra -> close",
                should_advance=True,
            )
        # Se esta em OBJECTING (objecao resolvida), vai pra BUYING
        if current_state == ConversationState.OBJECTING:
            return StateDecision(
                new_state=ConversationState.BUYING,
                new_stage="close",
                intent=intent,
                confidence=0.85,
                reasoning="lead com objecao pediu compra -> close",
                should_advance=True,
            )
        # Se esta em IDLE/WAITING_RESPONSE (sem contexto), qualifica antes
        if current_state in (ConversationState.IDLE, ConversationState.WAITING_RESPONSE):
            return StateDecision(
                new_state=ConversationState.ENGAGED,
                new_stage="qualify",
                intent=intent,
                confidence=0.8,
                reasoning="lead quer comprar mas contexto insuficiente; qualify antes de close",
                should_advance=True,
            )

    # Override 2: greeting em IDLE/WAITING_RESPONSE quando turn_count >= 2
    # significa lead ta respondendo de volta mas sem conteudo -> NAO loopar.
    if intent == Intent.GREETING and current_state in (
        ConversationState.IDLE,
        ConversationState.WAITING_RESPONSE,
    ) and turn_count >= 2:
        # Ja tentamos hook. Lead nao engajou. Manter state mas forcar proxima pergunta
        # ser mais direta (responsabilidade do Composer, nao da FSM).
        return StateDecision(
            new_state=ConversationState.WAITING_RESPONSE,
            new_stage="hook",
            intent=intent,
            confidence=0.6,
            reasoning=f"lead so cumprimentou {turn_count}x; manter hook mas quebrar com pergunta direta",
            should_advance=False,  # nao avanca stage; mas Composer deve forcar engajamento
        )

    # Transicao normal via matriz
    key = (current_state, intent)
    if key in _TRANSITIONS:
        new_state, new_stage, reasoning = _TRANSITIONS[key]
        # should_advance = True SE houve progresso real:
        # - state mudou pra ENGAGED/OBJECTING/BUYING/OPT_OUT/CLOSED_*/SCHEDULED, OU
        # - stage subiu no funil (legado).
        # NAO conta como "advance" se foi apenas IDLE/WAITING_RESPONSE -> WAITING_RESPONSE
        # (lead so respondeu, sem conteudo util).
        productive_states = {
            ConversationState.ENGAGED,
            ConversationState.OBJECTING,
            ConversationState.BUYING,
            ConversationState.OPT_OUT,
            ConversationState.SCHEDULED,
            ConversationState.HANDED_OFF,
            ConversationState.CLOSED_WON,
            ConversationState.CLOSED_LOST,
        }
        state_advanced = (new_state != current_state) and (new_state in productive_states)
        stage_advanced = False
        if new_stage != suggested_stage:
            stage_order = ["hook", "qualify", "pain", "amplify", "tease", "proof", "reveal", "feedback", "close"]
            if new_stage in stage_order and suggested_stage in stage_order:
                stage_advanced = stage_order.index(new_stage) > stage_order.index(suggested_stage)
            elif suggested_stage not in stage_order:
                stage_advanced = True
        should_advance = state_advanced or stage_advanced
        return StateDecision(
            new_state=new_state,
            new_stage=new_stage,
            intent=intent,
            confidence=0.9,
            reasoning=reasoning,
            should_advance=should_advance,
        )

    # Fallback: intent nao mapeado. Mantem state e stage, nao trava.
    return StateDecision(
        new_state=current_state,
        new_stage=suggested_stage or _state_to_default_stage(current_state),
        intent=intent,
        confidence=0.3,
        reasoning=f"intent {intent.value} nao mapeado para state {current_state.value}; manter",
        should_advance=False,
    )


def _state_to_default_stage(state: ConversationState) -> str:
    """Mapeia state -> stage legado (para UI/kanban)."""
    mapping = {
        ConversationState.IDLE: "hook",
        ConversationState.WAITING_RESPONSE: "hook",
        ConversationState.ENGAGED: "qualify",
        ConversationState.OBJECTING: "pain",
        ConversationState.BUYING: "close",
        ConversationState.SCHEDULED: "scheduled",
        ConversationState.OPT_OUT: "lost",
        ConversationState.HANDED_OFF: "handoff",
        ConversationState.CLOSED_WON: "won",
        ConversationState.CLOSED_LOST: "lost",
    }
    return mapping.get(state, "hook")


def detect_loop(turn_count: int, state: ConversationState) -> bool:
    """Detecta se o sistema esta travado no mesmo state por muitos turnos."""
    if turn_count < 3:
        return False
    return state in (ConversationState.IDLE, ConversationState.WAITING_RESPONSE)