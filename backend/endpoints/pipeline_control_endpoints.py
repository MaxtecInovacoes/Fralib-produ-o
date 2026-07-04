from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY

from backend.core.database import get_db, update_pipeline_state
from backend.core.auth import get_current_user
from backend.endpoints.sse_endpoints import adicionar_log

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/parar")
async def parar_pipeline(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, pausado=False)
    return {"status": "parado"}


@router.post("/reset")
async def reset_pipeline(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, pausado=False, config={})
    return {"status": "resetado", "mensagem": "Pipeline resetado com sucesso"}


@router.post("/cancelar")
async def cancelar_pipeline(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    result = db.execute(
        text(
            """
        UPDATE jobs SET status = 'failed_permanent'
        WHERE tenant_id = :tid AND status IN ('pending', 'running')
    """
        ),
        {"tid": tenant_id},
    )
    db.commit()
    cancelled = result.rowcount
    update_pipeline_state(db, tenant_id, pausado=False)
    adicionar_log(f"Pipeline cancelado ({cancelled} jobs)", "warning", user_id=tenant_id)
    return {"status": "cancelado", "jobs_cancelados": cancelled}


@router.post("/pausar")
async def pausar_pipeline(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, pausado=True)
    adicionar_log("Pipeline pausado pelo usuario", "warning", user_id=tenant_id)
    return {"status": "pausado"}


@router.post("/retomar")
async def retomar_pipeline(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, pausado=False)
    adicionar_log("Pipeline retomado pelo usuario", "info", user_id=tenant_id)
    return {"status": "retomado"}


@router.post("/arquivar-tudo")
async def arquivar_tudo(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    try:
        result = db.execute(
            text(
                "UPDATE leads SET status='arquivado', atualizado_em=:ts WHERE user_id=:uid AND status != 'arquivado'"
            ),
            {"uid": tenant_id, "ts": datetime.now().isoformat()},
        )
        db.commit()
        count = result.rowcount
        adicionar_log(f"{count} leads arquivados", "info", user_id=tenant_id)
        return {"ok": True, "message": f"{count} leads arquivados com sucesso"}
    except Exception as e:
        raise HTTPException(500, str(e))

