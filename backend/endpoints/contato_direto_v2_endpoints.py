"""
Endpoint de Contato Direto ATUALIZADO.

Mostra TODOS os leads com telefone (independente de confirmacao),
incluindo os mais recentes. Auto-refresh a cada 30s.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.access_control import require_superadmin

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/admin/outreach', tags=['contato-direto-v2'])


@router.get("/contato-direto-v2")
async def contato_direto_v2(
    plano: str = Query("todos", description="trial|todos|pro|ilimitado|..."),
    status: str = Query("todos", description="todos|sem_outreach|replied|converted|novo"),
    q: str = Query("", description="busca livre por nome, email ou telefone"),
    incluir_sem_telefone: bool = Query(True, description="incluir usuarios sem telefone"),
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Lista TODOS os usuarios da plataforma com WhatsApp OU sem telefone.
    Por padrao inclui usuarios sem telefone para que o admin veja todos.

    - Mostra leads novos (cadastrados ha menos de 7 dias)
    - Mostra leads antigos
    - Marca com badge "NOVO" os cadastrados recentes
    - Permite filtrar por status outreach
    """
    try:
        # Query principal - TODOS os usuarios (com ou sem telefone)
        if incluir_sem_telefone:
            where_telefone = "(u.telefone IS NULL OR (LENGTH(REGEXP_REPLACE(u.telefone, '[^0-9]', '', 'g')) BETWEEN 10 AND 13))"
        else:
            where_telefone = "u.telefone IS NOT NULL AND LENGTH(REGEXP_REPLACE(u.telefone, '[^0-9]', '', 'g')) BETWEEN 10 AND 11"

        rows = db.execute(text(f"""
            WITH outreach_status AS (
                SELECT
                    oa.user_id,
                    MAX(oa.status) AS outreach_status,
                    MAX(oa.replied_at) AS replied_at,
                    COUNT(*) FILTER (WHERE oa.status = 'sent') AS outreach_sent,
                    MAX(oa.campaign) AS last_campaign,
                    MAX(oa.sent_at) AS last_sent_at
                FROM outreach_attempts oa
                WHERE oa.campaign = 'reativacao_drip_v1_2026_06_26'
                GROUP BY oa.user_id
            )
            SELECT
                u.id AS user_id,
                u.email,
                COALESCE(NULLIF(u.nome, ''), NULLIF(u.name, ''), u.email) AS nome,
                u.plano,
                u.status AS user_status,
                u.telefone,
                u.criado_em,
                COALESCE(u.email_confirmado, false) AS email_confirmado,
                COALESCE(u.sites_used, 0) AS sites_used,
                COALESCE(u.tokens_used_month, 0) AS tokens_used_month,
                COALESCE(u.sdr_messages_today, 0) AS sdr_messages_today,
                COALESCE(os.outreach_status, 'none') AS outreach_status,
                COALESCE(os.replied_at, NULL) AS replied_at,
                COALESCE(os.outreach_sent, 0) AS outreach_sent,
                COALESCE(os.last_campaign, '') AS last_campaign,
                COALESCE(os.last_sent_at, NULL) AS last_sent_at,
                EXTRACT(DAY FROM (NOW() - u.criado_em::timestamp))::int AS dias_cadastro,
                EXTRACT(HOUR FROM (NOW() - u.criado_em::timestamp))::int AS horas_cadastro
            FROM users u
            LEFT JOIN outreach_status os ON os.user_id = u.id
            WHERE u.role != 'superadmin'
              AND {where_telefone}
              -- Excluir apenas fantasmas conhecidos
              AND u.email NOT LIKE 'test.%@test.com'
              AND u.email NOT LIKE 'pipeline.%@test.com'
              AND u.email NOT LIKE 'smoke.%@test.com'
              AND u.email NOT LIKE '%@fralib%'
              AND u.email NOT LIKE '%@teste.com'
        """)).fetchall()

        items = []
        for r in rows:
            user_id = r[0]
            email = r[1]
            nome = r[2]
            plano_user = r[3]
            user_status = r[4]
            telefone = r[5]
            criado_em = r[6]
            email_confirmado = r[7]
            sites_used = r[8]
            tokens_used = r[9]
            sdr_msgs = r[10]
            outreach_status = r[11]
            replied_at = r[12]
            outreach_sent = r[13]
            last_campaign = r[14]
            last_sent_at = r[15]
            dias_cadastro = r[16] or 0
            horas_cadastro = r[17] or 0

            # Normalizar telefone para wa.me (se tiver)
            telefone_str = str(telefone) if telefone else ""
            telefone_limpo = ''.join(c for c in telefone_str if c.isdigit())

            # Adicionar 55 se nao tiver codigo do pais
            if telefone_limpo and not telefone_limpo.startswith("55") and len(telefone_limpo) <= 11:
                telefone_limpo = "55" + telefone_limpo

            wa_link = None
            tem_whatsapp = False
            if telefone_limpo and len(telefone_limpo) >= 12:
                msg = f"Ola! Vi seu cadastro no FraLib e quero ajuda com meu site."
                wa_link = f"https://wa.me/{telefone_limpo}?text={msg.replace(' ', '%20')}"
                tem_whatsapp = True

            # Determinar status de outreach
            if outreach_status == 'replied':
                display_status = 'replied'
            elif sites_used > 0 or tokens_used > 0 or sdr_msgs > 0:
                display_status = 'converted'
            elif outreach_status in ('sent', 'pending'):
                display_status = 'sent'
            elif outreach_status == 'none':
                # Lead novo = cadastrado ha menos de 7 dias E sem outreach
                if dias_cadastro <= 7:
                    display_status = 'novo'
                else:
                    display_status = 'sem_outreach'
            else:
                display_status = 'sem_outreach'

            # Badge "NOVO" se cadastrado ha menos de 24h
            is_new_lead = horas_cadastro < 24 and outreach_status == 'none'

            items.append({
                "user_id": user_id,
                "email": email,
                "nome": nome or email.split('@')[0],
                "plano": plano_user or "trial",
                "user_status": user_status or "trial",
                "telefone": telefone_str if telefone_str else None,
                "telefone_normalizado": telefone_limpo,
                "wa_link": wa_link,
                "tem_whatsapp": tem_whatsapp,
                "email_confirmado": email_confirmado,
                "criado_em": str(criado_em) if criado_em else None,
                "dias_cadastro": dias_cadastro,
                "horas_cadastro": horas_cadastro,
                "is_new_lead": is_new_lead,
                "sites_used": sites_used,
                "tokens_used_month": tokens_used,
                "sdr_messages_today": sdr_msgs,
                "outreach_status": outreach_status,
                "outreach_sent": outreach_sent,
                "last_sent_at": str(last_sent_at) if last_sent_at else None,
                "replied_at": str(replied_at) if replied_at else None,
                "display_status": display_status,
                "last_campaign": last_campaign or ""
            })

        # Aplicar filtros
        filtered = items

        if plano != "todos":
            filtered = [i for i in filtered if i["plano"] == plano]

        if status != "todos":
            filtered = [i for i in filtered if i["display_status"] == status]

        if q:
            q_lower = q.lower()
            filtered = [
                i for i in filtered
                if q_lower in (i["email"] or "").lower()
                or q_lower in (i["nome"] or "").lower()
                or q_lower in (i["telefone"] or "")
                or q_lower in (i["telefone_normalizado"] or "")
            ]

        # Ordenar por mais recentes primeiro (dias_cadastro ASC = mais recente)
        filtered.sort(key=lambda x: x["dias_cadastro"])

        # Estatisticas
        total = len(items)
        sem_contato = sum(1 for i in items if i["display_status"] in ["sem_outreach", "novo"])
        replied = sum(1 for i in items if i["display_status"] == "replied")
        convertidos = sum(1 for i in items if i["display_status"] == "converted")
        novos = sum(1 for i in items if i["is_new_lead"])

        return {
            "ok": True,
            "total": total,
            "sem_contato": sem_contato,
            "replied": replied,
            "convertidos": convertidos,
            "novos": novos,
            "items": filtered,
            "_cache": "no-cache"
        }

    except Exception as e:
        logger.error(f"Erro contato-direto-v2: {e}")
        return {
            "ok": False,
            "error": str(e),
            "items": []
        }


@router.post("/contato-direto-v2/marcar-contatado/{user_id}")
async def marcar_contatado_v2(
    user_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Marca usuario como contatado manualmente.
    - Registra outreach_attempts com status='replied'
    - Cria entrada em interacoes_admin
    - Retorna wa_link pronto para abrir conversa
    """
    try:
        # Verificar se usuario existe
        u = db.execute(text("""
            SELECT id, email, nome, COALESCE(telefone, '') as telefone
            FROM users WHERE id = :id AND role != 'superadmin'
        """), {"id": user_id}).fetchone()

        if not u:
            raise HTTPException(404, "Usuario nao encontrado")

        email = u[1]
        nome = u[2]
        telefone = u[3]

        # Verificar se ja existe outreach para esta campanha
        existing = db.execute(text("""
            SELECT id, status FROM outreach_attempts
            WHERE user_id = :uid AND campaign = 'reativacao_drip_v1_2026_06_26'
            ORDER BY id DESC LIMIT 1
        """), {"uid": user_id}).fetchone()

        if existing:
            # Atualizar para replied
            db.execute(text("""
                UPDATE outreach_attempts
                SET status = 'replied',
                    replied_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) || '{"manual_contact": true}'::jsonb
                WHERE id = :id
            """), {"id": existing[0]})
        else:
            # Criar novo registro como replied (manual)
            db.execute(text("""
                INSERT INTO outreach_attempts
                (user_id, campaign, channel, status, replied_at, sent_at, metadata)
                VALUES (:uid, 'reativacao_drip_v1_2026_06_26', 'whatsapp', 'replied', NOW(), NOW(),
                        '{"manual_contact": true, "canal": "contato_direto_admin"}'::jsonb)
            """), {"uid": user_id})

        # Criar tabela interacoes se nao existir
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS interacoes_admin (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                canal VARCHAR(20),
                tipo VARCHAR(50),
                nota TEXT,
                criado_por VARCHAR(255),
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """))
        db.execute(text("""
            INSERT INTO interacoes_admin (user_id, canal, tipo, nota, criado_por)
            VALUES (:uid, 'whatsapp', 'contato_manual_direto', 'Marcado como contatado via painel admin', :criado_por)
        """), {"uid": user_id, "criado_por": user.get("email", "superadmin")})

        db.commit()

        # Gerar wa_link
        wa_link = None
        tel_limpo = ''.join(c for c in str(telefone) if c.isdigit())
        if tel_limpo:
            if not tel_limpo.startswith("55") and len(tel_limpo) <= 11:
                tel_limpo = "55" + tel_limpo
            if len(tel_limpo) >= 12:
                wa_link = f"https://wa.me/{tel_limpo}"

        return {
            "ok": True,
            "user_id": user_id,
            "email": email,
            "nome": nome,
            "telefone": telefone,
            "wa_link": wa_link,
            "message": f"{nome} marcado como contatado!"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro marcar contatado: {e}")
        raise HTTPException(500, f"Erro: {e}")