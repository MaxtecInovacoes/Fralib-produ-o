"""Leads SDR and WhatsApp integration endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import os, sys, re as _re

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.endpoints.sse_endpoints import adicionar_log
from backend.whatsapp_listener import is_tenant_connected, _salvar_interacao
from backend.whatsapp.sender import send_text_parts
from backend.services.credits_manager import plano_tem_sdr
from backend.services.sdr_gateway import SdrMessageContext, evaluate_sdr_output, has_prior_outbound

logger = logging.getLogger(__name__)



# Import models from leads_crud_models
from backend.endpoints.leads_crud_models import FeedbackRequest


router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("/{lead_id}/feedback")
async def registrar_feedback(
    lead_id: str,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """
    Registra feedback de conversao/perda de um lead.
    Salva na tabela sdr_learning para o Franz aprender com o historico.
    Se resultado='convertido', atualiza lead.status='convertido'.
    """
    if req.resultado not in ("convertido", "perdido"):
        raise HTTPException(
            status_code=400, detail="resultado deve ser 'convertido' ou 'perdido'"
        )

    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])

        # PERF: Unica query com LEFT JOIN para buscar lead E ultima mensagem
        # Antes: 2 queries separadas; Depois: 1 query com JOIN
        dados = db.execute(
            text("""
            SELECT
                l.id,
                l.segmento,
                l.tier,
                l.telefone,
                sub.mensagem_usada
            FROM leads l
            LEFT JOIN (
                SELECT lead_id, mensagem AS mensagem_usada
                FROM interacoes
                WHERE lead_id = :lead_id AND direcao = 'saida'
                ORDER BY id DESC
                LIMIT 1
            ) sub ON sub.lead_id = l.id
            WHERE l.id = :lead_id AND l.user_id = :uid
            """),
            {"lead_id": lead_id, "uid": tenant_id},
        ).fetchone()

        if not dados:
            raise HTTPException(status_code=404, detail="Lead nao encontrado")

        segmento = dados.segmento or ""
        tier = dados.tier or "STANDARD"
        telefone = dados.telefone or ""
        mensagem_usada = dados.mensagem_usada or ""

        variant = ""
        stage = ""
        price_tier = 0
        try:
            from agents.memory import carregar_memoria

            memoria_sdr = (
                carregar_memoria(f"franz_lead_{telefone}", user_id=tenant_id)
                or carregar_memoria(f"bryan_lead_{telefone}", user_id=tenant_id)
                or {}
            )
            variant = memoria_sdr.get("variant") or ""
            stage = memoria_sdr.get("estado") or ""
            price_tier = int(memoria_sdr.get("price_tier") or 0)
        except Exception:
            pass

        # Salvar na sdr_learning
        db.execute(
            text("""
            INSERT INTO sdr_learning
                (lead_id, nicho, segmento, tier, mensagem_usada, resultado, observacao, user_id, variant, stage, price_tier, criado_em)
            VALUES
                (:lead_id, :nicho, :segmento, :tier, :mensagem_usada, :resultado, :observacao, :user_id, :variant, :stage, :price_tier, NOW()::text)
        """),
            {
                "lead_id": lead_id,
                "nicho": segmento,
                "segmento": segmento,
                "tier": tier,
                "mensagem_usada": mensagem_usada,
                "resultado": req.resultado,
                "observacao": req.observacao,
                "user_id": tenant_id,
                "variant": variant,
                "stage": stage,
                "price_tier": price_tier,
            },
        )

        # Se convertido, atualizar status do lead
        if req.resultado == "convertido":
            db.execute(
                text(
                    "UPDATE leads SET status='convertido', atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
                ),
                {"id": lead_id, "uid": tenant_id},
            )

        db.commit()

        adicionar_log(
            f"[Feedback] Lead {lead_id} marcado como '{req.resultado}' no segmento '{segmento}'",
            "success" if req.resultado == "convertido" else "info",
        )

        return {
            "ok": True,
            "mensagem": f"Feedback '{req.resultado}' registrado com sucesso",
            "lead_id": lead_id,
            "segmento": segmento,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Leads SDR] Erro: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.post("/{lead_id}/enviar-mensagem")
async def enviar_mensagem_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Envia mensagem Franz para lead com site pronto (sdr_stage=pendente_wpp)."""
    import os, httpx

    tenant_id = int(usuario.get("tenant_id", usuario.get("id")))
    plano_row = db.execute(
        text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()
    plano = ((plano_row[0] if plano_row else "") or "").lower()
    status = ((plano_row[1] if plano_row else "") or "").lower()
    trial_expires_at = plano_row[2] if plano_row else None
    if not plano_tem_sdr(plano, status, trial_expires_at):
        raise HTTPException(
            403,
            {
                "reason": "sdr_plan_required",
                "message": "SDR/WhatsApp esta disponivel no Trial ativo e nos planos Pro, Ilimitado ou Admin.",
                "upgrade_url": "/planos",
            },
        )

    # Buscar lead
    row = db.execute(
        text(
            "SELECT nome, telefone, whatsapp, whatsapp_pendente, segmento, cidade, site_url, rating, sdr_stage, paleta_cores FROM leads WHERE id=:id AND user_id=:uid"
        ),
        {"id": lead_id, "uid": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Lead nao encontrado")

    nome, telefone, whatsapp, whatsapp_pendente, segmento, cidade, site_url, rating, sdr_stage, paleta_cores = row

    # Verificar se lead tem WhatsApp
    telefone_ou_whatsapp = (whatsapp or telefone or "").strip()
    if not telefone_ou_whatsapp:
        raise HTTPException(400, "Lead nao tem WhatsApp/Telefone. Adicione primeiro.")

    if not site_url:
        raise HTTPException(400, "Lead nao tem site gerado. Rode o pipeline primeiro.")

    # Verificar WPP conectado
    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        raise HTTPException(503, "MEOWHATS_KEY ausente na configuracao do servidor")
    wpp_tenant = f"fralib_user_{tenant_id}"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r_wpp = await c.get(
                f"{meowhats_url}/api/sessions", headers={"X-API-Key": meowhats_key}
            )
            wpp_ok = False
            if r_wpp.status_code == 200:
                for s in r_wpp.json():
                    if s.get("id") == wpp_tenant and s.get("status") == "connected":
                        wpp_ok = True
                        break
            if not wpp_ok:
                raise HTTPException(
                    400, "WhatsApp nao esta conectado. Conecte primeiro no painel."
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Erro ao verificar status do WhatsApp")

    # Gerar mensagem com Franz
    from agents.sdr_langgraph import iniciar_contato, FranzInput

    franz_input = FranzInput(
        nome=nome,
        cidade=cidade or "",
        segmento=segmento or "",
        telefone=telefone or "",
        whatsapp=whatsapp or "",
        rating=rating or 0.0,
        site_url=site_url,
        score_caio=80,
        tier="STANDARD",
        paleta_cores=paleta_cores or {},
    )
    franz_output = iniciar_contato(franz_input, user_id=tenant_id)

    # Se Franz bloqueou (fora do horario, duplicado, fila), nao enviar texto vazio
    if not franz_output.reply or not franz_output.reply.strip():
        return {
            "ok": False,
            "mensagem": franz_output.proximo_passo
            or "Fora do horario de atendimento. Lead permanece na fila.",
        }

    prior_outbound = has_prior_outbound(db, lead_id, tenant_id)
    guard = evaluate_sdr_output(
        SdrMessageContext(
            tenant_id=tenant_id,
            lead_id=lead_id,
            lead_name=nome or "",
            lead_segment=segmento or "",
            stage=sdr_stage or "pendente_wpp",
            next_stage=franz_output.next_stage or "",
            message=franz_output.reply,
            site_url=site_url,
            prior_outbound=prior_outbound,
            direction="outbound",
            plan_allows_sdr=True,
            whatsapp_connected=True,
            within_schedule=True,
            site_ready=bool(site_url),
        )
    )
    if not guard.allowed:
        return {"ok": False, "reason": guard.code, "mensagem": guard.reason}

    # Enviar via meowhats
    tel = (whatsapp or telefone or "").strip()
    tel = _re.sub(r"\D", "", tel)
    if not tel.startswith("55"):
        tel = "55" + tel
    jid = f"{tel}@s.whatsapp.net"

    if not is_tenant_connected(wpp_tenant):
        raise HTTPException(
            409,
            "WhatsApp do usuario nao esta conectado. Pareie o QR code antes de enviar mensagens.",
        )

    # Enviar via meowhats usando send_text_parts (unificado)
    async def _enviar_whatsapp():
        import asyncio
        client = httpx.Client(timeout=10)
        try:
            ok, err = send_text_parts(
                client,
                meowhats_url,
                meowhats_key,
                wpp_tenant,
                jid,
                [franz_output.reply]
            )
            return ok, err
        finally:
            client.close()

    ok, err = await asyncio.to_thread(_enviar_whatsapp)
    if not ok:
        raise HTTPException(500, f"Falha no envio: {err}")

    _salvar_interacao(lead_id, franz_output.reply, "saida", tenant_id)

    # Atualizar sdr_stage
    db.execute(
        text(
            "UPDATE leads SET sdr_stage=:stage, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
        ),
        {"id": lead_id, "stage": franz_output.next_stage or "hook", "uid": tenant_id},
    )
    db.commit()

    adicionar_log(f" Mensagem enviada para {nome} ({tel})", "success", tenant_id)
    return {"ok": True, "mensagem": f"Mensagem enviada para {nome}"}
