"""
Endpoints disparados por cron externo (crontab/PM2).

Autenticacao por header X-Cron-Secret == CRON_SECRET do .env.
Nunca expor sem secret - estes endpoints podem mandar emails em massa.
"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from database import engine
from services.email_service import enviar_email_resumo_diario
from whatsapp_listener import is_tenant_connected

router = APIRouter(prefix='/api/cron', tags=['cron'])

CRON_SECRET = os.getenv('CRON_SECRET', '')


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
async def despachar_fila_bryan(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """
    Despacha leads com sdr_stage='pendente_wpp' (site pronto, fora do horário).
    Chamado a cada 30min pelo PM2/cron. Respeita horário de atendimento (8h-21h Brasília).
    """
    _autorizar(x_cron_secret)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
    from agents.franz import iniciar_contato, BryanInput, _dentro_do_horario, _escolher_variante

    if not _dentro_do_horario():
        return {'status': 'fora_horario', 'mensagem': 'Fora do horário de atendimento (8h-21h Brasília)', 'enviados': 0}

    import httpx, re as _re
    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "")

    enviados = 0
    erros = 0

    with engine.connect() as conn:
        # Buscar leads pendentes (site pronto mas não abordados)
        rows = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.rating, l.user_id
            FROM leads l
            WHERE l.sdr_stage = 'pendente_wpp'
              AND l.status = 'concluido'
              AND l.site_url IS NOT NULL
            ORDER BY l.processado_em ASC
            LIMIT 10
        """)).fetchall()

        if not rows:
            return {'status': 'ok', 'mensagem': 'Nenhum lead na fila', 'enviados': 0}

        for row in rows:
            lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, rating, user_id = row
            try:
                bryan_input = BryanInput(
                    nome=nome or "", cidade=cidade or "", segmento=segmento or "",
                    telefone=telefone or "", whatsapp=whatsapp or "",
                    rating=rating or 0.0, site_url=site_url or "",
                    score_caio=80, tier="STANDARD"
                )
                if not user_id:
                    print(f"[Cron franz] ⚠️ lead {lead_id} sem user_id — ignorado (multi-tenant)")
                    continue
                bryan_output = iniciar_contato(bryan_input, user_id=user_id)

                if not bryan_output.reply or not bryan_output.reply.strip():
                    continue

                # Enviar via meowhats
                tel = (whatsapp or telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"
                wpp_tenant = f"fralib_user_{user_id}"

                if not is_tenant_connected(wpp_tenant):
                    print(f"[Cron franz] ⏸ Lead {nome}: tenant {wpp_tenant} sem WhatsApp conectado — pulando")
                    continue

                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": bryan_output.reply}
                    )
                    if r.status_code == 200:
                        conn.execute(text(
                            "UPDATE leads SET sdr_stage='hook', ab_variant=:var, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                        ), {"id": lead_id, "var": _escolher_variante(lead_id), "uid": user_id})
                        conn.commit()
                        enviados += 1
                        print(f"[Cron franz] ✅ Enviado para {nome} ({tel[-4:]})")
                    else:
                        erros += 1
                        print(f"[Cron franz] ❌ Falha envio {nome}: {r.text[:80]}")
            except Exception as e:
                erros += 1
                print(f"[Cron franz] ❌ Erro {nome}: {e}")

    return {'status': 'ok', 'enviados': enviados, 'erros': erros, 'total_fila': len(rows)}


@router.post('/followup-franz')
async def followup_bryan(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """
    Envia follow-up para leads sem resposta.
    - 1h sem resposta após intro → follow-up 1
    - 2h sem resposta após FU1 → follow-up 2
    - 3h sem resposta após FU2 → marca como lost
    Chamado a cada 1h pelo PM2/cron.
    """
    _autorizar(x_cron_secret)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
    from agents.franz import followup_automatico, _dentro_do_horario

    if not _dentro_do_horario():
        return {'status': 'fora_horario', 'mensagem': 'Fora do horário', 'enviados': 0}

    import httpx, re as _re
    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "")

    enviados = 0
    perdidos = 0
    erros = 0

    with engine.connect() as conn:
        # Leads que receberam intro/FU1/FU2 mas não responderam há mais de 1h
        rows = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.sdr_stage, l.user_id, l.atualizado_em
            FROM leads l
            WHERE l.status = 'concluido'
              AND l.sdr_stage IN ('hook', 'qualify', 'pain', 'amplify', 'tease', 'proof', 'reveal', 'feedback', 'followup_24h', 'followup_72h')
              AND l.atualizado_em < :limite
            ORDER BY l.atualizado_em ASC
            LIMIT 15
        """), {"limite": (datetime.utcnow() - timedelta(hours=1)).isoformat()}).fetchall()

        # Also fetch scheduled leads whose followup_date has arrived
        scheduled_rows = conn.execute(text("""
            SELECT l.id, l.nome, l.telefone, l.whatsapp, l.segmento, l.cidade,
                   l.site_url, l.sdr_stage, l.user_id, l.atualizado_em
            FROM leads l
            WHERE l.status = 'concluido'
              AND l.sdr_stage = 'scheduled'
              AND l.followup_date IS NOT NULL
              AND l.followup_date <= :hoje
            ORDER BY l.followup_date ASC
            LIMIT 10
        """), {"hoje": datetime.utcnow().strftime('%Y-%m-%d')}).fetchall()

        if not rows and not scheduled_rows:
            return {'status': 'ok', 'mensagem': 'Nenhum lead para follow-up', 'enviados': 0}

        for row in rows:
            lead_id, nome, telefone, whatsapp, segmento, cidade, site_url, sdr_stage, user_id, atualizado_em = row
            try:
                # Determinar tipo de follow-up
                if sdr_stage in ('hook', 'qualify', 'pain', 'amplify', 'tease', 'proof', 'reveal', 'feedback'):
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
                fu_output = followup_automatico(telefone or whatsapp or "", tipo, user_id=user_id)

                if not fu_output.reply or not fu_output.reply.strip():
                    continue

                # Enviar
                tel = (whatsapp or telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"
                if not user_id:
                    print(f"[Cron franz] ⚠️ lead {lead_id} sem user_id — ignorado (multi-tenant)")
                    continue
                wpp_tenant = f"fralib_user_{user_id}"

                if not is_tenant_connected(wpp_tenant):
                    print(f"[Cron franz] ⏸ Follow-up lead {lead_id}: tenant {wpp_tenant} sem WhatsApp conectado — pulando")
                    continue

                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": fu_output.reply}
                    )
                    if r.status_code == 200:
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
                fu_output = followup_automatico(telefone or whatsapp or "", "scheduled", user_id=user_id)

                if not fu_output.reply or not fu_output.reply.strip():
                    continue

                tel = (whatsapp or telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"
                if not user_id:
                    print(f"[Cron franz] ⚠️ lead {lead_id} sem user_id — ignorado (multi-tenant)")
                    continue
                wpp_tenant = f"fralib_user_{user_id}"

                if not is_tenant_connected(wpp_tenant):
                    print(f"[Cron FU] ⏸ Agendado lead {lead_id}: tenant {wpp_tenant} sem WhatsApp conectado — pulando")
                    continue

                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": fu_output.reply}
                    )
                    if r.status_code == 200:
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
