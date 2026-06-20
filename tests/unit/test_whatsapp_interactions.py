from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from whatsapp.interactions import save_interaction, update_lead_stage


class _FakeConnection:
    def __init__(self):
        self.calls = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.calls.append((str(query), params))

    def commit(self):
        self.commits += 1


class _FakeEngine:
    def __init__(self):
        self.connection = _FakeConnection()

    def connect(self):
        return self.connection


def _fixed_now():
    return datetime(2026, 6, 17, 10, 30, 0)


def test_save_interaction_persists_direction_and_user_scope():
    engine = _FakeEngine()

    save_interaction(engine, "lead-1", "Oi", "entrada", 2, now_factory=_fixed_now)

    query, params = engine.connection.calls[0]
    assert "INSERT INTO interacoes" in query
    assert params == {
        "lead_id": "lead-1",
        "mensagem": "Oi",
        "direcao": "entrada",
        "criado_em": "2026-06-17T10:30:00",
        "user_id": 2,
    }
    assert engine.connection.commits == 1


def test_update_lead_stage_is_scoped_by_lead_and_user():
    engine = _FakeEngine()

    update_lead_stage(engine, "lead-1", "followup1", 2, now_factory=_fixed_now)

    query, params = engine.connection.calls[0]
    assert "WHERE id=:id AND user_id=:uid" in query
    assert params == {
        "stage": "followup1",
        "ts": "2026-06-17T10:30:00",
        "id": "lead-1",
        "uid": 2,
    }
    assert engine.connection.commits == 1
