"""Tests para pipeline_fsm.py — FSM pura do pipeline."""

from __future__ import annotations

import pytest

from backend.pipeline_fsm import PHASES, is_valid_transition, next_phase


class TestPhases:
    def test_phases_contains_all(self) -> None:
        for p in ("hunter", "caio", "nicho", "variacao", "arquiteto",
                  "builder_renderer", "deploy"):
            assert p in PHASES

    def test_phases_order(self) -> None:
        assert PHASES.index("hunter") < PHASES.index("caio")
        assert PHASES.index("caio") < PHASES.index("nicho")
        assert PHASES.index("nicho") < PHASES.index("variacao")
        assert PHASES.index("variacao") < PHASES.index("arquiteto")
        assert PHASES.index("arquiteto") < PHASES.index("builder_renderer")
        assert PHASES.index("builder_renderer") < PHASES.index("deploy")


class TestValidTransition:
    def test_hunter_to_caio_valid(self) -> None:
        assert is_valid_transition("hunter", "caio") is True

    def test_caio_to_nicho_valid_pulo_jina(self) -> None:
        # FSM permite caio→nicho pulando jina em fast-path.
        assert is_valid_transition("caio", "nicho") is True

    def test_nicho_to_variacao_valid(self) -> None:
        assert is_valid_transition("nicho", "variacao") is True

    def test_variacao_to_arquiteto_valid(self) -> None:
        assert is_valid_transition("variacao", "arquiteto") is True

    def test_arquiteto_to_builder_valid(self) -> None:
        assert is_valid_transition("arquiteto", "builder_renderer") is True

    def test_builder_to_deploy_valid_pulo_gate(self) -> None:
        # FSM permite builder→deploy pulando quality_gate/validador
        # em fail-fast.
        assert is_valid_transition("builder_renderer", "deploy") is True

    def test_deploy_to_franz_valid(self) -> None:
        assert is_valid_transition("deploy", "franz_sdr") is True

    def test_unknown_from_invalid(self) -> None:
        assert is_valid_transition("unknown", "caio") is False

    def test_unknown_to_invalid(self) -> None:
        assert is_valid_transition("hunter", "unknown") is False

    def test_backward_invalid(self) -> None:
        assert is_valid_transition("deploy", "hunter") is False


class TestNextPhase:
    def test_hunter_next_is_caio(self) -> None:
        assert next_phase("hunter") == "caio"

    def test_franz_sdr_next_is_none(self) -> None:
        assert next_phase("franz_sdr") is None

    def test_unknown_next_is_none(self) -> None:
        assert next_phase("unknown_phase") is None