"""
Retargeting Endpoints
Captura visitantes anônimos, envia emails, gera custom audiences
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging
import hashlib
import os
import httpx
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/retargeting", tags=["Retargeting"])

# ============================================
# MODELS
# ============================================

class TrackVisitorRequest(BaseModel):
    session_id: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    pagina_visitada: Optional[str] = None
    tempo_permanencia_s: int = 0
    scroll_depth_pct: int = 0
    clicou_cta: bool = False
    origem: Optional[str] = None  # exit_popup, organic, etc
    user_agent: Optional[str] = None

class TrackVisitorResponse(BaseModel):
    ok: bool
    visitor_id: int
    message: str

class RetargetingStatsResponse(BaseModel):
    total_visitors: int
    total_emails_captured: int
    total_phones_captured: int
    conversion_rate: float
    retargeting_emails_sent: int
    pending_to_retarget: int

# ============================================
# ENDPOINTS
# ============================================

@router.post("/track", response_model=TrackVisitorResponse)
async def track_visitor(
    body: TrackVisitorRequest,
    db: Session = Depends(get_db)
):
    """Registra visitante anônimo (capturado por popup ou tracking)"""

    # Hash do IP (LGPD compliance)
    ip_hash = hashlib.md5(os.urandom(16)).hexdigest()[:16]

    # Verificar se já existe sessão
    existing = db.execute(
        text("SELECT id, email, telefone, converteu_cadastro FROM visitor_tracking WHERE session_id = :sid"),
        {"sid": body.session_id}
    ).fetchone()

    if existing:
        # Atualizar último acesso + métricas
        update_fields = ["ultimo_acesso = NOW()"]
        params = {"sid": body.session_id, "id": existing[0]}

        if body.tempo_permanencia_s > 0:
            update_fields.append("tempo_permanencia_s = GREATEST(tempo_permanencia_s, :tempo)")
            params["tempo"] = body.tempo_permanencia_s

        if body.scroll_depth_pct > 0:
            update_fields.append("scroll_depth_pct = GREATEST(scroll_depth_pct, :scroll)")
            params["scroll"] = body.scroll_depth_pct

        if body.email and not existing[1]:
            update_fields.append("email = :email")
            params["email"] = body.email

        if body.telefone and not existing[2]:
            update_fields.append("telefone = :telefone")
            params["telefone"] = body.telefone

        if body.clicou_cta:
            update_fields.append("clicou_cta = TRUE")

        if body.origem:
            update_fields.append("origem = COALESCE(origem, :origem)")
            params["origem"] = body.origem

        db.execute(
            text(f"UPDATE visitor_tracking SET {', '.join(update_fields)} WHERE session_id = :sid"),
            params
        )
        db.commit()

        return TrackVisitorResponse(
            ok=True,
            visitor_id=existing[0],
            message="Visitante atualizado"
        )

    # Criar novo registro
    result = db.execute(
        text("""
            INSERT INTO visitor_tracking (
                session_id, email, telefone,
                utm_source, utm_medium, utm_campaign,
                pagina_visitada, tempo_permanencia_s, scroll_depth_pct,
                clicou_cta, origem, user_agent, ip_hash
            ) VALUES (
                :session_id, :email, :telefone,
                :utm_source, :utm_medium, :utm_campaign,
                :pagina_visitada, :tempo, :scroll,
                :clicou_cta, :origem, :user_agent, :ip_hash
            )
            RETURNING id
        """),
        {
            "session_id": body.session_id,
            "email": body.email,
            "telefone": body.telefone,
            "utm_source": body.utm_source,
            "utm_medium": body.utm_medium,
            "utm_campaign": body.utm_campaign,
            "pagina_visitada": body.pagina_visitada,
            "tempo": body.tempo_permanencia_s,
            "scroll": body.scroll_depth_pct,
            "clicou_cta": body.clicou_cta,
            "origem": body.origem,
            "user_agent": body.user_agent,
            "ip_hash": ip_hash,
        }
    )

    visitor_id = result.fetchone()[0]
    db.commit()

    return TrackVisitorResponse(
        ok=True,
        visitor_id=visitor_id,
        message="Visitante registrado"
    )


@router.get("/stats", response_model=RetargetingStatsResponse)
async def get_retargeting_stats(db: Session = Depends(get_db)):
    """Estatísticas de retargeting"""

    # Total de visitantes
    total = db.execute(
        text("SELECT COUNT(*) FROM visitor_tracking")
    ).scalar() or 0

    # Com email capturado
    with_email = db.execute(
        text("SELECT COUNT(*) FROM visitor_tracking WHERE email IS NOT NULL")
    ).scalar() or 0

    # Com telefone
    with_phone = db.execute(
        text("SELECT COUNT(*) FROM visitor_tracking WHERE telefone IS NOT NULL")
    ).scalar() or 0

    # Conversões (viraram leads)
    conversions = db.execute(
        text("SELECT COUNT(*) FROM visitor_tracking WHERE converteu_cadastro = TRUE")
    ).scalar() or 0

    # Taxa de conversão
    conv_rate = (conversions / total * 100) if total > 0 else 0

    # Emails de retarget enviados
    emails_sent = db.execute(
        text("SELECT COUNT(*) FROM retargeting_emails")
    ).scalar() or 0

    # Pendentes para retarget (capturou email, ainda não converteu, ainda não recebeu email)
    pending = db.execute(
        text("""
            SELECT COUNT(*)
            FROM visitor_tracking v
            WHERE v.email IS NOT NULL
              AND v.converteu_cadastro = FALSE
              AND NOT EXISTS (
                  SELECT 1 FROM retargeting_emails r
                  WHERE r.visitor_id = v.id
              )
              AND v.criado_em < NOW() - INTERVAL '15 minutes'
        """)
    ).scalar() or 0

    return RetargetingStatsResponse(
        total_visitors=total,
        total_emails_captured=with_email,
        total_phones_captured=with_phone,
        conversion_rate=round(conv_rate, 2),
        retargeting_emails_sent=emails_sent,
        pending_to_retarget=pending
    )


@router.get("/visitors")
async def list_visitors(
    converted: Optional[str] = None,
    has_email: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Lista visitantes capturados"""

    query = """
        SELECT id, session_id, email, telefone,
               utm_source, utm_campaign, pagina_visitada,
               tempo_permanencia_s, scroll_depth_pct, clicou_cta,
               origem, converteu_cadastro,
               criado_em, ultimo_acesso
        FROM visitor_tracking
        WHERE 1=1
    """
    params = {}

    if has_email:
        query += " AND email IS NOT NULL"

    if converted == "yes":
        query += " AND converteu_cadastro = TRUE"
    elif converted == "no":
        query += " AND converteu_cadastro = FALSE"

    query += " ORDER BY ultimo_acesso DESC LIMIT 100"

    result = db.execute(query, params)
    rows = result.fetchall()

    visitors = []
    for r in rows:
        visitors.append({
            "id": r[0],
            "session_id": r[1],
            "email": r[2],
            "telefone": r[3],
            "utm_source": r[4],
            "utm_campaign": r[5],
            "pagina_visitada": r[6],
            "tempo_permanencia_s": r[7],
            "scroll_depth_pct": r[8],
            "clicou_cta": r[9],
            "origem": r[10],
            "converteu_cadastro": r[11],
            "criado_em": r[12].isoformat() if r[12] else None,
            "ultimo_acesso": r[13].isoformat() if r[13] else None,
        })

    return visitors


# ============================================
# RETARGETING - Envio de emails
# ============================================

@router.post("/send-emails")
async def send_retargeting_emails(
    etapa: str = "30min",  # 30min, 24h, 72h
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Dispara emails de retargeting para quem não converteu"""

    # Definir janela de tempo
    if etapa == "30min":
        min_age = "INTERVAL '15 minutes'"
        max_age = "INTERVAL '45 minutes'"
    elif etapa == "24h":
        min_age = "INTERVAL '23 hours'"
        max_age = "INTERVAL '25 hours'"
    elif etapa == "72h":
        min_age = "INTERVAL '71 hours'"
        max_age = "INTERVAL '73 hours'"
    else:
        raise HTTPException(400, "Etapa inválida")

    # Buscar visitantes elegíveis
    rows = db.execute(
        text(f"""
            SELECT v.id, v.email, v.telefone, v.utm_source
            FROM visitor_tracking v
            WHERE v.email IS NOT NULL
              AND v.converteu_cadastro = FALSE
              AND v.criado_em BETWEEN NOW() - {max_age} AND NOW() - {min_age}
              AND NOT EXISTS (
                  SELECT 1 FROM retargeting_emails r
                  WHERE r.visitor_id = v.id AND r.etapa = :etapa
              )
            ORDER BY v.criado_em ASC
            LIMIT :limit
        """),
        {"etapa": etapa, "limit": limit}
    ).fetchall()

    if not rows:
        return {"ok": True, "sent": 0, "message": "Nenhum visitante elegível"}

    sent = 0
    errors = []

    for row in rows:
        visitor_id, email, telefone, utm_source = row
        try:
            # Tentar enviar via Brevo
            brevo_result = await send_brevo_email(email, etapa, utm_source, telefone)

            # Salvar log
            db.execute(
                text("""
                    INSERT INTO retargeting_emails (
                        visitor_id, email, etapa, template_id,
                        brevo_message_id, status
                    ) VALUES (
                        :vid, :email, :etapa, :template,
                        :msg_id, :status
                    )
                """),
                {
                    "vid": visitor_id,
                    "email": email,
                    "etapa": etapa,
                    "template": f"retarget_{etapa}",
                    "msg_id": brevo_result.get("message_id"),
                    "status": "enviado" if brevo_result.get("ok") else "erro",
                }
            )
            sent += 1

        except Exception as e:
            logger.error(f"Erro ao enviar retarget para {email}: {e}")
            errors.append(f"{email}: {str(e)}")

    db.commit()

    return {
        "ok": True,
        "sent": sent,
        "total_elegiveis": len(rows),
        "errors": errors,
        "etapa": etapa
    }


async def send_brevo_email(email: str, etapa: str, utm_source: str = "", telefone: str = ""):
    """Envia email via Brevo"""

    brevo_api_key = os.getenv("BREVO_API_KEY", "")
    if not brevo_api_key:
        logger.warning("BREVO_API_KEY não configurada - pulando envio real")
        return {"ok": False, "message_id": None, "reason": "no_api_key"}

    # Templates por etapa
    templates = {
        "30min": {
            "subject": "Você esqueceu algo? 🎁",
            "html": f"""
            <h1>Oi! Tudo bem?</h1>
            <p>Você visitou a FraLib agora há pouco e parece ter se interessado.</p>
            <p>Antes de ir embora, queria te contar uma coisa:</p>
            <p><strong>Assine o Starter por 1 mês e teste sem compromisso.</strong></p>
            <p>Depois de 30 dias, pode migrar para o Pro com desconto exclusivo.</p>
            <p><a href="https://seunegociofralib.site/?utm_source=retarget_30min">Quero aproveitar</a></p>
            """
        },
        "24h": {
            "subject": "Bônus exclusivos pra você ⏰",
            "html": f"""
            <h1>Volta aqui!</h1>
            <p>Você visitou a FraLib ontem. Bateu curiosidade?</p>
            <p>Tenho um presente: <strong>1 mês de Starter por R$97</strong> (normal R$197).</p>
            <p>É sua chance de testar sem risco.</p>
            <p><a href="https://seunegociofralib.site/?utm_source=retarget_24h">Ativar agora</a></p>
            """
        },
        "72h": {
            "subject": "Última chance: Starter por R$97 ⏰",
            "html": f"""
            <h1>ÚLTIMA OPORTUNIDADE</h1>
            <p>Você visitou a FraLib há 3 dias. A oferta exclusiva está acabando.</p>
            <p><strong>Starter por R$97 no primeiro mês</strong> - sem cartão, cancele quando quiser.</p>
            <p>Depois disso, o preço volta para R$497/mês (Pro).</p>
            <p><a href="https://seunegociofralib.site/?utm_source=retarget_72h">Aproveitar AGORA</a></p>
            """
        }
    }

    template = templates.get(etapa, templates["30min"])

    payload = {
        "sender": {"name": "FraLib", "email": "contato@fralib.site"},
        "to": [{"email": email}],
        "subject": template["subject"],
        "htmlContent": template["html"]
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json"
                }
            )

            if r.status_code in (200, 201):
                data = r.json()
                return {"ok": True, "message_id": data.get("messageId")}
            else:
                return {"ok": False, "message_id": None, "error": r.text[:200]}
    except Exception as e:
        return {"ok": False, "message_id": None, "error": str(e)}


# ============================================
# META CUSTOM AUDIENCE
# ============================================

@router.post("/meta-audience")
async def generate_meta_audience(db: Session = Depends(get_db)):
    """Gera lista de emails para Custom Audience do Meta"""

    # Buscar emails de quem NÃO cadastrou
    rows = db.execute(
        text("""
            SELECT DISTINCT v.email
            FROM visitor_tracking v
            WHERE v.email IS NOT NULL
              AND v.converteu_cadastro = FALSE
              AND v.email LIKE '%@%'
            ORDER BY v.criado_em DESC
            LIMIT 10000
        """)
    ).fetchall()

    emails = [r[0] for r in rows if r[0]]

    if not emails:
        return {"ok": True, "count": 0, "emails": []}

    # Hash SHA256 dos emails (Meta exige hash)
    hashed_emails = []
    for email in emails:
        clean = email.strip().lower()
        hashed = hashlib.sha256(clean.encode()).hexdigest()
        hashed_emails.append(hashed)

    # Aqui você pode enviar para Meta Marketing API
    # ou apenas retornar para o usuário copiar
    meta_access_token = os.getenv("META_ACCESS_TOKEN", "")
    meta_ad_account = os.getenv("META_AD_ACCOUNT_ID", "")

    if meta_access_token and meta_ad_account:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"https://graph.facebook.com/v18.0/act_{meta_ad_account}/customaudiences",
                    params={
                        "name": f"FraLib_Retarget_{datetime.now().strftime('%Y%m%d')}",
                        "subtype": "CUSTOM",
                        "access_token": meta_access_token,
                        "payload": {
                            "schema": "EMAIL_SHA256",
                            "data": hashed_emails[:10000]
                        }
                    }
                )
                # Salvar log
                return {
                    "ok": True,
                    "count": len(hashed_emails),
                    "meta_response": r.json() if r.status_code < 300 else r.text
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "count": len(hashed_emails),
        "hashed_emails_sample": hashed_emails[:5],
        "message": "Configure META_ACCESS_TOKEN para upload automático"
    }