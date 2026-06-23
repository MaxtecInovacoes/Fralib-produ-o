"""Site Offer Helper.

Gera texto contextualizado pro Franz oferecer o site pronto (gratis, sem custo)
em QUALQUER momento da conversa - nao so no stage reveal.

Regras de UX:
1. Sempre oferecer o site (gratis, sem custo) ANTES de pedir qualificacao completa
2. Para gatekeeper: pedir pra mostrar pro decisor ("leva 2 min, e sem custo")
3. Anti-link-blindness: muitos nao clicam em link -> instrucoes explicitas de copia/cola
4. Link temporario com explicacao clara ("link de demonstracao")
5. NUNCA oferecer preco antes do lead pedir

Casos cobertos:
- offer_proactive(): na propria hook (sem aguardar lead pedir)
- offer_after_qualify(): apos 2-3 msgs com lead engajado
- offer_in_objection(): quando lead tem objecao (mostra que ja fez o trabalho)
- offer_to_gatekeeper(): quando e assistente, oferecer pra mostrar pro decisor
- offer_after_optout_attempt(): como ultimo recurso antes de aceitar
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_site_url_for_lead(memory) -> Optional[str]:
    """Retorna a URL do site pronto do lead, ou None se nao existir."""
    url = getattr(memory, "site_url", None)
    if not url or not str(url).strip():
        return None
    return str(url).strip()


def offer_proactive(memory, segmento: str = "", lead_nome: str = "") -> str:
    """Oferta proativa no primeiro contato - sem aguardar lead pedir.

    Args:
        memory: LeadMemory do lead.
        segmento: segmento do lead (academia, nutricionista, etc).
        lead_nome: nome do lead (opcional).

    Returns:
        Texto completo pronto pra enviar. None se nao tem site_url.
    """
    url = get_site_url_for_lead(memory)
    if not url:
        return None

    nome = lead_nome or getattr(memory, "nome", "") or "vocês"
    seg = segmento or getattr(memory, "segmento", "") or "seu negócio"

    return (
        f"Ei, sem compromisso nenhum: ja montei um site de demonstracao pra {nome}, "
        f"personalizado pro {seg}. E so pra voce ver a ideia — nao tem custo, nao "
        f"pede cartao, nao tem letras miudas. Se gostar a gente conversa depois.\n\n"
        f"Link: {url}\n\n"
        f"(Se nao abrir ao clicar, copia o link e cola no navegador do celular "
        f"ou computador — e um link temporario de demonstracao, nao tem problema nenhum.)"
    )


def offer_after_qualify(memory) -> str:
    """Oferta apos o lead ja ter engajado (1-2 msgs de conversa).

    Tom: "Como voce ja ta aqui, deixa eu te mostrar..."
    """
    url = get_site_url_for_lead(memory)
    if not url:
        return None

    nome = getattr(memory, "nome", "") or "vocês"

    return (
        f"Olha, ja que a gente ta conversando — acabei de montar um site de demonstracao "
        f"pra {nome}, totalmente sem compromisso. E so pra ver a ideia mesmo, nao tem "
        f"custo, nao tem que pagar nada.\n\n"
        f"Toma o link: {url}\n\n"
        f"Dica: se nao abrir direto, copia e cola no navegador. E um link temporario, "
        f"sem pegadinha nenhuma. Quando voce ver, me conta o que achou?"
    )


def offer_in_objection(memory, objection_type: str = "general") -> str:
    """Oferta quando lead objecao (preco, ja tem site, ja tem empresa).

    Tom: "O trabalho ja foi feito, voce so precisa ver."

    Args:
        objection_type: tipo de objecao (price, has_provider, no_need, time, trust).
    """
    url = get_site_url_for_lead(memory)
    if not url:
        return None

    nome = getattr(memory, "nome", "") or "vocês"

    # Counter-arguments por tipo
    counters = {
        "price": "Eu entendo que preco e uma preocupacao — mas esse e so o site de demonstracao, sem custo nenhum. Voce so paga SE aprovar e quiser colocar no ar.",
        "has_provider": "Que bom que voce ja tem alguem cuidando! Esse aqui e so uma demonstracao gratis, sem compromisso. Se voce gostar do que a gente fez, ai sim vale a pena comparar.",
        "no_need": "Tudo bem, talvez agora nao seja o momento. Mas a demonstracao ja esta pronta — da uma olhada de 2 minutos, sem compromisso. Quem sabe fica na manga pra quando precisar.",
        "time": "Levou poucos minutos. Posso te mandar o link agora, voce ve quando puder. Sem pressa.",
        "trust": "Entendo a cautela. E por isso que e so demonstracao — voce ve primeiro, sem pagar nada, sem compromisso. Se nao gostar, sem problema.",
        "general": "Entendo. Mas ja que a gente se falou, queria te mostrar uma coisa: a demonstracao do site ja esta pronta. E gratis, sem compromisso, sem custo."
    }
    counter = counters.get(objection_type, counters["general"])

    return (
        f"{counter}\n\n"
        f"Link de demonstracao (temporario, sem custo):\n{url}\n\n"
        f"(Se o link nao abrir, copia e cola no navegador do celular ou computador. "
        f"E so pra voce ver — depois a gente conversa.)"
    )


def offer_to_gatekeeper(memory, decisor_name_hint: str = "") -> str:
    """Oferta quando o lead NAO e decisor (assistente, recepcionista).

    Tom: "Voce pode mostrar pro dono/decisor? Leva 2 min."
    """
    url = get_site_url_for_lead(memory)
    if not url:
        return None

    nome = getattr(memory, "nome", "") or "vocês"
    decisor = decisor_name_hint or "ele"  # pronome generico

    return (
        f"Tranquilo! Sem problema. Posso te pedir uma coisa rapida? Ja esta pronta uma "
        f"demonstracao de site personalizada pra {nome}. E gratis, sem compromisso, leva "
        f"2 min pra ver. Voce consegue mostrar isso pro {decisor} quando ele tiver um tempinho?\n\n"
        f"Link de demonstracao: {url}\n\n"
        f"(Se o link nao abrir direto, copia e cola no navegador. E temporario, sem custo, "
        f"sem pegadinha. Se o {decisor} gostar, ai sim a gente conversa melhor. "
        f"Se nao, sem problema nenhum.)"
    )


def offer_after_optout_attempt(memory) -> str:
    """Oferta como ULTIMO recurso antes de aceitar opt-out.

    Tom: "Antes de ir, deixa eu te mostrar uma coisa que pode mudar de ideia."
    """
    url = get_site_url_for_lead(memory)
    if not url:
        return None

    nome = getattr(memory, "nome", "") or "vocês"

    return (
        f"Antes de ir, uma ultima coisa (e gratuita, sem compromisso): ja esta pronto "
        f"um site de demonstracao pra {nome}. Voce leva 2 minutos pra ver, decide depois.\n\n"
        f"Link: {url}\n\n"
        f"(Copia e cola no navegador se nao abrir ao clicar. E temporario, sem custo. "
        f"Olha sem compromisso — quem sabe voce gosta do que a gente fez. "
        f"Se nao gostar, tudo certo, sem ressentimento.)"
    )


def should_offer_site(memory, intent: str = "", turn_count: int = 0) -> bool:
    """Decide se o Franz DEVE oferecer o site neste turno.

    Args:
        memory: LeadMemory.
        intent: intent classificado.
        turn_count: numero de turnos ate agora.

    Returns:
        True se Franz deve oferecer o site, False caso contrario.
    """
    if not get_site_url_for_lead(memory):
        return False

    # Se o lead ja optou, NAO oferecer (deixar porta aberta mas sem forçar)
    state = getattr(memory, "conversation_state", "")
    if state in ("opt_out", "handed_off", "closed_won", "closed_lost", "scheduled"):
        return False

    # Ja ofereceu 2x neste lead? Nao insistir
    offers_made = getattr(memory, "site_offer_count", 0)
    if offers_made >= 2:
        return False

    # Lead pediu pra ver? SIM, sempre.
    if intent in ("buying_intent", "engagement", "question"):
        return True

    # Lead e gatekeeper? SIM, pra mostrar pro decisor.
    if intent == "gatekeeper":
        return True

    # Lead objecao? SIM, pra mostrar que ja fez o trabalho.
    if intent == "objection":
        return True

    # Lead cumprimentou 2x sem engajar? SIM, proativa.
    if intent == "greeting" and turn_count >= 2:
        return True

    # Lead engajou (respondeu pergunta)? SIM.
    if intent == "engagement":
        return True

    return False


def increment_offer_count(memory) -> None:
    """Incrementa contador de ofertas do site (chamado apos enviar)."""
    current = getattr(memory, "site_offer_count", 0)
    memory.site_offer_count = current + 1