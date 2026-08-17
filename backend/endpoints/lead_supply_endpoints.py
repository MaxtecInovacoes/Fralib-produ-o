from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.services.lead_supply_engine import lead_supply_engine as supply
from backend.services.credits_manager import validar_permissao_pipeline


router = APIRouter(prefix="/api/lead-supply", tags=["lead-supply"])


def _tenant_id(usuario: dict) -> int:
    return int(usuario.get("tenant_id") or usuario["id"])


def _get_waiting_reasons_and_counts(db: Session, tenant_id: int) -> tuple[str, dict]:
    counts = db.execute(
        text(
            "SELECT status, COUNT(*) FROM lead_inventory "
            "WHERE tenant_id=:uid GROUP BY status"
        ),
        {"uid": tenant_id},
    ).fetchall()
    c = {r[0]: int(r[1] or 0) for r in counts}
    raw = c.get("raw", 0) + c.get("qualifying", 0)
    err = c.get("error_retry", 0) + c.get("failed", 0)
    res = c.get("reserved", 0) + c.get("in_production", 0)
    reasons = []
    if raw:
        reasons.append(f"{raw} lead(s) aguardando qualificacao do Caio")
    if err:
        reasons.append(f"{err} lead(s) bloqueado(s) em erro")
    if res:
        reasons.append(f"{res} lead(s) ja em producao/reservado")
    jobs_rows = db.execute(
        text(
            "SELECT tipo, status, COUNT(*) FROM jobs "
            "WHERE tenant_id=:uid AND tipo IN ('lead_production_tick','pipeline_lead','pipeline_main','pipeline_multiplos') "
            "AND status IN ('pending','running','failed_retriable') "
            "GROUP BY tipo, status"
        ),
        {"uid": tenant_id},
    ).fetchall()
    if jobs_rows:
        reasons.append("pipeline ativa no momento")
    blocked_reason = (
        reasons[0] if len(reasons) == 1
        else ("; ".join(reasons) if reasons else "estoque aprovado zerado no momento")
    )
    counts_dict = {
        "raw": c.get("raw", 0),
        "qualifying": c.get("qualifying", 0),
        "error_retry": c.get("error_retry", 0),
        "failed": c.get("failed", 0),
        "reserved": c.get("reserved", 0),
        "in_production": c.get("in_production", 0),
        "approved": c.get("approved", 0),
        "site_done": c.get("site_done", 0),
    }
    return blocked_reason, counts_dict


def _permission_or_error(db: Session, tenant_id: int) -> dict:
    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm.get("allowed"):
        status_code = 429 if perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=status_code, detail=perm)
    return perm


@router.get("/status")
def get_lead_supply_status(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    data = supply.status(db, tenant_id)
    data["permission"] = validar_permissao_pipeline(db, tenant_id)
    return data


@router.get("/config")
def get_lead_supply_config(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    return {"config": supply.get_or_create_config(db, _tenant_id(usuario))}


class ConfigPayload(BaseModel):
    meta: Optional[dict] = None
    meta_nicho: Optional[str] = None
    meta_cidade: Optional[str] = None
    meta_leads: Optional[int] = None
    meta_tempo: Optional[int] = None
    estrategia_id: Optional[str] = None
    template_id: Optional[str] = None


@router.post("/config")
def save_lead_supply_config(
    payload: ConfigPayload,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _tenant_id(usuario)
    cfg = supply.save_config(db, tenant_id, payload.model_dump(exclude_none=True))
    if validar_permissao_pipeline(db, tenant_id).get("allowed"):
        supply.sync_supply(db, tenant_id)
    return {"ok": True, "config": cfg}


class PausePayload(BaseModel):
    hunter_pausado: Optional[bool] = None
    producao_pausada: Optional[bool] = None
    ativo: Optional[bool] = None


@router.post("/pause")
def pause_lead_supply(
    payload: PausePayload,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _tenant_id(usuario)
    cfg = supply.set_pause(
        db,
        tenant_id,
        hunter=payload.hunter_pausado,
        production=payload.producao_pausada,
        active=payload.ativo,
    )
    supply.sync_supply(db, tenant_id)
    return {"ok": True, "config": cfg}


@router.post("/start")
def start_lead_supply(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    _permission_or_error(db, tenant_id)
    cfg = supply.set_pause(db, tenant_id, hunter=False, production=False, active=True)
    immediate = supply.run_production_tick(db, {"reason": "start-inline"}, tenant_id)
    should_enqueue_tick = not (
        immediate.get("job_id")
        or immediate.get("duplicate_job")
        or immediate.get("waiting") == "pipeline_running"
        or immediate.get("waiting") == "no_approved_lead"
        or immediate.get("cooldown")
    )
    tick_job_id = None
    if should_enqueue_tick:
        tick_job_id = supply.enqueue_production_tick(db, tenant_id, delay_seconds=2, reason="start")
    body = {
        "ok": True,
        "config": cfg,
        "immediate": immediate,
        "job_id": immediate.get("job_id"),
        "tick_job_id": tick_job_id,
        "duplicate_job": immediate.get("duplicate_job"),
        "waiting": immediate.get("waiting"),
        "cooldown": immediate.get("cooldown"),
        "blocked": immediate.get("blocked"),
        "paused": immediate.get("paused"),
        "requeued_terminal_job": immediate.get("requeued_terminal_job"),
    }
    waiting = immediate.get("waiting")
    if waiting == "no_approved_lead":
        blocked_reason, counts = _get_waiting_reasons_and_counts(db, tenant_id)
        body["blocked_reason"] = blocked_reason
        body["counts"] = counts
    return body


@router.post("/refill")
def refill_lead_supply(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    _permission_or_error(db, tenant_id)
    job_id = supply.enqueue_hunter(db, tenant_id, delay_seconds=1, force=True)
    return {"ok": True, "job_id": job_id}


@router.post("/production/tick")
def tick_lead_production(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = _tenant_id(usuario)
    _permission_or_error(db, tenant_id)
    immediate = supply.run_production_tick(db, {"reason": "manual-inline"}, tenant_id)
    should_enqueue_tick = not (
        immediate.get("job_id")
        or immediate.get("duplicate_job")
        or immediate.get("waiting") == "pipeline_running"
        or immediate.get("waiting") == "no_approved_lead"
        or immediate.get("cooldown")
    )
    tick_job_id = None
    if should_enqueue_tick:
        tick_job_id = supply.enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="manual")
    body = {
        "ok": True,
        "immediate": immediate,
        "job_id": immediate.get("job_id"),
        "tick_job_id": tick_job_id,
        "duplicate_job": immediate.get("duplicate_job"),
        "waiting": immediate.get("waiting"),
        "cooldown": immediate.get("cooldown"),
        "inventory_id": immediate.get("inventory_id"),
        "lead_nome": immediate.get("lead_nome"),
        "message": immediate.get("message"),
        "blocked": immediate.get("blocked"),
        "paused": immediate.get("paused"),
        "requeued_terminal_job": immediate.get("requeued_terminal_job"),
    }
    waiting = immediate.get("waiting")
    if waiting == "no_approved_lead":
        blocked_reason, counts = _get_waiting_reasons_and_counts(db, tenant_id)
        body["blocked_reason"] = blocked_reason
        body["counts"] = counts
    return body


@router.post("/leads/{inventory_id}/discard")
def discard_inventory_lead(
    inventory_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
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
def retry_inventory_lead(
    inventory_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
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
def retry_all_error_leads(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):

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
