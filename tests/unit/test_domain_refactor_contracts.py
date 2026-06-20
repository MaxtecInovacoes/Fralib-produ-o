import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "core"))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@example.com")


def test_plan_contract_keeps_agency_paid_unlimited():
    from backend.domain.plans import COOLDOWNS, PLAN_LIMITS, get_plan_spec, is_paid_plan

    agency = get_plan_spec("agency")

    assert agency.monthly_brl == 497
    assert agency.monthly_credits == 99999
    assert agency.cooldown_seconds == 0
    assert agency.has_sdr is True
    assert agency.is_unlimited is True
    assert is_paid_plan("agency") is True
    assert PLAN_LIMITS["agency"] == 99999
    assert COOLDOWNS["agency"] == 0


def test_access_control_reuses_single_superadmin_gate(monkeypatch):
    from backend.core import access_control

    monkeypatch.setattr(access_control, "is_superadmin", lambda email: email == "admin@example.com")

    assert access_control.require_superadmin({"email": "admin@example.com"})["email"] == "admin@example.com"
    with pytest.raises(HTTPException) as exc:
        access_control.require_superadmin({"email": "user@example.com"})
    assert exc.value.status_code == 403


def test_llm_pricing_matches_token_tracker_compatibility():
    from backend.agents.token_tracker import _calcular_custo
    from backend.domain.llm_pricing import estimate_llm_cost_usd

    usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "cache_creation": 100_000,
        "cache_read": 100_000,
    }

    assert estimate_llm_cost_usd("anthropic/claude-opus-4.8", usage) == _calcular_custo(
        "anthropic/claude-opus-4.8",
        usage,
    )
    assert round(_calcular_custo("claude-sonnet-4-6", usage), 3) == 18.405


def test_builder_contract_utils_normalize_common_prompt_values():
    from backend.agents.builder_contract_utils import (
        archetype_id_from_visual_dna,
        first_value,
        list_value,
    )

    data = {"title": "Clinica Local", "items": ["A", "B"], "visual_dna": {"archetype": {"id": "zen_pure"}}}

    assert first_value(data, "headline", "title") == "Clinica Local"
    assert list_value(data["items"]) == ["A", "B"]
    assert list_value("A") == []
    assert archetype_id_from_visual_dna(data["visual_dna"]) == "ZEN_PURE"


def test_phase6_contract_decides_video_only_when_context_and_asset_match():
    from backend.domain.phase6_contract import (
        phase6_image_asset,
        phase6_should_use_video_hero,
        phase6_video_asset,
        sanitize_keyword_term,
    )

    academia = {
        "segmento": "academia",
        "videos": [{"url": "https://videos.pexels.com/video.mp4", "poster": "https://img.example/poster.jpg"}],
    }
    nutri = {"segmento": "nutricionista clinica", "photos": ["https://img.example/nutri.jpg"]}

    assert phase6_should_use_video_hero(academia, require_video_asset=True) is True
    assert phase6_video_asset(academia)["url"].startswith("https://videos.pexels.com")
    assert phase6_should_use_video_hero(nutri, require_video_asset=True) is False
    assert phase6_image_asset(nutri) == "https://img.example/nutri.jpg"
    assert sanitize_keyword_term("keyword research: nutricionista") == ""


def test_frontend_auth_fetch_uses_central_auth_helper():
    auth_helper = (ROOT / "frontend" / "js" / "auth-helper.js").read_text(encoding="utf-8")
    admin_scripts = (ROOT / "frontend" / "partials" / "admin" / "_scripts.html").read_text(encoding="utf-8")
    dashboard_scripts_path = ROOT / "frontend" / "partials" / "dashboard" / "_scripts.html"
    dashboard_scripts = (
        dashboard_scripts_path
        if dashboard_scripts_path.exists()
        else ROOT / "frontend" / "partials" / "admin" / "_scripts.html"
    ).read_text(encoding="utf-8")
    superadmin = (ROOT / "frontend" / "superadmin.html").read_text(encoding="utf-8")

    assert "toApiUrl" in auth_helper
    assert "window.__fralibAuthExpired = true" in auth_helper
    assert "window.AuthHelper.authFetch(url, opts || {})" in admin_scripts
    assert "window.AuthHelper.authFetch(url, opts || {})" in dashboard_scripts
    assert "window.AuthHelper.authFetch(url, opts)" in superadmin
