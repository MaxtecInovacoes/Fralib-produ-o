"""Compatibility wrapper for the legacy PRD validation import path."""

from backend.agents.validation_layer import (  # noqa: F401
    CORES_PROIBIDAS,
    calcular_score_validacao,
    gerar_prompt_retry,
    validar_html,
    validar_prd,
)
