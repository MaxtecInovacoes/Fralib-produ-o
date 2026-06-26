"""
Endpoints da lista de falhas de pipeline.

GET  /api/falhas             - lista falhas do tenant (com paginacao simples)
POST /api/falhas/{id}/retry  - reenfileira a falha como um novo job
GET  /api/falhas/contador    - quantidade nao vista (para badge no header)
POST /api/falhas/{id}/visto  - marca como visto (ao abrir a lista)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import os, sys
import uuid

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))

from backend.core.database import get_db
from backend.core.auth import get_current_user
from rate_limiter import limiter
import job_queue

router = APIRouter(prefix="/api/falhas", tags=["falhas"])


@router.get("")
@limiter.limit("60/minute")
async def listar_falhas(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    apenas_pendentes: bool = True,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = int(user["id"])
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    where = "tenant_id = :tid"
    if apenas_pendentes:
        where += " AND resolvido = FALSE"

    rows = db.execute(
        text(f"""
            SELECT id, lead_id, lead_nome, fase, mensagem_amigavel,
                   erro_tecnico, tentativas_automaticas, checkpoint_id,
                   criado_em, visto_pelo_usuario, resolvido
            FROM pipeline_failures
            WHERE {where}
            ORDER BY criado_em DESC
            LIMIT :lim OFFSET :off
        """),
        {"tid": tenant_id, "lim": limit, "off": offset},
    ).fetchall()

    total = (
        db.execute(
            text(f"SELECT COUNT(*) FROM pipeline_failures WHERE {where}"),
            {"tid": tenant_id},
        ).scalar()
        or 0
    )

    return {
        "total": int(total),
        "falhas": [
            {
                "id": r[0],
                "lead_id": r[1],
                "lead_nome": r[2],
                "fase": r[3],
                "mensagem": r[4],
                "erro_tecnico": r[5],
                "tentativas": r[6],
                "checkpoint_id": r[7],
                "criado_em": r[8].isoformat() if r[8] else None,
                "visto": bool(r[9]),
                "resolvido": bool(r[10]),
            }
            for r in rows
        ],
    }


@router.get("/contador")
@limiter.limit("120/minute")
async def contador_falhas(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = int(user["id"])
    n = (
        db.execute(
            text("""
            SELECT COUNT(*) FROM pipeline_failures
            WHERE tenant_id = :tid AND resolvido = FALSE AND visto_pelo_usuario = FALSE
        """),
            {"tid": tenant_id},
        ).scalar()
        or 0
    )
    return {"nao_vistas": int(n)}


@router.post("/{falha_id}/visto")
@limiter.limit("60/minute")
async def marcar_visto(
    request: Request,
    falha_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = int(user["id"])
    r = db.execute(
        text("""
            UPDATE pipeline_failures
            SET visto_pelo_usuario = TRUE
            WHERE id = :fid AND tenant_id = :tid
        """),
        {"fid": int(falha_id), "tid": tenant_id},
    )
    db.commit()
    if r.rowcount == 0:
        raise HTTPException(status_code=404, detail="Falha nao encontrada")
    return {"ok": True}


@router.post("/{falha_id}/retry")
@limiter.limit("20/minute")
async def retry_falha(
    request: Request,
    falha_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Reenfileira a falha como um novo job. Mantem checkpoint_id para que o
    pipeline retome do ponto onde parou (e nao gaste tokens repetindo agentes
    ja concluidos).
    """
    tenant_id = int(user["id"])
    row = db.execute(
        text("""
            SELECT id, lead_id, lead_nome, fase, payload, checkpoint_id, resolvido
            FROM pipeline_failures
            WHERE id = :fid AND tenant_id = :tid
        """),
        {"fid": int(falha_id), "tid": tenant_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Falha nao encontrada")
    if row[6]:
        raise HTTPException(status_code=400, detail="Falha ja foi resolvida")

    payload = row[4] or {}
    if not isinstance(payload, dict):
        payload = {}
    lead_id = row[1]
    checkpoint_id = row[5]
    run_id = payload.get("_run_id")
    if not run_id:
        run_id = uuid.uuid4().hex[:12]
        payload = {**payload, "_run_id": run_id}

    # Idempotency_key garante que retries duplos (usuario clica 2x) virem 1 job
    idem = f"retry-falha-{falha_id}"

    job_id = job_queue.enqueue(
        db,
        tipo="pipeline_lead",
        payload=payload,
        tenant_id=tenant_id,
        max_attempts=3,
        idempotency_key=idem,
        checkpoint_id=checkpoint_id,
        run_id=run_id,
    )

    if job_id is None:
        # Ja existia um job com essa idempotency_key
        return {"ok": True, "ja_enfileirado": True}

    db.execute(
        text("""
            UPDATE pipeline_failures
            SET resolvido = TRUE, resolvido_em = NOW()
            WHERE id = :fid AND tenant_id = :tid
        """),
        {"fid": int(falha_id), "tid": tenant_id},
    )
    db.commit()

    return {"ok": True, "job_id": job_id, "lead_id": lead_id}


@router.post("/retry-all")
@limiter.limit("5/minute")
async def retry_all_falhas(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Sprint 14.7: reenfileira TODAS as falhas pendentes do tenant como
    novos jobs pipeline_lead (um por falha). Mantem checkpoint_id de cada
    falha para retomar do ponto onde parou.

    Idempotency_key por falha garante que retries duplos (usuario clica 2x)
    nao geram jobs duplicados.
    """
    tenant_id = int(user["id"])
    rows = db.execute(
        text("""
            SELECT id, lead_id, payload, checkpoint_id, resolvido
            FROM pipeline_failures
            WHERE tenant_id = :tid AND resolvido = FALSE
            ORDER BY criado_em ASC
        """),
        {"tid": tenant_id},
    ).fetchall()

    if not rows:
        return {"ok": True, "reenfileiradas": 0, "ja_resolvidas": 0}

    reenfileiradas = 0
    ja_enfileiradas = 0
    erros = []
    for row in rows:
        try:
            falha_id = row[0]
            lead_id = row[1]
            payload = row[2] or {}
            if not isinstance(payload, dict):
                payload = {}
            checkpoint_id = row[3]
            run_id = payload.get("_run_id")
            if not run_id:
                run_id = uuid.uuid4().hex[:12]
                payload = {**payload, "_run_id": run_id}

            idem = f"retry-falha-{falha_id}"
            job_id = job_queue.enqueue(
                db,
                tipo="pipeline_lead",
                payload=payload,
                tenant_id=tenant_id,
                max_attempts=3,
                idempotency_key=idem,
                checkpoint_id=checkpoint_id,
                run_id=run_id,
            )

            if job_id is None:
                ja_enfileiradas += 1
                # Marca como resolvido tambem para nao aparecer no badge
                db.execute(
                    text("""
                        UPDATE pipeline_failures
                        SET resolvido = TRUE, resolvido_em = NOW()
                        WHERE id = :fid AND tenant_id = :tid
                    """),
                    {"fid": int(falha_id), "tid": tenant_id},
                )
            else:
                reenfileiradas += 1
                db.execute(
                    text("""
                        UPDATE pipeline_failures
                        SET resolvido = TRUE, resolvido_em = NOW()
                        WHERE id = :fid AND tenant_id = :tid
                    """),
                    {"fid": int(falha_id), "tid": tenant_id},
                )
        except Exception as e:
            erros.append({"falha_id": row[0], "erro": str(e)[:200]})

    db.commit()
    return {
        "ok": True,
        "reenfileiradas": reenfileiradas,
        "ja_enfileiradas": ja_enfileiradas,
        "erros": erros,
    }

