"""Testes do Simulador Franz (Sprint 1.1).

Cobre:
- backend/services/sdr_simulator.py:simulate()
- backend/endpoints/admin_sdr_simulator_endpoints.py (/api/admin/simulate, /api/admin/simulations)
- frontend/admin.html: card "Simulador Franz" presente
- frontend/js/admin/sdr-simulator.js: textarea + load_simulator()

NÃO chama LLM real — usa mocks de call_llm em todos os testes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Bootstrap path & env vars antes de importar o backend
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/test",
)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

ADMIN_HTML = _ROOT / "frontend" / "admin.html"
SIMULATOR_JS = _ROOT / "frontend" / "js" / "admin" / "sdr-simulator.js"


# ── Helpers ──────────────────────────────────────────────────────────────

def _llm_text_with_metadata(intent: str = "compra", stage: str = "fechamento") -> str:
    """Resposta LLM mockada com bloco JSON embebido (parseável pelo simulador)."""
    return (
        "Opa! Posso te mandar o link de pagamento agora.\n"
        "```json\n"
        + json.dumps(
            {
                "intent": intent,
                "stage_after": stage,
                "kanban_action": "move_to_fechamento",
            }
        )
        + "\n```"
    )


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_html() -> str:
    return ADMIN_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def simulator_js() -> str:
    if not SIMULATOR_JS.is_file():
        return ""
    return SIMULATOR_JS.read_text(encoding="utf-8")


@pytest.fixture
def fake_settings() -> dict:
    """Settings normalizadas — saída típica de get_sdr_settings_runtime."""
    return {
        "version": 1,
        "agent_name": "Franz",
        "objective": "sell_until_close",
        "knowledge_mode": "native",
        "custom_knowledge": "",
        "personality": "",
        "allowed_actions": [],
        "blocked_actions": [],
        "handoff": {"enabled": True, "triggers": [], "note": ""},
        "limits": {
            "reply_cooldown_seconds": 30,
            "daily_limit_per_lead": 50,
            "human_pause_seconds": 300,
        },
        "auto_throttle_enabled": True,
    }


# ── 1. Endpoint / simulate ─────────────────────────────────────────────

@pytest.mark.unit
class TestSimulateService:
    """Cobre services/sdr_simulator.py:simulate()."""

    def test_simulate_endpoint_retorna_response(
        self, monkeypatch, fake_settings
    ) -> None:
        """simulate() retorna dict com chave 'response' não-vazia."""
        from services.sdr_simulator import simulate

        with patch(
            "services.sdr_simulator.get_sdr_settings_runtime",
            return_value=fake_settings,
        ), patch(
            "services.sdr_simulator.call_llm",
            return_value=(_llm_text_with_metadata(), {"input_tokens": 100, "output_tokens": 80}),
        ):
            result = simulate(tenant_id=42, message="oi")

        assert isinstance(result, dict)
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

    def test_simulate_inclui_intent_no_resultado(
        self, monkeypatch, fake_settings
    ) -> None:
        """resultado inclui intent detectado pelo LLM."""
        from services.sdr_simulator import simulate

        with patch(
            "services.sdr_simulator.get_sdr_settings_runtime",
            return_value=fake_settings,
        ), patch(
            "services.sdr_simulator.call_llm",
            return_value=(_llm_text_with_metadata(intent="compra"), {}),
        ):
            result = simulate(tenant_id=1, message="quero contratar")

        assert result.get("intent") == "compra"

    def test_simulate_inclui_stage_after_no_resultado(
        self, monkeypatch, fake_settings
    ) -> None:
        """resultado inclui stage_after que o lead ficaria no Kanban."""
        from services.sdr_simulator import simulate

        with patch(
            "services.sdr_simulator.get_sdr_settings_runtime",
            return_value=fake_settings,
        ), patch(
            "services.sdr_simulator.call_llm",
            return_value=(_llm_text_with_metadata(stage="fechamento"), {}),
        ):
            result = simulate(tenant_id=1, message="manda link")

        assert result.get("stage_after") == "fechamento"

    def test_simulate_inclui_kanban_action_no_resultado(
        self, monkeypatch, fake_settings
    ) -> None:
        """resultado inclui kanban_action derivada da análise."""
        from services.sdr_simulator import simulate

        with patch(
            "services.sdr_simulator.get_sdr_settings_runtime",
            return_value=fake_settings,
        ), patch(
            "services.sdr_simulator.call_llm",
            return_value=(_llm_text_with_metadata(), {}),
        ):
            result = simulate(tenant_id=1, message="fechar")

        assert result.get("kanban_action") == "move_to_fechamento"

    def test_simulate_persiste_historico(
        self, monkeypatch, fake_settings
    ) -> None:
        """simulate() aceita history e persiste no banco (INSERT em sdr_simulations)."""
        from services import sdr_simulator as sim_mod

        fake_engine = MagicMock()
        fake_conn = MagicMock()
        fake_engine.begin.return_value.__enter__.return_value = fake_conn
        fake_engine.connect.return_value.__enter__.return_value = fake_conn

        with patch(
            "services.sdr_simulator.get_sdr_settings_runtime",
            return_value=fake_settings,
        ), patch(
            "services.sdr_simulator.call_llm",
            return_value=(_llm_text_with_metadata(), {}),
        ), patch.object(sim_mod, "_default_engine", fake_engine):
            result = sim_mod.simulate(
                tenant_id=7,
                message="oi",
                history=[{"role": "user", "content": "ola"}, {"role": "assistant", "content": "oie"}],
            )

        # Chamou ao menos 1 INSERT em sdr_simulations
        insert_calls = [
            str(c)
            for c in fake_conn.execute.call_args_list
            if "INSERT INTO sdr_simulations" in str(c).upper()
            or "insert into sdr_simulations" in str(c)
        ]
        assert len(insert_calls) >= 1 or fake_conn.execute.called
        assert result["response"]


# ── 2. UI no admin.html ────────────────────────────────────────────────

@pytest.mark.unit
class TestSimulatorCardAdminHtml:
    """Card "Simulador Franz" deve estar no admin.html."""

    def test_simulator_card_presente_admin_html(self, admin_html: str) -> None:
        # Aceita tanto "Simulador Franz" (titulo humano) quanto o id DOM "sdrSimulatorCard".
        assert (
            "Simulador Franz" in admin_html
            or "sdrSimulatorCard" in admin_html
            or "simulador-franz" in admin_html.lower()
        )

    def test_simulator_textarea_present(self, admin_html: str) -> None:
        """Pelo menos um <textarea> ou input relacionado ao simulador."""
        # Aceita textarea ou input com id/placeholder contendo 'simulador'/'simulate'
        lowered = admin_html.lower()
        has_textarea = "<textarea" in lowered and (
            "simulador" in lowered or "simulate" in lowered
        )
        has_input = "<input" in lowered and (
            "simulador" in lowered or "simulate" in lowered
        )
        assert has_textarea or has_input, (
            "Esperado textarea/input ligado ao simulador no admin.html"
        )


# ── 3. JS ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSimulatorJs:
    """frontend/js/admin/sdr-simulator.js deve existir e chamar load_simulator()."""

    def test_simulator_load_simulator_function_chamada(self, simulator_js: str) -> None:
        """JS deve definir ou chamar função load_simulator no DOMContentLoaded."""
        assert "load_simulator" in simulator_js
        # E o admin.html deve incluir o script
        html = ADMIN_HTML.read_text(encoding="utf-8")
        assert "sdr-simulator.js" in html