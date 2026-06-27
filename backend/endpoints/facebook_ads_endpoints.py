"""
Facebook Ads Endpoints
Rotas para gerenciar campanhas do Facebook Ads
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.services.facebook_ads_service import get_facebook_service, FacebookAdsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/facebook-ads", tags=["Facebook Ads"])


# ============================================
# MODELS
# ============================================

class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str
    daily_budget: int
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0
    spend: int = 0
    leads: int = 0
    cpl: int = 0


class AccountStatusResponse(BaseModel):
    name: str
    account_status: int
    balance: int
    currency: str
    spend: float


class InsightsResponse(BaseModel):
    total_impressions: int
    total_clicks: int
    total_spend: int
    total_leads: int
    avg_cpl: int
    campaigns: List[dict]
    period_days: int


class ActionRequest(BaseModel):
    campaign_id: str
    campaign_name: str
    action: str
    new_value: Optional[str] = None
    reason: str = ""


# ============================================
# ENDPOINTS
# ============================================

@router.get("/status", response_model=AccountStatusResponse)
async def get_account_status():
    """Retorna status da conta de anuncios"""
    try:
        service = get_facebook_service()
        return await service.get_account_status()
    except Exception as e:
        logger.error(f"Erro ao buscar status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filtrar por status: ACTIVE, PAUSED"),
    limit: int = Query(20, le=100, description="Limite de campanhas")
):
    """Lista todas as campanhas com metricas"""
    try:
        service = get_facebook_service()
        campaigns = await service.list_campaigns(status=status, limit=limit)

        result = []
        for c in campaigns:
            result.append(CampaignResponse(
                id=c.get("id", ""),
                name=c.get("name", ""),
                status=c.get("status", ""),
                daily_budget=c.get("daily_budget", 0) or 0,
                impressions=c.get("impressions", 0),
                clicks=c.get("clicks", 0),
                ctr=c.get("ctr", 0),
                spend=c.get("spend", 0),
                leads=c.get("leads", 0),
                cpl=c.get("cpl", 0),
            ))

        return result
    except Exception as e:
        logger.error(f"Erro ao listar campanhas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Retorna detalhes de uma campanha"""
    try:
        service = get_facebook_service()
        return await service.get_campaign_details(campaign_id)
    except Exception as e:
        logger.error(f"Erro ao buscar campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(days: int = Query(7, ge=1, le=30, description="Dias para buscar")):
    """Retorna metricas gerais"""
    try:
        service = get_facebook_service()
        return await service.get_overall_insights(days=days)
    except Exception as e:
        logger.error(f"Erro ao buscar insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pausa uma campanha"""
    try:
        service = get_facebook_service()
        success = await service.pause_campaign(campaign_id)
        return {"success": success, "action": "pause", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Erro ao pausar campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/activate")
async def activate_campaign(campaign_id: str):
    """Ativa uma campanha"""
    try:
        service = get_facebook_service()
        success = await service.activate_campaign(campaign_id)
        return {"success": success, "action": "activate", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Erro ao ativar campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/budget")
async def update_budget(campaign_id: str, budget: int = Query(..., description="Novo budget em centavos")):
    """Atualiza orcamento de uma campanha"""
    try:
        service = get_facebook_service()
        success = await service.update_campaign_budget(campaign_id, budget)
        return {"success": success, "action": "update_budget", "campaign_id": campaign_id, "new_budget": budget}
    except Exception as e:
        logger.error(f"Erro ao atualizar budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/create")
async def create_campaign(
    name: str = Query(..., description="Nome da campanha"),
    objective: str = Query("OUTCOME_LEADS", description="Objetivo: OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_TRAFFIC"),
    daily_budget: int = Query(..., description="Budget diario em centavos")
):
    """Cria nova campanha"""
    try:
        service = get_facebook_service()
        result = await service.create_campaign(name, objective, daily_budget)
        return result
    except Exception as e:
        logger.error(f"Erro ao criar campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))
