"""Leads CRUD models and helpers."""

from typing import Optional

from pydantic import BaseModel


class EditarSiteRequest(BaseModel):
    prompt: str


class LeadManualRequest(BaseModel):
    nome: str
    telefone: Optional[str] = None
    whatsapp: Optional[str] = None
    nicho: str
    cidade: str
    briefing: Optional[str] = None
    refs_visuais: Optional[str] = None  # Sprint 14.x: referências visuais do usuário
    score: Optional[int] = 80


class CamposLeadRequest(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    segmento: Optional[str] = None
    cidade: Optional[str] = None
    observacao: Optional[str] = None
    sdr_stage: Optional[str] = None
    status: Optional[str] = None


class FeedbackRequest(BaseModel):
    resultado: str  # 'convertido' ou 'perdido'
    observacao: str = ""
