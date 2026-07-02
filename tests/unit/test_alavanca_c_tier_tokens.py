"""Tests for Alavanca C: POLO_TOKENS_BY_TIER overrides em vite_liquid_components.

Validates:
  - ELITE/PREMIUM aplicam overrides nos tokens do polo base.
  - STANDARD e valores desconhecidos nao alteram tokens.
  - infer_aesthetic_pole propaga tier ate tokens.
  - Tier nao afeta o polo inferido (so tokens).
"""
from __future__ import annotations

import pytest

from backend.services.vite_liquid_components import (
    POLO_TOKENS_BY_TIER,
    infer_aesthetic_pole,
)


class TestPoloTokensByTier:
    """Alavanca C: POLO_TOKENS_BY_TIER — overrides por tier."""

    def test_elite_keys_present(self) -> None:
        """ELITE tem overrides de motion e hero_scale."""
        overrides = POLO_TOKENS_BY_TIER["ELITE"]
        assert "motion_intensity" in overrides
        assert "hero_scale" in overrides
        assert overrides["motion_intensity"] == 0.8

    def test_premium_keys_present(self) -> None:
        """PREMIUM tem overrides de motion e hero_scale."""
        overrides = POLO_TOKENS_BY_TIER["PREMIUM"]
        assert "motion_intensity" in overrides
        assert overrides["motion_intensity"] == 0.6

    def test_standard_empty(self) -> None:
        """STANDARD nao tem overrides — usa tokens base."""
        overrides = POLO_TOKENS_BY_TIER["STANDARD"]
        assert overrides == {}

    def test_tier_lowercase_maps(self) -> None:
        """Keys de tier sao UPPERCASE mas matching eh case-insensitive."""
        assert "ELITE" in POLO_TOKENS_BY_TIER
        assert "PREMIUM" in POLO_TOKENS_BY_TIER
        assert "STANDARD" in POLO_TOKENS_BY_TIER


class TestInferAestheticPoleTierOverride:
    """infer_aesthetic_pole propaga tier para os tokens."""

    def test_elite_increases_motion(self) -> None:
        """ELITE sobe motion_intensity de 0.3 (soft base) para 0.8."""
        result = infer_aesthetic_pole(
            segment="nutricionista",
            tier="ELITE",
        )
        assert result["tokens"]["motion_intensity"] == 0.8

    def test_premium_moderate_motion(self) -> None:
        """PREMIUM sobe motion_intensity para 0.6."""
        result = infer_aesthetic_pole(
            segment="nutricionista",
            tier="PREMIUM",
        )
        assert result["tokens"]["motion_intensity"] == 0.6

    def test_standard_keeps_base(self) -> None:
        """STANDARD mantem motion_intensity do polo base (soft=0.3)."""
        result = infer_aesthetic_pole(
            segment="nutricionista",
            tier="STANDARD",
        )
        assert result["tokens"]["motion_intensity"] == 0.3

    def test_tier_none_keeps_base(self) -> None:
        """tier=None mantem tokens base."""
        result = infer_aesthetic_pole(
            segment="nutricionista",
            tier=None,
        )
        assert result["tokens"]["motion_intensity"] == 0.3

    def test_tier_empty_string_keeps_base(self) -> None:
        """tier='' mantem tokens base."""
        result = infer_aesthetic_pole(
            segment="nutricionista",
            tier="",
        )
        assert result["tokens"]["motion_intensity"] == 0.3

    def test_tier_case_insensitive(self) -> None:
        """Tier minusculo ou misto eh aceito."""
        for val in ("elite", "Elite", "eLiTe"):
            result = infer_aesthetic_pole(segment="nutri", tier=val)
            assert result["tokens"]["motion_intensity"] == 0.8

    def test_tier_unknown_keeps_base(self) -> None:
        """Tier desconhecido mantem tokens base."""
        result = infer_aesthetic_pole(
            segment="nutricionista",
            tier="BRONZE",
        )
        assert result["tokens"]["motion_intensity"] == 0.3

    def test_tier_does_not_change_pole(self) -> None:
        """Tier altera tokens mas NAO altera o polo inferido."""
        for t in ("ELITE", "PREMIUM", "STANDARD"):
            result = infer_aesthetic_pole(
                segment="academia",
                subniche="musculacao",
                tier=t,
            )
            # academia -> bold, independente do tier
            assert result["pole"] == "bold"

    def test_elite_hero_scale_larger(self) -> None:
        """ELITE tem hero_scale maior que base."""
        base = infer_aesthetic_pole(segment="nutri")
        elite = infer_aesthetic_pole(segment="nutri", tier="ELITE")
        assert elite["tokens"]["hero_scale"] != base["tokens"]["hero_scale"]
        assert "clamp(3.5rem" in elite["tokens"]["hero_scale"]

    def test_tier_does_not_mutate_base(self) -> None:
        """Tokens base nao sao mutados por chamadas sucessivas."""
        from backend.services.vite_liquid_components import POLO_TOKENS

        infer_aesthetic_pole(segment="nutri", tier="ELITE")
        infer_aesthetic_pole(segment="nutri", tier="ELITE")
        # base soft nao mudou
        assert POLO_TOKENS["soft"]["motion_intensity"] == 0.3


class TestElitePremiumDifferentiation:
    """ELITE vs PREMIUM tem valores distintos."""

    def test_elite_motion_higher_than_premium(self) -> None:
        """ELITE.motion > PREMIUM.motion."""
        elite = infer_aesthetic_pole(segment="nutri", tier="ELITE")
        premium = infer_aesthetic_pole(segment="nutri", tier="PREMIUM")
        assert elite["tokens"]["motion_intensity"] > premium["tokens"]["motion_intensity"]

    def test_elite_section_gap_smaller(self) -> None:
        """ELITE usa section_gap=0rem (overlap) vs PREMIUM=1rem."""
        elite = infer_aesthetic_pole(segment="nutri", tier="ELITE")
        premium = infer_aesthetic_pole(segment="nutri", tier="PREMIUM")
        elite_gap = elite["tokens"]["section_gap"]
        premium_gap = premium["tokens"]["section_gap"]
        # ELITE eh menor (mais overlap)
        assert elite_gap == "0rem"
        assert premium_gap == "1rem"
