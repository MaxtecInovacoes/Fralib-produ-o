from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from backend.core.database import get_db
from sqlalchemy.orm import Session
import jwt
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from backend.core.access_control import require_superadmin
from backend.core.config import SUPERADMIN_EMAILS
from backend.domain.llm_pricing import estimate_llm_cost_usd
from backend.domain.plans import PLAN_SPECS, get_plan_spec, is_paid_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/superadmin', tags=['superadmin'])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ALGORITHM = "HS256"

@router.get("/config")
async def get_superadmin_config(user: dict = Depends(require_superadmin)):
    """Expose safe superadmin UI config without hardcoded frontend emails."""
    return {
        "ok": True,
        "superadmin_emails": sorted(SUPERADMIN_EMAILS),
        "current_email": user.get("email", ""),
    }


def _audit(db, actor, action, target_user_id, target_id=None, metadata=None, request=None):
    """Registra acao sensivel em audit_log. Falha silenciosa para nao quebrar o endpoint."""
    try:
        db.execute(text("""
            INSERT INTO audit_log (actor_id, target_user_id, action, target_type, target_id, metadata, ip, user_agent)
            VALUES (:actor, :target_user, :action, 'user', :target_id, CAST(:meta AS JSONB), :ip, :ua)
        """), {
            "actor": actor.get("id"),
            "target_user": target_user_id,
            "action": action,
            "target_id": str(target_id) if target_id is not None else None,
            "meta": json.dumps(metadata or {}),
            "ip": (request.client.host if request and request.client else None),
            "ua": (request.headers.get("user-agent") if request else None),
        })
        db.commit()
    except Exception as _e:
        print(f"[audit_log] falha ao registrar acao {action}: {_e}")
        try:
            db.rollback()
        except Exception:
            pass


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Metricas gerais do sistema"""
    try:
        # Total de usuarios
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        
        # Usuarios ativos (logaram nos ultimos 30 dias)
        active_users = db.execute(text(
            "SELECT COUNT(*) FROM users WHERE ultimo_acesso IS NOT NULL AND ultimo_acesso != ''"
        )).scalar()
        
        # Total de leads
        total_leads = db.execute(text("SELECT COUNT(*) FROM leads")).scalar()
        
        # Sites gerados (leads com site pronto)
        sites_gerados = db.execute(text(
            "SELECT COUNT(*) FROM leads WHERE processado = true"
        )).scalar()
        
        # Tokens consumidos total (from llm_usage)
        tokens_row = db.execute(text(
            "SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0) FROM llm_usage"
        )).fetchone()
        tokens_input = tokens_row[0] or 0
        tokens_output = tokens_row[1] or 0
        
        cost_rows = db.execute(text("""
            SELECT modelo, COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0)
            FROM llm_usage
            GROUP BY modelo
        """)).fetchall()
        custo_total = sum(
            estimate_llm_cost_usd(
                r[0] or "",
                {"input_tokens": int(r[1] or 0), "output_tokens": int(r[2] or 0)},
            )
            for r in cost_rows
        )
        
        # Pipeline runs (agrupados por gaps > 10min)
        pipeline_stats = db.execute(text("""
            WITH ordered AS (
              SELECT criado_em,
                     LAG(criado_em) OVER (ORDER BY criado_em) as prev_time,
                     input_tokens, output_tokens
              FROM llm_usage
            ),
            gaps AS (
              SELECT criado_em, input_tokens, output_tokens,
                     CASE WHEN prev_time IS NULL OR criado_em - prev_time > interval '10 minutes' THEN 1 ELSE 0 END as new_run
              FROM ordered
            ),
            runs AS (
              SELECT SUM(new_run) OVER (ORDER BY criado_em) as run_id,
                     input_tokens, output_tokens
              FROM gaps
            ),
            per_run AS (
              SELECT run_id, sum(input_tokens) as run_in, sum(output_tokens) as run_out
              FROM runs GROUP BY run_id
            )
            SELECT count(*), round(avg(run_in)), round(avg(run_out))
            FROM per_run
        """)).fetchone()
        total_pipelines = pipeline_stats[0] or 0
        avg_in = float(pipeline_stats[1] or 0)
        avg_out = float(pipeline_stats[2] or 0)
        custo_por_pipeline = round(avg_in / 1e6 * 3 + avg_out / 1e6 * 15, 4) if total_pipelines > 0 else 0
        
        # Usuarios pagantes
        pagantes = db.execute(text(
            "SELECT COUNT(*) FROM users WHERE plano_pago = true"
        )).scalar()
        
        return {
            "ok": True,
            "metrics": {
                "totalUsers": total_users or 0,
                "activeUsers": active_users or 0,
                "totalLeads": total_leads or 0,
                "sitesGerados": sites_gerados or 0,
                "tokensInput": tokens_input,
                "tokensOutput": tokens_output,
                "tokensConsumed": tokens_input + tokens_output,
                "custoTotalUSD": round(float(custo_total), 2),
                "pagantes": pagantes or 0,
                "totalPipelines": total_pipelines,
                "custoPorPipeline": custo_por_pipeline
            }
        }
    except Exception as e:
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.get("/users")
async def list_users(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Lista todos os usuarios com dados de consumo"""
    try:
        rows = db.execute(text("""
            SELECT
                u.id, u.email, u.nome, u.role, u.plano, u.status,
                u.creditos, u.creditos_max,
                u.sites_created_month, u.tokens_used_month,
                u.criado_em, u.ultimo_acesso,
                u.plano_pago, u.email_confirmado,
                COALESCE(u.telefone, '') as telefone,
                COALESCE(u.nicho, '') as nicho,
                COALESCE(ls.total_leads, 0) as total_leads,
                COALESCE(ls.sites_prontos, 0) as sites_prontos,
                COALESCE(tt.tokens_total, 0) as tokens_total,
                COALESCE(lu.llm_input, 0) as llm_input,
                COALESCE(lu.llm_output, 0) as llm_output
            FROM users u
            LEFT JOIN (
                SELECT user_id,
                    COUNT(*) as total_leads,
                    COUNT(*) FILTER (WHERE processado = true) as sites_prontos
                FROM leads GROUP BY user_id
            ) ls ON u.id = ls.user_id
            LEFT JOIN (
                SELECT user_id, SUM(tokens_consumidos) as tokens_total
                FROM token_transactions GROUP BY user_id
            ) tt ON u.id = tt.user_id
            LEFT JOIN (
                SELECT user_id,
                    SUM(input_tokens) as llm_input,
                    SUM(output_tokens) as llm_output
                FROM llm_usage GROUP BY user_id
            ) lu ON u.id = lu.user_id
            ORDER BY u.id DESC
        """)).fetchall()
        
        users_list = []
        for r in rows:
            users_list.append({
                "id": r[0],
                "email": r[1],
                "nome": r[2] or "",
                "role": r[3] or "user",
                "plano": r[4] or "trial",
                "status": r[5] or "trial",
                "creditos": r[6] or 0,
                "creditos_max": r[7] or 0,
                "sites_mes": r[8] or 0,
                "tokens_mes": r[9] or 0,
                "criado_em": r[10] or "",
                "ultimo_acesso": r[11] or "Nunca",
                "plano_pago": bool(r[12]),
                "email_confirmado": bool(r[13]),
                "telefone": r[14],
                "nicho": r[15],
                "total_leads": r[16] or 0,
                "sites_prontos": r[17] or 0,
                "tokens_total": r[18] or 0,
                "llm_input": r[19] or 0,
                "llm_output": r[20] or 0
            })
        
        return {"ok": True, "users": users_list, "total": len(users_list)}
    except Exception as e:
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.post("/users/{user_id}/toggle")
async def toggle_user(user_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Ativar/desativar usuario"""
    try:
        row = db.execute(text("SELECT status, email FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        if row[1] in SUPERADMIN_EMAILS:
            raise HTTPException(status_code=403, detail="Nao pode desativar o superadmin")

        new_status = "bloqueado" if row[0] != "bloqueado" else "ativo"
        db.execute(text("UPDATE users SET status = :status WHERE id = :id"), {"status": new_status, "id": user_id})
        db.commit()

        _audit(db, user, "toggle_user", user_id, target_id=user_id,
               metadata={"from": row[0], "to": new_status, "email": row[1]}, request=request)

        return {"ok": True, "new_status": new_status, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.post("/users/{user_id}/set-plan")
async def set_plan(user_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Alterar plano do usuario - recebe JSON {plano: 'trial'|'starter'|'pro'}"""
    try:
        body = await request.json()
        plano = body.get("plano", "trial")
        if plano not in PLAN_SPECS:
            raise HTTPException(status_code=400, detail="Plano invalido")
        
        row = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        
        plano_pago = is_paid_plan(plano)
        status_novo = "ativo" if plano_pago else plano
        creditos = get_plan_spec(plano).monthly_credits
        db.execute(text(
            """
            UPDATE users
            SET plano = :plano, plan = :plano, plano_pago = :pago, status = :status,
                creditos = :creditos, creditos_max = :creditos, last_reset_date = CURRENT_DATE
            WHERE id = :id
            """
        ), {"plano": plano, "pago": plano_pago, "status": status_novo, "creditos": creditos, "id": user_id})
        db.commit()

        _audit(db, user, "set_plan", user_id, target_id=user_id,
               metadata={"plano": plano, "plano_pago": plano_pago}, request=request)

        return {"ok": True, "plano": plano, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.post("/users/{user_id}/set-creditos")
async def set_creditos(user_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Definir creditos do usuario - recebe JSON {creditos: N}"""
    try:
        body = await request.json()
        creditos = int(body.get("creditos", 0))
        
        row = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        
        db.execute(text(
            "UPDATE users SET creditos = :c, creditos_max = :c WHERE id = :id"
        ), {"c": creditos, "id": user_id})
        db.commit()

        _audit(db, user, "set_creditos", user_id, target_id=user_id,
               metadata={"creditos": creditos}, request=request)

        return {"ok": True, "creditos": creditos, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.post("/impersonate/{user_id}")
async def impersonate(user_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Logar como outro usuario"""
    try:
        row = db.execute(text("SELECT id, email, role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        # Gerar token JWT para o usuario alvo
        token = jwt.encode(
            {"sub": str(row[0]), "email": row[1], "role": row[2] or "user",
             "exp": datetime.utcnow() + timedelta(hours=2)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )

        _audit(db, user, "impersonate", int(row[0]), target_id=int(row[0]),
               metadata={"email": row[1], "role": row[2] or "user"}, request=request)

        return {
            "ok": True,
            "token": token,
            "user": {"id": row[0], "email": row[1], "role": row[2]}
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.get("/usage")
async def get_usage(db: Session = Depends(get_db), user: dict = Depends(require_superadmin), periodo: str = "48h"):
    """Consumo de tokens por hora e por agente. Periodo: 24h, 48h, 7d, 30d"""
    try:
        # Whitelist estrita: periodo -> (hours_interval, granularidade)
        # Hours como inteiro literal evita qualquer interpolacao de string vinda do usuario
        PERIODO_CONFIG = {
            "24h": (24, "hour"),
            "48h": (48, "hour"),
            "7d":  (24 * 7, "day"),
            "30d": (24 * 30, "day"),
        }
        if periodo not in PERIODO_CONFIG:
            periodo = "48h"
        hours, gran = PERIODO_CONFIG[periodo]
        # gran vem da whitelist acima ("hour" ou "day"), seguro p/ interpolar
        time_group = f"date_trunc('{gran}', criado_em)"

        # Totais gerais (do periodo) — hours via bindparam
        totals = db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0) "
            "FROM llm_usage WHERE criado_em > NOW() - (:hours || ' hours')::interval"
        ), {"hours": hours}).fetchone()

        # Totais all-time
        totals_all = db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0) FROM llm_usage"
        )).fetchone()

        # Timeline
        timeline = db.execute(text(
            f"SELECT {time_group} as periodo, "
            "SUM(input_tokens) as input, SUM(output_tokens) as output, COUNT(*) as calls "
            "FROM llm_usage WHERE criado_em > NOW() - (:hours || ' hours')::interval "
            "GROUP BY periodo ORDER BY periodo"
        ), {"hours": hours}).fetchall()

        # Por agente (no periodo)
        by_agent = db.execute(text(
            "SELECT agente, COUNT(*) as calls, "
            "SUM(input_tokens) as input, SUM(output_tokens) as output "
            "FROM llm_usage WHERE criado_em > NOW() - (:hours || ' hours')::interval "
            "GROUP BY agente ORDER BY input DESC"
        ), {"hours": hours}).fetchall()

        # Por usuario (no periodo)
        by_user = db.execute(text(
            "SELECT u.email, u.nome, COUNT(*) as calls, "
            "SUM(l.input_tokens) as input, SUM(l.output_tokens) as output "
            "FROM llm_usage l LEFT JOIN users u ON u.id = l.user_id "
            "WHERE l.criado_em > NOW() - (:hours || ' hours')::interval "
            "GROUP BY u.email, u.nome ORDER BY input DESC"
        ), {"hours": hours}).fetchall()
        
        return {
            "ok": True,
            "periodo": periodo,
            "totals": {
                "calls": totals[0] or 0,
                "input_tokens": totals[1] or 0,
                "output_tokens": totals[2] or 0
            },
            "totals_all": {
                "calls": totals_all[0] or 0,
                "input_tokens": totals_all[1] or 0,
                "output_tokens": totals_all[2] or 0
            },
            "timeline": [{"periodo": str(h[0]), "input": h[1] or 0, "output": h[2] or 0, "calls": h[3] or 0} for h in timeline],
            "by_agent": [{"agente": a[0] or "unknown", "calls": a[1], "input": a[2] or 0, "output": a[3] or 0} for a in by_agent],
            "by_user": [{"email": u[0] or "unknown", "nome": u[1] or "", "calls": u[2], "input": u[3] or 0, "output": u[4] or 0} for u in by_user]
        }
    except Exception as e:
        print(f"[Superadmin] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


# ══════════════════════════════════════════════════════════════════════
# DASHBOARD CRÍTICO — Métricas de operação, custos, saúde, alertas
# ══════════════════════════════════════════════════════════════════════

def _calcular_custo(modelo: str, input_tokens: int, output_tokens: int) -> float:
    return estimate_llm_cost_usd(
        modelo,
        {"input_tokens": int(input_tokens or 0), "output_tokens": int(output_tokens or 0)},
    )


@router.get("/dashboard/overview")
async def dashboard_overview(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """KPIs principais: 24h, 7d, 30d"""
    try:
        exec_row = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE finished_at >= NOW() - INTERVAL '24 hours' AND status='completed') as sites_24h,
                COUNT(*) FILTER (WHERE finished_at >= NOW() - INTERVAL '7 days' AND status='completed') as sites_7d,
                COUNT(*) FILTER (WHERE finished_at >= NOW() - INTERVAL '30 days' AND status='completed') as sites_30d,
                COUNT(*) FILTER (WHERE finished_at >= NOW() - INTERVAL '24 hours') as total_24h,
                COUNT(*) FILTER (WHERE finished_at >= NOW() - INTERVAL '24 hours' AND status='failed') as falhas_24h
            FROM pipeline_executions
        """)).fetchone()

        custo_row = db.execute(text("""
            WITH totals AS (
                SELECT
                    COALESCE(SUM(cost_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours'), 0) as custo_24h,
                    COALESCE(SUM(cost_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0) as custo_7d,
                    COALESCE(SUM(cost_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days'), 0) as custo_30d
                FROM llm_budget_ledger
            ),
            grouped AS (
                SELECT COALESCE(job_id::text, run_id, id::text) AS ledger_group,
                       SUM(cost_usd) AS job_cost,
                       SUM(COALESCE(latency_ms, 0)) AS job_latency_ms,
                       MAX(created_at) AS last_call
                FROM llm_budget_ledger
                GROUP BY COALESCE(job_id::text, run_id, id::text)
            )
            SELECT totals.custo_24h, totals.custo_7d, totals.custo_30d,
                   COALESCE(AVG(grouped.job_cost) FILTER (WHERE grouped.last_call >= NOW() - INTERVAL '7 days'), 0) as custo_medio_site,
                   COALESCE(AVG(grouped.job_latency_ms) FILTER (WHERE grouped.last_call >= NOW() - INTERVAL '7 days'), 0) / 1000.0 as duracao_media_s
            FROM totals
            LEFT JOIN grouped ON TRUE
            GROUP BY totals.custo_24h, totals.custo_7d, totals.custo_30d
        """)).fetchone()

        fila_row = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pendentes,
                COUNT(*) FILTER (WHERE status = 'running') as rodando,
                COUNT(*) FILTER (WHERE status = 'failed_permanent') as dead_letter
            FROM jobs WHERE criado_em > NOW() - INTERVAL '7 days'
        """)).fetchone()

        total_24h = exec_row[3] or 1
        taxa_sucesso = round((exec_row[0] or 0) / total_24h * 100, 1) if total_24h > 0 else 0

        return {
            "sites": {"24h": exec_row[0] or 0, "7d": exec_row[1] or 0, "30d": exec_row[2] or 0},
            "taxa_sucesso_24h": taxa_sucesso,
            "falhas_24h": exec_row[4] or 0,
            "custo": {
                "24h": round(custo_row[0] or 0, 2),
                "7d": round(custo_row[1] or 0, 2),
                "30d": round(custo_row[2] or 0, 2),
                "medio_por_site": round(custo_row[3] or 0, 3),
            },
            "duracao_media_s": round(custo_row[4] or 0, 1),
            "fila": {
                "pendentes": fila_row[0] or 0,
                "rodando": fila_row[1] or 0,
                "dead_letter": fila_row[2] or 0,
            },
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/dashboard/costs")
async def dashboard_costs(db: Session = Depends(get_db), user: dict = Depends(require_superadmin),
                          period: str = "7d", group_by: str = "day"):
    """Breakdown de custos. group_by: day, agent, model, segmento"""
    PERIODS = {"24h": 24, "7d": 168, "30d": 720}
    hours = PERIODS.get(period, 168)

    try:
        if group_by == "day":
            rows = db.execute(text("""
                SELECT DATE(created_at) as dia, COUNT(*) as runs,
                       ROUND(SUM(cost_usd)::numeric, 3) as custo,
                       ROUND(AVG(cost_usd)::numeric, 3) as custo_medio
                FROM llm_budget_ledger
                WHERE created_at > NOW() - (:hours || ' hours')::interval
                GROUP BY dia ORDER BY dia
            """), {"hours": hours}).fetchall()
            return {"group_by": "day", "data": [
                {"dia": str(r[0]), "runs": r[1], "custo": float(r[2] or 0), "custo_medio": float(r[3] or 0)} for r in rows
            ]}

        if group_by == "agent":
            rows = db.execute(text("""
                SELECT COALESCE(agent, phase, 'unknown') as agente,
                       COUNT(*) as runs,
                       ROUND(SUM(cost_usd)::numeric, 4) as custo,
                       ROUND(SUM(input_tokens + cache_read_tokens + cache_created_tokens)::numeric, 0) as input_tokens,
                       ROUND(SUM(output_tokens)::numeric, 0) as output_tokens
                FROM llm_budget_ledger
                WHERE created_at > NOW() - (:hours || ' hours')::interval
                GROUP BY COALESCE(agent, phase, 'unknown') ORDER BY custo DESC
            """), {"hours": hours}).fetchall()
            return {"group_by": "agent", "data": [
                {"agente": r[0], "runs": r[1], "custo": float(r[2] or 0),
                 "input_tokens": int(r[3] or 0), "output_tokens": int(r[4] or 0)} for r in rows
            ]}

        if group_by == "model":
            rows = db.execute(text("""
                SELECT model, COUNT(*) as calls,
                       SUM(input_tokens + cache_read_tokens + cache_created_tokens) as input_t,
                       SUM(output_tokens) as output_t,
                       SUM(cost_usd) as custo
                FROM llm_budget_ledger
                WHERE created_at > NOW() - (:hours || ' hours')::interval
                GROUP BY model ORDER BY input_t DESC
            """), {"hours": hours}).fetchall()
            data = []
            for r in rows:
                custo = float(r[4] or 0)
                data.append({"modelo": r[0], "calls": r[1], "input_tokens": r[2] or 0,
                             "output_tokens": r[3] or 0, "custo_usd": round(custo, 3)})
            return {"group_by": "model", "data": data}

        if group_by == "segmento":
            rows = db.execute(text("""
                SELECT COALESCE(j.payload->>'nicho', j.payload->>'segmento', l.phase, 'unknown') as nicho,
                       COUNT(*) as runs,
                       ROUND(SUM(l.cost_usd)::numeric, 3) as custo,
                       ROUND(AVG(l.cost_usd)::numeric, 3) as custo_medio
                FROM llm_budget_ledger l
                LEFT JOIN jobs j ON j.id = l.job_id
                WHERE l.created_at > NOW() - (:hours || ' hours')::interval
                GROUP BY COALESCE(j.payload->>'nicho', j.payload->>'segmento', l.phase, 'unknown') ORDER BY custo DESC
            """), {"hours": hours}).fetchall()
            return {"group_by": "segmento", "data": [
                {"segmento": r[0], "runs": r[1], "custo": float(r[2] or 0), "custo_medio": float(r[3] or 0)} for r in rows
            ]}

        return {"error": "group_by invalido. Use: day, agent, model, segmento"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/dashboard/costs/projection")
async def costs_projection(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Projeção de custo mensal baseado nos últimos 7 dias."""
    try:
        row = db.execute(text("""
            SELECT COALESCE(SUM(cost_usd), 0) as custo_7d,
                   COUNT(DISTINCT COALESCE(job_id::text, run_id, id::text)) as runs_7d
            FROM llm_budget_ledger WHERE created_at > NOW() - INTERVAL '7 days'
        """)).fetchone()
        custo_7d = float(row[0] or 0)
        runs_7d = row[1] or 0
        custo_diario = custo_7d / 7
        return {
            "custo_7d": round(custo_7d, 2),
            "custo_diario_medio": round(custo_diario, 2),
            "projecao_mensal": round(custo_diario * 30, 2),
            "runs_diario_medio": round(runs_7d / 7, 1),
            "projecao_runs_mensal": round(runs_7d / 7 * 30, 0),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/dashboard/pipeline")
async def dashboard_pipeline(db: Session = Depends(get_db), user: dict = Depends(require_superadmin),
                             period: str = "7d"):
    """Performance do pipeline: taxa sucesso, falhas por fase, tempo por fase."""
    PERIODS = {"24h": 24, "7d": 168, "30d": 720}
    hours = PERIODS.get(period, 168)

    try:
        status_row = db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(*) FILTER (WHERE status='completed') as sucesso,
                   COUNT(*) FILTER (WHERE status='failed') as falhas
            FROM pipeline_executions
            WHERE started_at > NOW() - (:hours || ' hours')::interval
        """), {"hours": hours}).fetchone()

        falhas_fase = db.execute(text("""
            SELECT fase, COUNT(*) as total
            FROM pipeline_failures
            WHERE criado_em > NOW() - (:hours || ' hours')::interval
            GROUP BY fase ORDER BY total DESC
        """), {"hours": hours}).fetchall()

        tempo_fase = db.execute(text("""
            SELECT s.value->>'agente' as agente,
                   ROUND(AVG((s.value->>'duracao_ms')::float / 1000)::numeric, 1) as media_s,
                   COUNT(*) as chamadas
            FROM pipeline_traces, jsonb_array_elements(spans_json) as s
            WHERE created_at > NOW() - (:hours || ' hours')::interval
              AND s.value->>'duracao_ms' IS NOT NULL
            GROUP BY agente ORDER BY media_s DESC
        """), {"hours": hours}).fetchall()

        total = status_row[0] or 1
        return {
            "total_runs": status_row[0] or 0,
            "sucesso": status_row[1] or 0,
            "falhas": status_row[2] or 0,
            "taxa_sucesso": round((status_row[1] or 0) / total * 100, 1),
            "falhas_por_fase": [{"fase": r[0] or "unknown", "total": r[1]} for r in falhas_fase],
            "tempo_por_fase": [{"agente": r[0] or "unknown", "media_s": float(r[1] or 0), "chamadas": r[2]} for r in tempo_fase],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/dashboard/health")
async def dashboard_health(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Status de saúde de todos os serviços."""
    health = {}

    try:
        pg_conns = db.execute(text("SELECT COUNT(*) FROM pg_stat_activity WHERE state='active'")).scalar()
        health["postgres"] = {"status": "up", "connections_active": pg_conns}
    except Exception:
        health["postgres"] = {"status": "down"}

    try:
        workers_row = db.execute(text("""
            SELECT COUNT(DISTINCT worker_id) FROM jobs
            WHERE status='running' AND worker_heartbeat > NOW() - INTERVAL '2 minutes'
        """)).scalar()
        health["workers"] = {"status": "up" if workers_row > 0 else "degraded", "active": workers_row or 0}
    except Exception:
        health["workers"] = {"status": "unknown"}

    # SDR outbound queue
    try:
        from backend.services.outbound_queue import get_pending_count, get_recent_sent_count
        pending = get_pending_count()
        sent_last_hour = get_recent_sent_count()
        rate_limit_ok = sent_last_hour < 12
        redis_ok = False
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_timeout=1)
            r.ping()
            redis_ok = True
        except Exception:
            pass
        health["outbound_queue"] = {
            "status": "ok" if (rate_limit_ok and redis_ok) else "degraded",
            "pending": pending,
            "sent_last_hour": sent_last_hour,
            "rate_limit_ok": rate_limit_ok,
            "redis_ok": redis_ok,
        }
    except Exception:
        health["outbound_queue"] = {"status": "unknown"}

    try:
        fila = db.execute(text("""
            SELECT COUNT(*) FILTER (WHERE status='pending') as pending,
                   COUNT(*) FILTER (WHERE status='running') as running,
                   COUNT(*) FILTER (WHERE status='failed_permanent' AND criado_em > NOW() - INTERVAL '24 hours') as failed_24h
            FROM jobs
        """)).fetchone()
        health["queue"] = {"pending": fila[0] or 0, "running": fila[1] or 0, "failed_24h": fila[2] or 0}
    except Exception:
        health["queue"] = {"status": "unknown"}

    try:
        import psutil
        health["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        }
    except Exception as e:
        health["system"] = {"cpu_percent": None, "ram_percent": None, "disk_percent": None, "error": str(e)}

    return health


@router.get("/dashboard/alerts")
async def dashboard_alerts(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Alertas ativos baseados em regras."""
    alerts = []

    try:
        custo_hoje = db.execute(text(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_budget_ledger WHERE created_at >= CURRENT_DATE"
        )).scalar() or 0
        if custo_hoje > 20:
            alerts.append({"severity": "warning", "rule": "custo_diario_alto",
                           "message": f"Custo hoje: ${custo_hoje:.2f} (limite: $20)", "value": round(custo_hoje, 2)})

        falhas_recentes = db.execute(text("""
            SELECT fase, COUNT(*) as total FROM pipeline_failures
            WHERE criado_em > NOW() - INTERVAL '1 hour'
            GROUP BY fase HAVING COUNT(*) >= 3
        """)).fetchall()
        for r in falhas_recentes:
            alerts.append({"severity": "critical", "rule": "falhas_consecutivas",
                           "message": f"3+ falhas na fase '{r[0]}' na ultima hora", "fase": r[0], "total": r[1]})

        taxa_row = db.execute(text("""
            SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status='completed') as ok
            FROM pipeline_executions WHERE started_at > NOW() - INTERVAL '1 hour'
        """)).fetchone()
        if taxa_row and taxa_row[0] >= 3:
            taxa = (taxa_row[1] or 0) / taxa_row[0] * 100
            if taxa < 70:
                alerts.append({"severity": "warning", "rule": "taxa_sucesso_baixa",
                               "message": f"Taxa sucesso ultima hora: {taxa:.0f}%", "value": round(taxa, 1)})

        workers_alive = db.execute(text("""
            SELECT COUNT(DISTINCT worker_id) FROM jobs
            WHERE status='running' AND worker_heartbeat > NOW() - INTERVAL '2 minutes'
        """)).scalar() or 0
        if workers_alive == 0:
            pending = db.execute(text("SELECT COUNT(*) FROM jobs WHERE status='pending'")).scalar() or 0
            if pending > 0:
                alerts.append({"severity": "critical", "rule": "workers_down",
                               "message": f"Nenhum worker ativo com {pending} jobs pendentes"})

        try:
            import psutil
            disk = psutil.disk_usage('/').percent
            if disk > 90:
                alerts.append({"severity": "warning", "rule": "disk_alto",
                               "message": f"Disco em {disk:.0f}%", "value": disk})
        except Exception:
            pass

    except Exception as e:
        alerts.append({"severity": "error", "rule": "alert_engine_error", "message": str(e)})

    return {"alerts": alerts, "total": len(alerts), "critical": sum(1 for a in alerts if a["severity"] == "critical")}


@router.get("/dashboard/rate-limits")
async def dashboard_rate_limits(user: dict = Depends(require_superadmin)):
    """Status completo do rate limiting: budget, keys, calls/min, top tenants."""
    try:
        import ia_manager
        return ia_manager.get_rate_limit_status()
    except Exception as e:
        raise HTTPException(500, detail=f"Erro ao consultar rate limits: {e}")


@router.get("/dashboard/jobs/failed")
async def dashboard_jobs_failed(db: Session = Depends(get_db), user: dict = Depends(require_superadmin),
                                limit: int = 20):
    """Jobs falhados com detalhes para replay."""
    try:
        rows = db.execute(text("""
            SELECT pf.id, pf.job_id, pf.lead_nome, pf.fase, pf.mensagem_amigavel,
                   pf.erro_tecnico, pf.tentativas_automaticas, pf.criado_em, pf.tenant_id, u.email
            FROM pipeline_failures pf LEFT JOIN users u ON u.id = pf.tenant_id
            ORDER BY pf.criado_em DESC LIMIT :limit
        """), {"limit": limit}).fetchall()
        return {"jobs": [
            {"id": r[0], "job_id": r[1], "lead_nome": r[2], "fase": r[3],
             "mensagem": r[4], "erro": (r[5] or "")[:200], "tentativas": r[6],
             "created_at": str(r[7]), "tenant_id": r[8], "email": r[9]}
            for r in rows
        ]}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/dashboard/jobs/{job_id}/replay")
async def replay_job(job_id: int, db: Session = Depends(get_db), user: dict = Depends(require_superadmin),
                     request: Request = None):
    """Reprocessar job falhado — volta pra fila como pending."""
    try:
        job = db.execute(text("SELECT id, tipo, payload, tenant_id FROM jobs WHERE id = :id"), {"id": job_id}).fetchone()
        if not job:
            raise HTTPException(404, "Job nao encontrado")
        db.execute(text("""
            UPDATE jobs SET status='pending', attempts=0, last_error=NULL,
                           next_retry_at=NOW(), worker_id=NULL, worker_heartbeat=NULL
            WHERE id = :id
        """), {"id": job_id})
        db.commit()
        _audit(db, user, "replay_job", job[3], target_id=job_id, request=request)
        return {"ok": True, "message": f"Job #{job_id} re-enfileirado"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/dashboard/queue/pause")
async def pause_queue(db: Session = Depends(get_db), user: dict = Depends(require_superadmin), request: Request = None):
    """Pausa fila — adia todos pending em 24h."""
    try:
        db.execute(text("""
            UPDATE jobs SET next_retry_at = NOW() + INTERVAL '24 hours'
            WHERE status='pending' AND next_retry_at <= NOW()
        """))
        db.commit()
        _audit(db, user, "pause_queue", None, request=request)
        return {"ok": True, "message": "Fila pausada (jobs adiados 24h)"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/dashboard/queue/resume")
async def resume_queue(db: Session = Depends(get_db), user: dict = Depends(require_superadmin), request: Request = None):
    """Retoma fila — libera jobs adiados."""
    try:
        db.execute(text("UPDATE jobs SET next_retry_at = NOW() WHERE status='pending' AND next_retry_at > NOW()"))
        db.commit()
        _audit(db, user, "resume_queue", None, request=request)
        return {"ok": True, "message": "Fila retomada"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ══════════════════════════════════════════════════════════════════════
# SDR STUDIO — Editor de prompts do Franz SDR
# ══════════════════════════════════════════════════════════════════════

# Limites de seguranca
SDR_STUDIO_MAX_BYTES = 100 * 1024  # 100 KB por camada

# Diretorio raiz dos arquivos editaveis
_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"

# Mapeamento das 3 camadas editaveis (layer -> arquivo primario)
# Estas 3 camadas sao o ESPELHO do que o WhatsApp real injeta no system prompt do Franz.
# Quando FRALIB_SDR_PROMPTS_FROM_MD=1, o WhatsApp real le os mesmos arquivos.
_SDR_STUDIO_LAYERS: dict[str, dict[str, object]] = {
    "design_system": {
        "primary": _AGENTS_DIR / "FRANZ_PERSONA.md",
        "extras": [],
    },
    "user_system": {
        "primary": _AGENTS_DIR / "FRANZ_PLAYBOOK.md",
        "extras": [],
    },
    "rag": {
        "primary": _AGENTS_DIR / "FRANZ_RAG.md",
        "extras": [],
    },
}


def _sdr_read_concatenated(layer: str) -> str:
    """Le o conteudo da camada. Se houver extras, concatena com headers claros."""
    cfg = _SDR_STUDIO_LAYERS.get(layer)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"layer invalida: {layer}")
    primary: Path = cfg["primary"]  # type: ignore[assignment]
    extras: list[Path] = cfg["extras"]  # type: ignore[assignment]
    if not primary.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo primario nao encontrado: {primary.name}")
    parts: list[str] = []
    if extras:
        parts.append(f"# === {primary.name} ===\n")
        parts.append(primary.read_text(encoding="utf-8"))
        for extra in extras:
            if extra.exists():
                parts.append(f"\n\n# === {extra.name} ===\n")
                parts.append(extra.read_text(encoding="utf-8"))
        return "\n".join(parts)
    return primary.read_text(encoding="utf-8")


def _sdr_write_layer(layer: str, content: str) -> None:
    """Escreve o conteudo no arquivo primario da camada."""
    cfg = _SDR_STUDIO_LAYERS.get(layer)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"layer invalida: {layer}")
    primary: Path = cfg["primary"]  # type: ignore[assignment]
    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(content, encoding="utf-8")


@router.get("/sdr-studio/files")
async def sdr_studio_get_files(user: dict = Depends(require_superadmin)):
    """Retorna o conteudo atual das 3 camadas de prompt."""
    try:
        import os as _os
        md_mode = _os.getenv("FRALIB_SDR_PROMPTS_FROM_MD", "0").strip().lower() in {"1", "true", "on", "sim"}
        return {
            "ok": True,
            "design_system": _sdr_read_concatenated("design_system"),
            "user_system": _sdr_read_concatenated("user_system"),
            "rag": _sdr_read_concatenated("rag"),
            "whatsapp_mirror_enabled": md_mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[SDR Studio] get_files falhou")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sdr-studio/files/{layer}")
async def sdr_studio_save_layer(
    layer: str,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Salva o conteudo de UMA camada. Registra versao no DB antes de escrever (rollback point)."""
    if layer not in _SDR_STUDIO_LAYERS:
        raise HTTPException(status_code=400, detail=f"layer invalida: {layer}")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")
    content = body.get("content")
    note = (body.get("note") or "")[:255]
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="campo 'content' deve ser string")
    if len(content.encode("utf-8")) > SDR_STUDIO_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Conteudo excede {SDR_STUDIO_MAX_BYTES // 1024}KB",
        )

    # 1) Backup do estado atual antes de sobrescrever
    try:
        current = _sdr_read_concatenated(layer)
    except HTTPException:
        current = ""
    db.execute(
        text("""
            INSERT INTO sdr_studio_versions (layer, content, created_by, note)
            VALUES (:layer, :content, :by, :note)
        """),
        {
            "layer": layer,
            "content": current,
            "by": user.get("email", ""),
            "note": note or "auto-backup antes de save",
        },
    )
    db.commit()

    # 2) Escrever novo conteudo
    _sdr_write_layer(layer, content)

    _audit(db, user, "sdr_studio_save", None, target_id=layer,
           metadata={"layer": layer, "bytes": len(content.encode("utf-8"))},
           request=request)

    return {"ok": True, "layer": layer, "bytes": len(content.encode("utf-8"))}


@router.get("/sdr-studio/versions")
async def sdr_studio_list_versions(
    layer: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Lista as ultimas N versoes salvas (append-only)."""
    limit = max(1, min(int(limit or 20), 100))
    if layer and layer not in _SDR_STUDIO_LAYERS:
        raise HTTPException(status_code=400, detail=f"layer invalida: {layer}")
    try:
        if layer:
            rows = db.execute(
                text("""
                    SELECT id, layer, created_by, created_at, note,
                           LENGTH(content) AS bytes
                    FROM sdr_studio_versions
                    WHERE layer = :layer
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"layer": layer, "limit": limit},
            ).fetchall()
        else:
            rows = db.execute(
                text("""
                    SELECT id, layer, created_by, created_at, note,
                           LENGTH(content) AS bytes
                    FROM sdr_studio_versions
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()
        return {
            "ok": True,
            "versions": [
                {
                    "id": r[0],
                    "layer": r[1],
                    "created_by": r[2] or "",
                    "created_at": r[3].isoformat() if r[3] else None,
                    "note": r[4] or "",
                    "bytes": r[5] or 0,
                }
                for r in rows
            ],
        }
    except Exception as e:
        logger.exception("[SDR Studio] list_versions falhou")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sdr-studio/versions/{version_id}")
async def sdr_studio_get_version(
    version_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Retorna o conteudo completo de uma versao especifica."""
    row = db.execute(
        text("SELECT id, layer, content, created_by, created_at, note FROM sdr_studio_versions WHERE id = :id"),
        {"id": version_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Versao nao encontrada")
    return {
        "ok": True,
        "version": {
            "id": row[0],
            "layer": row[1],
            "content": row[2] or "",
            "created_by": row[3] or "",
            "created_at": row[4].isoformat() if row[4] else None,
            "note": row[5] or "",
        },
    }


@router.post("/sdr-studio/versions/{version_id}/restore")
async def sdr_studio_restore_version(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Restaura uma versao antiga: salva o estado atual como backup, depois escreve o conteudo antigo."""
    row = db.execute(
        text("SELECT layer, content FROM sdr_studio_versions WHERE id = :id"),
        {"id": version_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Versao nao encontrada")
    layer, content = row[0], row[1] or ""
    if layer not in _SDR_STUDIO_LAYERS:
        raise HTTPException(status_code=500, detail=f"versao com layer invalida: {layer}")

    # Backup do estado atual
    try:
        current = _sdr_read_concatenated(layer)
    except HTTPException:
        current = ""
    db.execute(
        text("""
            INSERT INTO sdr_studio_versions (layer, content, created_by, note)
            VALUES (:layer, :content, :by, :note)
        """),
        {
            "layer": layer,
            "content": current,
            "by": user.get("email", ""),
            "note": f"auto-backup antes de restore v{version_id}",
        },
    )
    db.commit()

    _sdr_write_layer(layer, content)

    _audit(db, user, "sdr_studio_restore", None, target_id=version_id,
           metadata={"layer": layer, "version_id": version_id}, request=request)

    return {"ok": True, "layer": layer, "restored_from": version_id}


from fastapi.responses import StreamingResponse as _StreamingResponse


@router.post("/sdr-studio/chat/stream")
async def sdr_studio_chat_stream(
    request: Request,
    user: dict = Depends(require_superadmin),
):
    """Chat de teste com streaming SSE. Yield chunks incrementais."""
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "detail": "JSON invalido"}
    messages = body.get("messages") or []
    stage = (body.get("stage") or "hook").strip()
    segmento = (body.get("segmento") or "academia").strip()
    cidade = (body.get("cidade") or "Sao Paulo").strip()
    modelo = (body.get("modelo") or "sonnet").strip()
    if not isinstance(messages, list) or not messages:
        return {"ok": False, "detail": "'messages' deve ser lista nao vazia"}

    try:
        ds = _sdr_read_concatenated("design_system")
        us = _sdr_read_concatenated("user_system")
        rag_layer = _sdr_read_concatenated("rag")
    except Exception as e:
        return {"ok": False, "detail": str(e)}

    # System prompt com FSM stage prompt + persona
    from backend.agents.sdr_langgraph.prompts import (
        FRANZ_PERSONA, get_prompt_for_persona,
    )
    stage_prompt = get_prompt_for_persona("consultivo", stage)
    system = f"{FRANZ_PERSONA}\n\n{stage_prompt}\n\nCONTEXTO RAG:\n{rag_layer}"
    user_msg = messages[-1].get("content", "")
    history = [{"role": m.get("role"), "content": m.get("content", "")}
               for m in messages[:-1] if m.get("role") in ("user", "assistant")]
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-5:])
    user_prompt = f"""LEAD: {user_msg}
CONTEXTO: segmento={segmento}, cidade={cidade}, stage={stage}
HISTORICO:
{history_text or '(sem historico)'}
Responda em pt-BR, tom consultivo, max 3 linhas."""

    async def event_generator():
        try:
            from backend.agents.sdr_langgraph.streaming import stream_franz_reply
            for chunk in stream_franz_reply(
                system=system,
                user=user_prompt,
                model=modelo,
                max_tokens=800,
                temperature=0.7,
            ):
                # SSE: cada chunk eh data: <texto>\n\n
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return _StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/sdr-studio/chat")
async def sdr_studio_chat(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Chat de teste com o Franz usando o system prompt atual (3 camadas concatenadas)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")
    messages = body.get("messages") or []
    stage = (body.get("stage") or "hook").strip()
    segmento = (body.get("segmento") or "academia").strip()
    cidade = (body.get("cidade") or "Sao Paulo").strip()
    modelo = (body.get("modelo") or "sonnet").strip()
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="'messages' deve ser lista nao vazia")
    if len(messages) > 30:
        raise HTTPException(status_code=400, detail="limite de 30 mensagens por chamada")

    # 1) Montar system prompt a partir dos 3 arquivos editaveis.
    #    Quando FRALIB_SDR_PROMPTS_FROM_MD=1, usa os mesmos helpers que o WhatsApp real
    #    (get_franz_persona / get_franz_stage_prompt / get_franz_rag) -> espelho fiel.
    import os as _os
    md_mode = _os.getenv("FRALIB_SDR_PROMPTS_FROM_MD", "0").strip().lower() in {"1", "true", "on", "sim"}
    try:
        ds = _sdr_read_concatenated("design_system")
        us = _sdr_read_concatenated("user_system")
        rag_layer = _sdr_read_concatenated("rag")
    except HTTPException:
        raise

    if md_mode:
        try:
            from agents.sdr_langgraph.prompts import (
                get_franz_persona, get_franz_stage_prompt, get_franz_rag,
            )
            persona = get_franz_persona()
            stage_prompt = get_franz_stage_prompt(stage) or us
            rag_inject = get_franz_rag() or rag_layer
        except Exception as e:
            logger.warning("[SDR Studio] helpers .md indisponiveis, usando conteudo direto: %s", e)
            persona, stage_prompt, rag_inject = ds, us, rag_layer
    else:
        persona, stage_prompt, rag_inject = ds, us, rag_layer

    system_prompt = (
        f"{persona}\n\n"
        f"{stage_prompt}\n\n"
        f"CONTEXTO RAG (conhecimento da base):\n{rag_inject}\n"
    )

    # 2) Construir o user prompt via build_user_prompt do sdr_langgraph (reutilizado de producao)
    history = [{"role": m.get("role"), "content": m.get("content", "")}
               for m in messages[:-1] if m.get("role") in ("user", "assistant")]
    incoming = messages[-1].get("content", "")
    try:
        from agents.sdr_langgraph.prompts import build_user_prompt
        user_prompt = build_user_prompt(
            stage=stage,
            incoming_message=incoming,
            nome="(lead de teste do SDR Studio)",
            cidade=cidade,
            segmento=segmento,
            rating=0.0,
            history=history,
            memory_facts=None,
        )
    except Exception as e:
        logger.warning("[SDR Studio] build_user_prompt falhou, usando fallback: %s", e)
        user_prompt = (
            f"CONTEXTO: lead de teste, segmento={segmento}, cidade={cidade}, stage={stage}\n"
            f"MENSAGEM: \"{incoming}\"\n"
            "Responda em pt-BR, tom consultivo, max 3 linhas."
        )

    # 3) Chamar Claude via llm_direct
    import time as _time
    t0 = _time.time()
    try:
        from agents.llm_direct import call_claude
        reply = call_claude(
            system=system_prompt,
            user=user_prompt,
            model=modelo,
            max_tokens=800,
            temperature=0.7,
            agent_name="sdr_studio",
            respect_agent_config=False,
            enable_context=False,
        )
    except Exception as e:
        logger.exception("[SDR Studio] call_claude falhou")
        raise HTTPException(status_code=502, detail=f"Falha ao chamar LLM: {e}")
    latency_ms = int((_time.time() - t0) * 1000)

    _audit(db, user, "sdr_studio_chat", None,
           metadata={"stage": stage, "segmento": segmento, "model": modelo,
                     "latency_ms": latency_ms, "msgs": len(messages)},
           request=request)

    return {
        "ok": True,
        "reply": reply or "",
        "latency_ms": latency_ms,
        "model": modelo,
    }
