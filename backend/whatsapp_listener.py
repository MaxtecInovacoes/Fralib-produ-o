"""
whatsapp_listener.py — Listener WebSocket do meowhats
Fica conectado ao meowhats e processa mensagens recebidas dos leads.
Quando um lead responde, chama Franz e atualiza sdr_stage no banco.
"""
import sys as _sys
import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _here)
_sys.path.insert(0, _os.path.dirname(_here))
import asyncio
import json
import os
import re
import threading
import hashlib
import logging
import time as _time
import datetime as _dt
from typing import Dict, List

import websockets
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from backend.services.credits_manager import plano_tem_sdr
from backend.services.sdr_settings import (
    daily_limit_per_lead,
    effective_daily_limit,
    get_sdr_settings_runtime,
    human_pause_seconds,
    is_within_outbound_schedule,
    reply_cooldown_seconds,
)
from whatsapp.lead_identity import (
    find_lead_by_phone_or_jid,
    normalize_jid_number,
    resolve_lid_number,
    user_id_from_tenant,
)
from whatsapp.interactions import save_interaction, update_lead_stage
from whatsapp.sdr_reply_service import (
    get_outgoing_formatter,
    is_duplicate_reply,
    map_next_stage,
    sanitize_reply,
)
from whatsapp.history_helper import get_context_with_summary as get_full_context
from whatsapp.sender import (
    send_handoff_notification,
)
from whatsapp.response_executor import (
    ExecutionContext,
    execute_response,
)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger("whatsapp_listener")
logging.basicConfig(level=logging.INFO, format="[WPP-Listener] %(message)s")

MEOWHATS_URL  = os.getenv("MEOWHATS_URL", "http://localhost:3001").replace("http://", "ws://").replace("https://", "wss://")
MEOWHATS_KEY  = os.getenv("MEOWHATS_KEY", "")
MEOWHATS_HTTP = os.getenv("MEOWHATS_URL", "http://localhost:3001")
DATABASE_URL  = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ══════════════════════════════════════════════════════════════════════
# ANTI-BAN: Debounce, Cooldown, Flood Detection, Daily Limit
# ══════════════════════════════════════════════════════════════════════

# 1. Debounce: acumula msgs do mesmo lead por 4s antes de processar
_DEBOUNCE_BUFFER: Dict[str, dict] = {}
_DEBOUNCE_LOCK = threading.Lock()

from whatsapp.rate_limiter import (
    RateLimiter,
    DEBOUNCE_SECONDS,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_DAILY_LIMIT,
    DEFAULT_FLOOD_SILENCE,
    DEFAULT_FLOOD_WINDOW,
    DEFAULT_HUMAN_PAUSE_SECONDS,
)
from agents.sdr_langgraph.lead_lock import _is_duplicate_message_id  # Deduplicação por message_id
from whatsapp.message_preprocessor import should_franz_respond  # Pré-processador de msg

# 5. Gate de billing: cache por user_id (evita query a cada msg)
_BILLING_CACHE: Dict[int, tuple] = {}  # user_id -> (can_use: bool, expires_at: float)
_BILLING_CACHE_TTL = 120.0  # 2 minutos


def _lead_key_user_id(lead_key: str) -> int | None:
    try:
        return int(str(lead_key).split(":", 1)[0])
    except Exception:
        return None


def _get_sdr_settings(user_id: int | None) -> dict:
    if not user_id:
        return {}
    try:
        return get_sdr_settings_runtime(user_id, engine)
    except Exception as e:
        logger.warning(f"[SDR Config] Falha ao carregar user {user_id}: {e}")
        return {}


def _cooldown_seconds_for_key(lead_key: str) -> float:
    user_id = _lead_key_user_id(lead_key)
    settings = _get_sdr_settings(user_id)
    return float(reply_cooldown_seconds(settings) if settings else DEFAULT_COOLDOWN_SECONDS)


def _daily_limit_for_key(lead_key: str) -> int:
    user_id = _lead_key_user_id(lead_key)
    settings = _get_sdr_settings(user_id)
    if not settings:
        return DEFAULT_DAILY_LIMIT
    # Trilha A — auto-throttle: aplicar redução baseada em phone_health_score
    phone_score = _get_phone_health_score(user_id)
    return int(effective_daily_limit(settings, phone_score))


def _human_pause_seconds_for_key(lead_key: str) -> float:
    user_id = _lead_key_user_id(lead_key)
    settings = _get_sdr_settings(user_id)
    return float(human_pause_seconds(settings) if settings else DEFAULT_HUMAN_PAUSE_SECONDS)


# Cache curto (60s) do phone_health_score por user_id, pra não martelar o DB
# a cada check de cooldown/daily_limit.
_PHONE_HEALTH_SCORE_CACHE: Dict[int, tuple] = {}
_PHONE_HEALTH_SCORE_CACHE_TTL = 60.0


def _get_phone_health_score(user_id: int | None) -> int | None:
    """Retorna score 0-100 do phone_health_score, ou None se não há dados.

    Cache 60s. Falha aberta (retorna None = sem throttle).
    """
    if not user_id:
        return None
    import time as _t
    cached = _PHONE_HEALTH_SCORE_CACHE.get(user_id)
    if cached and _t.time() < cached[1]:
        return cached[0]

    score: int | None = None
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT score FROM phone_health_score WHERE user_id=:id"
            ), {"id": user_id}).fetchone()
            if row and row[0] is not None:
                score = int(row[0])
    except Exception as e:
        logger.warning(f"[PhoneHealth] Falha ao ler score (user={user_id}): {e}")
        score = None  # fail open = sem throttle

    _PHONE_HEALTH_SCORE_CACHE[user_id] = (score, _t.time() + _PHONE_HEALTH_SCORE_CACHE_TTL)
    return score


def _invalidate_phone_health_score_cache(user_id: int) -> None:
    """Invalida cache de score. Usado após cron compute atualizar."""
    _PHONE_HEALTH_SCORE_CACHE.pop(user_id, None)


_RATE_LIMITER = RateLimiter(
    engine=engine,
    daily_limit_for_key=_daily_limit_for_key,
    cooldown_seconds_for_key=_cooldown_seconds_for_key,
    human_pause_seconds_for_key=_human_pause_seconds_for_key,
)


def _user_can_use_bot(user_id: int) -> bool:
    """Verifica se tenant tem SDR liberado. Cache de 2min."""
    import time as _t
    cached = _BILLING_CACHE.get(user_id)
    if cached and _t.time() < cached[1]:
        return cached[0]

    can_use = False
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT plano, plano_pago, trial_expires_at, creditos, status FROM users WHERE id=:id"
            ), {"id": user_id}).fetchone()
            if row:
                plano, plano_pago, trial_exp, creditos, status = row
                plano = (plano or "").lower()
                can_use = plano_tem_sdr(plano, status, trial_exp)
    except Exception as e:
        # Falha fechado: SDR não pode continuar sem confirmar plano/status.
        logger.error(f"[Billing Gate] Erro ao verificar user {user_id}: {e}")
        can_use = False

    _BILLING_CACHE[user_id] = (can_use, _t.time() + _BILLING_CACHE_TTL)
    return can_use


# ── Phone Health: pause_franz_until (Trilha A) ────────────────────────
# Cache curto (30s) por user_id. Se pause_franz_until > NOW(), bloqueia envios
# do Franz para o tenant. Freio de emergência acionado por superadmin ou
# pelo próprio tenant via /api/admin/phone-health/pause.
_PAUSE_FRANZ_CACHE: Dict[int, tuple] = {}  # user_id -> (paused: bool, expires_at: float)
_PAUSE_FRANZ_CACHE_TTL = 30.0


def _is_tenant_franz_paused(user_id: int) -> bool:
    """Retorna True se o Franz deste tenant está pausado via phone_health_score.pause_franz_until.

    Cache de 30s por user_id (mesmo padrão do _BILLING_CACHE). Falha
    aberta: se DB estiver indisponível, permite envio (fail open) para
    não bloquear o atendimento por causa de observabilidade.
    """
    import time as _t
    cached = _PAUSE_FRANZ_CACHE.get(user_id)
    if cached and _t.time() < cached[1]:
        return cached[0]

    paused = False
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT pause_franz_until FROM phone_health_score WHERE user_id=:id"
            ), {"id": user_id}).fetchone()
            if row and row[0] is not None:
                paused = row[0] > _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    except Exception as e:
        logger.warning(f"[PhoneHealth] Falha ao checar pause_franz_until (user={user_id}): {e}")
        paused = False  # fail open

    _PAUSE_FRANZ_CACHE[user_id] = (paused, _t.time() + _PAUSE_FRANZ_CACHE_TTL)
    return paused


def _invalidate_pause_cache(user_id: int) -> None:
    """Invalida cache de pause pra 1 tenant. Usado após setar pause via endpoint."""
    _PAUSE_FRANZ_CACHE.pop(user_id, None)


def _daily_reset_if_needed():
    """Reseta contadores diários à meia-noite."""
    _RATE_LIMITER.reset_daily_if_needed()


def _check_flood(lead_key: str) -> bool:
    """Retorna True se lead está em flood (deve ser ignorado)."""
    is_flood = _RATE_LIMITER.check_flood(lead_key)
    if is_flood:
        count = len(_RATE_LIMITER.flood_tracker.get(lead_key, []))
        logger.warning(f"🚫 FLOOD detectado: {lead_key} ({count} msgs em {DEFAULT_FLOOD_WINDOW}s) — silenciando {DEFAULT_FLOOD_SILENCE}s")
        return True
    return False


def _check_daily_limit(lead_key: str) -> bool:
    """Retorna True se atingiu limite diário."""
    return _RATE_LIMITER.check_daily_limit(lead_key)


def _increment_daily(lead_key: str):
    _RATE_LIMITER.increment_daily(lead_key)


def _check_cooldown(lead_key: str) -> bool:
    """Retorna True se lead está em cooldown (respondido recentemente)."""
    return _RATE_LIMITER.check_cooldown(lead_key)


def _cooldown_remaining(lead_key: str) -> float:
    return _RATE_LIMITER.cooldown_remaining(lead_key)


def _set_cooldown(lead_key: str):
    _RATE_LIMITER.set_cooldown(lead_key)


def _humanized_delay(reply_text: str) -> float:
    """Calcula delay humanizado variável."""
    return _RATE_LIMITER.humanized_delay(reply_text)


def _activate_human_pause(lead_key: str):
    """Ativa pausa do bot quando dono do número envia msg pro lead."""
    pause_seconds = _RATE_LIMITER.activate_human_pause(lead_key)
    logger.info(f"👤 Human takeover: bot pausado por {pause_seconds/60:.0f}min para {lead_key}")


def _is_human_paused(lead_key: str) -> bool:
    """Retorna True se bot está pausado (humano assumiu temporariamente)."""
    was_paused = lead_key in _RATE_LIMITER.human_pause
    paused = _RATE_LIMITER.is_human_paused(lead_key)
    if was_paused and not paused:
        logger.info(f"👤 Human pause expirou para {lead_key} — bot retoma")
    return paused


def _handle_contacts_upsert(tenant_id: str, contacts: list):
    """Armazena contatos salvos do WhatsApp do dono (evento contacts.upsert)."""
    total = _RATE_LIMITER.handle_contacts_upsert(tenant_id, contacts)
    logger.info(f"📇 Contatos salvos atualizados: tenant={tenant_id}, total={total}")


def _is_saved_contact(tenant_id: str, jid: str) -> bool:
    """Retorna True se o JID é um contato salvo na agenda do dono."""
    return _RATE_LIMITER.is_saved_contact(tenant_id, jid)


def _get_ignore_contacts_setting(user_id: int) -> bool:
    """Verifica se o toggle 'ignorar contatos salvos' está ativo no banco."""
    try:
        settings = _get_sdr_settings(user_id)
        if settings:
            return bool(settings.get("bot_ignore_saved_contacts"))
    except Exception:
        pass
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            row = conn.execute(
                _text("SELECT config_value FROM user_configs WHERE user_id = :uid AND config_key = 'bot_ignore_saved_contacts'"),
                {"uid": user_id}
            ).fetchone()
            return row is not None and str(row[0]).lower() in ("1", "true", "sim")
    except Exception:
        return False


def _debounce_incoming(tenant_id: str, msg_data: dict, executor, loop):
    """Debounce: acumula msgs do mesmo lead antes de processar."""
    key_data = msg_data.get("key", {})
    msg_id = key_data.get("id", "")
    jid = key_data.get("remoteJid", "")

    # Deduplicar por message_id do WhatsApp (race condition fix)
    if msg_id and _is_duplicate_message_id(msg_id):
        print(f"[WPP-Listener] Mensagem duplicada por ID: {msg_id[:16]}... ignorada")
        return

    if "@g.us" in jid:
        return

    # Ignorar contatos salvos na agenda (se toggle ativo)
    if _is_saved_contact(tenant_id, jid):
        user_id = _user_id_from_tenant(tenant_id)
        if user_id is not None and _get_ignore_contacts_setting(user_id):
            return

    # Resolver LID → telefone real (novo protocolo WhatsApp)
    raw_number = _normalizar_tel(jid)
    if "@lid" in jid:
        telefone = _resolver_lid(raw_number)
    else:
        telefone = raw_number

    # Detectar msg enviada pelo dono do número (fromMe) → pausar bot
    if key_data.get("fromMe", False):
        user_id = _user_id_from_tenant(tenant_id)
        if user_id is not None:
            lead_key = f"{user_id}:{telefone}"
            _activate_human_pause(lead_key)
            # Salvar msg do humano no histórico
            msg_content = msg_data.get("message", {})
            texto = (
                msg_content.get("conversation") or
                msg_content.get("extendedTextMessage", {}).get("text") or
                msg_content.get("imageMessage", {}).get("caption") or
                ""
            )
            if texto:
                lead = _buscar_lead_por_tel(telefone, user_id)
                if lead:
                    _salvar_interacao(lead[0], texto, "saida_humano", user_id)
        return

    user_id = _user_id_from_tenant(tenant_id)
    if user_id is None:
        return

    lead_key = f"{user_id}:{telefone}"

    # Extrair texto
    msg_content = msg_data.get("message", {})
    texto = (
        msg_content.get("conversation") or
        msg_content.get("extendedTextMessage", {}).get("text") or
        msg_content.get("imageMessage", {}).get("caption") or
        "[mídia]"
    )

    # Flood check
    if _check_flood(lead_key):
        logger.info(f"🚫 {telefone}: flood ativo, msg ignorada")
        return

    with _DEBOUNCE_LOCK:
        if lead_key in _DEBOUNCE_BUFFER:
            # Já tem buffer — append e resetar timer
            _DEBOUNCE_BUFFER[lead_key]["msgs"].append(texto)
            timer = _DEBOUNCE_BUFFER[lead_key].get("timer")
            if timer:
                timer.cancel()
        else:
            # Novo buffer
            _DEBOUNCE_BUFFER[lead_key] = {
                "msgs": [texto],
                "tenant_id": tenant_id,
                "msg_data": msg_data,
                "timer": None,
            }

        # Criar novo timer
        def _fire():
            with _DEBOUNCE_LOCK:
                entry = _DEBOUNCE_BUFFER.pop(lead_key, None)
            if entry:
                loop.run_in_executor(executor, _processar_mensagem_batch, entry["tenant_id"], entry["msg_data"], entry["msgs"])

        timer = threading.Timer(DEBOUNCE_SECONDS, _fire)
        _DEBOUNCE_BUFFER[lead_key]["timer"] = timer
        timer.start()


def _processar_mensagem_batch(tenant_id: str, msg_data: dict, msgs: List[str]):
    """Processa batch de mensagens acumuladas pelo debounce."""
    print(f"[WPP-Listener] 📦 Batch disparado: {len(msgs)} msgs", flush=True)
    # Juntar msgs em uma só (se múltiplas)
    if len(msgs) > 1:
        texto_final = "\n".join(msgs)
    else:
        texto_final = msgs[0]

    # Injetar texto consolidado no msg_data pra _processar_mensagem usar
    try:
        _processar_mensagem(tenant_id, msg_data, texto_override=texto_final)
    except Exception as e:
        print(f"[WPP-Listener] ❌ Erro em _processar_mensagem: {e}", flush=True)
        import traceback
        traceback.print_exc()

from whatsapp.connection_tracker import (
    _on_qr_timeout,
    _on_qr_success,
    _set_tenant_status,
    _get_tenant_status,
    _CONNECTED_STATUSES,
    is_tenant_connected,
    ESTADO_TO_STAGE,
)

def _normalizar_tel(jid: str) -> str:
    """Extrai número limpo do JID: '5511999@s.whatsapp.net' -> '5511999'"""
    return normalize_jid_number(jid)

def _resolver_lid(lid_number: str) -> str:
    """Resolve LID (novo protocolo WhatsApp) para número real via whatsmeow_lid_map."""
    whatsmeow_db = os.getenv("WHATSMEOW_DB_URL", "").strip()
    if not whatsmeow_db:
        logger.warning("[WPP-Listener] WHATSMEOW_DB_URL ausente; LID mantido sem resolver")
    resolved = resolve_lid_number(lid_number, whatsmeow_db)
    if resolved != lid_number:
        print(f"[WPP-Listener] LID {lid_number} → PN {resolved}", flush=True)
    return resolved

def _user_id_from_tenant(tenant_id: str):
    """Converte tenant_id 'fralib_user_{N}' em int N, ou None se inválido."""
    return user_id_from_tenant(tenant_id)

def _buscar_lead_por_tel(telefone: str, user_id: int):
    """Busca lead no banco pelo telefone ou JID, restrito ao user_id (tenant).
    Tenta com e sem código de país (55) e com/sem 9 extra (BR mobile).
    """
    return find_lead_by_phone_or_jid(telefone, user_id, engine)

def _salvar_interacao(lead_id: str, mensagem: str, direcao: str, user_id: int = None):
    """Salva mensagem na tabela interacoes."""
    try:
        save_interaction(engine, lead_id, mensagem, direcao, user_id)
    except Exception as e:
        logger.warning(f"Erro ao salvar interacao: {e}")

def _atualizar_stage(lead_id: str, sdr_stage: str, user_id: int):
    """Atualiza sdr_stage do lead no banco (escopo ao user_id)."""
    update_lead_stage(engine, lead_id, sdr_stage, user_id)


# Número do closer humano (recebe handoff)
CLOSER_HUMANO = os.getenv("CLOSER_NUMERO", "5541992049684")


def _notificar_handoff_humano(http_client, tenant_id: str, lead_id: str, nome: str, telefone: str, jid: str, meowhats_http: str, user_id: int):
    """
    Notifica o closer humano que um lead está pronto pra fechar.
    Envia resumo do lead + últimas mensagens pro número do closer.
    Franz para de responder (stage=handoff).
    """
    if not is_tenant_connected(tenant_id):
        logger.warning(
            f"Handoff de {nome} NAO notificado: tenant {tenant_id} desconectado "
            f"(status '{_get_tenant_status(tenant_id) or 'unknown'}')."
        )
        return
    try:
        # Buscar últimas interações (filtradas por ownership via JOIN com leads)
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT i.mensagem, i.direcao FROM interacoes i
                JOIN leads l ON l.id = i.lead_id
                WHERE i.lead_id = :lid AND l.user_id = :uid
                ORDER BY i.criado_em DESC LIMIT 6
            """), {"lid": lead_id, "uid": user_id}).fetchall()

        historico = "\n".join([
            f"{'👤 Lead' if r[1] == 'entrada' else '🤖 Franz'}: {r[0][:80]}"
            for r in reversed(rows)
        ]) if rows else "(sem histórico)"

        # Montar mensagem pro closer
        tel_mask = telefone[-4:] if telefone else "????"
        resumo = (
            f"🔥 *LEAD QUENTE — Pronto pra fechar!*\n\n"
            f"👤 *{nome}*\n"
            f"📱 Número: {telefone}\n"
            f"💬 Link direto: wa.me/{telefone}\n\n"
            f"_Últimas mensagens:_\n{historico}\n\n"
            f"⚡ Responda direto pro lead neste número.\n"
            f"Franz já parou de responder."
        )

        # Enviar pro closer humano
        meowhats_http_real = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        send_handoff_notification(
            http_client,
            meowhats_http_real,
            MEOWHATS_KEY,
            tenant_id,
            CLOSER_HUMANO,
            resumo,
        )
        logger.info(f"🔥 Handoff: lead {nome} ({tel_mask}) → closer humano {CLOSER_HUMANO}")

    except Exception as e:
        logger.error(f"Erro no handoff: {e}")

def _processar_mensagem(tenant_id: str, msg_data: dict, texto_override: str = None):
    """Processa mensagem recebida de um lead (com anti-ban integrado)."""
    try:
        user_id = _user_id_from_tenant(tenant_id)
        if user_id is None:
            logger.warning(f"tenant_id invalido '{tenant_id}' — mensagem descartada (multi-tenant)")
            return
        key = msg_data.get("key", {})
        from_me = bool(key.get("fromMe", False))

        jid = key.get("remoteJid", "")
        # Ignorar grupos
        if "@g.us" in jid:
            return

        # Resolver LID → telefone real
        raw_number = _normalizar_tel(jid)
        if "@lid" in jid:
            telefone = _resolver_lid(raw_number)
        else:
            telefone = raw_number
        push_name = msg_data.get("pushName", "")

        # Usar texto override (do debounce batch) ou extrair do msg_data
        if texto_override:
            texto = texto_override
        else:
            msg_content = msg_data.get("message", {})
            texto = (
                msg_content.get("conversation") or
                msg_content.get("extendedTextMessage", {}).get("text") or
                msg_content.get("imageMessage", {}).get("caption") or
                "[mídia]"
            )

        print(f"[WPP-Listener] Mensagem de {telefone} ({push_name}): {texto[:60]}", flush=True)

        # Buscar lead no banco (escopo ao user_id do tenant)
        lead = _buscar_lead_por_tel(telefone, user_id)
        if not lead:
            print(f"[WPP-Listener] Lead não encontrado para {telefone} — ignorando", flush=True)
            return

        lead_id, nome, segmento, cidade, sdr_stage_atual, status, tel_raw = lead
        lead_key = f"{user_id}:{telefone}"

        # ── Retroalimentacao: lead enviou URL de site proprio no WhatsApp?
        #    Atualiza lead_inventory.website para que o Caio nao some +20 pts
        #    por "sem site (oportunidade)" indevidamente.
        #    Constraints: NAO toca em site publicado (status='site_done') e
        #    NAO sobrescreve site valido ja conhecido.
        try:
            from whatsapp.interactions import extrair_url_website
            _url_site = extrair_url_website(texto)
            if _url_site:
                with engine.connect() as _conn_url:
                    _upd = _conn_url.execute(
                        text(
                            """
                            UPDATE lead_inventory
                            SET website = :url, atualizado_em = NOW()
                            WHERE lead_id = :lid
                              AND tenant_id = :uid
                              AND status <> 'site_done'
                              AND (website IS NULL OR website = '')
                            RETURNING id
                            """
                        ),
                        {"url": _url_site, "lid": lead_id, "uid": user_id},
                    )
                    if _upd.fetchone():
                        _conn_url.commit()
                        logger.info(
                            f"\U0001f517 Lead {nome}: website retroalimentado "
                            f"via WhatsApp → {_url_site}"
                        )
        except Exception as _werr:
            # IMPORTANTE: retroalimentacao NAO pode quebrar o handler.
            # Segue o fluxo normal (salvar interacao + Franz).
            logger.warning(
                f"[WPP-Listener] retroalimentacao website falhou (nao-bloqueante): {_werr}"
            )

        if from_me:
            try:
                with engine.connect() as conn:
                    last_bot = conn.execute(text("""
                        SELECT mensagem FROM interacoes
                        WHERE lead_id=:lead_id AND user_id=:user_id AND direcao='saida'
                        ORDER BY criado_em DESC LIMIT 1
                    """), {"lead_id": lead_id, "user_id": user_id}).scalar() or ""
                # Ignore echoes of messages the bot just sent through the same device.
                if texto.strip() and texto.strip() not in (last_bot or ""):
                    _salvar_interacao(lead_id, texto, "humano", user_id)
                    _activate_human_pause(lead_key)
                    try:
                        from agents.sdr_langgraph.learning import record_human_correction
                        record_human_correction(
                            user_id=user_id,
                            lead_id=lead_id,
                            agent="human",
                            human_message=texto,
                            previous_bot_message=last_bot,
                            context=f"stage={sdr_stage_atual}; lead={nome}; segmento={segmento}",
                        )
                    except Exception as learn_err:
                        logger.warning(f"Lead {nome}: erro ao registrar aprendizado humano: {learn_err}")
                    logger.info(f"👤 {nome}: mensagem humana detectada; bot pausado e aprendizado registrado")
                return
            except Exception as human_err:
                logger.warning(f"Lead {nome}: erro ao processar mensagem fromMe/humana: {human_err}")
                return

        # ── GATE DE BILLING — trial expirado ou sem créditos = bot silenciado ──
        if not _user_can_use_bot(user_id):
            logger.warning(f"🚫 {nome}: tenant {user_id} sem plano ativo/trial expirado — bot silenciado")
            return

        # ── GATE PHONE HEALTH — pause_franz_until (Trilha A) ─────────────
        # Freio de emergência: se o superadmin ou o próprio tenant pausou o
        # Franz via /api/{admin,superadmin}/phone-health/pause, bloqueia o envio.
        if _is_tenant_franz_paused(user_id):
            logger.warning(f"📴 {nome}: Franz pausado para tenant {user_id} (phone_health.pause_franz_until) — bot silenciado")
            return

        # Salvar wpp_jid se diferente do telefone (LID de conta business)
        raw_jid = jid.split('@')[0]
        if raw_jid != telefone and len(raw_jid) > 5:
            try:
                with engine.connect() as conn:
                    conn.execute(text("UPDATE leads SET wpp_jid=:jid WHERE id=:id AND user_id=:uid AND (wpp_jid IS NULL OR wpp_jid != :jid)"),
                                 {"jid": raw_jid, "id": lead_id, "uid": user_id})
                    conn.commit()
            except Exception:
                pass

        # ── CONTENT-BASED DEDUP (3ª camada anti-bug-3x) ────────────────
        # Cada msg duplicada do WhatsApp vem com message_id ÚNICO
        # (porque o MeoWhats regenera ID em cada reenvio).
        # O dedup por msg_id NÃO detecta. Aqui dedupamos por CONTEÚDO:
        # se a mesma msg do mesmo lead chegou nos últimos 5s, ignora.
        try:
            content_hash = hashlib.sha256(f"{telefone}:{texto}".encode()).hexdigest()[:32]
            with engine.connect() as conn:
                r = conn.execute(text("""
                    SELECT criado_em FROM interacoes
                    WHERE lead_id = :lid AND user_id = :uid
                      AND direcao = 'entrada'
                      AND mensagem = :msg
                      AND criado_em > to_char(NOW() - CAST('5 seconds' AS INTERVAL), 'YYYY-MM-DD\"T\"HH24:MI:SS')
                    LIMIT 1
                """), {"lid": lead_id, "uid": user_id, "msg": texto})
                if r.fetchone():
                    print(f"[WPP-Listener] Mensagem duplicada por CONTEUDO (5s): {nome} - ignorada")
                    return
        except Exception as _cd_err:
            logger.warning(f"[WPP-Listener] content dedup falhou (nao-bloqueante): {_cd_err}")

        # ── WPP LOCK ATÔMICO (4ª camada anti-bug-3x) ───────────────────
        # Usa wpp_lock_until na tabela leads para garantir que apenas 1 processo
        # processa msgs deste lead por vez, mesmo entre múltiplas instâncias.
        # SELECT FOR UPDATE SKIP LOCKED: se outra instância já tem o lock,
        # esta instância pula e ignora a mensagem (já está sendo processada).
        _acquired_lock = False
        _lock_lead_id = lead_id
        try:
            with engine.connect() as _lock_conn:
                # Tenta adquirir lock: atualiza wpp_lock_until para NOW() + 30s
                # apenas se NULL (não está bloqueado) OU se expirou
                _result = _lock_conn.execute(text("""
                    UPDATE leads
                    SET wpp_lock_until = NOW() + INTERVAL '30 seconds'
                    WHERE id = :lid
                      AND (wpp_lock_until IS NULL OR wpp_lock_until < NOW())
                    RETURNING id
                """), {"lid": lead_id})
                _lock_conn.commit()
                if _result.rowcount == 0:
                    # Outra instância está processando — ignorar esta msg
                    print(f"[WPP-Listener] {nome}: lock WPP ativo por outra instância — msg ignorada")
                    return
                _acquired_lock = True
        except Exception as _lock_err:
            logger.warning(f"[WPP-Listener] wpp_lock falhou: {_lock_err}")
            # Se lock falhar por DB, prosseguir com processamento (fail-open parcial)

        # Função helper para liberar lock ao fim do processamento
        def _release_wpp_lock():
            if not _acquired_lock:
                return
            try:
                with engine.connect() as _rl_conn:
                    _rl_conn.execute(text("""
                        UPDATE leads SET wpp_lock_until = NULL
                        WHERE id = :lid AND wpp_lock_until > NOW()
                    """), {"lid": _lock_lead_id})
                    _rl_conn.commit()
            except Exception:
                pass

        # Salvar mensagem recebida sempre (histórico)
        _salvar_interacao(lead_id, texto, "entrada", user_id)

        # Só responder se o site já foi deployado (status=concluido) e Franz já iniciou contato
        if status != "concluido":
            print(f"[WPP-Listener] Lead {nome}: status={status} — aguardando deploy antes de responder", flush=True)
            return
        if not sdr_stage_atual:
            print(f"[WPP-Listener] Lead {nome}: sdr_stage vazio — Franz ainda não iniciou contato", flush=True)
            return

        # Se stage é qualificados/ganhos/perdidos → Franz NÃO responde mais (humano assumiu)
        if sdr_stage_atual in ('qualificados', 'ganhos', 'perdidos', 'handoff', 'won', 'lost'):
            logger.info(f"Lead {nome}: stage={sdr_stage_atual} — humano assumiu, Franz parado")
            return

        sdr_settings = _get_sdr_settings(user_id)
        opt_out_like = bool(re.search(r"\b(stop|parar|pare|remover|sair|nao quero|não quero)\b", texto.lower()))
        if opt_out_like:
            _atualizar_stage(lead_id, "perdidos", user_id)
            logger.info(f"Lead {nome}: opt-out detectado — bot encerrado antes de chamar IA")
            return
        if (
            sdr_settings.get("response_mode") == "same_as_outbound"
            and not opt_out_like
            and not is_within_outbound_schedule(sdr_settings)
        ):
            logger.info(f"⏰ {nome}: resposta fora do horario configurado — aguardando janela")
            return

        # ── ANTI-BAN CHECKS ──────────────────────────────────────────
        # Human takeover: dono do número está conversando manualmente
        if _is_human_paused(lead_key):
            activated_at = _RATE_LIMITER.human_pause.get(lead_key, _time.time())
            remaining = _human_pause_seconds_for_key(lead_key) - (_time.time() - activated_at)
            logger.info(f"👤 {nome}: humano ativo, bot pausado ({remaining:.0f}s restantes)")
            return

        # Cooldown: não responder se já respondeu recentemente
        if _check_cooldown(lead_key):
            remaining = _cooldown_remaining(lead_key)
            logger.info(
                f"⏳ {nome}: cooldown ativo ({_cooldown_seconds_for_key(lead_key)}s) "
                f"— aguardando {remaining:.1f}s antes de responder"
            )
            if remaining > 0:
                _time.sleep(min(remaining, _cooldown_seconds_for_key(lead_key)))

        # Limite diário
        if _check_daily_limit(lead_key):
            logger.warning(f"🚫 {nome}: limite diário ({_daily_limit_for_key(lead_key)} msgs) atingido — Franz silenciado")
            return

        if not is_tenant_connected(tenant_id):
            current = _get_tenant_status(tenant_id) or "unknown"
            logger.warning(
                f"Lead {nome}: resposta bloqueada — tenant {tenant_id} esta em status '{current}'."
            )
            return

        # ── PRÉ-PROCESSADOR: detecta bot/auto-resposta/mídia ANTES do Franz ──
        # Evita que Franz responda a bots assistentes (Monica, Bia) ou mande SPAM
        # quando lead manda msg longa de opt-out/ausencia. Tambem detecta midia
        # sem texto (imagem/audio sem legenda) e responde pedindo descricao.
        msg_data_for_pp = {"contextInfo": msg_data.get("contextInfo", {})} if msg_data else None
        should_respond, auto_reply = should_franz_respond(texto, msg_data_for_pp)
        if not should_respond:
            if auto_reply:
                # Responder com auto-reply (handoff ou ask_human) - NAO chama Franz
                logger.info(f"[WPP-Listener] {nome}: pre-processor desviou do Franz (handoff/ask_human)")
                # Aqui idealmente enviariamos via MeoWhats, mas como o
                # pre-processador so classifica, apenas NAO chamamos Franz.
                # O reply do auto-reply pode ser implementado depois.
                return
            else:
                # Silencio total (no_response - ex: msg de ausencia)
                logger.info(f"[WPP-Listener] {nome}: pre-processor pediu silencio (no_response)")
                return

        # Chamar Franz para gerar resposta
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))

        history = []
        try:
            # Pega contexto completo (ate 100 msgs) com summary se > 30.
            # Isso garante que o Franz sabe o que foi conversado antes.
            history = get_full_context(engine, lead_id, user_id)
        except Exception as hist_err:
            logger.warning(f"Lead {nome}: erro ao carregar historico SDR: {hist_err}")

        # ── LIMITE 1 msg Franz por turno (anti-SPAM) ──────────────────
        # Se ja enviamos saida nos ultimos 60s E o lead nao mandou nada novo,
        # NAO responder de novo. Isso evita o "loop de 5 msgs" visto em producao
        # onde Franz mandava 5 msgs em sequencia (introducao + oferta + explicacao + pergunta).
        try:
            with engine.connect() as conn:
                # OPTIMIZADO: 1 query em vez de 2 (N+1 fix)
                row = conn.execute(text("""
                    SELECT
                        MAX(CASE WHEN direcao = 'saida' THEN criado_em END) as last_outbound,
                        MAX(CASE WHEN direcao = 'entrada' THEN criado_em END) as last_inbound
                    FROM interacoes
                    WHERE lead_id = :lid AND user_id = :uid
                """), {"lid": lead_id, "uid": user_id}).fetchone()
                last_outbound = row.last_outbound if row else None
                last_inbound = row.last_inbound if row else None
                if last_outbound and last_inbound:
                    # So bloqueia se: ultima saida foi DEPOIS da ultima entrada
                    # (significa que Franz ja respondeu a esta msg)
                    if str(last_outbound) > str(last_inbound):
                        logger.info(f"[WPP-Listener] {nome}: Franz ja respondeu a esta msg - nao duplicar")
                        return
        except Exception as _ts_err:
            logger.warning(f"[WPP-Listener] one-per-turn check falhou (nao-bloqueante): {_ts_err}")

        from agents.sdr_langgraph import responder_lead
        franz_output = responder_lead(
            telefone=tel_raw,
            mensagem_recebida=texto,
            nome_negocio=nome or push_name,
            lead_id=lead_id,
            cidade=cidade or "",
            segmento=segmento or "",
            history=history,
            sdr_stage=sdr_stage_atual or "",
            user_id=user_id,
        )
        resposta = franz_output.reply
        proximo_passo = franz_output.proximo_passo or ""

        # ── DETECÇÃO PASSIVA: opt_out cancelado ──
        # Se Franz ta com opt_out_pending=True e lead respondeu 'nao/continua',
        # o lead cancelou opt_out. Lesson importante: NAO classificar msgs ambiguas.
        try:
            with engine.connect() as conn:
                pending_row = conn.execute(text("""
                    SELECT opt_out_pending FROM leads
                    WHERE id = :lid AND user_id = :uid
                """), {"lid": lead_id, "uid": user_id}).fetchone()
            if pending_row and pending_row[0] is True:
                # Lead ta com opt_out_pending - checar se respondeu cancelando
                from agents.sdr_langgraph.learning import record_opt_out_canceled
                cancel_result = record_opt_out_canceled(
                    user_id=user_id, lead_id=lead_id,
                    bot_question="Voce quer parar de receber mensagens?",
                    lead_response=texto,
                    context=f"segmento={segmento}",
                )
                if cancel_result.get("learned"):
                    logger.info(f"[WPP-Listener] {nome}: opt_out cancelado pelo lead - lesson criada")
        except Exception as _oc_err:
            logger.warning(f"[WPP-Listener] opt_out cancel check falhou (nao-bloqueante): {_oc_err}")

        # ── APRENDIZADO PASSIVO (auto-learning por observação) ──
        # Detecta sinais automaticamente e cria lessons pra próximo turno:
        # - Reclamação do lead ("entendeu errado", "sua IA não entendeu")
        # - Engajamento positivo (lead pede link, elogia, manda sinal de compra)
        # - Opt-out cancelado (lead respondeu "nao" depois de Franz perguntar)
        # Inspirado em Meta WhatsApp Business AI, Chatwoot AI, Respond.io
        try:
            from agents.sdr_langgraph.learning import (
                record_lead_complaint,
                record_lead_engagement,
            )
            # Buscar ultima msg do bot pra contexto
            with engine.connect() as conn:
                last_bot_row = conn.execute(text("""
                    SELECT mensagem FROM interacoes
                    WHERE lead_id = :lid AND user_id = :uid AND direcao = 'saida'
                    ORDER BY criado_em DESC LIMIT 1
                """), {"lid": lead_id, "uid": user_id}).fetchone()
            last_bot_msg = last_bot_row[0] if last_bot_row else ""

            # Detectar reclamacao (passivo)
            complaint_result = record_lead_complaint(
                user_id=user_id, lead_id=lead_id,
                lead_message=texto,
                previous_bot_message=last_bot_msg,
                context=f"stage={sdr_stage_atual}; segmento={segmento}",
            )
            if complaint_result.get("learned"):
                logger.info(f"[WPP-Listener] {nome}: complaint detectado - lesson criada ({complaint_result.get('kinds')})")

            # Detectar engajamento positivo (passivo)
            positive_result = record_lead_engagement(
                user_id=user_id, lead_id=lead_id,
                lead_message=texto,
                previous_bot_message=last_bot_msg,
                context=f"stage={sdr_stage_atual}; segmento={segmento}",
            )
            if positive_result.get("learned"):
                logger.info(f"[WPP-Listener] {nome}: engagement positivo - lesson criada ({positive_result.get('kinds')})")
        except Exception as learn_err:
            logger.warning(f"[WPP-Listener] auto-learning falhou (nao-bloqueante): {learn_err}")

        # Se reply vazio (opt_out, fila, etc) — não enviar
        if not resposta or not resposta.strip():
            logger.info(f"Lead {nome}: Franz retornou reply vazio (intent={franz_output.intent}) — não envia")
            if franz_output.next_stage == "lost":
                _atualizar_stage(lead_id, "perdidos", user_id)
            return

        def _retry_extractor(raw_reply):
            from agents.llm_direct import call_claude

            return call_claude(
                system="Voce recebe um JSON malformado de um chatbot. Extraia APENAS o texto da mensagem que seria enviada ao cliente. Retorne SOMENTE o texto puro, sem JSON, sem aspas, sem formatacao.",
                user=f"Extraia a mensagem do cliente deste JSON:\n{raw_reply[:1000]}",
                model="haiku",
                max_tokens=500,
                temperature=0.0,
            )

        # Detecta QUALQUER formato de JSON retornado pelo LLM:
        # - { no inicio (JSON cru)
        # - "resposta" (campo PT)
        # - "novo_stage" (campo PT)
        # - "reply" (campo EN)
        # - ```json (markdown code block)
        # Sem essa deteccao completa, JSON do LLM vaza pro lead como texto cru!
        looks_like_json = (
            resposta.strip().startswith('{')
            or '"resposta"' in resposta
            or '"novo_stage"' in resposta
            or '"reply"' in resposta
            or resposta.strip().startswith('```json')
            or resposta.strip().startswith('```')
            or resposta.lstrip().startswith('```json')
        )
        if looks_like_json:
            logger.warning(f"[SDR][BUG] Resposta com JSON para lead={nome}: {resposta[:200]}")
            # Tentar regex primeiro - SEM chamar LLM extra para evitar 2 mensagens diferentes
            # NAO USA FALLBACK - se falhar, nao envia nada
            try:
                resposta_sanitizada = sanitize_reply(franz_output.reply, retry_extractor=None)
                if resposta_sanitizada and not resposta_sanitizada.startswith('{') and '"resposta"' not in resposta_sanitizada and '"reply"' not in resposta_sanitizada:
                    resposta = resposta_sanitizada
                else:
                    raise ValueError("sanitize_reply retornou resultado invalido")
            except ValueError as e:
                logger.error(f"[SDR][FALHA] Nao conseguiu sanitizar resposta para {nome}: {e}. Mensagem NAO enviada.")
                return  # NAO envia lixo para o cliente

        try:
            from agents.sdr_langgraph import learning as _learning_module
        except Exception:
            _learning_module = None
        format_outgoing_messages = get_outgoing_formatter(_learning_module)

        if is_duplicate_reply(history, resposta):
            logger.warning(f"Lead {nome}: resposta duplicada detectada — nao envia")
            return

        # Converter estado Franz → stage kanban via mapeamento
        _raw_stage, novo_stage = map_next_stage(franz_output.next_stage, sdr_stage_atual, ESTADO_TO_STAGE)

        # ── RESPONSE EXECUTOR: guard → send → persist → advance stage ──
        import httpx
        meowhats_http = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        with httpx.Client(timeout=15) as http_client:
            exec_ctx = ExecutionContext(
                engine=engine,
                http_client=http_client,
                meowhats_http=meowhats_http,
                meowhats_key=MEOWHATS_KEY,
                tenant_id=tenant_id,
                jid=jid,
                lead_id=lead_id,
                lead_name=nome or push_name,
                telefone=telefone,
                user_id=user_id,
                segmento=segmento or "",
                status=status,
                sdr_stage_atual=sdr_stage_atual or "",
                novo_stage=novo_stage,
                raw_stage=_raw_stage,
                resposta=resposta,
                resposta_partes=format_outgoing_messages(resposta),
                franz_output=franz_output,
                opt_out=opt_out_like,
                prior_outbound=False,
                lead_key=lead_key,
                is_tenant_connected_fn=is_tenant_connected,
                get_tenant_status_fn=_get_tenant_status,
                set_cooldown_fn=_set_cooldown,
                increment_daily_fn=_increment_daily,
                notify_handoff_fn=_notificar_handoff_humano,
                save_interaction_fn=_salvar_interacao,
                update_stage_fn=_atualizar_stage,
                humanized_delay_fn=_humanized_delay,
            )
            execute_response(exec_ctx)
            _release_wpp_lock()

    except Exception as e:
        _release_wpp_lock()
        logger.error(f"Erro ao processar mensagem: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def _conectar_e_ouvir():
    """Conecta ao WebSocket do meowhats e processa eventos."""
    if not MEOWHATS_KEY:
        raise RuntimeError("MEOWHATS_KEY ausente; listener WhatsApp bloqueado em fail-closed")

    ws_url = f"{MEOWHATS_URL}/ws"
    headers = {"X-API-Key": MEOWHATS_KEY}

    print(f"[WPP-Listener] Conectando ao meowhats WebSocket: {ws_url}", flush=True)

    loop = asyncio.get_event_loop()
    from concurrent.futures import ThreadPoolExecutor
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="wpp-msg")

    async with websockets.connect(
        ws_url,
        additional_headers=headers,
        ping_interval=30,
        ping_timeout=None,
        close_timeout=5,
    ) as ws:
        print("[WPP-Listener] ✅ Conectado ao meowhats WebSocket", flush=True)
        async for raw in ws:
            try:
                event = json.loads(raw)
                event_type = event.get("type", "")
                
                if event_type == "message":
                    data = event.get("data", {})
                    tenant_id = data.get("tenantId")
                    if not tenant_id:
                        logger.warning("Mensagem recebida sem tenantId — descartada (multi-tenant)")
                        continue
                    msg_data  = data.get("message", {})
                    # Anti-ban: debounce antes de processar (agrupa msgs rápidas)
                    _debounce_incoming(tenant_id, msg_data, _executor, loop)
                    
                elif event_type == "connection.update":
                    data = event.get("data", {})
                    tenant_id = data.get("tenantId") or ""
                    status = data.get("status") or ""
                    if tenant_id:
                        _old_status = _get_tenant_status(tenant_id)
                        _set_tenant_status(tenant_id, status)

                        # QR timeout tracking (anti-loop zumbi)
                        if status == "qr" and _old_status == "qr":
                            if not _on_qr_timeout(tenant_id):
                                # Max retries atingido — não processar mais
                                continue
                        elif status in _CONNECTED_STATUSES:
                            _on_qr_success(tenant_id)

                        # Alertar usuário quando WPP desconecta
                        if status in ("qr", "disconnected", "logged_out") and _old_status in _CONNECTED_STATUSES:
                            try:
                                import json as _json_wpp
                                _uid_num = int(tenant_id.replace("fralib_user_", "")) if "fralib_user_" in tenant_id else None
                                if _uid_num:
                                    from endpoints.sse_endpoints import adicionar_log
                                    adicionar_log(_json_wpp.dumps({
                                        "type": "pipeline_warning",
                                        "error_code": "WPP_DISCONNECTED",
                                        "severity": "warning",
                                        "title": "WhatsApp desconectou",
                                        "message": "Sua sessão WhatsApp caiu. Reconecte no painel para continuar enviando mensagens.",
                                    }), "PIPELINE_STATUS", user_id=_uid_num)
                            except Exception as _wpp_alert_err:
                                logger.debug(f"WPP alert SSE falhou: {_wpp_alert_err}")
                    # Avisar quando o pareamento e recusado por hijack tentativo
                    if status == "rejected":
                        logger.warning(f"Conexão WPP RECUSADA: tenant={tenant_id} — {data.get('error', '')}")
                    else:
                        logger.info(f"Conexão WPP: tenant={tenant_id} status={status}")

                elif event_type == "contacts.upsert":
                    data = event.get("data", {})
                    tenant_id = data.get("tenantId") or ""
                    contacts = data.get("contacts", [])
                    if tenant_id and contacts:
                        _handle_contacts_upsert(tenant_id, contacts)
                    
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.error(f"Erro no evento: {e}")

async def iniciar_listener(retry_delay: int = 5):
    """Loop com reconexão automática."""
    while True:
        try:
            await _conectar_e_ouvir()
        except Exception as e:
            print(f"[WPP-Listener] ⚠️ WebSocket desconectado: {e}. Reconectando em {retry_delay}s...", flush=True)
            await asyncio.sleep(retry_delay)

def start_background_listener():
    """Inicia o listener em background thread (chamado pelo server.py no startup)."""
    import threading

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(iniciar_listener())

    t = threading.Thread(target=_run, daemon=True, name="whatsapp-listener")
    t.start()
    logger.info("WhatsApp listener iniciado em background")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_os.path.join(_os.path.dirname(_here), ".env"), override=False)
    load_dotenv(dotenv_path=_os.path.join(_here, ".env"), override=False)
    asyncio.run(iniciar_listener())
