import os
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
for path in (
    ROOT / "backend",
    ROOT / "backend" / "agents",
    ROOT / "backend" / "core",
    ROOT / "backend" / "services",
):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

os.environ.setdefault("DATABASE_URL", "sqlite:///C:/tmp/fralib_agent_config_unit.db")
os.environ.setdefault("JWT_SECRET_KEY", "unit-test-secret-key-for-provider-lock")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@example.com")

import agents.llm_direct as llm_direct
from endpoints import agent_config_endpoints


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        self.headers = {}


class FakeIAManager:
    def __init__(self):
        self.alerts = []
        self.failures = []

    def mark_failure(self, key_id, error, cooldown_seconds=15):
        self.failures.append((key_id, error, cooldown_seconds))

    def raise_alert(self, tipo, key_id, mensagem, lead_id=None, user_id=None):
        self.alerts.append(
            {
                "tipo": tipo,
                "key_id": key_id,
                "mensagem": mensagem,
                "lead_id": lead_id,
                "user_id": user_id,
            }
        )


def _install_fake_ia(monkeypatch):
    fake = FakeIAManager()
    monkeypatch.setitem(sys.modules, "ia_manager", fake)
    return fake


def test_builder_router_failure_creates_provider_alert(monkeypatch):
    fake_ia = _install_fake_ia(monkeypatch)
    llm_direct.set_current_user_id(2)
    fake_router = types.ModuleType("services.llm_router")

    class ProviderError(RuntimeError):
        pass

    err = ProviderError("402 Client Error")
    err.response = FakeResponse(402, "Payment Required: saldo insuficiente")

    def fake_call_llm(**kwargs):
        raise err

    fake_router.call_llm = fake_call_llm
    fake_services = types.ModuleType("services")
    fake_services.__path__ = []
    monkeypatch.setitem(sys.modules, "services", fake_services)
    monkeypatch.setitem(sys.modules, "services.llm_router", fake_router)
    monkeypatch.setattr(
        llm_direct,
        "_load_agent_configs",
        lambda: {
            "builder_renderer": {
                "provider": "custom",
                "model_id": "deepseek-v4-flash",
                "temperature": 0.55,
                "max_tokens": 16000,
            }
        },
    )
    with pytest.raises(ProviderError):
        llm_direct.call_claude(
            "system",
            "user",
            agent_name="builder_renderer",
            respect_agent_config=True,
        )
    llm_direct.set_current_user_id(None)

    assert fake_ia.failures == []
    assert fake_ia.alerts
    alert = fake_ia.alerts[0]
    assert alert["tipo"] == "test_failed"
    assert alert["key_id"] is None
    assert alert["user_id"] == 2
    assert "builder_renderer" in alert["mensagem"]
    assert "custom/deepseek-v4-flash" in alert["mensagem"]
    assert "HTTP 402" in alert["mensagem"]


def test_builder_provider_lock_forces_aibee_by_default(monkeypatch):
    config = {
        "provider": "openrouter",
        "model_id": "anthropic/claude-sonnet-4.5",
        "fallback_provider": "openrouter",
        "fallback_model_id": "anthropic/claude-opus-4.8",
        "temperature": 0.55,
        "max_tokens": 16000,
    }

    locked = llm_direct.llm_config._enforce_builder_aibee_lock("builder_renderer", config)

    assert locked is not config
    assert config["provider"] == "openrouter"
    assert locked["provider"] == "anthropic"
    assert locked["model_id"] == llm_direct.llm_config.BUILDER_AIBEE_MODEL_ID
    assert locked["fallback_provider"] is None
    assert locked["fallback_model_id"] is None
    assert locked["max_tokens"] == 16000


def test_builder_provider_lock_rejects_openrouter_style_model(monkeypatch):
    locked = llm_direct.llm_config._enforce_builder_aibee_lock(
        "builder_renderer",
        {"provider": "anthropic", "model_id": "anthropic/claude-sonnet-4.5"},
    )

    assert locked["provider"] == "anthropic"
    assert locked["model_id"] == llm_direct.llm_config.BUILDER_AIBEE_MODEL_ID


def test_agent_config_endpoint_blocks_silent_builder_provider_change():
    with pytest.raises(Exception) as exc_info:
        agent_config_endpoints._guard_builder_provider_policy(
            "builder_renderer",
            {"provider": "openrouter", "model_id": "anthropic/claude-sonnet-4.5"},
            {"provider": "openrouter", "model_id": "anthropic/claude-sonnet-4.5"},
        )

    assert getattr(exc_info.value, "status_code", None) == 400
    assert "LiteLLM FraLib" in getattr(exc_info.value, "detail", "")


def test_agent_config_endpoint_rejects_explicit_builder_provider_override():
    with pytest.raises(Exception) as exc_info:
        agent_config_endpoints._guard_builder_provider_policy(
            "builder_renderer",
            {
                "provider": "openrouter",
                "confirm_non_aibee_builder_provider": agent_config_endpoints.BUILDER_NON_AIBEE_OVERRIDE_TOKEN,
            },
            {"provider": "openrouter"},
        )

    assert getattr(exc_info.value, "status_code", None) == 400


def test_agent_config_endpoint_accepts_proxy_alias_models():
    agent_config_endpoints._guard_agent_proxy_policy(
        {"provider": "anthropic", "model_id": "claude-sonnet-4-6"}
    )
    agent_config_endpoints._guard_agent_proxy_policy(
        {"provider": "anthropic", "model_id": "claude-haiku-4-5"}
    )

    with pytest.raises(Exception) as exc_info:
        agent_config_endpoints._guard_agent_proxy_policy(
            {"provider": "anthropic", "model_id": "anthropic/claude-sonnet-4.5"}
        )

    assert getattr(exc_info.value, "status_code", None) == 400


def test_aibee_env_auth_failure_marks_env_fallback_and_alerts(monkeypatch):
    fake_ia = _install_fake_ia(monkeypatch)

    class AuthError(RuntimeError):
        pass

    err = AuthError("401 Invalid API key")
    err.response = FakeResponse(401, "Invalid API key")

    llm_direct._alert_llm_provider_failure(
        "anthropic",
        "deepseek-v4-flash",
        err,
        key_id=None,
        source="builder_renderer",
        mark_env_fallback=True,
    )

    assert fake_ia.failures == [(None, "401 provider failure", 600)]
    assert fake_ia.alerts
    alert = fake_ia.alerts[0]
    assert alert["tipo"] == "key_invalid"
    assert "LiteLLM FraLib" in alert["mensagem"]
    assert "HTTP 401" in alert["mensagem"]


def test_admin_lead_supply_reads_provider_alerts():
    source = (ROOT / "frontend" / "partials" / "admin" / "_scripts.html").read_text(
        encoding="utf-8"
    )

    assert "/api/provider-alerts?only_unread=true&limit=10" in source
    assert "_leadSupplyProviderAlertRelevant" in source
    assert "Erro de IA/Builder" in source


def test_agent_router_prefers_cheaper_models_for_small_tasks():
    from agent_router import AgentRouter

    router = AgentRouter("simples")

    assert router.get_model("agente_nicho") == "haiku"
    assert router.get_model("agente_variacao") == "haiku"
    assert router.get_model("franz") == "haiku"
    assert router.get_model("builder_renderer") == "sonnet"
