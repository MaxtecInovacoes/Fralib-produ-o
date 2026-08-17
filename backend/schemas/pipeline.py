from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PipelineStartRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    segmento: str = Field(min_length=1)
    cidade: str = Field(min_length=1)
    quantidade: int = Field(default=1, ge=1, le=10)
    pipeline_id: str | None = None

    @field_validator("segmento", "cidade", "pipeline_id", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class PipelineActionResponse(BaseModel):
    ok: bool = True
    mensagem: str


class ArchiveAllResponse(BaseModel):
    ok: bool = True
    mensagem: str
    total_arquivados: int | None = None
