"""
Credits Manager - Sistema de Tokens/Ciclos por Plano
Usa PostgreSQL via SQLAlchemy (mesmo banco do sistema principal)

Planos:
  trial   -> 1 ciclo total (nao renova)
  starter -> 5 ciclos/semana (renova toda segunda)
  pro     -> 20 ciclos/semana (renova toda segunda)
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

# Mapeamento plano -> ciclos por semana
PLANO_CICLOS = {
    'trial':   1,
    'starter': 5,
    'pro':     20,
    'beta':    20,  # beta = pro
    'free':    1,
}

# Custo estimado por ciclo em USD
CUSTO_POR_CICLO_USD = 0.34

# Custo por edicao de site em USD
CUSTO_POR_EDICAO_USD = 0.05


def _ultima_segunda() -> date:
    """Retorna a data da ultima segunda-feira (ou hoje se for segunda)."""
    hoje = date.today()
    return hoje - timedelta(days=hoje.weekday())


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


def reset_semanal_se_necessario(db: Session, user_id: int) -> bool:
    """
    Verifica se precisa resetar creditos (toda segunda-feira).
    Retorna True se resetou.
    """
    row = db.execute(text(
        "SELECT plano, creditos_max, plano_pago, last_reset_date FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()

    if not row:
        return False

    plano, creditos_max, plano_pago, last_reset_date = row
    plano = plano or "trial"

    # Trial nao renova
    if plano == "trial" or not plano_pago:
        return False

    ultima_segunda = _ultima_segunda()

    # Verificar se ja resetou essa semana
    if last_reset_date is not None:
        if isinstance(last_reset_date, str):
            try:
                last_reset_date = date.fromisoformat(last_reset_date[:10])
            except Exception:
                last_reset_date = None

    if last_reset_date is not None and last_reset_date >= ultima_segunda:
        return False  # Ja resetou essa semana

    # Resetar creditos para o maximo do plano
    ciclos_plano = PLANO_CICLOS.get(plano, 1)
    db.execute(text(
        "UPDATE users SET creditos=:ciclos, last_reset_date=:hoje WHERE id=:id"
    ), {"ciclos": ciclos_plano, "hoje": ultima_segunda, "id": user_id})
    db.commit()

    # Registrar reset no historico
    _registrar_transacao(db, user_id, "reset",
        tokens_consumidos=0,
        custo_usd=0,
        descricao=f"Reset semanal: {ciclos_plano} ciclos restaurados ({plano})")
    return True


def verificar_pode_executar(db: Session, user_id: int) -> dict:
    """
    Verifica se usuario pode executar o pipeline.
    Aplica reset semanal automaticamente se necessario.

    Returns:
        {
            'pode': bool,
            'motivo': str,
            'plano': str,
            'creditos_restantes': int,
            'reset_em': str (data da proxima segunda),
            'upgrade_url': str
        }
    """
    # Aplicar reset semanal se necessario
    reset_semanal_se_necessario(db, user_id)

    # Buscar estado atual
    info = get_user_tokens(db, user_id)
    if "erro" in info:
        return {"pode": False, "motivo": "Usuario nao encontrado", "plano": "trial",
                "creditos_restantes": 0, "reset_em": "", "upgrade_url": "/planos"}

    plano = info["plano"]
    creditos = info["creditos"]
    plano_pago = info["plano_pago"]
    status = info["status"]

    # Calcular proxima segunda
    hoje = date.today()
    dias_ate_segunda = (7 - hoje.weekday()) % 7 or 7
    proxima_segunda = hoje + timedelta(days=dias_ate_segunda)
    reset_em = proxima_segunda.strftime("%d/%m/%Y")

    # Verificar trial expirado
    if plano == "trial" and info.get("trial_expires_at"):
        try:
            exp = date.fromisoformat(str(info["trial_expires_at"])[:10])
            if date.today() > exp:
                return {
                    "pode": False,
                    "motivo": "Seu periodo trial expirou. Assine um plano para continuar.",
                    "plano": plano,
                    "creditos_restantes": 0,
                    "reset_em": reset_em,
                    "upgrade_url": "/planos"
                }
        except Exception:
            pass

    # Verificar creditos
    if creditos <= 0:
        if plano == "trial":
            motivo = "Voce usou seu ciclo trial gratuito. Assine um plano para continuar gerando sites e atendendo clientes no automatico."
        else:
            motivo = f"Voce usou todos os {info['creditos_max']} ciclos desta semana. Seus creditos renovam na segunda-feira ({reset_em})."

        return {
            "pode": False,
            "motivo": motivo,
            "plano": plano,
            "creditos_restantes": 0,
            "reset_em": reset_em,
            "upgrade_url": "/planos"
        }

    return {
        "pode": True,
        "motivo": "",
        "plano": plano,
        "creditos_restantes": creditos,
        "reset_em": reset_em,
        "upgrade_url": "/planos"
    }


def consume_tokens(db: Session, user_id: int, quantidade: int = 1,
                   descricao: str = "Ciclo pipeline") -> bool:
    """
    Desconta tokens do usuario.
    Retorna True se sucesso, False se saldo insuficiente.
    """
    row = db.execute(text(
        "SELECT creditos FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()

    if not row or row[0] < quantidade:
        return False

    db.execute(text(
        "UPDATE users SET creditos=creditos-:qtd, sites_used=sites_used+:qtd WHERE id=:id"
    ), {"qtd": quantidade, "id": user_id})
    db.commit()

    custo = CUSTO_POR_CICLO_USD * quantidade
    _registrar_transacao(db, user_id, "ciclo",
        tokens_consumidos=quantidade,
        custo_usd=custo,
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
    Atualiza todos os campos relevantes no PostgreSQL.
    """
    from datetime import datetime
    ciclos = PLANO_CICLOS.get(plano, 1)
    ultima_segunda = _ultima_segunda()
    expira = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)

    db.execute(text("""
        UPDATE users SET
            plano = :plano,
            plan = :plano,
            plano_pago = true,
            status = 'ativo',
            creditos = :ciclos,
            creditos_max = :ciclos,
            last_reset_date = :reset,
            plan_expires_at = :expira,
            stripe_customer_id = COALESCE(:cid, stripe_customer_id),
            stripe_subscription_id = COALESCE(:sid, stripe_subscription_id)
        WHERE id = :user_id
    """), {
        "plano": plano,
        "ciclos": ciclos,
        "reset": ultima_segunda,
        "expira": expira.isoformat(),
        "cid": stripe_customer_id,
        "sid": stripe_subscription_id,
        "user_id": user_id
    })
    db.commit()

    _registrar_transacao(db, user_id, "bonus",
        tokens_consumidos=0,
        custo_usd=0,
        descricao=f"Plano {plano} ativado: {ciclos} ciclos/semana")
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
