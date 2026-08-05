"""Caio qualification provider for lead supply engine."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def run_caio_job(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    """Run the Caio qualification job on a lead."""
    from backend.services.lead_supply_storage import (
        _event,
        ensure_schema,
        get_or_create_config,
    )
    from backend.services.lead_supply_inventory import enqueue_production_tick

    ensure_schema(db)
    inv_id = str(payload.get("inventory_id") or "")
    row = db.execute(
        text(
            """
            SELECT * FROM lead_inventory
            WHERE id=:id AND tenant_id=:uid
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"id": inv_id, "uid": tenant_id},
    ).fetchone()
    if not row:
        db.commit()
        return {"ok": False, "error": "inventory_not_found"}
    item = dict(row._mapping)
    if item["status"] not in ("raw", "error_retry", "qualifying"):
        db.commit()
        return {"ok": True, "skipped": item["status"]}
    db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status='qualifying', attempts=attempts+1, atualizado_em=NOW()
            WHERE id=:id AND tenant_id=:uid
            """
        ),
        {"id": inv_id, "uid": tenant_id},
    )
    db.commit()

    from agents.caio import LeadInput as CaioInput, qualificar_lead

    dados = item.get("dados") if isinstance(item.get("dados"), dict) else json.loads(item.get("dados") or "{}")
    try:
        result = qualificar_lead(
            CaioInput(
                nome=item["nome"],
                cidade=item["cidade"] or "",
                segmento=item["segmento"] or "",
                telefone=item["telefone"] or "",
                whatsapp=item["whatsapp"] or "",
                rating=float(item["rating"] or 0.0),
                reviews_count=int(item["reviews_count"] or 0),
                fotos=dados.get("fotos") or [],
                website=item["website"] or "",
                logo_url=dados.get("logo_url") or "",
            )
        )
        cfg = get_or_create_config(db, tenant_id)
        approved = bool(result.qualificado and result.tier != "REJEITADO" and int(result.score or 0) >= int(cfg["score_minimo"]))
        new_status = "approved" if approved else "discarded"
        db.execute(
            text(
                """
                UPDATE lead_inventory
                SET status=:status, score_caio=:score, tier=:tier,
                    caio_motivo=:motivo, erro=NULL, atualizado_em=NOW()
                WHERE id=:id AND tenant_id=:uid
                """
            ),
            {
                "status": new_status,
                "score": int(result.score or 0),
                "tier": result.tier or "",
                "motivo": result.motivo or "",
                "id": inv_id,
                "uid": tenant_id,
            },
        )
        db.commit()
        if approved:
            _event(db, tenant_id, "caio", "success", f"Caio aprovou {item['nome']} (score {result.score})")
            enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="caio-approved")
        else:
            _event(db, tenant_id, "caio", "warning", f"Caio descartou {item['nome']}: {result.motivo}")
        return {"ok": True, "approved": approved, "score": int(result.score or 0)}
    except Exception as exc:
        db.execute(
            text(
                """
                UPDATE lead_inventory
                SET status='error_retry', erro=:erro, atualizado_em=NOW()
                WHERE id=:id AND tenant_id=:uid
                """
            ),
            {"erro": str(exc)[:1000], "id": inv_id, "uid": tenant_id},
        )
        db.commit()
        _event(db, tenant_id, "caio", "error", f"Caio falhou em {item['nome']}: {str(exc)[:180]}")
        return {"ok": False, "error": str(exc)}
