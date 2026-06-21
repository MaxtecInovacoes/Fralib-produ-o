"""Testes do modulo handoff (SDR -> Closer humano)."""
from unittest.mock import MagicMock, patch

import pytest


class TestShouldHandoff:
    def _make_memory(self, **overrides):
        m = MagicMock()
        m.bant_budget = ""
        m.bant_authority = ""
        m.bant_need_score = 0
        m.bant_timeline = ""
        m.stage = "hook"
        m.lead_temperature = "morno"
        m.main_objection = ""
        for k, v in overrides.items():
            setattr(m, k, v)
        return m

    def test_bant_completo_no_close_faz_handoff(self):
        m = self._make_memory(
            bant_budget="menos_500",
            bant_authority="decisor",
            bant_timeline="30_dias",
            stage="close",
        )
        from backend.agents.sdr_langgraph.handoff import should_handoff
        ok, reason = should_handoff(m, "Quero fechar")
        assert ok is True
        assert reason == "bant_complete_close"

    def test_lead_pediu_humano_faz_handoff(self):
        m = self._make_memory()
        from backend.agents.sdr_langgraph.handoff import should_handoff
        ok, reason = should_handoff(m, "Quero falar com humano")
        assert ok is True
        assert reason == "lead_pediu_humano"

    def test_lead_quente_no_reveal_faz_handoff(self):
        m = self._make_memory(lead_temperature="quente", stage="reveal")
        from backend.agents.sdr_langgraph.handoff import should_handoff
        ok, reason = should_handoff(m, "Gostei do site")
        assert ok is True
        assert reason == "lead_quente_revel"

    def test_lead_frio_hook_nao_faz_handoff(self):
        m = self._make_memory(lead_temperature="frio", stage="hook")
        from backend.agents.sdr_langgraph.handoff import should_handoff
        ok, reason = should_handoff(m, "ok")
        assert ok is False

    def test_bant_score_alto_close_faz_handoff(self):
        m = self._make_memory(
            bant_budget="500_1500",
            bant_need_score=15,
            bant_timeline="90_dias",
            stage="close",
        )
        from backend.agents.sdr_langgraph.handoff import should_handoff
        ok, reason = should_handoff(m, "Interessante")
        assert ok is True
        assert reason == "bant_score_alto"

    def test_triggers_human_variations(self):
        m = self._make_memory()
        from backend.agents.sdr_langgraph.handoff import should_handoff
        for trigger in ["Quero pessoa real", "Me passa o gerente", "Tem um atendente?"]:
            ok, reason = should_handoff(m, trigger)
            assert ok is True, f"Falhou para: {trigger}"


class TestHandoffToCloser:
    @patch("backend.agents.sdr_langgraph.handoff._notify_closer_via_whatsapp")
    @patch("backend.services.closer_queue.enqueue_closer")
    def test_enqueue_com_contexto_completo(self, mock_enqueue, mock_notify):
        mock_enqueue.return_value = 42
        mock_memory = MagicMock()
        mock_memory.telefone = "11999999999"
        mock_memory.lead_temperature = "quente"
        mock_memory.msgs_sent_count = 5
        mock_memory.wall_street_close_used = True
        mock_memory.pain_identified = "Perde cliente pro concorrente"
        mock_memory.main_objection = "achou caro"
        mock_memory.meddic_score = 8
        mock_memory.bant_budget = "500_1500"
        mock_memory.bant_authority = "decisor"
        mock_memory.bant_need_score = 8
        mock_memory.bant_timeline = "30_dias"
        mock_memory.humanization_profile = {"avg_response_time_min": 5}
        mock_memory.top_concorrentes = ["Concorrente X"]
        mock_memory.agent_notes = {"last_msgs_sent": []}
        mock_memory.variant = "A"

        history = [
            {"direcao": "entrada", "mensagem": "Oi", "criado_em": "2026-06-21T10:00:00"},
            {"direcao": "saida", "mensagem": "Oi tudo bem", "criado_em": "2026-06-21T10:01:00"},
        ]

        from backend.agents.sdr_langgraph.handoff import handoff_to_closer
        queue_id = handoff_to_closer(
            user_id=1,
            lead_id=100,
            lead_telefone="11999999999",
            lead_nome="Academia X",
            stage="close",
            memory=mock_memory,
            history=history,
        )

        assert queue_id == 42
        assert mock_memory.is_human_takeover is True
        mock_enqueue.assert_called_once()
        call_args = mock_enqueue.call_args.kwargs
        assert call_args["user_id"] == 1
        assert call_args["lead_id"] == 100
        assert call_args["temperature"] == "quente"
        assert call_args["bant_score"] == 33  # 10 budget + 5 authority + 8 need + 10 timeline
        assert "last_messages" in call_args["context"]
