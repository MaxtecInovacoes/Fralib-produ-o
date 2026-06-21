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
from backend.whatsapp_listener import is_tenant_connected, _salvar_interacao

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


@router.post('/despachar-fila-bryan')
@router.post('/despachar-fila-franz')
async def despachar_fila_franz(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """
    Despacha leads com sdr_stage='pendente_wpp' (site pronto, fora do horário).
    Chamado a cada 30min pelo PM2/cron. Respeita horário de atendimento (8h-21h Brasília).
    """
    _autorizar(x_cron_secret)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
    from agents.sdr_langgraph import iniciar_contato, FranzInput, _dentro_do_horario, _escolher_variante
    from services.sdr_gateway import SdrMessageContext, evaluate_sdr_output, has_prior_outbound

    import httpx, re as _re
    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        return {'status': 'erro_config', 'mensagem': 'MEOWHATS_KEY ausente', 'enviados': 0}

    enviados = 0
    erros = 0

    with engine.connect() as conn:
        # Buscar leads pendentes (site pronto mas não abordados)
        rows = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.rating, l.user_id,
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
        """), {"batch_limit": FRANZ_CRON_BATCH_LIMIT}).fetchall()

        if not rows:
            return {'status': 'ok', 'mensagem': 'Nenhum lead na fila', 'enviados': 0}

        for row in rows:
            (
                lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, rating,
                user_id, user_plano, user_status, user_trial_expires_at,
            ) = row
            try:
                if not plano_tem_sdr(user_plano, user_status, user_trial_expires_at):
                    continue
                franz_input = FranzInput(
                    nome=nome or "", cidade=cidade or "", segmento=segmento or "",
                    telefone=telefone or "", whatsapp=whatsapp or "",
                    rating=rating or 0.0, site_url=site_url or "",
                    score_caio=80, tier="STANDARD"
                )
                if not user_id:
                    print(f"[Cron Franz] ⚠️ lead {lead_id} sem user_id — ignorado (multi-tenant)")
                    continue
                wpp_tenant = f"fralib_user_{user_id}"
                if not _dentro_do_horario(user_id):
                    print(f"[Cron Franz] ⏰ Lead {nome}: fora do horario do tenant {user_id} — aguardando janela")
                    continue
                if not is_tenant_connected(wpp_tenant):
                    print(f"[Cron Franz] ⏸ Lead {nome}: tenant {wpp_tenant} sem WhatsApp conectado — pulando")
                    continue
                franz_output = iniciar_contato(franz_input, user_id=user_id)

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

                # Enviar via meowhats
                tel = (whatsapp or telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"

                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": franz_output.reply}
                    )
                    if r.status_code == 200:
                        _salvar_interacao(lead_id, franz_output.reply, "saida", user_id)
                        conn.execute(text(
                            "UPDATE leads SET sdr_stage='hook', ab_variant=:var, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                        ), {"id": lead_id, "var": _escolher_variante(lead_id), "uid": user_id})
                        conn.commit()
                        enviados += 1
                        print(f"[Cron Franz] ✅ Enviado para {nome} ({tel[-4:]})")

                        # Jitter humanizado entre envios (so apos sucesso, so se sobrou lead)
                        if enviados < len(rows):
                            delay = random.uniform(FRANZ_CRON_JITTER_MIN_S, FRANZ_CRON_JITTER_MAX_S)
                            print(f"[Cron Franz] ⏳ aguardando {delay:.1f}s antes do proximo envio")
                            time.sleep(delay)
                    else:
                        erros += 1
                        print(f"[Cron Franz] ❌ Falha envio {nome}: {r.text[:80]}")
            except Exception as e:
                erros += 1
                print(f"[Cron Franz] ❌ Erro {nome}: {e}")

    return {'status': 'ok', 'enviados': enviados, 'erros': erros, 'total_fila': len(rows)}


@router.post('/followup-bryan')
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

    import httpx, re as _re
    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        return {'status': 'erro_config', 'mensagem': 'MEOWHATS_KEY ausente', 'enviados': 0}

    enviados = 0
    perdidos = 0
    erros = 0

    with engine.connect() as conn:
        # ============================================================
        # FOLLOW-UP 1: leads com 24h+ sem resposta após intro
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
        """), {"limite_24h": (datetime.utcnow() - timedelta(hours=24)).isoformat()}).fetchall()

        # ============================================================
        # FOLLOW-UP 2: leads com 72h+ sem resposta após FU1
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
        """), {"limite_72h": (datetime.utcnow() - timedelta(hours=72)).isoformat()}).fetchall()

        # ============================================================
        # LOST: leads com 24h+ sem resposta após FU2
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
        """), {"limite_24h_lost": (datetime.utcnow() - timedelta(hours=24)).isoformat()}).fetchall()

        # Combinar FU1 e FU2 (lost é tratado separado)
        rows = list(rows_fu1) + list(rows_fu2)

        # Also fetch scheduled leads whose followup_date has arrived
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
                tel = (whatsapp or telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"
                wpp_tenant = f"fralib_user_{user_id}"

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

                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": fu_output.reply}
                    )
                    if r.status_code == 200:
                        _salvar_interacao(lead_id, fu_output.reply, "saida", user_id)
                        conn.execute(text(
                            "UPDATE leads SET sdr_stage=:stage, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                        ), {"id": lead_id, "stage": novo_stage, "uid": user_id})
                        conn.commit()
                        enviados += 1
                        print(f"[Cron FU] ✅ Follow-up '{tipo}' para {nome}")
                    else:
                        erros += 1
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
                tel = (whatsapp or telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"
                wpp_tenant = f"fralib_user_{user_id}"

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

                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": fu_output.reply}
                    )
                    if r.status_code == 200:
                        _salvar_interacao(lead_id, fu_output.reply, "saida", user_id)
                        # Volta pro stage anterior ao scheduled (discovery ou qualify)
                        conn.execute(text(
                            "UPDATE leads SET sdr_stage='pain', followup_date=NULL, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                        ), {"id": lead_id, "uid": user_id})
                        conn.commit()
                        enviados += 1
                        print(f"[Cron FU] 📅 Agendado retomado: {nome}")
                    else:
                        erros += 1
            except Exception as e:
                erros += 1
                print(f"[Cron FU] ❌ Erro scheduled {nome}: {e}")

    return {'status': 'ok', 'enviados': enviados, 'perdidos': perdidos, 'erros': erros, 'total': len(rows) + len(scheduled_rows)}
