"""Pipeline learning helpers.

Stores small, reusable lessons for active LLM agents. This is not model
fine-tuning; it is retrieval memory injected by ``llm_direct`` during pipeline
runs via ``agent_memory``.
"""

from __future__ import annotations

from typing import Any


ACTIVE_LEARNING_AGENTS = (
    "agente_nicho",
    "arquiteto_mestre",
    "builder_renderer",
    "validador",
    "franz",
)


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    return " ".join(text.split())[:180]


def _safe_add(warm: Any, entry: Any) -> None:
    try:
        warm.adicionar(entry)
    except Exception:
        pass


def record_pipeline_success(
    warm: Any,
    *,
    nicho: str,
    archetype: str = "",
    renderer: str = "builder_renderer",
    tier: str = "",
    site_url: str = "",
) -> int:
    """Record lessons after a generated site passes gates and deploy phase."""
    if not warm:
        return 0
    try:
        from agent_memory import MemoryEntry
    except Exception:
        from agents.agent_memory import MemoryEntry

    nicho = _clean(nicho, "*") or "*"
    archetype = _clean(archetype, "unknown") or "unknown"
    renderer = _clean(renderer, "builder_renderer") or "builder_renderer"
    tier = _clean(tier, "STANDARD") or "STANDARD"
    site_url = _clean(site_url)
    lessons = [
        (
            "arquiteto_mestre",
            f"Pipeline aprovado para nicho {nicho}: preservar DNA visual {archetype}, plano de secoes factual e contrato sem servicos inventados.",
        ),
        (
            "builder_renderer",
            f"Site aprovado em {nicho}/{tier}: renderer {renderer} deve manter hero 16:9, footer legivel, mapa unico e LGPD/SEO social.",
        ),
        (
            "agente_nicho",
            f"Briefing validado para {nicho}: separar fatos confirmados de inferencias e passar subnicho sem ampliar oferta.",
        ),
        (
            "validador",
            f"Gate aprovado em {nicho}: manter bloqueio de overflow na hero, mapa duplicado, footer ilegivel e texto sem contraste.",
        ),
    ]
    if site_url:
        lessons.append(("franz", f"Site publicado para {nicho}; SDR pode conduzir curiosidade antes de preco usando link somente apos contexto."))

    count = 0
    for agent, content in lessons:
        _safe_add(
            warm,
            MemoryEntry(
                tipo="pipeline_success",
                agente=agent,
                nicho=nicho,
                conteudo=content,
                confianca=0.72,
                vezes_usado=1,
                vezes_sucesso=1,
                fonte="pipeline_orchestrator_service",
            ),
        )
        count += 1
    return count


def record_pipeline_error(
    warm: Any,
    *,
    nicho: str,
    fase: str = "",
    erro: str = "",
) -> int:
    """Record compact failure lessons so future prompts avoid repeated errors."""
    if not warm:
        return 0
    try:
        from agent_memory import MemoryEntry
    except Exception:
        from agents.agent_memory import MemoryEntry

    nicho = _clean(nicho, "*") or "*"
    fase = _clean(fase, "unknown") or "unknown"
    erro = _clean(erro, "erro desconhecido") or "erro desconhecido"
    content = f"Falha recente em {nicho} na fase {fase}: evitar repetir causa '{erro}'. Validar entrada antes de prosseguir."
    for agent in ("arquiteto_mestre", "builder_renderer", "validador"):
        _safe_add(
            warm,
            MemoryEntry(
                tipo="pipeline_error",
                agente=agent,
                nicho=nicho,
                conteudo=content,
                confianca=0.65,
                vezes_usado=1,
                vezes_falha=1,
                fonte="pipeline_orchestrator_service",
            ),
        )
    return 3
