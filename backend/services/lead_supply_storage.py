"""Lead supply storage module - schema, config and state management."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core import job_queue

from backend.services.lead_supply_providers import (
    PLAN_DAILY_CAPS,
    PIPELINE_TYPES,
    PRODUCTION_TICK_JOB,
    SUPPLY_CAIO_JOB,
    SUPPLY_HUNTER_JOB,
)
from backend.services.lead_supply_filters import _slug, dedupe_key, default_targets, normalize_list


def ensure_schema(db: Session) -> None:
    """Ensure the lead supply schema exists in the database."""
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
    db.commit()


def get_user_plan(db: Session, tenant_id: int) -> str:
    """Get the user's plan."""
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    return (row[0] if row else "trial") or "trial"


def _row_to_config(row: Any, db: Session, tenant_id: int) -> dict[str, Any]:
    """Convert a database row to a config dictionary."""
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
    }


def get_or_create_config(db: Session, tenant_id: int) -> dict[str, Any]:
    """Get or create the lead supply config for a tenant."""
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
    """Save the lead supply configuration."""
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
    """Set pause state for the lead supply engine."""
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


def _event(db: Session, tenant_id: int, source: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
    """Log an event to the lead supply events table."""
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
        from sse_endpoints import adicionar_log

        adicionar_log(f"[{source}] {message}", level if level in {"info", "warning", "error", "success"} else "info", user_id=tenant_id)
    except Exception:
        pass


__all__ = [
    "ensure_schema",
    "get_or_create_config",
    "save_config",
    "get_user_plan",
    "set_pause",
    "_event",
    "_row_to_config",
]
