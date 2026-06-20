"""
Testes de integração para o fluxo SDR (Franz).

Estes testes verificam o fluxo E2E do SDR, incluindo:
1. Lead responde → Franz responde corretamente
2. Lead responde → não duplica mensagem
3. Outbound introdução continua funcionando

Executar: python -m pytest tests/integration/test_sdr_flow.py -v
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import pytest
from unittest.mock import MagicMock, patch


# ════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_lead_data():
    """Dados mock de um lead."""
    return {
        "telefone": "5511999999999",
        "lead_id": "lead_123",
        "nome": "Empresa Teste",
        "cidade": "São Paulo",
        "segmento": "tech",
        "rating": 4.5,
        "site_url": "https://empresa.com.br",
        "sdr_stage": "hook",
        "user_id": 1,
    }


@pytest.fixture
def mock_history():
    """History mock de conversa."""
    return [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Olá! Vi que você tem um site. Posso ajudar?"},
    ]


# ════════════════════════════════════════════════════════════════════
# BUG 1: Resposta JSON - E2E
# ════════════════════════════════════════════════════════════════════

def test_lead_responde_franz_responde_corretamente(mock_lead_data, mock_history):
    """
    E2E: Lead envia mensagem → Franz gera resposta correta (não JSON).

    BUG: Se Franz gerar JSON, não deve ser enviado ao lead.
    """
    from agents.sdr_langgraph.compat import responder_lead

    # Mock do grafo para retornar resposta limpa
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Claro! Vamos agendar uma conversa?",
            "detected_intent": "interested",
            "guard_reason": None,
            "memory": MagicMock(
                stage="qualify",
                active_agent="qualificacao",
                previous_agent="",
                model_dump=lambda: {}
            ),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance

        # Mock carregar_memoria
        with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
            mock_mem.return_value = {
                "nome": "Empresa Teste",
                "cidade": "São Paulo",
                "stage": "hook",
            }

            result = responder_lead(
                telefone=mock_lead_data["telefone"],
                mensagem_recebida="Quero saber mais sobre o serviço",
                nome_negocio=mock_lead_data["nome"],
                lead_id=mock_lead_data["lead_id"],
                cidade=mock_lead_data["cidade"],
                segmento=mock_lead_data["segmento"],
                rating=mock_lead_data["rating"],
                site_url=mock_lead_data["site_url"],
                history=mock_history,
                sdr_stage=mock_lead_data["sdr_stage"],
                user_id=mock_lead_data["user_id"],
            )

    # Verificar que resposta não é JSON
    assert not result.reply.startswith("{")
    assert '"resposta"' not in result.reply
    assert result.reply == "Claro! Vamos agendar uma conversa?"


def test_responder_nao_envia_json_puro_e2e(mock_lead_data):
    """
    E2E: Se Franz gerar JSON puro, NÃO deve ser enviado ao lead.
    """
    from agents.sdr_langgraph.compat import responder_lead

    # Mock do grafo para retornar JSON inválido
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": '{"invalid": "json"}',
            "detected_intent": "other",
            "guard_reason": None,
            "memory": MagicMock(
                stage="hook",
                active_agent="atendimento",
                previous_agent="",
                model_dump=lambda: {}
            ),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance

        with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}

            result = responder_lead(
                telefone=mock_lead_data["telefone"],
                mensagem_recebida="Olá",
                lead_id=mock_lead_data["lead_id"],
                user_id=mock_lead_data["user_id"],
            )

    # Se a resposta começar com { ou contiver "resposta", o listener
    # deve retornar (não enviar)
    should_send = not (
        result.reply.startswith("{") or
        '"resposta"' in result.reply or
        '"novo_stage"' in result.reply
    )

    assert should_send is False, "JSON puro não deve ser enviado"


# ════════════════════════════════════════════════════════════════════
# BUG 2: Watchdog - E2E
# ════════════════════════════════════════════════════════════════════

def test_lead_responde_nao_duplica_mensagem(mock_lead_data, mock_history):
    """
    E2E: Se lead responder, watchdog NÃO deve bloquear resposta.

    BUG: Watchdog estava bloqueando leads que responderam.
    """
    from agents.sdr_langgraph.watchdog import can_send_next_outbound

    # Com lead_responded=True, deve liberar
    pode_enviar, motivo = can_send_next_outbound(
        telefone=mock_lead_data["telefone"],
        user_id=mock_lead_data["user_id"],
        sdr_stage=mock_lead_data["sdr_stage"],
        lead_responded=True,  # BUGFIX: Este parâmetro reseta o watchdog
    )

    assert pode_enviar is True
    assert motivo == "lead_responded_can_reply"


def test_outbound_introducao_continua_funcionando(mock_lead_data):
    """
    E2E: Outbound (introdução) deve continuar funcionando normalmente.

    Garante que a correção do BUG 2 não quebrou o fluxo de outbound.
    """
    from agents.sdr_langgraph.compat import iniciar_contato

    # Mock do grafo para outbound
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Olá! Vi seu site e gostaria de ajudar.",
            "detected_intent": "outbound_intro",
            "guard_reason": None,
            "memory": MagicMock(
                stage="hook",
                active_agent="abordagem",
                previous_agent="",
                model_dump=lambda: {}
            ),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance

        # Mock watchdog para permitir envio
        with patch("agents.sdr_langgraph.compat._verificar_watchdog_outbound") as mock_watchdog:
            mock_watchdog.return_value = (True, "ok")

            with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
                mock_mem.return_value = {}

                result = iniciar_contato(
                    telefone=mock_lead_data["telefone"],
                    nome_negocio=mock_lead_data["nome"],
                    lead_id=mock_lead_data["lead_id"],
                    cidade=mock_lead_data["cidade"],
                    segmento=mock_lead_data["segmento"],
                    site_url=mock_lead_data["site_url"],
                    user_id=mock_lead_data["user_id"],
                )

    # Verificar que resposta foi gerada
    assert result.reply is not None
    assert len(result.reply) > 0
    assert result.enviado is True


# ════════════════════════════════════════════════════════════════════
# BUG 3: History sincronizada - E2E
# ════════════════════════════════════════════════════════════════════

def test_history_e2e_com_state_anterior(mock_lead_data):
    """
    E2E: History deve incluir mensagens do state LangGraph anterior.

    Simula que o lead está em uma conversa de longa duração.
    """
    from agents.sdr_langgraph.compat import responder_lead

    # History do DB (curta)
    db_history = [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Oi! Tudo bem?"},
    ]

    # Memória com state LangGraph (mais longo)
    langgraph_state = {
        "conversation_history": [
            {"type": "human", "content": "Mensagem antiga 1"},
            {"type": "ai", "content": "Resposta antiga 1"},
            {"type": "human", "content": "Mensagem antiga 2"},
            {"type": "ai", "content": "Resposta antiga 2"},
        ],
        "stage": "hook",
    }

    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Entendi! Continue me contando.",
            "detected_intent": "other",
            "guard_reason": None,
            "memory": MagicMock(
                stage="hook",
                active_agent="atendimento",
                previous_agent="",
                model_dump=lambda: {}
            ),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance

        with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
            mock_mem.return_value = langgraph_state

            # Capturar o state passado para o grafo
            captured_state = {}
            def capture_state(state):
                captured_state.update(state)
                return mock_instance.invoke.return_value

            mock_instance.invoke.side_effect = capture_state

            result = responder_lead(
                telefone=mock_lead_data["telefone"],
                mensagem_recebida="Continuando nossa conversa",
                lead_id=mock_lead_data["lead_id"],
                history=db_history,
                user_id=mock_lead_data["user_id"],
            )

    # Verificar que history mesclada foi passada
    passed_history = captured_state.get("history", [])

    # Deve conter mensagens do DB
    db_contents = [m["content"] for m in passed_history]
    assert "Olá" in db_contents
    assert "Oi! Tudo bem?" in db_contents

    # Deve conter mensagens do state LangGraph
    assert "Mensagem antiga 1" in db_contents
    assert "Resposta antiga 1" in db_contents


# ════════════════════════════════════════════════════════════════════
# Testes de regressão
# ════════════════════════════════════════════════════════════════════

def test_responder_lead_error_handling(mock_lead_data):
    """
    Se o grafo lançar erro, deve retornar resposta fallback.
    """
    from agents.sdr_langgraph.compat import responder_lead

    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = Exception("Grafo quebrou")
        mock_graph.return_value = mock_instance

        with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}

            result = responder_lead(
                telefone=mock_lead_data["telefone"],
                mensagem_recebida="Olá",
                lead_id=mock_lead_data["lead_id"],
                user_id=mock_lead_data["user_id"],
            )

    # Deve ter resposta fallback
    assert result.reply is not None
    assert result.reply != ""
    assert result.guard == "graph_error"


def test_followup_automatico_continua_funcionando(mock_lead_data):
    """
    Follow-up automático deve continuar funcionando.
    """
    from agents.sdr_langgraph.compat import followup_automatico

    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Olá! Retomando nossa conversa...",
            "detected_intent": "followup",
            "guard_reason": None,
            "memory": MagicMock(
                stage="followup_24h",
                active_agent="followup",
                previous_agent="",
                model_dump=lambda: {}
            ),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance

        with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}

            with patch("agents.sdr_langgraph.compat._verificar_watchdog_outbound") as mock_watchdog:
                mock_watchdog.return_value = (True, "ok")

                result = followup_automatico(
                    telefone=mock_lead_data["telefone"],
                    tipo="24h",
                    user_id=mock_lead_data["user_id"],
                )

    assert result.reply is not None
    assert result.enviado is True


def test_is_outbound_marcado_corretamente_para_intro(mock_lead_data):
    """
    Mensagem de outbound (introdução) deve ter is_outbound=True.
    """
    from agents.sdr_langgraph.compat import iniciar_contato

    captured_state = {}

    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        def capture_state(state):
            captured_state.update(state)
            return {
                "outgoing_message": "Olá!",
                "detected_intent": "outbound_intro",
                "guard_reason": None,
                "memory": MagicMock(
                    stage="hook",
                    active_agent="abordagem",
                    previous_agent="",
                    model_dump=lambda: {}
                ),
                "agent_handoff_reason": "",
            }
        mock_instance.invoke.side_effect = capture_state
        mock_graph.return_value = mock_instance

        with patch("agents.sdr_langgraph.compat._verificar_watchdog_outbound") as mock_watchdog:
            mock_watchdog.return_value = (True, "ok")

            with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
                mock_mem.return_value = {}

                iniciar_contato(
                    telefone=mock_lead_data["telefone"],
                    nome_negocio=mock_lead_data["nome"],
                    lead_id=mock_lead_data["lead_id"],
                    user_id=mock_lead_data["user_id"],
                )

    # is_outbound deve ser True para introdução
    assert captured_state.get("is_outbound") is True


def test_is_outbound_false_para_resposta(mock_lead_data):
    """
    Resposta a mensagem do lead deve ter is_outbound=False.
    """
    from agents.sdr_langgraph.compat import responder_lead

    captured_state = {}

    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        def capture_state(state):
            captured_state.update(state)
            return {
                "outgoing_message": "Respondendo...",
                "detected_intent": "other",
                "guard_reason": None,
                "memory": MagicMock(
                    stage="hook",
                    active_agent="atendimento",
                    previous_agent="",
                    model_dump=lambda: {}
                ),
                "agent_handoff_reason": "",
            }
        mock_instance.invoke.side_effect = capture_state
        mock_graph.return_value = mock_instance

        with patch("agents.sdr_langgraph.compat.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}

            responder_lead(
                telefone=mock_lead_data["telefone"],
                mensagem_recebida="Olá",
                lead_id=mock_lead_data["lead_id"],
                user_id=mock_lead_data["user_id"],
            )

    # is_outbound deve ser False para resposta
    assert captured_state.get("is_outbound") is False
