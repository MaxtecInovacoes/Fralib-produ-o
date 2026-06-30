"""Exceções customizadas do pipeline Fraub.

Todas as exceções aqui são de fail-fast: quando lançada, o pipeline
para imediatamente e loga erro detalhado. NÃO usar para fallbacks.
"""

from typing import Any


class PipelineError(Exception):
    """Base exception para todos os erros de pipeline."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.__class__.__name__}: {super().__str__()}" + (f" [{ctx}]" if ctx else "")


# ─── Fase 7: Variação Estrutural ────────────────────────────────────────────


class SubnichoNaoMapeadoError(PipelineError):
    """Lançada quando subnicho não está em SUB_NICHO_TEMPLATES e LLM falhou.

    NÃO é um fallback - é um erro que impede geração de site idêntico.
    """

    pass


class VariationSeedError(PipelineError):
    """Lançada quando VariationSeed não pode ser gerado."""

    pass


# ─── Fase 6: JINA Intelligence ───────────────────────────────────────────────


class JinaIntelligenceError(PipelineError):
    """Lançada quando JINA falha e não retorna dados."""

    pass


# ─── Fase 4-5: CAIO / Qualificação ─────────────────────────────────────────


class QualificacaoError(PipelineError):
    """Lançada quando CAIO falha na qualificação do lead."""

    pass


# ─── Fase 8-9: Designer / Arquiteto ─────────────────────────────────────────


class DesignDirectionError(PipelineError):
    """Lançada quando não consegue determinar direção visual."""

    pass


class DesignSystemNotFoundError(PipelineError):
    """Lançada quando design system slug não é encontrado."""

    pass


# ─── Fase 9-10: Builder / Copy ──────────────────────────────────────────────


class CopyGenerationError(PipelineError):
    """Lançada quando geração de copy falha após retry."""

    pass


class EstruturaInvalidaError(PipelineError):
    """Lançada quando estrutura não pode ser gerada após retry."""

    pass


# ─── Fase 10-11: HTML / Publication ─────────────────────────────────────────


class ImageNotAvailableError(PipelineError):
    """Lançada quando imagem não pode ser obtida para o nicho."""

    pass


class HTMLGenerationError(PipelineError):
    """Lançada quando geração de HTML falha."""

    pass


# ─── LLM ────────────────────────────────────────────────────────────────────


class LLMError(PipelineError):
    """Lançada quando todas as tentativas de LLM falham."""

    pass


class LLMTimeoutError(LLMError):
    """Lançada quando LLM timeout após retry."""

    pass


class LLMConnectionError(LLMError):
    """Lançada quando não consegue conectar ao LLM após retry."""

    pass


# ─── Validação ───────────────────────────────────────────────────────────────


class RequiredDataMissingError(PipelineError):
    """Lançada quando dado obrigatório está ausente."""

    pass
