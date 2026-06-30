import os
import sys
from datetime import datetime


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from services.sdr_settings import (  # noqa: E402
    build_sdr_system_prompt,
    daily_limit_per_lead,
    human_pause_seconds,
    is_within_outbound_schedule,
    normalize_sdr_settings,
    outbound_schedule_from_settings,
    reply_cooldown_seconds,
)


def test_sdr_settings_keep_native_defaults_safe():
    cfg = normalize_sdr_settings({})

    assert cfg["agent_name"] == "Franz"
    assert cfg["response_mode"] == "always"
    assert cfg["outbound_schedule"]["hora_inicio"] == 8
    assert cfg["outbound_schedule"]["hora_fim"] == 21
    assert cfg["outbound_schedule"]["dias_bloqueados"] == [6]
    assert reply_cooldown_seconds(cfg) == 30
    assert daily_limit_per_lead(cfg) == 50
    assert human_pause_seconds(cfg) == 300


def test_sdr_settings_normalize_untrusted_tenant_input():
    cfg = normalize_sdr_settings(
        {
            "agent_name": "Caio" * 50,
            "response_mode": "hack",
            "outbound_schedule": {
                "mode": "custom",
                "hora_inicio": 23,
                "hora_fim": 1,
                "dias_bloqueados": [6, "x", 9, 5, 5],
            },
            "limits": {
                "reply_cooldown_seconds": 0,
                "daily_limit_per_lead": 9999,
                "human_pause_seconds": 10,
            },
        }
    )

    assert len(cfg["agent_name"]) <= 40
    assert cfg["response_mode"] == "always"
    assert cfg["outbound_schedule"]["hora_inicio"] == 8
    assert cfg["outbound_schedule"]["hora_fim"] == 21
    assert cfg["outbound_schedule"]["dias_bloqueados"] == [6, 5]
    assert reply_cooldown_seconds(cfg) == 15
    assert daily_limit_per_lead(cfg) == 200
    assert human_pause_seconds(cfg) == 60


def test_sdr_settings_24h_schedule_is_legacy_compatible():
    cfg = normalize_sdr_settings({"outbound_schedule": {"mode": "always"}})

    assert outbound_schedule_from_settings(cfg) == {
        "modo": "livre",
        "hora_inicio": 0,
        "hora_fim": 24,
        "dias_bloqueados": [],
    }


def test_sdr_schedule_blocks_configured_days_and_hours():
    cfg = normalize_sdr_settings(
        {
            "outbound_schedule": {
                "mode": "custom",
                "hora_inicio": 8,
                "hora_fim": 20,
                "dias_bloqueados": [6],
            }
        }
    )

    assert is_within_outbound_schedule(cfg, datetime(2026, 6, 1, 10, 0)) is True
    assert is_within_outbound_schedule(cfg, datetime(2026, 6, 1, 22, 0)) is False
    assert is_within_outbound_schedule(cfg, datetime(2026, 6, 7, 10, 0)) is False


def test_sdr_schedule_repairs_legacy_weekday_block_inversion():
    cfg = normalize_sdr_settings(
        {
            "outbound_schedule": {
                "mode": "custom",
                "hora_inicio": 8,
                "hora_fim": 18,
                "dias_bloqueados": [0, 1, 2, 3, 4],
            }
        }
    )

    assert cfg["outbound_schedule"]["dias_bloqueados"] == [6]
    assert is_within_outbound_schedule(cfg, datetime(2026, 6, 30, 16, 45)) is True


def test_sdr_prompt_customization_cannot_override_platform_guardrails():
    cfg = normalize_sdr_settings(
        {
            "agent_name": "Lucas",
            "objective": "qualify_only",
            "personality": "formal e objetivo",
            "custom_knowledge": "Nunca ofereca desconto. Chame humano se pedir contrato.",
        }
    )

    prompt = build_sdr_system_prompt("BASE NATIVA", cfg)

    assert "Nome publico do SDR: Lucas" in prompt
    assert "formal e objetivo" in prompt
    assert "Nunca ofereca desconto" in prompt
    assert "NUNCA libera spam" in prompt
    assert "Se a base propria conflitar com as regras nativas" in prompt
