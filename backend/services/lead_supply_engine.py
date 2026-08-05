"""Lead inventory engine: Hunter/Caio supply separated from site production."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core import job_queue


PIPELINE_TYPES = ("pipeline_lead", "pipeline_multiplos", "pipeline_main")
SUPPLY_HUNTER_JOB = "lead_supply_hunter"
SUPPLY_CAIO_JOB = "lead_supply_caio"
PRODUCTION_TICK_JOB = "lead_production_tick"

# Quantas falhas consecutivas de pipeline (failed_permanent) antes de
# auto-pausar a producao. So acao humana (iniciar/retomar) reativa.
MAX_CONSECUTIVE_FAILURES = 3

PLAN_DAILY_CAPS = {
    "trial": 1,
    "free": 1,
    "starter": 6,
    "pro": 12,
    "beta": 12,
    "agency": 50,
    "ilimitado": 50,
    "admin": 50,
}


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = re.split(r"[,;\n]+", value)
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text_value = re.sub(r"\s+", " ", str(item or "").strip())
        key = text_value.lower()
        if text_value and key not in seen:
            cleaned.append(text_value)
            seen.add(key)
    return cleaned[:25]


def default_targets(plano: str, meta_diaria: int | None = None) -> dict[str, int]:
    plano_norm = (plano or "trial").lower()
    cap = PLAN_DAILY_CAPS.get(plano_norm, 1)
    daily = max(1, min(int(meta_diaria or cap), cap))
    monthly = daily * 30
    ideal = max(daily * 10, int(monthly * 1.2))
    minimum = max(daily * 3, int(ideal * 0.72))
    return {
        "meta_diaria": daily,
        "estoque_minimo": minimum,
        "estoque_alvo": ideal,
        "limite_diario_plano": cap,
    }


def dedupe_key(tenant_id: int, lead: dict[str, Any]) -> str:
    place = str(lead.get("place_id") or "").strip().lower()
    if place:
        marker = f"place:{place}"
    else:
        digits = re.sub(r"\D+", "", str(lead.get("whatsapp") or lead.get("telefone") or ""))
        if digits.startswith("55") and len(digits) > 11:
            digits = digits[2:]
        website = re.sub(r"^https?://(www\.)?", "", str(lead.get("website") or "").strip().lower()).split("/")[0]
        nome = _slug(str(lead.get("nome") or ""))
        cidade = _slug(str(lead.get("cidade") or ""))
        endereco = _slug(str(lead.get("endereco") or ""))[:48]
        if digits:
            marker = f"phone:{digits}"
        elif website:
            marker = f"web:{website}"
        else:
            marker = f"name:{nome}:{cidade}:{endereco}"
    return hashlib.sha1(f"{tenant_id}:{marker}".encode("utf-8")).hexdigest()


def _run_alter_safe(db: Session) -> None:
    """ALTER TABLE sem travar — verifica pg_catalog primeiro, so adquire lock se necessario."""
    exists = db.execute(
        text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='lead_supply_config' AND column_name='falhas_consecutivas'
        """)
    ).scalar()
    if not exists:
        try:
            db.execute(text("ALTER TABLE lead_supply_config ADD COLUMN IF NOT EXISTS falhas_consecutivas INTEGER NOT NULL DEFAULT 0"))
        except Exception:
            pass


def ensure_schema(db: Session) -> None:
    db.execute(text("DROP INDEX IF EXISTS idx_leads_unique"))
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_tenant_phone_city_unique
            ON leads (user_id, telefone, cidade)
            WHERE telefone IS NOT NULL AND trim(telefone) <> ''
              AND cidade IS NOT NULL AND trim(cidade) <> ''
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS lead_supply_config (
                tenant_id INTEGER PRIMARY KEY,
                segmentos JSONB NOT NULL DEFAULT '[]'::jsonb,
                cidades JSONB NOT NULL DEFAULT '[]'::jsonb,
                meta_diaria INTEGER NOT NULL DEFAULT 1,
                estoque_minimo INTEGER NOT NULL DEFAULT 3,
                estoque_alvo INTEGER NOT NULL DEFAULT 10,
                score_minimo INTEGER NOT NULL DEFAULT 45,
                provider VARCHAR(40) NOT NULL DEFAULT 'hunter',
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                hunter_pausado BOOLEAN NOT NULL DEFAULT FALSE,
                producao_pausada BOOLEAN NOT NULL DEFAULT FALSE,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS lead_requests (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                nicho TEXT NOT NULL,
                cidade TEXT NOT NULL,
                score_min INTEGER NOT NULL DEFAULT 45,
                quantidade_total INTEGER NOT NULL,
                quantidade_entregue INTEGER NOT NULL DEFAULT 0,
                quantidade_por_execucao INTEGER NOT NULL DEFAULT 10,
                status VARCHAR(20) NOT NULL DEFAULT 'enfileirado',
                modo VARCHAR(10) NOT NULL DEFAULT 'manual',
                cron_schedule VARCHAR(50),
                proxima_execucao TIMESTAMP,
                erro TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
    )
    _run_alter_safe(db)
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS lead_inventory (
                id VARCHAR(80) PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                origem VARCHAR(40) DEFAULT 'hunter',
                segmento VARCHAR(120),
                cidade VARCHAR(120),
                nome VARCHAR(255) NOT NULL,
                telefone VARCHAR(60),
                whatsapp VARCHAR(60),
                rating NUMERIC(3,1) DEFAULT 0,
                reviews_count INTEGER DEFAULT 0,
                website VARCHAR(500),
                endereco VARCHAR(700),
                maps_url VARCHAR(700),
                place_id VARCHAR(180),
                dedupe_key VARCHAR(80) NOT NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'raw',
                score_caio INTEGER DEFAULT 0,
                tier VARCHAR(40),
                caio_motivo TEXT,
                lead_id VARCHAR(100),
                dados JSONB NOT NULL DEFAULT '{}'::jsonb,
                erro TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                locked_by VARCHAR(80),
                locked_until TIMESTAMP,
                reservado_em TIMESTAMP,
                produzido_em TIMESTAMP,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_inventory_tenant_dedupe
            ON lead_inventory (tenant_id, dedupe_key)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_inventory_tenant_status
            ON lead_inventory (tenant_id, status, atualizado_em DESC)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS lead_supply_events (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                source VARCHAR(40) NOT NULL,
                level VARCHAR(20) NOT NULL DEFAULT 'info',
                message TEXT NOT NULL,
                payload JSONB DEFAULT '{}'::jsonb,
                criado_em TIMESTAMP DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_supply_events_tenant
            ON lead_supply_events (tenant_id, criado_em DESC)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pipeline_error_log (
                id SERIAL PRIMARY KEY,
                lead_id VARCHAR(100) NOT NULL,
                tenant_id INTEGER NOT NULL,
                step VARCHAR(60) NOT NULL,
                exception_type VARCHAR(120),
                message TEXT NOT NULL,
                traceback TEXT,
                fase_origem VARCHAR(40),
                criado_em TIMESTAMP DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_pipeline_error_log_tenant_lead
            ON pipeline_error_log (tenant_id, lead_id, criado_em DESC)
            """
        )
    )
    db.commit()


def get_user_plan(db: Session, tenant_id: int) -> str:
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    return (row[0] if row else "trial") or "trial"


def get_or_create_config(db: Session, tenant_id: int) -> dict[str, Any]:
    ensure_schema(db)
    row = db.execute(
        text("SELECT * FROM lead_supply_config WHERE tenant_id=:uid"),
        {"uid": tenant_id},
    ).fetchone()
    if not row:
        targets = default_targets(get_user_plan(db, tenant_id))
        db.execute(
            text(
                """
                INSERT INTO lead_supply_config (
                    tenant_id, meta_diaria, estoque_minimo, estoque_alvo, score_minimo
                )
                VALUES (:uid, :meta, :minimo, :alvo, 45)
                ON CONFLICT (tenant_id) DO NOTHING
                """
            ),
            {
                "uid": tenant_id,
                "meta": targets["meta_diaria"],
                "minimo": targets["estoque_minimo"],
                "alvo": targets["estoque_alvo"],
            },
        )
        db.commit()
        row = db.execute(
            text("SELECT * FROM lead_supply_config WHERE tenant_id=:uid"),
            {"uid": tenant_id},
        ).fetchone()
    return _row_to_config(row, db, tenant_id)


def save_config(db: Session, tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema(db)
    plano = get_user_plan(db, tenant_id)
    segmentos = normalize_list(payload.get("segmentos") or payload.get("nichos") or payload.get("segmento"))
    cidades = normalize_list(payload.get("cidades") or payload.get("cidade"))
    targets = default_targets(plano, payload.get("meta_diaria"))
    score_minimo = max(1, min(int(payload.get("score_minimo") or 45), 100))
    estoque_alvo = int(payload.get("estoque_alvo") or targets["estoque_alvo"])
    estoque_minimo = int(payload.get("estoque_minimo") or targets["estoque_minimo"])
    estoque_alvo = max(targets["meta_diaria"], min(estoque_alvo, targets["estoque_alvo"]))
    estoque_minimo = max(targets["meta_diaria"], min(estoque_minimo, estoque_alvo))
    db.execute(
        text(
            """
            INSERT INTO lead_supply_config (
                tenant_id, segmentos, cidades, meta_diaria, estoque_minimo,
                estoque_alvo, score_minimo, provider, ativo, hunter_pausado,
                producao_pausada, atualizado_em
            )
            VALUES (
                :uid, CAST(:segmentos AS jsonb), CAST(:cidades AS jsonb), :meta,
                :minimo, :alvo, :score, :provider, :ativo, :hunter_pausado,
                :producao_pausada, NOW()
            )
            ON CONFLICT (tenant_id) DO UPDATE SET
                segmentos=EXCLUDED.segmentos,
                cidades=EXCLUDED.cidades,
                meta_diaria=EXCLUDED.meta_diaria,
                estoque_minimo=EXCLUDED.estoque_minimo,
                estoque_alvo=EXCLUDED.estoque_alvo,
                score_minimo=EXCLUDED.score_minimo,
                provider=EXCLUDED.provider,
                ativo=EXCLUDED.ativo,
                hunter_pausado=EXCLUDED.hunter_pausado,
                producao_pausada=EXCLUDED.producao_pausada,
                atualizado_em=NOW()
            """
        ),
        {
            "uid": tenant_id,
            "segmentos": json.dumps(segmentos, ensure_ascii=False),
            "cidades": json.dumps(cidades, ensure_ascii=False),
            "meta": targets["meta_diaria"],
            "minimo": estoque_minimo,
            "alvo": estoque_alvo,
            "score": score_minimo,
            "provider": (payload.get("provider") or "hunter")[:40],
            "ativo": bool(payload.get("ativo", True)),
            "hunter_pausado": bool(payload.get("hunter_pausado", False)),
            "producao_pausada": bool(payload.get("producao_pausada", False)),
        },
    )
    db.commit()
    _event(db, tenant_id, "config", "info", "Configuração de abastecimento atualizada")
    return get_or_create_config(db, tenant_id)


def set_pause(db: Session, tenant_id: int, *, hunter: bool | None = None, production: bool | None = None, active: bool | None = None) -> dict[str, Any]:
    ensure_schema(db)
    get_or_create_config(db, tenant_id)
    updates = []
    params: dict[str, Any] = {"uid": tenant_id}
    if hunter is not None:
        updates.append("hunter_pausado=:hunter")
        params["hunter"] = bool(hunter)
    if production is not None:
        updates.append("producao_pausada=:production")
        params["production"] = bool(production)
    if active is not None:
        updates.append("ativo=:active")
        params["active"] = bool(active)
    if (active is True) or (production is False) or (hunter is False):
        # Reativacao manual: reseta contador de falhas do circuit breaker
        updates.append("falhas_consecutivas=0")
    if updates:
        db.execute(
            text(
                f"UPDATE lead_supply_config SET {', '.join(updates)}, atualizado_em=NOW() WHERE tenant_id=:uid"
            ),
            params,
        )
        db.commit()
    cfg = get_or_create_config(db, tenant_id)
    _event(db, tenant_id, "controle", "info", "Controle do motor atualizado")
    return cfg


def status(db: Session, tenant_id: int, limit: int = 30) -> dict[str, Any]:
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
              AND status IN (:st_pending, :st_running, :st_failed_retriable)
            GROUP BY tipo, status
            """
        ),
        {"uid": tenant_id, "st_pending": "pending", "st_running": "running", "st_failed_retriable": "failed_retriable"},
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
    # Ultimo lead Hunter (origem=hunter) e estatistica de buscas nas ultimas 24h
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
              AND criado_em > NOW() - make_interval(hours => 24)
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


def _compute_live_status(cfg: dict[str, Any], counts: dict[str, int], jobs: list[dict[str, Any]], events_rows: list[Any]) -> dict[str, Any]:
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


async def run_hunter_job(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    cfg = get_or_create_config(db, tenant_id)
    if not cfg["ativo"] or cfg["hunter_pausado"]:
        _event(db, tenant_id, "hunter", "info", "Hunter pausado pelo usuário")
        return {"ok": True, "paused": True}
    segmentos = normalize_list(payload.get("segmentos") or cfg["segmentos"])
    cidades = normalize_list(payload.get("cidades") or cfg["cidades"])
    if not segmentos or not cidades:
        _event(db, tenant_id, "hunter", "warning", "Informe ao menos um nicho e uma cidade")
        return {"ok": False, "error": "configuracao_incompleta"}
    counts = status(db, tenant_id, limit=1)["counts"]
    useful = sum(counts.get(k, 0) for k in ("raw", "qualifying", "approved", "reserved", "in_production"))
    needed = max(0, int(cfg["estoque_alvo"]) - useful)
    if payload.get("force"):
        needed = max(needed, int(payload.get("quantidade") or 1))
    if needed <= 0:
        _event(db, tenant_id, "hunter", "info", "Estoque alvo já está completo")
        return {"ok": True, "captured": 0, "needed": 0}

    batch_limit = max(1, min(int(os.getenv("LEAD_SUPPLY_HUNTER_BATCH", "8")), 20, needed))
    pairs = [(seg, cid) for seg in segmentos for cid in cidades]
    captured = 0
    _event(db, tenant_id, "hunter", "info", f"Hunter buscando até {batch_limit} lead(s) para abastecer estoque")

    from backend.agents.hunter.agent import get_agent

    hunter = get_agent()

    for segmento, cidade in pairs:
        if captured >= batch_limit:
            break
        try:
            result = await hunter.search(
                tenant_id=tenant_id,
                segmento=segmento,
                cidade=cidade,
                limite=max(1, batch_limit - captured),
            )
            leads = [lead.to_flat_dict() for lead in result.leads]
        except Exception as exc:
            _event(db, tenant_id, "hunter", "error", f"Hunter falhou em {segmento}/{cidade}: {str(exc)[:180]}")
            continue
        for candidate in leads or []:
            inv_id, inserted = _store_candidate(db, tenant_id, candidate, segmento, cidade)
            if inserted:
                captured += 1
                _enqueue_caio(db, tenant_id, inv_id)
            if captured >= batch_limit:
                break
    if captured:
        _event(db, tenant_id, "hunter", "success", f"Hunter adicionou {captured} lead(s) ao inventário")
    else:
        _event(db, tenant_id, "hunter", "warning", "Hunter não encontrou lead novo nesta rodada")
    return {"ok": True, "captured": captured, "needed": needed}


def run_caio_job(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
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

    from backend.agents.caio import LeadInput as CaioInput, qualificar_lead

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


def run_production_tick(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
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
              AND tipo IN (:tp_lead, :tp_multi, :tp_main)
              AND status IN (:st_pending, :st_running, :st_failed_retriable)
            """
        ),
        {
            "uid": tenant_id,
            "tp_lead": "pipeline_lead",
            "tp_multi": "pipeline_multiplos",
            "tp_main": "pipeline_main",
            "st_pending": "pending",
            "st_running": "running",
            "st_failed_retriable": "failed_retriable",
        },
    ).scalar() or 0
    if running:
        return {"ok": True, "waiting": "pipeline_running"}

    from backend.services.credits_manager import validar_permissao_pipeline

    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm.get("allowed"):
        if perm.get("reason") == "cooldown":
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
    # Verdade ou Silêncio: hidrata o lead_data na origem com o flat dict real
    # que o Hunter já capturou. Se vier vazio, segue vazio — o Manager marca
    # falha em step_hunter, nunca alucina dado fictício.
    dados = item.get("dados") if isinstance(item.get("dados"), dict) else json.loads(item.get("dados") or "{}")
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
        "lead_data": dados,
    }
    test_number = str(payload.get("_franz_test_number") or os.getenv("FRANZ_TEST_NUMBER", "")).strip()
    if test_number:
        payload_job["_franz_test_number"] = test_number
    # BUG FIX (2026-07-20): idempotency_key inclui run_id para permitir
    # re-processamento de lead que já teve pipeline no passado. O run_id
    # é único por tentativa, então não colide com jobs completed/failed.
    # A segurança contra duplicatas concorrentes já é garantida pelo
    # FOR UPDATE SKIP LOCKED em _reserve_next + status check.
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
        # Re-enfileira production_tick para tentar outro lead, senão
        # o sistema morre neste ponto para sempre.
        _event(db, tenant_id, "producao", "warning",
               f"Lead {item['nome']} já teve pipeline. Tentando próximo lead.")
        enqueue_production_tick(db, tenant_id, delay_seconds=2, reason="duplicate-retry")
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


def log_pipeline_error(
    db: Session,
    lead_id: str,
    tenant_id: int,
    step: str,
    exception_type: str,
    message: str,
    traceback_str: str | None = None,
) -> None:
    """Persiste erro de pipeline na tabela pipeline_error_log."""
    ensure_schema(db)
    db.execute(
        text(
            """
            INSERT INTO pipeline_error_log
                (lead_id, tenant_id, step, exception_type, message, traceback)
            VALUES (:lead_id, :tenant_id, :step, :exception_type, :message, :traceback)
            """
        ),
        {
            "lead_id": str(lead_id)[:100],
            "tenant_id": tenant_id,
            "step": str(step)[:60],
            "exception_type": str(exception_type)[:120],
            "message": str(message)[:1000],
            "traceback": str(traceback_str or "")[:10000],
        },
    )
    db.commit()


def handle_pipeline_job_finished(
    db: Session,
    job: dict[str, Any],
    *,
    success: bool,
    job_status: str,
    fase: str | None = None,
    mensagem: str | None = None,
) -> None:
    payload = dict(job.get("payload") or {})
    inv_id = payload.get("_inventory_id")
    tenant_id = job.get("tenant_id")
    if not inv_id or not tenant_id:
        return
    ensure_schema(db)
    if success:
        # Reseta contador de falhas ao primeiro sucesso
        db.execute(
            text("UPDATE lead_supply_config SET falhas_consecutivas=0, atualizado_em=NOW() WHERE tenant_id=:uid"),
            {"uid": tenant_id},
        )
        db.commit()
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

        # Hook: incrementa quantidade_entregue dos pedidos (lead_requests) com
        # mesma nicho+cidade, auto-conclui se atingiu meta. Garante que cada
        # pedido termina com site deployado.
        lead_id = payload.get("_lead_id_existente") or ""
        deploy_url = (
            payload.get("_deploy_url")
            or f"https://seunegociofralib.site/sites/{tenant_id}/"
        )
        try:
            from backend.services.lead_request_service import (
                ensure_table, increment_delivered,
            )
            ensure_table(db)
            item_row = db.execute(
                text(
                    "SELECT segmento, cidade FROM lead_inventory WHERE id=:id AND tenant_id=:tid"
                ),
                {"id": inv_id, "tid": tenant_id},
            ).mappings().first()
            if item_row:
                segmento = item_row["segmento"] or ""
                cidade = item_row["cidade"] or ""
                pedido_rows = db.execute(
                    text(
                        """
                        SELECT id FROM lead_requests
                        WHERE tenant_id=:tid
                          AND lower(trim(nicho))=lower(trim(:nicho))
                          AND lower(trim(cidade))=lower(trim(:cidade))
                          AND status IN ('executando', 'enfileirado')
                          AND quantidade_entregue < quantidade_total
                        """
                    ),
                    {
                        "tid": tenant_id,
                        "nicho": segmento,
                        "cidade": cidade,
                    },
                ).mappings().all()
                for p in pedido_rows:
                    increment_delivered(
                        db,
                        request_id=p["id"],
                        tenant_id=tenant_id,
                        lead_id=lead_id,
                        deploy_url=deploy_url,
                    )
                    _event(
                        db, tenant_id, "producao", "success",
                        f"Pedido #{p['id']} avançou (site deployado em {deploy_url})",
                    )
        except Exception as e:
            logger.warning(f"increment_delivered pedido falhou: {e}")

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
    # Circuit breaker: incrementa contador de falhas; se exceder limite, auto-pausa
    db.execute(
        text("UPDATE lead_supply_config SET falhas_consecutivas = falhas_consecutivas + 1, atualizado_em=NOW() WHERE tenant_id=:uid"),
        {"uid": tenant_id},
    )
    db.commit()
    cfg = get_or_create_config(db, tenant_id)
    falhas = cfg.get("falhas_consecutivas", 0)
    if falhas >= MAX_CONSECUTIVE_FAILURES:
        db.execute(
            text("UPDATE lead_supply_config SET producao_pausada=TRUE, ativo=FALSE, falhas_consecutivas=0, atualizado_em=NOW() WHERE tenant_id=:uid"),
            {"uid": tenant_id},
        )
        db.commit()
        _event(db, tenant_id, "producao", "critical",
               f"{falhas} falhas consecutivas. Produção auto-pausada. "
               "Apenas ação humana (iniciar/retomar) reativa.")
        return
    _event(db, tenant_id, "producao", "error",
           f"Pipeline falhou ({falhas}/{MAX_CONSECUTIVE_FAILURES} consecutivas). Lead em erro para revisão.")
    enqueue_production_tick(db, tenant_id, delay_seconds=5, reason="pipeline-failure")


def reap_stale_inventory_locks(
    db: Session,
    tenant_id: int | None = None,
    *,
    apply: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Reconcile expired inventory locks without changing lead production truth.

    `lead_inventory` is supply state only; `leads.status` remains the canonical
    site-production outcome. This reaper only releases or quarantines stale
    inventory reservations.
    """
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
    actions: list[dict[str, Any]] = []
    for row in rows:
        inv_id = str(row["id"])
        marker = f'"_inventory_id": "{inv_id}"'
        active_job = db.execute(
            text(
                """
                SELECT id, status
                FROM jobs
                WHERE tenant_id = :tenant_id
                  AND status IN ('pending', 'running', 'failed_retriable')
                  AND CAST(payload AS TEXT) LIKE :marker
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"tenant_id": row["tenant_id"], "marker": f"%{marker}%"},
        ).mappings().first()
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
    current = status(db, tenant_id, limit=1)
    cfg = current["config"]
    counts = current["counts"]
    if cfg["ativo"] and not cfg["hunter_pausado"]:
        useful = sum(counts.get(k, 0) for k in ("raw", "qualifying", "approved", "reserved", "in_production"))
        if useful < int(cfg["estoque_minimo"]):
            enqueue_hunter(db, tenant_id, delay_seconds=1, force=True)
    if cfg["ativo"] and not cfg["producao_pausada"] and counts.get("approved", 0) > 0:
        enqueue_production_tick(db, tenant_id, delay_seconds=1, reason="sync")
    return current


def enqueue_hunter(db: Session, tenant_id: int, *, delay_seconds: int = 0, force: bool = False) -> int | None:
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


def _store_candidate(db: Session, tenant_id: int, candidate: Any, segmento: str, cidade: str) -> tuple[str, bool]:
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


def _reserve_next(db: Session, tenant_id: int) -> dict[str, Any] | None:
    # 1. SELECT the next lead (FOR UPDATE SKIP LOCKED garante concorrencia)
    row = db.execute(
        text(
            """
            SELECT id, nome, dados, segmento, cidade, endereco, website,
                   maps_url, reviews_count, telefone, whatsapp, score_caio, lead_id,
                   tenant_id, criado_em
            FROM lead_inventory
            WHERE tenant_id=:uid
              AND status=:st_approved
              AND (locked_until IS NULL OR locked_until < NOW())
            ORDER BY score_caio DESC NULLS LAST, criado_em ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"uid": tenant_id, "st_approved": "approved"},
    ).fetchone()
    if not row:
        db.commit()
        return None

    row_dict = dict(row._mapping)
    lead_id = row_dict["id"]

    # 2. UPDATE status
    db.execute(
        text(
            """
            UPDATE lead_inventory
            SET status=:st_reserved,
                locked_by=:lock_id,
                locked_until=NOW() + make_interval(mins => 30),
                reservado_em=NOW(),
                atualizado_em=NOW()
            WHERE id=:lid
            """
        ),
        {
            "st_reserved": "reserved",
            "lock_id": f"prod-{uuid.uuid4().hex[:8]}",
            "lid": lead_id,
        },
    )
    db.commit()

    # 3. Return updated row
    row_dict["status"] = "reserved"
    return row_dict


def _ensure_lead_row(db: Session, tenant_id: int, item: dict[str, Any]) -> str:
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


def _existing_names(db: Session, tenant_id: int, cidade: str) -> set[str]:
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


def _event(db: Session, tenant_id: int, source: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
    ensure_schema(db)
    db.execute(
        text(
            """
            INSERT INTO lead_supply_events (tenant_id, source, level, message, payload)
            VALUES (:uid, :source, :level, :message, CAST(:payload AS jsonb))
            """
        ),
        {
            "uid": tenant_id,
            "source": source[:40],
            "level": level[:20],
            "message": message[:1000],
            "payload": json.dumps(payload or {}, ensure_ascii=False),
        },
    )
    db.commit()
    try:
        from backend.endpoints.sse_endpoints import adicionar_log

        adicionar_log(f"[{source}] {message}", level if level in {"info", "warning", "error", "success"} else "info", user_id=tenant_id)
    except Exception:
        pass


def _row_to_config(row: Any, db: Session, tenant_id: int) -> dict[str, Any]:
    data = dict(row._mapping)
    plano = get_user_plan(db, tenant_id)
    targets = default_targets(plano, data.get("meta_diaria"))
    segmentos = data.get("segmentos")
    cidades = data.get("cidades")
    if isinstance(segmentos, str):
        segmentos = json.loads(segmentos or "[]")
    if isinstance(cidades, str):
        cidades = json.loads(cidades or "[]")
    return {
        "tenant_id": tenant_id,
        "plano": plano,
        "segmentos": normalize_list(segmentos),
        "cidades": normalize_list(cidades),
        "meta_diaria": int(data.get("meta_diaria") or targets["meta_diaria"]),
        "estoque_minimo": int(data.get("estoque_minimo") or targets["estoque_minimo"]),
        "estoque_alvo": int(data.get("estoque_alvo") or targets["estoque_alvo"]),
        "score_minimo": int(data.get("score_minimo") or 45),
        "provider": data.get("provider") or "hunter",
        "ativo": bool(data.get("ativo", True)),
        "hunter_pausado": bool(data.get("hunter_pausado", False)),
        "producao_pausada": bool(data.get("producao_pausada", False)),
        "limite_diario_plano": targets["limite_diario_plano"],
        "falhas_consecutivas": int(data.get("falhas_consecutivas") or 0),
    }


def _lead_to_dict(lead: Any) -> dict[str, Any]:
    if isinstance(lead, dict):
        return dict(lead)
    if hasattr(lead, "model_dump"):
        return lead.model_dump()
    if hasattr(lead, "dict"):
        return lead.dict()
    return dict(getattr(lead, "__dict__", {}) or {})


def _slug(value: str) -> str:
    import unicodedata

    norm = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")


# Binding usado pelos endpoints/worker: `from ... import lead_supply_engine as supply`.
# Expõe o próprio módulo — todas as funções acima viram atributos (status, save_config,
# enqueue_hunter, run_hunter_job, run_production_tick, run_caio_job, etc.).
import sys as _sys

lead_supply_engine = _sys.modules[__name__]
