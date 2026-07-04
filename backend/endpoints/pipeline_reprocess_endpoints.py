from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.endpoints.sse_endpoints import adicionar_log
from backend.services.credits_manager import validar_permissao_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/reprocessar/{lead_id}")
async def reprocessar_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
    forcar_renovacao: bool = False,
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    _perm = validar_permissao_pipeline(db, tenant_id)
    if not _perm["allowed"]:
        _status = 429 if _perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=_status, detail=_perm)
    lead = db.execute(
        text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
        {"id": lead_id, "uid": tenant_id},
    ).fetchone()
    if not lead:
        raise HTTPException(404, "Lead nao encontrado")
    db.execute(
        text("UPDATE leads SET status='capturado', processado=false, atualizado_em=:ts WHERE id=:id AND user_id=:uid"),
        {"ts": datetime.now().isoformat(), "id": lead_id, "uid": tenant_id},
    )
    db.commit()
    _renovacao_label = " (renovacao forcada)" if forcar_renovacao else ""
    adicionar_log(f"Lead {lead.nome} reprocessando{_renovacao_label}...", "info", user_id=tenant_id)
    import job_queue as _jq

    _run_id = uuid.uuid4().hex[:12]
    config_reproc = {
        "segmento": lead.segmento or "",
        "cidade": lead.cidade or "",
        "quantidade": 1,
        "_lead_id_existente": lead_id,
        "_forcar_renovacao": forcar_renovacao,
        "_run_id": _run_id,
    }
    try:
        job_id = _jq.enqueue(
            db,
            tipo="pipeline_lead",
            payload={**config_reproc},
            tenant_id=tenant_id,
            max_attempts=3,
            priority=1,
            run_id=_run_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "reason": "job_queue_unavailable",
                "message": "Fila de produção indisponível. Reprocessamento não iniciou.",
            },
        ) from exc
    if not job_id:
        raise HTTPException(
            status_code=503,
            detail={
                "reason": "job_queue_rejected",
                "message": "Fila de produção rejeitou o reprocessamento.",
            },
        )
    adicionar_log(f"[Pipeline] Reprocessamento enfileirado (job #{job_id})", "info", user_id=tenant_id)
    return {"ok": True, "mensagem": "Lead marcado para reprocessamento"}


@router.get("/fila-reprocessamento")
async def fila_reprocessamento(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    leads = db.execute(
        text("SELECT id, nome, cidade, segmento, rating, score, tier FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY criado_em DESC"),
        {"uid": tenant_id},
    ).fetchall()
    return {"leads": [dict(r._mapping) for r in leads], "total": len(leads)}
