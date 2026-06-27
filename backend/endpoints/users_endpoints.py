from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from pydantic import BaseModel

import sys
import os

# Adicionar caminhos para importar os módulos core
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.services.credits_manager import plano_tem_sdr
from backend.services.sdr_settings import (
    fetch_sdr_settings,
    invalidate_sdr_settings_cache,
    outbound_schedule_from_settings,
    save_sdr_settings,
)
from backend.utils.password_utils import BCRYPT_MAX_BYTES, hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])

_WPP_CONNECTED_STATES = ("connected", "open", "authenticated")


async def _check_whatsapp_connected(user_id: int) -> bool:
    """Checa se o WhatsApp do user esta conectado no meowhats.

    Tem dois caminhos: rota direta /api/sessions/{tenant}/status e fallback
    listando todas as sessoes. Timeout maior (8s) + 1 retry para evitar
    falso 'desconectado' quando o meowhats demora a responder.
    """
    import httpx, asyncio, logging

    _log = logging.getLogger(__name__)

    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        _log.error("[wpp_check] MEOWHATS_KEY ausente; status retornado como desconectado")
        return False
    tenant_id = f"fralib_user_{user_id}"
    headers = {"X-API-Key": meowhats_key}

    async def _try_direct():
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(
                f"{meowhats_url}/api/sessions/{tenant_id}/status", headers=headers
            )
            if r.status_code == 200:
                return r.json().get("status") in _WPP_CONNECTED_STATES
            return None

    async def _try_list():
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{meowhats_url}/api/sessions", headers=headers)
            if r.status_code == 200:
                for s in r.json():
                    if s.get("tenantId") == tenant_id or s.get("id") == tenant_id:
                        return s.get("status") in _WPP_CONNECTED_STATES
                return False
            return None

    for tentativa in (1, 2):
        try:
            v = await _try_direct()
            if v is True:
                return True
            if v is False:
                # rota direta confirmou desconectado — tenta listar antes de aceitar
                v2 = await _try_list()
                if v2 is True:
                    return True
                if v2 is False:
                    return False
                # listar nao respondeu — segue retry
            # v is None (status != 200) — tenta listar
            v2 = await _try_list()
            if v2 is not None:
                return bool(v2)
        except Exception as e:
            _log.warning(f"[wpp_check] user={user_id} tentativa={tentativa} erro={e}")
            if tentativa == 1:
                await asyncio.sleep(0.4)
                continue

    return False


class UserProfileUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    nicho: Optional[str] = None
    origem: Optional[str] = None
    cep: Optional[str] = None
    rua: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str


@router.get("/profile")
async def get_profile(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    user_id = user["id"]
    query = text(
        "SELECT id, email, nome, telefone, endereco, nicho, origem, cep, rua, bairro, cidade, estado, plano, role, status FROM users WHERE id = :user_id"
    )
    result = db.execute(query, {"user_id": user_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return dict(result._mapping)


_ALLOWED_PROFILE_FIELDS = {
    "nome",
    "telefone",
    "endereco",
    "nicho",
    "origem",
    "cep",
    "rua",
    "bairro",
    "cidade",
    "estado",
}


@router.put("/profile")
async def update_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["id"]
    update_data = data.model_dump(exclude_unset=True)

    update_data = {k: v for k, v in update_data.items() if k in _ALLOWED_PROFILE_FIELDS}

    if not update_data:
        return {"status": "ok", "mensagem": "Nenhum dado para atualizar"}

    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE users SET {set_clause} WHERE id = :user_id")

    db.execute(query, {**update_data, "user_id": user_id})
    db.commit()

    return {"status": "ok", "mensagem": "Perfil atualizado com sucesso"}


@router.put("/password")
async def update_password(
    data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["id"]
    current_password = data.current_password or ""
    new_password = data.new_password or ""
    if len(new_password) < 12:
        raise HTTPException(400, "Senha deve ter pelo menos 12 caracteres")
    if len(new_password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise HTTPException(400, "Senha deve ter no maximo 72 bytes")
    if not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
        raise HTTPException(400, "Senha deve conter letras e numeros")

    row = db.execute(
        text("SELECT password_hash FROM users WHERE id=:id"),
        {"id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    if not verify_password(current_password, row[0]):
        raise HTTPException(403, "Senha atual incorreta")

    new_hash = hash_password(new_password)
    db.execute(
        text("UPDATE users SET password_hash=:hash, senha_hash=:hash WHERE id=:id"),
        {"hash": new_hash, "id": user_id},
    )
    db.commit()
    return {"status": "ok", "mensagem": "Senha alterada com sucesso"}


@router.get("/onboarding-status")
async def onboarding_status(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    user_id = user["id"]
    row = db.execute(
        text(
            "SELECT nome, telefone, nicho, plano, creditos, creditos_max, trial_expires_at, status, cidade FROM users WHERE id=:id"
        ),
        {"id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")

    perfil_ok = bool(row[0] and row[1] and row[2])  # nome + telefone + nicho
    plano = (row[3] or "trial").lower()
    status_conta = (row[7] or "").lower()
    trial_expires_at = row[6]
    whatsapp_allowed = plano_tem_sdr(plano, status_conta, trial_expires_at)
    # WPP agora é OPCIONAL - usuário pode criar site sem WPP e conectar depois
    whatsapp_required = False  # Não bloqueia mais o onboarding

    # Verificar WhatsApp conectado — 2 caminhos com fallback + retry
    wpp_ok = await _check_whatsapp_connected(user_id)

    # Verificar se tem lead demo
    lead_demo = db.execute(
        text("SELECT id FROM leads WHERE user_id=:uid AND status='demo' LIMIT 1"),
        {"uid": user_id},
    ).fetchone()

    # PR9: ja rodou pelo menos um pipeline real (lead concluido nao-demo)?
    pipeline_ok_row = db.execute(
        text(
            "SELECT 1 FROM leads WHERE user_id=:uid AND status='concluido' "
            "AND (status IS DISTINCT FROM 'demo') LIMIT 1"
        ),
        {"uid": user_id},
    ).fetchone()
    pipeline_ok = bool(pipeline_ok_row)

    return {
        "perfil_ok": perfil_ok,
        "wpp_ok": wpp_ok,
        "whatsapp_ok": wpp_ok,
        "whatsapp_allowed": whatsapp_allowed,
        "whatsapp_required": whatsapp_required,
        "whatsapp_blocked_by_plan": not whatsapp_allowed,
        "can_use_app": bool(perfil_ok and (not whatsapp_required or wpp_ok)),
        "blocking_steps": [
            step
            for step, blocked in (
                ("profile", not perfil_ok),
                ("whatsapp", whatsapp_required and not wpp_ok),
            )
            if blocked
        ],
        "perfil_required_fields": ["nome", "telefone", "nicho"],
        "sdr_message": (
            "Trial ativo com SDR liberado."
            if plano == "trial" and whatsapp_allowed
            else (
                "Starter gera sites sem SDR. Para WhatsApp automatico, faca upgrade para Pro."
                if plano == "starter"
                else "SDR ativo para este plano."
            )
        ),
        "pipeline_ok": pipeline_ok,
        "plano": row[3],
        "status": row[7],
        "creditos": row[4],
        "creditos_max": row[5],
        "trial_expires_at": trial_expires_at,
        "cidade": row[8],
        "tem_lead_demo": bool(lead_demo),
    }


@router.post("/criar-lead-demo")
async def criar_lead_demo(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    import uuid
    from datetime import datetime

    user_id = user["id"]

    # Verificar se ja tem lead demo
    existing = db.execute(
        text("SELECT id FROM leads WHERE user_id=:uid AND status='demo' LIMIT 1"),
        {"uid": user_id},
    ).fetchone()
    if existing:
        return {
            "status": "ok",
            "mensagem": "Lead demo ja existe",
            "lead_id": existing[0],
        }

    lead_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    db.execute(
        text("""
        INSERT INTO leads (id, nome, cidade, segmento, telefone, whatsapp, telefone_whatsapp,
            score, status, criado_em, atualizado_em, processado, tentativas, user_id,
            url_site, observacoes)
        VALUES (:id, :nome, :cidade, :seg, :tel, :tel, :tel,
            85, 'demo', :now, :now, false, 0, :uid,
            NULL, 'Lead de demonstracao — assine um plano para gerar leads reais')
    """),
        {
            "id": lead_id,
            "nome": "Academia Exemplo (DEMO)",
            "cidade": "São Paulo",
            "seg": "Academia",
            "tel": "(11) 99999-0000",
            "now": now,
            "uid": user_id,
        },
    )
    db.commit()
    return {"status": "ok", "mensagem": "Lead demo criado", "lead_id": lead_id}


# ─── Chave Anthropic por tenant (desativado no modelo comercial atual) ───
class AnthropicKeyRequest(BaseModel):
    api_key: str


@router.get("/anthropic-key/status")
async def status_anthropic_key(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    """Contrato legado: a oferta publica atual nao permite chave propria."""

    row = db.execute(
        text("SELECT plano FROM users WHERE id=:id"),
        {"id": user["id"]},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    plano = (row[0] or "").lower()
    return {"configurada": False, "hint": "", "plano": plano, "disponivel": False}


@router.put("/anthropic-key")
async def salvar_anthropic_key(
    body: AnthropicKeyRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    raise HTTPException(
        410,
        "Chave propria foi desativada. Use os planos com cooldown: Starter 60min, Pro 30min, Agency sem cooldown.",
    )


@router.delete("/anthropic-key")
async def remover_anthropic_key(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    db.execute(
        text("UPDATE users SET anthropic_key_encrypted=NULL WHERE id=:id"),
        {"id": user["id"]},
    )
    db.commit()
    try:
        from agents.llm_direct import invalidar_byok_cache

        invalidar_byok_cache(user["id"])
    except Exception:
        pass
    return {"status": "ok"}


# ═══ CONFIG HORÁRIO SDR ═══════════════════════════════════════════


class HorarioSDRRequest(BaseModel):
    modo: str  # 'livre' ou 'personalizado'
    hora_inicio: int = 8
    hora_fim: int = 21
    dias_bloqueados: list = [6]  # 0=seg, 6=dom


@router.get("/sdr-config")
async def get_sdr_config(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    """Retorna configuracao completa do SDR para o tenant atual."""

    return fetch_sdr_settings(db, user["id"])


@router.put("/sdr-config")
async def salvar_sdr_config(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Salva configuracao tenant-owned do SDR.

    Starter pode configurar a experiencia, mas a execucao do SDR continua
    bloqueada pelo gate comercial em runtime.
    """

    settings = save_sdr_settings(db, user["id"], body)
    try:
        from agents.sdr_langgraph import _HORARIO_CACHE

        _HORARIO_CACHE.pop(f"sdr_horario_{user['id']}", None)
    except Exception:
        pass
    invalidate_sdr_settings_cache(user["id"])
    return {"status": "ok", "config": settings}


@router.get("/sdr-horario")
async def get_sdr_horario(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    """Retorna config de horário do SDR do tenant."""
    return outbound_schedule_from_settings(fetch_sdr_settings(db, user["id"]))


@router.put("/sdr-horario")
async def salvar_sdr_horario(
    body: HorarioSDRRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Salva config de horário do SDR."""
    # Validar
    if body.modo not in ("livre", "personalizado"):
        raise HTTPException(400, "Modo deve ser 'livre' ou 'personalizado'")
    if body.hora_inicio < 0 or body.hora_inicio > 23:
        raise HTTPException(400, "hora_inicio deve ser 0-23")
    if body.hora_fim < 1 or body.hora_fim > 24:
        raise HTTPException(400, "hora_fim deve ser 1-24")
    if body.hora_inicio >= body.hora_fim:
        raise HTTPException(400, "hora_inicio deve ser menor que hora_fim")

    legacy_config = {
        "modo": body.modo,
        "hora_inicio": body.hora_inicio,
        "hora_fim": body.hora_fim,
        "dias_bloqueados": body.dias_bloqueados,
    }
    settings = fetch_sdr_settings(db, user["id"])
    settings["outbound_schedule"] = {
        "mode": "always" if body.modo == "livre" else "custom",
        "timezone": "America/Sao_Paulo",
        "hora_inicio": body.hora_inicio,
        "hora_fim": body.hora_fim,
        "dias_bloqueados": body.dias_bloqueados,
    }
    settings = save_sdr_settings(db, user["id"], settings)

    # Invalidar cache do bryan
    from agents.sdr_langgraph import _HORARIO_CACHE

    _HORARIO_CACHE.pop(f"sdr_horario_{user['id']}", None)
    invalidate_sdr_settings_cache(user["id"])

    return {"status": "ok", "config": outbound_schedule_from_settings(settings) or legacy_config}


# ============================================================
# LGPD - Direitos do Titular (Art. 18)
# ============================================================

@router.get("/export", tags=["lgpd"])
async def exportar_dados_usuario(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Exportar todos os dados do usuário (LGPD Art. 18 VI).
    Retorna JSON com todos os dados para portabilidade.
    """
    user_id = user["id"]
    tenant_id = user.get("tenant_id", user_id)

    # SECURITY: Todos os dados devem pertencer ao tenant do usuário autenticado
    # Verifica que tenant_id está correto para evitar IDOR
    if not tenant_id or tenant_id <= 0:
        raise HTTPException(status_code=403, detail="Tenant inválido")

    try:
        # Dados do usuário - usa user_id próprio
        user_data = db.execute(
            text("SELECT id, email, name, nome, plano, plan, created_at FROM users WHERE id = :id"),
            {"id": user_id}
        ).fetchone()

        # Verifica que o usuário pertence ao tenant
        if user_data:
            db_tenant = db.execute(
                text("SELECT tenant_id FROM users WHERE id = :id"),
                {"id": user_id}
            ).fetchone()
            if not db_tenant or db_tenant[0] != tenant_id:
                raise HTTPException(status_code=403, detail="Acesso negado")

        # Leads do usuário - USA user_id CORRETAMENTE
        leads = db.execute(
            text("""
                SELECT id, nome, email, telefone, whatsapp, cidade, segmento,
                       url_site, site_url, tier, status, created_at, atualizado_em
                FROM leads WHERE user_id = :uid
            """),
            {"uid": user_id}  # FIX: usar user_id, não tenant_id
        ).fetchall()

        # Interações - USA user_id CORRETAMENTE
        interacoes = db.execute(
            text("""
                SELECT id, lead_id, tipo, mensagem, direction, created_at
                FROM interacoes WHERE user_id = :uid
                LIMIT 1000
            """),
            {"uid": user_id}  # FIX: usar user_id, não tenant_id
        ).fetchall()

        # Pipeline runs (resumo) - USA user_id CORRETAMENTE
        pipelines = db.execute(
            text("""
                SELECT id, lead_id, fase_atual, status, started_at, finished_at
                FROM pipeline_runs WHERE user_id = :uid
                LIMIT 500
            """),
            {"uid": user_id}  # FIX: usar user_id, não tenant_id
        ).fetchall()

        # Credits (resumo)
        credits = db.execute(
            text("""
                SELECT credits, plano, renovacao, usado_mes
                FROM users WHERE id = :id
            """),
            {"id": user_id}
        ).fetchone()

        # Configurações SDR
        sdr_settings = db.execute(
            text("""
                SELECT config_key, config_value
                FROM user_configs WHERE user_id = :uid
            """),
            {"uid": user_id}
        ).fetchall()

        return {
            "status": "success",
            "exportado_em": datetime.now().isoformat(),
            "usuario": dict(user_data._mapping) if user_data else None,
            "leads_count": len(leads),
            "leads": [dict(l._mapping) for l in leads],
            "interacoes_count": len(interacoes),
            "interacoes": [dict(i._mapping) for i in interacoes],
            "pipelines_count": len(pipelines),
            "pipelines": [dict(p._mapping) for p in pipelines],
            "credits": dict(credits._mapping) if credits else None,
            "sdr_settings": [dict(s._mapping) for s in sdr_settings],
        }
    except Exception as e:
        print(f"[LGPD] Erro ao exportar dados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao exportar dados. Tente novamente.")


@router.delete("/conta", tags=["lgpd"])
async def deletar_conta_usuario(
    confirmacao: str = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Deletar conta e todos os dados (LGPD Art. 18 V).
    Requer confirmação: ?confirmacao=DELETAR-MINHA-CONTA
    """
    if confirmacao != "DELETAR-MINHA-CONTA":
        raise HTTPException(
            status_code=400,
            detail="Confirmação obrigatória. Use: ?confirmacao=DELETAR-MINHA-CONTA"
        )

    user_id = user["id"]
    tenant_id = user.get("tenant_id", user_id)

    try:
        # 1. Deletar interações - USA user_id CORRETAMENTE
        db.execute(text("DELETE FROM interacoes WHERE user_id = :uid"), {"uid": user_id})

        # 2. Deletar pipeline runs - USA user_id CORRETAMENTE
        db.execute(text("DELETE FROM pipeline_runs WHERE user_id = :uid"), {"uid": user_id})

        # 3. Deletar pipeline failures - USA user_id CORRETAMENTE
        db.execute(text("DELETE FROM pipeline_failures WHERE user_id = :uid"), {"uid": user_id})

        # 4. Deletar leads - USA user_id CORRETAMENTE
        db.execute(text("DELETE FROM leads WHERE user_id = :uid"), {"uid": user_id})

        # 5. Deletar user_configs - USA user_id
        db.execute(text("DELETE FROM user_configs WHERE user_id = :uid"), {"uid": user_id})

        # 6. Deletar licença - USA user_id
        db.execute(text("DELETE FROM licencas WHERE user_id = :uid"), {"uid": user_id})

        # 7. Deletar user (por último) - USA user_id
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})

        db.commit()

        return {
            "status": "deleted",
            "message": "Conta e todos os dados foram deletados permanentemente.",
            "deletado_em": datetime.now().isoformat(),
        }

    except Exception as e:
        db.rollback()
        print(f"[LGPD] Erro ao deletar conta: {e}")
        raise HTTPException(status_code=500, detail="Erro ao deletar conta. Tente novamente.")


# Import datetime needed
from datetime import datetime
