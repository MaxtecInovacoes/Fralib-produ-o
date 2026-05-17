"""
Credits Manager - Sistema de Planos FraLib

Planos:
  trial      -> 1 site gratis (nao renova)
  starter    -> sites ilimitados, cooldown 60min, 200 interacoes SDR/mes
  pro        -> sites ilimitados, cooldown 30min, SDR ilimitado (BYOK)
  ilimitado  -> sem cooldown, sem fila, SDR ilimitado
  avulso     -> pacotes extras (roda imediato, sem cooldown)

Cooldown e controlado em pipeline_endpoints.py via leads.processado_em.
Este modulo gerencia: verificacao de permissao, consumo de creditos (trial/avulso),
ativacao de plano, e registro de transacoes.
"""
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

# Planos que permitem pipeline ilimitado (controlado por cooldown, nao creditos)
PLANOS_ILIMITADOS = {'starter', 'pro', 'ilimitado', 'beta'}

# Custo estimado por ciclo em USD (pra tracking interno)
CUSTO_POR_CICLO_USD = 0.34
CUSTO_POR_EDICAO_USD = 0.05


def get_user_tokens(db: Session, user_id: int) -> dict:
    """Retorna saldo e info de tokens do usuario."""
    row = db.execute(text(
        "SELECT id, email, plano, creditos, creditos_max, plano_pago, status, "
        "trial_expires_at, last_reset_date, sites_used FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()

    if not row:
        return {"erro": "Usuario nao encontrado"}

    return {
        "user_id": row[0],
        "email": row[1],
        "plano": row[2] or "trial",
        "creditos": row[3] or 0,
        "creditos_max": row[4] or 1,
        "plano_pago": row[5] or False,
        "status": row[6] or "trial",
        "trial_expires_at": row[7],
        "last_reset_date": row[8],
        "sites_used": row[9] or 0,
    }


def verificar_pode_executar(db: Session, user_id: int) -> dict:
    """
    Verifica se usuario pode executar o pipeline.

    Logica:
      - Planos pagos (starter/pro/ilimitado): SEMPRE pode (cooldown e separado)
      - Trial: pode se creditos > 0
      - Trial expirado: bloqueado
      - Avulso: pode se sites_avulso > 0 (TODO: implementar campo)
    """
    info = get_user_tokens(db, user_id)
    if "erro" in info:
        return {"pode": False, "motivo": "Usuario nao encontrado", "plano": "trial",
                "creditos_restantes": 0, "upgrade_url": "/planos"}

    plano = info["plano"]
    creditos = info["creditos"]
    plano_pago = info["plano_pago"]

    # Planos pagos: sempre pode (cooldown controla frequencia)
    if plano in PLANOS_ILIMITADOS and plano_pago:
        return {
            "pode": True,
            "motivo": "",
            "plano": plano,
            "creditos_restantes": -1,  # ilimitado
            "upgrade_url": "/planos"
        }

    # Trial expirado
    if plano == "trial" and info.get("trial_expires_at"):
        try:
            exp = date.fromisoformat(str(info["trial_expires_at"])[:10])
            if date.today() > exp:
                return {
                    "pode": False,
                    "motivo": "Seu periodo trial expirou. Assine um plano para continuar.",
                    "plano": plano,
                    "creditos_restantes": 0,
                    "upgrade_url": "/planos"
                }
        except Exception:
            pass

    # Trial/free: verificar creditos
    if creditos <= 0:
        return {
            "pode": False,
            "motivo": "Voce usou seu site gratuito! Assine um plano para continuar gerando sites e atendendo clientes no automatico.",
            "plano": plano,
            "creditos_restantes": 0,
            "upgrade_url": "/planos"
        }

    return {
        "pode": True,
        "motivo": "",
        "plano": plano,
        "creditos_restantes": creditos,
        "upgrade_url": "/planos"
    }


def consume_tokens(db: Session, user_id: int, quantidade: int = 1,
                   descricao: str = "Ciclo pipeline") -> bool:
    """
    Desconta tokens do usuario (apenas trial/free).
    Planos pagos nao descontam creditos (sao ilimitados com cooldown).
    Retorna True se sucesso ou plano ilimitado, False se saldo insuficiente.
    """
    row = db.execute(text(
        "SELECT creditos, plano, plano_pago FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()

    if not row:
        return False

    creditos, plano, plano_pago = row
    plano = plano or "trial"

    # Planos pagos: nao desconta creditos, apenas incrementa sites_used
    if plano in PLANOS_ILIMITADOS and plano_pago:
        db.execute(text(
            "UPDATE users SET sites_used=sites_used+:qtd WHERE id=:id"
        ), {"qtd": quantidade, "id": user_id})
        db.commit()
        _registrar_transacao(db, user_id, "ciclo",
            tokens_consumidos=0,
            custo_usd=CUSTO_POR_CICLO_USD * quantidade,
            descricao=descricao)
        return True

    # Trial/free: desconta creditos
    if creditos < quantidade:
        return False

    db.execute(text(
        "UPDATE users SET creditos=creditos-:qtd, sites_used=sites_used+:qtd WHERE id=:id"
    ), {"qtd": quantidade, "id": user_id})
    db.commit()

    _registrar_transacao(db, user_id, "ciclo",
        tokens_consumidos=quantidade,
        custo_usd=CUSTO_POR_CICLO_USD * quantidade,
        descricao=descricao)
    return True


def consume_edicao(db: Session, user_id: int) -> bool:
    """
    Desconta 1 token de edicao de site.
    Edicao custa menos que um ciclo completo.
    """
    row = db.execute(text(
        "SELECT creditos, plano FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()

    if not row:
        return False

    creditos, plano = row
    plano = plano or "trial"

    # Apenas plano pro pode editar
    if plano not in ("pro", "beta"):
        return False

    if creditos < 1:
        return False

    db.execute(text(
        "UPDATE users SET creditos=creditos-1 WHERE id=:id"
    ), {"id": user_id})
    db.commit()

    _registrar_transacao(db, user_id, "edicao",
        tokens_consumidos=1,
        custo_usd=CUSTO_POR_EDICAO_USD,
        descricao="Edicao de site via prompt")
    return True


def ativar_plano(db: Session, user_id: int, plano: str,
                 stripe_customer_id: str = None,
                 stripe_subscription_id: str = None) -> bool:
    """
    Ativa plano apos pagamento confirmado pelo Stripe.
    Planos pagos = sites ilimitados (cooldown controla frequencia).
    """
    expira = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)

    db.execute(text("""
        UPDATE users SET
            plano = :plano,
            plan = :plano,
            plano_pago = true,
            status = 'ativo',
            creditos = 999,
            creditos_max = 999,
            plan_expires_at = :expira,
            stripe_customer_id = COALESCE(:cid, stripe_customer_id),
            stripe_subscription_id = COALESCE(:sid, stripe_subscription_id)
        WHERE id = :user_id
    """), {
        "plano": plano,
        "expira": expira.isoformat(),
        "cid": stripe_customer_id,
        "sid": stripe_subscription_id,
        "user_id": user_id
    })
    db.commit()

    _registrar_transacao(db, user_id, "bonus",
        tokens_consumidos=0,
        custo_usd=0,
        descricao=f"Plano {plano} ativado: sites ilimitados com cooldown")
    return True


def _registrar_transacao(db: Session, user_id: int, tipo: str,
                          tokens_consumidos: int = 0,
                          custo_usd: float = 0,
                          descricao: str = "") -> None:
    """Registra transacao no historico."""
    try:
        db.execute(text("""
            INSERT INTO token_transactions (user_id, tipo, tokens_consumidos, custo_usd, descricao)
            VALUES (:uid, :tipo, :tokens, :custo, :desc)
        """), {
            "uid": user_id,
            "tipo": tipo,
            "tokens": tokens_consumidos,
            "custo": custo_usd,
            "desc": descricao
        })
        db.commit()
    except Exception as e:
        print(f"[Credits] Erro ao registrar transacao: {e}")
