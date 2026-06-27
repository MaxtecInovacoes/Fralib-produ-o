"""
Cron endpoint: drip campaign diario (Sprint 14.4).

Roda 1x/dia via crontab. Para cada user em drip:
1. Verifica se respondeu/converteu -> marca status e pula
2. Se step N ja enviado e passaram >= 3 dias E step N+1 nao enviado -> envia N+1
3. Se step 5 ja enviado -> marca status='completed' e nao faz mais nada

Auth: X-Cron-Secret (mesmo padrao de cron_endpoints.py).
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from backend.core.database import engine
from backend.services.email_service import (
    enviar_email_reativacao_step2,
    enviar_email_reativacao_step3,
    enviar_email_reativacao_step4,
    enviar_email_reativacao_step5,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cron/outreach", tags=["cron-outreach"])

CRON_SECRET = os.getenv("CRON_SECRET", "")
DRIP_CAMPAIGN = "reativacao_drip_v1_2026_06_26"
DRIP_STEP_INTERVAL_DAYS = 3
DRIP_MAX_STEP = 5
DRIP_BATCH_LIMIT = 50

# Jitter humanizado entre envios (mesmo padrao de cron_endpoints.py)
DRIP_JITTER_MIN_S = 18
DRIP_JITTER_MAX_S = 75


def _autorizar(x_cron_secret: str | None) -> None:
    if not CRON_SECRET:
        raise HTTPException(500, "CRON_SECRET nao configurado no .env")
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(403, "Cron secret invalido")


def _step_email_func(step: int):
    """Mapeia step -> funcao de envio."""
    return {
        2: enviar_email_reativacao_step2,
        3: enviar_email_reativacao_step3,
        4: enviar_email_reativacao_step4,
        5: enviar_email_reativacao_step5,
    }.get(step)


@router.post("/drip-diario")
async def drip_diario(x_cron_secret: str | None = Header(None, alias="X-Cron-Secret")):
    """Processa proximos steps do drip. Roda 1x/dia."""
    _autorizar(x_cron_secret)

    enviados = 0
    pulados_replied = 0
    pulados_convertidos = 0
    completed = 0
    waiting = 0
    erros = 0
    novos_incluidos = 0

    agora = datetime.utcnow()
    limite_proximo_step = agora - timedelta(days=DRIP_STEP_INTERVAL_DAYS)
    limite_novo_inativo = agora - timedelta(days=7)  # user precisa ter 7+ dias para entrar

    with engine.connect() as conn:
        # 1. AUTO-INCLUSAO: pegar users novos que ja tem 7+ dias e nunca entraram no drip
        # Esses serao marcados como "step 0" (ainda nao receberam nada)
        # O step 1 sera disparado quando o admin acionar (ou pode auto-disparar via env var)
        novos = conn.execute(text("""
            SELECT u.id
            FROM users u
            WHERE u.email_confirmado = true
              AND u.status NOT IN ('blocked', 'suspended', 'deleted', 'inativo')
              AND u.email NOT LIKE 'test.%@test.com'
              AND u.email NOT LIKE 'pipeline.%@test.com'
              AND u.email NOT LIKE 'smoke.%@test.com'
              AND COALESCE(u.sites_used, 0) = 0
              AND COALESCE(u.tokens_used_month, 0) = 0
              AND COALESCE(u.sdr_messages_today, 0) = 0
              AND u.criado_em::timestamp < :limite
              AND NOT EXISTS (
                  SELECT 1 FROM outreach_attempts oa
                  WHERE oa.user_id = u.id AND oa.campaign = :camp
              )
            LIMIT :lim
        """), {"limite": limite_novo_inativo.isoformat(),
               "camp": DRIP_CAMPAIGN, "lim": 50}).fetchall()

        for (new_uid,) in novos:
            try:
                conn.execute(text("""
                    INSERT INTO outreach_attempts
                        (user_id, campaign, channel, status, metadata)
                    VALUES
                        (:uid, :camp, 'email', 'pending',
                         CAST('{"step": 0, "source": "auto_drip_diario"}' AS JSONB))
                """), {"uid": new_uid, "camp": DRIP_CAMPAIGN})
                conn.commit()
                novos_incluidos += 1
                logger.info(f"[Drip] novo inativo incluido: user {new_uid}")
            except Exception as e:
                # UNIQUE violation = race, ok
                conn.rollback()

        # 2. PROCESSAR: todos os users que ja estao no drip
        # Busca todos os users que tem ALGUM outreach nesta campanha,
        # exceto os que ja chegaram ao step 5 E foram enviados.
        # Para cada user, identificar:
        # - ultimo step enviado
        # - status (replied/converted se aplicavel)
        rows = conn.execute(text("""
            WITH user_drip AS (
                SELECT
                    oa.user_id,
                    MAX((oa.metadata->>'step')::int) AS max_step,
                    MAX(oa.sent_at) FILTER (WHERE oa.status = 'sent') AS ultimo_sent_at,
                    BOOL_OR(oa.replied_at IS NOT NULL) AS ja_respondeu,
                    MAX(oa.status) FILTER (WHERE oa.status IN ('replied', 'converted', 'completed')) AS status_final
                FROM outreach_attempts oa
                WHERE oa.campaign = :camp AND oa.channel = 'email'
                GROUP BY oa.user_id
            )
            SELECT
                ud.user_id,
                u.email,
                COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome,
                u.plano,
                u.creditos,
                ud.max_step,
                ud.ultimo_sent_at,
                ud.ja_respondeu,
                ud.status_final,
                COALESCE(u.sites_used, 0) AS sites_used,
                COALESCE(u.tokens_used_month, 0) AS tokens_month
            FROM user_drip ud
            JOIN users u ON u.id = ud.user_id
            ORDER BY ud.user_id
            LIMIT :lim
        """), {"camp": DRIP_CAMPAIGN, "lim": DRIP_BATCH_LIMIT}).fetchall()

        for row in rows:
            (user_id, email, nome, plano, creditos, max_step, ultimo_sent_at,
             ja_respondeu, status_final, sites_used, tokens_month) = row

            try:
                # Se ja converteu (gerou site OU consumiu tokens)
                if sites_used > 0 or tokens_month > 0:
                    if status_final != 'converted':
                        conn.execute(text("""
                            UPDATE outreach_attempts
                            SET status = 'converted', atualizado_em = NOW()
                            WHERE user_id = :uid AND campaign = :camp
                        """), {"uid": user_id, "camp": DRIP_CAMPAIGN})
                        conn.commit()
                        pulados_convertidos += 1
                    else:
                        pulados_convertidos += 1
                    continue

                # Se ja respondeu (manualmente marcado ou webhook)
                if ja_respondeu:
                    if status_final != 'replied':
                        conn.execute(text("""
                            UPDATE outreach_attempts
                            SET status = 'replied', atualizado_em = NOW()
                            WHERE user_id = :uid AND campaign = :camp AND status = 'sent'
                        """), {"uid": user_id, "camp": DRIP_CAMPAIGN})
                        conn.commit()
                        pulados_replied += 1
                    else:
                        pulados_replied += 1
                    continue

                # Se ja chegou ao step maximo
                if max_step and max_step >= DRIP_MAX_STEP:
                    if status_final != 'completed':
                        conn.execute(text("""
                            UPDATE outreach_attempts
                            SET status = 'completed', atualizado_em = NOW()
                            WHERE user_id = :uid AND campaign = :camp AND status = 'sent'
                        """), {"uid": user_id, "camp": DRIP_CAMPAIGN})
                        conn.commit()
                        completed += 1
                    else:
                        completed += 1
                    continue

                # Se ainda nao passou o intervalo, espera
                # Fix: comparar naive vs aware - normalizar para naive UTC
                if ultimo_sent_at:
                    sent_naive = ultimo_sent_at.replace(tzinfo=None) if ultimo_sent_at.tzinfo else ultimo_sent_at
                    if sent_naive > limite_proximo_step:
                        waiting += 1
                        continue

                # Identifica proximo step
                proximo_step = (max_step or 0) + 1
                if proximo_step > DRIP_MAX_STEP:
                    continue

                # Verifica se ja existe outreach para esse step (seguranca)
                existe = conn.execute(text("""
                    SELECT 1 FROM outreach_attempts
                    WHERE user_id = :uid AND campaign = :camp
                      AND metadata->>'step' = :step
                """), {"uid": user_id, "camp": DRIP_CAMPAIGN, "step": str(proximo_step)}).fetchone()

                if existe:
                    # Ja enviado, so atualiza max_step se necessario
                    waiting += 1
                    continue

                # Envia
                func = _step_email_func(proximo_step)
                if not func:
                    continue

                # step 5 recebe plano + creditos para personalizar
                if proximo_step == 5:
                    ok = await func(email, nome, plano=plano or 'trial', creditos=int(creditos or 0))
                else:
                    ok = await func(email, nome)

                if ok:
                    # Insere row para este step
                    try:
                        conn.execute(text("""
                            INSERT INTO outreach_attempts
                                (user_id, campaign, channel, status, sent_at, metadata)
                            VALUES
                                (:uid, :camp, 'email', 'sent', NOW(),
                                 CAST(:meta AS JSONB))
                        """), {
                            "uid": user_id,
                            "camp": DRIP_CAMPAIGN,
                            "meta": f'{{"step": {proximo_step}, "source": "drip_diario"}}',
                        })
                        conn.commit()
                        enviados += 1
                        logger.info(f"[Drip] step {proximo_step} enviado para user {user_id} ({email})")
                    except Exception as e:
                        # UNIQUE violation = duplicata (race)
                        conn.rollback()
                        waiting += 1
                else:
                    erros += 1
                    logger.error(f"[Drip] step {proximo_step} falhou para user {user_id}")

                # Jitter entre envios
                sleep_s = random.uniform(DRIP_JITTER_MIN_S, DRIP_JITTER_MAX_S)
                await asyncio.sleep(sleep_s)

            except Exception as e:
                erros += 1
                logger.error(f"[Drip] erro user {user_id}: {e}")

    return {
        "status": "ok",
        "campaign": DRIP_CAMPAIGN,
        "novos_incluidos": novos_incluidos,
        "enviados": enviados,
        "pulados_replied": pulados_replied,
        "pulados_convertidos": pulados_convertidos,
        "completed": completed,
        "waiting": waiting,
        "erros": erros,
    }