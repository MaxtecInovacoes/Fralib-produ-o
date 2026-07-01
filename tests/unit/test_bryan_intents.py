from pathlib import Path
import sys
import types

import pytest

pytestmark = pytest.mark.legacy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "agents"))
sys.path.insert(0, str(ROOT / "backend"))


def test_load_context_uses_nested_memory_and_database_stage(monkeypatch):
    from agents.sdr_langgraph import agent

    memory_module = types.SimpleNamespace(
        carregar_memoria=lambda session_id, user_id=None: {
            "estado": "hook",
            "lead": {
                "nome": "Start Academia",
                "segmento": "academia",
                "cidade": "Campina Grande do Sul",
                "site_url": "https://seunegociofralib.site/sites/2/start-academia/",
            },
        }
    )
    monkeypatch.setitem(sys.modules, "agents.memory", memory_module)
    monkeypatch.setattr(agent, "load_rag", lambda _agent_key="": "RAG Franz")
    monkeypatch.setattr(agent, "detect_intent_with_llm", lambda message: "is_decisor")

    result = agent.node_load_context(
        {
            "user_id": 2,
            "lead_id": "lead-1",
            "telefone": "4192049684",
            "incoming_message": "sou o dono",
            "sdr_stage": "pain",
        }
    )

    memory = result["memory"]
    assert memory.nome == "Start Academia"
    assert memory.segmento == "academia"
    assert memory.stage == "pain"
    assert result["detected_intent"] == "is_decisor"


def test_outbound_hook_is_deterministic_and_does_not_reveal_site():
    """Outbound hook NAO pode usar template fixo - deve lancar SDRFallbackError.

    Este teste verifica que o sistema NAO usa template fixo para outbound hooks.
    O comportamento correto é lancar excecao (forcando operador a criar hook manual).
    """
    from agents.sdr_langgraph import agent
    from agents.sdr_langgraph.state import LeadMemory
    from agents.sdr_langgraph.agent import SDRFallbackError

    memory = LeadMemory(
        lead_id="lead-1",
        user_id=2,
        telefone="4192049684",
        nome="Start Academia",
        cidade="Campina Grande do Sul",
        segmento="academia",
        site_url="https://seunegociofralib.site/sites/2/start-academia/",
    )

    # Sistema deve lancar excecao em vez de usar template fixo
    with pytest.raises(SDRFallbackError, match="Outbound hook"):
        agent.node_hook({"memory": memory, "is_outbound": True, "incoming_message": ""})


def test_is_decisor_returns_contextual_reply_instead_of_empty_message():
    from agents.sdr_langgraph import agent
    from agents.sdr_langgraph.state import LeadMemory

    memory = LeadMemory(
        lead_id="lead-1",
        user_id=2,
        telefone="4192049684",
        nome="Start Academia",
        cidade="Campina Grande do Sul",
        segmento="academia",
        stage="qualify",
    )

    result = agent.node_is_decisor({"memory": memory, "incoming_message": "sou o dono"})

    assert result["should_send"]
    assert result["outgoing_message"].strip()
    assert "alunos" in result["outgoing_message"].lower()
    assert memory.stage == "pain"


def test_lobo_persona_is_disabled_by_default(monkeypatch):
    from agents.sdr_langgraph.prompts import should_use_lobo

    monkeypatch.delenv("FRALIB_SDR_ENABLE_LOBO", raising=False)

    assert not should_use_lobo("objection_price", rejection_count=3)


def test_responder_lead_passes_database_stage_to_graph(monkeypatch):
    from agents.sdr_langgraph import compat
    from agents.sdr_langgraph.state import LeadMemory

    captured = {}

    class FakeGraph:
        def invoke(self, initial_state):
            captured.update(initial_state)
            return {
                "memory": LeadMemory(
                    lead_id=initial_state["lead_id"],
                    user_id=initial_state["user_id"],
                    telefone=initial_state["telefone"],
                    stage=initial_state["sdr_stage"],
                ),
                "outgoing_message": "Perfeito. Hoje chegam mais alunos por indicacao, Instagram ou Google?",
                "detected_intent": "other",
            }

    monkeypatch.setattr(compat, "get_sdr_graph", lambda: FakeGraph())
    monkeypatch.setitem(
        sys.modules,
        "agents.memory",
        types.SimpleNamespace(carregar_memoria=lambda session_id, user_id=None: {}),
    )

    out = compat.responder_lead(
        telefone="4192049684",
        mensagem_recebida="tenho interesse",
        lead_id="lead-1",
        sdr_stage="pain",
        user_id=2,
    )

    assert captured["sdr_stage"] == "pain"
    assert out.next_stage == "pain"
import pytest
