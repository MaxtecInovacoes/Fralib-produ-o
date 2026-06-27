"""
WhatsApp Automation Endpoints
Rotas para gerenciar automação de WhatsApp
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.services.whatsapp_automation_service import (
    get_automation_service,
    WhatsAppAutomationService,
    SequenceStage,
    AutomationConfig
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/automation", tags=["Automation"])

# ============================================
# MODELS
# ============================================

class SequenceStatusResponse(BaseModel):
    lead_id: str
    lead_name: str
    current_day: int
    next_message_at: Optional[str]
    stage: str
    engagement_score: int

class TriggerRequest(BaseModel):
    trigger_type: str  # sequence_7_days, followup, urgency, upsell
    lead_ids: Optional[List[str]] = None

class TriggerResponse(BaseModel):
    success: bool
    triggered: int
    errors: List[str] = []

class LeadScoringResponse(BaseModel):
    lead_id: str
    lead_name: str
    score: int
    factors: dict

class AutomationStatsResponse(BaseModel):
    total_leads: int
    in_sequence: int
    completed_today: int
    pending_followups: int
    urgency_messages_sent: int

class CustomMessageRequest(BaseModel):
    lead_id: str
    message: str
    stage_override: Optional[str] = None

# ============================================
# ENDPOINTS - STATUS & STATS
# ============================================

@router.get("/status/{lead_id}", response_model=SequenceStatusResponse)
async def get_sequence_status(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Retorna status da sequência para um lead"""
    user_id = usuario["id"]

    result = db.execute(
        """
        SELECT id, nome, proximo_sequencia_dia, sdr_stage, engajamento_score,
               COALESCE(atualizado_em, created_at) as last_update
        FROM leads
        WHERE id = :lead_id AND user_id = :user_id
        """,
        {"lead_id": lead_id, "user_id": user_id}
    ).fetchone()

    if not result:
        raise HTTPException(404, "Lead não encontrado")

    return SequenceStatusResponse(
        lead_id=result[0],
        lead_name=result[1],
        current_day=result[2] or 1,
        next_message_at=result[5].isoformat() if result[5] else None,
        stage=result[3] or "pendente_wpp",
        engagement_score=result[4] or 0
    )


@router.get("/stats", response_model=AutomationStatsResponse)
async def get_automation_stats(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Retorna estatísticas da automação"""
    user_id = usuario["id"]

    # Total de leads
    total = db.execute(
        "SELECT COUNT(*) FROM leads WHERE user_id = :user_id",
        {"user_id": user_id}
    ).scalar()

    # Em sequência ativa
    in_sequence = db.execute(
        """
        SELECT COUNT(*) FROM leads
        WHERE user_id = :user_id
          AND sdr_stage LIKE 'day%'
          AND status = 'concluido'
        """,
        {"user_id": user_id}
    ).scalar()

    # Completados hoje
    completed_today = db.execute(
        """
        SELECT COUNT(DISTINCT lead_id) FROM interacoes
        WHERE user_id = :user_id
          AND tipo = 'automation'
          AND created_at > NOW() - INTERVAL '1 day'
        """,
        {"user_id": user_id}
    ).scalar()

    # Follow-ups pendentes
    pending_followups = db.execute(
        """
        SELECT COUNT(*) FROM leads l
        WHERE l.user_id = :user_id
          AND l.status = 'concluido'
          AND l.sdr_stage IN ('pendente_wpp', 'hook')
          AND NOT EXISTS (
              SELECT 1 FROM interacoes i
              WHERE i.lead_id = l.id AND i.direcao = 'entrada'
          )
        """,
        {"user_id": user_id}
    ).scalar()

    # Urgência enviada
    urgency_sent = db.execute(
        """
        SELECT COUNT(*) FROM interacoes
        WHERE user_id = :user_id
          AND tipo = 'automation'
          AND etapa IN ('day6_offer', 'day7_urgency')
          AND created_at > NOW() - INTERVAL '1 day'
        """,
        {"user_id": user_id}
    ).scalar()

    return AutomationStatsResponse(
        total_leads=total or 0,
        in_sequence=in_sequence or 0,
        completed_today=completed_today or 0,
        pending_followups=pending_followups or 0,
        urgency_messages_sent=urgency_sent or 0
    )


# ============================================
# ENDPOINTS - TRIGGERS
# ============================================

@router.post("/trigger", response_model=TriggerResponse)
async def trigger_automation(
    body: TriggerRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Dispara automação selecionada"""
    user_id = usuario["id"]
    tenant_id = f"fralib_user_{user_id}"

    service = get_automation_service()
    triggered = 0
    errors = []

    try:
        if body.trigger_type == "sequence_7_days":
            await service.trigger_sequence_7_days(db, tenant_id)
            triggered = 1

        elif body.trigger_type == "followup":
            await service.trigger_followups(db, tenant_id)
            triggered = 1

        elif body.trigger_type == "urgency":
            await service.trigger_urgency(db, tenant_id)
            triggered = 1

        elif body.trigger_type == "upsell":
            await service.trigger_upsell(db, tenant_id)
            triggered = 1

        elif body.trigger_type == "custom_leads" and body.lead_ids:
            for lead_id in body.lead_ids:
                try:
                    lead = db.execute(
                        """
                        SELECT id, nome, telefone, email, segmento, site_url, plano
                        FROM leads WHERE id = :lead_id AND user_id = :user_id
                        """,
                        {"lead_id": lead_id, "user_id": user_id}
                    ).fetchone()

                    if lead:
                        config = AutomationConfig(
                            tenant_id=tenant_id,
                            lead_id=lead[0],
                            lead_name=lead[1],
                            lead_phone=lead[2],
                            lead_email=lead[3],
                            lead_segment=lead[4] or "",
                            site_url=lead[5] or "",
                            plan_type=lead[6] or "trial"
                        )
                        await service.send_automation_message(
                            db, config, SequenceStage.DAY_1_WELCOME
                        )
                        triggered += 1

                except Exception as e:
                    errors.append(f"Lead {lead_id}: {str(e)}")

        else:
            raise HTTPException(400, "Tipo de trigger inválido")

    except Exception as e:
        logger.error(f"Erro ao disparar automação: {e}")
        errors.append(str(e))

    return TriggerResponse(
        success=len(errors) == 0,
        triggered=triggered,
        errors=errors
    )


# ============================================
# ENDPOINTS - LEAD SCORING
# ============================================

@router.get("/scoring/{lead_id}", response_model=LeadScoringResponse)
async def get_lead_scoring(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Retorna score detalhado de um lead"""
    user_id = usuario["id"]

    service = get_automation_service()
    score = await service.calculate_lead_scoring(db, lead_id)

    # Buscar detalhes do lead
    lead = db.execute(
        """
        SELECT id, nome FROM leads
        WHERE id = :lead_id AND user_id = :user_id
        """,
        {"lead_id": lead_id, "user_id": user_id}
    ).fetchone()

    if not lead:
        raise HTTPException(404, "Lead não encontrado")

    # Fatores do score
    factors = await _calculate_score_factors(db, lead_id)

    return LeadScoringResponse(
        lead_id=lead[0],
        lead_name=lead[1],
        score=score,
        factors=factors
    )


async def _calculate_score_factors(db: Session, lead_id: str) -> dict:
    """Calcula fatores individuais do score"""

    result = db.execute(
        """
        SELECT
            COUNT(CASE WHEN i.direcao = 'entrada' THEN 1 END) as responses,
            COUNT(CASE WHEN i.tipo = 'pergunta' THEN 1 END) as questions,
            COUNT(CASE WHEN i.tipo = 'duvida' THEN 1 END) as doubts,
            COUNT(CASE WHEN i.tipo = 'automation' THEN 1 END) as automations,
            COUNT(DISTINCT DATE(i.created_at)) as active_days
        FROM interacoes i
        WHERE i.lead_id = :lead_id
        """,
        {"lead_id": lead_id}
    ).fetchone()

    return {
        "responses": result[0] or 0,
        "questions": result[1] or 0,
        "doubts": result[2] or 0,
        "automations_sent": result[3] or 0,
        "active_days": result[4] or 0,
        "engagement_level": _get_engagement_level(result[0] or 0)
    }


def _get_engagement_level(responses: int) -> str:
    if responses >= 10:
        return "high"
    elif responses >= 5:
        return "medium"
    elif responses >= 1:
        return "low"
    return "none"


# ============================================
# ENDPOINTS - CUSTOM MESSAGE
# ============================================

@router.post("/send-custom")
async def send_custom_message(
    body: CustomMessageRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Envia mensagem customizada para um lead"""
    user_id = usuario["id"]
    tenant_id = f"fralib_user_{user_id}"

    # Buscar dados do lead
    lead = db.execute(
        """
        SELECT id, nome, telefone, email, segmento, site_url, plano
        FROM leads WHERE id = :lead_id AND user_id = :user_id
        """,
        {"lead_id": body.lead_id, "user_id": user_id}
    ).fetchone()

    if not lead:
        raise HTTPException(404, "Lead não encontrado")

    config = AutomationConfig(
        tenant_id=tenant_id,
        lead_id=lead[0],
        lead_name=lead[1],
        lead_phone=lead[2],
        lead_email=lead[3],
        lead_segment=lead[4] or "",
        site_url=lead[5] or "",
        plan_type=lead[6] or "trial"
    )

    service = get_automation_service()

    # Determinar estágio
    stage = SequenceStage.FOLLOWUP_1
    if body.stage_override:
        try:
            stage = SequenceStage(body.stage_override)
        except ValueError:
            pass

    result = await service.send_automation_message(
        db, config, stage, body.message
    )

    if result.get("success"):
        return {"success": True, "message_id": result.get("message_id")}
    else:
        raise HTTPException(500, result.get("error", "Erro desconhecido"))


# ============================================
# ENDPOINTS - SEQUENCE MANAGEMENT
# ============================================

@router.get("/sequence-leads")
async def list_sequence_leads(
    status: Optional[str] = Query(None, description="Filtrar por estágio"),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Lista leads na sequência de 7 dias"""
    user_id = usuario["id"]

    query = """
        SELECT l.id, l.nome, l.telefone, l.segmento,
               l.proximo_sequencia_dia, l.sdr_stage, l.engajamento_score,
               l.site_url, l.trial_expires_at
        FROM leads l
        WHERE l.user_id = :user_id
          AND l.status = 'concluido'
          AND l.site_url IS NOT NULL
    """

    params = {"user_id": user_id}

    if status:
        if status == "active":
            query += " AND l.sdr_stage LIKE 'day%'"
        elif status == "pending":
            query += " AND l.sdr_stage = 'pendente_wpp'"
        elif status == "completed":
            query += " AND l.sdr_stage IN ('ganhos', 'perdidos')"

    query += " ORDER BY l.proximo_sequencia_dia ASC NULLS FIRST, l.created_at DESC LIMIT 50"

    result = db.execute(query, params)

    leads = []
    for row in result.fetchall():
        leads.append({
            "id": row[0],
            "nome": row[1],
            "telefone": row[2],
            "segmento": row[3],
            "current_day": row[4] or 0,
            "stage": row[5],
            "engagement_score": row[6] or 0,
            "site_url": row[7],
            "trial_expires_at": row[8].isoformat() if row[8] else None
        })

    return leads


@router.post("/sequence/{lead_id}/skip")
async def skip_sequence_day(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Pula um dia da sequência para um lead"""
    user_id = usuario["id"]

    result = db.execute(
        """
        UPDATE leads
        SET proximo_sequencia_dia = proximo_sequencia_dia + 1,
            atualizado_em = NOW()
        WHERE id = :lead_id AND user_id = :user_id
        RETURNING id, proximo_sequencia_dia
        """,
        {"lead_id": lead_id, "user_id": user_id}
    )

    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Lead não encontrado")

    db.commit()

    return {
        "success": True,
        "lead_id": row[0],
        "new_day": row[1]
    }


@router.post("/sequence/{lead_id}/reset")
async def reset_sequence(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Reseta a sequência para o dia 1"""
    user_id = usuario["id"]

    result = db.execute(
        """
        UPDATE leads
        SET proximo_sequencia_dia = 1,
            sdr_stage = 'pendente_wpp',
            atualizado_em = NOW()
        WHERE id = :lead_id AND user_id = :user_id
        RETURNING id
        """,
        {"lead_id": lead_id, "user_id": user_id}
    )

    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Lead não encontrado")

    db.commit()

    return {
        "success": True,
        "lead_id": row[0],
        "reset_to_day": 1
    }
