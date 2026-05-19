from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from auth import get_current_user
from database import get_db
from sqlalchemy.orm import Session
import jwt
import json
import os
from datetime import datetime, timedelta

router = APIRouter(prefix='/api/superadmin', tags=['superadmin'])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ALGORITHM = "HS256"

# Acesso restrito APENAS a dezigpi@gmail.com
SUPERADMIN_EMAIL = "dezigpi@gmail.com"

def require_superadmin(user: dict = Depends(get_current_user)):
    if user.get("email") != SUPERADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso negado: Super Admin apenas")
    return user


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
        
        # Custo estimado USD (claude-sonnet input=$3/M, output=$15/M; opus input=$15/M, output=$75/M; haiku input=$0.25/M, output=$1.25/M)
        cost_row = db.execute(text("""
            SELECT 
                COALESCE(SUM(CASE WHEN modelo LIKE '%opus%' THEN input_tokens * 15.0 / 1000000 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN modelo LIKE '%sonnet%' THEN input_tokens * 3.0 / 1000000 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN modelo LIKE '%haiku%' THEN input_tokens * 0.25 / 1000000 ELSE 0 END), 0) as input_cost,
                COALESCE(SUM(CASE WHEN modelo LIKE '%opus%' THEN output_tokens * 75.0 / 1000000 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN modelo LIKE '%sonnet%' THEN output_tokens * 15.0 / 1000000 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN modelo LIKE '%haiku%' THEN output_tokens * 1.25 / 1000000 ELSE 0 END), 0) as output_cost
            FROM llm_usage
        """)).fetchone()
        custo_total = (cost_row[0] or 0) + (cost_row[1] or 0)
        
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
        raise HTTPException(status_code=500, detail=str(e))


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
                (SELECT COUNT(*) FROM leads WHERE user_id = u.id) as total_leads,
                (SELECT COUNT(*) FROM leads WHERE user_id = u.id AND processado = true) as sites_prontos,
                (SELECT COALESCE(SUM(tokens_consumidos), 0) FROM token_transactions WHERE user_id = u.id) as tokens_total,
                (SELECT COALESCE(SUM(input_tokens), 0) FROM llm_usage WHERE user_id = u.id) as llm_input,
                (SELECT COALESCE(SUM(output_tokens), 0) FROM llm_usage WHERE user_id = u.id) as llm_output
            FROM users u
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/toggle")
async def toggle_user(user_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Ativar/desativar usuario"""
    try:
        row = db.execute(text("SELECT status, email FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        if row[1] == SUPERADMIN_EMAIL:
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/set-plan")
async def set_plan(user_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Alterar plano do usuario - recebe JSON {plano: 'trial'|'starter'|'pro'}"""
    try:
        body = await request.json()
        plano = body.get("plano", "trial")
        if plano not in ("trial", "starter", "pro", "ilimitado", "beta", "admin"):
            raise HTTPException(status_code=400, detail="Plano invalido")
        
        row = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        
        plano_pago = plano in ("starter", "pro", "beta", "ilimitado")
        status_novo = "ativo" if plano_pago else plano
        db.execute(text(
            "UPDATE users SET plano = :plano, plano_pago = :pago, status = :status WHERE id = :id"
        ), {"plano": plano, "pago": plano_pago, "status": status_novo, "id": user_id})
        db.commit()

        _audit(db, user, "set_plan", user_id, target_id=user_id,
               metadata={"plano": plano, "plano_pago": plano_pago}, request=request)

        return {"ok": True, "plano": plano, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# DASHBOARD CRÍTICO — Métricas de operação, custos, saúde, alertas
# ══════════════════════════════════════════════════════════════════════

# Preços por 1M tokens (USD)
_PRECOS = {
    "opus": {"input": 15.0, "output": 75.0},
    "claude-opus-4-0-20250514": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-6-20250514": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.25, "output": 1.25},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
}

def _calcular_custo(modelo: str, input_tokens: int, output_tokens: int) -> float:
    modelo_lower = (modelo or "").lower()
    precos = None
    for key, val in _PRECOS.items():
        if key in modelo_lower:
            precos = val
            break
    if not precos:
        precos = _PRECOS["sonnet"]
    return (input_tokens * precos["input"] + output_tokens * precos["output"]) / 1_000_000


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
            SELECT
                COALESCE(SUM(custo_total_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours'), 0) as custo_24h,
                COALESCE(SUM(custo_total_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0) as custo_7d,
                COALESCE(SUM(custo_total_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days'), 0) as custo_30d,
                COALESCE(AVG(custo_total_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0) as custo_medio_site,
                COALESCE(AVG(duracao_s) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0) as duracao_media_s
            FROM pipeline_token_usage
        """)).fetchone()

        fila_row = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pendentes,
                COUNT(*) FILTER (WHERE status = 'running') as rodando,
                COUNT(*) FILTER (WHERE status = 'failed_permanent') as dead_letter
            FROM jobs WHERE created_at > NOW() - INTERVAL '7 days'
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
                       ROUND(SUM(custo_total_usd)::numeric, 3) as custo,
                       ROUND(AVG(custo_total_usd)::numeric, 3) as custo_medio
                FROM pipeline_token_usage
                WHERE created_at > NOW() - (:hours || ' hours')::interval
                GROUP BY dia ORDER BY dia
            """), {"hours": hours}).fetchall()
            return {"group_by": "day", "data": [
                {"dia": str(r[0]), "runs": r[1], "custo": float(r[2] or 0), "custo_medio": float(r[3] or 0)} for r in rows
            ]}

        if group_by == "agent":
            rows = db.execute(text("""
                SELECT key as agente,
                       COUNT(*) as runs,
                       ROUND(SUM((value->>'custo_usd')::float)::numeric, 4) as custo,
                       ROUND(SUM((value->>'input_tokens')::int)::numeric, 0) as input_tokens,
                       ROUND(SUM((value->>'output_tokens')::int)::numeric, 0) as output_tokens
                FROM pipeline_token_usage, jsonb_each(por_agente)
                WHERE created_at > NOW() - (:hours || ' hours')::interval
                GROUP BY key ORDER BY custo DESC
            """), {"hours": hours}).fetchall()
            return {"group_by": "agent", "data": [
                {"agente": r[0], "runs": r[1], "custo": float(r[2] or 0),
                 "input_tokens": int(r[3] or 0), "output_tokens": int(r[4] or 0)} for r in rows
            ]}

        if group_by == "model":
            rows = db.execute(text("""
                SELECT modelo, COUNT(*) as calls,
                       SUM(input_tokens) as input_t, SUM(output_tokens) as output_t
                FROM llm_usage
                WHERE criado_em > NOW() - (:hours || ' hours')::interval
                GROUP BY modelo ORDER BY input_t DESC
            """), {"hours": hours}).fetchall()
            data = []
            for r in rows:
                custo = _calcular_custo(r[0], r[2] or 0, r[3] or 0)
                data.append({"modelo": r[0], "calls": r[1], "input_tokens": r[2] or 0,
                             "output_tokens": r[3] or 0, "custo_usd": round(custo, 3)})
            return {"group_by": "model", "data": data}

        if group_by == "segmento":
            rows = db.execute(text("""
                SELECT nicho, COUNT(*) as runs,
                       ROUND(SUM(custo_total_usd)::numeric, 3) as custo,
                       ROUND(AVG(custo_total_usd)::numeric, 3) as custo_medio
                FROM pipeline_token_usage
                WHERE created_at > NOW() - (:hours || ' hours')::interval AND nicho IS NOT NULL
                GROUP BY nicho ORDER BY custo DESC
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
            SELECT COALESCE(SUM(custo_total_usd), 0) as custo_7d, COUNT(*) as runs_7d
            FROM pipeline_token_usage WHERE created_at > NOW() - INTERVAL '7 days'
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
            WHERE created_at > NOW() - (:hours || ' hours')::interval
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

    try:
        fila = db.execute(text("""
            SELECT COUNT(*) FILTER (WHERE status='pending') as pending,
                   COUNT(*) FILTER (WHERE status='running') as running,
                   COUNT(*) FILTER (WHERE status='failed_permanent' AND created_at > NOW() - INTERVAL '24 hours') as failed_24h
            FROM jobs
        """)).fetchone()
        health["queue"] = {"pending": fila[0] or 0, "running": fila[1] or 0, "failed_24h": fila[2] or 0}
    except Exception:
        health["queue"] = {"status": "unknown"}

    try:
        import psutil
        health["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        }
    except Exception:
        health["system"] = {"cpu_percent": None, "ram_percent": None, "disk_percent": None}

    return health


@router.get("/dashboard/alerts")
async def dashboard_alerts(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Alertas ativos baseados em regras."""
    alerts = []

    try:
        custo_hoje = db.execute(text(
            "SELECT COALESCE(SUM(custo_total_usd), 0) FROM pipeline_token_usage WHERE created_at >= CURRENT_DATE"
        )).scalar() or 0
        if custo_hoje > 20:
            alerts.append({"severity": "warning", "rule": "custo_diario_alto",
                           "message": f"Custo hoje: ${custo_hoje:.2f} (limite: $20)", "value": round(custo_hoje, 2)})

        falhas_recentes = db.execute(text("""
            SELECT fase, COUNT(*) as total FROM pipeline_failures
            WHERE created_at > NOW() - INTERVAL '1 hour'
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


@router.get("/dashboard/jobs/failed")
async def dashboard_jobs_failed(db: Session = Depends(get_db), user: dict = Depends(require_superadmin),
                                limit: int = 20):
    """Jobs falhados com detalhes para replay."""
    try:
        rows = db.execute(text("""
            SELECT pf.id, pf.job_id, pf.lead_nome, pf.fase, pf.mensagem_amigavel,
                   pf.erro_tecnico, pf.tentativas_automaticas, pf.created_at, pf.tenant_id, u.email
            FROM pipeline_failures pf LEFT JOIN users u ON u.id = pf.tenant_id
            ORDER BY pf.created_at DESC LIMIT :limit
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
