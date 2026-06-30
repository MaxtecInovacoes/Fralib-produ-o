"""
Endpoints para entender e abordar usuarios inativos.
Permite descobrir POR QUE nao geraram pipeline e iniciar conversas.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.access_control import require_superadmin

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/admin/inativos', tags=['inativos'])


@router.get("/analise")
async def analisar_inativos(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Lista usuarios inativos com motivo pela inatividade.

    Critérios:
    - Nunca acessaram o sistema
    - Cadastrados ha mais de 24h
    - Plano trial ativo

    Inclui dados para contact via WhatsApp/email e motivo da inatividade.
    """
    try:
        # Query principal - usuarios com sinais de inatividade
        rows = db.execute(text("""
            SELECT
                u.id, u.email, u.nome, u.plano, u.status,
                u.criado_em, u.ultimo_acesso,
                u.email_confirmado,
                COALESCE(u.telefone, '') as telefone,
                COALESCE(u.nicho, '') as nicho,
                COALESCE(u.cidade, '') as cidade,
                u.trial_expires_at,
                u.plan_expires_at,
                EXTRACT(DAY FROM NOW() - u.criado_em::timestamp)::int as dias_desde_cadastro,
                (
                    SELECT COUNT(*) FROM leads WHERE user_id = u.id
                ) as total_leads,
                (
                    SELECT COUNT(*) FROM token_transactions WHERE user_id = u.id
                ) as total_tokens,
                (
                    SELECT MAX(criado_em) FROM token_transactions WHERE user_id = u.id
                ) as ultimo_token_uso,
                EXISTS(
                    SELECT 1 FROM users WHERE id = u.id AND perfil_completo = true
                ) as perfil_completo,
                EXISTS(
                    SELECT 1 FROM users WHERE id = u.id
                    WHERE nicho IS NOT NULL AND nicho != ''
                ) as tem_nicho,
                EXISTS(
                    SELECT 1 FROM users WHERE id = u.id
                    WHERE telefone IS NOT NULL AND telefone != ''
                ) as tem_telefone
            FROM users u
            WHERE u.role != 'superadmin'
            AND (
                u.ultimo_acesso IS NULL
                OR u.ultimo_acesso = ''
                OR u.ultimo_acesso = 'Nunca'
                OR u.ultimo_acesso < NOW() - INTERVAL '7 days'
            )
            AND u.criado_em < NOW() - INTERVAL '24 hours'
            ORDER BY u.criado_em DESC
        """)).fetchall()

        inativos = []
        for r in rows:
            dias_cadastro = r[14] or 0
            motivo = _classificar_motivo(r, dias_cadastro)

            # Normalizar telefone para wa.me
            telefone_raw = r[9] or ""
            telefone_limpo = telefone_raw.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            wa_link = None
            if telefone_limpo and len(telefone_limpo) >= 10:
                # Adicionar 55 se nao tiver codigo do pais
                if not telefone_limpo.startswith("55") and len(telefone_limpo) <= 11:
                    telefone_limpo = "55" + telefone_limpo
                wa_link = f"https://wa.me/{telefone_limpo}"

            # Calcular trial expirando
            trial_exp = r[12]
            trial_expirando = False
            dias_para_expirar = None
            if trial_exp:
                try:
                    exp_date = trial_exp if isinstance(trial_exp, datetime) else datetime.fromisoformat(str(trial_exp))
                    dias_para_expirar = (exp_date - datetime.now()).days
                    trial_expirando = 0 < dias_para_expirar <= 7
                except Exception:
                    pass

            inativos.append({
                "id": r[0],
                "email": r[1],
                "nome": r[2] or "",
                "plano": r[3] or "trial",
                "status": r[4] or "trial",
                "criado_em": str(r[5]) if r[5] else None,
                "ultimo_acesso": str(r[6]) if r[6] else "Nunca",
                "email_confirmado": r[7] or False,
                "telefone": telefone_raw,
                "telefone_normalizado": telefone_limpo if wa_link else "",
                "wa_link": wa_link,
                "nicho": r[10] or "",
                "cidade": r[11] or "",
                "dias_desde_cadastro": dias_cadastro,
                "trial_expira_em": str(trial_exp) if trial_exp else None,
                "trial_expirando": trial_expirando,
                "dias_para_expirar": dias_para_expirar,
                "total_leads": r[15] or 0,
                "total_tokens": r[16] or 0,
                "ultimo_token_uso": str(r[17]) if r[17] else None,
                "perfil_completo": r[18] or False,
                "tem_nicho": r[19] or False,
                "tem_telefone": r[20] or False,
                "categoria": motivo["categoria"],
                "motivo": motivo["motivo"],
                "sugestao_abordagem": motivo["sugestao"],
                "prioridade": motivo["prioridade"]
            })

        # Estatisticas
        stats = {
            "total": len(inativos),
            "trial_expirando": sum(1 for i in inativos if i["trial_expirando"]),
            "perfil_incompleto": sum(1 for i in inativos if not i["perfil_completo"]),
            "sem_telefone": sum(1 for i in inativos if not i["tem_telefone"]),
            "sem_nicho": sum(1 for i in inativos if not i["tem_nicho"]),
            "antigos_30_dias": sum(1 for i in inativos if i["dias_desde_cadastro"] > 30),
            "antigos_7_dias": sum(1 for i in inativos if 7 < i["dias_desde_cadastro"] <= 30)
        }

        return {
            "ok": True,
            "stats": stats,
            "inativos": inativos
        }
    except Exception as e:
        logger.error(f"Erro ao analisar inativos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")


def _classificar_motivo(row, dias_cadastro: int) -> dict:
    """Classifica o motivo da inatividade e sugere abordagem."""

    perfil_completo = row[18]
    tem_nicho = row[19]
    tem_telefone = row[20]
    total_leads = row[15] or 0
    nome = row[2] or ""
    cidade = row[11] or ""

    # Trial expirando (urgente!)
    if row[12]:
        try:
            exp = row[12] if isinstance(row[12], datetime) else datetime.fromisoformat(str(row[12]))
            dias = (exp - datetime.now()).days
            if 0 < dias <= 3:
                return {
                    "categoria": "urgente",
                    "motivo": f"Trial expira em {dias} dia(s)",
                    "sugestao": f"Oferecer upgrade ou estender trial. Risco alto de churn.",
                    "prioridade": 1
                }
        except Exception:
            pass

    # Antigo + sem nada
    if dias_cadastro > 30 and not tem_nicho and not tem_telefone and total_leads == 0:
        return {
            "categoria": "abandonou",
            "motivo": f"Cadastrado há {dias_cadastro} dias mas nunca usou",
            "sugestao": "Mensagem curta perguntando se ainda tem interesse. Oferecer ajuda 1-a-1.",
            "prioridade": 2
        }

    # Tem telefone mas nao engajou
    if tem_telefone and total_leads == 0:
        return {
            "categoria": "lead_quente",
            "motivo": "Tem WhatsApp mas nao criou leads ainda",
            "sugestao": "WhatsApp consultivo: ajudar a comecar primeiro pipeline.",
            "prioridade": 1
        }

    # Sem nicho definido
    if not tem_nicho and total_leads == 0:
        return {
            "categoria": "perfil_incompleto",
            "motivo": "Nao definiu nicho ainda",
            "sugestao": "Email com 3 nichos populares para escolher.",
            "prioridade": 2
        }

    # Sem telefone mas com perfil
    if perfil_completo and not tem_telefone:
        return {
            "categoria": "sem_canal_direto",
            "motivo": "Perfil OK mas sem WhatsApp",
            "sugestao": "Email pedindo WhatsApp para suporte consultivo.",
            "prioridade": 3
        }

    # Tem lead mas nao converteu
    if total_leads > 0 and total_leads < 3:
        return {
            "categoria": "engajou_pouco",
            "motivo": f"Criou {total_leads} lead(s) mas parou",
            "sugestao": "Demonstrar como gerar mais leads com o mesmo nicho.",
            "prioridade": 2
        }

    # Padrao
    return {
        "categoria": "geral",
        "motivo": "Inativo sem sinais claros",
        "sugestao": "Mensagem generica de reativacao.",
        "prioridade": 4
    }


@router.post("/iniciar-conversa")
async def iniciar_conversa(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Marca usuario como 'em conversa' e gera uma nota.

    Body: {user_id, canal: 'whatsapp'|'email', nota: string}
    """
    try:
        body = await request.json()
        user_id = body.get("user_id")
        canal = body.get("canal", "email")
        nota = body.get("nota", "")

        if not user_id:
            raise HTTPException(status_code=400, detail="user_id obrigatorio")

        # Verificar se usuario existe
        u = db.execute(text("SELECT email, nome FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        # Inserir interacao (reutilizando tabela outreach_events se existir)
        try:
            db.execute(text("""
                INSERT INTO interacoes (user_id, canal, tipo, nota, criado_por, criado_em)
                VALUES (:uid, :canal, 'iniciar_conversa', :nota, :criado_por, NOW())
            """), {
                "uid": user_id,
                "canal": canal,
                "nota": nota,
                "criado_por": user.get("email", "superadmin")
            })
        except Exception:
            # Se tabela nao existir, criar tabela
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
                VALUES (:uid, :canal, 'iniciar_conversa', :nota, :criado_por)
            """), {
                "uid": user_id,
                "canal": canal,
                "nota": nota,
                "criado_por": user.get("email", "superadmin")
            })

        db.commit()

        return {
            "ok": True,
            "message": f"Conversa iniciada com {u[1] or u[0]} via {canal}",
            "user_id": user_id,
            "email": u[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao iniciar conversa: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")


@router.post("/bulk-iniciar-conversa")
async def bulk_iniciar_conversa(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Inicia conversa com varios usuarios de uma vez.

    Body: {user_ids: [1,2,3], canal: 'email', nota_template: string}
    """
    try:
        body = await request.json()
        user_ids = body.get("user_ids", [])
        canal = body.get("canal", "email")
        nota_template = body.get("nota_template", "Conversa iniciada em massa")

        if not user_ids:
            raise HTTPException(status_code=400, detail="user_ids obrigatorio")

        # Criar tabela se nao existir
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

        # Inserir para cada user
        for uid in user_ids:
            db.execute(text("""
                INSERT INTO interacoes_admin (user_id, canal, tipo, nota, criado_por)
                VALUES (:uid, :canal, 'iniciar_conversa_bulk', :nota, :criado_por)
            """), {
                "uid": uid,
                "canal": canal,
                "nota": nota_template,
                "criado_por": user.get("email", "superadmin")
            })

        db.commit()

        return {
            "ok": True,
            "message": f"Conversa iniciada com {len(user_ids)} usuarios via {canal}",
            "count": len(user_ids)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Erro bulk iniciar conversa: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")


@router.get("/conversas-ativas")
async def listar_conversas_ativas(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Lista conversas ja iniciadas pelo admin.
    """
    try:
        # Criar tabela se nao existir
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
        db.commit()

        # Buscar conversas
        rows = db.execute(text("""
            SELECT
                i.id, i.user_id, i.canal, i.tipo, i.nota,
                i.criado_em, i.criado_por,
                u.email, u.nome, u.plano, u.status
            FROM interacoes_admin i
            LEFT JOIN users u ON u.id = i.user_id
            ORDER BY i.criado_em DESC
            LIMIT 100
        """)).fetchall()

        conversas = [
            {
                "id": r[0],
                "user_id": r[1],
                "canal": r[2],
                "tipo": r[3],
                "nota": r[4] or "",
                "criado_em": str(r[5]) if r[5] else None,
                "criado_por": r[6] or "",
                "user_email": r[7] or "",
                "user_nome": r[8] or "",
                "user_plano": r[9] or "",
                "user_status": r[10] or ""
            }
            for r in rows
        ]

        return {
            "ok": True,
            "total": len(conversas),
            "conversas": conversas
        }
    except Exception as e:
        logger.error(f"Erro listar conversas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")


@router.get("/template-sugestoes")
async def template_sugestoes(
    categoria: str = Query("geral", description="categoria do motivo"),
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Retorna templates de mensagem baseado na categoria.
    """
    templates = {
        "urgente": {
            "whatsapp": "Oi {nome}! Vi que sua trial no FraLib expira em {dias} dias. Posso te ajudar a aproveitar melhor esses dias finais? Tenho uma oferta especial se quiser continuar. Responda SIM e te ligo!",
            "email": "Assunto: Seu trial acaba em {dias} dias\n\nOi {nome},\n\nNotei que vc se cadastrou no FraLib mas talvez nao conseguiu testar ainda. Seu trial acaba em {dias} dias. Quer ajuda 1-a-1?\n\nPosso te ligar agora e mostrar como comecar em 15 minutos."
        },
        "lead_quente": {
            "whatsapp": "Oi {nome}! Sou do FraLib. Vi que vc criou sua conta mas ainda nao gerou seu primeiro site. Posso te ajudar a comecar? Me fala seu nicho que eu faco o primeiro pra vc gratis!",
            "email": "Assunto: Vamos criar seu primeiro site juntos?\n\nOi {nome},\n\nVi que vc esta com conta ativa no FraLib mas ainda nao gerou seu primeiro site. Posso te ajudar a comecar agora? Sao 15 minutos e sai com um site profissional pronto."
        },
        "perfil_incompleto": {
            "email": "Assunto: Falta so uma coisa pra comecar\n\nOi {nome},\n\nVi que vc criou conta no FraLib mas nao definiu seu nicho ainda. Qual sua area?\n\n- Nutricao\n- Advocacia\n- Odontologia\n- Outro\n\nResponde com a letra e eu comeco seu primeiro site agora mesmo!"
        },
        "abandonou": {
            "email": "Assunto: Ainda tem interesse?\n\nOi {nome},\n\nVc criou conta ha {dias} dias no FraLib mas ainda nao usou. Aconteceu alguma coisa?\n\nPosso te ajudar a comecar HOJE em 15 min. Ou se nao quer mais, sem problema tambem - me avisa?\n\nAbs,\nEquipe FraLib"
        },
        "engajou_pouco": {
            "whatsapp": "Oi {nome}! Vi que vc criou {total_leads} lead(s) no FraLib. Quer continuar de onde parou? Me fala o nicho que eu listo os proximos 5 negocios na sua cidade!",
            "email": "Assunto: Vamos gerar mais leads?\n\nOi {nome},\n\nVc ja criou {total_leads} lead(s) no FraLib. Bom comeco! Quer continuar explorando o mesmo nicho? Posso te ajudar a expandir."
        },
        "geral": {
            "email": "Assunto: Oi {nome}, tudo bem?\n\nVc criou conta no FraLib e eu queria entender: teve alguma duvida que travou seu uso?\n\nMe responde esse email com 1 frase do que aconteceu que te ajudo.\n\nAbs,\nEquipe FraLib"
        }
    }

    return {
        "ok": True,
        "categoria": categoria,
        "templates": templates.get(categoria, templates["geral"])
    }
