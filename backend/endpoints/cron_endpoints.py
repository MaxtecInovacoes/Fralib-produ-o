"""
Endpoints disparados por cron externo (crontab/PM2).

Autenticacao por header X-Cron-Secret == CRON_SECRET do .env.
Nunca expor sem secret - estes endpoints podem mandar emails em massa.
"""
import os
import random
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from backend.core.database import engine
from backend.services.email_service import enviar_email_resumo_diario
from backend.services.credits_manager import plano_tem_sdr
from backend.whatsapp.sender import send_text_parts

router = APIRouter(prefix='/api/cron', tags=['cron'])

CRON_SECRET = os.getenv('CRON_SECRET', '')

# Jitter humanizado entre envios do cron Franz (segundos).
# Faixa [min, max) com distribuicao uniforme — gera cadencia irregular
# (ex: 18s, 47s, 22s, 91s) em vez de rajada constante.
FRANZ_CRON_JITTER_MIN_S = 18
FRANZ_CRON_JITTER_MAX_S = 75

# Teto de leads despachados por ciclo de cron. Reduzido de 10 para 5
# para alinhar com a cadencia humanizada — 5 envios * ~46s medio =
# ~4 min de processamento/ciclo, sobra do ciclo de 30 min.
FRANZ_CRON_BATCH_LIMIT = 5


def _normalizar_phone(phone: str) -> str:
    import re as _re

    tel = _re.sub(r"\D", "", (phone or "").strip())
    if tel and not tel.startswith("55"):
        tel = "55" + tel
    return tel


def _send_sdr_direct(user_id: int, phone: str, message: str) -> tuple[bool, str]:
    """Envia follow-up/conversa ja iniciada direto, sem fila de primeiro contato."""
    import httpx

    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001").rstrip("/")
    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        return False, "MEOWHATS_KEY ausente"
    tel = _normalizar_phone(phone)
    if not tel:
        return False, "telefone ausente"
    tenant_key = f"fralib_user_{int(user_id)}"
    jid = f"{tel}@s.whatsapp.net"
    client = httpx.Client(timeout=15)
    try:
        return send_text_parts(client, meowhats_url, meowhats_key, tenant_key, jid, [message])
    finally:
        client.close()


def _autorizar(x_cron_secret: str):
    if not CRON_SECRET:
        raise HTTPException(500, 'CRON_SECRET nao configurado no .env')
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(403, 'Cron secret invalido')


@router.post('/email-resumo-diario')
async def email_resumo_diario(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Agrupa leads concluidos nas ultimas 24h por usuario e envia 1 email.
    Idempotencia simples: nao reenvia se a coluna ultimo_resumo_em foi atualizada hoje.
    """
    _autorizar(x_cron_secret)

    janela_inicio = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    hoje = datetime.utcnow().date().isoformat()
    enviados = 0
    pulados = 0
    erros = 0

    with engine.connect() as conn:
        # Garante a coluna de idempotencia (idempotente)
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ultimo_resumo_em TIMESTAMP"
        ))
        conn.commit()

        # Usuarios com pelo menos 1 lead concluido nas ultimas 24h
        rows = conn.execute(text("""
            SELECT u.id, u.email, u.nome, u.ultimo_resumo_em
            FROM users u
            WHERE EXISTS (
                SELECT 1 FROM leads l
                WHERE l.user_id = u.id
                  AND l.status = 'concluido'
                  AND l.processado_em >= :inicio
            )
        """), {'inicio': janela_inicio}).fetchall()

        for u in rows:
            uid, email, nome, ultimo = int(u[0]), u[1], u[2] or 'Cliente', u[3]
            # Pulou se ja enviou hoje
            if ultimo and str(ultimo)[:10] == hoje:
                pulados += 1
                continue
            leads_rows = conn.execute(text("""
                SELECT nome, COALESCE(site_url, url_site) AS site_url, cidade
                FROM leads
                WHERE user_id = :uid
                  AND status = 'concluido'
                  AND processado_em >= :inicio
                ORDER BY processado_em DESC
                LIMIT 50
            """), {'uid': uid, 'inicio': janela_inicio}).fetchall()
            leads = [{'nome': r[0], 'site_url': r[1], 'cidade': r[2]} for r in leads_rows]
            if not leads:
                continue
            try:
                ok = await enviar_email_resumo_diario(email, nome, leads)
                if ok:
                    enviados += 1
                    conn.execute(text(
                        "UPDATE users SET ultimo_resumo_em = NOW() WHERE id = :uid"
                    ), {'uid': uid})
                    conn.commit()
                else:
                    erros += 1
            except Exception as e:
                print(f'[Cron resumo] erro user {uid}: {e}')
                erros += 1

    return {'status': 'ok', 'enviados': enviados, 'pulados': pulados, 'erros': erros}


@router.post('/despachar-fila-franz')
async def despachar_fila_franz(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """
    Despacha leads com sdr_stage='pendente_wpp' (site pronto, fora do horário).
    Chamado a cada 30min pelo PM2/cron. Respeita horário de atendimento (8h-21h Brasília).
    """
    _autorizar(x_cron_secret)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
    from agents.sdr_langgraph import iniciar_contato, FranzInput, _escolher_variante
    from services.sdr_gateway import SdrMessageContext, evaluate_sdr_output, has_prior_outbound
    from backend.services.outbound_queue import enqueue_outbound
    from backend.whatsapp_listener import is_tenant_connected
    # === Sprint 1.2 — Bug #3: lock por lead para evitar que 2 ciclos
    # paralelos do cron processem o mesmo lead simultaneamente.
    # Mesmo padrão de ``responder_lead`` em whatsapp_listener.
    from backend.agents.sdr_langgraph.lead_lock import _lead_lock_guard

    enviados = 0
    erros = 0

    with engine.connect() as conn:
        # Buscar leads pendentes (site pronto mas não abordados)
        # USA FOR UPDATE SKIP LOCKED para evitar que múltiplas instâncias do cron
        # processem o mesmo lead simultaneamente
        rows = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.rating, l.user_id, l.paleta_cores,
                   u.plano, u.status, u.trial_expires_at
            FROM leads l
            JOIN users u ON u.id = l.user_id
            WHERE l.sdr_stage = 'pendente_wpp'
              AND l.status = 'concluido'
              AND l.site_url IS NOT NULL
              AND lower(COALESCE(u.plano, '')) IN ('trial','pro','beta','agency','ilimitado','admin')
              AND lower(COALESCE(u.status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')
            ORDER BY l.processado_em ASC
            LIMIT :batch_limit
            FOR UPDATE SKIP LOCKED
        """), {"batch_limit": FRANZ_CRON_BATCH_LIMIT}).fetchall()

        if not rows:
            return {'status': 'ok', 'mensagem': 'Nenhum lead na fila', 'enviados': 0}

        for row in rows:
            (
                lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, rating,
                user_id, paleta_cores, user_plano, user_status, user_trial_expires_at,
            ) = row
            try:
                if not plano_tem_sdr(user_plano, user_status, user_trial_expires_at):
                    continue
                franz_input = FranzInput(
                    nome=nome or "", cidade=cidade or "", segmento=segmento or "",
                    telefone=telefone or "", whatsapp=whatsapp or "",
                    rating=rating or 0.0, site_url=site_url or "",
                    score_caio=80, tier="STANDARD",
                    paleta_cores=paleta_cores or {},
                )
                if not user_id:
                    print(f"[Cron Franz] ⚠️ lead {lead_id} sem user_id — ignorado (multi-tenant)")
                    continue

                # === Sprint 1.2 — Bug #3: lock por lead antes de gerar/enviar ===
                # Se Redis offline, _lead_lock_guard lança RuntimeError (fail-closed).
                # Pular este lead (não bloquear o batch inteiro).
                try:
                    with _lead_lock_guard(str(lead_id)):
                        franz_output = iniciar_contato(franz_input, user_id=user_id)
                except RuntimeError as _lock_err:
                    print(f"[Cron Franz] 🔒 lock indisponível para lead {lead_id}: {_lock_err}")
                    continue
                except Exception as _lock_other_err:
                    print(f"[Cron Franz] ⚠️ erro no lock para lead {lead_id}: {_lock_other_err}")
                    continue

                if not franz_output.reply or not franz_output.reply.strip():
                    continue

                prior_outbound = has_prior_outbound(conn, lead_id, user_id)
                guard = evaluate_sdr_output(
                    SdrMessageContext(
                        tenant_id=user_id,
                        lead_id=lead_id,
                        lead_name=nome or "",
                        lead_segment=segmento or "",
                        stage="pendente_wpp",
                        next_stage=franz_output.next_stage or "",
                        message=franz_output.reply,
                        site_url=site_url or "",
                        prior_outbound=prior_outbound,
                        direction="outbound",
                        plan_allows_sdr=True,
                        whatsapp_connected=True,
                        within_schedule=True,
                        site_ready=bool(site_url),
                    )
                )
                if not guard.allowed:
                    erros += 1
                    print(f"[Cron Franz] 🛑 Guard bloqueou {nome}: {guard.code} - {guard.reason}")
                    continue

                # Primeiro contato nunca envia direto: entra na fila FIFO por tenant.
                tel = _normalizar_phone(whatsapp or telefone or "")
                if not tel:
                    erros += 1
                    print(f"[Cron Franz] ⚠️ Lead {nome}: telefone ausente — pulando")
                    continue

                msg_id = enqueue_outbound(
                    engine=engine,
                    tenant_id=user_id,
                    lead_id=str(lead_id),
                    phone=tel,
                    message=franz_output.reply,
                    source="franz",
                    priority=10,
                )
                # Se msg_id eh None, a mensagem ja foi enviada anteriormente - pular
                if msg_id is None:
                    erros += 1
                    print(f"[Cron Franz] ⚠️ Lead {nome}: mensagem ja enviada anteriormente — pulando")
                    continue
                conn.execute(text(
                    "UPDATE leads SET sdr_stage='pending_sdr_send', ab_variant=:var, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                ), {"id": lead_id, "var": _escolher_variante(lead_id), "uid": user_id})
                conn.commit()
                enviados += 1
                print(f"[Cron Franz] ✅ Enfileirado para {nome} ({tel[-4:]})")

                # Jitter humanizado entre envios (so apos sucesso, so se sobrou lead)
                if enviados < len(rows):
                    delay = random.uniform(FRANZ_CRON_JITTER_MIN_S, FRANZ_CRON_JITTER_MAX_S)
                    print(f"[Cron Franz] ⏳ aguardando {delay:.1f}s antes do proximo envio")
                    time.sleep(delay)
            except Exception as e:
                erros += 1
                print(f"[Cron Franz] ❌ Erro {nome}: {e}")

    return {'status': 'ok', 'enviados': enviados, 'erros': erros, 'total_fila': len(rows)}


@router.post('/followup-franz')
async def followup_franz(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """
    Envia follow-up para leads sem resposta.

    INTERVALOS CONFIGURADOS (em horas):
    - 24h sem resposta após intro → follow-up 1
    - 72h sem resposta após FU1 → follow-up 2
    - 24h sem resposta após FU2 → marca como lost

    Chamado a cada 1h pelo PM2/cron, mas só envia se passou o intervalo.
    """
    _autorizar(x_cron_secret)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
    from agents.sdr_langgraph import followup_automatico, _dentro_do_horario
    from services.sdr_gateway import SdrMessageContext, evaluate_sdr_output, has_prior_outbound
    from backend.whatsapp_listener import is_tenant_connected, _salvar_interacao

    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        return {'status': 'erro_config', 'mensagem': 'MEOWHATS_KEY ausente', 'enviados': 0}

    enviados = 0
    perdidos = 0
    erros = 0

    with engine.connect() as conn:
        # ============================================================
        # FOLLOW-UP 1: leads com 24h+ sem resposta após intro
        # USA FOR UPDATE SKIP LOCKED para evitar duplicação entre instâncias do cron
        # ============================================================
        rows_fu1 = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.sdr_stage, l.user_id, l.atualizado_em
            FROM leads l
            JOIN users u ON u.id = l.user_id
            WHERE l.status = 'concluido'
              AND lower(COALESCE(u.plano, '')) IN ('pro','agency','ilimitado','admin')
              AND lower(COALESCE(u.status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')
              AND l.sdr_stage IN (
                  'hook', 'qualify', 'intro',
                  'pain', 'amplify', 'followup1', 'f1',
                  'tease', 'proof', 'reveal', 'feedback', 'followup2', 'f2',
                  'negotiation', 'negociacao'
              )
              AND l.atualizado_em < :limite_24h
              AND EXISTS (
                  SELECT 1 FROM interacoes i
                  WHERE i.lead_id = l.id
                    AND i.user_id = l.user_id
                    AND i.direcao = 'saida'
              )
            ORDER BY l.atualizado_em ASC
            LIMIT 15
            FOR UPDATE SKIP LOCKED
        """), {"limite_24h": (datetime.utcnow() - timedelta(hours=24)).isoformat()}).fetchall()

        # ============================================================
        # FOLLOW-UP 2: leads com 72h+ sem resposta após FU1
        # USA FOR UPDATE SKIP LOCKED
        # ============================================================
        rows_fu2 = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.sdr_stage, l.user_id, l.atualizado_em
            FROM leads l
            JOIN users u ON u.id = l.user_id
            WHERE l.status = 'concluido'
              AND lower(COALESCE(u.plano, '')) IN ('pro','agency','ilimitado','admin')
              AND lower(COALESCE(u.status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')
              AND l.sdr_stage = 'followup_24h'
              AND l.atualizado_em < :limite_72h
            ORDER BY l.atualizado_em ASC
            LIMIT 15
            FOR UPDATE SKIP LOCKED
        """), {"limite_72h": (datetime.utcnow() - timedelta(hours=72)).isoformat()}).fetchall()

        # ============================================================
        # LOST: leads com 24h+ sem resposta após FU2
        # USA FOR UPDATE SKIP LOCKED
        # ============================================================
        rows_lost = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.sdr_stage, l.user_id, l.atualizado_em
            FROM leads l
            JOIN users u ON u.id = l.user_id
            WHERE l.status = 'concluido'
              AND lower(COALESCE(u.plano, '')) IN ('pro','agency','ilimitado','admin')
              AND lower(COALESCE(u.status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')
              AND l.sdr_stage = 'followup_72h'
              AND l.atualizado_em < :limite_24h_lost
            ORDER BY l.atualizado_em ASC
            LIMIT 15
            FOR UPDATE SKIP LOCKED
        """), {"limite_24h_lost": (datetime.utcnow() - timedelta(hours=24)).isoformat()}).fetchall()

        # Combinar FU1 e FU2 (lost é tratado separado)
        rows = list(rows_fu1) + list(rows_fu2)

        # Also fetch scheduled leads whose followup_date has arrived
        # USA FOR UPDATE SKIP LOCKED
        scheduled_rows = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.sdr_stage, l.user_id, l.atualizado_em
            FROM leads l
            JOIN users u ON u.id = l.user_id
            WHERE l.status = 'concluido'
              AND lower(COALESCE(u.plano, '')) IN ('pro','agency','ilimitado','admin')
              AND lower(COALESCE(u.status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')
              AND l.sdr_stage = 'scheduled'
              AND l.followup_date IS NOT NULL
              AND l.followup_date <= :hoje
            ORDER BY l.followup_date ASC
            LIMIT 10
            FOR UPDATE SKIP LOCKED
        """), {"hoje": datetime.utcnow().strftime('%Y-%m-%d')}).fetchall()

        if not rows and not rows_lost and not scheduled_rows:
            return {'status': 'ok', 'mensagem': 'Nenhum lead para follow-up', 'enviados': 0}

        # ============================================================
        # LOST: marcar leads sem resposta após 24h do FU2
        # ============================================================
        for row in rows_lost:
            lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, sdr_stage, user_id, atualizado_em = row
            if not user_id:
                print(f"[Cron FU] ⚠️ lead {lead_id} sem user_id — pulando lost")
                continue
            conn.execute(text(
                "UPDATE leads SET sdr_stage='lost', atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
            ), {"id": lead_id, "uid": user_id})
            conn.commit()
            perdidos += 1
            print(f"[Cron FU] 💀 {nome} marcado como lost (sem resposta)")

        for row in rows:
            lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, sdr_stage, user_id, atualizado_em = row
            try:
                # Determinar tipo de follow-up
                if sdr_stage in (
                    'hook', 'qualify', 'intro',
                    'pain', 'amplify', 'followup1', 'f1',
                    'tease', 'proof', 'reveal', 'feedback', 'followup2', 'f2',
                    'negotiation', 'negociacao',
                ):
                    tipo = "24h"
                    novo_stage = "followup_24h"
                elif sdr_stage == 'followup_24h':
                    tipo = "72h"
                    novo_stage = "followup_72h"
                elif sdr_stage == 'followup_72h':
                    # Marcar como perdido (escopo ao tenant)
                    if not user_id:
                        print(f"[Cron FU] ⚠️ lead {lead_id} sem user_id — pulando lost")
                        continue
                    conn.execute(text(
                        "UPDATE leads SET sdr_stage='lost', atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                    ), {"id": lead_id, "uid": user_id})
                    conn.commit()
                    perdidos += 1
                    print(f"[Cron FU] 💀 {nome} marcado como lost (sem resposta)")
                    continue
                else:
                    continue

                if not user_id:
                    print(f"[Cron FU] ⚠️ lead {lead_id} sem user_id — pulando")
                    continue
                tel = _normalizar_phone(whatsapp or telefone or "")
                wpp_tenant = f"fralib_user_{user_id}"
                if not tel:
                    erros += 1
                    print(f"[Cron FU] ⚠️ lead {lead_id}: telefone ausente — pulando")
                    continue

                if not _dentro_do_horario(user_id):
                    print(f"[Cron FU] ⏰ lead {lead_id}: fora do horario do tenant {user_id} — aguardando janela")
                    continue
                if not is_tenant_connected(wpp_tenant):
                    print(f"[Cron Franz] ⏸ Follow-up lead {lead_id}: tenant {wpp_tenant} sem WhatsApp conectado — pulando")
                    continue

                fu_output = followup_automatico(telefone or whatsapp or "", tipo, user_id=user_id)

                if not fu_output.reply or not fu_output.reply.strip():
                    continue

                prior_outbound = has_prior_outbound(conn, lead_id, user_id)
                guard = evaluate_sdr_output(
                    SdrMessageContext(
                        tenant_id=user_id,
                        lead_id=lead_id,
                        lead_name=nome or "",
                        lead_segment=segmento or "",
                        stage=sdr_stage or "",
                        next_stage=fu_output.next_stage or novo_stage,
                        message=fu_output.reply,
                        site_url=site_url or "",
                        prior_outbound=prior_outbound,
                        direction="followup",
                        plan_allows_sdr=True,
                        whatsapp_connected=True,
                        within_schedule=True,
                        site_ready=bool(site_url),
                    )
                )
                if not guard.allowed:
                    erros += 1
                    print(f"[Cron FU] 🛑 Guard bloqueou {nome}: {guard.code} - {guard.reason}")
                    continue

                ok, err = _send_sdr_direct(user_id, tel, fu_output.reply)
                if not ok:
                    erros += 1
                    print(f"[Cron FU] ❌ Falha envio direto {nome}: {err}")
                    continue
                _salvar_interacao(lead_id, fu_output.reply, "saida", user_id)
                conn.execute(text(
                    "UPDATE leads SET sdr_stage=:stage, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                ), {"id": lead_id, "stage": novo_stage, "uid": user_id})
                conn.commit()
                enviados += 1
                print(f"[Cron FU] ✅ Enviado direto '{tipo}' para {nome}")
            except Exception as e:
                erros += 1
                print(f"[Cron FU] ❌ Erro {nome}: {e}")

        # Processar leads agendados (scheduled) cuja data chegou
        for row in scheduled_rows:
            lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, sdr_stage, user_id, atualizado_em = row
            try:
                if not user_id:
                    print(f"[Cron FU] ⚠️ lead {lead_id} sem user_id — pulando scheduled")
                    continue
                tel = _normalizar_phone(whatsapp or telefone or "")
                wpp_tenant = f"fralib_user_{user_id}"
                if not tel:
                    erros += 1
                    print(f"[Cron FU] ⚠️ scheduled lead {lead_id}: telefone ausente — pulando")
                    continue

                if not _dentro_do_horario(user_id):
                    print(f"[Cron FU] ⏰ Agendado lead {lead_id}: fora do horario do tenant {user_id} — aguardando janela")
                    continue
                if not is_tenant_connected(wpp_tenant):
                    print(f"[Cron FU] ⏸ Agendado lead {lead_id}: tenant {wpp_tenant} sem WhatsApp conectado — pulando")
                    continue

                fu_output = followup_automatico(telefone or whatsapp or "", "scheduled", user_id=user_id)

                if not fu_output.reply or not fu_output.reply.strip():
                    continue

                prior_outbound = has_prior_outbound(conn, lead_id, user_id)
                guard = evaluate_sdr_output(
                    SdrMessageContext(
                        tenant_id=user_id,
                        lead_id=lead_id,
                        lead_name=nome or "",
                        lead_segment=segmento or "",
                        stage=sdr_stage or "",
                        next_stage=fu_output.next_stage or "pain",
                        message=fu_output.reply,
                        site_url=site_url or "",
                        prior_outbound=prior_outbound,
                        direction="followup",
                        plan_allows_sdr=True,
                        whatsapp_connected=True,
                        within_schedule=True,
                        site_ready=bool(site_url),
                    )
                )
                if not guard.allowed:
                    erros += 1
                    print(f"[Cron FU] 🛑 Guard bloqueou scheduled {nome}: {guard.code} - {guard.reason}")
                    continue

                ok, err = _send_sdr_direct(user_id, tel, fu_output.reply)
                if not ok:
                    erros += 1
                    print(f"[Cron FU] ❌ Falha envio direto scheduled {nome}: {err}")
                    continue
                _salvar_interacao(lead_id, fu_output.reply, "saida", user_id)
                # Volta pro stage anterior ao scheduled (discovery ou qualify)
                conn.execute(text(
                    "UPDATE leads SET sdr_stage='pain', followup_date=NULL, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                ), {"id": lead_id, "uid": user_id})
                conn.commit()
                enviados += 1
                print(f"[Cron FU] 📅 Enviado direto retomado: {nome}")
            except Exception as e:
                erros += 1
                print(f"[Cron FU] ❌ Erro scheduled {nome}: {e}")

    return {'status': 'ok', 'enviados': enviados, 'perdidos': perdidos, 'erros': erros, 'total': len(rows) + len(scheduled_rows)}


@router.post('/reengajar-leads')
async def reengajar_leads(
    x_cron_secret: str = Header(None, alias='X-Cron-Secret'),
    days_idle: int = 7,
):
    """Re-engaja leads abandonados (pararam de responder 7+ dias)."""
    _autorizar(x_cron_secret)

    try:
        from backend.services.ab_testing import (
            find_abandoned_leads,
            generate_reengagement_message,
            should_reengange,
        )
    except Exception as e:
        return {'status': 'error', 'message': f'ab_testing nao disponivel: {e}'}

    total_enviados = 0
    total_pulados = 0
    total_erros = 0
    detalhes = []

    with engine.connect() as conn:
        tenants = conn.execute(text("""
            SELECT id FROM users
            WHERE LOWER(COALESCE(plano, '')) IN ('trial','pro','beta','agency','ilimitado','admin')
              AND LOWER(COALESCE(status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')
        """)).fetchall()

        for (user_id,) in tenants:
            try:
                abandoned = find_abandoned_leads(user_id=user_id, days_idle=days_idle)
                for lead in abandoned:
                    if not should_reengange(lead["days_idle"]):
                        total_pulados += 1
                        continue

                    msg = generate_reengagement_message(lead)
                    detalhes.append({
                        "lead_id": lead["lead_id"],
                        "nome": lead["nome"],
                        "telefone": lead["telefone"],
                        "days_idle": lead["days_idle"],
                        "msg_preview": msg[:100],
                    })
                    total_enviados += 1
            except Exception as e:
                total_erros += 1

    return {
        'status': 'ok',
        'enviados': total_enviados,
        'pulados': total_pulados,
        'erros': total_erros,
        'detalhes': detalhes[:10],
    }


@router.get('/variant-report')
async def variant_report(
    x_cron_secret: str = Header(None, alias='X-Cron-Secret'),
    user_id: int = 1,
):
    """Retorna relatorio de A/B testing das variants."""
    _autorizar(x_cron_secret)
    try:
        from backend.services.ab_testing import get_variant_report
        return get_variant_report(user_id)
    except Exception as e:
        return {'error': str(e)}


@router.post('/processar-fila-outbound')
async def processar_fila_outbound(
    x_cron_secret: str = Header(None, alias='X-Cron-Secret'),
):
    """Processa 1 ciclo da fila outbound com rate limit.

    Cron: rodar a cada 1-2 minutos.
    Respeita o limite da fila por tenant.
    """
    _autorizar(x_cron_secret)

    try:
        from backend.services.outbound_queue import process_queue_once
        from agents.sdr_langgraph import _dentro_do_horario
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

    def sync_sender(phone: str, message: str, tenant_id: int | None = None):
        """Envia msg via WhatsApp do tenant; None reprograma sem falhar."""
        import requests

        if not tenant_id:
            return False
        if not _dentro_do_horario(int(tenant_id)):
            return None
        meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001").rstrip("/")
        meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
        if not meowhats_key:
            return None
        tenant_key = f"fralib_user_{int(tenant_id)}"
        try:
            status = requests.get(
                f"{meowhats_url}/api/sessions/{tenant_key}/status",
                headers={"X-API-Key": meowhats_key},
                timeout=8,
            )
            if status.status_code != 200 or "connected" not in status.text.lower():
                return None
            tel = _normalizar_phone(phone)
            if not tel:
                return False
            r = requests.post(
                f"{meowhats_url}/api/sessions/{tenant_key}/send",
                headers={"X-API-Key": meowhats_key},
                json={"jid": f"{tel}@s.whatsapp.net", "type": "text", "text": message},
                timeout=15,
            )
            return r.status_code == 200
        except Exception:
            return False

    result = process_queue_once(engine, sync_sender)
    return result


@router.get('/queue-stats')
async def queue_stats(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Retorna estatísticas da fila outbound para monitoramento.

    Inclui contadores, alertas e métricas de backlog.
    Use para Grafana/Prometheus ou dashboards de ops.
    """
    _autorizar(x_cron_secret)

    try:
        from backend.services.outbound_queue import get_queue_stats
        stats = get_queue_stats(engine)

        # Log de alerta se necessário
        if stats.get("backlog_alert"):
            print(f"[Queue Stats] ⚠️ ALERTA: backlog crescente ({stats['total_pending']} pending)")
        if stats.get("dlq_alert"):
            print(f"[Queue Stats] 🔴 ALERTA: DLQ com {stats['total_dlq']} mensagens")

        return {
            "status": "ok",
            "pending": stats["total_pending"],
            "failed": stats["total_failed"],
            "dlq": stats["total_dlq"],
            "sent_today": stats["total_sent_today"],
            "oldest_pending_minutes": stats.get("oldest_pending_minutes"),
            "alerts": {
                "backlog": stats.get("backlog_alert", False),
                "dlq": stats.get("dlq_alert", False),
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# Health Check: Redis + Sistema
# ============================================================

@router.get('/health')
async def health_check(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Health check completo do sistema SDR.

    Verifica:
    - Redis (lock distribuido)
    - Banco de dados
    - Meowhats (conectividade)

    Use para cron de monitoramento /healthz.
    """
    _autorizar(x_cron_secret)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "redis": None,
        "database": None,
        "meowhats": None,
    }

    # Redis health check
    try:
        from backend.agents.sdr_langgraph.lead_lock import (
            is_redis_available,
            get_redis_status,
            force_redis_reconnect,
        )
        redis_status = get_redis_status()
        if not redis_status.get("available"):
            # Tenta recovery automático
            recovered = force_redis_reconnect()
            redis_status = get_redis_status()
            redis_status["auto_recovery_attempted"] = True
            redis_status["recovered"] = recovered
        result["redis"] = redis_status
    except Exception as e:
        result["redis"] = {"available": False, "error": str(e)}

    # Database health check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["database"] = {"available": True}
    except Exception as e:
        result["database"] = {"available": False, "error": str(e)}

    # Meowhats health check
    try:
        meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        import httpx
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{meowhats_url}/health")
            result["meowhats"] = {"available": r.status_code == 200, "status_code": r.status_code}
    except Exception as e:
        result["meowhats"] = {"available": False, "error": str(e)}

    # Status geral
    all_healthy = (
        result["redis"] and result["redis"].get("available", False) and
        result["database"] and result["database"].get("available", False)
    )
    result["status"] = "healthy" if all_healthy else "degraded"

    # Log se não está saudável
    if not all_healthy:
        print(f"[Health] ⚠️ Sistema em modo DEGRADADO: {result}")

    return result


@router.post('/redis-reconnect')
async def redis_reconnect(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Força tentativa de reconexão ao Redis.

    Útil para recovery manual via cron quando auto-recovery falha.
    """
    _autorizar(x_cron_secret)

    try:
        from backend.agents.sdr_langgraph.lead_lock import (
            force_redis_reconnect,
            get_redis_status,
        )
        recovered = force_redis_reconnect()
        status = get_redis_status()
        return {
            "status": "ok",
            "reconnected": recovered,
            "redis_status": status,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post('/compute-phone-health-score')
async def compute_phone_health_score(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Recalcula phone_health_score para todos os tenants ativos.

    Idempotente — UPSERT em phone_health_score.
    Rodar 1x/hora via cron externo (X-Cron-Secret).
    """
    _autorizar(x_cron_secret)

    from backend.services.phone_health_service import compute_all_tenants

    try:
        snapshots = compute_all_tenants(engine)
    except Exception as e:
        logger.exception("compute_phone_health_score falhou")
        return {"status": "error", "message": str(e)}

    by_status: dict[str, int] = {}
    for snap in snapshots:
        by_status[snap.status] = by_status.get(snap.status, 0) + 1

    return {
        "status": "ok",
        "tenants_processed": len(snapshots),
        "by_status": by_status,
        "snapshot_at": datetime.utcnow().isoformat(),
    }


@router.post('/refresh-provider-health')
async def refresh_provider_health(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Faz ping em cada provider conhecido e UPSERT em provider_health.

    Idempotente — roda 1x a cada 5min via cron externo.
    Cron sugerido: ``*/5 * * * * curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \\
        https://api.fralib.com/api/cron/refresh-provider-health``
    """
    _autorizar(x_cron_secret)

    from backend.services.provider_health_service import refresh_all_providers

    try:
        summary = refresh_all_providers(engine)
    except Exception as e:
        logger.exception("refresh_provider_health falhou")
        return {"status": "error", "message": str(e)}

    return {
        "status": "ok",
        "providers_refreshed": summary["providers_refreshed"],
        "errors": summary["errors"],
        "by_status": summary["by_status"],
        "snapshot_at": datetime.utcnow().isoformat(),
    }


# ── Sprint 0.3 — Custos ─────────────────────────────────────────────────


@router.post('/refresh-facebook-ads-spend')
async def refresh_facebook_ads_spend(
    days: int = 1,
    x_cron_secret: str = Header(None, alias='X-Cron-Secret'),
) -> dict:
    """Busca spend FB Ads do(s) último(s) N dia(s) e grava cost_events.

    Lê credenciais de env (FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID). Sem credenciais,
    retorna 200 com status='skipped' e mensagem clara.

    Cron sugerido: ``0 1 * * * curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \\
        https://api.fralib.com/api/cron/refresh-facebook-ads-spend``
    """
    _autorizar(x_cron_secret)

    token = os.getenv("FB_ACCESS_TOKEN", "").strip()
    account_id = os.getenv("FB_AD_ACCOUNT_ID", "").strip()
    if not token or not account_id:
        return {
            "status": "skipped",
            "reason": "FB_ACCESS_TOKEN ou FB_AD_ACCOUNT_ID ausentes",
        }

    try:
        from backend.services.facebook_ads_service import (
            FacebookAdsConfigError,
            FacebookAdsService,
        )
        from backend.agents.cost_tracker import record_cost_event
    except Exception as e:
        logger.exception("imports falharam em refresh_facebook_ads_spend")
        return {"status": "error", "reason": f"imports: {e!s}"}

    persisted = 0
    skipped = 0
    errors = 0
    try:
        service = FacebookAdsService(
            access_token=token, ad_account_id=account_id
        )
        insights = await service.get_overall_insights(days=days)
    except FacebookAdsConfigError as fc:
        return {"status": "skipped", "reason": str(fc)}
    except Exception as exc:
        logger.exception("get_overall_insights falhou")
        return {"status": "error", "reason": f"fb_api: {exc!s}"}

    total_spend_cents = int(insights.get("total_spend", 0) or 0)
    spend_brl = total_spend_cents / 100.0
    # FB Ads cobra em BRL (currency BRL por default)
    spend_usd = 0.0
    days_period = int(insights.get("period_days", days) or days)

    if spend_brl > 0:
        ok = record_cost_event(
            provider="facebook_ads",
            service="refresh_spend",
            units=int(insights.get("total_eventos", 1) or 1),
            custo_usd=spend_usd,
            custo_brl=spend_brl,
            status="success",
            metadata={
                "days": days_period,
                "total_impressions": int(
                    insights.get("total_impressions", 0) or 0
                ),
                "total_clicks": int(insights.get("total_clicks", 0) or 0),
                "total_leads": int(insights.get("total_leads", 0) or 0),
                "campaigns_count": len(insights.get("campaigns", []) or []),
            },
        )
        persisted = 1 if ok else 0
        if not ok:
            errors += 1
    else:
        skipped += 1

    return {
        "status": "ok" if errors == 0 else "partial",
        "provider": "facebook_ads",
        "days": days_period,
        "spend_brl": spend_brl,
        "persisted": persisted,
        "skipped": skipped,
        "errors": errors,
        "snapshot_at": datetime.utcnow().isoformat(),
    }


@router.post('/refresh-usd-brl-rate')
async def refresh_usd_brl_rate(
    x_cron_secret: str = Header(None, alias='X-Cron-Secret'),
) -> dict:
    """Atualiza cotação USD/BRL via API pública e grava 1 cost_event.

    Cron sugerido: ``0 8 * * * curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \\
        https://api.fralib.com/api/cron/refresh-usd-brl-rate``
    """
    _autorizar(x_cron_secret)
    try:
        from backend.services.currency_service import refresh_usd_brl_rate as _fn
    except Exception as exc:
        logger.exception("imports falharam em refresh_usd_brl_rate")
        return {"status": "error", "reason": f"imports: {exc!s}"}

    try:
        result = _fn(engine)
        return {"status": "ok", **result}
    except Exception as exc:
        logger.exception("refresh_usd_brl_rate falhou")
        return {"status": "error", "reason": str(exc)}
