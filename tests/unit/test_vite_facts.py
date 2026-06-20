"""Tests for vite_facts module."""

import pytest


class TestFactsBusiness:
    """Test business facts extraction."""

    def test_facts_business_extracts_name(self):
        """Test _facts_business extracts name correctly."""
        from backend.services.vite_facts import _facts_business

        facts = {
            "business": {
                "name": "Academia Forte",
                "segment": "academia",
                "tagline": "Musculacao de verdade",
            }
        }

        result = _facts_business(facts)
        assert result["name"] == "Academia Forte"
        assert result["segment"] == "academia"
        assert result["tagline"] == "Musculacao de verdade"

    def test_facts_business_handles_missing(self):
        """Test _facts_business handles missing business dict."""
        from backend.services.vite_facts import _facts_business

        result = _facts_business({})
        assert result["name"] == "Business"
        assert result["segment"] == ""


class TestFactsThemeColor:
    """Test theme color extraction."""

    def test_facts_theme_color_returns_hex(self):
        """Test _facts_theme_color returns hex color."""
        from backend.services.vite_facts import _facts_theme_color

        facts = {"business": {"name": "Test"}}
        result = _facts_theme_color(facts)

        assert result.startswith("#")
        assert len(result) == 7

    def test_facts_theme_color_respects_explicit(self):
        """Test _facts_theme_color uses explicit color if set."""
        from backend.services.vite_facts import _facts_theme_color

        facts = {"business": {}, "theme_color": "#FF5500"}
        result = _facts_theme_color(facts)

        assert result == "#FF5500"


class TestFactsMetaDescription:
    """Test meta description generation."""

    def test_facts_meta_description_truncates_long(self):
        """Test _facts_meta_description truncates long descriptions."""
        from backend.services.vite_facts import _facts_meta_description

        facts = {
            "business": {
                "name": "A" * 200,
                "segment": "test",
            },
            "city": "Sao Paulo",
            "services": ["Service A", "Service B"],
        }

        result = _facts_meta_description(facts)
        assert len(result) <= 160

    def test_facts_meta_description_uses_business_name(self):
        """Test _facts_meta_description includes business name."""
        from backend.services.vite_facts import _facts_meta_description

        facts = {
            "business": {"name": "Meu Negocio"},
            "city": "Rio",
            "services": [],
        }

        result = _facts_meta_description(facts)
        assert "Meu Negocio" in result


class TestFactsJsonLd:
    """Test JSON-LD generation."""

    def test_facts_json_ld_returns_valid_json(self):
        """Test _facts_json_ld returns valid JSON string."""
        import json
        from backend.services.vite_facts import _facts_json_ld

        facts = {
            "business": {"name": "Test", "description": "Desc"},
            "city": "City",
            "phone": "123",
            "address": "Street 1",
        }

        result = _facts_json_ld(facts)
        parsed = json.loads(result)

        assert parsed["@type"] == "LocalBusiness"
        assert parsed["name"] == "Test"


class TestSegmentKey:
    """Test segment key detection."""

    def test_segment_key_for_academia(self):
        """Test segment key detection for academia."""
        from backend.services.vite_facts import _segment_key_for_business

        business = {"name": "Academia ABC", "segment": "fitness", "services": ["musculacao"]}
        result = _segment_key_for_business(business)

        assert result == "academia"

    def test_segment_key_for_restaurante(self):
        """Test segment key detection for restaurante."""
        from backend.services.vite_facts import _segment_key_for_business

        business = {"name": "Restaurante XYZ", "segment": "", "services": ["restaurante"]}
        result = _segment_key_for_business(business)

        assert result == "restaurante"

    def test_segment_key_returns_none_for_unknown(self):
        """Test segment key returns None for unknown segment."""
        from backend.services.vite_facts import _segment_key_for_business

        business = {"name": "Unknown", "segment": "", "services": []}
        result = _segment_key_for_business(business)

        assert result is None
