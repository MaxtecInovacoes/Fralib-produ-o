"""Rotas de controle do pipeline: iniciar, parar, reset, cancelar, pausar, retomar, arquivar-tudo."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, get_pipeline_state, update_pipeline_state, SessionLocal
from auth import get_current_user
from sse_endpoints import adicionar_log
from services.credits_manager import validar_permissao_pipeline
from backend.schemas.pipeline_trigger import PipelineTriggerRequest
from backend.services.admin_user_service import archive_all_leads

from pipeline_execution import (
    executar_pipeline_completo,
    executar_pipeline_multiplos,
    _check_rate_limit,
    _check_cooldown,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/iniciar")
def iniciar_pipeline(
    body: PipelineTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Inicia pipeline: Hunter -> Caio -> Arquiteto -> Builder -> QA -> Deploy."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    segmento = body.segmento.strip()
    cidade = body.cidade.strip()
    quantidade = int(body.quantidade)
    pipeline_id = body.pipeline_id or ""

    if not segmento or not cidade:
        raise HTTPException(400, "segmento e cidade sao obrigatorios")

    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm["allowed"]:
        status = 429 if perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=status, detail=perm)

    _check_rate_limit(str(tenant_id))

    pipeline_state = get_pipeline_state(db, tenant_id)
    if pipeline_state.get("rodando"):
        raise HTTPException(409, "Ja existe um pipeline rodando. Aguarde ou cancele.")

    config = {"segmento": segmento, "cidade": cidade, "quantidade": quantidade}
    if pipeline_id:
        config["pipeline_id"] = pipeline_id

    import job_queue as _jq
    try:
        job_id = _jq.enqueue(db, tipo="pipeline_lead", payload=config, tenant_id=tenant_id, max_attempts=3)
        if job_id:
            adicionar_log(f"[Pipeline] Job enfileirado #{job_id}: {segmento} em {cidade}", "info", user_id=tenant_id)
        else:
            background_tasks.add_task(
                executar_pipeline_multiplos if quantidade > 1 else executar_pipeline_completo,
                config, tenant_id,
            )
    except Exception as _e:
        print(f"[Iniciar] Enqueue falhou: {_e}")
        background_tasks.add_task(
            executar_pipeline_multiplos if quantidade > 1 else executar_pipeline_completo,
            config, tenant_id,
        )

    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, rodando=True, pausado=False, config=config)

    adicionar_log(f"Pipeline iniciado: {segmento} em {cidade} (x{quantidade})", "success", user_id=tenant_id)
    return {"ok": True, "mensagem": f"Pipeline iniciado: {segmento} em {cidade}"}


@router.post("/parar")
async def parar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Para o pipeline imediatamente."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, rodando=False, pausado=False)
    adicionar_log("Pipeline PARADO pelo usuario", "warning", user_id=tenant_id)
    return {"ok": True, "mensagem": "Pipeline parado"}


@router.post("/reset")
async def reset_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Reseta estado do pipeline (limpa erro, contadores, config)."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, rodando=False, pausado=False, erro=None,
            total_leads=0, leads_processados=0, config=None)
    adicionar_log("Pipeline RESETADO", "info", user_id=tenant_id)
    return {"ok": True, "mensagem": "Pipeline resetado"}


@router.post("/cancelar")
async def cancelar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Cancela o pipeline com motivo."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, rodando=False, pausado=False, erro="Cancelado pelo usuario")
    adicionar_log("Pipeline CANCELADO pelo usuario", "warning", user_id=tenant_id)
    return {"ok": True, "mensagem": "Pipeline cancelado"}


@router.post("/pausar")
async def pausar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Pausa o pipeline (mantem estado atual)."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, pausado=True)
    adicionar_log("Pipeline PAUSADO", "warning", user_id=tenant_id)
    return {"ok": True, "mensagem": "Pipeline pausado"}


@router.post("/retomar")
async def retomar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Retoma pipeline pausado."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, pausado=False)
    adicionar_log("Pipeline RETOMADO", "success", user_id=tenant_id)
    return {"ok": True, "mensagem": "Pipeline retomado"}


@router.post("/arquivar-tudo")
def arquivar_tudo(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Arquiva todos os leads capturados do tenant."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    archive_all_leads(db, tenant_id)
    adicionar_log("Todos os leads capturados foram arquivados", "info", user_id=tenant_id)
    return {"ok": True, "mensagem": "Leads arquivados"}
