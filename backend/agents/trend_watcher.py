"""
trend_watcher.py - Monitor de tendências de design web para updates em sites gerados.

Busca tendencias atuais de CSS, motion, layouts e retorna insights para manter
os sites do FraLib atualizados com o estado da arte em design web.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Queries para busca de tendencias
TREND_QUERIES = [
    "CSS Design Awards 2026 winners trends",
    "Awwwards site of the day 2026 features",
    "Tailwind CSS v4 best practices 2026",
    "GSAP ScrollTrigger latest animations 2026",
    "web design trends color palette 2026",
]

# Cache em memoria (24h)
_cache: dict[str, Any] = {}
_cache_timestamp: datetime | None = None
CACHE_DURATION_HOURS = 24


def _is_cache_valid() -> bool:
    """Verifica se o cache em memoria ainda e valido."""
    global _cache_timestamp
    if not _cache or _cache_timestamp is None:
        return False
    return datetime.now() - _cache_timestamp < timedelta(hours=CACHE_DURATION_HOURS)


def _jina_fetch(query: str, timeout: int = 15) -> str:
    """
    Busca texto via Jina AI Reader.
    Fallback retorna string vazia em caso de erro.
    """
    try:
        import requests
        from urllib.parse import quote

        url = f"https://r.jina.ai/https://www.google.com/search?q={quote(query)}"
        headers = {
            "X-Return-Format": "markdown",
            "X-Timeout": str(timeout),
        }
        jina_key = os.getenv("JINA_API_KEY", "")
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"

        resp = requests.get(url, headers=headers, timeout=timeout + 5)
        if resp.status_code == 200:
            return resp.text[:4000]
        logger.warning(f"[TrendWatcher] Jina retornou status {resp.status_code} para: {query}")
        return ""
    except Exception as e:
        logger.warning(f"[TrendWatcher] Jina erro em '{query}': {e}")
        return ""


def _extract_trends_from_text(text: str) -> dict[str, list[str]]:
    """
    Extrai tendencias do texto coletado.
    Por enquanto implementacao basica - pode ser melhorada com NLP.
    """
    text_lower = text.lower()

    trends = {
        "colors": [],
        "motion_styles": [],
        "layouts": [],
    }

    # Cores em alta 2026
    color_keywords = [
        "lavender", "sage", "terracotta", "ochre", "deep green", "burgundy",
        "electric blue", "coral", "cream", "charcoal", "mint", "rose gold",
        "#a855f7", "#8b5cf6", "#14b8a6", "#f59e0b", "#ef4444",
    ]
    for color in color_keywords:
        if color in text_lower:
            trends["colors"].append(color if color.startswith("#") else color.title())

    # Motion styles
    motion_keywords = [
        "parallax", "scroll-trigger", "morphing", "reveal", "fade-in",
        "slide-up", "stagger", "spring", "bounce", "elastic", "smooth scroll",
        "scroll-driven", "view transitions", "scroll-mask", "parallax-3d",
    ]
    for motion in motion_keywords:
        if motion in text_lower:
            trends["motion_styles"].append(motion.lower().replace("scroll-trigger", "scroll-trigger"))

    # Layouts
    layout_keywords = [
        "bento grid", "asymmetric", "masonry", "magazine", "split screen",
        "full-bleed", "hero video", "card-based", "layered", "immersive",
    ]
    for layout in layout_keywords:
        if layout in text_lower:
            trends["layouts"].append(layout)

    # Deduplicar e limitar
    trends["colors"] = list(dict.fromkeys(trends["colors"]))[:6]
    trends["motion_styles"] = list(dict.fromkeys(trends["motion_styles"]))[:6]
    trends["layouts"] = list(dict.fromkeys(trends["layouts"]))[:5]

    return trends


def _get_fallback_trends() -> dict[str, Any]:
    """
    Fallback deterministico baseado no estado atual do design web 2026.
    Usado quando web search falha ou em caso de erro.
    """
    return {
        "colors": [
            "#a855f7",  # Violet/Violet
            "#14b8a6",  # Teal
            "#f59e0b",  # Amber
            "#ec4899",  # Pink
            "#06b6d4",  # Cyan
            "#84cc16",  # Lime
        ],
        "motion_styles": [
            "parallax-3d",
            "scroll-trigger",
            "scroll-mask",
            "stagger-reveal",
            "spring-bounce",
            "view-transitions",
        ],
        "layouts": [
            "bento-grid",
            "asymmetric",
            "full-bleed-hero",
            "split-screen",
            "immersive",
        ],
        "last_updated": "2026-06-19",
        "source": "fallback-deterministic",
    }


def get_trends(nicho: str = "") -> dict[str, Any]:
    """
    Retorna tendencias atuais de design web.

    Args:
        nicho: Opcional. Nicho do cliente para tendencias customizadas.

    Returns:
        dict com:
            - colors: Lista de cores em alta
            - motion_styles: Lista de estilos de animacao
            - layouts: Lista de padroes de layout
            - last_updated: Data da ultima atualizacao (YYYY-MM-DD)
            - recommended_updates: Lista de updates recomendados

    Cache:
        - Em memoria por 24h
        - Proximo release: cache Redis/PostgreSQL para persistencia cross-request
    """
    global _cache, _cache_timestamp

    # Verificar cache
    if _is_cache_valid():
        logger.info("[TrendWatcher] Retornando dados do cache (24h)")
        return _cache

    logger.info("[TrendWatcher] Buscando tendencias atualizadas...")

    try:
        # Buscar tendencias de multiplas fontes
        all_text = ""
        for query in TREND_QUERIES:
            text = _jina_fetch(query)
            if text:
                all_text += text + "\n\n"

        # Extrair tendencias do texto coletado
        if all_text:
            trends = _extract_trends_from_text(all_text)

            # Se nao encontrou tendencias na busca, usar fallback deterministico
            has_trends = any([
                trends["colors"],
                trends["motion_styles"],
                trends["layouts"],
            ])

            if not has_trends:
                logger.warning("[TrendWatcher] Nenhuma tendencia extraida da busca, usando fallback")
                fallback = _get_fallback_trends()
                fallback["recommended_updates"] = _generate_recommendations(fallback)
                _cache = fallback
                _cache_timestamp = datetime.now()
                return fallback

            trends["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            trends["source"] = "web-search"
            trends["recommended_updates"] = _generate_recommendations(trends)

            # Atualizar cache
            _cache = trends
            _cache_timestamp = datetime.now()

            logger.info(
                f"[TrendWatcher] Tendencias atualizadas: "
                f"{len(trends['colors'])} cores, "
                f"{len(trends['motion_styles'])} motion, "
                f"{len(trends['layouts'])} layouts"
            )
            return trends

        # Se busca falhou, usar fallback
        logger.warning("[TrendWatcher] Web search retornou vazio, usando fallback")
        fallback = _get_fallback_trends()
        _cache = fallback
        _cache_timestamp = datetime.now()
        return fallback

    except Exception as e:
        logger.warning(f"[TrendWatcher] Erro ao buscar tendencias: {e}")
        fallback = _get_fallback_trends()
        _cache = fallback
        _cache_timestamp = datetime.now()
        return fallback


def _generate_recommendations(trends: dict[str, Any]) -> list[str]:
    """Gera recomendacoes de updates baseadas nas tendencias."""
    recommendations = []

    colors = trends.get("colors", [])
    motion = trends.get("motion_styles", [])
    layouts = trends.get("layouts", [])

    if colors:
        # Mostrar cor de forma amigavel
        sample_color = colors[0]
        recommendations.append(
            f"Considerar paleta com tons vibrantes como {sample_color} para destaque visual"
        )

    motion_str = " ".join(str(m) for m in motion)

    if "parallax" in motion_str.lower():
        recommendations.append(
            "Implementar parallax 3D sutil no hero para profundidade visual"
        )

    if "bento" in motion_str.lower() or "bento" in str(layouts).lower():
        recommendations.append(
            "Usar layout bento grid para organizar servicos com cards de tamanhos variados"
        )

    if "scroll-trigger" in motion_str.lower() or "scroll" in motion_str.lower():
        recommendations.append(
            "Adicionar animacoes scroll-triggered nos elementos abaixo da dobra"
        )

    if not recommendations:
        recommendations.append(
            "Revisar paleta de cores e adicionar micro-interacoes nos botoes"
        )

    return recommendations


def clear_cache() -> None:
    """Limpa o cache em memoria. Usado para forcar refresh."""
    global _cache, _cache_timestamp
    _cache = {}
    _cache_timestamp = None
    logger.info("[TrendWatcher] Cache limpo")


# Exports
__all__ = ["get_trends", "clear_cache", "_get_fallback_trends"]
