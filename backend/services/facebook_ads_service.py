"""
Facebook Ads Service
Servico para gerenciar campanhas do Facebook Ads

SEGURANCA: tokens NUNCA sao hardcoded. Devem vir de:
  1) Parametros do construtor (injetados em testes / endpoints)
  2) Env vars FB_ACCESS_TOKEN e FB_AD_ACCOUNT_ID
  3) app_settings (tabela settings do banco)
Sem credenciais validas, levantar FacebookAdsConfigError com mensagem clara.
"""
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FacebookAdsConfigError(RuntimeError):
    """Erro de configuracao: tokens ausentes."""


class FacebookAdsService:
    """Servico para gerenciar campanhas do Facebook Ads"""

    def __init__(self, access_token: str = None, ad_account_id: str = None):
        # Ordem de precedencia: arg > env > None (raise lazy)
        self.access_token = (
            access_token
            or os.getenv("FB_ACCESS_TOKEN", "").strip()
            or None
        )
        self.ad_account_id = (
            ad_account_id
            or os.getenv("FB_AD_ACCOUNT_ID", "").strip()
            or None
        )
        if not self.access_token:
            logger.warning(
                "[facebook_ads] FB_ACCESS_TOKEN ausente (defina em env ou passe ao construtor)"
            )
        if not self.ad_account_id:
            logger.warning(
                "[facebook_ads] FB_AD_ACCOUNT_ID ausente (defina em env ou passe ao construtor)"
            )
        self.api_version = "v18.0"
        self.api_base = "https://graph.facebook.com"

    def _ensure_credentials(self) -> None:
        """Garante credenciais validas antes de chamar API."""
        if not self.access_token:
            raise FacebookAdsConfigError(
                "FB_ACCESS_TOKEN ausente. Defina em env FB_ACCESS_TOKEN ou "
                "passe access_token= ao construtor."
            )
        if not self.ad_account_id:
            raise FacebookAdsConfigError(
                "FB_AD_ACCOUNT_ID ausente. Defina em env FB_AD_ACCOUNT_ID ou "
                "passe ad_account_id= ao construtor."
            )

    async def fb_get(self, endpoint: str, params: dict = None) -> dict:
        """Faz requisicao GET para a API do Facebook"""
        self._ensure_credentials()
        url = f"{self.api_base}/{self.api_version}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            return response.json()

    async def fb_post(self, endpoint: str, data: dict = None) -> dict:
        """Faz requisicao POST para a API do Facebook"""
        self._ensure_credentials()
        url = f"{self.api_base}/{self.api_version}/{endpoint}"
        data = data or {}
        data["access_token"] = self.access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=30.0)
            return response.json()

    def _safe_int(self, value):
        """Converte valor para int de forma segura"""
        try:
            if isinstance(value, list):
                return sum(int(x) for x in value if x)
            return int(value or 0)
        except:
            return 0

    def _safe_float(self, value):
        """Converte valor para float de forma segura"""
        try:
            if isinstance(value, list):
                return sum(float(x) for x in value if x)
            return float(value or 0)
        except:
            return 0.0

    # ============================================
    # STATUS DA CONTA
    # ============================================

    async def get_account_status(self) -> dict:
        """Retorna status da conta de anuncios"""
        fields = "id,name,account_status,balance,currency,timezone,spend"
        data = await self.fb_get(f"act_{self.ad_account_id}", {"fields": fields})

        return {
            "name": data.get("name", ""),
            "account_status": data.get("account_status"),
            "balance": int(data.get("balance", 0)),
            "currency": data.get("currency", "BRL"),
            "spend": float(data.get("spend", 0)),
        }

    # ============================================
    # CAMPANHAS
    # ============================================

    async def list_campaigns(self, status: str = None, limit: int = 20) -> List[dict]:
        """Lista todas as campanhas com metricas"""
        fields = "id,name,status,objective,daily_budget,created_time,start_time"
        params = {"fields": fields, "limit": limit}

        if status:
            filtering = json.dumps([
                {"field": "campaign.entity_status", "operator": "IN", "value": [status]}
            ])
            params["filtering"] = filtering

        campaigns_data = await self.fb_get(f"act_{self.ad_account_id}/campaigns", params)
        campaigns = campaigns_data.get("data", [])

        # Adicionar metricas para cada campanha
        for camp in campaigns:
            insights = await self.get_campaign_insights(camp["id"])
            if insights:
                camp.update(insights)
            else:
                camp.update({
                    "impressions": 0,
                    "clicks": 0,
                    "ctr": 0,
                    "cpc": 0,
                    "spend": 0,
                    "results": 0,
                    "cpl": 0,
                    "leads": 0,
                })

        return campaigns

    async def get_campaign_insights(self, campaign_id: str) -> Optional[dict]:
        """Retorna metricas de uma campanha"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        time_range = json.dumps({
            "since": start_date.strftime("%Y-%m-%d"),
            "until": end_date.strftime("%Y-%m-%d")
        })

        fields = "impressions,reach,clicks,ctr,cpc,spend,results,cost_per_result,frequency,cpm"
        params = {
            "fields": fields,
            "time_range": time_range,
            "level": "campaign"
        }

        try:
            data = await self.fb_get(f"act_{self.ad_account_id}/insights", params)

            if data.get("data"):
                insights = data["data"][0]
                results = self._safe_int(insights.get("results"))
                spend = self._safe_float(insights.get("spend"))
                cpl = (spend / results) if results > 0 else 0

                return {
                    "impressions": self._safe_int(insights.get("impressions")),
                    "reach": self._safe_int(insights.get("reach")),
                    "clicks": self._safe_int(insights.get("clicks")),
                    "ctr": self._safe_float(insights.get("ctr")),
                    "cpc": self._safe_float(insights.get("cpc")),
                    "spend": int(spend * 100),
                    "results": results,
                    "cpl": int(cpl * 100),
                    "leads": results,
                    "frequency": self._safe_float(insights.get("frequency")),
                }
        except Exception as e:
            logger.error(f"Erro ao buscar insights: {e}")

        return None

    async def get_campaign_details(self, campaign_id: str) -> dict:
        """Retorna detalhes de uma campanha"""
        fields = "id,name,status,objective,daily_budget,spend,start_time,stop_time"
        return await self.fb_get(campaign_id, {"fields": fields})

    # ============================================
    # ACOES
    # ============================================

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa uma campanha"""
        result = await self.fb_post(campaign_id, {"status": "PAUSED"})
        return "success" in str(result)

    async def activate_campaign(self, campaign_id: str) -> bool:
        """Ativa uma campanha"""
        result = await self.fb_post(campaign_id, {"status": "ACTIVE"})
        return "success" in str(result)

    async def update_campaign_budget(self, campaign_id: str, daily_budget: int) -> bool:
        """Atualiza orcamento de uma campanha"""
        result = await self.fb_post(campaign_id, {"daily_budget": daily_budget})
        return "success" in str(result)

    async def create_campaign(self, name: str, objective: str, daily_budget: int) -> dict:
        """Cria nova campanha"""
        data = {
            "name": name,
            "objective": objective,
            "status": "PAUSED",
            "daily_budget": daily_budget,
            "special_ad_categories": "[]"
        }

        result = await self.fb_post(f"act_{self.ad_account_id}/campaigns", data)

        if "error" in result:
            raise Exception(result["error"].get("message", "Erro desconhecido"))

        return {"id": result["id"], "name": name, "daily_budget": daily_budget}

    # ============================================
    # INSIGHTS GERAL
    # ============================================

    async def get_overall_insights(self, days: int = 7) -> dict:
        """Retorna metricas gerais da conta"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        time_range = json.dumps({
            "since": start_date.strftime("%Y-%m-%d"),
            "until": end_date.strftime("%Y-%m-%d")
        })

        params = {
            "fields": "impressions,reach,clicks,ctr,cpc,spend,results,cost_per_result",
            "time_range": time_range,
            "level": "campaign"
        }

        try:
            data = await self.fb_get(f"act_{self.ad_account_id}/insights", params)

            total_impressions = 0
            total_clicks = 0
            total_spend = 0
            total_leads = 0

            campaigns = []
            for d in data.get("data", []):
                impressions = self._safe_int(d.get("impressions"))
                clicks = self._safe_int(d.get("clicks"))
                spend = self._safe_float(d.get("spend"))
                leads = self._safe_int(d.get("results"))
                cpl = (spend / leads) if leads > 0 else 0

                total_impressions += impressions
                total_clicks += clicks
                total_spend += spend
                total_leads += leads

                campaigns.append({
                    "campaign_name": d.get("campaign_name", ""),
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": int(spend * 100),
                    "leads": leads,
                    "cpl": int(cpl * 100),
                })

            avg_cpl = (total_spend / total_leads) if total_leads > 0 else 0

            return {
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_spend": int(total_spend * 100),
                "total_leads": total_leads,
                "avg_cpl": int(avg_cpl * 100),
                "campaigns": campaigns,
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"Erro ao buscar insights: {e}")
            return {
                "total_impressions": 0,
                "total_clicks": 0,
                "total_spend": 0,
                "total_leads": 0,
                "avg_cpl": 0,
                "campaigns": [],
                "error": str(e),
            }


# Instancia global
_facebook_service: Optional[FacebookAdsService] = None


def get_facebook_service() -> FacebookAdsService:
    """Singleton lazy. Requer FB_ACCESS_TOKEN e FB_AD_ACCOUNT_ID em env.

    Se ausentes, retorna servico sem credenciais (raise lazy ao chamar API).
    """
    global _facebook_service
    if _facebook_service is None:
        _facebook_service = FacebookAdsService()
    return _facebook_service
