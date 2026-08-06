"""Lead Supply Control Endpoints — alimentam o painel admin.html (Central de Comando).

Endpoints expostos:
  GET    /api/lead-supply/status
  POST   /api/lead-supply/config
  POST   /api/lead-supply/start
  POST   /api/lead-supply/pause
  POST   /api/lead-supply/refill
  POST   /api/lead-supply/production/tick
  POST   /api/lead-supply/retry-all
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys
import json
import logging
from datetime import datetime, timezone

sys.path.append("/opt/fralib/backend")
sys.path.append("/opt/fralib/backend/core")

from database import get_db
from auth import get_current_user

logger = logging.getLogger("fralib.lead_supply")

router = APIRouter(prefix="/api/lead-supply", tags=["lead-supply"])


# ─── Models ──────────────────────────────────────────────────────────────────

class SupplyConfigIn(BaseModel):
    segmentos: list[str] = Field(default_factory=list)
    cidades: list[str] = Field(default_factory=list)
    meta_diaria: int = 1
    score_minimo: int = 45
    estoque_minimo: int = 3
    estoque_alvo: int = 10
    ativo: bool = True


class LeadSupplyItem(BaseModel):
    id: str
    nome: str
    cidade: str
    segmento: str
    status: str
    score_caio: int | None = None
    tier: str | None = None
    criado_em: str | None = None


class LeadSupplyStatus(BaseModel):
    config: dict
    inventory: list[dict]
    events: list[dict]
    actions: dict


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _tenant_id(usuario: dict) -> int:
    return usuario.get("tenant_id", usuario["id"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_inventory(row) -> dict:
    """Convert a lead_inventory row to dict with safe types."""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    # Convert datetime to string
    for k in ("criado_em", "atualizado_em", "reservado_em", "produzido_em", "locked_until"):
        v = d.get(k)
        if v is not None:
            d[k] = str(v)
    # Ensure score_caio is int or None
    sc = d.get("score_caio")
    d["score_caio"] = int(sc) if sc is not None else None
    return d


# ─── GET /status ─────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Retorna config + inventário + eventos recentes do lead supply."""
    uid = _tenant_id(usuario)

    # ── Config ──
    config_row = db.execute(text(
        "SELECT id, segmentos, cidades, meta_diaria, score_minimo, "
        "estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada, "
        "criado_em, atualizado_em "
        "FROM lead_supply_config WHERE tenant_id = :uid LIMIT 1"
    ), {"uid": uid}).fetchone()

    config = {
        "segmentos": [],
        "cidades": [],
        "meta_diaria": 1,
        "score_minimo": 45,
        "estoque_minimo": 3,
        "estoque_alvo": 10,
        "ativo": False,
        "hunter_pausado": False,
        "producao_pausada": False,
    }
    if config_row:
        d = dict(config_row._mapping)
        for k in ("segmentos", "cidades"):
            v = d.get(k)
            config[k] = json.loads(v) if isinstance(v, str) and v else (v or [])
        for k in ("meta_diaria", "score_minimo", "estoque_minimo", "estoque_alvo"):
            config[k] = d.get(k, config[k])
        config["ativo"] = bool(d.get("ativo", False))
        config["hunter_pausado"] = bool(d.get("hunter_pausado", False))
        config["producao_pausada"] = bool(d.get("producao_pausada", False))

    # ── Inventory ──
    inv_rows = db.execute(text(
        "SELECT id, nome, cidade, segmento, status, score_caio, tier, "
        "erro, criado_em, reservado_em "
        "FROM lead_inventory WHERE tenant_id = :uid "
        "ORDER BY criado_em DESC LIMIT 30"
    ), {"uid": uid}).fetchall()
    inventory = [_row_to_inventory(r) for r in inv_rows]

    # ── Events (últimos 20) ──
    event_rows = db.execute(text(
        "SELECT id, tipo, evento, nivel, mensagem, origem, payload, criado_em "
        "FROM lead_supply_events WHERE tenant_id = :uid "
        "ORDER BY criado_em DESC LIMIT 20"
    ), {"uid": uid}).fetchall()
    events = []
    for r in event_rows:
        d = dict(r._mapping)
        d["criado_em"] = str(d.get("criado_em", ""))
        payload = d.get("payload")
        if isinstance(payload, str):
            try:
                d["payload"] = json.loads(payload)
            except Exception:
                pass
        events.append(d)

    # ── Actions (próximos passos sugeridos) ──
    approved_count = sum(1 for i in inventory if i.get("status") == "approved")
    raw_count = sum(1 for i in inventory if i.get("status") == "raw")
    error_count = sum(1 for i in inventory if i.get("status") in ("error_retry", "discarded"))

    actions = {
        "hunter_pode_rodar": config.get("ativo") and not config.get("hunter_pausado"),
        "producao_pode_rodar": config.get("ativo") and not config.get("producao_pausada"),
        "precisa_refill": raw_count < config.get("estoque_minimo", 3) and approved_count < config.get("estoque_alvo", 10),
        "aprovados_disponiveis": approved_count,
        "em_estoque": raw_count,
        "em_erro": error_count,
        "meta_diaria": config.get("meta_diaria", 1),
        "score_minimo": config.get("score_minimo", 45),
    }

    return {
        "config": config,
        "inventory": inventory,
        "events": events,
        "actions": actions,
    }


# ─── POST /config ────────────────────────────────────────────────────────────

@router.post("/config")
async def save_config(
    payload: SupplyConfigIn,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Salva ou atualiza a configuração do lead supply."""
    uid = _tenant_id(usuario)

    seg_json = json.dumps(payload.segmentos)
    cid_json = json.dumps(payload.cidades)

    db.execute(text("""
        INSERT INTO lead_supply_config
            (tenant_id, segmentos, cidades, meta_diaria, score_minimo,
             estoque_minimo, estoque_alvo, ativo, hunter_pausado, producao_pausada,
             atualizado_em)
        VALUES (:uid, :seg, :cid, :meta, :score, :emin, :eal, :ativo, false, false, NOW())
        ON CONFLICT (tenant_id) DO UPDATE SET
            segmentos = :seg,
            cidades = :cid,
            meta_diaria = :meta,
            score_minimo = :score,
            estoque_minimo = :emin,
            estoque_alvo = :eal,
            ativo = :ativo,
            atualizado_em = NOW()
    """), {
        "uid": uid, "seg": seg_json, "cid": cid_json,
        "meta": payload.meta_diaria, "score": payload.score_minimo,
        "emin": payload.estoque_minimo, "eal": payload.estoque_alvo,
        "ativo": payload.ativo,
    })
    db.commit()

    return {"ok": True, "saved": True}


# ─── POST /start ─────────────────────────────────────────────────────────────

@router.post("/start")
async def start_supply(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Liga a esteira: cria pipeline imediata + ativa config."""
    uid = _tenant_id(usuario)

    # Ativar config
    db.execute(text("""
        UPDATE lead_supply_config SET ativo = true, atualizado_em = NOW()
        WHERE tenant_id = :uid
    """), {"uid": uid})
    db.commit()

    # Verificar se já tem pipeline rodando
    running = db.execute(text(
        "SELECT id FROM jobs WHERE tenant_id = :uid AND tipo = 'pipeline_lead' "
        "AND status IN ('pending','running') LIMIT 1"
    ), {"uid": uid}).fetchone()

    if running:
        return {"immediate": {"duplicate_job": True}, "job_id": running[0]}

    # Enfileirar hunter + caio para buscar leads
    try:
        from backend.services.lead_supply_inventory import enqueue_hunter
        job_id = enqueue_hunter(db, uid, delay_seconds=0, force=True)
        if job_id:
            return {"job_id": str(job_id)}
    except Exception as e:
        logger.warning(f"[lead-supply] enqueue_hunter falhou: {e}")

    return {"ok": True, "message": "Esteira ativada — hunter será acionado no próximo ciclo."}


# ─── POST /pause ─────────────────────────────────────────────────────────────

@router.post("/pause")
async def pause_supply(
    payload: dict,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Pausa/despausa hunter e/ou produção."""
    uid = _tenant_id(usuario)
    hunter_pausado = bool(payload.get("hunter_pausado", False))
    producao_pausada = bool(payload.get("producao_pausada", False))

    db.execute(text("""
        UPDATE lead_supply_config
        SET hunter_pausado = :hp, producao_pausada = :pp, atualizado_em = NOW()
        WHERE tenant_id = :uid
    """), {"hp": hunter_pausado, "pp": producao_pausada, "uid": uid})
    db.commit()

    return {
        "ok": True,
        "hunter_pausado": hunter_pausado,
        "producao_pausada": producao_pausada,
    }


# ─── POST /refill ────────────────────────────────────────────────────────────

@router.post("/refill")
async def refill_supply(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Força o Hunter a buscar novos leads (scrape)."""
    uid = _tenant_id(usuario)

    try:
        from backend.services.lead_supply_inventory import enqueue_hunter
        job_id = enqueue_hunter(db, uid, delay_seconds=5, force=True)
        return {"ok": True, "job_id": str(job_id) if job_id else None}
    except Exception as e:
        logger.warning(f"[lead-supply] refill falhou: {e}")
        return {"ok": True, "message": "Hunter enfileirado."}


# ─── POST /production/tick ───────────────────────────────────────────────────

@router.post("/production/tick")
async def production_tick(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Tenta reservar 1 lead aprovado e abrir pipeline de produção."""
    uid = _tenant_id(usuario)

    try:
        from backend.services.lead_supply_inventory import (
            _reserve_next,
            enqueue_production_tick,
            _ensure_lead_row,
        )

        # Tentar reservar lead aprovado
        lead = _reserve_next(db, uid)
        if lead:
            return {
                "job_id": lead.get("id"),
                "lead_id": lead.get("lead_id"),
                "nome": lead.get("nome"),
            }

        # Nenhum aprovado disponível — chamar hunter
        enqueue_hunter(db, uid, delay_seconds=10, force=False)
        return {"waiting": "no_approved_lead"}

    except Exception as e:
        logger.warning(f"[lead-supply] production/tick falhou: {e}")
        return {"waiting": "error", "message": str(e)}


# ─── POST /retry-all ─────────────────────────────────────────────────────────

@router.post("/retry-all")
async def retry_all(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Reprocessa todos os leads em error_retry/discarded."""
    uid = _tenant_id(usuario)

    rows = db.execute(text("""
        SELECT id FROM lead_inventory
        WHERE tenant_id = :uid AND status IN ('error_retry', 'discarded')
    """), {"uid": uid}).fetchall()

    reprocessed = 0
    for r in rows:
        inv_id = r[0]
        try:
            db.execute(text("""
                UPDATE lead_inventory
                SET status = 'raw', erro = NULL, attempts = 0,
                    locked_by = NULL, locked_until = NULL, atualizado_em = NOW()
                WHERE id = :id AND tenant_id = :uid
            """), {"id": inv_id, "uid": uid})
            reprocessed += 1
        except Exception:
            pass

    db.commit()

    if reprocessed > 0:
        try:
            from backend.services.lead_supply_inventory import enqueue_hunter
            enqueue_hunter(db, uid, delay_seconds=5, force=False)
        except Exception:
            pass

    return {"ok": True, "reprocessed": reprocessed}
