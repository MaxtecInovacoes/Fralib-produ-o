"""
Pipeline Fases - Módulos extraídos do monolito pipeline_orchestrator_service.py
遵循 ECC: Cada fase é um módulo independente com responsabilidade única.
"""

from backend.services.pipeline_fases.fase_08_arquiteto import executar_fase_8

__all__ = [
    "executar_fase_8",
]
