from datetime import datetime, timedelta

from backend.endpoints.pipeline_status_endpoints import (
    _pipeline_job_telemetry,
    _pipeline_runtime_summary,
)
from backend.endpoints.sse_endpoints import _build_log_entry


class _MappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _TelemetrySession:
    def __init__(self):
        self.calls = []
        self.rolled_back = False

    def execute(self, statement, params):
        sql = str(statement)
        self.calls.append((sql, params))
        if "FROM pipeline_run_spans" in sql:
            return _MappingResult(
                [
                    {
                        "fase_num": 2,
                        "fase_nome": "caio",
                        "agente": "caio",
                        "modelo": "claude-haiku",
                        "status": "success",
                        "started_at": datetime(2026, 6, 21, 10, 0, 0),
                        "finished_at": datetime(2026, 6, 21, 10, 0, 2),
                        "duracao_ms": 2000,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_read_tokens": 0,
                        "cache_created_tokens": 0,
                        "custo_usd": 0,
                        "erro": None,
                    }
                ]
            )
        if "FROM llm_budget_ledger" in sql:
            return _MappingResult(
                [
                    {
                        "phase": "caio",
                        "agent": "caio",
                        "provider": "anthropic",
                        "model": "claude-haiku",
                        "calls": 2,
                        "input_tokens": 1000,
                        "output_tokens": 250,
                        "cache_read_tokens": 500,
                        "cache_created_tokens": 100,
                        "cost_usd": 0.012345,
                        "latency_ms": 1800,
                    }
                ]
            )
        raise AssertionError(f"unexpected query: {sql}")

    def rollback(self):
        self.rolled_back = True


def test_pipeline_job_telemetry_aggregates_canonical_sources_with_tenant_scope():
    db = _TelemetrySession()
    job = {
        "id": 901,
        "run_id": "run-tenant-2",
        "status": "running",
        "iniciado_em": (datetime.now() - timedelta(seconds=12)).isoformat(),
        "criado_em": datetime.now().isoformat(),
        "concluido_em": None,
    }

    telemetry = _pipeline_job_telemetry(db, 2, job)

    assert telemetry["job_id"] == 901
    assert telemetry["run_id"] == "run-tenant-2"
    assert telemetry["elapsed_seconds"] >= 11
    assert telemetry["phases"][0]["duration_ms"] == 2000
    assert telemetry["llm"]["totals"] == {
        "calls": 2,
        "input_tokens": 1000,
        "output_tokens": 250,
        "cache_read_tokens": 500,
        "cache_created_tokens": 100,
        "cost_usd": 0.012345,
        "latency_ms": 1800,
        "total_tokens": 1850,
    }
    assert all(params["tenant_id"] == 2 for _, params in db.calls)
    assert all("tenant_id = :tenant_id" in sql for sql, _ in db.calls)


def test_structured_sse_log_keeps_pipeline_fields_at_envelope_level():
    entry = _build_log_entry(
        {
            "type": "progress",
            "event_kind": "pipeline_phase",
            "phase": "builder_renderer",
            "label": "Builder em execucao",
            "job_id": 901,
            "run_id": "run-tenant-2",
        },
        "pipeline",
    )

    assert entry["evento"] == "PIPELINE_STATUS"
    assert entry["mensagem"] == "Builder em execucao"
    assert entry["phase"] == "builder_renderer"
    assert entry["job_id"] == 901
    assert entry["run_id"] == "run-tenant-2"


def test_pending_job_does_not_count_queue_wait_as_execution_time():
    db = _TelemetrySession()
    job = {
        "id": 902,
        "run_id": "queued-run",
        "status": "pending",
        "iniciado_em": None,
        "criado_em": (datetime.now() - timedelta(minutes=5)).isoformat(),
        "concluido_em": None,
    }

    telemetry = _pipeline_job_telemetry(db, 2, job)

    assert telemetry["elapsed_seconds"] == 0
    assert telemetry["queued_seconds"] >= 299
    assert telemetry["started_at"] is None
    assert telemetry["queued_at"] == job["criado_em"]


class _SummarySession:
    def __init__(self):
        self.calls = []
        self.rolled_back = False

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return _MappingResult(
            [
                {
                    "sample_size": 3,
                    "average_elapsed_seconds": 612.7,
                    "fastest_seconds": 420,
                    "slowest_seconds": 980,
                    "average_calls": 14.4,
                    "average_tokens": 120345.9,
                    "average_cost_usd": 1.234567,
                }
            ]
        )

    def rollback(self):
        self.rolled_back = True


def test_pipeline_runtime_summary_reports_recent_completed_average():
    db = _SummarySession()

    summary = _pipeline_runtime_summary(db, 2)

    assert summary == {
        "sample_size": 3,
        "average_elapsed_seconds": 612,
        "fastest_seconds": 420,
        "slowest_seconds": 980,
        "average_calls": 14,
        "average_tokens": 120345,
        "average_cost_usd": 1.234567,
    }
    assert db.calls[0][1]["tenant_id"] == 2


def test_pipeline_waveform_uses_measured_telemetry_without_fake_eta():
    source = open(
        "frontend/js/admin/pipeline-waveform.js", encoding="utf-8"
    ).read()

    assert "telemetry.elapsed_seconds" in source
    assert "telemetry.started_at" in source
    assert "telemetry.queued_at" in source
    assert "state.elapsed += 1" not in source
    assert "telemetry.phases" in source
    assert "totals.total_tokens" in source
    assert "runtime_summary" in source
    assert "pwAvg" in source
    assert "pwLogList" in source
    assert "startFakeTicker" not in source
    assert "min restantes" not in source
