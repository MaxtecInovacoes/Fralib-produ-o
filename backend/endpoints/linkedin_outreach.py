"""
LinkedIn Outreach Endpoints - Prospecção Ativa

Fornece:
- Lista de prospects
- Templates de InMail
- Métricas de resposta
- Status de contato

Rotas:
- GET /api/intel/linkedin/prospects - Lista prospects
- POST /api/intel/linkedin/prospects - Adiciona prospect
- PUT /api/intel/linkedin/prospects/{id} - Atualiza status
- GET /api/intel/linkedin/templates - Templates
- POST /api/intel/linkedin/outreach - Envia mensagem
- GET /api/intel/linkedin/metrics - Métricas
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import os, sys
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.database import get_db
from backend.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intel/linkedin", tags=["linkedin-outreach"])


# ════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════════

class ProspectCreate(BaseModel):
    nome: str
    empresa: str
    cargo: str
    linkedin_url: str
    segmento: str
    cidade: str
    email: Optional[str] = None
    telefone: Optional[str] = None


class ProspectUpdate(BaseModel):
    status: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    response: Optional[str] = None
    notes: Optional[str] = None


class Template(BaseModel):
    id: str
    nome: str
    assunto: str
    corpo: str
    segmento: str
    created_at: str


class MetricData(BaseModel):
    total_prospects: int
    contacted: int
    responded: int
    converted: int
    response_rate: float
    conversion_rate: float


# ════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════

@router.get("/prospects")
async def list_prospects(
    segmento: Optional[str] = Query(None, description="Filtrar por segmento"),
    cidade: Optional[str] = Query(None, description="Filtrar por cidade"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    search: Optional[str] = Query(None, description="Buscar por nome/empresa"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista prospects do tenant.
    """
    tenant_id = user["tenant_id"]

    query = """
        SELECT id, nome, empresa, cargo, linkedin_url, segmento, cidade,
               email, telefone, status, last_contacted_at, response,
               notes, created_at, updated_at
        FROM linkedin_prospects
        WHERE tenant_id = :tid
    """
    params = {"tid": tenant_id}

    if segmento:
        query += " AND segmento ILIKE :seg"
        params["seg"] = f"%{segmento}%"

    if cidade:
        query += " AND cidade ILIKE :cid"
        params["cid"] = f"%{cidade}%"

    if status:
        query += " AND status = :stat"
        params["stat"] = status

    if search:
        query += " AND (nome ILIKE :search OR empresa ILIKE :search)"
        params["search"] = f"%{search}%"

    query += " ORDER BY created_at DESC"

    rows = db.execute(text(query), params).fetchall()

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "count": len(rows),
        "prospects": [
            {
                "id": str(r.id),
                "nome": r.nome,
                "empresa": r.empresa,
                "cargo": r.cargo,
                "linkedin_url": r.linkedin_url,
                "segmento": r.segmento,
                "cidade": r.cidade,
                "email": r.email,
                "telefone": r.telefone,
                "status": r.status,
                "last_contacted_at": r.last_contacted_at.isoformat() if r.last_contacted_at else None,
                "response": r.response,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in rows
        ]
    }


@router.post("/prospects")
async def create_prospect(
    data: ProspectCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adiciona um novo prospect."""
    tenant_id = user["tenant_id"]

    # Verifica duplicata
    exists = db.execute(text("""
        SELECT id FROM linkedin_prospects
        WHERE tenant_id = :tid AND empresa = :emp AND nome = :nome
    """), {"tid": tenant_id, "emp": data.empresa, "nome": data.nome}).fetchone()

    if exists:
        raise HTTPException(409, "Prospect já existe")

    result = db.execute(text("""
        INSERT INTO linkedin_prospects
        (tenant_id, nome, empresa, cargo, linkedin_url, segmento, cidade, email, telefone, status, created_at, updated_at)
        VALUES (:tid, :nome, :emp, :cargo, :url, :seg, :cid, :email, :tel, 'new', NOW(), NOW())
        RETURNING id
    """), {
        "tid": tenant_id,
        "nome": data.nome,
        "emp": data.empresa,
        "cargo": data.cargo,
        "url": data.linkedin_url,
        "seg": data.segmento,
        "cid": data.cidade,
        "email": data.email,
        "tel": data.telefone
    })

    prospect_id = result.fetchone()[0]
    db.commit()

    logger.info(f"[LinkedIn] Prospect created: tenant={tenant_id}, id={prospect_id}")

    return {"ok": True, "id": str(prospect_id)}


@router.put("/prospects/{prospect_id}")
async def update_prospect(
    prospect_id: str,
    data: ProspectUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza status de um prospect."""
    tenant_id = user["tenant_id"]

    # Verifica se existe
    exists = db.execute(text("""
        SELECT id FROM linkedin_prospects WHERE id = :id AND tenant_id = :tid
    """), {"id": prospect_id, "tid": tenant_id}).fetchone()

    if not exists:
        raise HTTPException(404, "Prospect não encontrado")

    # Constrói query dinâmica
    updates = []
    params = {"id": prospect_id, "tid": tenant_id}

    if data.status is not None:
        updates.append("status = :status")
        params["status"] = data.status

    if data.last_contacted_at is not None:
        updates.append("last_contacted_at = :contacted")
        params["contacted"] = data.last_contacted_at

    if data.response is not None:
        updates.append("response = :response")
        params["response"] = data.response

    if data.notes is not None:
        updates.append("notes = :notes")
        params["notes"] = data.notes

    if updates:
        updates.append("updated_at = NOW()")
        query = f"UPDATE linkedin_prospects SET {', '.join(updates)} WHERE id = :id AND tenant_id = :tid"
        db.execute(text(query), params)
        db.commit()

    return {"ok": True}


@router.post("/prospects/{prospect_id}/contact")
async def contact_prospect(
    prospect_id: str,
    message: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registra contato com prospect."""
    tenant_id = user["tenant_id"]

    # Atualiza status e timestamp
    db.execute(text("""
        UPDATE linkedin_prospects
        SET status = 'contacted', last_contacted_at = NOW(), response = :msg, updated_at = NOW()
        WHERE id = :id AND tenant_id = :tid
    """), {"id": prospect_id, "tid": tenant_id, "msg": message})

    db.commit()

    # Aqui você integraria com LinkedIn API para enviar mensagem
    # Por enquanto só registra o contato

    return {"ok": True, "message": "Contato registrado"}


@router.get("/templates")
async def get_templates(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna templates de InMail."""
    tenant_id = user["tenant_id"]

    # Templates padrão (poderiam vir de tenant_config)
    default_templates = [
        {
            "id": "cold_introduction",
            "nome": "Introdução Fria",
            "assunto": "Olá [nome], vi sua empresa no LinkedIn",
            "corpo": """Olá [nome],

Vi seu perfil no LinkedIn e fiquei impressionado com o trabalho da [empresa] em [cidade].

Sou especialista em ajudar negócios como o seu a captar mais clientes online através de sites otimizados.

Gostaria de compartilhar uma ideia rápida de como você poderia aumentar sua visibilidade?

Atenciosamente,
Seu Nome""",
            "segmento": "geral",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": "competitor_approach",
            "nome": "Abordagem por Concorrente",
            "assunto": "Uma ideia para [empresa]",
            "corpo": """Olá [nome],

Percebi que a [empresa] compete com [concorrente] no mercado de [segmento].

Fiz uma análise rápida e notei que você poderia estar perdendo oportunidades de captar clientes que buscam por [segmento] no Google.

Tenho uma solução que já ajudou vários negócios na sua região a aparecerem melhor online.

Gostaria de conversar por 5 minutos para mostrar?

Atenciosamente,
Seu Nome""",
            "segmento": "geral",
            "created_at": datetime.now().isoformat()
        }
    ]

    # Templates personalizados do tenant (se existirem)
    custom_rows = db.execute(text("""
        SELECT id, nome, assunto, corpo, segmento, created_at
        FROM linkedin_templates
        WHERE tenant_id = :tid
        ORDER BY created_at DESC
    """), {"tid": tenant_id}).fetchall()

    custom_templates = [
        {
            "id": str(r.id),
            "nome": r.nome,
            "assunto": r.assunto,
            "corpo": r.corpo,
            "segmento": r.segmento,
            "created_at": r.created_at.isoformat()
        }
        for r in custom_templates
    ]

    return {
        "ok": True,
        "templates": default_templates + custom_templates
    }


@router.post("/templates")
async def create_template(
    nome: str,
    assunto: str,
    corpo: str,
    segmento: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria template personalizado."""
    tenant_id = user["tenant_id"]

    result = db.execute(text("""
        INSERT INTO linkedin_templates
        (tenant_id, nome, assunto, corpo, segmento, created_at)
        VALUES (:tid, :nome, :assunto, :corpo, :seg, NOW())
        RETURNING id
    """), {
        "tid": tenant_id,
        "nome": nome,
        "assunto": assunto,
        "corpo": corpo,
        "seg": segmento
    })

    template_id = result.fetchone()[0]
    db.commit()

    return {"ok": True, "id": str(template_id)}


@router.get("/metrics")
async def get_metrics(
    periodo: str = Query("7d", description="Período: 7d, 30d, 90d"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna métricas de outreach."""
    tenant_id = user["tenant_id"]

    # Calcula data inicial
    if periodo == "7d":
        start_date = datetime.now() - timedelta(days=7)
    elif periodo == "30d":
        start_date = datetime.now() - timedelta(days=30)
    elif periodo == "90d":
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime.now() - timedelta(days=7)

    query = """
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'contacted' THEN 1 END) as contacted,
            COUNT(CASE WHEN status = 'responded' THEN 1 END) as responded,
            COUNT(CASE WHEN status = 'converted' THEN 1 END) as converted
        FROM linkedin_prospects
        WHERE tenant_id = :tid AND created_at >= :start_date
    """

    row = db.execute(text(query), {"tid": tenant_id, "start_date": start_date}).fetchone()

    total = row.total
    contacted = row.contacted
    responded = row.responded
    converted = row.converted

    response_rate = (responded / total * 100) if total > 0 else 0
    conversion_rate = (converted / total * 100) if total > 0 else 0

    return {
        "ok": True,
        "periodo": periodo,
        "tenant_id": tenant_id,
        "metrics": MetricData(
            total_prospects=total,
            contacted=contacted,
            responded=responded,
            converted=converted,
            response_rate=round(response_rate, 2),
            conversion_rate=round(conversion_rate, 2)
        ).dict()
    }


@router.post("/export")
async def export_prospects(
    format: str = Query("csv", description="Formato: csv, json"),
    segmento: Optional[str] = Query(None, description="Filtrar por segmento"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exporta prospects em formato CSV ou JSON."""
    tenant_id = user["tenant_id"]

    # Busca prospects
    prospects = await list_prospects(segmento=segmento, user=user, db=db)

    if format == "csv":
        # Gera CSV
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Nome", "Empresa", "Cargo", "LinkedIn", "Email", "Telefone", "Segmento", "Cidade", "Status"])

        for p in prospects["prospects"]:
            writer.writerow([
                p["nome"], p["empresa"], p["cargo"], p["linkedin_url"],
                p["email"] or "", p["telefone"] or "", p["segmento"], p["cidade"], p["status"]
            ])

        return {
            "ok": True,
            "format": "csv",
            "data": output.getvalue(),
            "filename": f"prospects_{tenant_id}.csv"
        }

    else:  # json
        return {
            "ok": True,
            "format": "json",
            "data": prospects["prospects"],
            "filename": f"prospects_{tenant_id}.json"
        }