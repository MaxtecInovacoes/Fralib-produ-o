"""
backend.agents - Agentes inteligentes do FraLib

Cada agente encapsula uma responsabilidade especifica do pipeline de geracao.
"""

# Trend Watcher - Monitor de tendencias de design web
from .trend_watcher import get_trends, clear_cache

# Benchmarker - Analisador de concorrencia
from .benchmarker import analisar_concorrencia, get_nichos_disponiveis, get_patterns_por_nicho

__all__ = [
    # Trend Watcher
    "get_trends",
    "clear_cache",
    # Benchmarker
    "analisar_concorrencia",
    "get_nichos_disponiveis",
    "get_patterns_por_nicho",
]