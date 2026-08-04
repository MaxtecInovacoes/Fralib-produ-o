"""Rotas CRUD do pipeline: ciclos, fila, status, reprocessar, fila-reprocessamento."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from auth import get_current_user
from sse_endpoints import adicionar_log

from pipeline_execution import (
    executar_pipeline_lead_existente,
    validar_permissao_pipeline,
    FraLibState,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/ciclos")
async def get_ciclos(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Lista ciclos do tenant."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    ciclos = db.execute(text(
        "SELECT id, nome, status, criado_em, atualizado_em FROM ciclos WHERE user_id=:uid ORDER BY criado_em DESC"
    ), {"uid": tenant_id}).fetchall()
    return {"ciclos": [dict(c._mapping) for c in ciclos]}


@router.get("/fila")
async def get_fila_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Status da fila de pipeline com leads capturados."""
    from database import get_pipeline_state
    tenant_id = usuario.get("tenant_id", usuario["id"])
    pipeline_state = get_pipeline_state(db, tenant_id)
    leads_capturados = db.execute(text(
        "SELECT id, nome, score FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 20"
    ), {"uid": tenant_id}).fetchall()

    return {
        "rodando": pipeline_state.get("rodando", False),
        "pausado": pipeline_state.get("pausado", False),
        "fase": pipeline_state.get("fase", "idle"),
        "total_leads": len(leads_capturados),
        "leads": [dict(l._mapping) for l in leads_capturados],
        "erro": pipeline_state.get("erro"),
    }


@router.get("/status")
async def get_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Status resumido do pipeline."""
    from database import get_pipeline_state
    tenant_id = usuario.get("tenant_id", usuario["id"])
    pipeline_state = get_pipeline_state(db, tenant_id)
    return {
        "rodando": pipeline_state.get("rodando", False),
        "pausado": pipeline_state.get("pausado", False),
        "fase": pipeline_state.get("fase", "idle"),
        "erro": pipeline_state.get("erro"),
        "total_leads": pipeline_state.get("total_leads", 0),
        "leads_processados": pipeline_state.get("leads_processados", 0),
        "progresso": round(pipeline_state.get("leads_processados", 0) / max(pipeline_state.get("total_leads", 1), 1) * 100),
    }


@router.post("/reprocessar/{lead_id}")
async def reprocessar_lead(
    lead_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
    forcar_renovacao: bool = False,
):
    """Marca lead para reprocessamento (pula hunter, usa dados existentes)."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    _perm = validar_permissao_pipeline(db, tenant_id)
    if not _perm["allowed"]:
        _status = 429 if _perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=_status, detail=_perm)

    lead = db.execute(
        text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
        {"id": lead_id, "uid": tenant_id}
    ).fetchone()
    if not lead:
        raise HTTPException(404, "Lead nao encontrado")

    db.execute(text(
        "UPDATE leads SET status='capturado', processado=false, atualizado_em=:ts WHERE id=:id AND user_id=:uid"
    ), {"ts": datetime.now().isoformat(), "id": lead_id, "uid": tenant_id})
    db.commit()

    _renovacao_label = " (renovacao forcada)" if forcar_renovacao else ""
    adicionar_log(f"Lead {lead.nome} reprocessando{_renovacao_label}...", "info", user_id=tenant_id)

    import job_queue as _jq
    config_reproc = {
        "segmento": lead.segmento or "", "cidade": lead.cidade or "",
        "quantidade": 1, "_lead_id_existente": lead_id,
        "_forcar_renovacao": forcar_renovacao,
    }
    try:
        job_id = _jq.enqueue(db, tipo="pipeline_lead", payload={**config_reproc}, tenant_id=tenant_id, max_attempts=3, priority=1)
        if job_id:
            adicionar_log(f"[Pipeline] Reprocessamento enfileirado (job #{job_id})", "info", user_id=tenant_id)
        else:
            background_tasks.add_task(executar_pipeline_lead_existente, lead_id, tenant_id, forcar_renovacao=forcar_renovacao)
    except Exception as _e:
        print(f"[Reprocessar] Enqueue falhou: {_e}")
        background_tasks.add_task(executar_pipeline_lead_existente, lead_id, tenant_id, forcar_renovacao=forcar_renovacao)

    return {"ok": True, "mensagem": "Lead marcado para reprocessamento"}


@router.get("/fila-reprocessamento")
async def fila_reprocessamento(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Lista leads capturados aguardando reprocessamento."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    leads = db.execute(text(
        "SELECT id, nome, cidade, segmento, rating, score, tier FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY criado_em DESC"
    ), {"uid": tenant_id}).fetchall()
    return {"leads": [dict(r._mapping) for r in leads], "total": len(leads)}
