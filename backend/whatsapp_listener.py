"""
whatsapp_listener.py — Listener WebSocket do meowhats
Fica conectado ao meowhats e processa mensagens recebidas dos leads.
Quando um lead responde, chama Bryan e atualiza sdr_stage no banco.
"""
import asyncio
import json
import os
import re
import random
import threading
import logging
import time as _time
from datetime import datetime, date as _date_type
from typing import Dict, List

import websockets
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
DEBOUNCE_SECONDS = 4.0

# 2. Cooldown: não responder ao mesmo lead mais de 1x a cada 30s
_LEAD_LAST_REPLY: Dict[str, float] = {}
COOLDOWN_SECONDS = 0.0  # DESABILITADO PRA TESTE (era 30.0)

# 3. Flood detection: >10 msgs em 60s = silêncio por 5min
_FLOOD_TRACKER: Dict[str, List[float]] = {}
FLOOD_THRESHOLD = 10
FLOOD_WINDOW = 60.0
FLOOD_SILENCE = 300.0
_FLOOD_SILENCED: Dict[str, float] = {}

# 4. Limite diário: max 20 respostas/dia por lead
_DAILY_COUNT: Dict[str, int] = {}
_DAILY_DATE: str = ""
DAILY_LIMIT = 50

# 5. Gate de billing: cache por user_id (evita query a cada msg)
_BILLING_CACHE: Dict[int, tuple] = {}  # user_id -> (can_use: bool, expires_at: float)
_BILLING_CACHE_TTL = 120.0  # 2 minutos


def _user_can_use_bot(user_id: int) -> bool:
    """Verifica se tenant tem plano ativo ou trial válido. Cache de 2min."""
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
                # Plano pago ativo → bot sempre liberado (créditos controlam pipeline, não bot)
                if plano_pago:
                    can_use = True
                # Trial ainda válido com créditos → OK
                elif plano == 'trial' and trial_exp:
                    from datetime import date as _d
                    exp = _d.fromisoformat(str(trial_exp)[:10])
                    if _d.today() <= exp and (creditos is None or creditos > 0):
                        can_use = True
                # Status bloqueado/suspenso → NUNCA
                if status in ('bloqueado', 'suspenso', 'cancelado'):
                    can_use = False
    except Exception as e:
        # Se DB falhar, permitir (fail-open pra não silenciar todos)
        logger.error(f"[Billing Gate] Erro ao verificar user {user_id}: {e}")
        can_use = True

    _BILLING_CACHE[user_id] = (can_use, _t.time() + _BILLING_CACHE_TTL)
    return can_use


def _daily_reset_if_needed():
    """Reseta contadores diários à meia-noite."""
    global _DAILY_COUNT, _DAILY_DATE
    hoje = _date_type.today().isoformat()
    if _DAILY_DATE != hoje:
        _DAILY_COUNT = {}
        _DAILY_DATE = hoje


def _check_flood(lead_key: str) -> bool:
    """Retorna True se lead está em flood (deve ser ignorado)."""
    now = _time.time()
    # Checar se está silenciado
    if lead_key in _FLOOD_SILENCED:
        if now - _FLOOD_SILENCED[lead_key] < FLOOD_SILENCE:
            return True
        else:
            del _FLOOD_SILENCED[lead_key]

    # Registrar timestamp
    if lead_key not in _FLOOD_TRACKER:
        _FLOOD_TRACKER[lead_key] = []
    _FLOOD_TRACKER[lead_key].append(now)
    # Limpar timestamps antigos
    _FLOOD_TRACKER[lead_key] = [t for t in _FLOOD_TRACKER[lead_key] if now - t < FLOOD_WINDOW]

    if len(_FLOOD_TRACKER[lead_key]) > FLOOD_THRESHOLD:
        _FLOOD_SILENCED[lead_key] = now
        logger.warning(f"🚫 FLOOD detectado: {lead_key} ({len(_FLOOD_TRACKER[lead_key])} msgs em {FLOOD_WINDOW}s) — silenciando {FLOOD_SILENCE}s")
        return True
    return False


def _check_daily_limit(lead_key: str) -> bool:
    """Retorna True se atingiu limite diário."""
    _daily_reset_if_needed()
    return _DAILY_COUNT.get(lead_key, 0) >= DAILY_LIMIT


def _increment_daily(lead_key: str):
    _daily_reset_if_needed()
    _DAILY_COUNT[lead_key] = _DAILY_COUNT.get(lead_key, 0) + 1


def _check_cooldown(lead_key: str) -> bool:
    """Retorna True se lead está em cooldown (respondido recentemente)."""
    last = _LEAD_LAST_REPLY.get(lead_key, 0)
    return (_time.time() - last) < COOLDOWN_SECONDS


def _set_cooldown(lead_key: str):
    _LEAD_LAST_REPLY[lead_key] = _time.time()


def _humanized_delay(reply_text: str) -> float:
    """Calcula delay humanizado variável."""
    # TESTE: delay mínimo pra debug
    return 2.0


# 5. Human takeover pause: dono do número mandou msg → bot pausa
_HUMAN_PAUSE: Dict[str, float] = {}
HUMAN_PAUSE_SECONDS = 300.0  # 5 minutos de pausa quando dono intervém

# 6. Ignorar contatos salvos: bot não responde quem está na agenda do dono
_SAVED_CONTACTS: Dict[str, set] = {}  # tenant_id → set de JIDs salvos


def _activate_human_pause(lead_key: str):
    """Ativa pausa do bot quando dono do número envia msg pro lead."""
    _HUMAN_PAUSE[lead_key] = _time.time()
    logger.info(f"👤 Human takeover: bot pausado por {HUMAN_PAUSE_SECONDS/60:.0f}min para {lead_key}")


def _is_human_paused(lead_key: str) -> bool:
    """Retorna True se bot está pausado (humano assumiu temporariamente)."""
    if lead_key not in _HUMAN_PAUSE:
        return False
    elapsed = _time.time() - _HUMAN_PAUSE[lead_key]
    if elapsed >= HUMAN_PAUSE_SECONDS:
        del _HUMAN_PAUSE[lead_key]
        logger.info(f"👤 Human pause expirou para {lead_key} — bot retoma")
        return False
    return True


def _handle_contacts_upsert(tenant_id: str, contacts: list):
    """Armazena contatos salvos do WhatsApp do dono (evento contacts.upsert)."""
    if tenant_id not in _SAVED_CONTACTS:
        _SAVED_CONTACTS[tenant_id] = set()
    for c in contacts:
        jid = c.get("jid", "")
        if jid and "@s.whatsapp.net" in jid:
            _SAVED_CONTACTS[tenant_id].add(jid)
    logger.info(f"📇 Contatos salvos atualizados: tenant={tenant_id}, total={len(_SAVED_CONTACTS[tenant_id])}")


def _is_saved_contact(tenant_id: str, jid: str) -> bool:
    """Retorna True se o JID é um contato salvo na agenda do dono."""
    return jid in _SAVED_CONTACTS.get(tenant_id, set())


def _get_ignore_contacts_setting(user_id: int) -> bool:
    """Verifica se o toggle 'ignorar contatos salvos' está ativo no banco."""
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
    jid = key_data.get("remoteJid", "")
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

# Cache do status de conexao por tenant, alimentado por eventos connection.update
# do meowhats. Multi-tenant pos-fix (2026-05-13): meowhats emite "connected",
# "pairing", "rejected", "logged_out", "disconnected", "reconnecting", "qr",
# "timeout". So "connected" significa que o device esta pareado e pronto para
# enviar mensagens.
_TENANT_STATUS: dict[str, str] = {}
_TENANT_STATUS_LOCK = threading.Lock()
_CONNECTED_STATUSES = frozenset({"connected", "open", "authenticated"})

# Contador de QR timeouts por tenant (anti-loop zumbi)
_QR_TIMEOUT_COUNT: dict[str, int] = {}
_QR_MAX_RETRIES = 3


def _on_qr_timeout(tenant_id: str) -> bool:
    """Chamado quando QR code expira sem ser escaneado. Retorna False se deve parar."""
    _QR_TIMEOUT_COUNT[tenant_id] = _QR_TIMEOUT_COUNT.get(tenant_id, 0) + 1
    count = _QR_TIMEOUT_COUNT[tenant_id]
    if count >= _QR_MAX_RETRIES:
        print(f"[WPP] {tenant_id}: QR timeout {count}x — parando tentativas. Reconectar manualmente.")
        return False
    print(f"[WPP] {tenant_id}: QR timeout ({count}/{_QR_MAX_RETRIES})")
    return True


def _on_qr_success(tenant_id: str):
    """Chamado quando QR é escaneado com sucesso."""
    _QR_TIMEOUT_COUNT.pop(tenant_id, None)


def _set_tenant_status(tenant_id: str, status: str) -> None:
    if not tenant_id or not status:
        return
    with _TENANT_STATUS_LOCK:
        _TENANT_STATUS[tenant_id] = status


def _get_tenant_status(tenant_id: str) -> str:
    if not tenant_id:
        return ""
    with _TENANT_STATUS_LOCK:
        return _TENANT_STATUS.get(tenant_id, "")


def is_tenant_connected(tenant_id: str, *, fallback_http: bool = True) -> bool:
    """Retorna True se o tenant esta com WhatsApp pareado e pronto para envio.

    Usa o cache local (alimentado pelo WebSocket). Se o cache esta vazio para
    aquele tenant e fallback_http=True, consulta GET /api/sessions/{id}/status
    e cacheia o resultado. Chame com fallback_http=False em hot paths onde
    consultas HTTP sao caras.
    """
    cached = _get_tenant_status(tenant_id)
    if cached:
        return cached in _CONNECTED_STATUSES
    if not fallback_http:
        return False
    try:
        import httpx
        with httpx.Client(timeout=3) as c:
            r = c.get(
                f"{MEOWHATS_HTTP}/api/sessions/{tenant_id}/status",
                headers={"X-API-Key": MEOWHATS_KEY},
            )
            if r.status_code == 200:
                status = (r.json() or {}).get("status", "")
                _set_tenant_status(tenant_id, status)
                return status in _CONNECTED_STATUSES
    except Exception as e:
        logger.debug(f"is_tenant_connected fallback HTTP falhou ({tenant_id}): {e}")
    return False

# Mapeamento estado Bryan -> sdr_stage kanban
ESTADO_TO_STAGE = {
    # Stages novos (Franz prompt v2)
    "intro":       "intro",
    "qualify":     "intro",
    "proof":       "followup1",
    "link":        "followup1",
    "value":       "followup2",
    "price":       "negociacao",
    "negotiate":   "negociacao",
    "close":       "negociacao",
    "won":         "ganhos",
    "lost":        "perdidos",
    # Stages legados (compatibilidade)
    "hook":        "intro",
    "pain":        "followup1",
    "amplify":     "followup1",
    "tease":       "followup2",
    "reveal":      "negociacao",
    "feedback":    "negociacao",
    "urgency":     "negociacao",
    "followup1":   "followup1",
    "followup2":   "followup2",
    "rapport":     "followup2",
    "education":   "followup2",
    "negotiation": "negociacao",
    "offer":       "negociacao",
    "qualificado": "qualificados",
    "handoff":     "qualificados",
    "scheduled":   "followup1",
}

def _normalizar_tel(jid: str) -> str:
    """Extrai número limpo do JID: '5511999@s.whatsapp.net' -> '5511999'"""
    return re.sub(r'\D', '', jid.split('@')[0])

def _resolver_lid(lid_number: str) -> str:
    """Resolve LID (novo protocolo WhatsApp) para número real via whatsmeow_lid_map."""
    try:
        from sqlalchemy import create_engine as _ce2, text as _t2
        whatsmeow_db = os.getenv("WHATSMEOW_DB_URL", "postgresql://postgres:fralib2024@localhost:5433/whatsmeow")
        # Garantir formato postgresql:// (SQLAlchemy não aceita postgres://)
        if whatsmeow_db.startswith("postgres://"):
            whatsmeow_db = whatsmeow_db.replace("postgres://", "postgresql://", 1)
        eng = _ce2(whatsmeow_db)
        with eng.connect() as conn:
            row = conn.execute(_t2("SELECT pn FROM whatsmeow_lid_map WHERE lid=:lid"), {"lid": lid_number}).fetchone()
            if row:
                print(f"[WPP-Listener] LID {lid_number} → PN {row[0]}", flush=True)
                return row[0]
    except Exception as e:
        print(f"[WPP-Listener] Erro ao resolver LID {lid_number}: {e}", flush=True)
    return lid_number

_TENANT_RE = re.compile(r'^fralib_user_(\d+)$')

def _user_id_from_tenant(tenant_id: str):
    """Converte tenant_id 'fralib_user_{N}' em int N, ou None se inválido."""
    if not tenant_id:
        return None
    m = _TENANT_RE.match(tenant_id)
    return int(m.group(1)) if m else None

def _buscar_lead_por_tel(telefone: str, user_id: int):
    """Busca lead no banco pelo telefone ou JID, restrito ao user_id (tenant).
    Tenta com e sem código de país (55) e com/sem 9 extra (BR mobile).
    """
    # Gera variantes: com 55 e sem 55
    tel_com_55 = telefone if telefone.startswith('55') else '55' + telefone
    tel_sem_55 = telefone[2:] if telefone.startswith('55') and len(telefone) > 11 else telefone

    # Variantes com/sem 9 extra (BR: 55+DDD(2)+9+8dig vs 55+DDD(2)+8dig)
    variantes = {tel_com_55, tel_sem_55}
    # Se tem 55+DDD+9+8dig (13 chars com 55), gerar sem o 9
    if len(tel_com_55) == 13 and tel_com_55[4] == '9':
        variantes.add(tel_com_55[:4] + tel_com_55[5:])  # remove 9
    # Se tem 55+DDD+8dig (12 chars com 55), gerar com o 9
    if len(tel_com_55) == 12:
        variantes.add(tel_com_55[:4] + '9' + tel_com_55[4:])  # add 9
    # Sem 55 também
    for v in list(variantes):
        if v.startswith('55') and len(v) > 4:
            variantes.add(v[2:])

    variantes_list = list(variantes)

    with engine.connect() as conn:
        # Busca por telefone normalizado (tenta todas variantes com/sem 55, com/sem 9)
        # Usar ANY com array pra suportar N variantes
        row = conn.execute(text("""
            SELECT id, nome, segmento, cidade, sdr_stage, status,
                   COALESCE(NULLIF(telefone_whatsapp,''), NULLIF(whatsapp,''), telefone, '') as tel_raw
            FROM leads
            WHERE user_id = :uid
              AND regexp_replace(COALESCE(NULLIF(telefone_whatsapp,''), NULLIF(whatsapp,''), telefone, ''), '\\D', '', 'g')
                  = ANY(:variantes)
            LIMIT 1
        """), {"variantes": variantes_list, "uid": user_id}).fetchone()
        if row:
            return row
        # Fallback: buscar por wpp_jid (LID de conta business)
        row = conn.execute(text("""
            SELECT id, nome, segmento, cidade, sdr_stage, status,
                   COALESCE(NULLIF(telefone_whatsapp,''), NULLIF(whatsapp,''), telefone, '') as tel_raw
            FROM leads
            WHERE user_id = :uid AND wpp_jid = :jid
            LIMIT 1
        """), {"jid": telefone, "uid": user_id}).fetchone()
        return row

def _salvar_interacao(lead_id: str, mensagem: str, direcao: str, user_id: int = None):
    """Salva mensagem na tabela interacoes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO interacoes (lead_id, mensagem, direcao, criado_em, user_id)
                VALUES (:lead_id, :mensagem, :direcao, :criado_em, :user_id)
            """), {
                "lead_id": lead_id,
                "mensagem": mensagem,
                "direcao": direcao,
                "criado_em": datetime.now().isoformat(),
                "user_id": user_id
            })
            conn.commit()
    except Exception as e:
        logger.warning(f"Erro ao salvar interacao: {e}")

def _atualizar_stage(lead_id: str, sdr_stage: str, user_id: int):
    """Atualiza sdr_stage do lead no banco (escopo ao user_id)."""
    with engine.connect() as conn:
        conn.execute(text(
            "UPDATE leads SET sdr_stage=:stage, atualizado_em=:ts WHERE id=:id AND user_id=:uid"
        ), {"stage": sdr_stage, "ts": datetime.now().isoformat(), "id": lead_id, "uid": user_id})
        conn.commit()


# Número do closer humano (recebe handoff)
CLOSER_HUMANO = os.getenv("CLOSER_NUMERO", "5541992049684")


def _notificar_handoff_humano(http_client, tenant_id: str, lead_id: str, nome: str, telefone: str, jid: str, meowhats_http: str, user_id: int):
    """
    Notifica o closer humano que um lead está pronto pra fechar.
    Envia resumo do lead + últimas mensagens pro número do closer.
    Bryan para de responder (stage=handoff).
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
            f"Bryan já parou de responder."
        )

        # Enviar pro closer humano
        closer_jid = f"{CLOSER_HUMANO}@s.whatsapp.net"
        meowhats_http_real = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        http_client.post(
            f"{meowhats_http_real}/api/sessions/{tenant_id}/send",
            headers={"X-API-Key": MEOWHATS_KEY},
            json={"jid": closer_jid, "type": "text", "text": resumo}
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
        # Ignorar mensagens enviadas por nós
        if key.get("fromMe", False):
            return

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

        # ── GATE DE BILLING — trial expirado ou sem créditos = bot silenciado ──
        if not _user_can_use_bot(user_id):
            logger.warning(f"🚫 {nome}: tenant {user_id} sem plano ativo/trial expirado — bot silenciado")
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

        # Salvar mensagem recebida sempre (histórico)
        _salvar_interacao(lead_id, texto, "entrada", user_id)

        # Só responder se o site já foi deployado (status=concluido) e Bryan já iniciou contato
        if status != "concluido":
            print(f"[WPP-Listener] Lead {nome}: status={status} — aguardando deploy antes de responder", flush=True)
            return
        if not sdr_stage_atual:
            print(f"[WPP-Listener] Lead {nome}: sdr_stage vazio — Bryan ainda não iniciou contato", flush=True)
            return

        # Se stage é qualificados/ganhos/perdidos → Bryan NÃO responde mais (humano assumiu)
        if sdr_stage_atual in ('qualificados', 'ganhos', 'perdidos', 'handoff', 'won', 'lost'):
            logger.info(f"Lead {nome}: stage={sdr_stage_atual} — humano assumiu, Bryan parado")
            return

        # ── ANTI-BAN CHECKS ──────────────────────────────────────────
        # Human takeover: dono do número está conversando manualmente
        if _is_human_paused(lead_key):
            remaining = HUMAN_PAUSE_SECONDS - (_time.time() - _HUMAN_PAUSE.get(lead_key, 0))
            logger.info(f"👤 {nome}: humano ativo, bot pausado ({remaining:.0f}s restantes)")
            return

        # Cooldown: não responder se já respondeu recentemente
        if _check_cooldown(lead_key):
            logger.info(f"⏳ {nome}: cooldown ativo ({COOLDOWN_SECONDS}s) — resposta adiada")
            return

        # Limite diário
        if _check_daily_limit(lead_key):
            logger.warning(f"🚫 {nome}: limite diário ({DAILY_LIMIT} msgs) atingido — Bryan silenciado")
            return

        # Chamar Bryan para gerar resposta
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))

        # Flag: usar Bryan Managed Agent (agent loop com tools) ou legacy (single-shot)
        USE_AGENT_LOOP = os.getenv("BRYAN_AGENT_LOOP", "1") == "1"

        if USE_AGENT_LOOP:
            from agents.bryan_agent_loop import bryan_agent_loop, BryanAgentOutput as _BAO
            agent_result = bryan_agent_loop(
                lead_data={"id": lead_id, "nome": nome, "segmento": segmento, "cidade": cidade, "telefone": telefone},
                mensagem=texto,
                historico_resumo="",
                sdr_stage=sdr_stage_atual,
                user_id=user_id,
            )
            print(f"[Bryan Agent] ✅ Resultado: stage={agent_result.novo_stage}, tools={agent_result.tools_used}, iter={agent_result.iterations}", flush=True)

            resposta = agent_result.resposta
            proximo_passo = ""

            # Mapear output do agent loop pro formato esperado
            class _FakeBryanOutput:
                reply = agent_result.resposta
                next_stage = agent_result.novo_stage or sdr_stage_atual
                should_handoff = agent_result.should_handoff
                intent = ""
                proximo_passo = ""
                update_facts = {"followup_date": agent_result.followup_date} if agent_result.followup_date else {}
            bryan_output = _FakeBryanOutput()
        else:
            from agents.bryan import responder_lead
            bryan_output = responder_lead(
                telefone=tel_raw,
                mensagem_recebida=texto,
                nome_negocio=nome or push_name,
                user_id=user_id,
            )
            resposta = bryan_output.reply
            proximo_passo = bryan_output.proximo_passo or ""

        # Se reply vazio (opt_out, fila, etc) — não enviar
        if not resposta or not resposta.strip():
            logger.info(f"Lead {nome}: Bryan retornou reply vazio (intent={bryan_output.intent}) — não envia")
            if bryan_output.next_stage == "lost":
                _atualizar_stage(lead_id, "perdidos", user_id)
            return

        # SEGURANÇA: NUNCA enviar JSON bruto pro cliente
        # Se resposta parece JSON, extrair só o texto
        if resposta.strip().startswith('{') or '"resposta"' in resposta or '"novo_stage"' in resposta:
            logger.warning(f"Lead {nome}: resposta contém JSON! Sanitizando antes de enviar...")
            import re as _re_san
            # Tentar extrair campo "resposta" do JSON
            _resp_match = _re_san.search(r'"resposta"\s*:\s*"((?:[^"\\]|\\.)*)"', resposta)
            if _resp_match:
                resposta = _resp_match.group(1).replace('\\"', '"').replace('\\n', '\n')
            else:
                # Remover tudo que parece JSON
                resposta = _re_san.sub(r'\{[\s\S]*?\}', '', resposta).strip()
                resposta = _re_san.sub(r'```[\s\S]*?```', '', resposta).strip()
            # Se ainda parece JSON ou vazio → retry com LLM pedindo só texto
            if not resposta or resposta.strip().startswith('{') or '"resposta"' in resposta:
                logger.warning(f"Lead {nome}: sanitização falhou — retry via LLM pra extrair texto")
                try:
                    from agents.llm_direct import call_claude
                    _raw_json = agent_result.resposta if 'agent_result' in dir() else bryan_output.reply
                    _fix_resp = call_claude(
                        system="Voce recebe um JSON malformado de um chatbot. Extraia APENAS o texto da mensagem que seria enviada ao cliente. Retorne SOMENTE o texto puro, sem JSON, sem aspas, sem formatacao.",
                        user=f"Extraia a mensagem do cliente deste JSON:\n{_raw_json[:1000]}",
                        model="haiku",
                        max_tokens=500,
                        temperature=0.0,
                    )
                    _fix_resp = _fix_resp.strip().strip('"').strip()
                    if _fix_resp and not _fix_resp.startswith('{') and '"resposta"' not in _fix_resp:
                        resposta = _fix_resp
                        logger.info(f"Lead {nome}: retry LLM extraiu resposta OK ({len(resposta)} chars)")
                    else:
                        # ÚLTIMO RECURSO: mensagem genérica segura — NUNCA deixar cliente sem resposta
                        resposta = "Opa, tudo bem? Me dá um minuto que já te respondo! 👍"
                        logger.error(f"Lead {nome}: retry LLM falhou — usando resposta genérica de segurança")
                except Exception as _retry_err:
                    # ÚLTIMO RECURSO: mensagem genérica segura
                    resposta = "Opa, tudo bem? Me dá um minuto que já te respondo! 👍"
                    logger.error(f"Lead {nome}: retry LLM exception: {_retry_err} — usando resposta genérica")

        # Salvar resposta do Bryan
        _salvar_interacao(lead_id, resposta, "saida", user_id)

        # Converter estado Bryan → stage kanban via mapeamento
        _raw_stage = bryan_output.next_stage or sdr_stage_atual or "hook"
        novo_stage = ESTADO_TO_STAGE.get(_raw_stage, _raw_stage)

        _atualizar_stage(lead_id, novo_stage, user_id)

        # Se Bryan agendou follow-up, salvar a data
        if _raw_stage == "scheduled":
            facts = bryan_output.update_facts or {}
            followup_date = facts.get("followup_date", "")
            if followup_date:
                # Fallback: se LLM retornou data no passado, corrigir para amanhã
                from datetime import datetime as _dt, timedelta as _td
                import pytz as _tz
                try:
                    _hoje = _dt.now(_tz.timezone("America/Sao_Paulo")).date()
                    _data_parsed = _dt.strptime(followup_date, "%Y-%m-%d").date()
                    if _data_parsed <= _hoje:
                        followup_date = (_hoje + _td(days=1)).strftime("%Y-%m-%d")
                        logger.warning(f"Lead {nome}: data no passado corrigida para {followup_date}")
                except (ValueError, TypeError):
                    # Formato inválido — default amanhã
                    followup_date = (_dt.now(_tz.timezone("America/Sao_Paulo")).date() + _td(days=1)).strftime("%Y-%m-%d")
                    logger.warning(f"Lead {nome}: followup_date inválido, usando amanhã {followup_date}")

                with engine.connect() as conn:
                    conn.execute(text(
                        "UPDATE leads SET followup_date=:fd WHERE id=:id AND user_id=:uid"
                    ), {"fd": followup_date, "id": lead_id, "uid": user_id})
                    conn.commit()
                logger.info(f"Lead {nome}: agendado para {followup_date}")

        logger.info(f"Lead {nome}: stage {sdr_stage_atual} -> {novo_stage}")

        # Gate multi-tenant: nao tente enviar se o device do tenant nao esta
        # pareado/conectado. Evita erros silenciosos em "pairing", "rejected",
        # "logged_out", "disconnected".
        if not is_tenant_connected(tenant_id):
            current = _get_tenant_status(tenant_id) or "unknown"
            logger.warning(
                f"Lead {nome}: envio BLOQUEADO — tenant {tenant_id} esta em status '{current}'. "
                f"Resposta de Bryan ja salva no historico; sera reenviada quando reconectar."
            )
            return

        # Enviar resposta via meowhats COM delay humanizado (composing)
        import httpx
        meowhats_http = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        try:
            with httpx.Client(timeout=15) as c:
                # 1. Mostrar "digitando..." (composing)
                try:
                    c.post(
                        f"{meowhats_http}/api/sessions/{tenant_id}/presence",
                        headers={"X-API-Key": MEOWHATS_KEY},
                        json={"jid": jid, "type": "composing"}
                    )
                except Exception:
                    pass  # não crítico

                # 2. Delay humanizado variável (anti-ban)
                delay_secs = _humanized_delay(resposta)
                _time.sleep(delay_secs)

                # 3. Enviar mensagem
                r = c.post(
                    f"{meowhats_http}/api/sessions/{tenant_id}/send",
                    headers={"X-API-Key": MEOWHATS_KEY},
                    json={"jid": jid, "type": "text", "text": resposta}
                )
                if r.status_code == 200:
                    logger.info(f"✅ Resposta enviada para {telefone} (delay={delay_secs:.1f}s)")
                    # Registrar cooldown e incrementar contador diário
                    _set_cooldown(lead_key)
                    _increment_daily(lead_key)
                else:
                    logger.warning(f"Falha ao enviar resposta: {r.text[:80]}")

                # 4. Se handoff → notificar humano e parar Bryan
                if bryan_output.should_handoff or _raw_stage == 'handoff':
                    _notificar_handoff_humano(c, tenant_id, lead_id, nome, telefone, jid, meowhats_http, user_id)

        except Exception as e:
            logger.warning(f"Erro ao enviar resposta WPP: {e}")

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def _conectar_e_ouvir():
    """Conecta ao WebSocket do meowhats e processa eventos."""
    ws_url = f"{MEOWHATS_URL}/ws"
    headers = {"X-API-Key": MEOWHATS_KEY} if MEOWHATS_KEY else {}

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
