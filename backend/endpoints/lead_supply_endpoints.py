from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.services.lead_supply_engine import lead_supply_engine as supply
from backend.services.credits_manager import validar_permissao_pipeline


router = APIRouter(prefix="/api/lead-supply", tags=["lead-supply"])


def _tenant_id(usuario: dict) -> int:
    return int(usuario.get("tenant_id", usuario["id"]))


def _permission_or_error(db: Session, tenant_id: int) -> dict:
    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm.get("allowed"):
        status_code = 429 if perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=status_code, detail=perm)
    return perm


@router.get("/status")
async def get_lead_supply_status(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    data = supply.status(db, tenant_id)
    data["permission"] = validar_permissao_pipeline(db, tenant_id)
    return data


@router.get("/config")
async def get_lead_supply_config(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    return {"config": supply.get_or_create_config(db, _tenant_id(usuario))}


@router.post("/config")
async def save_lead_supply_config(
    request: Request,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    tenant_id = _tenant_id(usuario)
    cfg = supply.save_config(db, tenant_id, payload)
    if validar_permissao_pipeline(db, tenant_id).get("allowed"):
        supply.sync_supply(db, tenant_id)
    return {"ok": True, "config": cfg}


@router.post("/pause")
async def pause_lead_supply(
    request: Request,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    tenant_id = _tenant_id(usuario)
    cfg = supply.set_pause(
        db,
        tenant_id,
        hunter=payload.get("hunter_pausado") if "hunter_pausado" in payload else None,
        production=payload.get("producao_pausada") if "producao_pausada" in payload else None,
        active=payload.get("ativo") if "ativo" in payload else None,
    )
    supply.sync_supply(db, tenant_id)
    return {"ok": True, "config": cfg}


@router.post("/start")
async def start_lead_supply(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    _permission_or_error(db, tenant_id)
    cfg = supply.set_pause(db, tenant_id, hunter=False, production=False, active=True)
    supply.enqueue_hunter(db, tenant_id, delay_seconds=1, force=True)
    immediate = supply.run_production_tick(db, {"reason": "start-inline"}, tenant_id)
    should_enqueue_tick = not (
        immediate.get("job_id")
        or immediate.get("duplicate_job")
        or immediate.get("waiting") == "pipeline_running"
        or immediate.get("cooldown")
    )
    tick_job_id = None
    if should_enqueue_tick:
        tick_job_id = supply.enqueue_production_tick(db, tenant_id, delay_seconds=2, reason="start")
    return {
        "ok": True,
        "config": cfg,
        "immediate": immediate,
        "job_id": immediate.get("job_id"),
        "tick_job_id": tick_job_id,
    }


@router.post("/refill")
async def refill_lead_supply(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    _permission_or_error(db, tenant_id)
    job_id = supply.enqueue_hunter(db, tenant_id, delay_seconds=1, force=True)
    return {"ok": True, "job_id": job_id}


@router.post("/production/tick")
async def tick_lead_production(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    _permission_or_error(db, tenant_id)
    immediate = supply.run_production_tick(db, {"reason": "manual-inline"}, tenant_id)
    should_enqueue_tick = not (
        immediate.get("job_id")
        or immediate.get("duplicate_job")
        or immediate.get("waiting") == "pipeline_running"
        or immediate.get("cooldown")
    )
    tick_job_id = None
    if should_enqueue_tick:
        tick_job_id = supply.enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="manual")
    return {
        "ok": True,
        "immediate": immediate,
        "job_id": immediate.get("job_id"),
        "tick_job_id": tick_job_id,
        "duplicate_job": immediate.get("duplicate_job"),
        "waiting": immediate.get("waiting"),
        "cooldown": immediate.get("cooldown"),
    }


@router.post("/leads/{inventory_id}/discard")
async def discard_inventory_lead(
    inventory_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    from sqlalchemy import text

    tenant_id = _tenant_id(usuario)
    supply.ensure_schema(db)
    result = db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status='discarded', erro='Descartado manualmente pelo usuário',
                locked_by=NULL, locked_until=NULL, atualizado_em=NOW()
            WHERE id=:id AND tenant_id=:uid
            """
        ),
        {"id": inventory_id, "uid": tenant_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Lead não encontrado")
    supply.sync_supply(db, tenant_id)
    return {"ok": True}


@router.post("/leads/{inventory_id}/retry")
async def retry_inventory_lead(
    inventory_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    from sqlalchemy import text

    tenant_id = _tenant_id(usuario)
    supply.ensure_schema(db)
    result = db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status='approved', erro=NULL, locked_by=NULL, locked_until=NULL,
                atualizado_em=NOW()
            WHERE id=:id AND tenant_id=:uid
              AND status IN ('error_retry','failed','discarded')
            """
        ),
        {"id": inventory_id, "uid": tenant_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Lead não encontrado ou não elegível para retry")
    supply.enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="manual-retry")
    return {"ok": True}


@router.post("/retry-all")
async def retry_all_error_leads(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    from sqlalchemy import text

    tenant_id = _tenant_id(usuario)
    supply.ensure_schema(db)
    result = db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status='approved', erro=NULL, locked_by=NULL, locked_until=NULL,
                atualizado_em=NOW()
            WHERE tenant_id=:uid
              AND status IN ('error_retry','failed','discarded')
            """
        ),
        {"uid": tenant_id},
    )
    db.commit()
    reprocessed = int(result.rowcount or 0)
    if reprocessed:
        supply.enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="manual-retry-all")
    return {"ok": True, "reprocessed": reprocessed}
