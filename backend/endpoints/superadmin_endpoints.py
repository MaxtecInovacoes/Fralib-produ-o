from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from auth import get_current_user
from database import get_db
from sqlalchemy.orm import Session
import jwt
import json
import os

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
        if plano not in ("trial", "starter", "pro", "beta", "admin"):
            raise HTTPException(status_code=400, detail="Plano invalido")
        
        row = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        
        plano_pago = plano in ("starter", "pro", "beta")
        db.execute(text(
            "UPDATE users SET plano = :plano, plano_pago = :pago WHERE id = :id"
        ), {"plano": plano, "pago": plano_pago, "id": user_id})
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
            {"sub": str(row[0]), "email": row[1], "role": row[2] or "user"},
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
