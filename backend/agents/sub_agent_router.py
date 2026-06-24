"""Router para sub-agentes especializados (Sprint 6 - v1.9).

Recebe estetica + prd + facts, dispatch para o handler correto.
Fallback para default_agent se estetica nao registrada.

Pattern identico a tools_site.py (TOOLS_DISPATCH).
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.agents.sub_agents import (
    SUB_AGENT_DISPATCH,
    default_agent,
    list_sub_agents,
)

logger = logging.getLogger(__name__)


def route_to_sub_agent(
    estetica: str,
    prd: dict,
    facts: dict,
) -> str:
    """Dispatch para o sub-agente correto baseado na estetica.

    Args:
        estetica: nome da estetica (BOLD_ENERGY/EDITORIAL/MINIMAL/KINETIC/SCROLL/IMMERSIVE_3D).
        prd: dict com o PRD do lead (do agente arquiteto).
        facts: dict com fatos do lead (business_name, tagline, city, etc).

    Returns:
        String HTML otimizado para a estetica.
    """
    try:
        from backend.services.tracing import trace_run
        _HAS_TRACING = True
    except ImportError:
        _HAS_TRACING = False
        from contextlib import contextmanager
        @contextmanager
        def trace_run(*args, **kwargs):
            yield None

    handler = SUB_AGENT_DISPATCH.get(estetica, default_agent)

    if _HAS_TRACING:
        with trace_run(
            "sub_agent_router",
            "route",
            inputs={"estetica": estetica, "facts_keys": list(facts.keys())},
        ):
            html = handler(prd, facts)
    else:
        html = handler(prd, facts)

    return html


def get_sub_agent_for_nicho(nicho: str) -> str:
    """Mapeia nicho do lead para estetica recomendada.

    Args:
        nicho: nicho do lead (academia_crossfit, restaurante_familiar, etc).

    Returns:
        Nome da estetica recomendada.
    """
    NICHO_TO_ESTETICA = {
        "academia_crossfit": "BOLD_ENERGY",
        "nutricionista_esportiva": "MINIMAL",
        "barbearia_premium": "EDITORIAL",
        "restaurante_familiar": "KINETIC",
        "clinica_estetica": "EDITORIAL",
        "advocacia_trabalhista": "EDITORIAL",
        "ecommerce_basico": "SCROLL",
        "saas_premium": "IMMERSIVE_3D",
        "default": "MINIMAL",
    }
    return NICHO_TO_ESTETICA.get(nicho, "default")


def is_valid_estetica(estetica: str) -> bool:
    """Verifica se a estetica esta registrada."""
    return estetica in SUB_AGENT_DISPATCH
