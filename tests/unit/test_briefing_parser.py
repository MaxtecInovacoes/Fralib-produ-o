"""Tests para BriefingParser — schema validation com Pydantic."""

from __future__ import annotations

import pytest

from backend.agents.briefing_parser import (
    parse_briefing,
    briefing_is_valid,
    BriefingParseError,
    BriefingBusiness,
    BriefingLead,
)


VALID_BRIEFING = {
    "business": {
        "name": "Academia Força",
        "segment": "academia",
        "city": "Curitiba",
        "whatsapp": "41999887766",
        "address": "Rua das Flores 123",
        "maps_url": "https://maps.google.com/?place=academia-forca",
        "rating": 4.7,
        "total_avaliacoes": 120,
    },
    "tenant_id": "tenant-1",
    "tier": "PREMIUM",
}


class TestParseValidBriefing:
    def test_valid_returns_briefing_lead(self) -> None:
        result = parse_briefing(VALID_BRIEFING)
        assert isinstance(result, BriefingLead)

    def test_valid_extracts_business_name(self) -> None:
        result = parse_briefing(VALID_BRIEFING)
        assert result.business.name == "Academia Força"

    def test_valid_extracts_city(self) -> None:
        result = parse_briefing(VALID_BRIEFING)
        assert result.business.city == "Curitiba"

    def test_valid_tier_uppercased(self) -> None:
        result = parse_briefing(VALID_BRIEFING)
        assert result.tier == "PREMIUM"

    def test_valid_lower_tier_uppercased(self) -> None:
        result = parse_briefing({**VALID_BRIEFING, "tier": "premium"})
        assert result.tier == "PREMIUM"

    def test_default_tier_standard(self) -> None:
        payload = dict(VALID_BRIEFING)
        payload.pop("tier", None)
        result = parse_briefing(payload)
        assert result.tier == "STANDARD"


class TestParseInvalidBriefing:
    def test_non_dict_payload_raises(self) -> None:
        with pytest.raises(BriefingParseError, match="dict"):
            parse_briefing("not a dict")  # type: ignore

    def test_missing_business_raises(self) -> None:
        with pytest.raises(BriefingParseError, match="business"):
            parse_briefing({"tenant_id": "x"})

    def test_empty_business_name_raises(self) -> None:
        payload = {
            "business": {
                "name": "", "segment": "academia", "city": "Curitiba",
                "whatsapp": "41999887766",
            }
        }
        with pytest.raises(BriefingParseError):
            parse_briefing(payload)

    def test_missing_city_raises(self) -> None:
        payload = {
            "business": {
                "name": "X", "segment": "academia", "city": "",
                "whatsapp": "41999887766",
            }
        }
        with pytest.raises(BriefingParseError):
            parse_briefing(payload)

    def test_no_contact_raises(self) -> None:
        payload = {
            "business": {
                "name": "X", "segment": "academia", "city": "Curitiba",
                "whatsapp": "", "phone": "",
            }
        }
        with pytest.raises(BriefingParseError, match="contato"):
            parse_briefing(payload)

    def test_invalid_maps_url_raises(self) -> None:
        payload = {
            "business": {
                "name": "X", "segment": "academia", "city": "Curitiba",
                "whatsapp": "41999887766", "maps_url": "not-a-url",
            }
        }
        with pytest.raises(BriefingParseError, match="maps_url"):
            parse_briefing(payload)

    def test_rating_too_high_raises(self) -> None:
        payload = {
            "business": {
                "name": "X", "segment": "academia", "city": "Curitiba",
                "whatsapp": "41999887766", "rating": 6.0,
            }
        }
        with pytest.raises(BriefingParseError, match="rating"):
            parse_briefing(payload)

    def test_invalid_tier_raises(self) -> None:
        payload = dict(VALID_BRIEFING)
        payload["tier"] = "BRONZE"
        with pytest.raises(BriefingParseError, match="tier"):
            parse_briefing(payload)


class TestBriefingIsValid:
    def test_valid_returns_true(self) -> None:
        assert briefing_is_valid(VALID_BRIEFING) is True

    def test_invalid_returns_false(self) -> None:
        assert briefing_is_valid({"business": {}}) is False

    def test_missing_returns_false(self) -> None:
        assert briefing_is_valid({}) is False


class TestBriefingParserNoFallback:
    def test_no_default_values_returned(self) -> None:
        with pytest.raises(BriefingParseError):
            parse_briefing({})

    def test_propagates_pydantic_error_chain(self) -> None:
        try:
            parse_briefing({"business": {"name": "", "segment": "x",
                                          "city": "y", "whatsapp": "41999"}})
        except BriefingParseError as exc:
            assert exc.__cause__ is not None

    def test_partial_briefing_rejected(self) -> None:
        partial = {"business": {"name": "X"}}
        with pytest.raises(BriefingParseError):
            parse_briefing(partial)