"""Endpoints de telemetria: duracao media por fase, ultimo job ativo.

GET /api/pipeline/tempo?tenant_id=
    - fases: {buscar: {ultima_duracao_s, media_duracao_s, rodando, ultimo_inicio},
              analisar: {...},
              produzir: {...},
              publicar: {...}}
    - ativo: bool (algum job running nos ultimos 60s)
    - ultimo_job: {id, tipo, status, lead_nome, fase_atual, duracao_s, started_at}
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

import os, sys
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

from backend.core.database import get_db
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/pipeline", tags=["pipeline-tempo"])

_PHASES = ["buscar", "analisar", "produzir", "publicar"]


def _phase_for_fase_nome(fase_nome: str | None) -> str:
    """Mapeia nome de fase do pipeline para um dos 4 macro-estados."""
    if not fase_nome:
        return ""
    f = fase_nome.lower()
    # buscar = hunter, captura, lead_supply
    if any(t in f for t in ("hunter", "captura", "lead_supply", "jina", "supply")):
        return "buscar"
    if any(t in f for t in ("nicho", "benchmark", "variacao", "arquiteto", "designer", "analis")):
        return "analisar"
    if any(t in f for t in ("builder", "renderer", "vite", "produzir", "site_build")):
        return "produzir"
    if any(t in f for t in ("deploy", "public", "franz", "outreach", "sdr")):
        return "publicar"
    return ""


@router.get("/tempo")
async def pipeline_tempo(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Retorna duracao media + ultimo status por macro-fase."""
    tenant_id = int(user["id"])

    # Query: ultimas 50 spans do tenant, agrupadas por macro-fase
    rows = db.execute(
        text("""
            SELECT id, fase_nome, agente, modelo,
                   started_at, finished_at, duracao_ms, status,
                   lead_id, erro
            FROM pipeline_run_spans
            WHERE tenant_id = :tid
              AND started_at > NOW() - INTERVAL '24 hours'
            ORDER BY started_at DESC
            LIMIT 200
        """),
        {"tid": tenant_id},
    ).fetchall()

    # Agrupa por macro-fase
    phases_data = {
        ph: {
            "ultima_duracao_s": None,
            "media_duracao_s": None,
            "rodando": False,
            "ultimo_inicio": None,
            "ultimo_agente": None,
            "ultimo_status": None,
        }
        for ph in _PHASES
    }
    durations_by_phase: dict[str, list[int]] = {ph: [] for ph in _PHASES}
    latest_started_by_phase: dict[str, object] = {ph: None for ph in _PHASES}

    for r in rows:
        fase = r[1] or ""
        macro = _phase_for_fase_nome(fase)
        if macro not in _PHASES:
            continue
        duracao_ms = r[6]
        status = r[7]
        started_at = r[4]
        agente = r[2]
        if duracao_ms and duracao_ms > 0:
            durations_by_phase[macro].append(int(duracao_ms))
        if latest_started_by_phase[macro] is None or (
            started_at and started_at > latest_started_by_phase[macro]["started_at"]
        ):
            latest_started_by_phase[macro] = {
                "started_at": started_at,
                "agente": agente,
                "status": status,
                "duracao_ms": duracao_ms,
                "error_message": r[9] if len(r) > 9 else None,
            }

    for ph in _PHASES:
        durs = durations_by_phase[ph]
        if durs:
            phases_data[ph]["media_duracao_s"] = round(sum(durs) / len(durs) / 1000, 1)
            phases_data[ph]["ultima_duracao_s"] = round(max(durs) / 1000, 1)
        latest = latest_started_by_phase[ph]
        if latest:
            phases_data[ph]["ultimo_inicio"] = latest["started_at"].isoformat() if latest["started_at"] else None
            phases_data[ph]["ultimo_agente"] = latest["agente"]
            phases_data[ph]["ultimo_status"] = latest["status"]
            phases_data[ph]["rodando"] = latest["status"] == "running"

    # Job ativo: o mais recente que esta rodando agora
    ativo_row = db.execute(
        text("""
            SELECT j.id, j.tipo, j.status, l.nome, j.iniciado_em, j.last_phase
            FROM jobs j
            LEFT JOIN leads l ON l.id = j.lead_id AND l.user_id = j.tenant_id
            WHERE j.tenant_id = :tid
              AND j.status = 'running'
              AND j.worker_heartbeat > NOW() - INTERVAL '120 seconds'
            ORDER BY j.iniciado_em DESC
            LIMIT 1
        """),
        {"tid": tenant_id},
    ).fetchone()

    ativo = False
    ultimo_job = None
    if ativo_row:
        ativo = True
        jid, jtipo, jstatus, lnome, jiniciado, jphase = ativo_row
        duracao_s = None
        if jiniciado:
            try:
                delta = (datetime_utcnow() - jiniciado).total_seconds()
                duracao_s = int(delta)
            except Exception:
                pass
        ultimo_job = {
            "id": jid,
            "tipo": jtipo,
            "status": jstatus,
            "lead_nome": lnome or "—",
            "fase_atual": jphase or "—",
            "duracao_s": duracao_s,
            "started_at": jiniciado.isoformat() if jiniciado else None,
        }

    # Ultimo job completed (mesmo que nao esteja rodando agora)
    ultimo_completed_row = db.execute(
        text("""
            SELECT j.id, j.tipo, j.status, l.nome, j.concluido_em, j.last_phase
            FROM jobs j
            LEFT JOIN leads l ON l.id = j.lead_id AND l.user_id = j.tenant_id
            WHERE j.tenant_id = :tid
              AND j.status IN ('completed', 'failed_permanent')
            ORDER BY j.concluido_em DESC NULLS LAST
            LIMIT 1
        """),
        {"tid": tenant_id},
    ).fetchone()

    ultimo_completed = None
    if ultimo_completed_row:
        jid, jtipo, jstatus, lnome, jconc, jphase = ultimo_completed_row
        ultimo_completed = {
            "id": jid,
            "tipo": jtipo,
            "status": jstatus,
            "lead_nome": lnome or "—",
            "fase_atual": jphase or "—",
            "concluido_em": jconc.isoformat() if jconc else None,
        }

    # Sprint 14.10: detecta jobs zumbis (running + heartbeat velho) ANTES
    # do reap_dead_workers do worker agir. Retorna lista explicita para
    # o admin alertar.
    zumbi_rows = db.execute(
        text("""
            SELECT j.id, j.tipo, j.worker_id, j.last_phase,
                   j.iniciado_em, j.worker_heartbeat,
                   EXTRACT(EPOCH FROM (NOW() - j.worker_heartbeat))::INT AS heartbeat_age_s,
                   j.last_error
            FROM jobs j
            WHERE j.tenant_id = :tid
              AND j.status = 'running'
              AND (j.worker_heartbeat IS NULL
                   OR j.worker_heartbeat < NOW() - INTERVAL '5 minutes')
            ORDER BY j.worker_heartbeat NULLS FIRST
            LIMIT 20
        """),
        {"tid": tenant_id},
    ).fetchall()

    zumbis = [
        {
            "id": r[0],
            "tipo": r[1],
            "worker_id": r[2],
            "fase": r[3],
            "started_at": r[4].isoformat() if r[4] else None,
            "heartbeat_at": r[5].isoformat() if r[5] else None,
            "heartbeat_age_s": r[6],
            "last_error": r[7],
        }
        for r in zumbi_rows
    ]

    return {
        "tenant_id": tenant_id,
        "ativo": ativo,
        "ultimo_job": ultimo_job,
        "ultimo_completed": ultimo_completed,
        "fases": phases_data,
        "zumbis": zumbis,
        "tem_zumbi": len(zumbis) > 0,
    }


def datetime_utcnow():
    """Wrapper para evitar import circular no topo."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


@router.post("/zumbis/ressuscitar")
async def ressuscitar_zumbis(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Sprint 14.10: ressuscita manualmente jobs zumbis do tenant.

    Job zumbi = status='running' + heartbeat > 5min OU heartbeat NULL.
    Acao: UPDATE status='pending', attempts-=1, last_error+=worker_died,
          worker_id=NULL, next_retry_at=NOW().

    Retorna { ressuscitados, ja_ressuscitados } para feedback no admin.
    """
    from sqlalchemy import text
    tenant_id = int(user["id"])

    # Ressuscita jobs com heartbeat NULL ou > 5min
    result = db.execute(
        text("""
            UPDATE jobs
            SET status = 'pending',
                attempts = GREATEST(attempts - 1, 0),
                last_error = COALESCE(last_error || ' | ', '') || 'zumbi_ressuscitado_manual',
                worker_id = NULL,
                worker_heartbeat = NULL,
                next_retry_at = NOW()
            WHERE tenant_id = :tid
              AND status = 'running'
              AND (worker_heartbeat IS NULL
                   OR worker_heartbeat < NOW() - INTERVAL '5 minutes')
            RETURNING id
        """),
        {"tid": tenant_id},
    )
    ressuscitados = [row[0] for row in result.fetchall()]
    db.commit()
    return {
        "ok": True,
        "ressuscitados": ressuscitados,
        "count": len(ressuscitados),
    }
