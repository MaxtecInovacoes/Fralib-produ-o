"""
Compat - Interface compatível com bryan.py
Permite que o resto do sistema continue usando responder_lead(), iniciar_contato(), etc
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Optional
from pydantic import BaseModel

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(AGENTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, AGENTS_DIR)

from .agent import get_sdr_graph
from .lead_lock import _lead_lock_guard  # Fix bug 3x duplicate replies

# Importar ESTADO_TO_STAGE do source of truth (DRY)
from backend.whatsapp.connection_tracker import ESTADO_TO_STAGE


# ════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMAS (compat com bryan.py)
# ════════════════════════════════════════════════════════════════════

class BryanInput(BaseModel):
    """Compat com BryanInput original"""
    nome: str
    cidade: str
    segmento: str
    telefone: str
    whatsapp: Optional[str] = None
    rating: Optional[float] = 0
    site_url: Optional[str] = None
    score_caio: Optional[int] = 0
    concorrentes: Optional[dict] = None
    # Sprint 14.x: paleta_cores para identidade visual no WhatsApp SDR
    paleta_cores: Optional[Dict[str, str]] = {}
    tier: Optional[str] = "STANDARD"
    proof: Optional[str] = None


class BryanOutput(BaseModel):
    """Compat com BryanOutput original"""
    reply: str
    intent: str = "other"
    next_stage: str = "hook"
    estrategia: str = "rapport_build"
    proximo_passo: str = "Aguardar resposta do lead (24h)"
    enviado: bool = False
    should_handoff: bool = False
    price_tier: int = 0
    guard: Optional[str] = None
    update_facts: Optional[dict] = None
    active_agent: str = ""
    previous_agent: str = ""
    handoff_reason: str = ""


FranzInput = BryanInput
FranzOutput = BryanOutput


def _lead_payload_from_memory(memoria: dict | None) -> dict:
    """Lê contexto tanto da memória nova flat quanto da antiga nested."""
    data = dict(memoria or {})
    nested = data.get("lead") if isinstance(data.get("lead"), dict) else {}
    lead = dict(nested)
    for key in (
        "nome", "cidade", "segmento", "telefone", "whatsapp", "rating",
        "site_url", "score_caio", "concorrentes", "tier", "proof",
        "paleta_cores"
    ):
        if data.get(key) not in (None, ""):
            lead[key] = data.get(key)
    return lead


# ════════════════════════════════════════════════════════════════════
# ENTRY POINTS
# ════════════════════════════════════════════════════════════════════

def iniciar_contato(lead: BryanInput, user_id: int = None) -> BryanOutput:
    """
    Inicia contato com lead qualificado (substitui bryan.iniciar_contato).
    Mantém assinatura compatível.
    """
    if not user_id:
        raise ValueError("user_id obrigatorio em iniciar_contato (multi-tenant)")

    # Salvar dados do lead na memória antes de gerar a intro
    session_id = f"franz_lead_{lead.telefone}"
    try:
        from agents.memory import carregar_memoria, salvar_memoria
        memoria = carregar_memoria(session_id, user_id=user_id) or {}

        # Atualizar dados do lead
        lead_payload = {
            "nome": lead.nome,
            "cidade": lead.cidade,
            "segmento": lead.segmento,
            "telefone": lead.telefone,
            "whatsapp": lead.whatsapp or lead.telefone,
            "rating": lead.rating or 0,
            "site_url": lead.site_url or "",
            "score_caio": lead.score_caio or 0,
            "concorrentes": lead.concorrentes,
            "tier": lead.tier or "STANDARD",
            "proof": lead.proof,
            # Sprint 14.x: paleta_cores para identidade visual no SDR
            "paleta_cores": getattr(lead, "paleta_cores", {}) or {},
        }
        memoria.update({
            **lead_payload,
            "lead": {
                **lead_payload,
            },
            "user_id": user_id,
            "telefone": lead.telefone,
            "lead_id": lead.telefone,
        })
        salvar_memoria(session_id, memoria, user_id=user_id)
    except Exception as e:
        print(f"[SDR Compat] Erro ao salvar dados do lead: {e}")

    # WATCHDOG: previne vícios do bryan antigo
    try:
        from agents.memory import carregar_memoria as _carregar
        mem = _carregar(session_id, user_id=user_id) or {}
        sdr_stage_atual = mem.get("estado", "pendente_wpp")
        pode_enviar, motivo = _verificar_watchdog_outbound(lead.telefone, user_id, sdr_stage_atual)
        if not pode_enviar:
            print(f"[SDR Compat] 🛑 Watchdog bloqueou intro: {motivo}")
            return BryanOutput(
                reply="",
                intent="watchdog_blocked",
                next_stage=sdr_stage_atual,
                estrategia="fila",
                proximo_passo=f"Watchdog: {motivo}",
                enviado=False,
                guard=f"watchdog_{motivo}",
            )
    except Exception as e:
        print(f"[SDR Compat] Watchdog erro (seguindo): {e}")

    # Invocar o grafo
    graph = get_sdr_graph()
    initial_state = {
        "user_id": user_id,
        "lead_id": lead.telefone,
        "telefone": lead.telefone,
        "incoming_message": "",  # Outbound (sem mensagem recebida)
        "is_outbound": True,
        "nome": lead.nome,
        "cidade": lead.cidade,
        "segmento": lead.segmento,
        "rating": lead.rating or 0,
        "site_url": lead.site_url or "",
        "paleta_cores": getattr(lead, "paleta_cores", {}) or {},
    }

    try:
        result = graph.invoke(initial_state)
    except Exception as e:
        print(f"[SDR Compat] Erro no grafo: {e}")
        return BryanOutput(
            reply="",
            intent="error",
            next_stage="hook",
            estrategia="fila",
            proximo_passo=f"Erro: {str(e)[:50]}",
            enviado=False,
            guard="graph_error",
        )

    memory = result.get("memory")
    if not memory:
        return BryanOutput(reply="", enviado=False, guard="no_memory")

    return BryanOutput(
        reply=result.get("outgoing_message", ""),
        intent=result.get("detected_intent", "other"),
        next_stage=memory.stage if memory else "hook",
        estrategia="rapport_build",
        proximo_passo="Aguardar resposta do lead (24h)",
        enviado=False,
        guard=result.get("guard_reason"),
        update_facts=memory.model_dump() if memory else None,
        active_agent=getattr(memory, "active_agent", "") if memory else "",
        previous_agent=getattr(memory, "previous_agent", "") if memory else "",
        handoff_reason=result.get("agent_handoff_reason", ""),
    )


def _verificar_watchdog_outbound(telefone: str, user_id: int, sdr_stage: str) -> tuple:
    """
    Watchdog: previne vícios do bryan antigo.
    Bloqueia envio se:
    - Já mandou 2+ mensagens sem resposta real
    - Cooldown de 24h não passou
    """
    try:
        from .watchdog import can_send_next_outbound
        pode_enviar, motivo = can_send_next_outbound(telefone, user_id, sdr_stage)
        return pode_enviar, motivo
    except Exception as e:
        print(f"[Compat] Erro watchdog: {e}")
        return True, "watchdog_error"


def responder_lead(
    telefone: str,
    mensagem_recebida: str,
    nome_negocio: str = "",
    lead_id: str = "",
    cidade: str = "",
    segmento: str = "",
    rating: float = 0,
    site_url: str = "",
    history: list | None = None,
    sdr_stage: str = "",
    user_id: int = None,
) -> BryanOutput:
    """
    Responde mensagem do lead (substitui bryan.responder_lead).
    Mantém assinatura compatível.

    IMPORTANTE: Wrapped em _lead_lock_guard para prevenir race condition
    onde 2 threads/processos processam a mesma msg simultaneamente.
    """
    if not user_id:
        raise ValueError("user_id obrigatorio em responder_lead (multi-tenant)")

    # Lock global por lead_id - garante que só 1 execução por vez
    lock_key = lead_id or telefone or ""
    with _lead_lock_guard(lock_key):
        return _responder_lead_locked(
            telefone=telefone,
            mensagem_recebida=mensagem_recebida,
            nome_negocio=nome_negocio,
            lead_id=lead_id,
            cidade=cidade,
            segmento=segmento,
            rating=rating,
            site_url=site_url,
            history=history,
            sdr_stage=sdr_stage,
            user_id=user_id,
        )


def _responder_lead_locked(
    telefone: str,
    mensagem_recebida: str,
    nome_negocio: str = "",
    lead_id: str = "",
    cidade: str = "",
    segmento: str = "",
    rating: float = 0,
    site_url: str = "",
    history: list | None = None,
    sdr_stage: str = "",
    user_id: int = None,
) -> BryanOutput:
    """Implementação interna do responder_lead (wrapped em lock)."""

    # Carregar dados do lead da memória
    session_id = f"franz_lead_{telefone}"
    try:
        from agents.memory import carregar_memoria
        memoria = carregar_memoria(session_id, user_id=user_id) or {}
        lead_data = _lead_payload_from_memory(memoria)
    except Exception:
        lead_data = {}

    # BUGFIX: Carregar state LangGraph anterior e mesclar com history
    # Problema: history do DB tem só 8 últimas, mas state pode ter conversas mais longas
    merged_history = list(history or [])

    # Tentar carregar mensagens da memória do lead (se existir conversation_history)
    try:
        lg_history = memoria.get("conversation_history", [])
        if lg_history and isinstance(lg_history, list):
            # lg_history é lista de mensagens LangGraph (com type e content)
            for msg in lg_history[-10:]:  # Pegar últimas 10 mensagens do state
                if isinstance(msg, dict):
                    role = "assistant" if msg.get("type") == "ai" else "user"
                    content = msg.get("content", "")
                else:
                    # Mensagem no formato str ou objeto
                    role = "assistant"
                    content = str(msg) if msg else ""
                if content:
                    merged_history.insert(0, {"role": role, "content": content})
    except Exception as e:
        print(f"[SDR] Erro ao carregar state LangGraph anterior: {e}")

    # Remover duplicatas mantendo ordem (mais antigo primeiro)
    seen = set()
    deduped_history = []
    for item in merged_history:
        key = f"{item.get('role')}:{item.get('content', '')[:50]}"
        if key not in seen:
            seen.add(key)
            deduped_history.append(item)
    merged_history = deduped_history[-20:]  # Manter últimas 20 mensagens

    # Invocar o grafo
    graph = get_sdr_graph()
    initial_state = {
        "user_id": user_id,
        "lead_id": lead_id or telefone,
        "telefone": telefone,
        "incoming_message": mensagem_recebida,
        "is_outbound": False,
        "nome": nome_negocio or lead_data.get("nome", ""),
        "cidade": cidade or lead_data.get("cidade", ""),
        "segmento": segmento or lead_data.get("segmento", ""),
        "rating": rating or lead_data.get("rating", 0),
        "site_url": site_url or lead_data.get("site_url", ""),
        "history": merged_history,
        "sdr_stage": sdr_stage or "",
    }

    try:
        result = graph.invoke(initial_state)
    except Exception as e:
        print(f"[SDR Compat] Erro no grafo: {e}")
        return BryanOutput(
            reply="Opa, tudo bem? Me dá um minuto que já te respondo!",
            intent="error",
            next_stage="hook",
            estrategia="fila",
            proximo_passo=f"Erro: {str(e)[:50]}",
            enviado=False,
            guard="graph_error",
        )

    memory = result.get("memory")
    reply = result.get("outgoing_message", "")

    if not reply:
        return BryanOutput(
            reply="",
            intent=result.get("detected_intent", "other"),
            next_stage=(memory.stage if memory else "hook"),
            estrategia="noop",
            proximo_passo="Sem ação necessária",
            enviado=False,
            guard=result.get("guard_reason", "no_reply"),
            active_agent=getattr(memory, "active_agent", "") if memory else "",
            previous_agent=getattr(memory, "previous_agent", "") if memory else "",
            handoff_reason=result.get("agent_handoff_reason", ""),
        )

    return BryanOutput(
        reply=reply,
        intent=result.get("detected_intent", "other"),
        next_stage=memory.stage if memory else "hook",
        estrategia="franz_consultivo",
        proximo_passo="Aguardar resposta do lead",
        enviado=False,
        guard=result.get("guard_reason"),
        update_facts=memory.model_dump() if memory else None,
        active_agent=getattr(memory, "active_agent", "") if memory else "",
        previous_agent=getattr(memory, "previous_agent", "") if memory else "",
        handoff_reason=result.get("agent_handoff_reason", ""),
    )


def followup_automatico(
    telefone: str,
    tipo: str = "24h",
    user_id: int = None,
) -> BryanOutput:
    """
    Gera follow-up automático (substitui bryan.followup_automatico).
    """
    if not user_id:
        raise ValueError("user_id obrigatorio em followup_automatico (multi-tenant)")

    # Determinar stage do follow-up
    followup_stage = "followup_24h" if tipo == "24h" else "followup_72h"

    # Forçar a stage na memória
    try:
        from agents.memory import carregar_memoria, salvar_memoria
        session_id = f"franz_lead_{telefone}"
        memoria = carregar_memoria(session_id, user_id=user_id) or {}
        memoria["stage"] = followup_stage
        salvar_memoria(session_id, memoria, user_id=user_id)
    except Exception:
        pass

    # WATCHDOG: previne spam de follow-up
    try:
        pode_enviar, motivo = _verificar_watchdog_outbound(telefone, user_id, followup_stage)
        if not pode_enviar:
            print(f"[SDR Compat] 🛑 Watchdog bloqueou follow-up {tipo}: {motivo}")
            return BryanOutput(
                reply="",
                intent="watchdog_blocked",
                next_stage=followup_stage,
                estrategia="fila",
                proximo_passo=f"Watchdog: {motivo}",
                enviado=False,
                guard=f"watchdog_{motivo}",
            )
    except Exception as e:
        print(f"[SDR Compat] Watchdog erro (seguindo): {e}")

    # Invocar o grafo
    return responder_lead(
        telefone=telefone,
        mensagem_recebida="",  # Outbound
        nome_negocio="",
        user_id=user_id,
    )


_PRE_REVEAL_STAGES = {
    "hook",
    "intro",
    "qualify",
    "pain",
    "amplify",
    "tease",
    "followup1",
    "followup2",
    "followup_24h",
    "followup_72h",
    "f1",
    "f2",
}


def gerar_followup(lead: dict, tipo: str = "24h", user_id: int = None) -> str:
    """
    Compat leve com o Bryan antigo para previews/testes determinísticos.
    Nunca revela URL antes do estágio de prova/reveal.
    """
    nome = (lead or {}).get("nome") or "seu negócio"
    segmento = (lead or {}).get("segmento") or "captação"
    stage = str((lead or {}).get("sdr_stage") or "hook").lower()
    agent_name = _agent_name_for_user(user_id)

    if stage in _PRE_REVEAL_STAGES:
        if tipo == "72h":
            return (
                f"{agent_name} aqui. Última tentativa por aqui: vocês ainda "
                f"querem melhorar a captação de clientes para {nome}?"
            )
        return (
            f"{agent_name} aqui. Minha mensagem passou batido; vocês ainda "
            f"querem avaliar uma ideia simples para {segmento}?"
        )

    return (
        f"{agent_name} aqui. Você conseguiu olhar a ideia que mandei? "
        "Me diz se faz sentido ajustar com a cara de vocês."
    )


# ════════════════════════════════════════════════════════════════════
# FUNCTIONS AUXILIARES (compat com whatsapp_listener)
# ════════════════════════════════════════════════════════════════════

def _dentro_do_horario(user_id: int = None) -> bool:
    """Compat com bryan._dentro_do_horario"""
    from .tools import is_within_schedule
    return is_within_schedule(user_id)


def _agent_name_for_user(user_id: int = None) -> str:
    """Compat com bryan._agent_name_for_user"""
    from .tools import get_agent_name
    return get_agent_name(user_id)


def _escolher_variante(lead_id: str, segmento: str = "", tier: str = "", user_id: int = None) -> str:
    """Compat com bryan._escolher_variante"""
    from .tools import choose_variant
    return choose_variant(lead_id, segmento, user_id)


# ════════════════════════════════════════════════════════════════════
# CONSTANTES EXPORTADAS (compat com bryan)
# ════════════════════════════════════════════════════════════════════

ESTADOS_SDR = [
    "hook", "qualify", "pain", "amplify", "tease",
    "proof", "reveal", "feedback", "close", "urgency",
    "handoff", "won", "lost", "scheduled", "followup_24h", "followup_72h",
]

# NOTE: ESTADO_TO_STAGE agora é importado de backend.whatsapp.connection_tracker
# (linha ~23) para manter DRY - fonte unica de verdade


# ════════════════════════════════════════════════════════════════════
# CACHE DE HORÁRIO (compat com bryan._HORARIO_CACHE)
# ════════════════════════════════════════════════════════════════════

_HORARIO_CACHE = {}  # {cache_key: (config, expiry_timestamp)}


def _get_horario_config(user_id: int) -> dict:
    """Compat com bryan._get_horario_config"""
    import time
    _cache_key = f"sdr_horario_{user_id}"
    cached = _HORARIO_CACHE.get(_cache_key)
    if cached and time.time() < cached[1]:
        return cached[0]
    try:
        from . import _get_sdr_settings_for_user as _local_settings
        from services.sdr_settings import outbound_schedule_from_settings

        settings = _local_settings(user_id)
        config = outbound_schedule_from_settings(settings) if settings else None
        _HORARIO_CACHE[_cache_key] = (config, time.time() + 300)
        return config
    except Exception:
        return None


def _get_sdr_settings_for_user(user_id: int | None) -> dict:
    """Compat com bryan._get_sdr_settings_for_user"""
    if not user_id:
        return {}
    try:
        from database import engine
        from services.sdr_settings import get_sdr_settings_runtime
        return get_sdr_settings_runtime(user_id, engine)
    except Exception:
        return {}
