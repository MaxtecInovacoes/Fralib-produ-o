from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.pipeline_phase_tracking import pipeline_phase_key, set_pipeline_job_phase


def test_pipeline_phase_key_maps_known_phases_and_arquiteto_alias():
    assert pipeline_phase_key(1) == "hunter"
    assert pipeline_phase_key(9) == "builder_renderer"
    assert pipeline_phase_key(10) == "deploy"
    assert pipeline_phase_key(6, "arquiteto mestre") == "designer"
    assert pipeline_phase_key(99) == "fase_99"


class _FakeBeginConnection:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.calls.append((str(query), params))


class _FakeEngine:
    def __init__(self):
        self.connection = _FakeBeginConnection()

    def begin(self):
        return self.connection


def test_set_pipeline_job_phase_updates_by_job_id():
    engine = _FakeEngine()

    set_pipeline_job_phase(engine, {"_job_id": 123, "_run_id": "run-1"}, 2, "builder_renderer")

    query, params = engine.connection.calls[0]
    assert "UPDATE jobs" in query
    assert params == {
        "fase": "builder_renderer",
        "tenant_id": 2,
        "job_id": 123,
        "run_id": "run-1",
    }


def test_set_pipeline_job_phase_skips_when_no_job_or_run_id():
    engine = _FakeEngine()

    set_pipeline_job_phase(engine, {}, 2, "hunter")

    assert engine.connection.calls == []


def test_set_pipeline_job_phase_caps_phase_length():
    engine = _FakeEngine()

    set_pipeline_job_phase(engine, {"_run_id": "run-1"}, 2, "x" * 120)

    assert len(engine.connection.calls[0][1]["fase"]) == 80
