"""Helpers for multi-lead pipeline execution flow."""

from __future__ import annotations


def handle_pipeline_no_leads(
    *,
    config: dict,
    segmento: str,
    cidade: str,
    logger,
) -> bool:
    """Handle the repeated empty-pool branch for the multi-run pipeline.

    Returns True when the caller should continue retrying with a fresh cache.
    """
    if not config.get("_cache_invalidado"):
        logger(
            "Cache esgotado. Buscando leads novos no Google Maps...",
            "info",
        )
        config["_cache_invalidado"] = True
        config["force_fresh"] = True
        return True

    logger(
        "Sem mais leads disponiveis para "
        + segmento
        + " em "
        + cidade
        + ". Tente outro nicho ou uma cidade maior.",
        "warning",
    )
    return False
