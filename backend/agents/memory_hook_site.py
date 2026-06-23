"""Hook de memory 3-tier para agentes do pipeline de site (Nicho, Arquiteto, Validador).

Pluga a infraestrutura existente (agent_memory.Core/Warm) no fluxo do
orchestrator. Antes do LLM call do agente, seta thread-local memory;
depois, persiste lesson com score do validador (feedback loop Nicho<->Validador).

v1.1-baseline-2026-06-23 (Sprint 1): novo modulo espelhando o padrao de
sdr_langgraph/memory_hook.py mas reutilizando o singleton de Core/Warm
(nao duplica instancia).
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_core: Optional[object] = None
_warm: Optional[object] = None


def _ensure_loaded() -> tuple[Optional[object], Optional[object]]:
    """Carrega Core/Warm uma vez (singleton thread-local).

    Returns:
        (core, warm) ou (None, None) se falhar ao carregar.
    """
    global _core, _warm
    if _core is None or _warm is None:
        try:
            from backend.agent_memory import CoreMemory, WarmMemory
            _core = CoreMemory()
            _warm = WarmMemory()
        except Exception as e:
            logger.warning(f"[memory_hook_site] falha ao carregar Core/Warm: {e}")
            _core = None
            _warm = None
    return _core, _warm


def inject_memory_for_site(agente: str, nicho: str) -> None:
    """Seta thread-local memory antes do LLM call de Nicho/Arquiteto/Validador.

    Args:
        agente: nome do agente (agente_nicho, arquiteto_mestre, validador).
        nicho: segmento do lead (academia_crossfit, nutricionista_esportiva, etc).
    """
    try:
        from backend.agent_memory import set_memory
    except ImportError:
        try:
            from agent_memory import set_memory
        except ImportError:
            logger.warning("[memory_hook_site] set_memory nao encontrado")
            return

    core, warm = _ensure_loaded()
    if core is not None and warm is not None:
        try:
            set_memory(core, warm, nicho or "default")
            logger.debug(f"[memory_hook_site] memory injetada para {agente}/{nicho}")
        except Exception as e:
            logger.warning(f"[memory_hook_site] set_memory falhou: {e}")


def persist_lesson_with_score(
    agente: str,
    nicho: str,
    conteudo: str,
    *,
    validador_score: float = 0.0,
    confianca_base: float = 0.7,
) -> None:
    """Persiste lesson em Warm ajustando confianca pelo score do validador.

    Feedback loop Nicho<->Validador (Sprint 1): briefing do Nicho entra em
    Warm com score do Validador como multiplicador de confianca.
    Briefing bom (score >= 7) -> confianca ate 1.0.
    Briefing ruim (score < 5) -> confianca cai para 0.3-0.5.

    Args:
        agente: nome do agente (agente_nicho, arquiteto_mestre, validador, builder_renderer).
        nicho: segmento do lead.
        conteudo: lesson aprendida (string curta, max ~180 chars).
        validador_score: 0-10 do validador LLM-as-judge.
        confianca_base: confianca inicial antes do multiplicador.
    """
    core, warm = _ensure_loaded()
    if warm is None:
        logger.warning("[memory_hook_site] warm indisponivel; lesson nao persistida")
        return

    if validador_score >= 7.0:
        score_multiplier = 1.2
    elif validador_score >= 5.0:
        score_multiplier = 1.0
    else:
        score_multiplier = 0.5

    _confianca = min(1.0, max(0.3, confianca_base * score_multiplier))

    try:
        from backend.agent_memory import MemoryEntry
    except ImportError:
        try:
            from agent_memory import MemoryEntry
        except ImportError:
            logger.warning("[memory_hook_site] MemoryEntry nao encontrado")
            return

    try:
        warm.adicionar(
            MemoryEntry(
                tipo="agent_lesson",
                agente=agente,
                nicho=nicho,
                conteudo=conteudo[:180],
                confianca=_confianca,
                fonte=f"validador_score={validador_score:.1f}",
            )
        )
        logger.debug(
            f"[memory_hook_site] lesson persistida: {agente}/{nicho} "
            f"score={validador_score} conf={_confianca:.2f}"
        )
    except Exception as e:
        logger.warning(f"[memory_hook_site] warm.adicionar falhou: {e}")
