"""
whatsapp_listener.py — Listener WebSocket do meowhats
Fica conectado ao meowhats e processa mensagens recebidas dos leads.
Quando um lead responde, chama Bryan e atualiza sdr_stage no banco.
"""
import asyncio
import json
import os
import re
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
DATABASE_URL  = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Mapeamento estado Bryan -> sdr_stage kanban
ESTADO_TO_STAGE = {
    "intro":       "intro",
    "followup1":   "f1",
    "followup2":   "f2",
    "rapport":     "f2",
    "education":   "f2",
    "negotiation": "negotiation",
    "qualificado": "qualificado",
    "won":         "won",
    "lost":        "lost",
}

def _normalizar_tel(jid: str) -> str:
    """Extrai número limpo do JID: '5511999@s.whatsapp.net' -> '5511999'"""
    return re.sub(r'\D', '', jid.split('@')[0])

def _buscar_lead_por_tel(telefone: str):
    """Busca lead no banco pelo telefone."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, nome, segmento, cidade, sdr_stage, status
            FROM leads
            WHERE regexp_replace(COALESCE(telefone_whatsapp, whatsapp, telefone, ''), '\\D', '', 'g') = :tel
            LIMIT 1
        """), {"tel": telefone}).fetchone()
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

def _atualizar_stage(lead_id: str, sdr_stage: str):
    """Atualiza sdr_stage do lead no banco."""
    with engine.connect() as conn:
        conn.execute(text(
            "UPDATE leads SET sdr_stage=:stage, atualizado_em=:ts WHERE id=:id"
        ), {"stage": sdr_stage, "ts": datetime.now().isoformat(), "id": lead_id})
        conn.commit()

def _processar_mensagem(tenant_id: str, msg_data: dict):
    """Processa mensagem recebida de um lead."""
    try:
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

        # Buscar lead no banco
        lead = _buscar_lead_por_tel(telefone)
        if not lead:
            logger.info(f"Lead não encontrado para {telefone} — ignorando")
            return

        lead_id, nome, segmento, cidade, sdr_stage_atual, status = lead

        # Salvar mensagem recebida sempre (histórico)
        _salvar_interacao(lead_id, texto, "entrada")

        # Só responder se o site já foi deployado (status=concluido) e Bryan já iniciou contato
        if status != "concluido":
            logger.info(f"Lead {nome}: status={status} — aguardando deploy antes de responder")
            return
        if not sdr_stage_atual:
            logger.info(f"Lead {nome}: sdr_stage vazio — Bryan ainda não iniciou contato")
            return

        # Chamar Bryan para gerar resposta
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))
        from agents.bryan import responder_lead

        bryan_output = responder_lead(
            telefone=telefone,
            mensagem_recebida=texto,
            nome_negocio=nome or push_name
        )

        resposta = bryan_output.mensagem.texto
        proximo_passo = bryan_output.proximo_passo or ""

        # Salvar resposta do Bryan
        _salvar_interacao(lead_id, resposta, "saida")

        # Determinar novo stage baseado no proximo_passo
        novo_stage = sdr_stage_atual or "intro"
        pp = proximo_passo.lower()
        if "negoci" in pp or "proposta" in pp:
            novo_stage = "negotiation"
        elif "qualific" in pp or "ganho" in pp or "fechou" in pp:
            novo_stage = "qualificado"
        elif "perdido" in pp or "desistiu" in pp or "não quer" in pp:
            novo_stage = "lost"
        elif "followup" in pp or "follow" in pp or "aguardar" in pp:
            # Avançar followup
            if sdr_stage_atual in ("intro", None, ""):
                novo_stage = "f1"
            elif sdr_stage_atual == "f1":
                novo_stage = "f2"
            else:
                novo_stage = sdr_stage_atual

        _atualizar_stage(lead_id, novo_stage)
        logger.info(f"Lead {nome}: stage {sdr_stage_atual} -> {novo_stage}")

        # Enviar resposta via meowhats
        import httpx
        meowhats_http = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        try:
            with httpx.Client(timeout=10) as c:
                r = c.post(
                    f"{meowhats_http}/api/sessions/{tenant_id}/send",
                    headers={"X-API-Key": MEOWHATS_KEY},
                    json={"jid": jid, "type": "text", "text": resposta}
                )
                if r.status_code == 200:
                    logger.info(f"Resposta enviada para {telefone}")
                else:
                    logger.warning(f"Falha ao enviar resposta: {r.text[:80]}")
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
                    tenant_id = data.get("tenantId", "fralib")
                    msg_data  = data.get("message", {})
                    # Processar em thread separada para não bloquear o WebSocket
                    loop.run_in_executor(_executor, _processar_mensagem, tenant_id, msg_data)
                    
                elif event_type == "connection.update":
                    data = event.get("data", {})
                    logger.info(f"Conexão WPP: tenant={data.get('tenantId')} status={data.get('status')}")
                    
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
