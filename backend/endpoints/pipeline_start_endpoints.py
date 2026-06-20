from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import asyncio
import logging
import uuid

from backend.core.database import (
    get_db,
    get_pipeline_state,
    update_pipeline_state,
)
from backend.core.auth import get_current_user
from backend.endpoints.sse_endpoints import adicionar_log
from backend.whatsapp_listener import is_tenant_connected
from backend.services.credits_manager import validar_permissao_pipeline, plano_tem_sdr
from pipeline_runtime_utils import check_rate_limit as _check_rate_limit

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])
logger = logging.getLogger("uvicorn")


@router.post("/iniciar")
async def iniciar_pipeline(
    request: Request,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        config = await request.json()
    except Exception:
        config = {}
    tenant_id = usuario.get("tenant_id", usuario["id"])
    _plano_row = db.execute(
        text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()
    _plano_user = (_plano_row[0] if _plano_row else "trial").lower()
    _status_user = (_plano_row[1] if _plano_row else "") or ""
    _trial_expires_at = _plano_row[2] if _plano_row else None
    _MAX_QTD = {"trial": 1, "starter": 10, "pro": 50, "beta": 50, "ilimitado": 999, "agency": 999}
    _max_qtd = _MAX_QTD.get(_plano_user, 1)
    config_limpo = {
        "segmento": (config.get("segmento") or "").strip(),
        "cidade": (config.get("cidade") or "").strip(),
        "quantidade": min(int(config.get("quantidade") or 10), _max_qtd),
        "score_minimo": int(config.get("score_minimo") or 45),
    }
    if not config_limpo["segmento"] or not config_limpo["cidade"]:
        raise HTTPException(
            status_code=400, detail="Segmento e cidade são obrigatórios."
        )

    _tenant_wpp = f"fralib_user_{tenant_id}"
    _whatsapp_connected = is_tenant_connected(_tenant_wpp)
    config_limpo["_whatsapp_connected"] = _whatsapp_connected
    _sdr_required = plano_tem_sdr(_plano_user, _status_user, _trial_expires_at)
    config_limpo["_sdr_required"] = _sdr_required
    if _sdr_required and not _whatsapp_connected:
        raise HTTPException(
            status_code=428,
            detail={
                "reason": "whatsapp_required",
                "message": "Conecte seu WhatsApp para rodar este ciclo com SDR ativo.",
                "action": "Abra Meu Perfil, clique em CONECTAR / QR CODE e escaneie o QR.",
            },
        )
    if not _whatsapp_connected:
        logger.warning(
            "Tenant %s sem WhatsApp conectado; plano sem SDR ativo, pipeline segue sem Franz",
            tenant_id,
        )

    _state = get_pipeline_state(db, tenant_id)
    if _state.get("pausado"):
        raise HTTPException(status_code=429, detail="Pipeline pausada para este tenant.")
    active_jobs = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM jobs
            WHERE tenant_id=:uid
              AND tipo IN ('pipeline_lead','pipeline_multiplos','pipeline_main')
              AND status IN ('pending','running','failed_retriable')
            """
        ),
        {"uid": tenant_id},
    ).scalar() or 0
    if active_jobs:
        raise HTTPException(
            status_code=429,
            detail={
                "reason": "pipeline_already_queued",
                "message": "Você já tem pipeline em fila ou execução. Aguarde a conclusão.",
                "active_jobs": int(active_jobs),
            },
        )

    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm["allowed"]:
        _status = 429 if perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=_status, detail=perm)

    if config.get("processar_fila"):
        raise HTTPException(
            status_code=410,
            detail={
                "reason": "legacy_queue_disabled",
                "message": "A fila antiga foi desativada. Use o Estoque de Leads para abastecer e puxar 1 lead aprovado por vez.",
            },
        )

    _fila = (
        db.execute(
            text(
                "SELECT COUNT(*) FROM leads WHERE lower(cidade)=:cidade AND lower(segmento)=:segmento AND user_id=:user_id AND status='capturado'"
            ),
            {
                "cidade": config_limpo["cidade"].lower().strip(),
                "segmento": config_limpo["segmento"].lower().strip(),
                "user_id": tenant_id,
            },
        ).scalar()
        or 0
    )
    if _fila > 0:
        return {
            "status": "fila_pendente",
            "mensagem": f"Voce tem {_fila} lead(s) capturado(s) para {config_limpo['segmento']} em {config_limpo['cidade']} que ainda nao passaram pela pipeline. Processe-os antes de capturar mais.",
            "leads_na_fila": _fila,
            "config": config_limpo,
        }

    _check_rate_limit(str(tenant_id))
    update_pipeline_state(db, tenant_id, pausado=False, config=config_limpo)

    import job_queue as _jq

    try:
        _run_id = uuid.uuid4().hex[:12]
        idem = f"pipeline-{tenant_id}-{_run_id}"
        _priority = (
            1 if _plano_user in ("pro", "ilimitado", "agency") else (2 if _plano_user == "starter" else 3)
        )
        job_id = _jq.enqueue(
            db,
            tipo="pipeline_multiplos",
            payload={**config_limpo, "_run_id": _run_id},
            tenant_id=tenant_id,
            max_attempts=3,
            idempotency_key=idem,
            priority=_priority,
            run_id=_run_id,
        )
        if job_id is None:
            return {
                "status": "ja_enfileirado",
                "mensagem": "Pipeline ja esta na fila",
                "config": config_limpo,
            }
        return {
            "status": "iniciado",
            "mensagem": "Pipeline iniciado com 7 agentes",
            "config": config_limpo,
            "job_id": job_id,
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Sistema de filas temporariamente indisponível. Tente novamente em alguns segundos.",
        )
