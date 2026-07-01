"""Handoff do SDR para o Closer humano.

Quando o lead chega em 'won' ou pede explicitamente contato humano,
o SDR chama handoff_to_closer() que:
1. Enfileira no closer_queue
2. Notifica o closer via WhatsApp (mensagem separada, NAO no chat do lead)
3. Marca o lead como is_human_takeover=True
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

log = logging.getLogger("sdr-handoff")


def handoff_to_closer(
    *,
    user_id: int,
    lead_id: int,
    lead_telefone: str,
    lead_nome: str,
    stage: str,
    memory: Any,  # LeadMemory
    history: list[dict[str, Any]],
) -> int:
    """Enfileira lead para closer humano. Retorna queue_id.

    Args:
        user_id: tenant ID
        lead_id: lead ID no DB
        lead_telefone: telefone do lead
        lead_nome: nome do lead (para contexto do closer)
        stage: stage atual do SDR ('won', 'close', etc.)
        memory: LeadMemory instance (com BANT/MEDDIC/temperature)
        history: últimas mensagens do lead (formato interacoes)
    """
    try:
        from backend.core.database import engine
        from backend.services.closer_queue import enqueue_closer

        # Monta contexto das últimas 10 msgs
        last_msgs = []
        for h in history[-10:]:
            last_msgs.append({
                "direction": h.get("direcao", "?"),
                "text": (h.get("mensagem") or h.get("text") or "")[:500],
                "criado_em": h.get("criado_em"),
            })

        # Monta contexto rico
        context = {
            "last_messages": last_msgs,
            "stage": stage,
            "msgs_sent_count": memory.msgs_sent_count,
            "humanization_profile": memory.humanization_profile,
            "wall_street_close_used": memory.wall_street_close_used,
            "top_concorrentes": memory.top_concorrentes,
            "agent_notes": memory.agent_notes,
            "variant": memory.variant,
        }

        # BANT score agregado
        bant_score = (
            (10 if memory.bant_budget else 0)
            + (5 if memory.bant_authority else 0)
            + memory.bant_need_score
            + (10 if memory.bant_timeline else 0)
        )

        # MEDDIC score agregado
        meddic_score = memory.meddic_score

        queue_id = enqueue_closer(
            engine,
            user_id=user_id,
            lead_id=lead_id,
            lead_telefone=lead_telefone,
            lead_nome=lead_nome,
            stage_at_handoff=stage,
            context=context,
            bant_score=bant_score,
            meddic_score=meddic_score,
            main_objection=memory.main_objection or "",
            pain_identified=memory.pain_identified or "",
            temperature=memory.lead_temperature or "morno",
        )

        # Notifica o closer via WhatsApp (mensagem separada)
        _notify_closer_via_whatsapp(
            user_id=user_id,
            queue_id=queue_id,
            lead_nome=lead_nome,
            lead_telefone=lead_telefone,
            temperature=memory.lead_temperature or "morno",
            bant_score=bant_score,
            pain_identified=memory.pain_identified or "",
        )

        # Marca como takeover humano
        memory.is_human_takeover = True
        log.info(
            f"[HANDOFF] Tenant {user_id}: lead {lead_id} ({lead_nome}) "
            f"enfileirado para closer queue_id={queue_id} bant={bant_score} temp={memory.lead_temperature}"
        )

        return queue_id
    except Exception as e:
        log.error(f"[HANDOFF] Falha ao enfileirar lead {lead_id}: {e}")
        raise


def _notify_closer_via_whatsapp(
    *,
    user_id: int,
    queue_id: int,
    lead_nome: str,
    lead_telefone: str,
    temperature: str,
    bant_score: int,
    pain_identified: str,
) -> None:
    """Envia msg de aviso para o closer do tenant.

    O closer recebe no WhatsApp dele (não no chat do lead):
    "🔥 Lead quente na fila! [nome] - [telefone]"
    "   Dor: [dor]"
    "   Score BANT: [n]/35"
    "   Temperatura: [quente/morno/frio]"
    "   Acesse: /api/closer/queue"
    """
    try:
        closer_phone = os.getenv(f"FRALIB_CLOSER_PHONE_USER_{user_id}") or os.getenv("FRALIB_CLOSER_PHONE_DEFAULT")
        if not closer_phone:
            log.warning(f"[HANDOFF] Nenhum closer_phone configurado para tenant {user_id}")
            return
        emoji = {"quente": "🔥", "morno": "🌡️", "frio": "❄️"}.get(temperature, "🌡️")
        message = (
            f"{emoji} *Lead na fila do closer!*\n\n"
            f"👤 {lead_nome}\n"
            f"📞 {lead_telefone}\n"
            f"🎯 Dor: {pain_identified[:200] if pain_identified else 'não identificada'}\n"
            f"📊 BANT: {bant_score}/35\n"
            f"🌡️ Temp: {temperature}\n"
            f"📋 Queue ID: {queue_id}\n\n"
            f"Acesse: https://fralib.app/api/closer/queue"
        )
        # Em produção, enviar via meowhats:
        # send_whatsapp_message(closer_phone, message)
        log.info(f"[HANDOFF] Notificaria closer {closer_phone}: {message[:120]}")
    except Exception as e:
        log.warning(f"[HANDOFF] Erro ao notificar closer: {e}")
