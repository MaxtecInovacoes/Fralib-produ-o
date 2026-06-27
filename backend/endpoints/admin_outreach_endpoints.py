"""
Endpoints admin/outreach — campanha de reativação (Sprint 14.3).

Endpoints:
- GET  /api/admin/outreach/inativos              → lista candidatos
- POST /api/admin/outreach/disparar/{campaign}   → dispara (DRY_RUN por padrão)
- GET  /api/admin/outreach/dashboard/{campaign}  → métricas
- GET  /api/admin/outreach/respostas             → inbox de replies

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
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.access_control import require_superadmin
from backend.core.database import get_db
from backend.services.email_service import enviar_email_reativacao

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
    payload: DispararRequest = Depends(),
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Dispara email de reativação para todos os inativos.

    Idempotente: se outreach_attempts já tem (user_id, campaign, 'email'),
    pula. dry_run=true (default) só simula — não envia.
    """
    dry_run = payload.dry_run
    channel = "email"

    # Lista inativos (mesmo filtro do GET /inativos)
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

    for row in candidatos:
        user_id, email, nome, plano, creditos, criado_em = (
            int(row[0]), row[1], row[2], row[3], int(row[4] or 0), row[5]
        )
        dias = _dias_cadastrado(criado_em)

        # Verifica idempotência: outreach_attempts UNIQUE (user_id, campaign, channel)
        existing = db.execute(text("""
            SELECT id, status FROM outreach_attempts
            WHERE user_id = :uid AND campaign = :camp AND channel = :ch
        """), {"uid": user_id, "camp": campaign, "ch": channel}).fetchone()

        if existing:
            pulados += 1
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "skipped",
                "motivo": f"ja_enviado (status={existing[1]})",
            })
            continue

        if dry_run:
            detalhes.append({
                "user_id": user_id,
                "email": email,
                "acao": "would_send",
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
                "meta": '{"source": "admin_outreach_disparar"}',
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

        # Envia
        ok = await enviar_email_reativacao(
            email=email,
            nome=nome,
            dias_cadastrado=dias,
            plano=plano or "trial",
            creditos=creditos,
        )

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

    return {
        "campaign": campaign,
        "dry_run": dry_run,
        "total_candidatos": len(candidatos),
        "enviados": enviados,
        "pulados": pulados,
        "erros": erros,
        "detalhes": detalhes,
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