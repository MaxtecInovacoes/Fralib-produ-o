"""
Endpoints admin/outreach — campanha de reativação (Sprint 14.3).

Endpoints:
- GET  /api/admin/outreach/inativos              → lista candidatos
- POST /api/admin/outreach/disparar/{campaign}   → dispara (DRY_RUN por padrão)
- GET  /api/admin/outreach/dashboard/{campaign}  → métricas
- GET  /api/admin/outreach/respostas             → inbox de replies
- GET  /api/admin/outreach/contato-direto        → leads com wa.me (Sprint 14.6)

Idempotência: UNIQUE INDEX (user_id, campaign, channel) garante 1 envio/user/campanha.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.access_control import require_superadmin
from backend.core.database import get_db
from backend.services.email_service import (
    enviar_email_reativacao_step1,
    enviar_email_reativacao_step2,
    enviar_email_reativacao_step3,
    enviar_email_reativacao_step4,
    enviar_email_reativacao_step5,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/outreach", tags=["admin-outreach"])

# Jitter humanizado entre envios (mesmo padrão do cron_endpoints.py)
REATIVACAO_JITTER_MIN_S = 18
REATIVACAO_JITTER_MAX_S = 75


# ----------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------
class DispararRequest(BaseModel):
    dry_run: bool = True
    campaign: Optional[str] = None  # se None, gera nome automático
    step: int = 1  # qual step do drip disparar (1-5)
    user_ids: Optional[list[int]] = None  # se passado, envia só para esses users (bypass filtro inativos)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _dias_cadastrado(criado_em_str: str | None) -> int:
    """Calcula dias desde o cadastro. Trata criado_em como ISO string."""
    if not criado_em_str:
        return 0
    try:
        criado = datetime.fromisoformat(str(criado_em_str).replace("Z", "+00:00").split(".")[0])
        if criado.tzinfo:
            criado = criado.replace(tzinfo=None)
        return max(0, (datetime.utcnow() - criado).days)
    except Exception:
        return 0


# ----------------------------------------------------------------------------
# GET /inativos — lista candidatos (sites_used=0, email_confirmado=true)
# ----------------------------------------------------------------------------
@router.get("/inativos")
async def listar_inativos(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Lista clientes que confirmaram email mas nunca usaram a ferramenta."""
    rows = db.execute(text("""
        SELECT
            u.id,
            u.email,
            COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome,
            u.plano,
            u.status,
            u.email_confirmado,
            u.creditos,
            u.criado_em,
            u.telefone,
            (SELECT COUNT(*) FROM outreach_attempts oa
             WHERE oa.user_id = u.id) AS outreach_enviados
        FROM users u
        WHERE u.email_confirmado = true
          AND u.status NOT IN ('blocked', 'suspended', 'deleted', 'inativo')
          AND u.email NOT LIKE 'test.%@test.com'
          AND u.email NOT LIKE 'pipeline.%@test.com'
          AND u.email NOT LIKE 'smoke.%@test.com'
          AND COALESCE(u.sites_used, 0) = 0
          AND COALESCE(u.tokens_used_today, 0) = 0
          AND COALESCE(u.tokens_used_month, 0) = 0
          AND COALESCE(u.sdr_messages_today, 0) = 0
        ORDER BY
            CASE u.plano WHEN 'ilimitado' THEN 0 WHEN 'pro' THEN 1 ELSE 2 END,
            u.criado_em ASC
    """)).fetchall()

    items = []
    for r in rows:
        items.append({
            "id": int(r[0]),
            "email": r[1],
            "nome": r[2],
            "plano": r[3],
            "status": r[4],
            "email_confirmado": r[5],
            "creditos": int(r[6] or 0),
            "criado_em": r[7],
            "dias_cadastrado": _dias_cadastrado(r[7]),
            "telefone": r[8],
            "outreach_enviados": int(r[9] or 0),
        })

    return {
        "total": len(items),
        "items": items,
    }


# ----------------------------------------------------------------------------
# POST /disparar/{campaign} — dispara email (idempotente)
# ----------------------------------------------------------------------------
@router.post("/disparar/{campaign}")
async def disparar_campanha(
    campaign: str,
    payload: DispararRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Dispara email de reativação para todos os inativos.

    Idempotente: se outreach_attempts já tem (user_id, campaign, 'email'),
    pula. dry_run=true (default) só simula — não envia.
    """
    dry_run = payload.dry_run
    channel = "email"

    # Lista inativos (mesmo filtro do GET /inativos) OU user_ids especificos
    if payload.user_ids:
        # Bypass filtro: envia só para os user_ids passados (modo manual, ex: admin demo)
        candidatos = db.execute(text("""
            SELECT
                u.id,
                u.email,
                COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome,
                u.plano,
                u.creditos,
                u.criado_em
            FROM users u
            WHERE u.id = ANY(:uids)
        """), {"uids": payload.user_ids}).fetchall()
    else:
        candidatos = db.execute(text("""
            SELECT
                u.id,
                u.email,
                COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome,
                u.plano,
                u.creditos,
                u.criado_em
            FROM users u
            WHERE u.email_confirmado = true
              AND u.status NOT IN ('blocked', 'suspended', 'deleted', 'inativo')
              AND u.email NOT LIKE 'test.%@test.com'
              AND u.email NOT LIKE 'pipeline.%@test.com'
              AND u.email NOT LIKE 'smoke.%@test.com'
              AND COALESCE(u.sites_used, 0) = 0
            ORDER BY
                CASE u.plano WHEN 'ilimitado' THEN 0 WHEN 'pro' THEN 1 ELSE 2 END,
                u.criado_em ASC
        """)).fetchall()

    enviados = 0
    pulados = 0
    erros = 0
    detalhes = []

    step_funcs = {
        1: enviar_email_reativacao_step1,
        2: enviar_email_reativacao_step2,
        3: enviar_email_reativacao_step3,
        4: enviar_email_reativacao_step4,
        5: enviar_email_reativacao_step5,
    }

    if payload.step not in step_funcs:
        raise HTTPException(400, f"step deve ser 1-5, recebido {payload.step}")

    send_func = step_funcs[payload.step]

    for row in candidatos:
        user_id, email, nome, plano, creditos, criado_em = (
            int(row[0]), row[1], row[2], row[3], int(row[4] or 0), row[5]
        )
        dias = _dias_cadastrado(criado_em)

        # Verifica idempotencia por step: outreach_attempts UNIQUE (user_id, campaign, channel)
        # mas cada step e uma row diferente (step fica em metadata.jsonb)
        # entao a dedup e (user_id, campaign, channel, step)
        existing = db.execute(text("""
            SELECT id, status FROM outreach_attempts
            WHERE user_id = :uid AND campaign = :camp
              AND channel = :ch
              AND metadata->>'step' = :step
        """), {"uid": user_id, "camp": campaign, "ch": channel, "step": str(payload.step)}).fetchone()

        if existing:
            pulados += 1
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "skipped",
                "motivo": f"step_{payload.step}_ja_enviado (status={existing[1]})",
            })
            continue

        if dry_run:
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "would_send",
                "step": payload.step,
                "dias_cadastrado": dias,
                "plano": plano,
                "creditos": creditos,
            })
            continue

        # Tenta inserir pending + enviar
        try:
            db.execute(text("""
                INSERT INTO outreach_attempts (user_id, campaign, channel, status, metadata)
                VALUES (:uid, :camp, :ch, 'pending', CAST(:meta AS JSONB))
            """), {
                "uid": user_id,
                "camp": campaign,
                "ch": channel,
                "meta": f'{{"step": {payload.step}, "source": "admin_outreach_disparar"}}',
            })
            db.commit()
        except Exception as e:
            # UNIQUE violation = duplicata (race condition)
            db.rollback()
            pulados += 1
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "skipped",
                "motivo": f"race_dedup: {str(e)[:80]}",
            })
            continue

        # Envia - cada step tem assinatura diferente
        try:
            if payload.step == 1:
                ok = await send_func(email=email, nome=nome, dias_cadastrado=dias,
                                     plano=plano or "trial", creditos=creditos)
            elif payload.step == 5:
                ok = await send_func(email=email, nome=nome, plano=plano or "trial",
                                     creditos=creditos)
            else:
                ok = await send_func(email=email, nome=nome)
        except Exception as e:
            ok = False
            print(f"[Admin outreach] erro ao enviar step {payload.step} para user {user_id}: {e}")

        if ok:
            db.execute(text("""
                UPDATE outreach_attempts
                SET status = 'sent', sent_at = NOW()
                WHERE user_id = :uid AND campaign = :camp AND channel = :ch
            """), {"uid": user_id, "camp": campaign, "ch": channel})
            db.commit()
            enviados += 1
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "sent",
                "dias_cadastrado": dias,
            })
        else:
            db.execute(text("""
                UPDATE outreach_attempts
                SET status = 'failed', error_message = 'enviar_email_reativacao retornou False'
                WHERE user_id = :uid AND campaign = :camp AND channel = :ch
            """), {"uid": user_id, "camp": campaign, "ch": channel})
            db.commit()
            erros += 1
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "failed",
            })

        # Jitter humanizado entre envios
        if not dry_run:
            sleep_s = random.uniform(REATIVACAO_JITTER_MIN_S, REATIVACAO_JITTER_MAX_S)
            await asyncio.sleep(sleep_s)

    # Relatorio paralelo ao admin (so quando envio real, nao dry_run)
    if not dry_run and (enviados > 0 or erros > 0):
        try:
            from backend.services.email_service import enviar_relatorio_drip_admin
            await enviar_relatorio_drip_admin(
                campaign=campaign,
                step=payload.step,
                enviados=enviados,
                pulados=pulados,
                erros=erros,
                total_candidatos=len(candidatos),
            )
        except Exception as e:
            print(f"[Admin outreach] relatorio admin falhou: {e}")

    return {
        "campaign": campaign,
        "step": payload.step,
        "dry_run": dry_run,
        "total_candidatos": len(candidatos),
        "enviados": enviados,
        "pulados": pulados,
        "erros": erros,
        "detalhes": detalhes,
    }


# ----------------------------------------------------------------------------
# POST /marcar-replied/{campaign}/{user_id} — tracking manual de resposta
# ----------------------------------------------------------------------------
class MarcarRepliedRequest(BaseModel):
    nota: Optional[str] = None


@router.post("/marcar-replied/{campaign}/{user_id}")
async def marcar_replied(
    campaign: str,
    user_id: int,
    payload: MarcarRepliedRequest = MarcarRepliedRequest(),
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Marca outreach como 'replied' manualmente.

    Use quando o admin recebe resposta do cliente por qualquer canal
    (email, WhatsApp, telefone) e quer parar a sequencia de drip.

    Tambem atualiza replied_at na row para o dashboard refletir.
    """
    # Atualiza todas as rows sent dessa campanha+user
    result = db.execute(text("""
        UPDATE outreach_attempts
        SET status = 'replied',
            replied_at = NOW(),
            atualizado_em = NOW()
        WHERE user_id = :uid
          AND campaign = :camp
          AND channel = 'email'
          AND status = 'sent'
        RETURNING id
    """), {"uid": user_id, "camp": campaign})
    updated = len(result.fetchall())
    db.commit()

    if updated == 0:
        return {
            "ok": False,
            "mensagem": f"Nenhum outreach 'sent' encontrado para user {user_id} na campanha {campaign}",
        }

    return {
        "ok": True,
        "user_id": user_id,
        "campaign": campaign,
        "rows_atualizadas": updated,
        "mensagem": "Sequencia de drip parada para este usuario.",
    }


# ----------------------------------------------------------------------------
# GET /drip-progresso/{campaign} — progresso detalhado por step
# ----------------------------------------------------------------------------
@router.get("/drip-progresso/{campaign}")
async def drip_progresso(
    campaign: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Mostra quantos usuarios estao em cada step do drip + status."""
    rows = db.execute(text("""
        SELECT
            COALESCE((metadata->>'step')::int, 0) AS step,
            COUNT(*) FILTER (WHERE status = 'sent') AS sent,
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed,
            COUNT(*) FILTER (WHERE status = 'replied') AS replied,
            COUNT(*) FILTER (WHERE status = 'converted') AS converted,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed
        FROM outreach_attempts
        WHERE campaign = :camp AND channel = 'email'
        GROUP BY step
        ORDER BY step
    """), {"camp": campaign}).fetchall()

    steps = []
    for row in rows:
        steps.append({
            "step": int(row[0]),
            "sent": int(row[1]),
            "pending": int(row[2]),
            "failed": int(row[3]),
            "replied": int(row[4]),
            "converted": int(row[5]),
            "completed": int(row[6]),
        })

    # Total geral
    total_users = db.execute(text("""
        SELECT COUNT(DISTINCT user_id)
        FROM outreach_attempts
        WHERE campaign = :camp
    """), {"camp": campaign}).scalar() or 0

    return {
        "campaign": campaign,
        "total_users": int(total_users),
        "steps": steps,
    }


# ----------------------------------------------------------------------------
# GET /dashboard/{campaign} — métricas
# ----------------------------------------------------------------------------
@router.get("/dashboard/{campaign}")
async def dashboard_campanha(
    campaign: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Métricas agregadas da campanha + taxa de conversão (voltou a usar)."""
    counts = db.execute(text("""
        SELECT
            status,
            COUNT(*) AS n
        FROM outreach_attempts
        WHERE campaign = :camp
        GROUP BY status
    """), {"camp": campaign}).fetchall()

    metrics = {row[0]: int(row[1]) for row in counts}
    total = sum(metrics.values())

    # Conversão: outreach que resultaram em uso real (sites_used > 0 ou tokens_used_month > 0)
    converted = db.execute(text("""
        SELECT COUNT(DISTINCT oa.user_id)
        FROM outreach_attempts oa
        JOIN users u ON u.id = oa.user_id
        WHERE oa.campaign = :camp
          AND (COALESCE(u.sites_used, 0) > 0
               OR COALESCE(u.tokens_used_month, 0) > 0
               OR COALESCE(u.sdr_messages_today, 0) > 0)
    """), {"camp": campaign}).scalar() or 0

    conversion_rate = (converted / total * 100) if total else 0.0

    return {
        "campaign": campaign,
        "total": total,
        "by_status": metrics,
        "converted_users": int(converted),
        "conversion_rate_pct": round(conversion_rate, 2),
    }


# ----------------------------------------------------------------------------
# GET /respostas — inbox de replies
# ----------------------------------------------------------------------------
@router.get("/respostas")
async def listar_respostas(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Lista outreach que tiveram replied_at preenchido (futuro: webhook Resend)."""
    rows = db.execute(text("""
        SELECT
            oa.id,
            oa.user_id,
            oa.campaign,
            oa.channel,
            oa.replied_at,
            u.email,
            COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome
        FROM outreach_attempts oa
        JOIN users u ON u.id = oa.user_id
        WHERE oa.replied_at IS NOT NULL
        ORDER BY oa.replied_at DESC
    """)).fetchall()

    return {
        "total": len(rows),
        "items": [
            {
                "outreach_id": int(r[0]),
                "user_id": int(r[1]),
                "campaign": r[2],
                "channel": r[3],
                "replied_at": r[4].isoformat() if r[4] else None,
                "email": r[5],
                "nome": r[6],
            }
            for r in rows
        ],
    }


# ----------------------------------------------------------------------------
# GET /contato-direto — lista users com telefone valido + outreach atual
# ----------------------------------------------------------------------------
@router.get("/contato-direto")
async def contato_direto(
    plano: str = Query("todos", description="trial|todos|pro|ilimitado|..."),
    status: str = Query("todos", description="todos|sem_outreach|replied|converted"),
    q: str = Query("", description="busca por nome ou email"),
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Lista usuarios com telefone valido para contato direto via WhatsApp.

    Filtros:
    - plano: filtra por plano do usuario (default: todos)
    - status: sem_outreach|replied|converted|todos
    - q: busca livre por nome ou email

    Gera wa_link no formato: https://wa.me/55{numero}?text={msg_encoded}
    """
    # Query principal: users com telefone valido + outreach atual
    # Status 'converted' = user que voltou a usar (sites_used > 0 ou tokens > 0)
    # Status 'replied' = tem outreach_attempts com status replied
    # Status 'sem_outreach' = nao tem outreach_attempts para esta campanha
    rows = db.execute(text("""
        WITH outreach_status AS (
            SELECT
                oa.user_id,
                MAX(oa.status) AS outreach_status,
                MAX(oa.replied_at) AS replied_at,
                COUNT(*) FILTER (WHERE oa.status = 'sent') AS outreach_sent,
                MAX(oa.campaign) AS last_campaign
            FROM outreach_attempts oa
            WHERE oa.campaign = 'reativacao_drip_v1_2026_06_26'
            GROUP BY oa.user_id
        ),
        user_with_outreach AS (
            SELECT
                u.id AS user_id,
                u.email,
                COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome,
                u.plano,
                u.status AS user_status,
                u.telefone,
                u.criado_em,
                COALESCE(u.sites_used, 0) AS sites_used,
                COALESCE(u.tokens_used_month, 0) AS tokens_used_month,
                COALESCE(u.sdr_messages_today, 0) AS sdr_messages_today,
                COALESCE(os.outreach_status, 'none') AS outreach_status,
                COALESCE(os.replied_at, NULL) AS replied_at,
                COALESCE(os.outreach_sent, 0) AS outreach_sent,
                COALESCE(os.last_campaign, '') AS last_campaign
            FROM users u
            LEFT JOIN outreach_status os ON os.user_id = u.id
            WHERE u.email_confirmado = true
              AND u.status NOT IN ('blocked', 'suspended', 'deleted', 'inativo')
              AND u.email NOT LIKE 'test.%@test.com'
              AND u.email NOT LIKE 'pipeline.%@test.com'
              AND u.email NOT LIKE 'smoke.%@test.com'
              -- Telefone valido: existe e tem 10-11 digitos (DDD + numero)
              AND u.telefone IS NOT NULL
              AND LENGTH(REGEXP_REPLACE(u.telefone, '[^0-9]', '', 'g')) BETWEEN 10 AND 11
        )
        SELECT * FROM user_with_outreach
        WHERE 1=1
          -- Filtro plano
          AND (:plano = 'todos' OR plano = :plano)
          -- Filtro status outreach
          AND (
            (:status = 'todos')
            OR (:status = 'sem_outreach' AND outreach_status = 'none')
            OR (:status = 'replied' AND outreach_status = 'replied')
            OR (:status = 'converted' AND (
                outreach_status = 'converted'
                OR sites_used > 0
                OR tokens_used_month > 0
                OR sdr_messages_today > 0
            ))
          )
          -- Busca livre
          AND (
            :q = ''
            OR LOWER(nome) LIKE '%' || LOWER(:q) || '%'
            OR LOWER(email) LIKE '%' || LOWER(:q) || '%'
          )
        ORDER BY
            CASE
                WHEN :status = 'sem_outreach' THEN 0
                WHEN outreach_status = 'replied' THEN 1
                WHEN sites_used > 0 OR tokens_used_month > 0 OR sdr_messages_today > 0 THEN 2
                ELSE 3
            END,
            outreach_sent DESC,
            nome ASC
    """), {
        "plano": plano if plano != "todos" else "todos",
        "status": status,
        "q": q,
    }).fetchall()

    items = []
    for r in rows:
        user_id = int(r[0])
        email = str(r[1])
        nome = str(r[2])
        plano_val = str(r[3]) if r[3] else "trial"
        user_status = str(r[4]) if r[4] else "trial"
        telefone = str(r[5]) if r[5] else ""
        criado_em = r[6]
        sites_used = int(r[7] or 0)
        tokens_used_month = int(r[8] or 0)
        sdr_messages_today = int(r[9] or 0)
        outreach_status = str(r[10]) if r[10] else "none"
        replied_at = r[11]
        outreach_sent = int(r[12] or 0)
        last_campaign = str(r[13]) if r[13] else ""

        # Normalizar telefone para wa.me
        # Remove tudo que nao e digito
        digits_only = "".join(filter(str.isdigit, telefone))
        # Se comeca com 0 (prefixo internacional), remove
        if digits_only.startswith("0"):
            digits_only = digits_only[1:]
        # Garante 10-11 digitos (DDD + 9 digitos ou DDD + 8 digitos)
        if len(digits_only) >= 10:
            # Usa apenas os 11 primeiros digitos se tiver mais
            numero_normalizado = digits_only[:11]
            # Mensagem padrao
            msg = f"Oi {nome.split()[0]}, tudo bem? Vi que voce tem um site do FraLib esperando por voce. Posso te ajudar a finalizar? 😊"
            from urllib.parse import quote
            msg_encoded = quote(msg)
            wa_link = f"https://wa.me/55{numero_normalizado}?text={msg_encoded}"
        else:
            wa_link = None
            numero_normalizado = None

        # Determinar status final para exibicao
        if sites_used > 0 or tokens_used_month > 0 or sdr_messages_today > 0:
            display_status = "converted"
        elif outreach_status == "replied":
            display_status = "replied"
        elif outreach_status == "none":
            display_status = "sem_outreach"
        else:
            display_status = outreach_status

        items.append({
            "user_id": user_id,
            "email": email,
            "nome": nome,
            "plano": plano_val,
            "user_status": user_status,
            "telefone": telefone,
            "telefone_normalizado": numero_normalizado,
            "wa_link": wa_link,
            "criado_em": str(criado_em) if criado_em else None,
            "sites_used": sites_used,
            "tokens_used_month": tokens_used_month,
            "sdr_messages_today": sdr_messages_today,
            "outreach_status": outreach_status,
            "outreach_sent": outreach_sent,
            "last_campaign": last_campaign,
            "display_status": display_status,
            "replied_at": replied_at.isoformat() if replied_at else None,
        })

    # Estatisticas para os cards do topo
    total = len(items)
    sem_contato = sum(1 for i in items if i["display_status"] == "sem_outreach")
    replied = sum(1 for i in items if i["display_status"] == "replied")
    convertidos = sum(1 for i in items if i["display_status"] == "converted")

    return {
        "total": total,
        "sem_contato": sem_contato,
        "replied": replied,
        "convertidos": convertidos,
        "items": items,
    }