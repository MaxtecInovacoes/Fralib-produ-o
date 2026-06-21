"""Testes do Dream job + Agent Bus."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.services.agent_bus import (
    AgentBus,
    BusEvent,
    get_bus,
    publish_deal_won,
    publish_objection_detected,
    publish_pain_identified,
    publish_site_ready,
)
from backend.services.dreamer import (
    GLOBAL_LESSONS_PATH,
    _extract_patterns,
    _promote_lessons,
    run_dream,
)


class TestAgentBus:
    def test_singleton(self):
        b1 = get_bus()
        b2 = get_bus()
        assert b1 is b2

    def test_publish_notifies_subscriber(self):
        bus = AgentBus()
        received = []
        bus.subscribe("lead_responded", lambda e: received.append(e))
        event = BusEvent("lead_responded", "sdr", {"lead_id": 1})
        n = bus.publish(event)
        assert n == 1
        assert len(received) == 1
        assert received[0].payload["lead_id"] == 1

    def test_multi_subscriber(self):
        bus = AgentBus()
        a, b = [], []
        bus.subscribe("objection_detected", lambda e: a.append(e))
        bus.subscribe("objection_detected", lambda e: b.append(e))
        n = bus.publish(BusEvent("objection_detected", "sdr", {"obj": "x"}))
        assert n == 2
        assert len(a) == 1
        assert len(b) == 1

    def test_history_circular_buffer(self):
        bus = AgentBus(max_history=3)
        for i in range(5):
            bus.publish(BusEvent("lead_responded", "sdr", {"i": i}))
        history = bus.get_recent()
        assert len(history) == 3
        # Ultimos 3 (i=2,3,4)
        assert [e.payload["i"] for e in history] == [2, 3, 4]

    def test_filter_by_event_type(self):
        bus = AgentBus()
        bus.publish(BusEvent("lead_responded", "sdr", {"n": 1}))
        bus.publish(BusEvent("site_ready", "builder", {"n": 2}))
        responded = bus.get_recent("lead_responded")
        assert len(responded) == 1
        assert responded[0].payload["n"] == 1

    def test_stats_increment(self):
        bus = AgentBus()
        bus.publish(BusEvent("lead_responded", "sdr", {}))
        bus.publish(BusEvent("lead_responded", "sdr", {}))
        bus.publish(BusEvent("site_ready", "builder", {}))
        stats = bus.get_stats()
        assert stats["lead_responded"] == 2
        assert stats["site_ready"] == 1

    def test_subscriber_exception_nao_quebra(self):
        bus = AgentBus()
        received = []
        def bad_cb(e):
            raise RuntimeError("boom")
        def good_cb(e):
            received.append(e)
        bus.subscribe("deal_won", bad_cb)
        bus.subscribe("deal_won", good_cb)
        n = bus.publish(BusEvent("deal_won", "sdr", {"x": 1}))
        assert n == 1  # so o good_cb conta como sucesso
        assert len(received) == 1


class TestPublishHelpers:
    def test_publish_objection_detected(self):
        bus = get_bus()
        # Limpa history pra nao pegar lixo
        received = []
        bus.subscribe("objection_detected", lambda e: received.append(e))
        n = publish_objection_detected(
            tenant_id=1, segment="academia",
            objection="achou caro", lead_id=42,
            response_template="Justo, mas..."
        )
        assert n >= 1
        assert len(received) >= 1

    def test_publish_pain_identified(self):
        bus = get_bus()
        received = []
        bus.subscribe("pain_identified", lambda e: received.append(e))
        n = publish_pain_identified(
            tenant_id=1, segment="restaurante",
            pain="perco cliente pro concorrente", lead_id=10,
        )
        assert n >= 1
        assert any(e.payload["pain"] == "perco cliente pro concorrente" for e in received)

    def test_publish_site_ready(self):
        bus = get_bus()
        received = []
        bus.subscribe("site_ready", lambda e: received.append(e))
        n = publish_site_ready(
            tenant_id=1, segment="clinica",
            variant="A", lead_id=5, url="https://x.com",
        )
        assert n >= 1

    def test_publish_deal_won(self):
        bus = get_bus()
        received = []
        bus.subscribe("deal_won", lambda e: received.append(e))
        n = publish_deal_won(
            tenant_id=1, segment="academia",
            lead_id=1, bant_score=33,
        )
        assert n >= 1


class TestDreamerPatterns:
    def test_extract_patterns_basicos(self):
        leads = [
            {"segmento": "academia", "stage": "hook", "main_objection": "", "deal_status": "", "wall_street_close_used": False, "bant_budget": "500_1500"},
            {"segmento": "academia", "stage": "close", "main_objection": "achou caro", "deal_status": "won", "wall_street_close_used": True, "bant_budget": "500_1500"},
            {"segmento": "restaurante", "stage": "qualify", "main_objection": "vou pensar", "deal_status": "lost", "wall_street_close_used": False, "bant_budget": ""},
        ]
        patterns = _extract_patterns(leads)
        assert patterns["segmentos_mais_comuns"]["academia"] == 2
        assert patterns["stages_mais_comuns"]["hook"] == 1
        assert patterns["won_count"] == 1
        assert patterns["lost_count"] == 1
        assert patterns["wall_street_close_attempts"] == 1

    def test_promote_lessons_com_padroes(self):
        from collections import Counter
        patterns = {
            "objecoes_comuns": Counter({"achou caro": 5, "vou pensar": 3}),
            "segmentos_mais_comuns": Counter({"academia": 8, "restaurante": 5}),
            "stages_mais_comuns": Counter(),
            "wall_street_close_success": 3,
            "wall_street_close_attempts": 5,
            "bant_budget_distribution": Counter({"500_1500": 10}),
            "bant_authority_distribution": Counter(),
            "bant_timeline_distribution": Counter(),
            "won_count": 3,
            "lost_count": 5,
            "opt_out_count": 1,
        }
        lessons = _promote_lessons(patterns)
        assert any("achou caro" in l for l in lessons)
        assert any("Wall Street" in l for l in lessons)
        assert any("bant" in l.lower() for l in lessons)


class TestDreamRun:
    def test_run_dream_dry_run_sem_dados(self, tmp_path):
        output = tmp_path / "lessons.json"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("backend.services.dreamer.LEARNING_DIR", tmp_path)
            # Cria estrutura vazia
            (tmp_path / "u1").mkdir()
            stats = run_dream(apply=False, output_path=output)
        assert stats.tenants_processed == 0
        assert not output.exists()

    def test_run_dream_dry_run_com_dados(self, tmp_path):
        # Cria estrutura de memoria fake
        u1 = tmp_path / "u1"
        u1.mkdir()
        memory = {
            "lead_id": "1",
            "segmento": "academia",
            "stage": "close",
            "deal_status": "won",
            "main_objection": "achou caro",
            "wall_street_close_used": True,
            "bant_budget": "500_1500",
        }
        (u1 / "franz_lead_1.json").write_text(json.dumps(memory), encoding="utf-8")
        u2 = tmp_path / "u2"
        u2.mkdir()
        (u2 / "franz_lead_2.json").write_text(json.dumps({
            "lead_id": "2",
            "segmento": "academia",
            "stage": "qualify",
            "deal_status": "lost",
            "main_objection": "",
            "bant_budget": "",
        }), encoding="utf-8")

        output = tmp_path / "global_lessons.json"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("backend.services.dreamer.LEARNING_DIR", tmp_path)
            stats = run_dream(apply=True, output_path=output)

        assert stats.tenants_processed == 2
        assert stats.leads_analyzed == 2
        assert stats.lessons_promoted > 0
        assert output.exists()
        lessons_data = json.loads(output.read_text(encoding="utf-8"))
        assert "stats" in lessons_data
        assert "lessons" in lessons_data
        assert lessons_data["stats"]["tenants"] == 2
        assert lessons_data["stats"]["won"] == 1
