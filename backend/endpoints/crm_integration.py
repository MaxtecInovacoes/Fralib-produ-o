"""
CRM Integration Endpoints - Sincronização com CRMs externos

Suporta:
- Salesforce
- HubSpot

Rotas:
- GET /api/crm/config - Configuração atual
- POST /api/crm/config - Configurar CRM
- DELETE /api/crm/config - Remover configuração
- POST /api/crm/sync/{lead_id} - Sincronizar lead
- GET /api/crm/sync/history - Histórico de sincronizações
- GET /api/crm/sync/stats - Estatísticas
- POST /api/crm/test - Testar conexão
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import os, sys
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))

import requests
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crm", tags=["crm-integration"])


# ════════════════════════════════════════════════════════════════════
# CRIPTOGRAFIA PARA CREDENCIAIS
# ════════════════════════════════════════════════════════════════════

def _get_encryption_key() -> bytes:
    """Gera ou recupera chave de criptografia."""
    key_env = os.getenv("FRALIB_CRM_ENCRYPTION_KEY")
    if key_env:
        return base64.urlsafe_b64decode(key_env)
    # Fallback: usa hash de secret do ambiente
    secret = os.getenv("SECRET_KEY", "fralib-default-secret")
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def _encrypt(data: str) -> str:
    """Criptografa string."""
    if not data:
        return ""
    key = _get_encryption_key()
    f = Fernet(key)
    return base64.urlsafe_b64encode(f.encrypt(data.encode())).decode()


def _decrypt(data: str) -> str:
    """Descriptografa string."""
    if not data:
        return ""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.decrypt(base64.urlsafe_b64decode(data.encode())).decode()


# ════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════════

class CRMConfig(BaseModel):
    crm_type: str  # "salesforce" ou "hubspot"
    api_key: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    instance_url: Optional[str] = None
    webhook_url: Optional[str] = None


class CRMTestResult(BaseModel):
    connected: bool
    message: str
    account_name: Optional[str] = None


class SyncResult(BaseModel):
    sync_id: str
    crm_id: str
    status: str
    message: str


# ════════════════════════════════════════════════════════════════════
# CRM CLIENTS
# ════════════════════════════════════════════════════════════════════

class SalesforceClient:
    """Client para Salesforce REST API."""

    def __init__(self, instance_url: str, access_token: str):
        self.instance_url = instance_url.rstrip("/")
        self.access_token = access_token
        self.api_version = "v58.0"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> dict:
        """Testa conexão com Salesforce."""
        url = f"{self.instance_url}/services/data/{self.api_version}/limits"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        if resp.ok:
            return {"connected": True, "message": "Conectado ao Salesforce"}
        return {"connected": False, "message": resp.text}

    def create_lead(self, lead_data: dict) -> dict:
        """Cria Lead no Salesforce."""
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Lead"

        sf_lead = {
            "FirstName": lead_data.get("nome", "").split()[0],
            "LastName": " ".join(lead_data.get("nome", "").split()[1:]) or lead_data.get("nome", ""),
            "Company": lead_data.get("empresa", "Individual"),
            "Title": lead_data.get("cargo", ""),
            "Email": lead_data.get("email", ""),
            "Phone": lead_data.get("telefone", ""),
            "City": lead_data.get("cidade", ""),
            "Description": f"Segmento: {lead_data.get('segmento', '')}\n"
                           f"Stage: {lead_data.get('stage', '')}\n"
                           f"SDR Notes: {lead_data.get('notes', '')}",
            "LeadSource": "FraLib SDR"
        }

        resp = requests.post(url, headers=self._headers(), json=sf_lead, timeout=10)

        if resp.ok:
            result = resp.json()
            return {"success": True, "id": result.get("id")}
        return {"success": False, "error": resp.text}

    def update_lead(self, crm_id: str, lead_data: dict) -> dict:
        """Atualiza Lead no Salesforce."""
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Lead/{crm_id}"

        sf_lead = {
            "Description": f"Segmento: {lead_data.get('segmento', '')}\n"
                           f"Stage: {lead_data.get('stage', '')}\n"
                           f"SDR Notes: {lead_data.get('notes', '')}",
            "Status": _map_stage_to_sf_status(lead_data.get("stage", ""))
        }

        resp = requests.patch(url, headers=self._headers(), json=sf_lead, timeout=10)

        if resp.ok:
            return {"success": True}
        return {"success": False, "error": resp.text}


class HubSpotClient:
    """Client para HubSpot CRM API v3."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.hubapi.com"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> dict:
        """Testa conexão com HubSpot."""
        url = f"{self.base_url}/account-info/v3/details"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        if resp.ok:
            data = resp.json()
            return {
                "connected": True,
                "message": "Conectado ao HubSpot",
                "account_name": data.get("accountName", "")
            }
        return {"connected": False, "message": resp.text}

    def create_contact(self, lead_data: dict) -> dict:
        """Cria Contact no HubSpot."""
        url = f"{self.base_url}/crm/v3/objects/contacts"

        properties = {
            "firstname": lead_data.get("nome", "").split()[0],
            "lastname": " ".join(lead_data.get("nome", "").split()[1:]) or lead_data.get("nome", ""),
            "company": lead_data.get("empresa", "Individual"),
            "jobtitle": lead_data.get("cargo", ""),
            "email": lead_data.get("email", ""),
            "phone": lead_data.get("telefone", ""),
            "city": lead_data.get("cidade", ""),
            "segmento": lead_data.get("segmento", ""),
            "hs_lead_status": _map_stage_to_hubspot_status(lead_data.get("stage", "")),
            "description": lead_data.get("notes", "")
        }

        resp = requests.post(url, headers=self._headers(), json={"properties": properties}, timeout=10)

        if resp.ok:
            result = resp.json()
            return {"success": True, "id": result.get("id")}
        return {"success": False, "error": resp.text}

    def update_contact(self, crm_id: str, lead_data: dict) -> dict:
        """Atualiza Contact no HubSpot."""
        url = f"{self.base_url}/crm/v3/objects/contacts/{crm_id}"

        properties = {
            "hs_lead_status": _map_stage_to_hubspot_status(lead_data.get("stage", "")),
            "description": lead_data.get("notes", "")
        }

        resp = requests.patch(url, headers=self._headers(), json={"properties": properties}, timeout=10)

        if resp.ok:
            return {"success": True}
        return {"success": False, "error": resp.text}


def _map_stage_to_sf_status(stage: str) -> str:
    """Mapeia stage do FraLib para status do Salesforce."""
    mapping = {
        "hook": "New",
        "qualify": "Working",
        "pain": "Working",
        "amplify": "Working",
        "tease": "Working",
        "proof": "Nurturing",
        "reveal": "Nurturing",
        "feedback": "Nurturing",
        "close": "Closed - Won",
        "won": "Closed - Won",
        "lost": "Closed - Lost"
    }
    return mapping.get(stage, "New")


def _map_stage_to_hubspot_status(stage: str) -> str:
    """Mapeia stage do FraLib para status do HubSpot."""
    mapping = {
        "hook": "NEW",
        "qualify": "IN_PROGRESS",
        "pain": "IN_PROGRESS",
        "amplify": "IN_PROGRESS",
        "tease": "IN_PROGRESS",
        "proof": "OPEN",
        "reveal": "OPEN",
        "feedback": "SUBMITTED_TO_DECISION_MAKER",
        "close": "CLOSED_WON",
        "won": "CLOSED_WON",
        "lost": "CLOSED_LOST"
    }
    return mapping.get(stage, "NEW")


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def _get_crm_config(db, tenant_id: int) -> Optional[dict]:
    """Busca configuração CRM do tenant."""
    row = db.execute(text("""
        SELECT crm_type, api_key_encrypted, access_token_encrypted,
               refresh_token_encrypted, instance_url, webhook_url, last_sync_at
        FROM crm_configs
        WHERE tenant_id = :tid
    """), {"tid": tenant_id}).fetchone()

    if not row:
        return None

    return {
        "crm_type": row.crm_type,
        "api_key": _decrypt(row.api_key_encrypted) if row.api_key_encrypted else None,
        "access_token": _decrypt(row.access_token_encrypted) if row.access_token_encrypted else None,
        "refresh_token": _decrypt(row.refresh_token_encrypted) if row.refresh_token_encrypted else None,
        "instance_url": row.instance_url,
        "webhook_url": row.webhook_url,
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None
    }


def _save_crm_config(db, tenant_id: int, config: CRMConfig) -> None:
    """Salva configuração CRM do tenant."""
    db.execute(text("""
        INSERT INTO crm_configs
        (tenant_id, crm_type, api_key_encrypted, access_token_encrypted,
         refresh_token_encrypted, instance_url, webhook_url, updated_at)
        VALUES (:tid, :type, :api, :access, :refresh, :url, :webhook, NOW())
        ON CONFLICT (tenant_id) DO UPDATE SET
            crm_type = EXCLUDED.crm_type,
            api_key_encrypted = EXCLUDED.api_key_encrypted,
            access_token_encrypted = EXCLUDED.access_token_encrypted,
            refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
            instance_url = EXCLUDED.instance_url,
            webhook_url = EXCLUDED.webhook_url,
            updated_at = NOW()
    """), {
        "tid": tenant_id,
        "type": config.crm_type,
        "api": _encrypt(config.api_key) if config.api_key else None,
        "access": _encrypt(config.access_token) if config.access_token else None,
        "refresh": _encrypt(config.refresh_token) if config.refresh_token else None,
        "url": config.instance_url,
        "webhook": config.webhook_url
    })
    db.commit()


# ════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════

@router.get("/config")
async def get_crm_config_endpoint(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna configuração CRM do tenant."""
    tenant_id = user["tenant_id"]
    config = _get_crm_config(db, tenant_id)

    if not config:
        return {
            "ok": True,
            "configured": False,
            "crm_type": None,
            "message": "Nenhum CRM configurado"
        }

    # Remove dados sensíveis da resposta
    safe_config = {
        "configured": True,
        "crm_type": config["crm_type"],
        "instance_url": config.get("instance_url"),
        "webhook_url": config.get("webhook_url"),
        "last_sync_at": config.get("last_sync_at"),
        "has_api_key": bool(config.get("api_key")),
        "has_access_token": bool(config.get("access_token"))
    }

    return {"ok": True, **safe_config}


@router.post("/config")
async def save_crm_config(
    config: CRMConfig,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Salva configuração CRM do tenant."""
    tenant_id = user["tenant_id"]

    if config.crm_type not in ("salesforce", "hubspot"):
        raise HTTPException(400, "CRM deve ser 'salesforce' ou 'hubspot'")

    _save_crm_config(db, tenant_id, config)

    logger.info(f"[CRM] Config saved: tenant={tenant_id}, crm={config.crm_type}")

    return {"ok": True, "message": f"CRM {config.crm_type} configurado com sucesso"}


@router.delete("/config")
async def delete_crm_config(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove configuração CRM do tenant."""
    tenant_id = user["tenant_id"]

    db.execute(text("DELETE FROM crm_configs WHERE tenant_id = :tid"), {"tid": tenant_id})
    db.commit()

    logger.info(f"[CRM] Config deleted: tenant={tenant_id}")

    return {"ok": True, "message": "Configuração CRM removida"}


@router.post("/test")
async def test_crm_connection(
    config: CRMConfig,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Testa conexão com CRM."""
    try:
        if config.crm_type == "salesforce":
            client = SalesforceClient(
                instance_url=config.instance_url or "",
                access_token=config.access_token or ""
            )
        elif config.crm_type == "hubspot":
            client = HubSpotClient(access_token=config.access_token or "")
        else:
            raise HTTPException(400, "CRM não suportado")

        result = client.test_connection()
        return CRMTestResult(**result).dict()

    except Exception as e:
        logger.error(f"[CRM] Test failed: {e}")
        return CRMTestResult(
            connected=False,
            message=f"Erro ao testar conexão: {str(e)}"
        ).dict()


@router.post("/sync/{lead_id}")
async def sync_lead_to_crm(
    lead_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sincroniza lead para CRM."""
    tenant_id = user["tenant_id"]

    # Busca configuração
    config = _get_crm_config(db, tenant_id)
    if not config or not config.get("access_token"):
        raise HTTPException(400, "CRM não configurado ou sem access token")

    # Busca lead
    lead = db.execute(text("""
        SELECT id, nome, empresa, cargo, email, telefone, cidade,
               segmento, stage, status, notas, created_at
        FROM leads
        WHERE id = :lid AND user_id = :tid
    """), {"lid": lead_id, "tid": tenant_id}).fetchone()

    if not lead:
        raise HTTPException(404, "Lead não encontrado")

    # Prepara dados
    lead_data = {
        "nome": lead.nome or "",
        "empresa": lead.empresa or "",
        "cargo": lead.cargo or "",
        "email": lead.email or "",
        "telefone": lead.telefone or "",
        "cidade": lead.cidade or "",
        "segmento": lead.segmento or "",
        "stage": lead.stage or "hook",
        "notes": lead.notas or ""
    }

    # Verifica se já foi sincronizado
    existing_sync = db.execute(text("""
        SELECT crm_id, crm_type FROM crm_sync_history
        WHERE tenant_id = :tid AND lead_id = :lid
        ORDER BY synced_at DESC LIMIT 1
    """), {"tid": tenant_id, "lid": lead_id}).fetchone()

    try:
        if config["crm_type"] == "salesforce":
            client = SalesforceClient(
                instance_url=config["instance_url"] or "",
                access_token=config["access_token"] or ""
            )
        else:
            client = HubSpotClient(access_token=config["access_token"] or "")

        if existing_sync:
            # Update
            if config["crm_type"] == "salesforce":
                result = client.update_lead(existing_sync.crm_id, lead_data)
            else:
                result = client.update_contact(existing_sync.crm_id, lead_data)
            crm_id = existing_sync.crm_id
        else:
            # Create
            if config["crm_type"] == "salesforce":
                result = client.create_lead(lead_data)
            else:
                result = client.create_contact(lead_data)
            crm_id = result.get("id", "")

        if result.get("success"):
            # Registra sincronização
            db.execute(text("""
                INSERT INTO crm_sync_history
                (tenant_id, lead_id, crm_type, crm_lead_id, status, synced_at)
                VALUES (:tid, :lid, :type, :cid, 'success', NOW())
            """), {
                "tid": tenant_id,
                "lid": lead_id,
                "type": config["crm_type"],
                "cid": crm_id
            })

            # Atualiza last_sync_at
            db.execute(text("""
                UPDATE crm_configs SET last_sync_at = NOW() WHERE tenant_id = :tid
            """), {"tid": tenant_id})

            db.commit()

            return SyncResult(
                sync_id=lead_id,
                crm_id=crm_id,
                status="success",
                message="Lead sincronizado com sucesso"
            ).dict()

        raise HTTPException(500, result.get("error", "Erro desconhecido"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CRM] Sync failed: {e}")

        # Registra falha
        db.execute(text("""
            INSERT INTO crm_sync_history
            (tenant_id, lead_id, crm_type, crm_lead_id, status, synced_at)
            VALUES (:tid, :lid, :type, '', 'failed', NOW())
        """), {"tid": tenant_id, "lid": lead_id, "type": config["crm_type"]})
        db.commit()

        return SyncResult(
            sync_id=lead_id,
            crm_id="",
            status="failed",
            message=str(e)
        ).dict()


@router.get("/sync/history")
async def get_sync_history(
    periodo: str = Query("30d", description="Período: 7d, 30d, 90d"),
    limit: int = Query(50, description="Limite de registros"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna histórico de sincronizações."""
    tenant_id = user["tenant_id"]

    # Calcula data inicial
    if periodo == "7d":
        start_date = datetime.now() - timedelta(days=7)
    elif periodo == "90d":
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime.now() - timedelta(days=30)

    rows = db.execute(text("""
        SELECT h.id, h.lead_id, h.crm_type, h.crm_lead_id, h.status, h.synced_at,
               l.nome as lead_nome, l.email as lead_email
        FROM crm_sync_history h
        LEFT JOIN leads l ON l.id = h.lead_id
        WHERE h.tenant_id = :tid AND h.synced_at >= :start_date
        ORDER BY h.synced_at DESC
        LIMIT :limit
    """), {"tid": tenant_id, "start_date": start_date, "limit": limit}).fetchall()

    return {
        "ok": True,
        "periodo": periodo,
        "count": len(rows),
        "history": [
            {
                "id": str(r.id),
                "lead_id": str(r.lead_id),
                "lead_nome": r.lead_nome,
                "lead_email": r.lead_email,
                "crm_type": r.crm_type,
                "crm_id": r.crm_lead_id,
                "status": r.status,
                "synced_at": r.synced_at.isoformat() if r.synced_at else None
            }
            for r in rows
        ]
    }


@router.get("/sync/stats")
async def get_sync_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas de sincronização."""
    tenant_id = user["tenant_id"]

    # Stats gerais
    row = db.execute(text("""
        SELECT
            COUNT(*) as total_syncs,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as successes,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failures,
            MAX(synced_at) as last_sync
        FROM crm_sync_history
        WHERE tenant_id = :tid
    """), {"tid": tenant_id}).fetchone()

    # Leads syncados vs total
    leads_row = db.execute(text("""
        SELECT
            COUNT(*) as total_leads,
            COUNT(DISTINCT lead_id) as synced_leads
        FROM crm_sync_history
        WHERE tenant_id = :tid AND status = 'success'
    """), {"tid": tenant_id}).fetchone()

    return {
        "ok": True,
        "total_syncs": row.total_syncs,
        "successes": row.successes,
        "failures": row.failures,
        "success_rate": round(row.successes / row.total_syncs * 100, 1) if row.total_syncs > 0 else 0,
        "total_leads": leads_row.total_leads,
        "synced_leads": leads_row.synced_leads,
        "last_sync": row.last_sync.isoformat() if row.last_sync else None
    }
