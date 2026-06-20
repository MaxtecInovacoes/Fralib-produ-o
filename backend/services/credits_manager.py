"""
Credits Manager - Sistema de Planos FraLib.

Planos efetivos:
  trial      -> 1 pipeline completa total, com SDR durante o trial ativo
  starter    -> 180 creditos/mes, cooldown 60min, sem SDR
  pro        -> 360 creditos/mes, cooldown 30min, com SDR
  agency     -> R$497/mes, sem limite/cooldown, com SDR
  ilimitado  -> legado sem limite/cooldown, com SDR
  beta       -> legado equivalente a pro

Credito pago consome quando deploy funciona; trial consome so apos site pronto + envio SDR confirmado.
Reset lazy mensal: nao depende de cron, verifica mes no momento da checagem.
"""
from datetime import datetime, timezone, timedelta, date as date_type
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from backend.domain.plans import (
    COOLDOWNS,
    LIMITES_DIARIOS,
    PLAN_CREDITOS_PADRAO,
    PLAN_LIMITS,
    PLANOS_COM_SDR,
    PLANOS_ILIMITADOS,
    PLANOS_TRIAL,
)

BRT = timezone(timedelta(hours=-3))
STATUS_BLOQUEIO_SDR = {"bloqueado", "suspenso", "cancelado", "inadimplente", "desativado"}

CUSTO_POR_CICLO_USD = 0.34
CUSTO_POR_EDICAO_USD = 0.05


def _hoje_brt() -> date_type:
    return datetime.now(BRT).date()


def _proximo_reset_iso() -> str:
    agora = datetime.now(BRT)
    primeiro = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    proximo = (primeiro + timedelta(days=32)).replace(day=1)
    return proximo.isoformat()


def _mes_ref() -> str:
    return datetime.now(BRT).strftime("%Y-%m")


def _parse_mes_ref(value) -> Optional[str]:
    if not value:
        return None
    try:
        if isinstance(value, str):
            return value[:7]
        return value.strftime("%Y-%m")
    except Exception:
        return None


def _parse_datetime(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def trial_ativo(trial_expires_at) -> bool:
    """Trial sem expiracao explicita continua valido para tenants antigos."""
    expires_at = _parse_datetime(trial_expires_at)
    if not expires_at:
        return True
    return expires_at >= datetime.utcnow()


def plano_tem_sdr(plano: str, status: str = "", trial_expires_at=None) -> bool:
    plano_norm = (plano or "trial").lower()
    status_norm = (status or "").lower()
    if status_norm in STATUS_BLOQUEIO_SDR:
        return False
    if plano_norm == "trial":
        return trial_ativo(trial_expires_at)
    return plano_norm in PLANOS_COM_SDR


def trial_credit_waits_for_sdr_delivery(db: Session, tenant_id: int) -> bool:
    """Trial/free so deve consumir o unico credito quando o WhatsApp sair de verdade."""
    row = db.execute(
        text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()
    plano = ((row[0] if row else "trial") or "trial").lower()
    status = ((row[1] if row else "") or "").lower()
    trial_expires_at = row[2] if row else None
    return plano in PLANOS_TRIAL and plano_tem_sdr(plano, status, trial_expires_at)


def _count_trial_delivery_pending(db: Session, tenant_id: int) -> int:
    try:
        return db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM leads
                WHERE user_id=:uid
                  AND status IN ('concluido','deployed')
                  AND COALESCE(sdr_stage,'') IN ('pending_sdr_send','pendente_wpp')
                """
            ),
            {"uid": tenant_id},
        ).scalar() or 0
    except Exception:
        return 0


def _reset_mensal_lazy(db: Session, user_id: int, plano: str, creditos: int) -> int:
    """Recarrega creditos de planos pagos quando vira o mes BRT."""
    row = db.execute(
        text("SELECT last_reset_date FROM users WHERE id=:id"),
        {"id": user_id},
    ).fetchone()
    mes_atual = _mes_ref()
    mes_reset = _parse_mes_ref(row[0] if row else None)
    if mes_reset != mes_atual:
        limite = PLAN_CREDITOS_PADRAO.get(plano, 1)
        hoje = _hoje_brt().isoformat()
        db.execute(
            text(
                """
                UPDATE users
                SET creditos=:limite, creditos_max=:limite, last_reset_date=:hoje,
                    sites_hoje=0, sites_hoje_date=:hoje
                WHERE id=:id
                """
            ),
            {"limite": limite, "hoje": hoje, "id": user_id},
        )
        db.commit()
        return limite
    return creditos


def validar_permissao_pipeline(db: Session, tenant_id: int) -> dict:
    """Gate: status + creditos do plano + cooldown."""
    row = db.execute(
        text(
            "SELECT plano, plano_pago, creditos, ultimo_deploy_at, status "
            "FROM users WHERE id=:id"
        ),
        {"id": tenant_id},
    ).fetchone()
    if not row:
        return {"allowed": False, "reason": "user_not_found", "message": "Usuario nao encontrado"}

    plano = (row[0] or "trial").lower()
    plano_pago = row[1] or False
    creditos = row[2] or 0
    ultimo_deploy = row[3]
    status = (row[4] or "").lower()

    if status in {"bloqueado", "suspenso", "cancelado", "inadimplente"}:
        return {
            "allowed": False,
            "reason": "status_bloqueado",
            "message": "Conta sem permissao ativa para rodar pipeline.",
            "plano": plano,
            "upgrade_url": "/planos",
        }

    limite = PLAN_LIMITS.get(plano, 1)
    cooldown_secs = COOLDOWNS.get(plano, 3600)

    if plano in ("trial", "free") and not plano_pago:
        pending_delivery = _count_trial_delivery_pending(db, tenant_id)
        if pending_delivery > 0:
            return {
                "allowed": False,
                "reason": "trial_delivery_pending",
                "message": "Seu primeiro ciclo gratuito ainda esta finalizando o envio pelo WhatsApp. Aguarde a entrega ou reprocessamento.",
                "plano": plano,
                "pending_delivery": pending_delivery,
            }
        if creditos <= 0:
            return {
                "allowed": False,
                "reason": "limite_plano",
                "message": "Voce ja usou seu site gratuito.",
                "action": "upgrade",
                "plano": plano,
                "upgrade_url": "/planos",
            }
        return {
            "allowed": True,
            "creditos_restantes": creditos,
            "limite_mensal": 1,
            "limite_diario": 1,
            "plano": plano,
        }

    if plano in PLANOS_ILIMITADOS:
        return {
            "allowed": True,
            "creditos_restantes": 99999,
            "limite_mensal": 99999,
            "limite_diario": 99999,
            "plano": plano,
        }

    creditos_mes = _reset_mensal_lazy(db, tenant_id, plano, creditos)
    restantes = min(creditos_mes, limite)
    if restantes <= 0:
        return {
            "allowed": False,
            "reason": "creditos_esgotados",
            "message": f"Seus {limite} creditos mensais acabaram.",
            "creditos_usados": max(0, limite - creditos_mes),
            "limite_mensal": limite,
            "limite_diario": limite,
            "reset_at": _proximo_reset_iso(),
            "plano": plano,
            "action": "upgrade_or_wait",
            "upsell": _get_upsell(plano),
        }

    if cooldown_secs > 0 and ultimo_deploy:
        agora = datetime.now(BRT)
        try:
            ult = ultimo_deploy if ultimo_deploy.tzinfo else ultimo_deploy.replace(tzinfo=timezone.utc)
            ult_brt = ult.astimezone(BRT)
            elapsed = (agora - ult_brt).total_seconds()
            restante_cd = cooldown_secs - elapsed
            if restante_cd > 0:
                fila = _count_fila(db, tenant_id)
                return {
                    "allowed": False,
                    "reason": "cooldown",
                    "message": f"Aguarde {int(restante_cd//60)}min {int(restante_cd%60)}s antes de rodar outro pipeline.",
                    "cooldown_restante_seg": int(restante_cd),
                    "cooldown_total_seg": cooldown_secs,
                    "proximo_em": (agora + timedelta(seconds=restante_cd)).isoformat(),
                    "creditos_restantes": restantes,
                    "limite_mensal": limite,
                    "limite_diario": limite,
                    "plano": plano,
                    "leads_na_fila": fila,
                    "auto_run": fila > 0,
                    "action": "wait_or_upgrade",
                    "upsell": _get_upsell(plano),
                }
        except Exception:
            pass

    return {
        "allowed": True,
        "creditos_restantes": restantes,
        "limite_mensal": limite,
        "limite_diario": limite,
        "plano": plano,
    }


def consumir_credito_diario(db: Session, tenant_id: int, lead_nome: str = "") -> bool:
    """Consome 1 credito + atualiza ultimo_deploy_at. Chamar apos deploy OK."""
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    plano = (row[0] if row else "trial").lower()
    agora = datetime.now(BRT)

    if plano in PLANOS_ILIMITADOS:
        db.execute(
            text("UPDATE users SET sites_used=COALESCE(sites_used,0)+1, ultimo_deploy_at=:ts WHERE id=:id"),
            {"ts": agora, "id": tenant_id},
        )
    else:
        db.execute(
            text(
                "UPDATE users SET creditos=GREATEST(creditos-1,0), "
                "sites_used=COALESCE(sites_used,0)+1, ultimo_deploy_at=:ts WHERE id=:id"
            ),
            {"ts": agora, "id": tenant_id},
        )
    db.commit()

    _registrar_transacao(
        db,
        tenant_id,
        "ciclo",
        tokens_consumidos=1,
        custo_usd=CUSTO_POR_CICLO_USD,
        descricao=f"Pipeline concluido: {lead_nome}",
    )
    return True


def consumir_credito_trial_entregue(db: Session, tenant_id: int, lead_nome: str = "") -> bool:
    """Consome o trial idempotentemente depois do envio WhatsApp confirmado."""
    row = db.execute(
        text("SELECT plano, status, trial_expires_at, creditos FROM users WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()
    if not row:
        return False
    plano = ((row[0] or "trial")).lower()
    status = (row[1] or "").lower()
    creditos = row[3] or 0
    if plano not in PLANOS_TRIAL or not plano_tem_sdr(plano, status, row[2]) or creditos <= 0:
        return False
    return consumir_credito_diario(db, tenant_id, lead_nome)


def get_user_tokens(db: Session, user_id: int) -> dict:
    """Retorna saldo e info de tokens do usuario."""
    row = db.execute(
        text(
            "SELECT id, email, plano, creditos, creditos_max, plano_pago, status, "
            "trial_expires_at, last_reset_date, sites_used, sites_hoje, ultimo_deploy_at FROM users WHERE id=:id"
        ),
        {"id": user_id},
    ).fetchone()
    if not row:
        return {"erro": "Usuario nao encontrado"}
    plano = (row[2] or "trial").lower()
    limite = PLAN_LIMITS.get(plano, 1)
    creditos = 99999 if plano in PLANOS_ILIMITADOS else (row[3] or 0)
    return {
        "user_id": row[0],
        "email": row[1],
        "plano": plano,
        "creditos": creditos,
        "creditos_max": row[4] or 1,
        "plano_pago": row[5] or False,
        "status": row[6] or "trial",
        "trial_expires_at": row[7],
        "last_reset_date": row[8],
        "sites_used": row[9] or 0,
        "sites_hoje": row[10] or 0,
        "limite_diario": limite,
        "limite_mensal": limite,
        "creditos_restantes_hoje": max(0, creditos),
        "creditos_restantes_mes": max(0, creditos),
        "ultimo_deploy_at": row[11],
    }


def verificar_pode_executar(db: Session, user_id: int) -> dict:
    """Wrapper legado - redireciona pra validar_permissao_pipeline."""
    perm = validar_permissao_pipeline(db, user_id)
    if perm["allowed"]:
        return {
            "pode": True,
            "motivo": "",
            "plano": perm.get("plano", "trial"),
            "creditos_restantes": perm.get("creditos_restantes", -1),
            "upgrade_url": "/planos",
        }
    return {
        "pode": False,
        "motivo": perm.get("message", "Bloqueado"),
        "plano": perm.get("plano", "trial"),
        "creditos_restantes": perm.get("creditos_restantes", 0),
        "upgrade_url": "/planos",
        "detail": perm,
    }


def consume_tokens(db: Session, user_id: int, quantidade: int = 1, descricao: str = "Ciclo pipeline") -> bool:
    """Wrapper legado - redireciona pra consumir_credito_diario."""
    return consumir_credito_diario(db, user_id, descricao)


def consume_edicao(db: Session, user_id: int) -> bool:
    """Desconta 1 token de edicao de site para planos com edicao."""
    row = db.execute(text("SELECT creditos, plano FROM users WHERE id=:id"), {"id": user_id}).fetchone()
    if not row:
        return False
    creditos, plano = row
    plano = (plano or "trial").lower()
    if plano not in ("pro", "beta", "ilimitado", "agency"):
        return False
    if plano in PLANOS_ILIMITADOS:
        _registrar_transacao(
            db,
            user_id,
            "edicao",
            tokens_consumidos=0,
            custo_usd=CUSTO_POR_EDICAO_USD,
            descricao="Edicao de site via prompt",
        )
        return True
    if creditos < 1:
        return False
    db.execute(text("UPDATE users SET creditos=creditos-1 WHERE id=:id"), {"id": user_id})
    db.commit()
    _registrar_transacao(
        db,
        user_id,
        "edicao",
        tokens_consumidos=1,
        custo_usd=CUSTO_POR_EDICAO_USD,
        descricao="Edicao de site via prompt",
    )
    return True


def ativar_plano(
    db: Session,
    user_id: int,
    plano: str,
    provider_customer_id: str = None,
    provider_subscription_id: str = None,
) -> bool:
    """Ativa plano apos pagamento confirmado pelo provedor de billing."""
    plano = (plano or "starter").lower()
    expira = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
    creditos_plano = PLAN_CREDITOS_PADRAO.get(plano, 1)
    hoje = _hoje_brt().isoformat()
    db.execute(
        text(
            """
            UPDATE users SET
                plano = :plano, plan = :plano, plano_pago = true, status = 'ativo',
                creditos = :creditos, creditos_max = :creditos,
                sites_hoje = 0, sites_hoje_date = :hoje, last_reset_date = :hoje,
                plan_expires_at = :expira,
                payment_provider = 'mercadopago',
                mercadopago_payer_id = COALESCE(:cid, mercadopago_payer_id),
                mercadopago_subscription_id = COALESCE(:sid, mercadopago_subscription_id)
            WHERE id = :user_id
            """
        ),
        {
            "plano": plano,
            "expira": expira.isoformat(),
            "creditos": creditos_plano,
            "cid": provider_customer_id,
            "sid": provider_subscription_id,
            "user_id": user_id,
            "hoje": hoje,
        },
    )
    db.commit()
    _registrar_transacao(
        db,
        user_id,
        "bonus",
        tokens_consumidos=0,
        custo_usd=0,
        descricao=f"Plano {plano} ativado: {PLAN_LIMITS.get(plano, '?')} creditos/mes",
    )
    return True


def _count_fila(db: Session, tenant_id: int) -> int:
    try:
        return db.execute(
            text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='capturado'"),
            {"uid": tenant_id},
        ).scalar() or 0
    except Exception:
        return 0


def _get_upsell(plano: str) -> Optional[str]:
    upsells = {
        "starter": "Pro: 360 creditos/mes + cooldown 30min + SDR",
        "pro": "Agency: R$497/mes + sem cooldown + SDR em volume",
        "beta": "Agency: R$497/mes + sem cooldown + SDR em volume",
    }
    return upsells.get(plano)


def _registrar_transacao(
    db: Session,
    user_id: int,
    tipo: str,
    tokens_consumidos: int = 0,
    custo_usd: float = 0,
    descricao: str = "",
) -> None:
    """Registra transacao no historico."""
    try:
        db.execute(
            text(
                """
                INSERT INTO token_transactions (user_id, tipo, tokens_consumidos, custo_usd, descricao)
                VALUES (:uid, :tipo, :tokens, :custo, :desc)
                """
            ),
            {
                "uid": user_id,
                "tipo": tipo,
                "tokens": tokens_consumidos,
                "custo": custo_usd,
                "desc": descricao,
            },
        )
        db.commit()
    except Exception as e:
        print(f"[Credits] Erro ao registrar transacao: {e}")
