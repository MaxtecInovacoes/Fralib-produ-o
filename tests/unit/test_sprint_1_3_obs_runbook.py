"""Testes Sprint 1.3 — safe_log_silent_failure + runbook exists."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from utils.safe_log import safe_log_silent_failure  # noqa: E402


@pytest.mark.unit
class TestSafeLogSilentFailure:
    """safe_log_silent_failure: loga warning estruturado com throttling."""

    def test_logs_warning_with_context(self, caplog):
        caplog.set_level(logging.WARNING, logger="fralib.observability")
        try:
            raise ValueError("test error")
        except ValueError as e:
            safe_log_silent_failure(
                e, op="humanization", lead_id="lead_123", stage="qualify"
            )
        # Pelo menos 1 log
        records = [r for r in caplog.records if r.name == "fralib.observability"]
        assert len(records) >= 1
        # Mensagem tem contexto
        record = records[0]
        assert "humanization" in record.message
        assert "lead_123" in record.message
        assert "qualify" in record.message
        assert "ValueError" in record.message
        assert "test error" in record.message

    def test_throttling_prevents_spam(self, caplog):
        """Mesmo (lead, op) mais de 1x em < 60s → throttled."""
        caplog.set_level(logging.WARNING, logger="fralib.observability")

        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            safe_log_silent_failure(e, op="test_op", lead_id="lead_throttle")
            safe_log_silent_failure(e, op="test_op", lead_id="lead_throttle")
            safe_log_silent_failure(e, op="test_op", lead_id="lead_throttle")

        records = [r for r in caplog.records if r.name == "fralib.observability"]
        # Apenas 1 log (throttle 60s)
        assert len(records) == 1

    def test_different_ops_not_throttled(self, caplog):
        """Mesmo lead, ops diferentes → ambos logam."""
        caplog.set_level(logging.WARNING, logger="fralib.observability")

        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            safe_log_silent_failure(e, op="op_a", lead_id="lead_1")
            safe_log_silent_failure(e, op="op_b", lead_id="lead_1")

        records = [r for r in caplog.records if r.name == "fralib.observability"]
        assert len(records) == 2

    def test_different_leads_not_throttled(self, caplog):
        """Mesmo op, leads diferentes → ambos logam."""
        caplog.set_level(logging.WARNING, logger="fralib.observability")

        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            safe_log_silent_failure(e, op="same_op", lead_id="lead_a")
            safe_log_silent_failure(e, op="same_op", lead_id="lead_b")

        records = [r for r in caplog.records if r.name == "fralib.observability"]
        assert len(records) == 2

    def test_no_lead_id_uses_none_key(self, caplog):
        """lead_id=None funciona com throttle separado."""
        caplog.set_level(logging.WARNING, logger="fralib.observability")

        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            safe_log_silent_failure(e, op="op_no_lead")
            safe_log_silent_failure(e, op="op_no_lead")

        records = [r for r in caplog.records if r.name == "fralib.observability"]
        # Throttle mesmo sem lead_id (key = (None, "op_no_lead"))
        assert len(records) == 1

    def test_extra_kwargs_in_message(self, caplog):
        caplog.set_level(logging.WARNING, logger="fralib.observability")
        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            safe_log_silent_failure(
                e, op="op_extra", lead_id="L", extra={"tokens": 1500, "model": "haiku"}
            )
        records = [r for r in caplog.records if r.name == "fralib.observability"]
        # Extra vem como repr de dict
        assert "tokens" in records[0].message
        assert "1500" in records[0].message
        assert "haiku" in records[0].message


# ── Runbook ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRunbook:
    """Runbook existe e cobre 8 cenarios."""

    def test_runbook_file_exists(self):
        runbook = Path("docs/RUNBOOK.md")
        assert runbook.exists(), "docs/RUNBOOK.md deve existir"

    def test_runbook_covers_8_scenarios(self):
        content = Path("docs/RUNBOOK.md").read_text(encoding="utf-8")
        scenarios = [
            "Redis indisponível",
            "LLM rate limit",
            "LLM 5xx",
            "WhatsApp ban",
            "Franz travado",
            "Tenant silencioso",
            "Pipeline jobs estagnados",
            "Outbound queue DLQ",
        ]
        for s in scenarios:
            # Match tolerant (case insensitive, partial)
            assert s.lower() in content.lower(), f"Runbook nao cobre cenario: {s}"

    def test_runbook_has_recover_steps(self):
        content = Path("docs/RUNBOOK.md").read_text(encoding="utf-8")
        assert "Recover" in content
        assert "Diagnose" in content
        assert "Sintomas" in content
