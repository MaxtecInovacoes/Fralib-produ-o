from fastapi import APIRouter, Depends
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.database import get_db, get_pipeline_state
from backend.core.auth import get_current_user
from backend.agents.pipeline_checkpoint import carregar_checkpoint as _load_ckpt
from backend.agents.pipeline_checkpoint import gerar_pipeline_id

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_COOLDOWN_POR_PLANO = {
    "trial": 0,
    "starter": 3600,
    "pro": 1800,
    "agency": 0,
    "ilimitado": 0,
    "beta": 1800,
    "free": 0,
}


_PHASE_INFO = {
    "hunter": (1, "Hunter"),
    "hunter_kw": (1, "Hunter"),
    "caio": (2, "Caio"),
    "jina": (3, "Jina"),
    "market_intelligence": (4, "Mercado"),
    "media": (5, "Midia"),
    "unsplash": (5, "Midia"),
    "prompt_agent": (6, "Agente de Prompt"),
    "agente_nicho": (6, "Agente de Prompt"),
    "agente_variacao": (7, "Variacao"),
    "variation": (7, "Variacao"),
    "arquiteto_mestre": (8, "Design"),
    "designer": (8, "Design"),
    "builder_renderer": (9, "Builder Renderer"),
    "deploy": (10, "Deploy"),
    "franz": (11, "Franz"),
    "bryan": (11, "Franz"),
}


def _phase_info(phase: str | None) -> tuple[int | None, str | None]:
    value = str(phase or "").strip().lower()
    if not value:
        return None, None
    if value in _PHASE_INFO:
        return _PHASE_INFO[value]
    if "builder" in value or "renderer" in value:
        return _PHASE_INFO["builder_renderer"]
    if "deploy" in value:
        return _PHASE_INFO["deploy"]
    if "franz" in value or "bryan" in value or "whatsapp" in value:
        return _PHASE_INFO["franz"]
    if "jina" in value or "keyword" in value or "mercado" in value:
        return _PHASE_INFO["jina"]
    if "caio" in value or "qualifica" in value:
        return _PHASE_INFO["caio"]
    if "hunter" in value or "lead" in value:
        return _PHASE_INFO["hunter"]
    return None, phase


def _current_pipeline_job(db: Session, tenant_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, tipo, status, last_phase, last_error, run_id,
                   worker_heartbeat, iniciado_em, criado_em, concluido_em
            FROM jobs
            WHERE tenant_id = :tenant_id
              AND tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
              AND status IN ('running', 'pending', 'failed_retriable')
            ORDER BY
                CASE status WHEN 'running' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
                COALESCE(iniciado_em, criado_em) DESC,
                id DESC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id},
    ).mappings().first()
    if not row:
        return None
    phase_num, phase_label = _phase_info(row.get("last_phase"))
    return {
        "id": row["id"],
        "tipo": row["tipo"],
        "status": row["status"],
        "last_phase": row["last_phase"],
        "phase_num": phase_num,
        "phase_label": phase_label,
        "last_error": (row["last_error"] or "")[:500] if row["last_error"] else None,
        "run_id": row["run_id"],
        "worker_heartbeat": row["worker_heartbeat"].isoformat()
        if row["worker_heartbeat"]
        else None,
        "iniciado_em": row["iniciado_em"].isoformat() if row["iniciado_em"] else None,
        "criado_em": row["criado_em"].isoformat() if row["criado_em"] else None,
        "concluido_em": row["concluido_em"].isoformat()
        if row["concluido_em"]
        else None,
    }


def _latest_pipeline_job(db: Session, tenant_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, tipo, status, last_phase, last_error, run_id,
                   worker_heartbeat, iniciado_em, criado_em, concluido_em
            FROM jobs
            WHERE tenant_id = :tenant_id
              AND tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
            ORDER BY COALESCE(iniciado_em, criado_em) DESC, id DESC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id},
    ).mappings().first()
    if not row:
        return None
    phase_num, phase_label = _phase_info(row.get("last_phase"))
    return {
        "id": row["id"],
        "tipo": row["tipo"],
        "status": row["status"],
        "last_phase": row["last_phase"],
        "phase_num": phase_num,
        "phase_label": phase_label,
        "last_error": (row["last_error"] or "")[:500]
        if row["last_error"]
        else None,
        "run_id": row["run_id"],
        "worker_heartbeat": row["worker_heartbeat"].isoformat()
        if row["worker_heartbeat"]
        else None,
        "iniciado_em": row["iniciado_em"].isoformat()
        if row["iniciado_em"]
        else None,
        "criado_em": row["criado_em"].isoformat() if row["criado_em"] else None,
        "concluido_em": row["concluido_em"].isoformat()
        if row["concluido_em"]
        else None,
    }


def _elapsed_seconds(job: dict) -> int:
    start_raw = job.get("iniciado_em")
    if not start_raw:
        return 0
    try:
        started = datetime.fromisoformat(str(start_raw))
        finished_raw = job.get("concluido_em")
        finished = datetime.fromisoformat(str(finished_raw)) if finished_raw else None
        now = datetime.now(tz=started.tzinfo) if started.tzinfo else datetime.now()
        return max(0, int(((finished or now) - started).total_seconds()))
    except (TypeError, ValueError):
        return 0


def _queued_seconds(job: dict) -> int:
    queued_raw = job.get("criado_em")
    if not queued_raw:
        return 0
    try:
        queued = datetime.fromisoformat(str(queued_raw))
        started_raw = job.get("iniciado_em")
        started = datetime.fromisoformat(str(started_raw)) if started_raw else None
        now = datetime.now(tz=queued.tzinfo) if queued.tzinfo else datetime.now()
        return max(0, int(((started or now) - queued).total_seconds()))
    except (TypeError, ValueError):
        return 0


def _pipeline_job_telemetry(db: Session, tenant_id: int, job: dict | None) -> dict | None:
    if not job:
        return None

    run_id = job.get("run_id")
    job_id = job.get("id")
    phases = []
    llm_by_phase = []

    if run_id:
        try:
            rows = db.execute(
                text(
                    """
                    SELECT fase_num, fase_nome, agente, modelo, status,
                           started_at, finished_at, duracao_ms,
                           input_tokens, output_tokens, cache_read_tokens,
                           cache_created_tokens, custo_usd, erro
                    FROM pipeline_run_spans
                    WHERE tenant_id = :tenant_id AND run_id = :run_id
                    ORDER BY started_at ASC, fase_num ASC, id ASC
                    """
                ),
                {"tenant_id": tenant_id, "run_id": run_id},
            ).mappings().all()
            for row in rows:
                phase_num = row.get("fase_num")
                if not phase_num:
                    phase_num, _ = _phase_info(row.get("fase_nome"))
                phases.append(
                    {
                        "phase_num": phase_num,
                        "phase": str(row.get("fase_nome") or ""),
                        "agent": str(row.get("agente") or ""),
                        "model": str(row.get("modelo") or ""),
                        "status": str(row.get("status") or "unknown"),
                        "started_at": row["started_at"].isoformat()
                        if row.get("started_at")
                        else None,
                        "finished_at": row["finished_at"].isoformat()
                        if row.get("finished_at")
                        else None,
                        "duration_ms": int(row.get("duracao_ms") or 0),
                        "input_tokens": int(row.get("input_tokens") or 0),
                        "output_tokens": int(row.get("output_tokens") or 0),
                        "cache_read_tokens": int(
                            row.get("cache_read_tokens") or 0
                        ),
                        "cache_created_tokens": int(
                            row.get("cache_created_tokens") or 0
                        ),
                        "cost_usd": float(row.get("custo_usd") or 0),
                        "error": str(row.get("erro") or "")[:300] or None,
                    }
                )
        except Exception:
            db.rollback()

    if job_id or run_id:
        try:
            rows = db.execute(
                text(
                    """
                    SELECT COALESCE(NULLIF(phase, ''), 'unknown') AS phase,
                           COALESCE(NULLIF(agent, ''), 'unknown') AS agent,
                           COALESCE(NULLIF(provider, ''), 'unknown') AS provider,
                           model,
                           COUNT(*) AS calls,
                           COALESCE(SUM(input_tokens), 0) AS input_tokens,
                           COALESCE(SUM(output_tokens), 0) AS output_tokens,
                           COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,
                           COALESCE(SUM(cache_created_tokens), 0) AS cache_created_tokens,
                           COALESCE(SUM(cost_usd), 0) AS cost_usd,
                           COALESCE(SUM(latency_ms), 0) AS latency_ms
                    FROM llm_budget_ledger
                    WHERE tenant_id = :tenant_id
                      AND (
                            (:job_id IS NOT NULL AND job_id = :job_id)
                         OR (job_id IS NULL AND :run_id IS NOT NULL AND run_id = :run_id)
                      )
                    GROUP BY phase, agent, provider, model
                    ORDER BY MIN(created_at) ASC
                    """
                ),
                {"tenant_id": tenant_id, "job_id": job_id, "run_id": run_id},
            ).mappings().all()
            llm_by_phase = [
                {
                    "phase": str(row.get("phase") or "unknown"),
                    "agent": str(row.get("agent") or "unknown"),
                    "provider": str(row.get("provider") or "unknown"),
                    "model": str(row.get("model") or "unknown"),
                    "calls": int(row.get("calls") or 0),
                    "input_tokens": int(row.get("input_tokens") or 0),
                    "output_tokens": int(row.get("output_tokens") or 0),
                    "cache_read_tokens": int(row.get("cache_read_tokens") or 0),
                    "cache_created_tokens": int(
                        row.get("cache_created_tokens") or 0
                    ),
                    "cost_usd": float(row.get("cost_usd") or 0),
                    "latency_ms": int(row.get("latency_ms") or 0),
                }
                for row in rows
            ]
        except Exception:
            db.rollback()

    totals = {
        "calls": sum(item["calls"] for item in llm_by_phase),
        "input_tokens": sum(item["input_tokens"] for item in llm_by_phase),
        "output_tokens": sum(item["output_tokens"] for item in llm_by_phase),
        "cache_read_tokens": sum(
            item["cache_read_tokens"] for item in llm_by_phase
        ),
        "cache_created_tokens": sum(
            item["cache_created_tokens"] for item in llm_by_phase
        ),
        "cost_usd": round(sum(item["cost_usd"] for item in llm_by_phase), 6),
        "latency_ms": sum(item["latency_ms"] for item in llm_by_phase),
    }
    totals["total_tokens"] = (
        totals["input_tokens"]
        + totals["output_tokens"]
        + totals["cache_read_tokens"]
        + totals["cache_created_tokens"]
    )

    return {
        "job_id": job_id,
        "run_id": run_id,
        "status": job.get("status"),
        "queued_at": job.get("criado_em"),
        "started_at": job.get("iniciado_em"),
        "finished_at": job.get("concluido_em"),
        "elapsed_seconds": _elapsed_seconds(job),
        "queued_seconds": _queued_seconds(job),
        "phases": phases,
        "llm": {"totals": totals, "by_phase": llm_by_phase},
        "measured": bool(phases or llm_by_phase),
    }


def _pipeline_runtime_summary(db: Session, tenant_id: int) -> dict:
    try:
        row = db.execute(
            text(
                """
                WITH recent AS (
                    SELECT id,
                           EXTRACT(EPOCH FROM (concluido_em - iniciado_em))::int AS elapsed_seconds
                    FROM jobs
                    WHERE tenant_id = :tenant_id
                      AND tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                      AND status = 'completed'
                      AND iniciado_em IS NOT NULL
                      AND concluido_em IS NOT NULL
                      AND concluido_em >= iniciado_em
                    ORDER BY concluido_em DESC, id DESC
                    LIMIT 20
                ),
                ledger AS (
                    SELECT job_id,
                           COUNT(*) AS calls,
                           COALESCE(SUM(input_tokens), 0)
                         + COALESCE(SUM(output_tokens), 0)
                         + COALESCE(SUM(cache_read_tokens), 0)
                         + COALESCE(SUM(cache_created_tokens), 0) AS total_tokens,
                           COALESCE(SUM(cost_usd), 0) AS cost_usd
                    FROM llm_budget_ledger
                    WHERE tenant_id = :tenant_id
                      AND job_id IN (SELECT id FROM recent)
                    GROUP BY job_id
                )
                SELECT COUNT(recent.id) AS sample_size,
                       COALESCE(AVG(recent.elapsed_seconds), 0) AS average_elapsed_seconds,
                       COALESCE(MIN(recent.elapsed_seconds), 0) AS fastest_seconds,
                       COALESCE(MAX(recent.elapsed_seconds), 0) AS slowest_seconds,
                       COALESCE(AVG(ledger.calls), 0) AS average_calls,
                       COALESCE(AVG(ledger.total_tokens), 0) AS average_tokens,
                       COALESCE(AVG(ledger.cost_usd), 0) AS average_cost_usd
                FROM recent
                LEFT JOIN ledger ON ledger.job_id = recent.id
                """
            ),
            {"tenant_id": tenant_id},
        ).mappings().first()
    except Exception:
        db.rollback()
        row = None
    if not row:
        return {
            "sample_size": 0,
            "average_elapsed_seconds": 0,
            "fastest_seconds": 0,
            "slowest_seconds": 0,
            "average_calls": 0,
            "average_tokens": 0,
            "average_cost_usd": 0,
        }
    return {
        "sample_size": int(row.get("sample_size") or 0),
        "average_elapsed_seconds": int(float(row.get("average_elapsed_seconds") or 0)),
        "fastest_seconds": int(row.get("fastest_seconds") or 0),
        "slowest_seconds": int(row.get("slowest_seconds") or 0),
        "average_calls": int(float(row.get("average_calls") or 0)),
        "average_tokens": int(float(row.get("average_tokens") or 0)),
        "average_cost_usd": round(float(row.get("average_cost_usd") or 0), 6),
    }


def _latest_pipeline_failure(db: Session, tenant_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT pf.mensagem_amigavel, pf.erro_tecnico, pf.fase, pf.criado_em,
                   j.last_error
            FROM pipeline_failures pf
            LEFT JOIN jobs j ON j.id = pf.job_id
            WHERE pf.tenant_id = :tenant_id
            ORDER BY pf.criado_em DESC, pf.id DESC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id},
    ).mappings().first()
    if not row:
        row = db.execute(
            text(
                """
                SELECT last_error, last_phase, concluido_em
                FROM jobs
                WHERE tenant_id = :tenant_id
                  AND tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                  AND status = 'failed_permanent'
                ORDER BY COALESCE(concluido_em, criado_em) DESC, id DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).mappings().first()
        if not row or not row.get("last_error"):
            return None
        return {
            "mensagem": str(row.get("last_error") or "")[:200],
            "fase": row.get("last_phase"),
            "quando": row.get("concluido_em").isoformat() if row.get("concluido_em") else None,
            "source": "jobs",
        }
    message = row.get("mensagem_amigavel") or row.get("last_error") or row.get("erro_tecnico")
    return {
        "mensagem": str(message or "")[:200],
        "fase": row.get("fase"),
        "quando": row.get("criado_em").isoformat() if row.get("criado_em") else None,
        "source": "pipeline_failures",
    }


@router.get("/cooldown-status")
async def cooldown_status(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    from services.credits_manager import (
        validar_permissao_pipeline,
        get_user_tokens,
        LIMITES_DIARIOS,
        COOLDOWNS,
    )

    perm = validar_permissao_pipeline(db, tenant_id)
    info = get_user_tokens(db, tenant_id)
    plano = info.get("plano", "trial")
    cooldown_secs = COOLDOWNS.get(plano, 3600)
    limite = LIMITES_DIARIOS.get(plano, 1)
    pode_rodar = perm["allowed"]
    cooldown_info = {"ativo": False, "total_seg": cooldown_secs, "restante_seg": 0, "percentual_completo": 100}
    if not pode_rodar and perm.get("reason") == "cooldown":
        cooldown_info = {
            "ativo": True,
            "total_seg": cooldown_secs,
            "restante_seg": perm.get("cooldown_restante_seg", 0),
            "proximo_em": perm.get("proximo_em"),
            "percentual_completo": round((1 - perm.get("cooldown_restante_seg", 0) / max(cooldown_secs, 1)) * 100, 1),
        }
    creditos_info = {
        "limite_diario": limite,
        "limite_mensal": info.get("limite_mensal", limite),
        "usados_hoje": info.get("sites_hoje", 0),
        "restantes_hoje": info.get("creditos_restantes_hoje", limite),
        "restantes_mes": info.get("creditos_restantes_mes", info.get("creditos_restantes_hoje", limite)),
        "reset_at": None,
    }
    if not pode_rodar and perm.get("reason") == "creditos_esgotados":
        from services.credits_manager import _proximo_reset_iso
        creditos_info["reset_at"] = _proximo_reset_iso()
    fila_row = db.execute(text("""
        SELECT COUNT(*) as total,
               (SELECT nome FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1),
               (SELECT cidade FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1)
        FROM leads WHERE user_id=:uid AND status='capturado'
    """), {"uid": tenant_id}).fetchone()
    fila = {"leads_aguardando": fila_row[0] if fila_row else 0, "proximo_lead_nome": fila_row[1] if fila_row else None, "proximo_lead_cidade": fila_row[2] if fila_row else None, "auto_run_ativo": (fila_row[0] or 0) > 0}
    uso = {"sites_hoje": info.get("sites_hoje", 0), "sites_total": info.get("sites_used", 0)}
    _UPSELL_MSGS = {
        "trial": {"plano_sugerido": "starter", "mensagem_curta": "Starter: 180 sites/mes", "mensagem_longa": "Com o Starter voce gera 180 sites por mes com cooldown de 1h, sem SDR."},
        "starter": {"plano_sugerido": "pro", "mensagem_curta": "Pro: 360 creditos/mes + SDR", "mensagem_longa": "No Pro sao 360 creditos por mes, cooldown de 30 minutos e SDR ativo."},
        "pro": {"plano_sugerido": "ilimitado", "mensagem_curta": "Ilimitado: sem limite + SDR ilimitado", "mensagem_longa": "No Ilimitado nao tem cooldown, limite mensal ou limite de SDR."},
    }
    upsell_data = _UPSELL_MSGS.get(plano)
    upsell = {"mostrar": True, "plano_atual": plano, **upsell_data, "url": f"/planos?from=cooldown&current={plano}"} if (not pode_rodar and upsell_data) else None
    bloqueio = {"motivo": perm.get("reason", "unknown"), "mensagem": perm.get("message", "Bloqueado")} if not pode_rodar else None
    return {"pode_rodar": pode_rodar, "plano": plano, "cooldown": cooldown_info, "creditos": creditos_info, "fila": fila, "uso": uso, "upsell": upsell, "bloqueio": bloqueio}


@router.get("/status")
async def get_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    state = get_pipeline_state(db, tenant_id)
    current_job = _current_pipeline_job(db, tenant_id)
    latest_job = current_job or _latest_pipeline_job(db, tenant_id)
    total_leads = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid"), {"uid": tenant_id}).scalar() or 0
    total_sites = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND (site_url IS NOT NULL AND site_url != '' OR url_site IS NOT NULL AND url_site != '')"), {"uid": tenant_id}).scalar() or 0
    total_enviados = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status = 'contatado'"), {"uid": tenant_id}).scalar() or 0
    ciclo_atual = db.execute(text("SELECT COALESCE(MAX(ciclo), 0) FROM leads WHERE user_id=:uid"), {"uid": tenant_id}).scalar() or 0
    _ckpt_info = None
    _pid = None
    try:
        _cfg = state.get("config") or {}
        _pid = gerar_pipeline_id(tenant_id, _cfg.get("segmento", ""), _cfg.get("cidade", ""))
        _ckpt = _load_ckpt(_pid)
        if _ckpt and _ckpt.get("agentes"):
            _ckpt_info = {"fases_concluidas": list(_ckpt["agentes"].keys()), "total_fases": len(_ckpt["agentes"]), "ultimo_agente": _ckpt.get("ultimo_agente"), "atualizado_em": _ckpt.get("atualizado_em")}
    except Exception:
        pass
    _ultimo_erro = _latest_pipeline_failure(db, tenant_id)
    _cooldown_info = None
    try:
        _user_row = db.execute(text("SELECT plano, ultimo_deploy_at FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
        _plano = (_user_row[0] if _user_row else "trial") or "trial"
        _cd_secs = _COOLDOWN_POR_PLANO.get(_plano, 3600)
        _fila_count = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='capturado'"), {"uid": tenant_id}).scalar() or 0
        _cooldown_info = {"plano": _plano, "cooldown_total": _cd_secs, "cooldown_restante": 0, "bloqueado": False, "leads_na_fila": _fila_count, "auto_run": False}
    except Exception:
        pass
    rodando = bool(current_job and current_job.get("status") in {"running", "pending", "failed_retriable"})
    telemetry = _pipeline_job_telemetry(db, tenant_id, latest_job)
    runtime_summary = _pipeline_runtime_summary(db, tenant_id)
    return {"rodando": rodando, "pausado": state["pausado"], "config": state["config"], "iniciado_em": state.get("iniciado_em").isoformat() if state.get("iniciado_em") else None, "totalLeads": total_leads, "totalSites": total_sites, "totalEnviados": total_enviados, "cicloAtual": ciclo_atual, "checkpoint": _ckpt_info, "ultimo_erro": _ultimo_erro, "cooldown": _cooldown_info, "pipeline_id": _pid, "current_job": current_job, "latest_job": latest_job, "telemetry": telemetry, "runtime_summary": runtime_summary, "fase_atual": current_job.get("last_phase") if current_job else None, "fase_num": current_job.get("phase_num") if current_job else None, "fase_label": current_job.get("phase_label") if current_job else None}


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        uid = usuario.get("tenant_id", usuario["id"])
        total_com_site = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND (site_url IS NOT NULL AND site_url != '' OR url_site IS NOT NULL AND url_site != '')"), {"uid": uid}).scalar() or 0
        total_respondeu = db.execute(text("SELECT COUNT(DISTINCT i.lead_nome) FROM interacoes i JOIN leads l ON l.nome=i.lead_nome WHERE l.user_id=:uid AND i.direcao='entrada'"), {"uid": uid}).scalar() or 0
        taxa_resposta = round(total_respondeu / total_com_site * 100, 1) if total_com_site > 0 else 0
        nicho_top = db.execute(text("SELECT segmento, COUNT(CASE WHEN (site_url IS NOT NULL AND site_url != '' OR url_site IS NOT NULL AND url_site != '') THEN 1 END) * 100.0 / COUNT(*) as conv FROM leads WHERE user_id = :uid AND segmento IS NOT NULL AND segmento != '' GROUP BY segmento HAVING COUNT(*) >= 3 ORDER BY conv DESC LIMIT 1"), {"uid": uid}).fetchone()
        cidade_top = db.execute(text("SELECT cidade, COUNT(*) as total FROM leads WHERE user_id = :uid AND cidade IS NOT NULL AND cidade != '' GROUP BY cidade ORDER BY total DESC LIMIT 1"), {"uid": uid}).fetchone()
        ticket_medio = db.execute(text("SELECT COALESCE(AVG(valor_venda), 0) FROM leads WHERE user_id=:uid AND valor_venda > 0"), {"uid": uid}).scalar() or 0
        total_msgs = db.execute(text("SELECT COUNT(*) FROM interacoes i JOIN leads l ON l.nome=i.lead_nome WHERE l.user_id=:uid AND i.direcao='saida'"), {"uid": uid}).scalar() or 0
        return {"taxa_resposta": taxa_resposta, "nicho_top": nicho_top.segmento if nicho_top else "—", "nicho_top_conv": round(nicho_top.conv, 1) if nicho_top else 0, "cidade_top": cidade_top.cidade if cidade_top else "—", "cidade_top_total": cidade_top.total if cidade_top else 0, "ticket_medio": float(ticket_medio), "total_msgs_franz": total_msgs, "total_msgs_bryan": total_msgs}
    except Exception:
        return {"taxa_resposta": 0}
