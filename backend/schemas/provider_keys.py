from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class ProviderKeyCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    provider: str = Field(min_length=1)
    label: str = Field(min_length=1)
    apikey: str = Field(min_length=1)
    base_url: str | None = None

    @field_validator("provider", "label", "apikey", "base_url", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
        return value


class ProviderKeyUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    label: str | None = None
    apikey: str | None = None
    base_url: str | None = None
    enabled: bool | None = None

    @field_validator("label", "apikey", "base_url", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ProviderKeyTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    provider: str = Field(min_length=1)
    apikey: str = Field(min_length=1)
    base_url: str | None = None

    @field_validator("provider", "apikey", "base_url", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value
