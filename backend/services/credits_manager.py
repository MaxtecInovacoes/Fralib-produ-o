"""
Credits Manager - Sistema de Planos FraLib (Duplo Cadeado)

Lógica: créditos diários + cooldown. Ambos precisam passar.

Planos:
  trial      -> 1 site total (não renova)
  starter    -> 6 sites/dia, cooldown 60min, reset 00:00 BRT
  pro        -> 16 sites/dia, cooldown 30min, reset 00:00 BRT
  ilimitado  -> sem limite, sem cooldown
  beta       -> igual pro

Crédito só consome quando deploy funciona (chamado após sucesso).
Reset lazy: não depende de cron, verifica data no momento da checagem.
"""
from datetime import datetime, timezone, timedelta, date as date_type
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

BRT = timezone(timedelta(hours=-3))

LIMITES_DIARIOS = {"trial": 1, "starter": 6, "pro": 16, "ilimitado": 99999, "beta": 16, "free": 1}
COOLDOWNS = {"trial": 0, "starter": 3600, "pro": 1800, "ilimitado": 0, "beta": 1800, "free": 0}
PLANOS_ILIMITADOS = {'ilimitado'}

CUSTO_POR_CICLO_USD = 0.34
CUSTO_POR_EDICAO_USD = 0.05


def _hoje_brt() -> date_type:
    return datetime.now(BRT).date()


def _proximo_reset_iso() -> str:
    agora = datetime.now(BRT)
    amanha = agora.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return amanha.isoformat()


def _reset_lazy(db: Session, user_id: int) -> int:
    """Reset lazy: se mudou o dia BRT, zera sites_hoje. Retorna sites_hoje atual."""
    row = db.execute(text(
        "SELECT sites_hoje, sites_hoje_date FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()
    sites_hoje = (row[0] or 0) if row else 0
    sites_date = row[1] if row else None
    hoje = _hoje_brt()
    if sites_date is None or sites_date != hoje:
        db.execute(text(
            "UPDATE users SET sites_hoje=0, sites_hoje_date=:hoje WHERE id=:id"
        ), {"hoje": hoje.isoformat(), "id": user_id})
        db.commit()
        return 0
    return sites_hoje


def validar_permissao_pipeline(db: Session, tenant_id: int) -> dict:
    """
    Gate duplo: créditos diários + cooldown.
    Retorna dict com allowed=True/False + detalhes.
    """
    row = db.execute(text(
        "SELECT plano, plano_pago, creditos, ultimo_deploy_at FROM users WHERE id=:id"
    ), {"id": tenant_id}).fetchone()
    if not row:
        return {"allowed": False, "reason": "user_not_found", "message": "Usuário não encontrado"}

    plano = (row[0] or "trial").lower()
    plano_pago = row[1] or False
    creditos_legacy = row[2] or 0
    ultimo_deploy = row[3]

    limite = LIMITES_DIARIOS.get(plano, 1)
    cooldown_secs = COOLDOWNS.get(plano, 3600)

    # ═══ TRIAL: lógica legada (1 total, não diário) ═══
    if plano in ("trial", "free") and not plano_pago:
        if creditos_legacy <= 0:
            return {
                "allowed": False, "reason": "limite_plano",
                "message": "Você já usou seu site gratuito.",
                "action": "upgrade", "plano": plano,
                "upgrade_url": "/planos"
            }
        return {"allowed": True, "creditos_restantes": creditos_legacy, "limite_diario": 1, "plano": plano}

    # ═══ ILIMITADO: sem restrição ═══
    if plano in PLANOS_ILIMITADOS:
        return {"allowed": True, "creditos_restantes": 99999, "limite_diario": 99999, "plano": plano}

    # ═══ CRÉDITOS DIÁRIOS (starter/pro/beta) ═══
    sites_hoje = _reset_lazy(db, tenant_id)
    restantes = limite - sites_hoje

    if restantes <= 0:
        return {
            "allowed": False, "reason": "creditos_esgotados",
            "message": f"Seus {limite} sites de hoje acabaram.",
            "creditos_usados": sites_hoje, "limite_diario": limite,
            "reset_at": _proximo_reset_iso(),
            "plano": plano,
            "action": "upgrade_or_wait",
            "upsell": _get_upsell(plano)
        }

    # ═══ COOLDOWN ═══
    if cooldown_secs > 0 and ultimo_deploy:
        agora = datetime.now(BRT)
        try:
            ult = ultimo_deploy if ultimo_deploy.tzinfo else ultimo_deploy.replace(tzinfo=timezone.utc)
            ult_brt = ult.astimezone(BRT)
            elapsed = (agora - ult_brt).total_seconds()
            restante_cd = cooldown_secs - elapsed
            if restante_cd > 0:
                return {
                    "allowed": False, "reason": "cooldown",
                    "message": f"Aguarde {int(restante_cd//60)}min {int(restante_cd%60)}s antes de rodar outro pipeline.",
                    "cooldown_restante_seg": int(restante_cd),
                    "cooldown_total_seg": cooldown_secs,
                    "proximo_em": (agora + timedelta(seconds=restante_cd)).isoformat(),
                    "creditos_restantes": restantes, "limite_diario": limite,
                    "plano": plano,
                    "leads_na_fila": _count_fila(db, tenant_id),
                    "auto_run": _count_fila(db, tenant_id) > 0,
                    "action": "wait_or_upgrade",
                    "upsell": _get_upsell(plano)
                }
        except Exception:
            pass

    # ═══ LIBERADO ═══
    return {
        "allowed": True,
        "creditos_restantes": restantes,
        "limite_diario": limite,
        "plano": plano
    }


def consumir_credito_diario(db: Session, tenant_id: int, lead_nome: str = "") -> bool:
    """Consome 1 crédito diário + atualiza ultimo_deploy_at. Chamar APÓS deploy OK."""
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    plano = (row[0] if row else "trial").lower()

    agora = datetime.now(BRT)

    if plano in ("trial", "free"):
        db.execute(text(
            "UPDATE users SET creditos=GREATEST(creditos-1,0), sites_used=COALESCE(sites_used,0)+1, ultimo_deploy_at=:ts WHERE id=:id"
        ), {"ts": agora, "id": tenant_id})
    else:
        db.execute(text(
            "UPDATE users SET sites_hoje=COALESCE(sites_hoje,0)+1, sites_used=COALESCE(sites_used,0)+1, ultimo_deploy_at=:ts WHERE id=:id"
        ), {"ts": agora, "id": tenant_id})
    db.commit()

    _registrar_transacao(db, tenant_id, "ciclo",
        tokens_consumidos=1, custo_usd=CUSTO_POR_CICLO_USD,
        descricao=f"Pipeline concluido: {lead_nome}")
    return True


# ═══ Funções legadas (mantidas pra compatibilidade) ═══

def get_user_tokens(db: Session, user_id: int) -> dict:
    """Retorna saldo e info de tokens do usuario."""
    row = db.execute(text(
        "SELECT id, email, plano, creditos, creditos_max, plano_pago, status, "
        "trial_expires_at, last_reset_date, sites_used, sites_hoje, ultimo_deploy_at FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()
    if not row:
        return {"erro": "Usuario nao encontrado"}
    plano = (row[2] or "trial").lower()
    sites_hoje = row[10] or 0
    limite = LIMITES_DIARIOS.get(plano, 1)
    return {
        "user_id": row[0], "email": row[1], "plano": plano,
        "creditos": row[3] or 0, "creditos_max": row[4] or 1,
        "plano_pago": row[5] or False, "status": row[6] or "trial",
        "trial_expires_at": row[7], "last_reset_date": row[8],
        "sites_used": row[9] or 0,
        "sites_hoje": sites_hoje, "limite_diario": limite,
        "creditos_restantes_hoje": max(0, limite - sites_hoje),
        "ultimo_deploy_at": row[11],
    }


def verificar_pode_executar(db: Session, user_id: int) -> dict:
    """Wrapper legado — redireciona pra validar_permissao_pipeline."""
    perm = validar_permissao_pipeline(db, user_id)
    if perm["allowed"]:
        return {"pode": True, "motivo": "", "plano": perm.get("plano", "trial"),
                "creditos_restantes": perm.get("creditos_restantes", -1), "upgrade_url": "/planos"}
    return {
        "pode": False,
        "motivo": perm.get("message", "Bloqueado"),
        "plano": perm.get("plano", "trial"),
        "creditos_restantes": perm.get("creditos_restantes", 0),
        "upgrade_url": "/planos",
        "detail": perm
    }


def consume_tokens(db: Session, user_id: int, quantidade: int = 1,
                   descricao: str = "Ciclo pipeline") -> bool:
    """Wrapper legado — redireciona pra consumir_credito_diario."""
    return consumir_credito_diario(db, user_id, descricao)


def consume_edicao(db: Session, user_id: int) -> bool:
    """Desconta 1 token de edicao de site (apenas pro)."""
    row = db.execute(text(
        "SELECT creditos, plano FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()
    if not row:
        return False
    creditos, plano = row
    plano = plano or "trial"
    if plano not in ("pro", "beta"):
        return False
    if creditos < 1:
        return False
    db.execute(text("UPDATE users SET creditos=creditos-1 WHERE id=:id"), {"id": user_id})
    db.commit()
    _registrar_transacao(db, user_id, "edicao", tokens_consumidos=1,
        custo_usd=CUSTO_POR_EDICAO_USD, descricao="Edicao de site via prompt")
    return True


def ativar_plano(db: Session, user_id: int, plano: str,
                 stripe_customer_id: str = None,
                 stripe_subscription_id: str = None) -> bool:
    """Ativa plano apos pagamento confirmado pelo Stripe."""
    expira = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
    db.execute(text("""
        UPDATE users SET
            plano = :plano, plan = :plano, plano_pago = true, status = 'ativo',
            creditos = 999, creditos_max = 999,
            sites_hoje = 0, sites_hoje_date = :hoje,
            plan_expires_at = :expira,
            stripe_customer_id = COALESCE(:cid, stripe_customer_id),
            stripe_subscription_id = COALESCE(:sid, stripe_subscription_id)
        WHERE id = :user_id
    """), {
        "plano": plano, "expira": expira.isoformat(),
        "cid": stripe_customer_id, "sid": stripe_subscription_id,
        "user_id": user_id, "hoje": _hoje_brt().isoformat()
    })
    db.commit()
    _registrar_transacao(db, user_id, "bonus", tokens_consumidos=0, custo_usd=0,
        descricao=f"Plano {plano} ativado: {LIMITES_DIARIOS.get(plano, '?')} sites/dia")
    return True


# ═══ Helpers internos ═══

def _count_fila(db: Session, tenant_id: int) -> int:
    try:
        return db.execute(text(
            "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='capturado'"
        ), {"uid": tenant_id}).scalar() or 0
    except Exception:
        return 0


def _get_upsell(plano: str) -> Optional[str]:
    upsells = {
        "starter": "Pro: 16 sites/dia + cooldown 30min",
        "pro": "Ilimitado: sem limite + sem espera",
        "beta": "Ilimitado: sem limite + sem espera",
    }
    return upsells.get(plano)


def _registrar_transacao(db: Session, user_id: int, tipo: str,
                          tokens_consumidos: int = 0,
                          custo_usd: float = 0,
                          descricao: str = "") -> None:
    """Registra transacao no historico."""
    try:
        # Guarda: tabela token_transactions pode nao existir ainda
        db.execute(text("SELECT to_regclass('public.token_transactions')"))
        has_table = db.fetchone()[0] is not None
    except Exception:
        db.rollback()
        has_table = False
    if not has_table:
        return
    try:
        db.execute(text("""
            INSERT INTO token_transactions (user_id, tipo, tokens_consumidos, custo_usd, descricao)
            VALUES (:uid, :tipo, :tokens, :custo, :desc)
        """), {
            "uid": user_id, "tipo": tipo,
            "tokens": tokens_consumidos, "custo": custo_usd, "desc": descricao
        })
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Credits] Erro ao registrar transacao: {e}")


def deduzir_creditos_por_pipeline(db: Session, tenant_id: int, run_id: str) -> dict:
    """Desconta crédito do pipeline com base no custo real do trace."""
    # Buscar custo real do trace
    trace_row = db.execute(text(
        "SELECT custo_total_usd FROM pipeline_traces WHERE run_id = :rid ORDER BY created_at DESC LIMIT 1"
    ), {"rid": run_id}).fetchone()

    custo_usd = float(trace_row[0]) if trace_row and trace_row[0] else CUSTO_POR_CICLO_USD

    # Consumir crédito diário
    ok = consumir_credito_diario(db, tenant_id, lead_nome=f"run_id={run_id}")

    # Registrar transação com custo real
    _registrar_transacao(
        db, tenant_id, "pipeline",
        tokens_consumidos=1,
        custo_usd=custo_usd,
        descricao=f"Pipeline concluido: run_id={run_id}"
    )

    return {
        "ok": ok,
        "deduzidos": 1 if ok else 0,
        "custo_usd": custo_usd,
    }
