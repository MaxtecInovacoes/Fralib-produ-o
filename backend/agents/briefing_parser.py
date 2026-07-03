"""Briefing Parser com schema validation (Pydantic)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BriefingParseError(ValueError):
    def __init__(self, message: str, problems: list[str]):
        super().__init__(message)
        self.problems = problems


class BriefingBusiness(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    segment: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    whatsapp: str = Field(default="", max_length=50)
    phone: str = Field(default="", max_length=50)
    address: str = Field(default="", max_length=500)
    maps_url: str = Field(default="", max_length=2000)
    price_range: str = Field(default="", max_length=50)
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    total_avaliacoes: int = Field(default=0, ge=0)
    subnicho: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=2000)

    @field_validator("maps_url")
    @classmethod
    def _maps_url_must_be_http(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"maps_url deve comecar com http(s):// — recebeu: {v[:80]}")
        return v


class BriefingLead(BaseModel):
    business: BriefingBusiness
    tenant_id: Optional[str] = None
    tier: str = Field(default="STANDARD", max_length=20)
    source: str = Field(default="hunter", max_length=50)
    notes: str = Field(default="", max_length=2000)
    briefing_livre: str = Field(default="", max_length=10000)

    @field_validator("tier")
    @classmethod
    def _tier_known(cls, v: str) -> str:
        v = str(v or "").strip().upper()
        if v and v not in ("ELITE", "PREMIUM", "STANDARD"):
            raise ValueError(f"tier deve ser ELITE/PREMIUM/STANDARD (recebeu {v!r})")
        return v or "STANDARD"

    @model_validator(mode="after")
    def _at_least_one_contact(self) -> "BriefingLead":
        if not self.business.whatsapp and not self.business.phone:
            raise ValueError(
                "briefing precisa de pelo menos um contato (whatsapp ou phone)"
            )
        return self


def parse_briefing(payload: dict[str, Any]) -> BriefingLead:
    if not isinstance(payload, dict):
        raise BriefingParseError(
            f"briefing payload deve ser dict (recebeu {type(payload).__name__})",
            [f"payload type={type(payload).__name__}"],
        )

    problems: list[str] = []

    if "business" not in payload:
        problems.append("campo obrigatorio 'business' ausente")
        raise BriefingParseError(
            "briefing invalido: falta campo 'business'", problems,
        )

    business_raw = payload["business"]
    if not isinstance(business_raw, dict):
        raise BriefingParseError(
            f"briefing.business deve ser dict (recebeu {type(business_raw).__name__})",
            [f"type={type(business_raw).__name__}"],
        )

    try:
        business = BriefingBusiness(**business_raw)
    except Exception as exc:
        problems.extend(_extract_pydantic_errors(exc))
        raise BriefingParseError(
            f"briefing.business invalido: {'; '.join(problems)}", problems,
        ) from exc

    full_payload = {
        "business": business.model_dump(),
        "tenant_id": payload.get("tenant_id"),
        "tier": payload.get("tier", "STANDARD"),
        "source": payload.get("source", "hunter"),
        "notes": payload.get("notes", ""),
        "briefing_livre": payload.get("briefing_livre", ""),
    }

    try:
        return BriefingLead(**full_payload)
    except Exception as exc:
        problems.extend(_extract_pydantic_errors(exc))
        raise BriefingParseError(
            f"briefing invalido: {'; '.join(problems)}", problems,
        ) from exc


def _extract_pydantic_errors(exc: Exception) -> list[str]:
    problems: list[str] = []
    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return [str(exc)]
    try:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "")
            problems.append(f"{loc}: {msg}")
    except Exception:
        problems.append(str(exc))
    return problems or [str(exc)]


def briefing_is_valid(payload: dict[str, Any]) -> bool:
    try:
        parse_briefing(payload)
        return True
    except BriefingParseError:
        return False