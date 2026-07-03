"""
Cron Endpoints for Automation
Dispara automações de WhatsApp via cron job
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.database import get_db
from backend.services.whatsapp_automation_service import get_automation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cron", tags=["Cron"])


class CronTriggerRequest(BaseModel):
    task: str
    force: bool = False


@router.post("/automation")
async def trigger_daily_automation(
    db: Session = Depends(get_db),
    task: str = "sequence_7_days"
):
    """Dispara automações do dia (chamado por cron externo)"""

    # Buscar todos os tenants ativos
    tenants = db.execute(
        text("""
            SELECT DISTINCT u.id
            FROM users u
            WHERE u.status = 'ativo'
              AND u.plano IN ('trial', 'starter', 'pro', 'business', 'ilimitado')
        """)
    ).fetchall()

    results = {
        "timestamp": datetime.now().isoformat(),
        "tenants_processed": 0,
        "messages_sent": 0,
        "errors": []
    }

    service = get_automation_service()

    for tenant_row in tenants:
        tenant_id = f"fralib_user_{tenant_row[0]}"

        try:
            if task == "sequence_7_days":
                await service.trigger_sequence_7_days(db, tenant_id)

            elif task == "followup":
                await service.trigger_followups(db, tenant_id)

            elif task == "urgency":
                await service.trigger_urgency(db, tenant_id)

            elif task == "upsell":
                await service.trigger_upsell(db, tenant_id)

            elif task == "all":
                await service.trigger_sequence_7_days(db, tenant_id)
                await service.trigger_followups(db, tenant_id)
                await service.trigger_urgency(db, tenant_id)

            results["tenants_processed"] += 1

        except Exception as e:
            logger.error(f"Erro no tenant {tenant_id}: {e}")
            results["errors"].append(f"Tenant {tenant_id}: {str(e)}")

    # Contar mensagens enviadas hoje
    messages_today = db.execute(
        text("""
            SELECT COUNT(*)
            FROM interacoes
            WHERE tipo = 'automation'
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
    ).scalar()

    results["messages_sent"] = messages_today

    return results


@router.get("/automation/schedule")
async def get_automation_schedule(db: Session = Depends(get_db)):
    """Retorna o schedule de automações pendentes"""

    # Leads esperando mensagem do dia
    pending_today = db.execute(
        text("""
            SELECT COUNT(*)
            FROM leads
            WHERE status = 'concluido'
              AND site_url IS NOT NULL
              AND proximo_sequencia_dia BETWEEN 1 AND 7
        """)
    ).scalar()

    # Follow-ups pendentes
    pending_followup = db.execute(
        text("""
            SELECT COUNT(*)
            FROM leads l
            WHERE l.status = 'concluido'
              AND l.site_url IS NOT NULL
              AND l.sdr_stage = 'pendente_wpp'
              AND NOT EXISTS (
                  SELECT 1 FROM interacoes i
                  WHERE i.lead_id = l.id
                    AND i.direcao = 'entrada'
              )
        """)
    ).scalar()

    # Urgência (trial acabando)
    urgency_pending = db.execute(
        text("""
            SELECT COUNT(*)
            FROM leads
            WHERE status = 'concluido'
              AND trial_expires_at BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
        """)
    ).scalar()

    return {
        "pending_sequence": pending_today or 0,
        "pending_followup": pending_followup or 0,
        "pending_urgency": urgency_pending or 0,
        "last_check": datetime.now().isoformat()
    }


@router.post("/automation/test/{lead_id}")
async def test_automation_for_lead(
    lead_id: str,
    db: Session = Depends(get_db)
):
    """Testa automação para um lead específico (debug)"""

    lead = db.execute(
        text("""
            SELECT l.id, l.nome, l.telefone, l.email, l.segmento,
                   l.site_url, l.plano, l.user_id, l.proximo_sequencia_dia,
                   l.sdr_stage, l.engajamento_score
            FROM leads l
            WHERE l.id = :lead_id
        """),
        {"lead_id": lead_id}
    ).fetchone()

    if not lead:
        return {"error": "Lead não encontrado"}

    tenant_id = f"fralib_user_{lead[7]}"

    from backend.services.whatsapp_automation_service import (
        AutomationConfig, SequenceStage
    )

    config = AutomationConfig(
        tenant_id=tenant_id,
        lead_id=lead[0],
        lead_name=lead[1],
        lead_phone=lead[2],
        lead_email=lead[3],
        lead_segment=lead[4] or "",
        site_url=lead[5] or "",
        plan_type=lead[6] or "trial",
        next_sequence_day=lead[8] or 1
    )

    service = get_automation_service()
    stage = service._get_current_sequence_stage(config)

    return {
        "lead_id": lead[0],
        "lead_name": lead[1],
        "current_day": lead[8] or 1,
        "current_stage": lead[9],
        "proposed_stage": stage.value if stage else None,
        "message_preview": service._get_message_template(stage, config, {}, None) if stage else None
    }