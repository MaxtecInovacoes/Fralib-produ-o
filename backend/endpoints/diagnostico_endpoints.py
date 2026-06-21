"""
diagnostico_endpoints.py
==========================
Endpoints para diagnostico didatico de falhas.

GET /api/diagnostico/{falha_id}   - Explica UMA falha
GET /api/diagnostico/resumo      - Resumo das ultimas 20 falhas diagnosticadas
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.services.error_diagnostics import diagnosticar, diagnosticar_em_lote

router = APIRouter(prefix="/api/diagnostico", tags=["diagnostico"])


@router.get("/{falha_id}")
async def diagnostico_falha(
    falha_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Retorna explicacao didatica de uma falha especifica."""
    tenant_id = int(user["id"])

    row = db.execute(
        text("""
            SELECT id, tenant_id, lead_id, lead_nome, fase, mensagem_amigavel,
                   erro_tecnico, tentativas_automaticas, criado_em
            FROM pipeline_failures
            WHERE id = :fid AND tenant_id = :tid
        """),
        {"fid": falha_id, "tid": tenant_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Falha nao encontrada")

    erro_tecnico = row[5] or ""
    fase = row[3]
    diag = diagnosticar(erro_tecnico, fase)

    return {
        "falha_id": row[0],
        "lead_id": row[2],
        "lead_nome": row[3],
        "fase": fase,
        "mensagem_amigavel": row[4],
        "erro_tecnico": erro_tecnico[:500],
        "tentativas": row[6],
        "criado_em": row[7].isoformat() if row[7] else None,
        "diagnostico": diag,
    }


@router.get("")
async def diagnostico_resumo(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Resumo das ultimas falhas diagnosticadas."""
    tenant_id = int(user["id"])

    rows = db.execute(
        text("""
            SELECT id, lead_nome, fase, mensagem_amigavel, erro_tecnico,
                   tentativas_automaticas, criado_em
            FROM pipeline_failures
            WHERE tenant_id = :tid AND resolvido = FALSE
            ORDER BY criado_em DESC
            LIMIT :lim
        """),
        {"tid": tenant_id, "lim": min(limit, 100)},
    ).fetchall()

    erros = [
        {
            "id": r[0],
            "lead_nome": r[1],
            "fase": r[2],
            "mensagem_amigavel": r[3],
            "erro_tecnico": r[4],
            "tentativas": r[5],
            "criado_em": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]

    # Aplica diagnostico em lote
    erros_com_diag = diagnosticar_em_lote(erros)

    return {
        "tenant_id": tenant_id,
        "total": len(erros_com_diag),
        "falhas": erros_com_diag,
    }