"""
Franz Agent Tools — Ferramentas MCP-like para o Franz (SDR/Outreach).

Pattern identico ao Theo e Arquiteto: lista de tool schemas + execute_tool()
dispatcher. Franz usa estas tools para interagir com DB, WhatsApp e pipeline
durante o fluxo de qualificacao e outreach.

Uso no agent loop:
    tools = FRANZ_TOOLS
    response = anthropic_client.messages.create(
        model=MODEL, max_tokens=4000, tools=tools, ...
    )
    if response.stop_reason == "tool_use":
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                # feed result back as tool_result block
"""
import json
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from backend.core.database import engine
from sqlalchemy import text

logger = logging.getLogger("fralib.franz.tools")

# =====================================================================
# TOOL DEFINITIONS
# =====================================================================

FRANZ_TOOLS = [
    {
        "name": "buscar_lead",
        "description": (
            "Busca dados completos de um lead por ID ou telefone. "
            "Retorna: nome, cidade, segmento, tier, score, status, site_url, "
            "ultima_interacao. Use SEMPRE no inicio do atendimento para "
            "entender quem e o lead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead (UUID ou numero)"
                },
                "telefone": {
                    "type": "string",
                    "description": "Telefone do lead (para buscar por wpp_jid)"
                },
            },
        },
    },
    {
        "name": "consultar_historico",
        "description": (
            "Retorna as ultimas interacoes do lead com o sistema: "
            "mensagens trocadas, stages do pipeline, outcomes. "
            "Use para personalizar a abordagem e nao repetir assuntos ja tratados."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead"
                },
                "limite": {
                    "type": "integer",
                    "description": "Max de interacoes (default 20, max 50)",
                    "default": 20,
                },
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "consultar_site",
        "description": (
            "Busca o site HTML ja gerado do lead. "
            "Retorna URL do site e metadados. "
            "Use para mencionar algo especifico do site na conversa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead"
                },
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "agendar_followup",
        "description": (
            "Agenda um follow-up para o lead em um slot valido. "
            "Calcula automaticamente o proximo slot disponivel dentro "
            "da janela de atendimento (08:00-21:00). "
            "Use quando o lead pedir para voltar mais tarde ou nao responder."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead"
                },
                "tenant_id": {
                    "type": "integer",
                    "description": "ID do tenant"
                },
                "tipo": {
                    "type": "string",
                    "enum": ["followup_1h", "followup_24h", "followup_3d", "followup_7d", "reengajamento"],
                    "description": "Tipo de follow-up",
                },
                "mensagem": {
                    "type": "string",
                    "description": "Mensagem pre-definida para enviar no follow-up (opcional)"
                },
                "motivo": {
                    "type": "string",
                    "description": "Motivo do agendamento (ex: lead_pediu_voltar, sem_resposta)"
                },
            },
            "required": ["lead_id", "tenant_id", "tipo"],
        },
    },
    {
        "name": "marcar_status_lead",
        "description": (
            "Atualiza o status do lead no pipeline. "
            "Use para avançar o lead: hot_lead → negociacao → contratado. "
            "OU marcar como conversion_lost com motivo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead"
                },
                "novo_status": {
                    "type": "string",
                    "enum": [
                        "pendente",
                        "em_contato",
                        "hot_lead",
                        "negociacao",
                        "contratado",
                        "conversion_lost",
                        "followup",
                    ],
                    "description": "Novo status do lead",
                },
                "motivo": {
                    "type": "string",
                    "description": "Obrigatorio se novo_status for conversion_lost"
                },
            },
            "required": ["lead_id", "novo_status"],
        },
    },
    {
        "name": "registrar_interacao",
        "description": (
            "Registra uma interacao com o lead no banco. "
            "Use para deixar track de cada mensagem trocada. "
            "Isso alimenta o historico consultado por consultar_historico."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead"
                },
                "tenant_id": {
                    "type": "integer",
                    "description": "ID do tenant"
                },
                "tipo": {
                    "type": "string",
                    "enum": ["mensagem_enviada", "mensagem_recebida", "ligacao", "email", "nota"],
                    "description": "Tipo de interacao"
                },
                "conteudo": {
                    "type": "string",
                    "description": "Conteudo da interacao (texto da mensagem, resumo da ligacao, etc)"
                },
                "stage": {
                    "type": "string",
                    "description": "Stage do pipeline no momento da interacao"
                },
                "sentimento": {
                    "type": "string",
                    "enum": ["positivo", "neutro", "negativo"],
                    "description": "Sentimento detectado na interacao"
                },
            },
            "required": ["lead_id", "tenant_id", "tipo", "conteudo"],
        },
    },
    {
        "name": "enviar_whatsapp",
        "description": (
            "Envia uma mensagem WhatsApp para o lead via meowhats API. "
            "Use apos qualificar a mensagem com verify_message. "
            "IMPORTANTE: Nao envie mensagens fora da janela 08:00-21:00 "
            "sem autorizacao explicita."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "telefone": {
                    "type": "string",
                    "description": "Telefone do lead (com DDI, ex: 554185134105)"
                },
                "mensagem": {
                    "type": "string",
                    "description": "Mensagem a enviar (ja validada)"
                },
                "tenant_id": {
                    "type": "integer",
                    "description": "ID do tenant"
                },
            },
            "required": ["telefone", "mensagem", "tenant_id"],
        },
    },
    {
        "name": "verificar_status_wpp",
        "description": (
            "Verifica se a sessao WhatsApp do tenant esta conectada. "
            "Use antes de tentar enviar mensagens para garantir que "
            "o canal esta disponivel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {
                    "type": "integer",
                    "description": "ID do tenant"
                },
            },
            "required": ["tenant_id"],
        },
    },
    {
        "name": "buscar_leads_similares",
        "description": (
            "Busca leads semanticamente similares no banco usando RAG vetorial. "
            "Use para encontrar casos de sucesso no mesmo segmento/cidade "
            "e adaptar a abordagem do SDR."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead atual (para buscar similares a ele)"
                },
                "query": {
                    "type": "string",
                    "description": "Descricao textual para busca semantica (ex: 'restaurante japones Curitiba PREMIUM')"
                },
                "limite": {
                    "type": "integer",
                    "description": "Max resultados (default 5)",
                    "default": 5,
                },
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "marcar_deferido",
        "description": (
            "Marca uma mensagem para envio diferido (fora da janela de atendimento). "
            "Calcula o proximo slot valido (proxima 08:00) e agenda. "
            "Use quando o lead responder fora do horario ou quando "
            "o follow-up deve ser enviado no proximo dia util."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID do lead"
                },
                "tenant_id": {
                    "type": "integer",
                    "description": "ID do tenant"
                },
                "mensagem": {
                    "type": "string",
                    "description": "Mensagem a enviar quando sair do defer"
                },
                "motivo": {
                    "type": "string",
                    "description": "Motivo do defer (ex: fora_horario, aguardando_resposta)"
                },
            },
            "required": ["lead_id", "tenant_id", "mensagem"],
        },
    },
]


# =====================================================================
# TOOL EXECUTION
# =====================================================================

def execute_tool(tool_name: str, tool_input: dict, context: dict = None) -> str:
    """Dispatcher principal — roteia para a implementacao correta."""
    try:
        dispatch = {
            "buscar_lead": _tool_buscar_lead,
            "consultar_historico": _tool_consultar_historico,
            "consultar_site": _tool_consultar_site,
            "agendar_followup": _tool_agendar_followup,
            "marcar_status_lead": _tool_marcar_status_lead,
            "registrar_interacao": _tool_registrar_interacao,
            "enviar_whatsapp": _tool_enviar_whatsapp,
            "verificar_status_wpp": _tool_verificar_status_wpp,
            "buscar_leads_similares": _tool_buscar_leads_similares,
            "marcar_deferido": _tool_marcar_deferido,
        }
        handler = dispatch.get(tool_name)
        if not handler:
            return _json_error(f"Tool desconhecida: {tool_name}")
        return handler(tool_input, context)
    except Exception as exc:
        logger.error("execute_tool(%s) falhou: %s", tool_name, exc)
        return _json_error(str(exc))


# =====================================================================
# IMPLEMENTATIONS
# =====================================================================

def _tool_buscar_lead(tool_input: dict, context: dict = None) -> str:
    """Busca lead por ID ou telefone."""
    lead_id = tool_input.get("lead_id", "")
    telefone = tool_input.get("telefone", "")

    with engine.connect() as conn:
        if lead_id:
            row = conn.execute(text("""
                SELECT id, nome, cidade, segmento, telefone, whatsapp,
                       tier, score, status, site_url, html_gerado,
                       dados_completos, ultima_interacao
                FROM leads WHERE id = :lid LIMIT 1
            """), {"lid": lead_id}).fetchone()
        elif telefone:
            clean = telefone.replace("+", "").replace("-", "").replace(" ", "")
            row = conn.execute(text("""
                SELECT id, nome, cidade, segmento, telefone, whatsapp,
                       tier, score, status, site_url, html_gerado,
                       dados_completos, ultima_interacao
                FROM leads
                WHERE REPLACE(REPLACE(REPLACE(telefone, '+', ''), '-', ''), ' ', '') = :tel
                   OR REPLACE(REPLACE(REPLACE(whatsapp, '+', ''), '-', ''), ' ', '') = :tel
                LIMIT 1
            """), {"tel": clean}).fetchone()
        else:
            return _json_error("Forneca lead_id ou telefone")

    if not row:
        return _json_error("Lead nao encontrado")

    dados = row._mapping
    dc = dados.get("dados_completos") or {}
    result = {
        "lead_id": dados["id"],
        "nome": dados["nome"],
        "cidade": dados["cidade"],
        "segmento": dados["segmento"],
        "telefone": dados["telefone"],
        "whatsapp": dados["whatsapp"],
        "tier": dados["tier"],
        "score": dados["score"],
        "status": dados["status"],
        "site_url": dados["site_url"],
        "tem_site": bool(dados["site_url"]),
        "ultima_interacao": (
            dados["ultima_interacao"].isoformat()
            if dados["ultima_interacao"]
            else None
        ),
        "dados_adicionais": dc,
    }
    return json.dumps(result, ensure_ascii=False)


def _tool_consultar_historico(tool_input: dict, context: dict = None) -> str:
    """Ultimas interacoes do lead."""
    lead_id = tool_input.get("lead_id", "")
    limite = min(int(tool_input.get("limite", 20)), 50)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT tipo, conteudo, stage, sentimento, criado_em
            FROM interacoes
            WHERE lead_id = :lid
            ORDER BY criado_em DESC
            LIMIT :lim
        """), {"lid": lead_id, "lim": limite}).fetchall()

    if not rows:
        return json.dumps({"historico": [], "total": 0}, ensure_ascii=False)

    historico = []
    for r in rows:
        historico.append({
            "tipo": r[0],
            "conteudo": r[1][:300] if r[1] else "",
            "stage": r[2],
            "sentimento": r[3],
            "data": r[4].isoformat() if r[4] else None,
        })

    return json.dumps({"historico": historico, "total": len(historico)}, ensure_ascii=False)


def _tool_consultar_site(tool_input: dict, context: dict = None) -> str:
    """Busca site do lead."""
    lead_id = tool_input.get("lead_id", "")

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT site_url, html_gerado, dados_completos
            FROM leads WHERE id = :lid LIMIT 1
        """), {"lid": lead_id}).fetchone()

    if not row or not row[0]:
        return json.dumps({"site_url": None, "tem_site": False}, ensure_ascii=False)

    dc = row[2] or {}
    return json.dumps({
        "site_url": row[0],
        "tem_site": True,
        "tem_html": bool(row[1]),
        "dados_adicionais": dc,
    }, ensure_ascii=False)


def _tool_agendar_followup(tool_input: dict, context: dict = None) -> str:
    """Agenda follow-up via job_queue."""
    from backend.core.job_queue import enqueue

    lead_id = tool_input["lead_id"]
    tenant_id = int(tool_input["tenant_id"])
    tipo = tool_input["tipo"]
    mensagem = tool_input.get("mensagem", "")
    motivo = tool_input.get("motivo", "sdr_agendou")

    delay_map = {
        "followup_1h": 3600,
        "followup_24h": 86400,
        "followup_3d": 259200,
        "followup_7d": 604800,
        "reengajamento": 1209600,
    }
    delay = delay_map.get(tipo, 86400)

    payload = {
        "_job_tipo": "franz_followup",
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "mensagem": mensagem,
        "motivo": motivo,
        "tipo_followup": tipo,
    }
    job_id = enqueue(
        None,  # db session — caller deve fornecer se precisar rastrear
        tipo="franz_outreach",
        payload=payload,
        tenant_id=tenant_id,
        idempotency_key=f"followup:{lead_id}:{tipo}:{datetime.utcnow().strftime('%Y%m%d')}",
        delay_seconds=delay,
        priority=3,
    )
    proximo = datetime.utcnow() + timedelta(seconds=delay)
    return json.dumps({
        "ok": job_id is not None,
        "job_id": job_id,
        "tipo": tipo,
        "agendado_para": proximo.isoformat(),
        "delay_segundos": delay,
    }, ensure_ascii=False)


def _tool_marcar_status_lead(tool_input: dict, context: dict = None) -> str:
    """Atualiza status do lead."""
    lead_id = tool_input["lead_id"]
    novo_status = tool_input["novo_status"]
    motivo = tool_input.get("motivo", "")

    allowed = {
        "pendente", "em_contato", "hot_lead", "negociacao",
        "contratado", "conversion_lost", "followup",
    }
    if novo_status not in allowed:
        return _json_error(f"Status invalido: {novo_status}")

    if novo_status == "conversion_lost" and not motivo:
        return _json_error("Motivo obrigatorio para conversion_lost")

    with engine.connect() as conn:
        updates = {"status": novo_status}
        if motivo:
            updates["conversion_lost_reason"] = motivo
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        conn.execute(text(f"""
            UPDATE leads SET {set_clause} WHERE id = :lead_id
        """), {"lead_id": lead_id, **updates})
        conn.commit()

    return json.dumps({"ok": True, "lead_id": lead_id, "novo_status": novo_status}, ensure_ascii=False)


def _tool_registrar_interacao(tool_input: dict, context: dict = None) -> str:
    """Registra interacao na tabela interacoes."""
    lead_id = tool_input["lead_id"]
    tenant_id = int(tool_input["tenant_id"])
    tipo = tool_input["tipo"]
    conteudo = tool_input.get("conteudo", "")
    stage = tool_input.get("stage", "")
    sentimento = tool_input.get("sentimento", "neutro")

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO interacoes (lead_id, tenant_id, tipo, conteudo, stage, sentimento, criado_em)
            VALUES (:lid, :tid, :tipo, :cont, :stage, :sent, NOW())
        """), {
            "lid": lead_id, "tid": tenant_id, "tipo": tipo,
            "cont": conteudo[:1000], "stage": stage, "sent": sentimento,
        })
        conn.commit()

    return json.dumps({"ok": True, "registrado": tipo}, ensure_ascii=False)


def _tool_enviar_whatsapp(tool_input: dict, context: dict = None) -> str:
    """Envia WhatsApp via meowhats API (best-effort via HTTP)."""
    import httpx

    telefone = tool_input["telefone"]
    mensagem = tool_input["mensagem"]
    tenant_id = int(tool_input["tenant_id"])

    base_url = os.getenv("MEOWHATS_BASE_URL", "http://localhost:3001")
    api_key = os.getenv("MEOWHATS_API_KEY", "")

    # Limpar telefone
    clean = telefone.replace("+", "").replace("-", "").replace(" ", "").replace("@lid", "")

    try:
        resp = httpx.post(
            f"{base_url}/api/sessions/{tenant_id}/send",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"jid": f"{clean}@s.whatsapp.net", "type": "text", "text": mensagem},
            timeout=15,
        )
        if resp.status_code == 200:
            return json.dumps({"ok": True, "enviado_para": clean}, ensure_ascii=False)
        return json.dumps({
            "ok": False,
            "erro": f"HTTP {resp.status_code}: {resp.text[:200]}",
        }, ensure_ascii=False)
    except Exception as exc:
        logger.warning("enviar_whatsapp falhou: %s", exc)
        return _json_error(f"Falha ao enviar WhatsApp: {exc}")


def _tool_verificar_status_wpp(tool_input: dict, context: dict = None) -> str:
    """Verifica status da sessao WhatsApp."""
    tenant_id = int(tool_input["tenant_id"])
    base_url = os.getenv("MEOWHATS_BASE_URL", "http://localhost:3001")
    api_key = os.getenv("MEOWHATS_API_KEY", "")

    try:
        resp = httpx.get(
            f"{base_url}/api/sessions/{tenant_id}/status",
            headers={"X-API-Key": api_key},
            timeout=10,
        )
        data = resp.json() if resp.status_code == 200 else {"error": resp.text[:200]}
        return json.dumps({
            "conectado": data.get("status") == "connected",
            "status": data.get("status", "unknown"),
            "qr": data.get("qr") is not None,
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"conectado": False, "status": "erro", "erro": str(exc)}, ensure_ascii=False)


def _tool_buscar_leads_similares(tool_input: dict, context: dict = None) -> str:
    """Busca leads similares via RAG."""
    from backend.core.rag import search_leads

    lead_id = tool_input.get("lead_id", "")
    query = tool_input.get("query", "")
    limite = min(int(tool_input.get("limite", 5)), 20)

    if not query:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT segmento, cidade, tier, nome FROM leads WHERE id = :lid LIMIT 1
            """), {"lid": lead_id}).fetchone()
        if row:
            query = f"{row[3]} {row[1]} {row[0]} {row[2] or ''}"
        else:
            return json.dumps({"similares": [], "nota": "Lead nao encontrado para gerar query"}, ensure_ascii=False)

    results = search_leads(query, tenant_id=None, limit=limite, min_similarity=0.6)
    return json.dumps({"similares": results, "query_usada": query}, ensure_ascii=False)


def _tool_marcar_deferido(tool_input: dict, context: dict = None) -> str:
    """Marca mensagem para envio diferido (proximo slot 08:00)."""
    from backend.core.job_queue import enqueue

    lead_id = tool_input["lead_id"]
    tenant_id = int(tool_input["tenant_id"])
    mensagem = tool_input["mensagem"]
    motivo = tool_input.get("motivo", "fora_horario")

    # Calcular proximo slot 08:00
    now = datetime.utcnow()
    proxima_manha = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour >= 21:
        proxima_manha += timedelta(days=1)
    delay = max(60, int((proxima_manha - now).total_seconds()))

    payload = {
        "_job_tipo": "franz_deferred",
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "mensagem": mensagem,
        "motivo": motivo,
    }
    job_id = enqueue(
        None,
        tipo="franz_outreach",
        payload=payload,
        tenant_id=tenant_id,
        idempotency_key=f"deferred:{lead_id}:{now.strftime('%Y%m%d')}",
        delay_seconds=delay,
        priority=3,
    )
    return json.dumps({
        "ok": job_id is not None,
        "job_id": job_id,
        "deferido_ate": proxima_manha.isoformat(),
        "delay_segundos": delay,
        "motivo": motivo,
    }, ensure_ascii=False)


# =====================================================================
# HELPERS
# =====================================================================

def _json_error(msg: str) -> str:
    return json.dumps({"ok": False, "erro": msg}, ensure_ascii=False)


# ===== Horario comercial (08:00-21:00) =====

def dentro_horario_atendimento() -> bool:
    """Retorna True se estamos na janela de atendimento (08:00-21:00 UTC)."""
    h = datetime.utcnow().hour
    return 8 <= h < 21


def proximo_slot_valido() -> datetime:
    """Calcula o proximo horario de atendimento valido."""
    now = datetime.utcnow()
    slot = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour >= 21:
        slot += timedelta(days=1)
    elif now.hour < 8:
        slot = now.replace(hour=8, minute=0)
    else:
        slot = now + timedelta(minutes=30)
    return slot
