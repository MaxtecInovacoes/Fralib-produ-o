"""
SDR Graph - Define o grafo de estados do agente.
Cada node é um estágio ou ação. Edges definem as transições.

⚠️  ORQUESTRADOR - NÃO É MONOLITO
=================================
Este arquivo é um ORQUESTRADOR que define o grafo LangGraph.
Lógica extraída para:
- state.py: Definições de estado
- nodes/__init__.py: Nodes do grafo
- tools.py: Ferramentas do agente
- prompts.py: Prompts do sistema
- learning.py: Aprendizado e ajuste
- multi_agent.py: Multi-agente
- watchdog.py: Watchdog/timeout
- compat.py: Compatibilidade

@architecture Orquestrador (define grafo, coordena nodes)
"""

from __future__ import annotations
import os
import sys
import json
import re
from typing import Any

try:
    from langgraph.graph import StateGraph, END
    _LANGGRAPH_IMPORT_ERROR: Exception | None = None
except Exception as _exc:
    StateGraph = None  # type: ignore[assignment]
    END = "__end__"
    _LANGGRAPH_IMPORT_ERROR = _exc

# Setup paths
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(AGENTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, AGENTS_DIR)

from .state import SDRState, LeadMemory
from .tools import (
    load_rag,
    detect_intent_with_llm,
    check_segment_contamination,
    is_valid_length,
    has_one_question,
    is_within_schedule,
    get_greeting,
    choose_variant,
)
from .turn_tracing import sdr_traced, start_turn_trace, end_turn_trace, get_active_trace
from .prompts import (
    build_stage_prompt,
    build_user_prompt,
    should_use_lobo,
    get_persona_text,
    get_franz_persona,
    get_franz_stage_prompt,
    get_franz_rag,
)
from .multi_agent import (
    agent_system_overlay,
    build_agent_context,
    choose_agent,
    record_agent_handoff,
    save_agent_note,
)
from .learning import evaluate_bot_turn, learning_overlay


STAGE_PROGRESSION = [
    "hook", "qualify", "pain", "amplify", "tease",
    "proof", "reveal", "feedback", "close"
]


def _normalize_memory_payload(raw: dict | None) -> dict:
    """Aceita memoria antiga nested e memoria nova flat do Franz."""
    data = dict(raw or {})
    nested = data.get("lead")
    if isinstance(nested, dict):
        for key, value in nested.items():
            if key in LeadMemory.model_fields and value and not data.get(key):
                data[key] = value
    if data.get("estado") and not data.get("stage"):
        data["stage"] = data.get("estado")
    return data


class SDRFallbackError(Exception):
    """Exceção quando LLM falha apos retries. NAO usa template pre-definido.

    Sprint 1.7: caller captura, marca memory.needs_human_followup=True,
    NAO envia mensagem. Humano precisa intervir.
    """
    pass


def _llm_with_retries_and_breaker(stage: str, fn):
    """Chama fn() (que faz call_claude) com:
    - circuit breaker guard antes
    - retry 3x com backoff 5/15/30s + jitter
    - em sucesso: fecha circuito do stage
    - em falha: registra, levanta SDRFallbackError

    NAO retorna texto generico. Se tudo falhar, propaga erro pra caller.
    """
    from services.retry_helper import retry_with_backoff
    from .circuit_breaker import get_breaker

    breaker = get_breaker()
    breaker.guard(stage)  # CircuitOpenError se aberto

    @retry_with_backoff(max_retries=3, base_delay=5.0, max_delay=30.0)
    def _attempt():
        # Cada tentativa registra falha aqui pra circuit abrir após 3 tentativas
        try:
            reply = fn()
            if not reply or not reply.strip():
                raise SDRFallbackError(f"LLM {stage} returned empty reply")
            return reply
        except Exception as exc:
            breaker.record_failure(stage)
            raise

    try:
        reply = _attempt()
        breaker.record_success(stage)
        return reply
    except Exception as exc:
        # Garante 1 falha registrada mesmo se escape ocorreu
        if isinstance(exc, SDRFallbackError):
            raise
        breaker.record_failure(stage)
        raise SDRFallbackError(f"LLM {stage} failed after retries: {exc}") from exc


def _next_stage(current: str, suggested: str, fallback: str) -> str:
    current = current or "hook"
    suggested = suggested or fallback or current
    if suggested in {"opt_out", "lost", "won", "handoff", "scheduled", "gatekeeper"}:
        return suggested
    if current not in STAGE_PROGRESSION or suggested not in STAGE_PROGRESSION:
        return fallback or current
    current_idx = STAGE_PROGRESSION.index(current)
    suggested_idx = STAGE_PROGRESSION.index(suggested)
    if suggested_idx <= current_idx:
        return current
    return STAGE_PROGRESSION[min(current_idx + 1, suggested_idx)]


def _orchestrator_decide(
    memory,
    incoming_message: str,
    llm_suggested_stage: str,
) -> "OrchestratorDecision":
    """Wrapper do Orchestrator. Substitui o _next_stage antigo na logica de decisao.

    Mantem compatibilidade: retorna OrchestratorDecision com state + stage.
    Na duvida, falha fechado para retry em vez de escolher estado legado.
    """
    try:
        from .orchestrator import orchestrate, update_lead_memory_after_turn
        decision = orchestrate(
            incoming_message=incoming_message or "",
            current_state_str=memory.conversation_state or "idle",
            current_stage=memory.stage or "hook",
            turn_count=memory.turn_count or 0,
            suggested_stage=llm_suggested_stage,
        )
        update_lead_memory_after_turn(memory, decision)
        return decision
    except Exception as e:
        raise SDRFallbackError(f"orchestrator failed: {e}") from e


# ════════════════════════════════════════════════════════════════════
# NODE 1: load_context (entrada - carrega tudo que precisa)
# ════════════════════════════════════════════════════════════════════

def _simplify_language(reply: str) -> str:
    """Reescreve a reply com tom didatico, como se fosse pra crianca de 10 anos.

    Heuristicas simples (sem LLM call pra nao custar):
    - Remove jargoes comuns
    - Substitui palavras formais por coloquiais
    - Corta redundancias
    - Garante tom de WhatsApp

    Aplica transformacoes leves. NAO muda o conteudo, so a forma.
    """
    if not reply:
        return reply

    import re
    result = reply

    # Gírias e palavras em inglês - aplica em TODAS as mensagens
    gíria_replacements = [
        (r"\bvc\b", "você"),
        (r"\bvcs\b", "vocês"),
        (r"\bpq\b", "porque"),
        (r"\bq\b\b", "que"),
        (r"\btmj\b", "tamo junto"),
        (r"\bmsm\b", "mesmo"),
        (r"\btb\b", "também"),
        (r"\blgpd\b", "LGPD"),
        (r"\bmto\b", "muito"),
        (r"\bhj\b", "hoje"),
        (r"\bflw\b", "falou"),
        (r"\bvlw\b", "valeu"),
        (r"\btd\b", "tudo"),
        (r"\bmds\b", "meu Deus"),
        (r"\bsds\b", "meu Deus"),
        (r"\bpdc\b", "pode crer"),
        (r"\bkkkk\b", "kk"),
        (r"\bfeedback\b", "opinião"),
        (r"\bfollow\s*up\b", "retorno"),
        (r"\blead\b", "cliente"),
    ]
    for pattern, replacement in gíria_replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Só simplifica conteúdo de mensagens longas
    if len(result) < 20:
        return result

    # Substituicoes: jargao -> linguagem simples
    # Ordem importa: regras mais especificas ANTES das genericas.
    # "captam" (3a pessoa) -> "atraem" (preserva conjugacao)
    # "captar/captacao" -> "atrar/atrat" (infinitivo / substantivo)
    replacements = [
        (r"\bcaptam\b", "atraem"),
        (r"\bcaptando\b", "atrando"),
        (r"\bcaptar\b", "atrar"),
        (r"\bcaptacao\b", "atrat"),
        (r"\bcapt[aá]vamos\b", "atraiamos"),
        (r"\botimizar?\b", "melhorar"),
        (r"\bimplementa[rm]os?\b", "fazemos"),
        (r"\bsoluç(?:ões|oes|oes?)\b", "coisas"),
        (r"\bsolucoes\b", "coisas"),
        (r"\bsolucao\b", "coisa"),
        (r"\bconvers[aã]o\b", "cliente que vem"),
        (r"\bconversoes\b", "clientes que vem"),
        (r"\bvisualiza[çc]ao\b", "ver"),
        (r"\bferramenta\b", "coisa"),
        (r"\bplataforma\b", "coisa"),
        (r"\bferramentas\b", "coisas"),
        (r"\bdesenvolver\b", "fazer"),
        (r"\bdesenvolvemos\b", "fazemos"),
        (r"\bdigital\b", "online"),
        (r"\bdigitalizar\b", "colocar online"),
        (r"\bmaximiz[aá]r\b", "aumentar"),
        (r"\bperformance\b", "resultado"),
        (r"\bconversion\b", "cliente"),
        (r"\bagendar uma (call|conversa|reuni[aã]o|reuniao)\b", "marcar um bate-papo"),
        (r"\bcall\b", "conversa"),
        (r"\bpoderia\b", "pode"),
        # "gostaria de [verbo]" -> "quer [verbo]" (forma mais comum)
        (r"\bgostaria de\b", "quer"),
        # "gostaria" sozinho (sem "de") -> "queria" (soa mais natural em pt-BR)
        (r"\bgostaria\b", "queria"),
        # Colapsa "quer/queria [muito] de [verbo]" -> sem o "de" (glitch do gostaria de + outro verbo)
        (r"\b(quer|queria)\s+(\w+\s+)?de\s+(\w+)\b", r"\1 \2\3"),
        (r"\bsolicitar\b", "pedir"),
        (r"\bdespesa\b", "gasto"),
        (r"\bvalores\b", "preço"),
        (r"\bcontratacao\b", "fechar"),
        (r"\bcontratar\b", "fechar"),
        (r"\badquirir\b", "comprar"),
        (r"\bsoluç(?:ões|oes|oes?)\s+personalizadas?\b", "coisa sob medida"),
        (r"\bsolucoes?\s+personalizadas?\b", "coisa sob medida"),
        (r"\bROI\b", "retorno"),
        (r"\balavanc[aá]r\b", "fazer crescer"),
        (r"\balavancagem\b", "crescimento"),
        (r"\boptimi[zs]e\b", "melhore"),
        (r"\butilizar\b", "usar"),
        (r"\bfeedback\b", "opinião"),
        (r"\bfollow\s*up\b", "retorno"),
        (r"\blead\b", "cliente"),
        (r"\bonline\b", "online"),
    ]
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def _reply_already_has_offer(reply: str) -> bool:
    """Heuristica: detecta se a reply ja tem uma oferta de site.

    Evita duplicar a oferta (ex: LLM ja mandou link + Studio prependeria de novo).
    """
    if not reply:
        return False
    reply_lower = reply.lower()
    signals = [
        "site_url" in reply_lower,
        "demonstra" in reply_lower,
        "fralib.com" in reply_lower or "seunegociofralib" in reply_lower,
        "link" in reply_lower and ("site" in reply_lower or "prév" in reply_lower or "prévio" in reply_lower),
        "leva 2 min" in reply_lower,
        "sem custo" in reply_lower,
    ]
    return any(signals)


@sdr_traced("node_load_context")
def node_load_context(state: SDRState) -> dict:
    """Carrega memória do lead, RAG, contexto inicial"""
    try:
        from utils.pii_masker import mask_phone as _mp
        _tel = _mp(state.get("telefone", "?"))
    except Exception:
        _tel = "****"
    print(f"[SDR] Loading context for {_tel}")

    # === Sprint 1.2 — Bug #2 fix: history injetada ANTES de montar LeadMemory ===
    # Antes: o state["history"] (lista de turnos anteriores: [{"role": "user/assistant",
    #        "content": "..."}]) era ignorado aqui — só aparecia mais tarde em nodes
    #        downstream, depois de LeadMemory já estar montado. Resultado: no turno
    #        3-4 o Franz esquecia o que o lead disse no turno 1.
    # Agora: lemos a history ANTES, populamos o LeadMemory com last_message_received/
    #        last_message_sent/turn_count e devolvemos ``history`` no resultado
    #        para o resto do grafo consumir (back-compat: se history vazio,
    #        caímos no fallback do JSON do carregar_memoria).
    state_history = state.get("history") or []

    # Carregar memória
    try:
        from agents.memory import carregar_memoria
        session_id = f"franz_lead_{state.get('telefone', '')}"
        memoria_raw = carregar_memoria(session_id, user_id=state.get("user_id"))
        if memoria_raw:
            memoria_payload = _normalize_memory_payload(memoria_raw)
            # Construir LeadMemory do dict
            try:
                memory = LeadMemory(
                    lead_id=state.get("lead_id", state.get("telefone", "")),
                    user_id=state.get("user_id", 0),
                    telefone=state.get("telefone", ""),
                    **{
                        k: v for k, v in memoria_payload.items()
                        if k in LeadMemory.model_fields and k not in ("lead_id", "user_id", "telefone")
                    }
                )
            except Exception:
                memory = LeadMemory(
                    lead_id=state.get("lead_id", state.get("telefone", "")),
                    user_id=state.get("user_id", 0),
                    telefone=state.get("telefone", ""),
                )
        else:
            memory = LeadMemory(
                lead_id=state.get("lead_id", state.get("telefone", "")),
                user_id=state.get("user_id", 0),
                telefone=state.get("telefone", ""),
            )
    except Exception as e:
        print(f"[SDR] Erro ao carregar memória: {e}")
        memory = LeadMemory(
            lead_id=state.get("lead_id", state.get("telefone", "")),
            user_id=state.get("user_id", 0),
            telefone=state.get("telefone", ""),
        )

    # O banco da chamada atual e a fonte de verdade para identidade do lead.
    # Isso evita memoria antiga/vazia contaminando outro contexto do mesmo telefone.
    for field in ("lead_id", "nome", "cidade", "segmento", "site_url", "paleta_cores"):
        value = state.get(field)
        if value:
            setattr(memory, field, value)
    if state.get("rating"):
        memory.rating = state.get("rating") or 0.0
    memory.user_id = state.get("user_id", memory.user_id)
    memory.telefone = state.get("telefone", memory.telefone)
    state_stage = (state.get("sdr_stage") or "").strip()
    if state_stage and state_stage not in {
        "pendente_wpp", "pending_sdr_send", "blocked_plan", "sdr_enqueue_failed"
    }:
        memory.stage = state_stage

    # Detectar intent
    incoming = state.get("incoming_message", "")
    if incoming:
        intent = detect_intent_with_llm(incoming)
    else:
        intent = "other"

    # Escolher persona baseado no intent e rejection_count
    memory_ref = memory  # usar referência
    persona = state.get("persona")
    if not persona or persona == "auto":
        persona = "lobo" if should_use_lobo(
            intent,
            memory_ref.rejection_count if memory_ref else 0,
        ) else "consultivo"

    print(f"[SDR] Intent detected: {intent}")
    print(f"[SDR] Memory stage: {memory.stage}")
    print(f"[SDR] Persona: {persona}")

    selected_agent, handoff_reason = choose_agent(
        intent=intent,
        stage=memory.stage,
        incoming=incoming,
        is_outbound=bool(state.get("is_outbound")),
    )
    agent_context = build_agent_context(memory, selected_agent, handoff_reason)
    record_agent_handoff(memory, selected_agent, handoff_reason)
    rag_context = load_rag(selected_agent)
    # === Sprint 12.9+: concatenar FRANZ_RAG.md se flag ativa ===
    try:
        franz_md_rag = get_franz_rag()
        if franz_md_rag:
            rag_context = f"{franz_md_rag}\n\n{rag_context}"
    except Exception as _rag_err:
        print(f"[SDR] get_franz_rag falhou (nao-bloqueante): {_rag_err}")
    rag_context = f"{rag_context}\n\n{learning_overlay(memory.user_id, selected_agent)}"

    print(f"[SDR] Agent selected: {selected_agent} ({handoff_reason})")

    # === Sprint 1.2 — Bug #2 fix: hidratar LeadMemory com state["history"] ===
    # Se o runtime passou history (caso comum — ver whatsapp_listener / simulator),
    # usa como fonte de verdade para last_message_received / last_message_sent /
    # turn_count. Isso garante que o LLM consegue referenciar o turno 1 quando
    # o lead responde no turno 3-4.
    if state_history:
        try:
            last_user_msg = ""
            last_assistant_msg = ""
            user_turns = 0
            for h in state_history:
                role = (h.get("role") or "").strip()
                content = (h.get("content") or "").strip()
                if not content:
                    continue
                if role == "user":
                    last_user_msg = content
                    user_turns += 1
                elif role == "assistant":
                    last_assistant_msg = content
            if last_user_msg:
                memory.last_message_received = last_user_msg[:1000]
            if last_assistant_msg:
                memory.last_message_sent = last_assistant_msg[:1000]
            if user_turns and not memory.turn_count:
                memory.turn_count = user_turns
            from datetime import datetime as _dt
            memory.last_lead_response_at = _dt.now().isoformat()
        except Exception as _hist_err:
            print(f"[SDR] history hydration falhou (nao-bloqueante): {_hist_err}")

    return {
        "memory": memory,
        "rag_context": rag_context,
        "detected_intent": intent,
        "current_stage": memory.stage,
        "variant": memory.variant or choose_variant(memory.lead_id, memory.segmento, memory.user_id),
        "persona": persona,
        "selected_agent": selected_agent,
        "previous_agent": agent_context.get("previous_agent", ""),
        "agent_context": agent_context,
        "agent_handoff_reason": handoff_reason,
        # Sprint 1.2 — passa history adiante pro próximo node.
        # Se state já tinha history, repassa a mesma; senão repassa [].
        # Garante que o grafo inteiro consegue iterar state["history"] sem
        # precisar reler do storage.
        "history": state_history,
    }


# ════════════════════════════════════════════════════════════════════
# NODE 2: check_schedule (verifica horário)
# ════════════════════════════════════════════════════════════════════

@sdr_traced("node_check_schedule")
def node_check_schedule(state: SDRState) -> dict:
    """Verifica se está no horário de atendimento"""
    if not is_within_schedule(state.get("user_id")):
        print("[SDR] Fora do horário")
        return {
            "should_send": False,
            "guard_reason": "outside_schedule",
            "outgoing_message": "",
        }
    return {}


# ════════════════════════════════════════════════════════════════════
# NODE 3: route_intent (decide qual node executar)
# ════════════════════════════════════════════════════════════════════

def route_by_intent(state: SDRState) -> str:
    """Decide qual node executar baseado no intent"""
    intent = state.get("detected_intent", "other")
    stage = state.get("current_stage", "hook")
    stage_aliases = {
        "intro": "qualify",
        "followup1": "followup_24h",
        "followup2": "followup_72h",
        "f1": "followup_24h",
        "f2": "followup_72h",
    }
    stage = stage_aliases.get(stage, stage)

    # Routes diretas por intent
    if intent == "opt_out":
        return "node_opt_out"
    if intent == "gatekeeper":
        return "node_gatekeeper"
    if intent == "schedule":
        return "node_schedule"
    if intent == "is_decisor":
        return "node_is_decisor"
    if intent == "greeting":
        return "node_greeting"

    # Caso contrário, vai para o node do stage atual
    return f"node_{stage}"


def route_after_schedule(state: SDRState) -> str:
    """Interrompe o grafo quando o guard de horário bloqueia a chamada."""
    if state.get("guard_reason") == "outside_schedule" and not state.get("should_send"):
        return "save_and_send"
    return route_by_intent(state)


@sdr_traced("node_greeting")
def node_greeting(state: SDRState) -> dict:
    """Cumprimento inbound: retoma contexto e conduz com uma pergunta curta."""
    memory = state.get("memory")
    if not memory:
        return {"outgoing_message": "", "should_send": False}

    # === SDR Turn Tracing (Feature #4 do roadmap 10/10) ===
    # Wrap todo o atendimento em 1 trace com 3 spans.
    _turn_trace = None
    try:
        from .turn_tracing import SDRTurnTrace
        _turn_trace = SDRTurnTrace(
            lead_id=str(state.get("lead_id") or state.get("telefone") or "unknown"),
            lead_nome=memory.nome or "",
            nicho=memory.segmento or "default",
        )
        _span_intent = _turn_trace.start_span("intent_classifier", agente="franz")
    except Exception as _trace_err:
        print(f"[SDR] tracing init falhou (nao-bloqueante): {_trace_err}")

    greeting = get_greeting()
    history = state.get("history", []) or []
    prior_assistant = next(
        (
            (h.get("content") or "").strip()
            for h in reversed(history)
            if h.get("role") == "assistant" and (h.get("content") or "").strip()
        ),
        "",
    )

    # ANTES: templates fixos (sempre "Retomando o que te mandei...") - REPETITIVO
    # AGORA: chamar LLM pra gerar resposta contextual e variada
    incoming_msg = state.get("incoming_message", "")
    try:
        from agents.llm_direct import call_claude
        contexto = f"Lead respondeu: '{incoming_msg}'"
        if memory.segmento:
            contexto += f" | Segmento: {memory.segmento}"
        if memory.nome:
            contexto += f" | Nome do negocio: {memory.nome}"
        if memory.cidade:
            contexto += f" | Cidade: {memory.cidade}"
        if prior_assistant:
            contexto += f" | Ultima msg minha: '{prior_assistant[:200]}'"

        system = (
            "Voce e o Franz, assistente virtual de uma empresa local brasileira. "
            "REGRAS OBRIGATORIAS (nao quebre nenhuma):\n"
            "1. Responda APENAS em portugues brasileiro. NUNCA em chines, japones ou outro idioma.\n"
            "2. MAXIMO 2 frases curtas (no maximo 80 palavras totais).\n"
            "3. NAO use templates fixos como 'Retomando o que te mandei'.\n"
            "4. NAO use placeholders como [nome] ou {nome}.\n"
            "5. Use o nome do lead se disponivel no contexto.\n"
            "6. Faca 1 pergunta aberta no final.\n"
            "7. Tom: educado, levemente informal, 1 emoji no maximo.\n"
            "8. NUNCA use caracteres chineses, japoneses ou coreanos.\n"
            "9. Se o lead parece ser bot/recepcionista, faca pergunta pra confirmar se e humano.\n"
            "10. NAO fale em nome proprio alem de 'Franz'.\n"
            "11. NAO mencione o segmento de forma robotica como template.\n"
            "Exemplo BOM: 'Oi Jéssica! Tudo ótimo por aqui. Você é nutricionista em Curitiba mesmo?'\n"
            "Exemplo RUIM: 'Retomando o que te mandei: hoje a prioridade de vocês é captar mais clientes para nutricionista.'\n"
        )
        llm_reply = _llm_with_retries_and_breaker("greeting", lambda: call_claude(
            system=system,
            user=contexto[:500],
            model="sonnet",  # Sonnet (Haiku falha no proxy kpalabz)
            max_tokens=120,  # 2-3 frases curtas, NAO tagarelando
            temperature=0.3,  # baixa variacao, evita chines/outros idiomas
            agent_name="sdr_greeting_node",
            respect_agent_config=False,
            enable_context=False,
        ).strip())
        reply = llm_reply
    except SDRFallbackError:
        # Sprint 1.7: marca pra humano, NAO envia nada
        memory.needs_human_followup = True
        memory.last_failure_stage = "greeting"
        try:
            from utils.safe_log import safe_log_silent_failure as _slf
            _slf(
                Exception("greeting SDRFallbackError"),
                op="sdr_greeting", lead_id=str(getattr(memory, "lead_id", "?")),
                stage="greeting",
                extra={"reason": "LLM failed after retries"},
            )
        except Exception:
            pass
        return {
            "outgoing_message": "",
            "should_send": False,
            "memory": memory,
            "next_stage": memory.stage,
            "needs_human_followup": True,
        }
    except Exception as _g_err:
        # NAO USA FALLBACK - lancar erro para retry
        raise SDRFallbackError(f"LLM greeting failed: {_g_err}") from _g_err

    memory.last_message_received = state.get("incoming_message", "")
    memory.last_message_sent = reply
    save_agent_note(memory, state.get("selected_agent") or "atendimento", "Lead cumprimentou/abriu conversa; Franz gerou resposta contextual via LLM.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": memory.stage,
    }


# ════════════════════════════════════════════════════════════════════
# NODE 4: node_hook (primeira abordagem)
# ════════════════════════════════════════════════════════════════════

@sdr_traced("node_hook")
def node_hook(state: SDRState) -> dict:
    """Stage HOOK - primeira mensagem"""
    memory = state.get("memory")
    if not memory:
        return {"outgoing_message": "", "should_send": False}

    greeting = get_greeting()
    variant = state.get("variant", "A")

    if state.get("is_outbound") and not state.get("incoming_message"):
        # NAO USA FALLBACK - lancha erro para retry
        raise SDRFallbackError(
            f"Outbound hook requires LLM generation for lead {memory.nome or memory.telefone}. "
            "Sistema NAO pode usar template fixo."
        )

    # Tentar LLM
    try:
        from agents.llm_direct import call_claude

        # === Sprint 12.9+: usar loader MD se FRALIB_SDR_PROMPTS_FROM_MD=1 ===
        stage_name = state.get("stage", "hook")
        md_stage = get_franz_stage_prompt(stage_name)
        if md_stage:
            stage_prompt = md_stage
        else:
            stage_prompt = build_stage_prompt(
                stage="hook",
                variant=variant,
                segmento=memory.segmento,
                rating=memory.rating,
            )

        user_prompt = build_user_prompt(
            stage="hook",
            incoming_message=state.get("incoming_message", ""),
            nome=memory.nome,
            cidade=memory.cidade,
            segmento=memory.segmento,
            rating=memory.rating,
        )

        # === Sprint 1.2 — Bug #1 fix: custom_knowledge injetado no system prompt ===
        # Antes: usava só ``get_persona_text(persona)`` + overlay + stage + rag.
        #        O bloco do tenant (custom_knowledge, personality, allowed/blocked
        #        actions, handoff, etc.) era montado por ``build_sdr_system_prompt``
        #        em services/sdr_settings.py mas nunca era chamado — ficava morto.
        # Agora: se o tenant passou ``sdr_settings`` no state (via admin/settings),
        #        passamos a base_prompt inteira (persona + overlay + stage + rag)
        #        pelo ``build_sdr_system_prompt`` para injetar o bloco do tenant
        #        (custom_knowledge + personality + handoff, capped em 3500 chars).
        #        Se não houver settings, mantém o comportamento nativo (back-compat).
        sdr_settings = state.get("sdr_settings") or {}
        if sdr_settings:
            try:
                from backend.services.sdr_settings import build_sdr_system_prompt

                # === Sprint 12.9+: usar loaders MD se FRALIB_SDR_PROMPTS_FROM_MD=1 ===
                # get_franz_persona() carrega FRANZ_PERSONA.md (fallback constante)
                persona_texto = get_franz_persona()
                base_for_tenant = (
                    persona_texto + "\n\n" +
                    agent_system_overlay(state.get("agent_context", {})) + "\n\n" +
                    stage_prompt + "\n\n" +
                    state.get("rag_context", "")
                )
                full_system = build_sdr_system_prompt(base_for_tenant, sdr_settings)
            except Exception as _tenant_err:
                print(f"[SDR] build_sdr_system_prompt falhou (nao-bloqueante): {_tenant_err}")
                full_system = (
                    get_franz_persona() + "\n\n" +
                    agent_system_overlay(state.get("agent_context", {})) + "\n\n" +
                    stage_prompt + "\n\n" +
                    state.get("rag_context", "")
                )
        else:
            full_system = (
                get_persona_text(state.get("persona", "consultivo")) + "\n\n" +
                agent_system_overlay(state.get("agent_context", {})) + "\n\n" +
                stage_prompt + "\n\n" +
                state.get("rag_context", "")
            )

        # === Sprint 3A: Tools dinâmicas SDR (opt-in via FRALIB_SDR_USE_TOOLS=1) ===
        # Pre-fetch das 3 read-only tools: playbook + similar conversations + lead quality.
        # Resultado injetado no full_system como secao extra. Backward-compat 100% se flag off.
        if os.getenv("FRALIB_SDR_USE_TOOLS", "0") == "1":
            try:
                from .tools_sdr import (
                    get_nicho_playbook,
                    retrieve_similar_conversations,
                    check_lead_quality,
                    format_similar_conversations_for_prompt,
                    format_lead_quality_for_prompt,
                )
                playbook = get_nicho_playbook(memory.segmento or "default")
                playbook_text = (
                    f"NICHO: {memory.segmento or 'default'}\n"
                    f"TOM: {playbook.get('tom_recomendado', 'consultivo')}\n"
                    f"PERGUNTAS OBRIGATORIAS: "
                    f"{', '.join(playbook.get('perguntas_obrigatorias', [])[:5])}\n"
                    f"GATILHOS CONVERSAO: "
                    f"{', '.join(playbook.get('gatilhos_conversao', [])[:5])}"
                )
                # === Sprint 3B: RAG semantico (opt-in via FRALIB_SDR_USE_RAG=1) ===
                # Substitui retrieve_similar_conversations (keyword/tail) por
                # search_similar_conversations (cosseno em embedding space).
                # Fallback automatico se RAG off ou indice vazio.
                if os.getenv("FRALIB_SDR_USE_RAG", "0") == "1":
                    try:
                        from .retrieval_semantico import (
                            search_similar_conversations,
                            format_search_results_for_prompt,
                            current_backend,
                        )
                        rag_results = search_similar_conversations(
                            user_id=memory.user_id,
                            nicho=memory.segmento or "default",
                            query=state.get("incoming_message", "")[:500],
                            top_k=3,
                            min_score=0.0,
                        )
                        similar_text = format_search_results_for_prompt(rag_results)
                        # Se RAG nao retornou nada, cai no tail (Sprint 3A)
                        if not similar_text:
                            similar_convs = retrieve_similar_conversations(
                                memory.segmento or "default",
                                user_id=memory.user_id,
                                top_k=3,
                            )
                            similar_text = format_similar_conversations_for_prompt(similar_convs)
                    except Exception as _rag_err:
                        print(f"[SDR] retrieval_semantico falhou, usando tail: {_rag_err}")
                        similar_convs = retrieve_similar_conversations(
                            memory.segmento or "default",
                            user_id=memory.user_id,
                            top_k=3,
                        )
                        similar_text = format_similar_conversations_for_prompt(similar_convs)
                else:
                    similar_convs = retrieve_similar_conversations(
                        memory.segmento or "default",
                        user_id=memory.user_id,
                        top_k=3,
                    )
                    similar_text = format_similar_conversations_for_prompt(similar_convs)
                lead_q = check_lead_quality(
                    user_id=memory.user_id,
                    telefone=memory.telefone or "",
                    lead_id=memory.lead_id or "",
                )
                lead_text = format_lead_quality_for_prompt(lead_q)
                # === Sprint 3C: Telemetria Variacao (opt-in via FRALIB_SDR_USE_TELEMETRIA=1) ===
                # Injeta ranking de templates por taxa de conversao (real do nicho).
                # Cold start: se < 3 conversas por template, retorna [] (sem ruido no prompt).
                telemetria_text = ""
                if os.getenv("FRALIB_SDR_USE_TELEMETRIA", "0") == "1":
                    try:
                        from .telemetria_variacao import (
                            rank_variacoes_by_conversion,
                            format_variacao_stats_for_prompt,
                        )
                        ranking = rank_variacoes_by_conversion(
                            user_id=memory.user_id,
                            nicho=memory.segmento or "default",
                            min_amostra=3,
                        )
                        telemetria_text = format_variacao_stats_for_prompt(ranking)
                    except Exception as _tel_err:
                        print(f"[SDR] telemetria_variacao falhou (nao-bloqueante): {_tel_err}")
                tools_extra = "\n\n".join(
                    x for x in [playbook_text, similar_text, lead_text, telemetria_text] if x
                )
                if tools_extra:
                    full_system = full_system + "\n\n" + tools_extra
            except Exception as _tools_err:
                print(f"[SDR] tools_sdr pre-fetch falhou (nao-bloqueante): {_tools_err}")

        # === Memory 3-tier (Feature #1 do roadmap 10/10) ===
        # Injeta top-10 core + top-3 warm via thread-local setada antes do LLM call.
        # O call_claude em llm_direct.py checa thread-local e injeta automaticamente
        # atraves de gerar_prompt_com_memoria.
        try:
            from .memory_hook import inject_memory_for_franz
            inject_memory_for_franz(memory, memory.segmento or "default")
        except Exception as _mem_err:
            print(f"[SDR] memory hook inject falhou (nao-bloqueante): {_mem_err}")

        try:
            response_text = _llm_with_retries_and_breaker("hook", lambda: call_claude(
                system=full_system,
                user=user_prompt,
                model="sonnet",  # ← SONNET (não Haiku)
                max_tokens=400,
                temperature=0.3,
                agent_name=state.get("selected_agent") or "franz",
                enable_context=False,
            ))

            # Parse JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                reply = data.get("reply", "")
                next_stage = data.get("next_stage", "qualify")
                update_facts = data.get("update_facts", {})
            else:
                reply = response_text.strip()
                next_stage = "qualify"
                update_facts = {}
        except SDRFallbackError:
            # Sprint 1.7: NUNCA usa template fixo. Marca pra humano.
            memory.needs_human_followup = True
            memory.last_failure_stage = "hook"
            try:
                from utils.safe_log import safe_log_silent_failure as _slf
                _slf(
                    Exception("hook SDRFallbackError"),
                    op="sdr_hook", lead_id=str(getattr(memory, "lead_id", "?")),
                    stage="hook",
                    extra={"reason": "LLM failed after retries"},
                )
            except Exception:
                pass
            return {
                "outgoing_message": "",
                "should_send": False,
                "memory": memory,
                "next_stage": memory.stage,
                "needs_human_followup": True,
            }
    except Exception as e:
        print(f"[SDR] hook LLM falhou: {e}")
        # NAO USA FALLBACK - lancar erro para retry
        raise SDRFallbackError(f"LLM hook failed: {e}") from e

    # === Sprint 3A: save_sdr_lesson (se turno significativo) ===
    # Persiste lesson quando: stage terminal (won/lost/opt_out) OU intent == objection_price
    # Multiplicador aplicado: converteu=+1.5x, nao converteu=0.3x
    if os.getenv("FRALIB_SDR_USE_TOOLS", "0") == "1":
        try:
            from .tools_sdr import save_sdr_lesson
            stage = memory.stage
            intent = (memory.last_intent or "").lower()
            should_save = (
                stage in ("won", "lost", "opt_out")
                or intent == "objection_price"
            )
            if should_save:
                converteu = stage == "won"
                lesson_text = (
                    f"lead {stage}: tom={memory.last_intent or 'n/a'}, "
                    f"turnos={memory.turn_count}"
                )
                save_sdr_lesson(
                    lesson=lesson_text,
                    score=0.7,
                    nicho=memory.segmento or "default",
                    user_id=memory.user_id,
                    lead_id=memory.lead_id or "",
                    converteu=converteu,
                )
                # === Sprint 3B: indexa conversa no RAG (para futuras buscas) ===
                # Constroi snippet a partir das ultimas mensagens do lead+bot.
                if os.getenv("FRALIB_SDR_USE_RAG", "0") == "1" and memory.lead_id:
                    try:
                        from .retrieval_semantico import index_conversation
                        snippet = (
                            f"lead: {state.get('incoming_message', '')[:200]}\n"
                            f"bot: {reply[:200]}"
                        )
                        index_conversation(
                            user_id=memory.user_id,
                            nicho=memory.segmento or "default",
                            lead_id=memory.lead_id,
                            text=snippet,
                            metadata={
                                "converteu": converteu,
                                "intent_final": memory.last_intent or "",
                                "stage": stage,
                                "tom_usado": memory.persona or "consultivo",
                            },
                        )
                    except Exception as _idx_err:
                        print(f"[SDR] index_conversation falhou (nao-bloqueante): {_idx_err}")
                # === Sprint 3C: telemetria variacao (rastreia qual template converteu) ===
                if os.getenv("FRALIB_SDR_USE_TELEMETRIA", "0") == "1" and memory.lead_id:
                    try:
                        from .telemetria_variacao import record_variacao_outcome
                        # template_id derivado de persona + segmento (heuristica simples)
                        template_id = f"v_{(memory.persona or 'consultivo').replace(' ', '_')}_{(memory.segmento or 'default').replace(' ', '_')}"
                        record_variacao_outcome(
                            user_id=memory.user_id,
                            nicho=memory.segmento or "default",
                            template_id=template_id,
                            converteu=converteu,
                            duracao_turnos=memory.turn_count or 0,
                            lead_id=memory.lead_id,
                            lead_score=0.0,  # TODO: cruzar com Caio quando disponivel
                            variacao_meta={
                                "intent_final": memory.last_intent or "",
                                "tom": memory.persona or "consultivo",
                            },
                        )
                    except Exception as _tel_err:
                        print(f"[SDR] record_variacao_outcome falhou (nao-bloqueante): {_tel_err}")
        except Exception as _save_err:
            print(f"[SDR] save_sdr_lesson falhou (nao-bloqueante): {_save_err}")

    # Validar
    contaminado = check_segment_contamination(reply, memory.segmento)
    if contaminado:
        raise SDRFallbackError(f"hook reply contaminated: {contaminado}")

    # === FSM + Intent orchestrator (substitui _next_stage legado) ===
    # BUG FIX: stage-loop quando lead só cumprimenta. Orchestrator classifica intent +
    # consulta FSM pra decidir proximo state/stage. Prioriza intent > stage.
    orch = _orchestrator_decide(
        memory=memory,
        incoming_message=state.get("incoming_message", ""),
        llm_suggested_stage=next_stage,
    )
    if orch.in_loop or orch.force_break_loop:
        print(f"[SDR] hook: orchestrator loop-break detected; state={orch.state_before.value}->{orch.state_after.value}")
    # Atualiza reply se orchestrator detectou loop mas reply é generico demais
    if orch.force_break_loop and len(reply.strip()) < 30:
        # Sprint 1.7: regenera via LLM (lead-specific). NAO usa template hardcoded.
        try:
            from agents.llm_direct import call_claude
            contexto = (
                "Lead travado em loop, precisa pergunta direta sobre decisor. "
                f"Segmento: {memory.segmento or 'nao informado'}. "
                f"Cidade: {memory.cidade or 'nao informada'}."
            )
            system = (
                "Voce e o Franz. Gere 1 frase perguntando diretamente se o lead e decisor. "
                "Tom natural WhatsApp, sem template fixo."
            )
            reply = _llm_with_retries_and_breaker("hook_loopbreak", lambda: call_claude(
                system=system,
                user=contexto,
                model="sonnet",
                max_tokens=120,
                temperature=0.3,
                agent_name="sdr_hook_loopbreak",
                enable_context=False,
            )).strip()
        except SDRFallbackError:
            # Sem LLM: silenciar (NAO mandar template). Marcar pra humano.
            memory.needs_human_followup = True
            memory.last_failure_stage = "hook_loopbreak"
            try:
                from utils.safe_log import safe_log_silent_failure as _slf
                _slf(
                    Exception("loopbreak SDRFallbackError"),
                    op="sdr_hook_loopbreak",
                    lead_id=str(getattr(memory, "lead_id", "?")),
                    stage="hook",
                    extra={"reason": "loop-break regeneration failed"},
                )
            except Exception:
                pass
            reply = ""

    memory.last_message_sent = reply
    if isinstance(update_facts, dict):
        save_agent_note(memory, state.get("selected_agent") or "abordagem", update_facts.get("agent_note"))
    memory.attempts += 1

    return {
        "outgoing_message": reply,
        "should_send": bool(reply and is_valid_length(reply)),
        "memory": memory,
    }


# ════════════════════════════════════════════════════════════════════
# NODE 5: node_qualify, node_pain, node_amplify, node_tease, etc
# ════════════════════════════════════════════════════════════════════

def make_stage_node(stage_name: str):
    """Factory para criar um node de stage genérico"""
    def node(state: SDRState) -> dict:
        memory = state.get("memory")
        if not memory:
            return {"outgoing_message": "", "should_send": False}

        incoming = state.get("incoming_message", "")
        persona = state.get("persona", "consultivo")

        # Tentar LLM
        try:
            from agents.llm_direct import call_claude

            # === Sprint 12.9+: usar loaders MD se FRALIB_SDR_PROMPTS_FROM_MD=1 ===
            persona_text = get_franz_persona()

            # Stage prompt para a persona (passa variant e variant_example)
            # Tenta MD primeiro (FRANZ_PLAYBOOK.md), fallback para constante
            md_stage = get_franz_stage_prompt(stage_name)
            if md_stage:
                stage_prompt = md_stage
            else:
                stage_prompt = build_stage_prompt(
                    stage=stage_name,
                    variant=state.get("variant", "A"),
                    segmento=memory.segmento,
                    rating=memory.rating,
                    site_url=memory.site_url,
                    top_concorrentes=memory.top_concorrentes,
                    persona=persona,
                    cidade=memory.cidade,
                    nome=memory.nome,
                )

            # History
            history = state.get("history", [])

            user_prompt = build_user_prompt(
                stage=stage_name,
                incoming_message=incoming,
                nome=memory.nome,
                cidade=memory.cidade,
                segmento=memory.segmento,
                rating=memory.rating,
                history=history,
                memory_facts={
                    "nome_contato": memory.nome_contato,
                    "is_decisor": memory.is_decisor,
                    "pain_identified": memory.pain_identified,
                    "site_revealed": memory.site_revealed,
                    "price_tier": memory.price_tier,
                },
            )

            # System completo: persona + stage prompt + rag
            full_system = (
                persona_text + "\n\n" +
                agent_system_overlay(state.get("agent_context", {})) + "\n\n" +
                stage_prompt + "\n\n" +
                state.get("rag_context", "")
            )

            response_text = _llm_with_retries_and_breaker(stage_name, lambda: call_claude(
                system=full_system,
                user=user_prompt,
                model="sonnet",
                max_tokens=500,
                temperature=0.3,
                agent_name=state.get("selected_agent") or "franz",
                enable_context=False,
            ))

            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                reply = data.get("reply", "")
                next_stage = data.get("next_stage", stage_name)
                update_facts = data.get("update_facts", {})
            else:
                reply = response_text.strip()[:300]
                next_stage = stage_name
                update_facts = {}
        except SDRFallbackError:
            # Sprint 1.7: marca pra humano, NAO envia nada
            memory.needs_human_followup = True
            memory.last_failure_stage = stage_name
            try:
                from utils.safe_log import safe_log_silent_failure as _slf
                _slf(
                    Exception(f"{stage_name} SDRFallbackError"),
                    op=f"sdr_stage_{stage_name}",
                    lead_id=str(getattr(memory, "lead_id", "?")),
                    stage=stage_name,
                    extra={"reason": "LLM failed after retries"},
                )
            except Exception:
                pass
            return {
                "outgoing_message": "",
                "should_send": False,
                "memory": memory,
                "next_stage": memory.stage,
                "needs_human_followup": True,
            }
        except Exception as e:
            print(f"[SDR] {stage_name} LLM falhou: {e}")
            # NAO USA FALLBACK - lancar erro para retry
            raise SDRFallbackError(f"LLM {stage_name} failed: {e}") from e

        # Validar
        if not is_valid_length(reply) or not has_one_question(reply):
            # Truncar ou corrigir
            if not is_valid_length(reply):
                linhas = reply.split("\n")[:3]
                reply = "\n".join(linhas)
            if not has_one_question(reply):
                # Manter só até a primeira pergunta
                idx = reply.find("?")
                if idx > 0:
                    reply = reply[:idx+1]

        # Contaminação
        contaminado = check_segment_contamination(reply, memory.segmento)
        if contaminado:
            raise SDRFallbackError(f"{stage_name} reply contaminated: {contaminado}")

        # Atualizar memory
        previous_stage = memory.stage
        memory.last_message_received = incoming
        if update_facts:
            for k, v in update_facts.items():
                if hasattr(memory, k) and v:
                    setattr(memory, k, v)
            save_agent_note(memory, state.get("selected_agent") or stage_name, update_facts.get("agent_note"))

        # Avançar stage apenas quando o modelo sugerir transição válida.
        # Inbound deve responder ao que foi perguntado, sem empurrar script.
        # === FSM + Intent orchestrator (substitui _next_stage legado) ===
        orch = _orchestrator_decide(
            memory=memory,
            incoming_message=incoming,
            llm_suggested_stage=next_stage,
        )
        if orch.state_after.value == "opt_out" and orch.intent.value == "opt_out":
            next_stage = "lost"
        elif orch.stage_after in STAGE_PROGRESSION:
            next_stage = orch.stage_after
        else:
            next_stage = _next_stage(memory.stage, next_stage, stage_name)
        if next_stage in STAGE_PROGRESSION:
            memory.update_stage(next_stage)
        elif next_stage:
            memory.stage = next_stage

        memory.last_message_sent = reply
        try:
            evaluation = evaluate_bot_turn(
                user_id=memory.user_id,
                lead_id=memory.lead_id,
                agent=state.get("selected_agent") or stage_name,
                reply=reply,
                previous_stage=previous_stage,
                next_stage=memory.stage,
                history=state.get("history") or [],
            )
            if evaluation.get("issues"):
                save_agent_note(
                    memory,
                    "supervisor",
                    f"Quality evaluator flagged: {', '.join(evaluation['issues'])}",
                )
        except Exception as learning_err:
            print(f"[SDR] learning evaluator failed: {learning_err}")
        if not (getattr(memory, "agent_notes", {}) or {}).get(state.get("selected_agent") or stage_name):
            save_agent_note(
                memory,
                state.get("selected_agent") or stage_name,
                f"Atuou no stage {stage_name}; ultima pergunta enviada: {reply[:180]}",
            )
        memory.attempts += 1

        return {
            "outgoing_message": reply,
            "should_send": bool(reply),
            "memory": memory,
            "next_stage": next_stage,
        }

    return node


# ════════════════════════════════════════════════════════════════════
# NODES ESPECIAIS: opt_out, gatekeeper, schedule, is_decisor
# ════════════════════════════════════════════════════════════════════

@sdr_traced("node_opt_out")
def node_opt_out(state: SDRState) -> dict:
    """Lead pediu pra parar.

    REGRA SIMPLES: NUNCA marcar opt_out direto. Sempre perguntar confirmacao.

    O LLM (Sonnet) ja e capaz de interpretar a intencao. Quando ele classifica
    como opt_out, a gente so pergunta confirmacao uma vez. Se lead disser
    'sim', marca opt_out. Caso contrario, volta pro funil.

    Essa logica NAO precisa de stage awareness porque:
    1. Se o Franz ta perguntando, lead ja demonstrou intencao de sair.
    2. Mesmo em hook, se lead disser 'sim', confirma.
    3. Se lead disser 'nao' ou 'continua', volta pro funil.
    4. Liberdade maxima pro LLM interpretar nuances.

    Bug fix: Carolina Ragugnetti 2026-06-25.
    """
    import re
    memory = state.get("memory")
    if not memory:
        return {}

    incoming = (state.get("incoming_message") or "").strip().lower()

    # STEP 2: ja perguntou antes, lead respondeu agora
    if memory.opt_out_pending:
        # Detectar confirmação positiva
        confirmou = bool(re.search(r"\b(sim|yes|quero|parar|stop|pode|para|cancela|tira)\b", incoming))
        # Detectar negação (lead quer continuar)
        cancelou = bool(re.search(r"\b(nao|não|no|continua|seguir|continuar|fica|nao\s+para|não\s+para)\b", incoming))

        if confirmou and not cancelou:
            memory.confirm_opt_out_from_pending()
            reply = "Entendido! Vou remover seu contato agora. Se mudar de ideia no futuro, pode chamar 👍"
            save_agent_note(memory, "supervisor", "Lead CONFIRMOU opt-out; encerrado.")
            return {
                "outgoing_message": reply,
                "should_send": True,
                "memory": memory,
                "next_stage": "opt_out",
            }
        elif cancelou:
            memory.cancel_opt_out_pending()
            save_agent_note(memory, "supervisor", "Lead cancelou opt-out pendente; volta pro funil.")
            # Pergunta aberta - deixa LLM responder com contexto
            return {
                "outgoing_message": "",  # vazio = deixa o LLM gerar resposta natural
                "should_send": False,
                "memory": memory,
                "next_stage": memory.stage or "qualify",
            }
        else:
            # Resposta ambigua - re-pergunta
            memory.request_opt_out_confirmation()
            reply = (
                "So pra eu entender direito: voce quer que eu PARE de mandar mensagens? "
                "Responde 'sim' se quiser parar, ou 'continua' se quiser seguir a conversa."
            )
            return {
                "outgoing_message": reply,
                "should_send": True,
                "memory": memory,
                "next_stage": "opt_out_pending",
            }

    # STEP 1: primeira vez - PERGUNTA confirmação (qualquer stage)
    memory.request_opt_out_confirmation()
    reply = (
        "Entendi. Pra eu ter certeza: voce quer que eu pare de mandar mensagens? "
        "Responde 'sim' pra parar, ou 'continua' pra seguir conversando."
    )
    save_agent_note(memory, "supervisor", "Franz perguntou confirmacao opt-out.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": "opt_out_pending",
    }


@sdr_traced("node_is_decisor")
def node_is_decisor(state: SDRState) -> dict:
    """Lead confirmou que é decisor - gerar resposta via LLM (NAO usa fallback)"""
    memory = state.get("memory")
    if not memory:
        return {}

    memory.is_decisor = True
    memory.gatekeeper_level = 0
    incoming = memory.last_message_received or state.get("incoming_message", "")

    # Gerar resposta via LLM - NAO usa template fixo
    try:
        from agents.llm_direct import call_claude
        contexto = f"Lead confirmou ser decisor. Respondeu: '{incoming}'"
        if memory.nome:
            contexto += f" | Negocio: {memory.nome}"
        if memory.segmento:
            contexto += f" | Segmento: {memory.segmento}"

        system = (
            "Voce e o Franz. Lead confirmou que e o decisor. "
            "Gere resposta curta (max 2 linhas) perguntando sobre o negocio.\n"
            "REGRAS: max 2 frases, 1 pergunta, tom consultivo."
        )
        reply = _llm_with_retries_and_breaker("is_decisor", lambda: call_claude(
            system=system,
            user=contexto,
            model="sonnet",
            max_tokens=100,
            temperature=0.3,
            agent_name="sdr_is_decisor",
            enable_context=False,
        )).strip()
    except SDRFallbackError:
        memory.needs_human_followup = True
        memory.last_failure_stage = "is_decisor"
        try:
            from utils.safe_log import safe_log_silent_failure as _slf
            _slf(
                Exception("is_decisor SDRFallbackError"),
                op="sdr_is_decisor",
                lead_id=str(getattr(memory, "lead_id", "?")),
                stage="is_decisor",
                extra={"reason": "LLM failed after retries"},
            )
        except Exception:
            pass
        return {
            "outgoing_message": "",
            "should_send": False,
            "memory": memory,
            "next_stage": memory.stage,
            "needs_human_followup": True,
        }
    except Exception as e:
        raise SDRFallbackError(f"Failed to generate decisor response: {e}") from e

    memory.last_message_sent = reply
    memory.update_stage("qualify")
    save_agent_note(memory, state.get("selected_agent") or "qualificacao", "Lead confirmou ser decisor; pode qualificar dor e canal de captacao.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": memory.stage,
    }


@sdr_traced("node_schedule")
def node_schedule(state: SDRState) -> dict:
    """Lead quer agendar"""
    memory = state.get("memory")
    if not memory:
        return {}

    incoming = state.get("incoming_message", "")
    from datetime import datetime, timedelta
    target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Tentar extrair dia/hora
    import re
    time_match = re.search(r"\b(\d{1,2})\s*[h:](\d{0,2})", incoming)
    time_label = ""
    if time_match:
        h = int(time_match.group(1))
        m = time_match.group(2) or "00"
        time_label = f" às {h:02d}h{m}"

    if "amanhã" in incoming.lower():
        label = "amanhã"
    elif "segunda" in incoming.lower():
        label = "segunda"
    else:
        label = "amanhã"

    # Sprint 1.7: gerar reply via LLM (lead-specific). SEM template hardcoded.
    try:
        from agents.llm_direct import call_claude
        contexto = (
            f"Lead quer agendar. Mensagem dele: '{incoming}'. "
            f"Sugerir label: {label}{time_label}. "
            f"Responde confirmando com tom natural do Franz."
        )
        if memory.nome:
            contexto += f" Lead: {memory.nome}."
        if memory.segmento:
            contexto += f" Segmento: {memory.segmento}."
        system = (
            "Voce e o Franz. Confirme o agendamento em 1 frase usando o label sugerido. "
            "Tom: natural, WhatsApp, sem parecer template."
        )
        reply = _llm_with_retries_and_breaker("schedule", lambda: call_claude(
            system=system,
            user=contexto,
            model="sonnet",
            max_tokens=80,
            temperature=0.3,
            agent_name="sdr_schedule",
            enable_context=False,
        )).strip()
    except SDRFallbackError:
        memory.needs_human_followup = True
        memory.last_failure_stage = "schedule"
        try:
            from utils.safe_log import safe_log_silent_failure as _slf
            _slf(
                Exception("schedule SDRFallbackError"),
                op="sdr_schedule",
                lead_id=str(getattr(memory, "lead_id", "?")),
                stage="schedule",
                extra={"reason": "LLM failed after retries"},
            )
        except Exception:
            pass
        return {
            "outgoing_message": "",
            "should_send": False,
            "memory": memory,
            "next_stage": memory.stage,
            "needs_human_followup": True,
        }

    memory.stage = "scheduled"
    memory.followup_date = target_date
    memory.last_message_received = incoming
    memory.last_message_sent = reply
    save_agent_note(memory, state.get("selected_agent") or "followup", f"Retomar {label}{time_label}; respeitar agendamento.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": "scheduled",
    }


# ════════════════════════════════════════════════════════════════════
# NODES DE GATEKEEPER (5 níveis)
# ════════════════════════════════════════════════════════════════════

@sdr_traced("node_gatekeeper")
def node_gatekeeper(state: SDRState) -> dict:
    """Navega gatekeeper com 5 níveis de insistência"""
    memory = state.get("memory")
    if not memory:
        return {}

    incoming = state.get("incoming_message", "")
    text = (incoming or "").lower()

    is_absent = bool(re.search(r"(n[aã]o|nao).{0,18}(est[aá]|t[aá]|se encontra|veio)|fora|saiu|ausente", text))

    level = min(memory.gatekeeper_level + 1, 5)
    subject = "alunos novos" if "academia" in memory.segmento.lower() else "clientes novos"

    if level == 1 and not is_absent:
        reply = f"Tranquilo. Consegue me passar pra ele? É coisa de 2 min sobre como a {memory.nome} capta {subject}."
    elif level <= 2:
        reply = f"Tranquilo, sem problema. Qual horário costuma ser melhor pra falar com ele sobre captar {subject} na {memory.nome}?"
    elif level == 3:
        reply = f"Entendi. Posso te mandar uma ideia curta pra você mostrar pra ele sobre captar {subject}?"
    elif level == 4:
        reply = "Beleza. Ele tem um WhatsApp direto que eu possa chamar sem te atrapalhar?"
    else:
        reply = "Combinado. Qual dia e horário você acha melhor eu tentar de novo?"

    memory.gatekeeper_level = level
    memory.is_decisor = False
    memory.last_message_sent = reply
    save_agent_note(memory, state.get("selected_agent") or "qualificacao", f"Gatekeeper nivel {level}; decisor ainda nao confirmado.")
    memory.attempts += 1

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": "gatekeeper",
    }


# ════════════════════════════════════════════════════════════════════
# NODE FINAL: save_and_send
# ════════════════════════════════════════════════════════════════════

@sdr_traced("node_save_and_send")
def node_save_and_send(state: SDRState) -> dict:
    """Salva memória e marca como pronto para enviar"""
    memory = state.get("memory")
    if not memory:
        return {}

    if not state.get("should_send", False):
        return {}

    # === Site Offer proativo (Feature: oferecer site pronto) ===
    # Antes de qualquer envio, verifica se deve oferecer o site pronto.
    # Adiciona a oferta ANTES da reply se ainda nao foi oferecida 2x.
    reply = (
        state.get("proposed_reply", "")
        or state.get("draft", "")
        or state.get("outgoing_message", "")
    )
    if reply:
        try:
            from .site_offer import should_offer_site, offer_proactive, increment_offer_count
            incoming = state.get("incoming_message", "") or ""
            detected_intent = state.get("detected_intent", "") or ""
            turn_count = getattr(memory, "turn_count", 0) or 0
            if should_offer_site(memory, intent=detected_intent, turn_count=turn_count):
                # Detectar tipo de objecao (se for objection)
                offer_text = offer_proactive(memory, segmento=memory.segmento or "")
                if offer_text and not _reply_already_has_offer(reply):
                    # Prepend a oferta (separada por quebra de linha)
                    reply = f"{offer_text}\n\n---\n\n{reply}"
                    increment_offer_count(memory)
                    state["site_offer_injected"] = True
        except Exception as _so_err:
            print(f"[SDR] site_offer falhou (nao-bloqueante): {_so_err}")

    # === Simplificacao de linguagem (tom didatico) ===
    # Reescreve jargoes com linguagem simples, como se fosse pra crianca de 10 anos.
    if reply:
        try:
            reply = _simplify_language(reply)
        except Exception as _sl_err:
            print(f"[SDR] simplify_language falhou: {_sl_err}")

    # === LLM-as-judge quality gate (Feature 2 do roadmap 10/10) ===
    # Avalia a resposta antes de enviar. Bloqueia se score < 3.
    # PULA para intents óbvios: greeting, acknowledgment, opt_out
    if reply:
        try:
            # Detectar intent para pular judge em casos obvios
            detected_intent = state.get("detected_intent", "") or ""
            skip_judge = detected_intent.lower() in ("greeting", "acknowledgment", "opt_out")
            if skip_judge:
                # Para intents óbvios, usa score alto automático
                quality_score = 5
                quality_issues = []
                quality_should_send = True
            else:
                from .quality_judge import evaluate_reply
                incoming = state.get("incoming_message", "")
                stage = state.get("current_stage") or memory.stage or "hook"
                segmento = memory.segmento or ""
                quality = evaluate_reply(
                    incoming=incoming,
                    reply=reply,
                    stage=stage,
                    segmento=segmento,
                    min_score_to_send=3,
                    enable_llm=True,
                )
                quality_score = quality.score
                quality_issues = quality.issues
                quality_should_send = quality.should_send

            # Persistir score na LeadMemory
            if not hasattr(memory, "last_quality_score") or memory.last_quality_score is None:
                memory.last_quality_score = 0
            memory.last_quality_score = quality_score
            memory.last_quality_issues = quality_issues
            # Logar
            from .turn_tracing import get_active_trace
            trace = get_active_trace(str(state.get("lead_id") or memory.telefone or ""))
            if trace:
                span = trace.start_span("quality_judge", modelo="skip" if skip_judge else "haiku", score=quality_score)
                trace.end_span(span, status="completed", score=quality_score, should_send=quality_should_send)
            # Bloquear envio se score < 3
            if not quality_should_send:
                print(f"[SDR] JUDGE BLOQUEOU ENVIO: score={quality_score}, issues={quality_issues}")
                print(f"[SDR] Reply rejeitada: {reply[:100]}")
                return {}  # nao envia
        except Exception as _judge_err:
            # Sprint 1.3: silent failure → logger.warning estruturado
            from utils.safe_log import safe_log_silent_failure
            safe_log_silent_failure(
                _judge_err,
                op="quality_judge",
                lead_id=state.lead_id if hasattr(state, "lead_id") else None,
            )

    # Persiste o trace do turno SDR (todos os nodes ja instrumentaram spans)
    try:
        from .turn_tracing import end_turn_trace
        lead_id = str(state.get("lead_id") or memory.telefone or "unknown")
        end_turn_trace(lead_id)
    except Exception as _trace_end_err:
        print(f"[SDR] end_turn_trace falhou: {_trace_end_err}")

    # === Sprint 1.5 — auditoria de turnos (sdr_turns) ===
    # Grava cada turno processado em sdr_turns para auditoria
    # (stage_before -> stage_after, intent, confidence, latency, custo).
    # Falha transparente: NAO bloqueia o envio se o insert falhar.
    if reply and state.get("should_send", False):
        try:
            record_sdr_turn(
                lead_id=str(state.get("lead_id") or memory.lead_id or ""),
                tenant_id=int(state.get("tenant_id") or memory.user_id or 0),
                stage_before=str(state.get("stage_before") or ""),
                stage_after=str(
                    state.get("stage_after")
                    or getattr(memory, "stage", "")
                    or ""
                ),
                intent=str(state.get("detected_intent") or ""),
                confidence=_safe_float(state.get("confidence"), default=None),
                latency_ms=_safe_int(state.get("latency_ms")),
                llm_cost_usd=_safe_float(state.get("llm_cost_usd"), default=None),
            )
        except Exception as _turn_err:
            print(f"[SDR] record_sdr_turn falhou (no-bloqueante): {_turn_err}")

    # ════════════════════════════════════════════════════════════════
    # HUMANIZACAO (Fase 1 - SDD §1.4)
    # - Calcula delay humano variavel
    # - Detecta duplicatas (anti-repete-msgs)
    # - Detecta msg parece-robo
    # - Aplica Wall Street close se hesitou
    # ════════════════════════════════════════════════════════════════
    reply = (
        state.get("proposed_reply", "")
        or state.get("draft", "")
        or state.get("outgoing_message", "")
    )
    if reply:
        try:
            from agents.sdr_langgraph.humanization import (
                calc_humanize_delay,
                detect_msg_duplicate,
                is_robot_like,
                msg_hash,
                pick_wall_street_close,
            )
            from agents.sdr_langgraph.state import LeadMemory as _LM

            # 1. Detecta msg parece-robo
            if is_robot_like(reply):
                print(f"[SDR-HUMANIZE] Mensagem parece-robo detectada: {reply[:80]}")
                # Log pra revisar prompt depois

            # 2. Detecta msg duplicada
            previous_msgs = list(memory.agent_notes.get("last_msgs_sent", []))
            if detect_msg_duplicate(reply, previous_msgs):
                # Substitui por variacao
                reply = reply + " Me conta, faz sentido?"
                print(f"[SDR-HUMANIZE] Msg duplicada detectada, variacao adicionada")

            # 3. Wall Street close automatico (se hesitou e ainda nao usou)
            stage = memory.stage
            has_hesitated = memory.rejection_count > 0 or "vou pensar" in reply.lower() or "agora nao" in reply.lower()
            if has_hesitated and not memory.wall_street_close_used and stage in ("close", "feedback", "reveal"):
                wall_street = pick_wall_street_close(memory.segmento)
                reply = reply + "\n\n" + wall_street
                memory.wall_street_close_used = True

            # 4. Calcula delay humano
            is_objetou = memory.rejection_count > 0 or memory.main_objection
            is_first = memory.msgs_sent_count == 0
            is_quente = memory.lead_temperature == "quente"
            delay = calc_humanize_delay(
                last_response_time_min=memory.humanization_profile.get("avg_response_time_min"),
                is_objetou=is_objetou,
                is_first_msg=is_first,
                is_quente=is_quente,
            )
            print(f"[SDR-HUMANIZE] delay={delay.seconds:.1f}s reason={delay.reason}")

            # 5. Atualiza contadores e dedup hash
            memory.msgs_sent_count += 1
            memory.last_msg_sent_hash = msg_hash(reply)
            previous_msgs.append(reply)
            memory.agent_notes["last_msgs_sent"] = previous_msgs[-5:]

            # Re-inject no state pra envio
            state["proposed_reply"] = reply
            state["outgoing_message"] = reply
            state["send_delay_seconds"] = delay.seconds
        except Exception as e:
            print(f"[SDR-HUMANIZE] Erro humanizacao (nao-fatal): {e}")

    # Salvar memória
    try:
        from agents.memory import salvar_memoria
        session_id = f"franz_lead_{memory.telefone}"
        salvar_memoria(
            session_id,
            memory.model_dump(),
            user_id=memory.user_id,
        )
    except Exception as e:
        print(f"[SDR] Erro ao salvar memória: {e}")

    # === Sprint 1.4 — hook record_outcome (terminal stage) ===
    # Se o stage final for 'ganho' ou 'perdido', grava 1 linha em
    # lead_outcomes. Falha transparente: nunca quebra o envio.
    try:
        final_stage = (
            state.get("stage_after")
            or getattr(memory, "stage", "")
            or ""
        )
        if str(final_stage).strip().lower() in {"ganho", "perdido", "won", "lost"}:
            _handle_terminal_stage(
                memory=memory,
                state=state,
                stage_after=str(final_stage),
            )
    except Exception as _hook_err:
        print(f"[SDR] _handle_terminal_stage no-op: {_hook_err}")

    return {}


# ════════════════════════════════════════════════════════════════════
# CONSTRUÇÃO DO GRAFO
# ════════════════════════════════════════════════════════════════════

def build_sdr_graph() -> Any:
    """Constrói o grafo SDR"""
    if StateGraph is None:
        raise SDRFallbackError(
            f"LangGraph indisponivel ou incompativel: {_LANGGRAPH_IMPORT_ERROR}"
        )

    workflow = StateGraph(SDRState)

    # Nodes de carregamento
    workflow.add_node("load_context", node_load_context)
    workflow.add_node("check_schedule", node_check_schedule)
    workflow.add_node("save_and_send", node_save_and_send)

    # Nodes especiais
    workflow.add_node("node_opt_out", node_opt_out)
    workflow.add_node("node_gatekeeper", node_gatekeeper)
    workflow.add_node("node_schedule", node_schedule)
    workflow.add_node("node_is_decisor", node_is_decisor)
    workflow.add_node("node_greeting", node_greeting)

    # Nodes de stage
    for stage_name in [
        "hook", "qualify", "pain", "amplify", "tease",
        "proof", "reveal", "feedback", "close",
        "followup_24h", "followup_72h"
    ]:
        workflow.add_node(f"node_{stage_name}", make_stage_node(stage_name))

    # Edges
    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "check_schedule")

    # Após check_schedule, vai para roteamento por intent
    workflow.add_conditional_edges(
        "check_schedule",
        route_after_schedule,
        {
            "save_and_send": "save_and_send",
            "node_opt_out": "node_opt_out",
            "node_gatekeeper": "node_gatekeeper",
            "node_schedule": "node_schedule",
            "node_is_decisor": "node_is_decisor",
            "node_greeting": "node_greeting",
            "node_hook": "node_hook",
            "node_qualify": "node_qualify",
            "node_pain": "node_pain",
            "node_amplify": "node_amplify",
            "node_tease": "node_tease",
            "node_proof": "node_proof",
            "node_reveal": "node_reveal",
            "node_feedback": "node_feedback",
            "node_close": "node_close",
            "node_followup_24h": "node_followup_24h",
            "node_followup_72h": "node_followup_72h",
        }
    )

    # Todos os nodes de stage vão para save_and_send
    for stage_name in [
        "hook", "qualify", "pain", "amplify", "tease",
        "proof", "reveal", "feedback", "close",
        "followup_24h", "followup_72h", "opt_out",
        "gatekeeper", "schedule", "is_decisor", "greeting"
    ]:
        workflow.add_edge(f"node_{stage_name}", "save_and_send")

    workflow.add_edge("save_and_send", END)

    return workflow


# ════════════════════════════════════════════════════════════════════
# SDR GRAPH CLASS - Entry point
# ════════════════════════════════════════════════════════════════════

class SDRGraph:
    """Wrapper do grafo para fácil invocação"""

    def __init__(self):
        self.graph = build_sdr_graph().compile()

    def invoke(self, state: dict) -> dict:
        """Executa o grafo"""
        return self.graph.invoke(state)


_singleton: SDRGraph = None


def get_sdr_graph() -> SDRGraph:
    global _singleton
    if _singleton is None:
        _singleton = SDRGraph()
    return _singleton


# ══════════════════════════════════════════════════════════════════════════
# Sprint 1.5 — helpers de auditoria de turnos
# ══════════════════════════════════════════════════════════════════════════

def _safe_float(value: Any, default: float | None = 0.0) -> float | None:
    """Converte para float seguro (None → default)."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any) -> int | None:
    """Converte para int seguro (None → None)."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1.4 — hook record_outcome (terminal stage)
# ═══════════════════════════════════════════════════════════════════════════════

def _record_lead_outcome(
    lead_id: str | int,
    tenant_id: int,
    nicho: str | None,
    horario_contato: str | None,
    abordagem_usada: str | None,
    site_template_usado: str | None,
    kanban_stage_final: str,
    dias_ate_fechamento: int | None = None,
) -> int | None:
    """Hook do Sprint 1.4 — chama ``record_outcome`` quando lead termina.

    Falha transparente: nunca levanta exceção para o grafo.
    """
    try:
        from backend.services.lead_outcomes_service import record_outcome
        return record_outcome(
            lead_id=lead_id,
            tenant_id=tenant_id,
            nicho=nicho,
            horario_contato=horario_contato,
            abordagem_usada=abordagem_usada,
            site_template_usado=site_template_usado,
            kanban_stage_final=kanban_stage_final,
            dias_ate_fechamento=dias_ate_fechamento,
        )
    except Exception as _ro_err:
        print(f"[SDR] _record_lead_outcome no-op: {_ro_err}")
        return None


def _handle_terminal_stage(
    memory,
    state: "SDRState | dict",
    stage_after: str | None = None,
) -> int | None:
    """Sprint 1.4 — se stage_after é terminal (ganho/perdido), chama record_outcome.

    Idempotência: usa o próprio lead_id + stage como ``idempotency_key``,
    então ``record_outcome`` pode ser chamado 2x sem duplicar.
    """
    terminal = (stage_after or "").strip().lower()
    if terminal not in {"ganho", "perdido", "won", "lost"}:
        return None
    kanban = "ganho" if terminal in {"ganho", "won"} else "perdido"
    lead_id = getattr(memory, "lead_id", None) or state.get("lead_id") if hasattr(state, "get") else None
    tenant_id = getattr(memory, "user_id", None) or (state.get("user_id") if hasattr(state, "get") else None)
    nicho = getattr(memory, "segmento", None)
    abordagem = getattr(memory, "persona", None)
    template = getattr(memory, "variant", None) or state.get("variant") if hasattr(state, "get") else None
    try:
        from datetime import datetime as _dt
        last_sent = getattr(memory, "last_message_sent", None)
        horario = None
        if last_sent:
            try:
                horario = _dt.now().strftime("%H:%M")
            except Exception:
                horario = None
        return _record_lead_outcome(
            lead_id=lead_id,
            tenant_id=tenant_id,
            nicho=nicho,
            horario_contato=horario,
            abordagem_usada=abordagem,
            site_template_usado=template,
            kanban_stage_final=kanban,
            dias_ate_fechamento=None,
        )
    except Exception as _e:
        print(f"[SDR] _handle_terminal_stage no-op: {_e}")
        return None


def record_outcome(  # noqa: F811 - alias para tests
    lead_id,
    tenant_id,
    nicho=None,
    horario_contato=None,
    abordagem_usada=None,
    site_template_usado=None,
    kanban_stage_final=None,
    dias_ate_fechamento=None,
    **kwargs,
):
    """Alias publico usado por tests."""
    return _record_lead_outcome(
        lead_id=lead_id,
        tenant_id=tenant_id,
        nicho=nicho,
        horario_contato=horario_contato,
        abordagem_usada=abordagem_usada,
        site_template_usado=site_template_usado,
        kanban_stage_final=kanban_stage_final or "",
        dias_ate_fechamento=dias_ate_fechamento,
    )


# Alias legacy usado por testes (mantido nome curto)
_handle_terminal_stage_alias = _handle_terminal_stage


def record_sdr_turn(
    lead_id: str,
    tenant_id: int,
    stage_before: str = "",
    stage_after: str = "",
    intent: str = "",
    confidence: float | None = None,
    latency_ms: int | None = None,
    llm_cost_usd: float | None = None,
) -> int | None:
    """Insere 1 linha em ``sdr_turns`` para auditoria de turnos do SDR.

    Args:
        lead_id: id do lead (string — alguns sistemas usam UUIDs).
        tenant_id: id do tenant (int).
        stage_before: stage anterior (string).
        stage_after: stage novo (string).
        intent: intent classificado (string).
        confidence: score 0.00-1.00 (float).
        latency_ms: latência do turno em ms (int).
        llm_cost_usd: custo do LLM em USD (float).

    Returns:
        ID inserido ou None se a tabela nao existe / erro.

    Comportamento fail-safe:
        - Sem ``DATABASE_URL`` → no-op (testes).
        - Sem engine no contexto → no-op silencioso.
        - Tabela ausente → no-op silencioso (NAO quebra o agente).
    """
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return None
    if not lead_id or not tenant_id:
        return None
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url, pool_pre_ping=False)
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    INSERT INTO sdr_turns (
                        lead_id, tenant_id, stage_before, stage_after,
                        intent, confidence, latency_ms, llm_cost_usd
                    ) VALUES (
                        :lid, :tid, :sb, :sa, :intent, :conf, :lat, :cost
                    )
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "lid": lead_id,
                    "tid": tenant_id,
                    "sb": (stage_before or "")[:40],
                    "sa": (stage_after or "")[:40],
                    "intent": (intent or "")[:40],
                    "conf": confidence if confidence is not None else None,
                    "lat": latency_ms,
                    "cost": llm_cost_usd if llm_cost_usd is not None else None,
                },
            ).fetchone()
            conn.commit()
        if row:
            try:
                return int(row[0])
            except Exception:
                return None
        return None
    except Exception as exc:
        # NAO quebra o agente se a tabela nao existir.
        print(f"[SDR] record_sdr_turn no-op (tabela ausente?): {exc}")
        return None
