"""
Competitive Intelligence Endpoints - Análise de Concorrentes

Fornece:
- Lista de concorrentes por segmento
- Battle cards
- Análise de mercado
- Scripts de objection handling

Rotas:
- GET /api/intel/competitors - Lista concorrentes
- POST /api/intel/competitors - Adiciona concorrente
- GET /api/intel/competitors/{id} - Detalhes
- PUT /api/intel/competitors/{id} - Atualiza
- DELETE /api/intel/competitors/{id} - Remove
- GET /api/intel/battle-cards - Battle cards por segmento
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import os, sys
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intel/competitors", tags=["competitive-intelligence"])


# ════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════════

class CompetitorCreate(BaseModel):
    segmento: str
    nome: str
    site_url: Optional[str] = ""
    pricing: Optional[str] = ""
    strengths: Optional[str] = ""
    weaknesses: Optional[str] = ""
    battle_card: Optional[str] = ""
    source: str = "manual"


class CompetitorUpdate(BaseModel):
    nome: Optional[str] = None
    site_url: Optional[str] = None
    pricing: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    battle_card: Optional[str] = None


class BattleCard(BaseModel):
    segmento: str
    concorrentes: list[str]
    nosso_diferencial: str
    scripts: dict[str, str]  # "objection": "response"


# ════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════

@router.get("")
async def list_competitors(
    segmento: Optional[str] = Query(None, description="Filtrar por segmento"),
    search: Optional[str] = Query(None, description="Buscar por nome"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista concorrentes do tenant.
    Se segmento for passado, filtra. Se não, retorna todos.
    """
    tenant_id = user["tenant_id"]

    query = """
        SELECT id, segmento, nome, site_url, pricing,
               strengths, weaknesses, battle_card, source, created_at
        FROM competitor_intel
        WHERE tenant_id = :tid
    """
    params = {"tid": tenant_id}

    if segmento:
        query += " AND segmento ILIKE :seg"
        params["seg"] = f"%{segmento}%"

    if search:
        query += " AND nome ILIKE :search"
        params["search"] = f"%{search}%"

    query += " ORDER BY created_at DESC"

    rows = db.execute(text(query), params).fetchall()

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "count": len(rows),
        "competitors": [
            {
                "id": str(r.id),
                "segmento": r.segmento,
                "nome": r.nome,
                "site_url": r.site_url,
                "pricing": r.pricing,
                "strengths": r.strengths,
                "weaknesses": r.weaknesses,
                "battle_card": r.battle_card,
                "source": r.source,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in rows
        ]
    }


@router.post("")
async def create_competitor(
    data: CompetitorCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adiciona um novo concorrente."""
    tenant_id = user["tenant_id"]

    result = db.execute(text("""
        INSERT INTO competitor_intel
        (tenant_id, segmento, nome, site_url, pricing, strengths, weaknesses, battle_card, source, created_at)
        VALUES (:tid, :seg, :nome, :url, :pricing, :str, :weak, :bc, :src, NOW())
        RETURNING id
    """), {
        "tid": tenant_id,
        "seg": data.segmento,
        "nome": data.nome,
        "url": data.site_url or "",
        "pricing": data.pricing or "",
        "str": data.strengths or "",
        "weak": data.weaknesses or "",
        "bc": data.battle_card or "",
        "src": data.source
    })

    competitor_id = result.fetchone()[0]
    db.commit()

    logger.info(f"[Competitor] Created: tenant={tenant_id}, id={competitor_id}")

    return {"ok": True, "id": str(competitor_id)}


@router.get("/{competitor_id}")
async def get_competitor(
    competitor_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca detalhes de um concorrente."""
    tenant_id = user["tenant_id"]

    row = db.execute(text("""
        SELECT id, segmento, nome, site_url, pricing,
               strengths, weaknesses, battle_card, source, created_at
        FROM competitor_intel
        WHERE id = :id AND tenant_id = :tid
    """), {"id": competitor_id, "tid": tenant_id}).fetchone()

    if not row:
        raise HTTPException(404, "Concorrente não encontrado")

    return {
        "ok": True,
        "competitor": {
            "id": str(row.id),
            "segmento": row.segmento,
            "nome": row.nome,
            "site_url": row.site_url,
            "pricing": row.pricing,
            "strengths": row.strengths,
            "weaknesses": row.weaknesses,
            "battle_card": row.battle_card,
            "source": row.source,
            "created_at": row.created_at.isoformat() if row.created_at else None
        }
    }


@router.put("/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    data: CompetitorUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza um concorrente."""
    tenant_id = user["tenant_id"]

    # Verifica se existe
    exists = db.execute(text("""
        SELECT id FROM competitor_intel WHERE id = :id AND tenant_id = :tid
    """), {"id": competitor_id, "tid": tenant_id}).fetchone()

    if not exists:
        raise HTTPException(404, "Concorrente não encontrado")

    # Constrói query dinâmica
    updates = []
    params = {"id": competitor_id, "tid": tenant_id}

    if data.nome is not None:
        updates.append("nome = :nome")
        params["nome"] = data.nome
    if data.site_url is not None:
        updates.append("site_url = :url")
        params["url"] = data.site_url
    if data.pricing is not None:
        updates.append("pricing = :pricing")
        params["pricing"] = data.pricing
    if data.strengths is not None:
        updates.append("strengths = :str")
        params["str"] = data.strengths
    if data.weaknesses is not None:
        updates.append("weaknesses = :weak")
        params["weak"] = data.weaknesses
    if data.battle_card is not None:
        updates.append("battle_card = :bc")
        params["bc"] = data.battle_card

    if updates:
        query = f"UPDATE competitor_intel SET {', '.join(updates)} WHERE id = :id AND tenant_id = :tid"
        db.execute(text(query), params)
        db.commit()

    return {"ok": True}


@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove um concorrente."""
    tenant_id = user["tenant_id"]

    result = db.execute(text("""
        DELETE FROM competitor_intel WHERE id = :id AND tenant_id = :tid
        RETURNING id
    """), {"id": competitor_id, "tid": tenant_id})

    deleted = result.fetchone()

    if not deleted:
        raise HTTPException(404, "Concorrente não encontrado")

    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════
# BATTLE CARDS (agregados por segmento)
# ════════════════════════════════════════════════════════════════════

@router.get("/battle-cards/summary")
async def get_battle_cards_summary(
    segmento: Optional[str] = Query(None, description="Filtrar por segmento"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna battle cards agregados por segmento.
    Útil para o SDR usar quando encontrar um concorrente.
    """
    tenant_id = user["tenant_id"]

    query = """
        SELECT segmento,
               json_agg(json_build_object(
                   'nome', nome,
                   'pricing', pricing,
                   'strengths', strengths,
                   'weaknesses', weaknesses,
                   'battle_card', battle_card
               )) as concorrentes
        FROM competitor_intel
        WHERE tenant_id = :tid
    """
    params = {"tid": tenant_id}

    if segmento:
        query += " AND segmento ILIKE :seg"
        params["seg"] = f"%{segmento}%"

    query += " GROUP BY segmento"

    rows = db.execute(text(query), params).fetchall()

    # Scripts padrão por tipo de objeção
    default_scripts = {
        "preco": "Entendo a preocupação com preço. Nosso modelo é diferente: você só paga depois de aprovar o site. E o investimento é menor que manter um site tradicional.",
        "tempo": "O site fica pronto em poucos dias. E você pode ir ajustando durante o processo.",
        "nao_preciso": "A maioria dos negócios na sua região já tem um site. Seus clientes estão te encontrando nos concorrentes.",
        "tenho_facebook": "Ótimo que já está online! Mas o Facebook não substitui um site próprio. Você não controla o que aparece no Google."
    }

    return {
        "ok": True,
        "battle_cards": [
            {
                "segmento": row.segmento,
                "concorrentes": row.concorrentes,
                "scripts": default_scripts
            }
            for row in rows
        ]
    }
