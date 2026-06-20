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

from langgraph.graph import StateGraph, END

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
from .prompts import (
    build_stage_prompt,
    build_user_prompt,
    should_use_lobo,
    get_persona_text,
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


def _segment_subject(segmento: str) -> str:
    segment = (segmento or "").lower()
    if any(term in segment for term in ("academia", "fitness", "gym", "crossfit", "pilates")):
        return "alunos novos"
    if any(term in segment for term in ("clinica", "clínica", "odont", "estetica", "estética")):
        return "pacientes novos"
    return "clientes novos"


def _mentions_price_or_payment(incoming: str) -> bool:
    text = (incoming or "").lower()
    return any(
        term in text
        for term in (
            "preco", "preço", "valor", "quanto custa", "custa quanto",
            "pagamento", "parcela", "parcelado", "pix", "cartao", "cartão",
        )
    )


def _mentions_link_or_site(incoming: str) -> bool:
    text = (incoming or "").lower()
    return any(term in text for term in ("site", "link", "pagina", "página", "ver", "manda"))


def _commercial_fallback(memory: LeadMemory, stage: str, incoming: str = "") -> tuple[str, str] | None:
    if _mentions_link_or_site(incoming) and memory.site_url:
        return (
            f"Claro. A prévia que montei pra {memory.nome or 'vocês'} está aqui: {memory.site_url}\n"
            "Dá pra ajustar cores, fotos e textos. O que você mudaria primeiro?",
            "feedback",
        )

    if _mentions_price_or_payment(incoming) or stage == "close":
        if stage == "followup_72h":
            return (
                "Pra ser bem direto: o projeto completo é R$ 1.499 em até 12x.\n"
                "Como última tentativa, dá pra avaliar um início mais simples por R$ 999 no Pix. Faz sentido pra você?",
                "close",
            )
        if stage == "followup_24h":
            return (
                "O projeto completo fica R$ 1.499 em até 12x, só depois de aprovado.\n"
                "Se o valor era o ponto, consigo tentar uma condição de follow-up por R$ 1.299. Quer que eu veja isso?",
                "close",
            )
        return (
            "O projeto completo fica R$ 1.499 em até 12x, e vocês só pagam depois de aprovar tudo.\n"
            "Se preferir Pix, eu chamo uma pessoa pra confirmar a melhor condição. Faz sentido seguir?",
            "close",
        )

    return None


def _fallback_reply(stage: str, memory: LeadMemory, incoming: str = "") -> tuple[str, str]:
    """Fallback contextual quando o LLM/proxy falha."""
    nome = memory.nome or "o negócio"
    segmento = memory.segmento or "atendimento"
    subject = _segment_subject(segmento)
    commercial = _commercial_fallback(memory, stage, incoming)
    if commercial:
        return commercial

    if stage == "hook":
        if "academia" in segmento.lower():
            place = f" a {nome}" if memory.nome else ""
            city = f" em {memory.cidade}" if memory.cidade else ""
            return f"Boa tarde! Vi{place}{city}. Vocês trabalham mais com musculação, funcional ou acompanhamento?", "qualify"
        if memory.rating:
            return f"Boa tarde! Vi a {nome} no Google com {memory.rating} estrelas. Vocês atendem bastante gente da região?", "qualify"
        return f"Boa tarde! Falo com o responsável pela {nome}?", "qualify"
    if stage in {"qualify", "followup_24h", "followup_72h"}:
        return f"Perfeito. Hoje chegam mais {subject} por indicação, Instagram ou Google?", "pain"
    if stage == "pain":
        return f"Entendi. E quando alguém procura {segmento} em {memory.cidade or 'sua região'}, vocês aparecem bem no Google?", "amplify"
    if stage == "amplify":
        return f"Faz sentido. Se tivesse uma forma simples de aparecer melhor para {subject}, você avaliaria?", "tease"
    if stage == "tease":
        return "Posso te mostrar uma ideia curta antes de qualquer decisão?", "proof"
    if stage in {"proof", "reveal"} and memory.site_url:
        return f"Show. Montei esta prévia para vocês: {memory.site_url}. O que achou da ideia?", "feedback"
    if stage == "feedback":
        return "O que você mudaria para ficar com a cara de vocês?", "close"
    if stage == "close":
        return "Quer que eu deixe isso pronto para vocês avaliarem com calma?", "close"
    return f"Entendi. Me conta melhor como a {nome} recebe {subject} hoje?", stage or "qualify"


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


# ════════════════════════════════════════════════════════════════════
# NODE 1: load_context (entrada - carrega tudo que precisa)
# ════════════════════════════════════════════════════════════════════

def node_load_context(state: SDRState) -> dict:
    """Carrega memória do lead, RAG, contexto inicial"""
    print(f"[SDR] Loading context for {state.get('telefone', '?')}")

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
    for field in ("lead_id", "nome", "cidade", "segmento", "site_url"):
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
    rag_context = f"{rag_context}\n\n{learning_overlay(memory.user_id, selected_agent)}"

    print(f"[SDR] Agent selected: {selected_agent} ({handoff_reason})")

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
    }


# ════════════════════════════════════════════════════════════════════
# NODE 2: check_schedule (verifica horário)
# ════════════════════════════════════════════════════════════════════

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


def node_greeting(state: SDRState) -> dict:
    """Cumprimento inbound: retoma contexto e conduz com uma pergunta curta."""
    memory = state.get("memory")
    if not memory:
        return {"outgoing_message": "", "should_send": False}

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

    if prior_assistant:
        if memory.segmento:
            reply = (
                f"{greeting}! Retomando o que te mandei: hoje a prioridade de vocês "
                f"é captar mais clientes para {memory.segmento} ou era outro assunto?"
            )
        elif memory.nome:
            reply = (
                f"{greeting}! Retomando o que te mandei sobre a {memory.nome}: "
                "vocês querem mais clientes pelo online ou era outro assunto?"
            )
        else:
            reply = (
                f"{greeting}! Retomando minha mensagem: você quer falar sobre "
                "captação de clientes ou era outro assunto?"
            )
    elif memory.segmento:
        reply = (
            f"{greeting}! Tudo bem? Você quer ajuda com captação de clientes para "
            f"{memory.segmento} ou era outro assunto?"
        )
    else:
        reply = (
            f"{greeting}! Tudo bem? Me diz rapidinho: você quer falar sobre "
            "site/captação de clientes ou é outro assunto?"
        )

    memory.last_message_received = state.get("incoming_message", "")
    memory.last_message_sent = reply
    save_agent_note(memory, state.get("selected_agent") or "atendimento", "Lead cumprimentou/abriu conversa; responder contexto antes de vender.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": memory.stage,
    }


# ════════════════════════════════════════════════════════════════════
# NODE 4: node_hook (primeira abordagem)
# ════════════════════════════════════════════════════════════════════

def node_hook(state: SDRState) -> dict:
    """Stage HOOK - primeira mensagem"""
    memory = state.get("memory")
    if not memory:
        return {"outgoing_message": "", "should_send": False}

    greeting = get_greeting()
    variant = state.get("variant", "A")

    if state.get("is_outbound") and not state.get("incoming_message"):
        reply, next_stage = _fallback_reply("hook", memory, "")
        memory.update_stage(next_stage)
        memory.last_message_sent = reply
        save_agent_note(memory, state.get("selected_agent") or "abordagem", "Abordagem inicial enviada; proximo agente deve validar permissao/interesse antes de vender.")
        memory.attempts += 1
        return {
            "outgoing_message": reply,
            "should_send": bool(reply and is_valid_length(reply) and has_one_question(reply)),
            "memory": memory,
            "next_stage": memory.stage,
        }

    # Tentar LLM
    try:
        from agents.llm_direct import call_claude

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

        full_system = (
            get_persona_text(state.get("persona", "consultivo")) + "\n\n" +
            agent_system_overlay(state.get("agent_context", {})) + "\n\n" +
            stage_prompt + "\n\n" +
            state.get("rag_context", "")
        )

        response_text = call_claude(
            system=full_system,
            user=user_prompt,
            model="sonnet",  # ← SONNET (não Haiku)
            max_tokens=400,
            temperature=0.7,
            agent_name=state.get("selected_agent") or "franz",
            enable_context=False,
        )

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
    except Exception as e:
        print(f"[SDR] hook LLM falhou: {e}")
        reply, next_stage = _fallback_reply("hook", memory, state.get("incoming_message", ""))
        update_facts = {}

    # Validar
    contaminado = check_segment_contamination(reply, memory.segmento)
    if contaminado:
        print(f"[SDR] hook: contaminação detectada {contaminado}, usando fallback")
        if memory.segmento and "academia" in memory.segmento.lower():
            reply = f"{greeting}! Vocês trabalham mais com musculação, funcional ou acompanhamento?"
        else:
            reply = f"{greeting}! Falo com o responsável pela {memory.nome}?"

    next_stage = _next_stage(memory.stage, next_stage, "qualify")
    memory.update_stage(next_stage)
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

            # Persona texto
            persona_text = get_persona_text(persona)

            # Stage prompt para a persona (passa variant e variant_example)
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

            response_text = call_claude(
                system=full_system,
                user=user_prompt,
                model="sonnet",
                max_tokens=500,
                temperature=0.7,
                agent_name=state.get("selected_agent") or "franz",
                enable_context=False,
            )

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
        except Exception as e:
            print(f"[SDR] {stage_name} LLM falhou: {e}")
            reply, next_stage = _fallback_reply(stage_name, memory, incoming)
            update_facts = {}

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
            print(f"[SDR] {stage_name}: contaminado {contaminado}, fallback")
            if "academia" in memory.segmento.lower():
                reply = f"Desculpa, me expressei mal. Falando da {memory.nome}: como vocês captam alunos novos hoje?"
            else:
                reply = f"Quero entender melhor a {memory.nome}: como vocês captam clientes novos hoje?"

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

def node_opt_out(state: SDRState) -> dict:
    """Lead pediu pra parar - encerra"""
    memory = state.get("memory")
    if not memory:
        return {}

    memory.mark_opt_out()
    reply = "Entendido! Vou remover seu contato agora. Se mudar de ideia no futuro, pode chamar 👍"
    save_agent_note(memory, "supervisor", "Lead pediu opt-out; nao retomar contato automatico.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": "opt_out",
    }


def node_is_decisor(state: SDRState) -> dict:
    """Lead confirmou que é decisor - atualiza e segue funil"""
    memory = state.get("memory")
    if not memory:
        return {}

    memory.is_decisor = True
    memory.gatekeeper_level = 0
    memory.last_message_received = state.get("incoming_message", "")
    reply, next_stage = _fallback_reply("qualify", memory, memory.last_message_received)
    memory.update_stage(next_stage)
    memory.last_message_sent = reply
    save_agent_note(memory, state.get("selected_agent") or "qualificacao", "Lead confirmou ser decisor; pode qualificar dor e canal de captacao.")

    return {
        "outgoing_message": reply,
        "should_send": True,
        "memory": memory,
        "next_stage": memory.stage,
    }


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

    reply = f"Combinado. Te chamo {label}{time_label} então."

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

def node_save_and_send(state: SDRState) -> dict:
    """Salva memória e marca como pronto para enviar"""
    memory = state.get("memory")
    if not memory:
        return {}

    if not state.get("should_send", False):
        return {}

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

    return {}


# ════════════════════════════════════════════════════════════════════
# CONSTRUÇÃO DO GRAFO
# ════════════════════════════════════════════════════════════════════

def build_sdr_graph() -> StateGraph:
    """Constrói o grafo SDR"""

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
