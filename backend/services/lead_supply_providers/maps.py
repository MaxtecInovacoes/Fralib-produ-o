"""Production tick provider for lead supply engine."""

from __future__ import annotations

import os
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core import job_queue


def run_production_tick(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    """Run the production tick to process approved leads."""
    from backend.services.lead_supply_storage import (
        _event,
        get_or_create_config,
    )
    from backend.services.lead_supply_inventory import (
        _ensure_lead_row,
        _reserve_next,
        enqueue_hunter,
    )
    from backend.services.credits_manager import validar_permissao_pipeline

    cfg = get_or_create_config(db, tenant_id)
    if not cfg["ativo"] or cfg["producao_pausada"]:
        _event(db, tenant_id, "producao", "info", "Produção pausada pelo usuário")
        return {"ok": True, "paused": True}
    running = db.execute(
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
    if running:
        return {"ok": True, "waiting": "pipeline_running"}

    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm.get("allowed"):
        if perm.get("reason") == "cooldown":
            from backend.services.lead_supply_inventory import enqueue_production_tick

            delay = max(30, min(int(perm.get("cooldown_restante_seg") or 300) + 10, 7200))
            enqueue_production_tick(db, tenant_id, delay_seconds=delay, reason="cooldown")
            _event(db, tenant_id, "producao", "info", f"Produção em cooldown. Próxima tentativa em {delay//60}min")
            return {"ok": True, "cooldown": delay}
        _event(db, tenant_id, "producao", "warning", perm.get("message", "Plano sem permissão para produzir"))
        return {"ok": True, "blocked": perm.get("reason")}

    item = _reserve_next(db, tenant_id)
    if not item:
        _event(db, tenant_id, "producao", "info", "Sem lead aprovado disponível. Hunter vai abastecer a fila.")
        enqueue_hunter(db, tenant_id, delay_seconds=1, force=True)
        return {"ok": True, "waiting": "no_approved_lead"}
    lead_id = _ensure_lead_row(db, tenant_id, item)
    run_id = uuid.uuid4().hex[:12]
    payload_job = {
        "segmento": item["segmento"] or "",
        "cidade": item["cidade"] or "",
        "quantidade": 1,
        "score_minimo": int(cfg["score_minimo"]),
        "_lead_id_existente": lead_id,
        "_inventory_id": item["id"],
        "_forcar_renovacao": True,
        "_cold_run": True,
        "_prompt_agent_flow": True,
        "_run_id": run_id,
    }
    test_number = str(payload.get("_bryan_test_number") or os.getenv("BRYAN_TEST_NUMBER", "")).strip()
    if test_number:
        payload_job["_bryan_test_number"] = test_number
    existing_job = db.execute(
        text(
            """
            SELECT id, status
            FROM jobs
            WHERE tenant_id=:uid
              AND tipo='pipeline_lead'
              AND status IN ('pending','running','failed_retriable')
              AND CAST(payload AS text) LIKE :inventory_marker
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"uid": tenant_id, "inventory_marker": f'%\"_inventory_id\": \"{item["id"]}\"%'},
    ).fetchone()
    if existing_job:
        db.execute(
            text(
                """
                UPDATE lead_inventory
                SET status='approved', locked_by=NULL, locked_until=NULL,
                    erro='Pipeline ativa já existe para este lead',
                    atualizado_em=NOW()
                WHERE id=:id AND tenant_id=:uid
                """
            ),
            {"id": item["id"], "uid": tenant_id},
        )
        db.commit()
        return {"ok": True, "duplicate_job": True, "existing_job_id": existing_job[0]}
    job_id = job_queue.enqueue(
        db,
        tipo="pipeline_lead",
        payload=payload_job,
        tenant_id=tenant_id,
        max_attempts=3,
        idempotency_key=f"inventory-pipeline-{item['id']}-{run_id}",
        priority=1,
        run_id=run_id,
    )
    if not job_id:
        db.execute(
            text(
                """
                UPDATE lead_inventory
                SET status='approved', locked_by=NULL, locked_until=NULL,
                    erro='Pipeline já estava enfileirada para este lead',
                    atualizado_em=NOW()
                WHERE id=:id AND tenant_id=:uid
                """
            ),
            {"id": item["id"], "uid": tenant_id},
        )
        db.commit()
        return {"ok": True, "duplicate_job": True}
    db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status='in_production', lead_id=:lead_id, atualizado_em=NOW()
            WHERE id=:id AND tenant_id=:uid
            """
        ),
        {"lead_id": lead_id, "id": item["id"], "uid": tenant_id},
    )
    db.commit()
    _event(db, tenant_id, "producao", "success", f"Pipeline enfileirada para {item['nome']} (job #{job_id})")
    return {"ok": True, "job_id": job_id, "lead_id": lead_id, "inventory_id": item["id"]}
