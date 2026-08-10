# Franz Agent Loop - MCP-like agent loop for WhatsApp conversations
from __future__ import annotations

from typing import Optional, List, Dict, Any

from .franz_tools import FranzAgentOutput, execute_tool, get_available_tools, _tool_check_intent, _tool_send_template, _tool_escalate_human


# Stage progression map
_STAGE_PROGRESSION = {
    "hook": "qualification",
    "qualification": "objection_handling",
    "objection_handling": "closing",
    "closing": "follow_up",
    "follow_up": "closed",
    "lost": "closed",
    "opt_out": "closed",
}


def franz_agent_loop(
    lead_data: Dict[str, Any],
    mensagem: str,
    historico_resumo: str = "",
    sdr_stage: str = "hook",
    user_id: int = 0,
    max_iterations: int = 3,
) -> FranzAgentOutput:
    """Franz agent loop — processa mensagem do lead e retorna resposta SDR.

    Args:
        lead_data: dict com {id, nome, segmento, cidade, telefone, ...}
        mensagem: texto recebido do lead
        historico_resumo: resumo do histórico (não usado atualmente)
        sdr_stage: estágio atual do funil SDR
        user_id: tenant_id do lead
        max_iterations: max tool calls por resposta

    Returns:
        FranzAgentOutput com reply, novo_stage, tools_used, etc.
    """
    tools_used: List[str] = []
    iterations = 0

    nome = lead_data.get("nome", "Lead")
    segmento = lead_data.get("segmento", "")
    cidade = lead_data.get("cidade", "")

    # 1. Check intent
    intent_result = _tool_check_intent({"message": mensagem}, {"lead_data": lead_data})
    intent = intent_result.get("intent", "unknown")
    tools_used.append("check_intent")

    # 2. Handle special intents
    if intent == "opt_out":
        return FranzAgentOutput(
            reply="Tudo bem! Se mudar de ideia, estarei por aqui. 👋",
            intent="opt_out",
            novo_stage="opt_out",
            tools_used=tools_used,
            iterations=0,
            should_handoff=False,
        )

    if intent == "agendamento":
        return FranzAgentOutput(
            reply=f"Ótimo, {nome}! Que tal agendarmos uma call rápida? Me diga o melhor horário e eu confirmo! 📅",
            intent="agendamento",
            novo_stage="closing",
            tools_used=tools_used,
            iterations=0,
        )

    if intent == "objecao":
        tools_used.append("send_template")
        tmpl = _tool_send_template({"template_id": "objection_price"}, {"lead_data": lead_data})
        reply = tmpl.get("reply", "Entendo! Vamos conversar sobre valores.")
        return FranzAgentOutput(
            reply=reply,
            intent="objecao",
            novo_stage="qualification",
            tools_used=tools_used,
            iterations=0,
        )

    # 3. Normal SDR flow — respond based on stage
    reply = _generate_reply(nome, segmento, cidade, sdr_stage, mensagem, intent, lead_data)

    # 4. Advance stage
    novo_stage = _STAGE_PROGRESSION.get(sdr_stage, sdr_stage)

    # 5. Escalation check
    should_handoff = sdr_stage in ("closed", "lost", "opt_out")

    return FranzAgentOutput(
        reply=reply,
        intent=intent,
        novo_stage=novo_stage,
        tools_used=tools_used,
        iterations=iterations,
        resposta=reply,
        should_handoff=should_handoff,
    )


# ---------------------------------------------------------------------------
# Stage-specific reply generators
# ---------------------------------------------------------------------------

_STAGE_REPLIES: Dict[str, List[str]] = {
    "hook": [
        "{nome}, vi que você tem um negócio de {segmento} em {cidade}! 🚀 Muitos empresários da área estão usando site profissional para fechar mais contratos. Quer saber como funciona?",
        "Oi {nome}! Tudo bem? Estou entrando em contato sobre {segmento} em {cidade} — preparei uma oferta especial pra você! 😊",
        "E aí {nome}! Aqui é o Franz da FraLib. Vi que você trabalha com {segmento} aí em {cidade} e tenho uma ideia que pode multiplicar seus clientes. Bora conversar?",
    ],
    "qualification": [
        "Para eu te passar a solução ideal: quantos clientes você atende por mês? E já tem site ou está começando do zero?",
        "Me conta mais: você prefere um site mais simples para mostrar serviços ou algo mais completo com agendamento online?",
        "Certo! E qual é o maior desafio hoje — atrair novos clientes ou converter os que já te encontram?",
    ],
    "objection_handling": [
        "Te entendo, {nome}. O investimento é menor do que parece — muitos clientes recuperam o valor no primeiro mês. Quer que eu te mostre um case parecido?",
        "Sem pressa nenhuma! Vamos começar com algo que caiba no seu bolso. O importante é dar o primeiro passo. 👍",
    ],
    "closing": [
        "Perfeito! Vou preparar tudo. Você prefere receber o link por aqui ou por e-mail? 📲",
        "Show! Pra começar, me confirma seu melhor horário para eu enviar a proposta completa?",
    ],
    "follow_up": [
        "Oi {nome}! Passando pra ver se conseguiu ver a proposta. Alguma dúvida? Estou aqui! 😊",
        "E aí, {nome}! Lembrete: a oferta especial pra {cidade} ainda tá valendo essa semana. Quer avançar?",
    ],
}


def _generate_reply(
    nome: str,
    segmento: str,
    cidade: str,
    stage: str,
    mensagem: str,
    intent: str,
    lead_data: Dict[str, Any],
) -> str:
    """Generate a contextual SDR reply based on stage and intent."""
    import random
    templates = _STAGE_REPLIES.get(stage, _STAGE_REPLIES["hook"])
    template = random.choice(templates)

    reply = template.format(
        nome=nome or "parceiro",
        segmento=segmento or "seu segmento",
        cidade=cidade or "sua região",
    )

    # If lead sent a question, acknowledge it
    if mensagem.strip().endswith("?") or intent in ("qualificacao", "interesse"):
        reply = f"Boa pergunta! {reply}"

    return reply
