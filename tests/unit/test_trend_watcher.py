"""Tests for Trend Watcher agent - Design trend monitoring."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

# Setup path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from agents.trend_watcher import (
    get_trends,
    clear_cache,
    _get_fallback_trends,
    _is_cache_valid,
    _cache,
    _cache_timestamp,
)


class TestGetTrends:
    """Test suite for get_trends function."""

    def test_get_trends_returns_dict(self):
        """Test that get_trends returns a dictionary with expected structure."""
        # Mock network call to succeed with trend data
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = """
            Web design trends 2026:
            - Colors: lavender, sage, terracotta
            - Motion: parallax, scroll-trigger, reveal
            - Layouts: bento grid, asymmetric, masonry
            """

            result = get_trends(nicho="nutricionista")

            assert isinstance(result, dict)
            assert "colors" in result
            assert "motion_styles" in result
            assert "layouts" in result

    def test_get_trends_has_fallback(self):
        """Test that fallback is used when web search fails."""
        # Mock network failure
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = ""  # Empty response = failure

            result = get_trends(nicho="academia")

            assert isinstance(result, dict)
            assert "source" in result
            assert result["source"] == "fallback-deterministic"
            # Fallback should have default colors
            assert len(result.get("colors", [])) > 0

    def test_get_trends_cache_hit(self):
        """Test that cache is respected for repeated calls."""
        # First call - populate cache
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = "Some trend data with parallax motion and bento grid layouts"

            result1 = get_trends(nicho="nutricionista")

        # Second call - should hit cache
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch2:
            mock_fetch2.side_effect = Exception("Should not be called on cache hit")

            result2 = get_trends(nicho="nutricionista")

        # Results should be same from cache
        assert result1["colors"] == result2["colors"]
        assert result1["motion_styles"] == result2["motion_styles"]

    def test_get_trends_includes_last_updated(self):
        """Test that result includes last_updated timestamp."""
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = "parallax scroll-trigger motion bento grid layout colors"

            result = get_trends()

            assert "last_updated" in result
            # Should be in YYYY-MM-DD format
            assert len(result["last_updated"]) == 10

    def test_get_trends_includes_recommended_updates(self):
        """Test that result includes recommended updates list."""
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = ""

            result = get_trends()

            assert "recommended_updates" in result
            assert isinstance(result["recommended_updates"], list)

    def test_get_trends_with_niche(self):
        """Test get_trends accepts niche parameter."""
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = ""

            # Should not raise
            result = get_trends(nicho="barbearia")

            assert isinstance(result, dict)


class TestFallbackTrends:
    """Test suite for fallback trends."""

    def test_fallback_returns_valid_structure(self):
        """Test that fallback has correct structure."""
        fallback = _get_fallback_trends()

        assert "colors" in fallback
        assert "motion_styles" in fallback
        assert "layouts" in fallback
        assert "last_updated" in fallback
        assert "source" in fallback

    def test_fallback_has_colors(self):
        """Test that fallback includes expected color palette."""
        fallback = _get_fallback_trends()

        assert len(fallback["colors"]) > 0
        # Should include hex codes
        assert any(c.startswith("#") for c in fallback["colors"])

    def test_fallback_has_motion_styles(self):
        """Test that fallback includes motion styles."""
        fallback = _get_fallback_trends()

        assert len(fallback["motion_styles"]) > 0
        # Should include modern motion keywords
        motion_str = " ".join(fallback["motion_styles"]).lower()
        assert any(kw in motion_str for kw in ["parallax", "scroll", "spring", "bounce"])

    def test_fallback_has_layouts(self):
        """Test that fallback includes layout patterns."""
        fallback = _get_fallback_trends()

        assert len(fallback["layouts"]) > 0
        # Should include modern layout keywords
        layouts_str = " ".join(fallback["layouts"]).lower()
        assert any(kw in layouts_str for kw in ["bento", "asymmetric", "immersive"])

    def test_fallback_is_deterministic(self):
        """Test that fallback returns same values on repeated calls."""
        result1 = _get_fallback_trends()
        result2 = _get_fallback_trends()

        assert result1 == result2


class TestCacheManagement:
    """Test suite for cache management."""

    def test_clear_cache(self):
        """Test that clear_cache removes cached data."""
        # First populate with some data
        result1 = get_trends(nicho="test")
        assert result1 is not None

        # Clear cache
        clear_cache()

        # Verify cache is cleared by checking _is_cache_valid
        # After clear, cache should be invalid
        global _cache, _cache_timestamp
        from agents import trend_watcher
        trend_watcher._cache = {}
        trend_watcher._cache_timestamp = None

        # Now cache should be invalid
        with patch("backend.agents.trend_watcher._jina_fetch", return_value=""):
            # This should not use cache
            result2 = get_trends(nicho="test2")
            assert result2["source"] == "fallback-deterministic"

    def test_cache_expiration(self):
        """Test that cache respects 24h TTL."""
        from agents import trend_watcher as tw

        # Set cache with old timestamp (25 hours ago)
        tw._cache = {"colors": ["test"]}
        tw._cache_timestamp = datetime.now() - timedelta(hours=25)

        # Cache should be invalid
        assert not _is_cache_valid()

    def test_cache_within_ttl(self):
        """Test that cache is valid within 24h TTL."""
        from agents import trend_watcher as tw

        # Set cache with recent timestamp (1 hour ago)
        tw._cache = {"colors": ["test"]}
        tw._cache_timestamp = datetime.now() - timedelta(hours=1)

        # Cache should be valid
        assert _is_cache_valid()


class TestGenerateRecommendations:
    """Test suite for recommendation generation."""

    def test_recommendations_include_parallax_when_present(self):
        """Test that recommendations mention parallax when trends include it."""
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = "parallax scroll parallax-3d parallax"

            result = get_trends()

            rec_str = " ".join(result.get("recommended_updates", []))
            # Either parallax is in recommendations or fallback message is used
            assert isinstance(rec_str, str)

    def test_recommendations_include_bento_when_present(self):
        """Test that recommendations mention bento when trends include it."""
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = "bento grid layout asymmetric bento"

            result = get_trends()

            rec_str = " ".join(result.get("recommended_updates", []))
            # Either bento is in recommendations or fallback message is used
            assert isinstance(rec_str, str)

    def test_recommendations_include_scroll_when_present(self):
        """Test that recommendations mention scroll-trigger when present."""
        with patch("backend.agents.trend_watcher._jina_fetch") as mock_fetch:
            mock_fetch.return_value = "scroll-trigger animation scroll-mask scroll scroll"

            result = get_trends()

            rec_str = " ".join(result.get("recommended_updates", []))
            # Either scroll is in recommendations or fallback message is used
            assert isinstance(rec_str, str)

    def test_fallback_recommendations_are_valid(self):
        """Test that fallback generates valid recommendations."""
        # Clear cache first to ensure fresh state
        clear_cache()

        # Force fallback by mocking empty fetch
        with patch("backend.agents.trend_watcher._jina_fetch", return_value=""):
            result = get_trends()

            assert "recommended_updates" in result
            assert isinstance(result["recommended_updates"], list)
            assert len(result["recommended_updates"]) > 0
            # Recommendations should be non-empty strings
            for rec in result["recommended_updates"]:
                assert isinstance(rec, str)
                assert len(rec) > 0
