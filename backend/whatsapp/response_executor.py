"""Response execution: guard → send → persist → advance stage."""

import logging
import time as _time

from sqlalchemy import text

from whatsapp.sender import send_presence_composing, send_text_parts
from whatsapp.sdr_reply_service import normalize_followup_date
from backend.services.sdr_gateway import SdrMessageContext, evaluate_sdr_output, has_prior_outbound

logger = logging.getLogger("whatsapp_listener")


class ExecutionContext:
    """All data needed to execute a response send."""

    __slots__ = (
        "engine",
        "http_client",
        "meowhats_http",
        "meowhats_key",
        "tenant_id",
        "jid",
        "lead_id",
        "lead_name",
        "telefone",
        "user_id",
        "segmento",
        "status",
        "sdr_stage_atual",
        "novo_stage",
        "raw_stage",
        "resposta",
        "resposta_partes",
        "franz_output",
        "opt_out",
        "prior_outbound",
        "lead_key",
        "is_tenant_connected_fn",
        "get_tenant_status_fn",
        "set_cooldown_fn",
        "increment_daily_fn",
        "notify_handoff_fn",
        "save_interaction_fn",
        "update_stage_fn",
        "humanized_delay_fn",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def evaluate_guard(ctx: ExecutionContext):
    """Run SDR output guard. Returns (allowed: bool, guard_result)."""
    try:
        with ctx.engine.connect() as conn:
            prior_outbound = has_prior_outbound(conn, ctx.lead_id, ctx.user_id)
    except Exception:
        prior_outbound = False

    guard = evaluate_sdr_output(
        SdrMessageContext(
            tenant_id=ctx.user_id,
            lead_id=ctx.lead_id,
            lead_name=ctx.lead_name,
            lead_segment=ctx.segmento or "",
            stage=ctx.sdr_stage_atual or "",
            next_stage=ctx.novo_stage or "",
            message=ctx.resposta,
            site_url="",
            prior_outbound=prior_outbound,
            direction="reply",
            plan_allows_sdr=True,
            whatsapp_connected=True,
            within_schedule=True,
            site_ready=(ctx.status == "concluido"),
            human_assumed=False,
            opt_out=ctx.opt_out,
        )
    )
    return guard.allowed, guard


def check_tenant_connected(ctx: ExecutionContext):
    """Returns (connected: bool, current_status: str)."""
    connected = ctx.is_tenant_connected_fn(ctx.tenant_id)
    if not connected:
        current = ctx.get_tenant_status_fn(ctx.tenant_id) or "unknown"
    else:
        current = ctx.get_tenant_status_fn(ctx.tenant_id) or "connected"
    return connected, current


def send_response(ctx: ExecutionContext):
    """Send message, persist, advance stage.

    Returns True if message was sent successfully, False otherwise.
    """
    # 1. Composing presence
    try:
        send_presence_composing(ctx.http_client, ctx.meowhats_http, ctx.meowhats_key, ctx.tenant_id, ctx.jid)
    except Exception:
        pass  # non-critical

    # 2. Humanized delay
    delay_secs = ctx.humanized_delay_fn(ctx.resposta)
    _time.sleep(delay_secs)

    # 3. Set cooldown ANTES do envio (evita race condition)
    # Isso impede que outra thread envie enquanto esta está enviando
    ctx.set_cooldown_fn(ctx.lead_key)
    ctx.increment_daily_fn(ctx.lead_key)

    # 4. Send in parts. Resposta a inbound nunca entra na fila de prospeccao:
    # lead respondeu, entao o atendimento precisa continuar imediatamente.
    send_ok, last_error = send_text_parts(
        ctx.http_client,
        ctx.meowhats_http,
        ctx.meowhats_key,
        ctx.tenant_id,
        ctx.jid,
        ctx.resposta_partes,
        before_send=lambda idx, parte: _time.sleep(min(2.5 + len(parte) / 90, 5.0)) if idx > 0 else None,
    )

    if not send_ok:
        logger.warning(f"Falha ao enviar resposta: {last_error}")
        return False

    # 5. Persist output
    ctx.save_interaction_fn(ctx.lead_id, ctx.resposta, "saida", ctx.user_id)
    ctx.update_stage_fn(ctx.lead_id, ctx.novo_stage, ctx.user_id)

    # 6. Scheduled follow-up
    if ctx.raw_stage == "scheduled":
        facts = ctx.franz_output.update_facts or {}
        followup_date = facts.get("followup_date", "")
        if followup_date:
            followup_date, followup_status = normalize_followup_date(followup_date)
            if followup_status == "past":
                logger.warning(f"Lead {ctx.lead_name}: data no passado corrigida para {followup_date}")
            elif followup_status == "invalid":
                logger.warning(f"Lead {ctx.lead_name}: followup_date invalido, usando amanha {followup_date}")

            with ctx.engine.connect() as conn:
                conn.execute(text(
                    "UPDATE leads SET followup_date=:fd WHERE id=:id AND user_id=:uid"
                ), {"fd": followup_date, "id": ctx.lead_id, "uid": ctx.user_id})
                conn.commit()
            logger.info(f"Lead {ctx.lead_name}: agendado para {followup_date}")

    logger.info(f"Lead {ctx.lead_name}: stage {ctx.sdr_stage_atual} -> {ctx.novo_stage}")
    logger.info(
        f"✅ Resposta enviada para {ctx.telefone} "
        f"(partes={len(ctx.resposta_partes)} delay={delay_secs:.1f}s)"
    )

    # 7. Handoff
    if ctx.franz_output.should_handoff or ctx.raw_stage == "handoff":
        ctx.notify_handoff_fn(
            ctx.http_client, ctx.tenant_id, ctx.lead_id,
            ctx.lead_name, ctx.telefone, ctx.jid, ctx.meowhats_http, ctx.user_id
        )

    return True


def execute_response(ctx: ExecutionContext):
    """Full execution: guard → connection check → send.

    Returns (sent: bool, blocked_reason: str or None).
    """
    allowed, guard = evaluate_guard(ctx)
    if not allowed:
        logger.warning(
            f"Lead {ctx.lead_name}: resposta bloqueada pelo SDR guard "
            f"code={guard.code} reason={guard.reason}"
        )
        if guard.code == "opt_out":
            ctx.update_stage_fn(ctx.lead_id, "perdidos", ctx.user_id)
        return False, f"guard:{guard.code}"

    connected, current_status = check_tenant_connected(ctx)
    if not connected:
        logger.warning(
            f"Lead {ctx.lead_name}: envio BLOQUEADO — tenant {ctx.tenant_id} esta em status '{current_status}'. "
            f"Resposta nao foi marcada como enviada."
        )
        return False, f"disconnected:{current_status}"

    try:
        sent = send_response(ctx)
        return sent, None if sent else "send_failed"
    except Exception as e:
        logger.warning(f"Erro ao enviar resposta WPP: {e}")
        return False, f"exception:{e}"
