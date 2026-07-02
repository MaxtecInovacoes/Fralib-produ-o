"""Tests for Alavanca A+D: motion_intensity boost logic em vite_visual_lanes.

Validates:
  - Wellness lanes (health-trust, botanical-editorial, etc.) respond to
    prompt_priority boosts: trust -> visible, presence -> sharp.
  - Tier multiplier (ELITE/PREMIUM) escalona motion em todas lanes.
  - Defaults sao estaveis quando nao ha sinais (fallback).
  - resolve_visual_lane propaga prompt_priority e tier ate attitude.
"""
from __future__ import annotations

import pytest

from backend.services.vite_visual_lanes import (
    _lane_attitude_with_boosts,
    resolve_visual_lane,
)


class TestWellnessLaneBoosts:
    """Alavanca A+D: wellness lanes reagem a prompt_priority."""

    @pytest.mark.parametrize("lane_id", [
        "health-trust",
        "botanical-editorial",
        "clinical-soft",
        "coastal-light",
        "clinic-ivory",
        "rose-clay",
        "editorial-light",
    ])
    def test_wellness_default_motion_minimal(self, lane_id: str) -> None:
        """Wellness lane sem boost fica em motion_intensity minimal."""
        result = _lane_attitude_with_boosts(lane_id)
        assert result["motion_intensity"] == "minimal"

    @pytest.mark.parametrize("lane_id", [
        "health-trust",
        "botanical-editorial",
        "clinical-soft",
    ])
    def test_wellness_trust_boost_motion_visible(self, lane_id: str) -> None:
        """Wellness + prompt_priority=trust: minimal -> visible."""
        result = _lane_attitude_with_boosts(lane_id, prompt_priority="trust")
        assert result["motion_intensity"] == "visible"

    @pytest.mark.parametrize("lane_id", [
        "health-trust",
        "botanical-editorial",
    ])
    def test_wellness_presence_boost_motion_sharp(self, lane_id: str) -> None:
        """Wellness + prompt_priority=presence: minimal -> sharp."""
        result = _lane_attitude_with_boosts(lane_id, prompt_priority="presence")
        assert result["motion_intensity"] == "sharp"

    def test_wellness_case_insensitive_priority(self) -> None:
        """prompt_priority eh case-insensitive."""
        result = _lane_attitude_with_boosts("health-trust", prompt_priority="TRUST")
        assert result["motion_intensity"] == "visible"

    def test_non_wellness_lane_ignores_priority(self) -> None:
        """Lanes nao-wellness ignoram prompt_priority (mantem default)."""
        result = _lane_attitude_with_boosts("iron-pulse", prompt_priority="trust")
        assert result["motion_intensity"] == "sharp"  # default do iron-pulse

    def test_wellness_no_priority_motion_minimal(self) -> None:
        """Wellness lane com prompt_priority=None fica em minimal."""
        result = _lane_attitude_with_boosts("health-trust", prompt_priority=None)
        assert result["motion_intensity"] == "minimal"


class TestTierMultiplier:
    """Tier multiplier escala motion em todas lanes."""

    @pytest.mark.parametrize("tier", ["ELITE", "PREMIUM"])
    def test_elite_premium_boosts_minimal_to_visible(self, tier: str) -> None:
        """ELITE/PREMIUM em lane com motion=minimal sobe para visible."""
        result = _lane_attitude_with_boosts("health-trust", tier=tier)
        assert result["motion_intensity"] == "visible"

    def test_tier_case_insensitive(self) -> None:
        """Tier eh case-insensitive."""
        result = _lane_attitude_with_boosts("health-trust", tier="premium")
        assert result["motion_intensity"] == "visible"

    def test_tier_standard_no_boost(self) -> None:
        """STANDARD tier nao aplica boost."""
        result = _lane_attitude_with_boosts("health-trust", tier="STANDARD")
        assert result["motion_intensity"] == "minimal"

    def test_tier_empty_no_boost(self) -> None:
        """tier=None/'' nao aplica boost."""
        for tier_val in (None, ""):
            result = _lane_attitude_with_boosts("health-trust", tier=tier_val)
            assert result["motion_intensity"] == "minimal"


class TestResolveVisualLanePropagation:
    """resolve_visual_lane propaga prompt_priority e tier para attitude."""

    def test_resolve_with_priority_affects_motion(self) -> None:
        """resolve_visual_lane com prompt_priority altera motion_intensity."""
        lane = resolve_visual_lane(
            segment="nutricionista",
            visual_lane="health-trust",
            prompt_priority="trust",
        )
        blocks = lane.get("blocks", {})
        assert blocks.get("motion_intensity") == "visible"

    def test_resolve_with_tier_affects_motion(self) -> None:
        """resolve_visual_lane com tier altera motion_intensity."""
        lane = resolve_visual_lane(
            segment="nutricionista",
            visual_lane="health-trust",
            tier="ELITE",
        )
        blocks = lane.get("blocks", {})
        assert blocks.get("motion_intensity") == "visible"

    def test_resolve_without_signals_uses_minimal(self) -> None:
        """resolve_visual_lane sem sinais fica em motion=minimal."""
        lane = resolve_visual_lane(
            segment="nutricionista",
            visual_lane="health-trust",
        )
        blocks = lane.get("blocks", {})
        assert blocks.get("motion_intensity") == "minimal"


class TestFallbackStability:
    """Defaults sao estaveis — mesmo com sinais, estrutura nao quebra."""

    def test_unknown_lane_fallback(self) -> None:
        """Lane desconhecida retorna estrutura estavel."""
        result = _lane_attitude_with_boosts("xyz-unknow-lane")
        assert "motion_intensity" in result
        assert "aesthetic_mode" in result

    def test_empty_lane_id_fallback(self) -> None:
        """Lane vazia retorna estrutura estavel."""
        result = _lane_attitude_with_boosts("")
        assert result["motion_intensity"] == "composed"
        assert result["aesthetic_mode"] == "balanced"

    def test_all_lanes_return_all_keys(self) -> None:
        """Toda lane retorna todas as chaves de attitude."""
        EXPECTED_KEYS = {
            "aesthetic_mode",
            "spacing_density",
            "radius_mode",
            "container_strategy",
            "typography_scale",
            "heading_style",
            "surface_depth",
            "overlap_mode",
            "motion_intensity",
            "image_treatment",
        }
        for lane_id in ("health-trust", "iron-pulse", "graphite-core", ""):
            result = _lane_attitude_with_boosts(lane_id)
            assert EXPECTED_KEYS <= set(result), f"{lane_id} missing keys"
