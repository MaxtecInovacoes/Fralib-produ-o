"""
franz_agent_loop.py — Franz SDR Managed Agent Loop.

Filosofia: Franz recebe uma mensagem do lead + contexto do lead,
chama Claude com FRANZ_TOOLS disponiveis, executa as ferramentas
que Claude pedir, e devolve uma resposta em texto para o WhatsApp.

Loop managed:
  user_message → Claude → (tool_use | text)
  tool_use    → execute_tool() → tool_result → Claude → (tool_use | text)
  text        → retorna para o listener

Max 10 iteracoes pra evitar loops infinitos.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time

logger = logging.getLogger("franz_agent_loop")

# Garantir que backend/ fica no path para imports absolutos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agents.llm_direct import call_claude
from backend.agents.franz.franz_tools import FRANZ_TOOLS, execute_tool

# Max rodadas de tool_use → tool_result antes de forçar resposta textual
_MAX_TURNS = 10


def _build_system_prompt(
    nome_lead: str,
    segmento: str,
    sdr_stage: str,
    historico_recente: str = "",
    site_url: str = "",
) -> str:
    """Monta system prompt contextualizado para Franz."""
    base = f"""Voce e Franz, SDR senior da FraLib. Voce conversa via WhatsApp com leads que receberam uma landing page.

LEAD ATUAL:
- Nome: {nome_lead}
- Segmento: {segmento}
- Stage atual: {sdr_stage}
- Site: {site_url or 'nao deployado ainda'}

DIRETRIZES DE COMUNICACAO (Portugues brasileiro, informal mas profissional):
1. Seja curto e direto — mensagens de WhatsApp tem 1-3 linhas maximo.
2. NUNCA envie JSON, codigo, markdown ou texto formatado. So texto puro.
3. NUNCA use fallbacks genericos do tipo "Me da um minuto". Se nao sabe, admita.
4. Personalize com o nome do lead e dados do segmento.
5. Objetivo: mover o lead para o proximo stage do funil.
6. Nao seja agressivo na venda. Converse, entenda a dor, proponha proximo passo.
7. Se o lead demonstrou interesse forte → proponha uma call ou apresentacao.
8. Se o lead tem duvida tecnica → responda simples, sem jargoes.
9. NUNCA peca dados sensiveis (CPF, RG, cartao) no WhatsApp inicial.
10. Se o lead pedir para parar de receber mensagens → respeite imediatamente.

HISTORICO RECENTE:
{historico_recente or '(primeira mensagem)'}

FERRAMENTAS DISPONIVEIS:
- buscar_lead: busca dados completos do lead
- consultar_historico: ve todas as interacoes anteriores
- consultar_site: ve a URL do site gerado para o lead
- marcar_status_lead: atualiza o status do lead (hot_lead, negociacao, etc)
- registrar_interacao: registra uma interacao no banco
- enviar_whatsapp: envia mensagem WhatsApp (use com cautela)
- agendar_followup: agenda follow-up automatico
- marcar_deferido: marca lead como deferido para contato futuro
- buscar_leads_similares: busca leads do mesmo segmento
- verificar_status_wpp: verifica conexao WhatsApp

IMPORTANTE: Nao invente informacoes sobre o lead ou o site. Se precisar de dados, use as ferramentas.
Seja humano, seja relevante, seja rapido."""
    return base


def run_agent_loop(
    lead_id: str,
    tenant_id: int,
    mensagem_recebida: str,
    nome_lead: str,
    segmento: str = "",
    sdr_stage: str = "",
    telefone: str = "",
    historico_recente: str = "",
    site_url: str = "",
) -> dict:
    """
    Executa o Franz agent loop.

    Returns dict com:
        reply: str — resposta para enviar ao lead
        next_stage: str — stage sugerido para atualizar
        update_facts: dict — dados extras (followup_date, etc)
        tools_used: list — ferramentas chamadas (para debug)
    """
    context = {
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "telefone": telefone,
        "nome_lead": nome_lead,
    }

    system = _build_system_prompt(
        nome_lead=nome_lead,
        segmento=segmento,
        sdr_stage=sdr_stage,
        historico_recente=historico_recente,
        site_url=site_url,
    )

    messages = [
        {"role": "user", "content": f"Mensagem do lead: {mensagem_recebida}"}
    ]

    tools_used = []
    start_time = time.time()

    for turn in range(_MAX_TURNS):
        try:
            resp = call_claude(
                system=system,
                user="",  # ja mandamos na primeira mensagem
                messages=messages if turn > 0 else None,
                model="sonnet",
                max_tokens=1024,
                temperature=0.7,
                agent_name="franz",
                tools=FRANZ_TOOLS,
            )
        except Exception as exc:
            logger.error("Franz agent loop call_claude falhou (turn %d): %s", turn, exc)
            return {
                "reply": "Opa, tive um probleminha aqui. Ja volto pra continuar nossa conversa! 👍",
                "next_stage": sdr_stage or "hook",
                "update_facts": {},
                "tools_used": tools_used,
            }

        # Parse response — pode vir como string JSON ou dict
        if isinstance(resp, str):
            try:
                resp_data = json.loads(resp)
            except json.JSONDecodeError:
                resp_data = {"content": resp, "stop_reason": "end_turn"}
        else:
            resp_data = resp

        # Verificar se Claude quer usar ferramentas
        # Claude API retorna content blocks: [{type: "text", text: "..."}, {type: "tool_use", ...}]
        content_blocks = resp_data.get("content", [])
        if not isinstance(content_blocks, list):
            content_blocks = [content_blocks]

        has_tool_use = any(
            isinstance(b, dict) and b.get("type") == "tool_use"
            for b in content_blocks
        )

        if not has_tool_use:
            # Claude deu resposta textual — extrair texto
            text_parts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            reply_text = "".join(text_parts).strip()

            if not reply_text:
                reply_text = "Opa, tudo bem? Deixa eu verificar algo aqui e ja te respondo!"

            logger.info("Franz agent loop: %d turn(s), %d tools, reply=%d chars",
                       turn + 1, len(tools_used), len(reply_text))
            return {
                "reply": reply_text,
                "next_stage": sdr_stage or "hook",
                "update_facts": {},
                "tools_used": tools_used,
            }

        # Processar tool_use blocks — coletar todas as ferramentas
        assistant_content = []
        tool_results = []

        for block in content_blocks:
            if isinstance(block, dict):
                assistant_content.append(block)

            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue

            tool_name = block.get("name", "")
            tool_input = block.get("input", {})
            tool_id = block.get("id", "")

            logger.debug("Franz tool call: %s(%s)", tool_name, json.dumps(tool_input, ensure_ascii=False))
            tools_used.append(tool_name)

            try:
                result_str = execute_tool(tool_name, tool_input, context)
            except Exception as exc:
                logger.error("execute_tool(%s) falhou: %s", tool_name, exc)
                result_str = json.dumps({"ok": False, "erro": f"Erro interno: {exc}"})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_str[:4000],  # cap tamanho
            })

        # Montar mensagem de assistant + tool_result para o proximo turno
        if turn == 0:
            # Primeiro turn: enviar mensagem original do lead
            messages.append({"role": "user", "content": mensagem_recebida})

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

    # Max turns atingido — forcar resposta
    logger.warning("Franz agent loop: max %d turns atingido, forçando resposta", _MAX_TURNS)
    try:
        resp = call_claude(
            system=system + "\n\nATENCAO: Ja usamos muitas ferramentas. Responda o lead AGORA com texto direto, sem mais tool calls.",
            user="Responda o lead agora. Mensagem original: " + mensagem_recebida,
            model="sonnet",
            max_tokens=512,
            temperature=0.7,
            agent_name="franz",
        )
        if isinstance(resp, str):
            reply_text = resp.strip()
        else:
            reply_text = resp.get("content", [{}])[0].get("text", "").strip() if isinstance(resp.get("content"), list) else str(resp)
    except Exception as exc:
        logger.error("Franz fallback response falhou: %s", exc)
        reply_text = "Opa, tudo bem? Me da um minutinho que ja te respondo! 👍"

    return {
        "reply": reply_text or "Opa, tudo bem? Me da um minutinho que ja te respondo! 👍",
        "next_stage": sdr_stage or "hook",
        "update_facts": {},
        "tools_used": tools_used,
    }
