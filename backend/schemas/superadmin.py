from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class SetPlanRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    plano: str = Field(validation_alias=AliasChoices("plano", "plan"))

    @field_validator("plano", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class SetCreditsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    creditos: int = Field(validation_alias=AliasChoices("creditos", "credits"), ge=0)


class ContactAliasModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    telefone: str | None = Field(
        default=None,
        validation_alias=AliasChoices("telefone", "phone"),
    )

    @field_validator("telefone", mode="before")
    @classmethod
    def _strip_phone(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value
