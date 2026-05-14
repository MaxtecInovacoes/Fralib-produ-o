"""
whatsapp_listener.py — Listener WebSocket do meowhats
Fica conectado ao meowhats e processa mensagens recebidas dos leads.
Quando um lead responde, chama Bryan e atualiza sdr_stage no banco.
"""
import asyncio
import json
import os
import re
import threading
import logging
from datetime import datetime

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

# Cache do status de conexao por tenant, alimentado por eventos connection.update
# do meowhats. Multi-tenant pos-fix (2026-05-13): meowhats emite "connected",
# "pairing", "rejected", "logged_out", "disconnected", "reconnecting", "qr",
# "timeout". So "connected" significa que o device esta pareado e pronto para
# enviar mensagens.
_TENANT_STATUS: dict[str, str] = {}
_TENANT_STATUS_LOCK = threading.Lock()
_CONNECTED_STATUSES = frozenset({"connected", "open", "authenticated"})


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
    "hook":        "intro",
    "qualify":     "intro",
    "pain":        "f1",
    "amplify":     "f1",
    "tease":       "f2",
    "proof":       "f2",
    "reveal":      "negotiation",
    "feedback":    "negotiation",
    "close":       "negotiation",
    "urgency":     "negotiation",
    "followup1":   "f1",
    "followup2":   "f2",
    "rapport":     "f2",
    "education":   "f2",
    "negotiation": "negotiation",
    "qualificado": "qualificado",
    "handoff":     "qualificado",
    "won":         "won",
    "lost":        "lost",
    "scheduled":   "f1",
}

def _normalizar_tel(jid: str) -> str:
    """Extrai número limpo do JID: '5511999@s.whatsapp.net' -> '5511999'"""
    return re.sub(r'\D', '', jid.split('@')[0])

_TENANT_RE = re.compile(r'^fralib_user_(\d+)$')

def _user_id_from_tenant(tenant_id: str):
    """Converte tenant_id 'fralib_user_{N}' em int N, ou None se inválido."""
    if not tenant_id:
        return None
    m = _TENANT_RE.match(tenant_id)
    return int(m.group(1)) if m else None

def _buscar_lead_por_tel(telefone: str, user_id: int):
    """Busca lead no banco pelo telefone ou JID, restrito ao user_id (tenant).
    Tenta com e sem código de país (55) para cobrir ambos formatos.
    """
    # Gera variantes: com 55 e sem 55
    tel_com_55 = telefone if telefone.startswith('55') else '55' + telefone
    tel_sem_55 = telefone[2:] if telefone.startswith('55') and len(telefone) > 11 else telefone

    with engine.connect() as conn:
        # Busca por telefone normalizado (tenta ambas variantes), filtrando por user_id
        row = conn.execute(text("""
            SELECT id, nome, segmento, cidade, sdr_stage, status,
                   COALESCE(telefone_whatsapp, whatsapp, telefone, '') as tel_raw
            FROM leads
            WHERE user_id = :uid
              AND regexp_replace(COALESCE(telefone_whatsapp, whatsapp, telefone, ''), '\\D', '', 'g')
                  IN (:tel1, :tel2)
            LIMIT 1
        """), {"tel1": tel_com_55, "tel2": tel_sem_55, "uid": user_id}).fetchone()
        if row:
            return row
        # Fallback: buscar por wpp_jid (LID de conta business)
        row = conn.execute(text("""
            SELECT id, nome, segmento, cidade, sdr_stage, status,
                   COALESCE(telefone_whatsapp, whatsapp, telefone, '') as tel_raw
            FROM leads
            WHERE user_id = :uid AND wpp_jid = :jid
            LIMIT 1
        """), {"jid": telefone, "uid": user_id}).fetchone()
        return row

def _salvar_interacao(lead_id: str, mensagem: str, direcao: str):
    """Salva mensagem na tabela interacoes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO interacoes (lead_id, mensagem, direcao, criado_em)
                VALUES (:lead_id, :mensagem, :direcao, :criado_em)
            """), {
                "lead_id": lead_id,
                "mensagem": mensagem,
                "direcao": direcao,
                "criado_em": datetime.now().isoformat()
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

def _processar_mensagem(tenant_id: str, msg_data: dict):
    """Processa mensagem recebida de um lead."""
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

        telefone = _normalizar_tel(jid)
        push_name = msg_data.get("pushName", "")

        # Extrair texto da mensagem
        msg_content = msg_data.get("message", {})
        texto = (
            msg_content.get("conversation") or
            msg_content.get("extendedTextMessage", {}).get("text") or
            msg_content.get("imageMessage", {}).get("caption") or
            "[mídia]"
        )

        logger.info(f"Mensagem de {telefone} ({push_name}): {texto[:60]}")

        # Buscar lead no banco (escopo ao user_id do tenant)
        lead = _buscar_lead_por_tel(telefone, user_id)
        if not lead:
            logger.info(f"Lead não encontrado para {telefone} — ignorando")
            return

        lead_id, nome, segmento, cidade, sdr_stage_atual, status, tel_raw = lead

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
        _salvar_interacao(lead_id, texto, "entrada")

        # Só responder se o site já foi deployado (status=concluido) e Bryan já iniciou contato
        if status != "concluido":
            logger.info(f"Lead {nome}: status={status} — aguardando deploy antes de responder")
            return
        if not sdr_stage_atual:
            logger.info(f"Lead {nome}: sdr_stage vazio — Bryan ainda não iniciou contato")
            return

        # Se stage é handoff ou won → Bryan NÃO responde mais (humano assumiu)
        if sdr_stage_atual in ('handoff', 'won'):
            logger.info(f"Lead {nome}: stage={sdr_stage_atual} — humano assumiu, Bryan parado")
            _salvar_interacao(lead_id, texto, "entrada")
            return

        # Chamar Bryan para gerar resposta
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))
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
                _atualizar_stage(lead_id, "lost", user_id)
            return

        # Salvar resposta do Bryan
        _salvar_interacao(lead_id, resposta, "saida")

        # Usar next_stage direto do Bryan (state machine real)
        novo_stage = bryan_output.next_stage or sdr_stage_atual or "hook"

        _atualizar_stage(lead_id, novo_stage, user_id)

        # Se Bryan agendou follow-up, salvar a data
        if novo_stage == "scheduled":
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
        import httpx, time
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

                # 2. Delay proporcional ao tamanho da msg (~40 chars/seg, min 2s, max 8s)
                delay_secs = min(max(len(resposta) * 0.025, 2.0), 8.0)
                time.sleep(delay_secs)

                # 3. Enviar mensagem
                r = c.post(
                    f"{meowhats_http}/api/sessions/{tenant_id}/send",
                    headers={"X-API-Key": MEOWHATS_KEY},
                    json={"jid": jid, "type": "text", "text": resposta}
                )
                if r.status_code == 200:
                    logger.info(f"Resposta enviada para {telefone} (delay={delay_secs:.1f}s)")
                else:
                    logger.warning(f"Falha ao enviar resposta: {r.text[:80]}")

                # 4. Se handoff → notificar humano e parar Bryan
                if bryan_output.should_handoff or novo_stage == 'handoff':
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
    
    logger.info(f"Conectando ao meowhats WebSocket: {ws_url}")
    
    loop = asyncio.get_event_loop()
    from concurrent.futures import ThreadPoolExecutor
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="wpp-msg")

    async with websockets.connect(
        ws_url,
        additional_headers=headers,
        ping_interval=20,
        ping_timeout=30,
    ) as ws:
        logger.info("Conectado ao meowhats WebSocket")
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
                    # Processar em thread separada para não bloquear o WebSocket
                    loop.run_in_executor(_executor, _processar_mensagem, tenant_id, msg_data)
                    
                elif event_type == "connection.update":
                    data = event.get("data", {})
                    tenant_id = data.get("tenantId") or ""
                    status = data.get("status") or ""
                    if tenant_id:
                        _set_tenant_status(tenant_id, status)
                    # Avisar quando o pareamento e recusado por hijack tentativo
                    if status == "rejected":
                        logger.warning(f"Conexão WPP RECUSADA: tenant={tenant_id} — {data.get('error', '')}")
                    else:
                        logger.info(f"Conexão WPP: tenant={tenant_id} status={status}")
                    
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
            logger.warning(f"WebSocket desconectado: {e}. Reconectando em {retry_delay}s...")
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
