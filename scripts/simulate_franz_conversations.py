"""Run deterministic Franz SDR conversation simulations without external LLM calls.

This script monkeypatches Franz's LLM call and memory layer so we can test the
state machine, RAG wiring, guardrails, pricing fallback, opt-out, and follow-up
behavior without spending tokens or sending WhatsApp messages.
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend" / "agents")]

import agents.sdr_langgraph as franz  # noqa: E402


class MemoryStore:
    def __init__(self) -> None:
        self.data: dict[tuple[int | None, str], dict] = {}

    def load(self, key: str, user_id: int | None = None):
        return deepcopy(self.data.get((user_id, key)))

    def save(self, key: str, value: dict, user_id: int | None = None) -> None:
        self.data[(user_id, key)] = deepcopy(value)


def _field(prompt: str, label: str, default: str = "") -> str:
    match = re.search(rf"- {re.escape(label)}: (.*)", prompt)
    return match.group(1).strip() if match else default


def fake_call(system, user, model, max_tokens, temperature, agent_name=None, **kwargs):
    """Small deterministic behavior model for simulation."""
    if agent_name != "franz":
        raise AssertionError(f"expected agent_name=franz, got {agent_name}")
    if "Você é Franz" not in system:
        raise AssertionError("Franz system prompt missing")
    if "Conhecimento RAG - Franz" not in user:
        raise AssertionError("Franz RAG was not injected")

    stage = _field(user, "Stage atual", "hook")
    company = (_field(user, "Empresa", "Cliente").split(" (")[0] or "Cliente").strip()
    site_url = _field(user, "Site gerado", "")
    client_match = re.search(r'=== CLIENTE AGORA ===\n"(.*?)"', user, re.DOTALL)
    client_msg = (client_match.group(1) if client_match else "").lower()

    if any(term in client_msg for term in ("amanhã", "amanha", "me chama", "depois")):
        return json.dumps(
            {
                "intent": "schedule",
                "emotion": "ocupado",
                "reply": "Combinado. Posso te chamar amanhã no começo da tarde?",
                "next_stage": "scheduled",
                "should_handoff": False,
                "price_tier": 0,
                "update_facts": {"followup_requested": True},
            }
        )
    if "não tenho interesse" in client_msg or "nao tenho interesse" in client_msg:
        return json.dumps(
            {
                "intent": "rejection",
                "emotion": "resistente",
                "reply": "Sem problema. Antes de eu encerrar, vocês hoje recebem clientes novos mais por indicação ou Google?",
                "next_stage": "pain",
                "should_handoff": False,
                "price_tier": 0,
                "update_facts": {},
            }
        )
    if "quem é" in client_msg or "quem e" in client_msg or "o que você quer" in client_msg:
        return json.dumps(
            {
                "intent": "objection_trust",
                "emotion": "desconfiado",
                "reply": f"Sou Franz, da FraLib. Vi uma oportunidade simples pra {company} aparecer melhor na cidade. Posso te mostrar?",
                "next_stage": "tease",
                "should_handoff": False,
                "price_tier": 0,
                "update_facts": {"lead_asked_what_i_do": True},
            }
        )
    if any(term in client_msg for term in ("quanto", "preço", "preco", "caro", "parcela")):
        return json.dumps(
            {
                "intent": "objection_price",
                "emotion": "aberto",
                "reply": "O projeto completo fica R$ 1.499 em até 12x sem juros.\nSó paga depois que aprovar e estiver no ar.",
                "next_stage": "close",
                "should_handoff": False,
                "price_tier": 1,
                "update_facts": {"main_objection": "price"},
            }
        )
    if any(term in client_msg for term in ("manda", "link", "mostrar", "ver")):
        return json.dumps(
            {
                "intent": "wants_link",
                "emotion": "curioso",
                "reply": f"Aqui está:\n{site_url}\n\nOlha sem compromisso e me diz o que mudaria pra ficar com a cara de vocês.",
                "next_stage": "feedback",
                "should_handoff": False,
                "price_tier": 0,
                "update_facts": {},
            }
        )
    if any(term in client_msg for term in ("sou eu", "sou o dono", "pode falar")):
        return json.dumps(
            {
                "intent": "is_decisor",
                "emotion": "aberto",
                "reply": "Boa. Hoje clientes novos chegam mais por indicação, Instagram ou Google?",
                "next_stage": "pain",
                "should_handoff": False,
                "price_tier": 0,
                "update_facts": {"is_decisor": True},
            }
        )
    if any(term in client_msg for term in ("gostei", "curti", "ficou bom")):
        return json.dumps(
            {
                "intent": "acceptance",
                "emotion": "animado",
                "reply": "Boa. Quer que eu ajuste logo, cores e dados pra deixar pronto pra aprovação?",
                "next_stage": "close",
                "should_handoff": False,
                "price_tier": 0,
                "update_facts": {},
            }
        )

    if stage in ("hook", "intro", "qualify"):
        reply = "Boa tarde! Falo com o responsável pela empresa?"
        next_stage = "qualify"
    elif stage == "pain":
        reply = "Entendi. Se alguém pesquisa esse serviço na cidade, vocês aparecem bem?"
        next_stage = "amplify"
    elif stage == "amplify":
        reply = "Vi uma oportunidade simples de melhorar isso. Posso te mostrar o que eu faria primeiro?"
        next_stage = "tease"
    else:
        reply = "Entendi. Me conta o que faria isso valer a pena pra vocês?"
        next_stage = stage

    return json.dumps(
        {
            "intent": "engagement",
            "emotion": "neutro",
            "reply": reply,
            "next_stage": next_stage,
            "should_handoff": False,
            "price_tier": 0,
            "update_facts": {},
        }
    )


def install_patches(store: MemoryStore) -> None:
    franz._dentro_do_horario = lambda user_id=None: True
    franz._consultar_aprendizado_segmento = lambda segmento: ""
    franz._consultar_variante_vencedora = lambda **kwargs: ""
    franz._carregar_historico_interacoes = lambda *args, **kwargs: ""
    franz.carregar_memoria = store.load
    franz.salvar_memoria = store.save
    franz.call_claude = fake_call


def assert_message_ok(text: str, allow_price: bool = False, allow_link: bool = False) -> None:
    if text.count("?") > 1:
        raise AssertionError(f"more than one question: {text!r}")
    if not allow_price and re.search(r"R\$\s*\d", text):
        raise AssertionError(f"price leaked too early: {text!r}")
    if not allow_link and re.search(r"https?://", text):
        raise AssertionError(f"link leaked too early: {text!r}")
    if len([line for line in text.splitlines() if line.strip()]) > 3:
        raise AssertionError(f"too many lines: {text!r}")


def run_scenario(name: str, messages: list[str]) -> list[tuple[str, str]]:
    store = MemoryStore()
    install_patches(store)
    lead = franz.BryanInput(
        nome="Óticas Teste",
        cidade="Campina Grande do Sul",
        segmento="ótica",
        telefone="41999999999",
        rating=4.8,
        site_url="https://seunegociofralib.site/sites/1/oticas-teste/",
        tier="STANDARD",
    )
    transcript: list[tuple[str, str]] = []
    intro = franz.iniciar_contato(lead, user_id=1)
    assert_message_ok(intro.reply)
    transcript.append(("Franz", intro.reply))
    for msg in messages:
        transcript.append(("Lead", msg))
        out = franz.responder_lead(lead.telefone, msg, lead.nome, user_id=1)
        allow_link = out.intent == "wants_link" or out.next_stage in ("feedback", "close", "reveal")
        allow_price = out.intent == "objection_price" and out.next_stage in ("close", "urgency", "negotiation", "negociacao")
        assert_message_ok(out.reply, allow_price=allow_price, allow_link=allow_link)
        if out.intent == "schedule" and out.next_stage != "scheduled":
            raise AssertionError(f"schedule intent did not schedule follow-up: {out}")
        transcript.append(("Franz", out.reply))
    print(f"\n=== {name} ===")
    for speaker, text in transcript:
        print(f"{speaker}: {text}")
    return transcript


def main() -> None:
    scenarios = {
        "interessado_ate_link_e_preco": [
            "sou eu, pode falar",
            "hoje vem mais por indicação",
            "manda o link pra eu ver",
            "gostei, quanto custa?",
        ],
        "sem_interesse": [
            "não tenho interesse",
            "não quero mesmo",
            "para",
        ],
        "desconfiado": [
            "quem é você e o que quer?",
            "manda então",
        ],
        "foge_para_depois": [
            "estou ocupado, me chama amanhã",
        ],
    }
    for name, messages in scenarios.items():
        run_scenario(name, messages)
    print("\nOK: Franz simulation suite passed")


if __name__ == "__main__":
    main()
