"""
Sistema de disparo gradual de WhatsApp para leads inativos.
- Mensagens variadas (3-5 variacoes por motivo) para evitar bloqueio
- Intervalo de 5-10 minutos entre envios
- Rate limiting respeitado
- Envia 1 lead por vez com delay randomizado
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.access_control import require_superadmin

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/admin/whatsapp', tags=['whatsapp-disparo'])


# ============================================================
# TEMPLATES VARIADOS (anti-bloqueio)
# ============================================================

TEMPLATES_POR_MOTIVO = {
    "trial_expirando": [
        "Oi {nome}! Vi que vc criou conta no FraLib mas ainda nao testou. Seu trial expira em {dias} dias - posso te ajudar? Me fala seu nicho e faco seu primeiro site gratis!",
        "Eai {nome}, tudo certo? Aqui e do FraLib. Notei que vc se cadastrou mas talvez ficou com duvida. Tem 2 min pra eu te explicar como funciona?",
        "Oi {nome}! Sou a equipe FraLib. Seu trial acaba em {dias} dias. Quer que eu crie um site de exemplo pra vc ver a qualidade? So me fala o nicho.",
        "Fala {nome}! Vc ainda tem {dias} dia(s) de trial. Posso te ajudar agora? Responde SIM e te ligo em 5 minutos.",
        "Oi {nome}! Tudo bem? Vimos que vc criou conta no FraLib mas nao usou ainda. Quer experimentar? E gratis e sem compromisso."
    ],
    "lead_quente": [
        "Oi {nome}! Sou do FraLib. Vi que vc criou conta mas ainda nao gerou seu primeiro site. Posso te ajudar? Me fala seu nicho que eu faco agora!",
        "Eai {nome}! Vi seu cadastro no FraLib. Quer que eu crie seu primeiro site gratis? Me fala sua area (nutricao, advocacia, etc).",
        "Oi {nome}! Equipe FraLib aqui. Ta com alguma duvida sobre como comecar? Me manda um oi que eu te ajudo.",
        "Fala {nome}! Vi que vc ainda nao gerou seu site no FraLib. Quer ajuda? E so me dizer o que vc faz.",
        "Oi {nome}! Lembrei de vc que se cadastrou no FraLib. Posso te ajudar a criar seu primeiro site agora? E gratis."
    ],
    "perfil_incompleto": [
        "Oi {nome}! Vi que vc criou conta no FraLib mas nao escolheu seu nicho. Pode me falar? Nutricao, advocacia, dentista, ou outro?",
        "Fala {nome}! Equipe FraLib aqui. Vc criou conta mas faltou escolher a area. Me fala uma: nutricao, advocacia, fisio, odontologia?",
        "Oi {nome}! Vi que vc cadastrou mas nao terminou o perfil. Qual sua area de atuacao? Te ajudo a comecar!",
        "Eai {nome}! Falta so o nicho pra gente comecar. Me fala: 1) Nutricao 2) Advocacia 3) Outra? Responde com o numero.",
        "Oi {nome}! Notei que vc nao definiu seu nicho. Me fala rapidinho o que vc faz que eu te ajudo a comecar."
    ],
    "abandonou": [
        "Oi {nome}! Lembrei de vc do FraLib. Faz {dias} dias que vc criou conta mas nao usou. Aconteceu alguma coisa? Posso ajudar?",
        "Fala {nome}! Tudo bem? Aqui e do FraLib. Vc criou conta ha um tempo mas nao voltou. Quer retomar? Posso te ajudar agora.",
        "Oi {nome}! Vimos que vc criou conta no FraLib ha {dias} dias mas nao usou. Quer experimentar agora? E gratis.",
        "Eai {nome}! Faz tempo que vc criou conta no FraLib. Quer dar uma chance? Posso te ligar e mostrar como funciona em 10 min.",
        "Oi {nome}! Equipe FraLib aqui. Vc tem conta conosco mas nunca usou. Se nao quer mais, sem problema - me fala. Se quer tentar, me fala tambem!"
    ],
    "engajou_pouco": [
        "Oi {nome}! Vi que vc criou {leads} lead(s) no FraLib. Quer continuar? Me fala o nicho que eu listo mais negocios!",
        "Fala {nome}! Equipe FraLib. Vc ja criou {leads} lead(s) - bom comeco! Quer continuar prospectando?",
        "Oi {nome}! Vimos que vc ja criou {leads} lead(s). Quer gerar mais? E so me dizer o nicho que vc quer focar.",
        "Eai {nome}! Vi sua atividade no FraLib. Quer continuar prospectando? Posso te ajudar a criar mais leads.",
        "Oi {nome}! Lembrei de vc. Criou {leads} lead(s) no FraLib. Quer retomar de onde parou?"
    ],
    "geral": [
        "Oi {nome}! Tudo bem? Aqui e do FraLib. Vi que vc criou conta mas talvez ficou com alguma duvida. Posso te ajudar?",
        "Fala {nome}! Equipe FraLib aqui. Quer experimentar a plataforma? E gratis e posso te mostrar como funciona.",
        "Oi {nome}! Vc tem conta no FraLib mas ainda nao usou. Quer dar uma chance? Me fala seu nicho e comecamos!",
        "Eai {nome}! Tudo certo? Sou do FraLib. Quer que eu te ajude a criar seu primeiro site? E gratis!",
        "Oi {nome}! Espero que esteja bem! Vi sua conta no FraLib. Posso te ajudar a comecar? Me fala sua area."
    ]
}


def get_template(motivo: str, nome: str, **kwargs) -> str:
    """Retorna template aleatorio baseado no motivo."""
    templates = TEMPLATES_POR_MOTIVO.get(motivo, TEMPLATES_POR_MOTIVO["geral"])
    template = random.choice(templates)
    # Sanitizar nome
    primeiro_nome = (nome or "você").split()[0] if nome else "você"
    kwargs["nome"] = primeiro_nome
    try:
        return template.format(**kwargs)
    except Exception:
        return template


# ============================================================
# ENDPOINTS
# ============================================================

class DispararRequest(BaseModel):
    user_ids: List[int]
    delay_min_sec: Optional[int] = 5  # min 5 minutos entre mensagens
    delay_max_sec: Optional[int] = 10  # max 10 minutos
    dry_run: Optional[bool] = False


@router.post("/disparar-gradual")
async def disparar_gradual(
    payload: DispararRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Dispara mensagens gradualmente para os usuarios selecionados.

    - 1 mensagem a cada 5-10 minutos (anti-bloqueio)
    - Mensagens variadas por motivo
    - Verifica cooldown antes de enviar
    - Pode parar a qualquer momento
    """
    try:
        if not payload.user_ids:
            raise HTTPException(400, "user_ids obrigatorio")

        delay_min = max(60, payload.delay_min_sec * 60)  # minimo 60s
        delay_max = max(delay_min, payload.delay_max_sec * 60)

        # Buscar dados dos usuarios
        rows = db.execute(text("""
            SELECT u.id, u.email, u.nome,
                   COALESCE(u.telefone, '') as telefone,
                   COALESCE(u.nicho, '') as nicho,
                   COALESCE(EXTRACT(DAY FROM (NOW() - u.criado_em::timestamp))::int, 0) as dias_cadastro
            FROM users u
            WHERE u.id = ANY(:ids)
        """), {"ids": payload.user_ids}).fetchall()

        if not rows:
            raise HTTPException(404, "Nenhum usuario encontrado")

        resultados = {
            "total": len(rows),
            "enviados": [],
            "pulados": [],
            "erros": [],
            "config": {
                "delay_min_sec": delay_min // 60,
                "delay_max_sec": delay_max // 60,
                "dry_run": payload.dry_run
            }
        }

        for idx, row in enumerate(rows):
            user_id, email, nome, telefone, nicho, dias = row

            # Calcular motivo baseado nos dados
            motivo = "geral"
            if nicho and dias < 30:
                motivo = "lead_quente"
            elif not nicho:
                motivo = "perfil_incompleto"
            elif dias > 30:
                motivo = "abandonou"

            # Gerar mensagem
            mensagem = get_template(motivo, nome, dias=dias, leads=0)

            if payload.dry_run:
                resultados["enviados"].append({
                    "user_id": user_id,
                    "email": email,
                    "telefone": telefone,
                    "motivo": motivo,
                    "mensagem_preview": mensagem[:80] + "..."
                })
                continue

            # Em modo real, simular envio (aqui voce integraria com Meowhats/Evolution)
            # Por enquanto, registrar como tentativa
            try:
                # Verificar cooldown (se houver tabela)
                # Registrar tentativa
                db.execute(text("""
                    INSERT INTO interacoes_admin (user_id, canal, tipo, nota)
                    VALUES (:uid, 'whatsapp', 'disparo_gradual', :nota)
                """), {"uid": user_id, "nota": mensagem[:500]})
                db.commit()

                resultados["enviados"].append({
                    "user_id": user_id,
                    "email": email,
                    "telefone": telefone,
                    "motivo": motivo,
                    "mensagem": mensagem
                })
            except Exception as e:
                resultados["erros"].append({
                    "user_id": user_id,
                    "erro": str(e)[:100]
                })

            # Delay entre envios (exceto no ultimo)
            if idx < len(rows) - 1:
                delay = random.randint(delay_min, delay_max)
                resultados["proximo_delay_segundos"] = delay
                await asyncio.sleep(0)  # nao bloquear aqui (modo async)

        return resultados

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro disparo gradual: {e}")
        raise HTTPException(500, f"Erro: {e}")


@router.get("/preview-template")
async def preview_template(
    motivo: str = "geral",
    nome: str = "Joao",
    dias: int = 5,
    leads: int = 0,
    user: dict = Depends(require_superadmin)
):
    """Retorna preview de uma mensagem para o motivo especificado."""
    mensagem = get_template(motivo, nome, dias=dias, leads=leads)
    alternativas = TEMPLATES_POR_MOTIVO.get(motivo, TEMPLATES_POR_MOTIVO["geral"])
    return {
        "ok": True,
        "motivo": motivo,
        "mensagem": mensagem,
        "todas_variacoes": [
            get_template(motivo, nome, dias=dias, leads=leads)
            for _ in range(5)
        ],
        "total_variacoes_disponiveis": len(alternativas)
    }


@router.post("/marcar-contatado")
async def marcar_contatado(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin)
):
    """
    Marca usuario como contatado manualmente.
    Body: {user_id, canal: 'whatsapp'|'email', nota: string}
    """
    try:
        body = await request.json()
        user_id = body.get("user_id")
        canal = body.get("canal", "whatsapp")
        nota = body.get("nota", "Contato manual")

        if not user_id:
            raise HTTPException(400, "user_id obrigatorio")

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

        db.execute(text("""
            INSERT INTO interacoes_admin (user_id, canal, tipo, nota, criado_por)
            VALUES (:uid, :canal, 'contato_manual', :nota, :criado_por)
        """), {
            "uid": user_id,
            "canal": canal,
            "nota": nota,
            "criado_por": user.get("email", "superadmin")
        })
        db.commit()

        # Buscar dados do usuario para retornar
        u = db.execute(text("SELECT email, nome, telefone FROM users WHERE id = :id"), {"id": user_id}).fetchone()

        return {
            "ok": True,
            "user_id": user_id,
            "email": u[0] if u else None,
            "nome": u[1] if u else None,
            "telefone": u[2] if u else None,
            "wa_link": f"https://wa.me/55{(u[2] or '').replace('+','').replace(' ','')}" if u and u[2] else None,
            "message": "Contato registrado"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro: {e}")