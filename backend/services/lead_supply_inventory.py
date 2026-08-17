"""Lead supply inventory operations - status, candidates, locks and job handling."""


import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core import job_queue

from backend.services.lead_supply_providers import (
    PRODUCTION_TICK_JOB,
    SUPPLY_CAIO_JOB,
    SUPPLY_HUNTER_JOB,
)
from backend.services.lead_supply_filters import dedupe_key
from backend.services.lead_supply_storage import (
    _event,
    ensure_schema,
    get_or_create_config,
)


def _compute_live_status(cfg: dict[str, Any], counts: dict[str, int], jobs: list[dict[str, Any]], events_rows: list[Any]) -> dict[str, Any]:
    """Compute the live status of the lead supply engine."""
    latest_source = ""
    latest_level = ""
    latest_message = ""
    if events_rows:
        latest_source = str(events_rows[0][0] or "")
        latest_level = str(events_rows[0][1] or "")
        latest_message = str(events_rows[0][2] or "")
    hunter_job = any((j.get("tipo") == "lead_supply_hunter" and int(j.get("total") or 0) > 0) for j in jobs)
    caio_job = any((j.get("tipo") == "lead_supply_caio" and int(j.get("total") or 0) > 0) for j in jobs)
    prod_job = any((str(j.get("tipo") or "").startswith("lead_production_tick") or str(j.get("tipo") or "").startswith("pipeline_")) and int(j.get("total") or 0) > 0 for j in jobs)
    approved = int(counts.get("approved", 0) or 0)
    raw = int(counts.get("raw", 0) or 0)
    qualifying = int(counts.get("qualifying", 0) or 0)
    reserved = int(counts.get("reserved", 0) or 0)
    in_prod = int(counts.get("in_production", 0) or 0)
    if not cfg.get("ativo", True):
        phase = "desligado"
        detail = "Motores desligados"
    elif cfg.get("producao_pausada"):
        phase = "pausado"
        detail = "Produção pausada"
    elif in_prod or reserved or prod_job:
        phase = "produzindo"
        detail = "Produção em andamento"
    elif approved > 0:
        phase = "aprovados"
        detail = f"{approved} lead(s) aprovados prontos"
    elif qualifying > 0 or caio_job:
        phase = "qualificando"
        detail = f"Caio qualificando {qualifying or 1} lead(s)"
    elif raw > 0 or hunter_job:
        phase = "buscando"
        detail = f"Hunter buscando {raw or 1} lead(s)"
    else:
        phase = "aguardando"
        detail = "Aguardando próxima rodada"
    return {
        "phase": phase,
        "detail": detail,
        "last_source": latest_source,
        "last_level": latest_level,
        "last_message": latest_message,
    }


def status(db: Session, tenant_id: int, limit: int = 30) -> dict[str, Any]:
    """Get the current status of the lead supply engine."""
    cfg = get_or_create_config(db, tenant_id)
    counts_rows = db.execute(
        text(
            """
            SELECT status, COUNT(*)
            FROM lead_inventory
            WHERE tenant_id=:uid
            GROUP BY status
            """
        ),
        {"uid": tenant_id},
    ).fetchall()
    counts = {r[0]: int(r[1] or 0) for r in counts_rows}
    discard_rows = db.execute(
        text(
            """
            SELECT caio_motivo, COUNT(*)
            FROM lead_inventory
            WHERE tenant_id=:uid
              AND status='discarded'
              AND caio_motivo IS NOT NULL
              AND caio_motivo <> ''
            GROUP BY caio_motivo
            ORDER BY COUNT(*) DESC
            LIMIT 5
            """
        ),
        {"uid": tenant_id},
    ).fetchall()
    discard_breakdown = [
        {"motivo": r[0] or "", "total": int(r[1] or 0)}
        for r in discard_rows
    ]
    nicho_rows = db.execute(
        text(
            """
            SELECT segmento, cidade, status, COUNT(*)
            FROM lead_inventory
            WHERE tenant_id=:uid
              AND segmento IS NOT NULL
            GROUP BY segmento, cidade, status
            """
        ),
        {"uid": tenant_id},
    ).fetchall()
    nicho_map: dict[tuple[str, str], dict[str, Any]] = {}
    for r in nicho_rows:
        segmento = r[0] or ""
        cidade = r[1] or ""
        status_name = r[2] or ""
        total = int(r[3] or 0)
        key = (segmento, cidade)
        item = nicho_map.setdefault(
            key,
            {"segmento": segmento, "cidade": cidade, "brutos": 0, "approved": 0, "discarded": 0},
        )
        if status_name in ("raw", "qualifying"):
            item["brutos"] += total
        elif status_name == "approved":
            item["approved"] += total
        elif status_name in ("discarded", "error_retry", "failed"):
            item["discarded"] += total
    nicho_cidade_breakdown = sorted(
        nicho_map.values(),
        key=lambda x: (int(x.get("approved") or 0), int(x.get("brutos") or 0), int(x.get("discarded") or 0)),
        reverse=True,
    )[:6]
    jobs_rows = db.execute(
        text(
            """
            SELECT tipo, status, COUNT(*)
            FROM jobs
            WHERE tenant_id=:uid
              AND tipo IN ('lead_supply_hunter','lead_supply_caio','lead_production_tick',
                           'pipeline_lead','pipeline_multiplos','pipeline_main')
              AND status IN ('pending','running','failed_retriable')
            GROUP BY tipo, status
            """
        ),
        {"uid": tenant_id},
    ).fetchall()
    jobs = [
        {"tipo": r[0], "status": r[1], "total": int(r[2] or 0)}
        for r in jobs_rows
    ]
    leads_rows = db.execute(
        text(
            """
            SELECT id, nome, segmento, cidade, status, score_caio, tier, erro,
                   caio_motivo, lead_id, atualizado_em
            FROM lead_inventory
            WHERE tenant_id=:uid
            ORDER BY atualizado_em DESC
            LIMIT :limit
            """
        ),
        {"uid": tenant_id, "limit": limit},
    ).fetchall()
    events_rows = db.execute(
        text(
            """
            SELECT source, level, message, criado_em
            FROM lead_supply_events
            WHERE tenant_id=:uid
            ORDER BY criado_em DESC
            LIMIT 12
            """
        ),
        {"uid": tenant_id},
    ).fetchall()
    approved_available = counts.get("approved", 0)
    gap_para_meta = max(0, int(cfg.get("estoque_alvo") or 0) - int(approved_available or 0))
    cfg["estoque_atual"] = approved_available
    cfg["estoque_total_util"] = sum(
        counts.get(k, 0) for k in ("raw", "qualifying", "approved", "reserved", "in_production")
    )
    live = _compute_live_status(cfg, counts, jobs, events_rows)
    last_hunter_row = db.execute(
        text(
            """
            SELECT id, nome, segmento, cidade, score_caio, tier, criado_em
            FROM lead_inventory
            WHERE tenant_id=:uid AND origem='hunter'
            ORDER BY criado_em DESC
            LIMIT 1
            """
        ),
        {"uid": tenant_id},
    ).fetchone()
    hunter_24h = db.execute(
        text(
            """
            SELECT
              COUNT(*) AS total_runs,
              SUM(CASE WHEN status IN ('raw','qualifying','approved','reserved','in_production','site_done') THEN 1 ELSE 0 END) AS found,
              SUM(CASE WHEN status IN ('discarded','error_retry','failed') THEN 1 ELSE 0 END) AS lost
            FROM lead_inventory
            WHERE tenant_id=:uid AND origem='hunter'
              AND criado_em > NOW() - INTERVAL '24 hours'
            """
        ),
        {"uid": tenant_id},
    ).fetchone()
    last_hunter_lead = None
    if last_hunter_row:
        last_hunter_lead = {
            "id": last_hunter_row[0],
            "nome": last_hunter_row[1],
            "segmento": last_hunter_row[2],
            "cidade": last_hunter_row[3],
            "score": last_hunter_row[4] or 0,
            "tier": last_hunter_row[5] or "-",
            "criado_em": str(last_hunter_row[6]) if last_hunter_row[6] else None,
        }
    hunter_24h_stats = {
        "runs": int(hunter_24h[0] or 0) if hunter_24h else 0,
        "found": int(hunter_24h[1] or 0) if hunter_24h else 0,
        "lost": int(hunter_24h[2] or 0) if hunter_24h else 0,
    }
    return {
        "config": cfg,
        "counts": counts,
        "jobs": jobs,
        "discard_breakdown": discard_breakdown,
        "nicho_cidade_breakdown": nicho_cidade_breakdown,
        "gap_para_meta": gap_para_meta,
        "last_hunter_lead": last_hunter_lead,
        "hunter_24h": hunter_24h_stats,
        "leads": [
            {
                "id": r[0],
                "nome": r[1],
                "segmento": r[2],
                "cidade": r[3],
                "status": r[4],
                "score_caio": r[5] or 0,
                "tier": r[6] or "",
                "erro": r[7] or "",
                "caio_motivo": r[8] or "",
                "lead_id": r[9] or "",
                "atualizado_em": str(r[10]),
            }
            for r in leads_rows
        ],
        "events": [
            {"source": r[0], "level": r[1], "message": r[2], "criado_em": str(r[3])}
            for r in events_rows
        ],
        "live": live,
    }


def _lead_to_dict(lead: Any) -> dict[str, Any]:
    """Convert a lead object to a dictionary."""
    if isinstance(lead, dict):
        return dict(lead)
    if hasattr(lead, "model_dump"):
        return lead.model_dump()
    if hasattr(lead, "dict"):
        return lead.dict()
    return dict(getattr(lead, "__dict__", {}) or {})


def _store_candidate(db: Session, tenant_id: int, candidate: Any, segmento: str, cidade: str) -> tuple[str, bool]:
    """Store a candidate lead in the inventory."""
    lead = getattr(candidate, "lead", candidate)
    raw = _lead_to_dict(lead)
    raw["segmento"] = raw.get("segmento") or segmento
    raw["cidade"] = raw.get("cidade") or cidade
    key = dedupe_key(tenant_id, raw)
    inv_id = uuid.uuid4().hex
    score = int(getattr(candidate, "score", 0) or 0)
    tier = str(getattr(candidate, "tier", "") or "")
    caio_result = getattr(candidate, "caio_resultado", None)
    raw["caio_resultado"] = caio_result or {}
    row = db.execute(
        text(
            """
            INSERT INTO lead_inventory (
                id, tenant_id, origem, segmento, cidade, nome, telefone, whatsapp,
                rating, reviews_count, website, endereco, maps_url, place_id,
                dedupe_key, status, score_caio, tier, dados, atualizado_em
            )
            VALUES (
                :id, :uid, 'hunter', :segmento, :cidade, :nome, :telefone, :whatsapp,
                :rating, :reviews_count, :website, :endereco, :maps_url, :place_id,
                :dedupe, 'raw', :score, :tier, CAST(:dados AS jsonb), NOW()
            )
            ON CONFLICT (tenant_id, dedupe_key) DO NOTHING
            RETURNING id
            """
        ),
        {
            "id": inv_id,
            "uid": tenant_id,
            "segmento": raw.get("segmento") or segmento,
            "cidade": raw.get("cidade") or cidade,
            "nome": raw.get("nome") or "Lead sem nome",
            "telefone": raw.get("telefone") or "",
            "whatsapp": raw.get("whatsapp") or "",
            "rating": raw.get("rating") or 0.0,
            "reviews_count": raw.get("total_avaliacoes") or len(raw.get("reviews") or []),
            "website": raw.get("website") or "",
            "endereco": raw.get("endereco") or "",
            "maps_url": raw.get("maps_url") or "",
            "place_id": raw.get("place_id") or "",
            "dedupe": key,
            "score": score,
            "tier": tier,
            "dados": json.dumps(raw, ensure_ascii=False, default=str),
        },
    ).fetchone()
    db.commit()
    if row:
        return str(row[0]), True
    existing = db.execute(
        text("SELECT id FROM lead_inventory WHERE tenant_id=:uid AND dedupe_key=:dedupe"),
        {"uid": tenant_id, "dedupe": key},
    ).fetchone()
    return str(existing[0]) if existing else inv_id, False


def _enqueue_caio(db: Session, tenant_id: int, inventory_id: str) -> None:
    """Enqueue a Caio qualification job for a lead."""
    job_queue.enqueue(
        db,
        tipo=SUPPLY_CAIO_JOB,
        payload={"inventory_id": inventory_id},
        tenant_id=tenant_id,
        max_attempts=2,
        idempotency_key=f"lead-caio-{inventory_id}",
        priority=1,
        run_id=uuid.uuid4().hex[:12],
    )


def _existing_names(db: Session, tenant_id: int, cidade: str) -> set[str]:
    """Get existing lead names for deduplication."""
    rows = db.execute(
        text(
            """
            SELECT lower(trim(nome)) FROM leads
            WHERE user_id=:uid
              AND lower(cidade)=lower(:cidade)
              AND (
                    COALESCE(processado, false) = true
                 OR lower(COALESCE(status, '')) IN ('processando','em_andamento','concluido')
              )
            UNION
            SELECT lower(trim(nome)) FROM lead_inventory
            WHERE tenant_id=:uid
              AND lower(cidade)=lower(:cidade)
              AND lower(COALESCE(status, '')) NOT IN ('error_retry')
            """
        ),
        {"uid": tenant_id, "cidade": cidade},
    ).fetchall()
    return {str(r[0]) for r in rows if r[0]}


def _reserve_next(db: Session, tenant_id: int) -> dict[str, Any] | None:
    """Reserve the next approved lead for production."""
    row = db.execute(
        text(
            """
            WITH next_lead AS (
                SELECT id
                FROM lead_inventory
                WHERE tenant_id=:uid
                  AND status='approved'
                  AND (locked_until IS NULL OR locked_until < NOW())
                ORDER BY score_caio DESC NULLS LAST, criado_em ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE lead_inventory li
            SET status='reserved',
                locked_by=:lock_id,
                locked_until=NOW() + INTERVAL '30 minutes',
                reservado_em=NOW(),
                atualizado_em=NOW()
            FROM next_lead
            WHERE li.id=next_lead.id
            RETURNING li.*
            """
        ),
        {"uid": tenant_id, "lock_id": f"prod-{uuid.uuid4().hex[:8]}"},
    ).fetchone()
    db.commit()
    return dict(row._mapping) if row else None


def _ensure_lead_row(db: Session, tenant_id: int, item: dict[str, Any]) -> str:
    """Ensure a lead row exists in the leads table."""
    if item.get("lead_id"):
        return str(item["lead_id"])
    lead_id = str(uuid.uuid4())
    dados = item.get("dados") if isinstance(item.get("dados"), dict) else json.loads(item.get("dados") or "{}")
    dados.update(
        {
            "endereco": item.get("endereco") or dados.get("endereco") or "",
            "website": item.get("website") or dados.get("website") or "",
            "maps_url": item.get("maps_url") or dados.get("maps_url") or "",
            "total_avaliacoes": int(item.get("reviews_count") or dados.get("total_avaliacoes") or 0),
            "inventory_id": item["id"],
        }
    )
    params = {
        "nome": item["nome"],
        "cidade": item.get("cidade") or "",
        "segmento": item.get("segmento") or "",
        "telefone": item.get("telefone") or "",
        "whatsapp": item.get("whatsapp") or "",
        "rating": item.get("rating") or 0.0,
        "score": item.get("score_caio") or 0,
        "tier": item.get("tier") or "STANDARD",
        "uid": tenant_id,
        "now": datetime.now().isoformat(),
        "dados": json.dumps(dados, ensure_ascii=False, default=str),
    }
    contact = params["telefone"] or params["whatsapp"]
    if contact:
        existing = db.execute(
            text(
                """
                SELECT id
                FROM leads
                WHERE user_id=:uid
                  AND lower(cidade)=lower(:cidade)
                  AND (telefone=:contact OR whatsapp=:contact)
                ORDER BY criado_em DESC
                LIMIT 1
                """
            ),
            {"uid": tenant_id, "cidade": params["cidade"], "contact": contact},
        ).fetchone()
        if existing:
            lead_id = str(existing[0])
            db.execute(
                text(
                    """
                    UPDATE leads
                    SET nome=:nome,
                        segmento=:segmento,
                        telefone=:telefone,
                        whatsapp=:whatsapp,
                        rating=:rating,
                        score=:score,
                        tier=:tier,
                        status='processando',
                        processado=false,
                        atualizado_em=:now,
                        dados_completos=:dados
                    WHERE id=:id AND user_id=:uid
                    """
                ),
                {**params, "id": lead_id},
            )
            db.execute(
                text("UPDATE lead_inventory SET lead_id=:lead_id WHERE id=:id AND tenant_id=:uid"),
                {"lead_id": lead_id, "id": item["id"], "uid": tenant_id},
            )
            db.commit()
            return lead_id
    db.execute(
        text(
            """
            INSERT INTO leads (
                id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,
                user_id,criado_em,atualizado_em,processado,tentativas,dados_completos
            )
            VALUES (
                :id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,
                'processando',:uid,:now,:now,false,0,:dados
            )
            ON CONFLICT (id) DO UPDATE SET
                status='processando', atualizado_em=EXCLUDED.atualizado_em
            """
        ),
        {**params, "id": lead_id},
    )
    db.execute(
        text("UPDATE lead_inventory SET lead_id=:lead_id WHERE id=:id AND tenant_id=:uid"),
        {"lead_id": lead_id, "id": item["id"], "uid": tenant_id},
    )
    db.commit()
    return lead_id


def handle_pipeline_job_finished(
    db: Session,
    job: dict[str, Any],
    *,
    success: bool,
    job_status: str,
    fase: str | None = None,
    mensagem: str | None = None,
) -> None:
    """Handle a pipeline job finished event."""
    payload = dict(job.get("payload") or {})
    inv_id = payload.get("_inventory_id")
    tenant_id = job.get("tenant_id")
    if not inv_id or not tenant_id:
        return
    ensure_schema(db)
    if success:
        db.execute(
            text(
                """
                UPDATE lead_inventory
                SET status='site_done', produzido_em=NOW(), erro=NULL,
                    locked_by=NULL, locked_until=NULL, atualizado_em=NOW()
                WHERE id=:id AND tenant_id=:uid
                """
            ),
            {"id": inv_id, "uid": tenant_id},
        )
        db.commit()
        _event(db, tenant_id, "producao", "success", "Site concluído. Próximo lead será puxado pelo controle de plano.")
        enqueue_production_tick(db, tenant_id, delay_seconds=5, reason="pipeline-success")
        sync_supply(db, tenant_id)
        return
    if job_status == "pending":
        db.execute(
            text(
                """
                UPDATE lead_inventory
                SET erro=:erro, atualizado_em=NOW()
                WHERE id=:id AND tenant_id=:uid
                """
            ),
            {"erro": (mensagem or fase or "retry automático")[:1000], "id": inv_id, "uid": tenant_id},
        )
        db.commit()
        return
    db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status='error_retry', erro=:erro, locked_by=NULL,
                locked_until=NULL, atualizado_em=NOW()
            WHERE id=:id AND tenant_id=:uid
            """
        ),
        {"erro": (mensagem or fase or "pipeline falhou")[:1000], "id": inv_id, "uid": tenant_id},
    )
    db.commit()
    _event(db, tenant_id, "producao", "error", "Pipeline falhou para um lead aprovado. Lead ficou em erro para revisão.")
    lead_id = payload.get("_lead_id_existente") or payload.get("lead_id")
    if lead_id:
        try:
            db.execute(
                text(
                    """
                    UPDATE leads
                    SET status='erro_pipeline',
                        erro_pipeline=:erro,
                        atualizado_em=NOW()
                    WHERE id=:lead_id
                      AND user_id=:uid
                      AND status NOT IN ('concluido', 'descartado')
                    """
                ),
                {
                    "lead_id": lead_id,
                    "uid": tenant_id,
                    "erro": (mensagem or fase or "pipeline falhou")[:500],
                },
            )
            db.commit()
        except Exception:
            db.rollback()
    enqueue_production_tick(db, tenant_id, delay_seconds=5, reason="pipeline-failure")


def reap_stale_inventory_locks(
    db: Session,
    tenant_id: int | None = None,
    *,
    apply: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Reconcile expired inventory locks without changing lead production truth."""
    ensure_schema(db)
    params: dict[str, Any] = {"limit": max(1, min(int(limit or 200), 1000))}
    tenant_filter = ""
    if tenant_id is not None:
        tenant_filter = "AND li.tenant_id = :tenant_id"
        params["tenant_id"] = int(tenant_id)
    rows = db.execute(
        text(
            f"""
            SELECT li.id, li.tenant_id, li.status, li.lead_id, li.locked_by,
                   li.locked_until, li.erro, l.status AS lead_status
            FROM lead_inventory li
            LEFT JOIN leads l ON l.id = li.lead_id AND l.user_id = li.tenant_id
            WHERE li.status IN ('reserved', 'in_production', 'processing')
              AND li.locked_until IS NOT NULL
              AND li.locked_until < CURRENT_TIMESTAMP
              {tenant_filter}
            ORDER BY li.locked_until ASC
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()

    # Busca todos os jobs ativos de uma vez (1 query em vez de N)
    tenant_ids = list({row["tenant_id"] for row in rows})
    if tenant_ids:
        active_jobs = db.execute(
            text(
                """
                SELECT j.id, j.tenant_id, j.payload
                FROM jobs j
                WHERE j.tenant_id = ANY(:tenant_ids)
                  AND j.status IN ('pending', 'running', 'failed_retriable')
                """
            ),
            {"tenant_ids": tenant_ids},
        ).mappings().all()
    else:
        active_jobs = []

    jobs_by_inventory: dict[str, dict[str, Any]] = {}
    for job in active_jobs:
        try:
            payload = json.loads(job["payload"])
        except Exception:
            payload = {}
        inv_id = str(payload.get("_inventory_id", "")) if isinstance(payload, dict) else ""
        if inv_id:
            jobs_by_inventory[inv_id] = job

    actions: list[dict[str, Any]] = []
    for row in rows:
        inv_id = str(row["id"])
        active_job = jobs_by_inventory.get(inv_id)
        if active_job:
            actions.append(
                {
                    "inventory_id": inv_id,
                    "tenant_id": row["tenant_id"],
                    "action": "keep_active_job",
                    "job_id": active_job["id"],
                    "status": row["status"],
                }
            )
            continue
        if row.get("lead_status") == "concluido":
            new_status = "site_done"
            reason = "lead_concluido"
        elif row["status"] == "reserved" and not row.get("lead_id"):
            new_status = "approved"
            reason = "reserved_without_lead_expired"
        else:
            new_status = "quality_hold"
            reason = "stale_inventory_lock_without_active_job"
        actions.append(
            {
                "inventory_id": inv_id,
                "tenant_id": row["tenant_id"],
                "from_status": row["status"],
                "to_status": new_status,
                "reason": reason,
                "lead_id": row.get("lead_id"),
                "lead_status": row.get("lead_status"),
                "apply": bool(apply),
            }
        )
        if apply:
            db.execute(
                text(
                    """
                    UPDATE lead_inventory
                    SET status=:status,
                        locked_by=NULL,
                        locked_until=NULL,
                        erro=:erro,
                        atualizado_em=CURRENT_TIMESTAMP
                    WHERE id=:id AND tenant_id=:tenant_id
                    """
                ),
                {
                    "status": new_status,
                    "erro": "" if new_status in {"approved", "site_done"} else reason,
                    "id": inv_id,
                    "tenant_id": row["tenant_id"],
                },
            )
    if apply:
        db.commit()
    else:
        db.rollback()
    return {
        "ok": True,
        "apply": bool(apply),
        "checked": len(rows),
        "actions": actions,
    }


def sync_supply(db: Session, tenant_id: int) -> dict[str, Any]:
    """Sync the lead supply based on current status."""
    current = status(db, tenant_id, limit=1)
    cfg = current["config"]
    counts = current["counts"]
    hunter_configured = bool(cfg.get("segmentos")) and bool(cfg.get("cidades"))
    if cfg["ativo"] and not cfg["hunter_pausado"] and hunter_configured:
        useful = sum(counts.get(k, 0) for k in ("raw", "qualifying", "approved", "reserved", "in_production"))
        if useful < int(cfg["estoque_minimo"]):
            enqueue_hunter(db, tenant_id, delay_seconds=1, force=True)
    if cfg["ativo"] and not cfg["producao_pausada"] and counts.get("approved", 0) > 0:
        enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="sync")
    return current


def enqueue_hunter(db: Session, tenant_id: int, *, delay_seconds: int = 0, force: bool = False) -> int | None:
    """Enqueue a Hunter job."""
    run_id = uuid.uuid4().hex[:12]
    idem = f"lead-supply-hunter-{tenant_id}-{int(datetime.utcnow().timestamp() // 60)}"
    return job_queue.enqueue(
        db,
        tipo=SUPPLY_HUNTER_JOB,
        payload={"force": force, "_run_id": run_id},
        tenant_id=tenant_id,
        max_attempts=2,
        idempotency_key=idem,
        delay_seconds=delay_seconds,
        priority=2,
        run_id=run_id,
    )


def enqueue_production_tick(db: Session, tenant_id: int, *, delay_seconds: int = 0, reason: str = "manual") -> int | None:
    """Enqueue a production tick job."""
    bucket = int(datetime.utcnow().timestamp() // max(1, min(delay_seconds or 30, 300)))
    run_id = uuid.uuid4().hex[:12]
    return job_queue.enqueue(
        db,
        tipo=PRODUCTION_TICK_JOB,
        payload={"reason": reason, "_run_id": run_id},
        tenant_id=tenant_id,
        max_attempts=1,
        idempotency_key=f"lead-production-tick-{tenant_id}-{bucket}",
        delay_seconds=delay_seconds,
        priority=1,
        run_id=run_id,
    )


__all__ = [
    "status",
    "sync_supply",
    "_store_candidate",
    "_enqueue_caio",
    "_reserve_next",
    "_ensure_lead_row",
    "_lead_to_dict",
    "_compute_live_status",
    "handle_pipeline_job_finished",
    "reap_stale_inventory_locks",
    "enqueue_hunter",
    "enqueue_production_tick",
]
