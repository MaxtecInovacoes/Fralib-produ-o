"""Hook de memory 3-tier para o Franz SDR.

Pluga a infraestrutura existente (agent_memory.Core/Warm) no fluxo do
agente de WhatsApp. Antes do LLM call, seta thread-local memory;
depois, persiste o que aprendeu (se o lead engajou, respondeu, etc).

Feature #1 do roadmap Franz 10/10.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from .state import LeadMemory

logger = logging.getLogger(__name__)


# Carrega Core/Warm uma vez no startup (singleton)
_core = None
_warm = None


def _ensure_loaded():
    """Carrega Core e Warm do disco uma vez."""
    global _core, _warm
    if _core is None or _warm is None:
        try:
            from backend.agent_memory import CoreMemory, WarmMemory
            _core = CoreMemory()
            _warm = WarmMemory()
        except Exception as e:
            logger.warning(f"[memory_hook] falha ao carregar Core/Warm: {e}")
            _core = None
            _warm = None
    return _core, _warm


def inject_memory_for_franz(memory: LeadMemory, segmento: str) -> None:
    """Seta thread-local memory antes do LLM call.

    Args:
        memory: LeadMemory do lead atual.
        segmento: segmento do lead (academia, restaurante, etc).
    """
    try:
        from backend.agent_memory import set_memory
        core, warm = _ensure_loaded()
        if core is not None and warm is not None:
            set_memory(core, warm, segmento or memory.segmento or "default")
    except ImportError:
        # fallback quando rodando fora do venv (sem backend.* no path)
        from agent_memory import set_memory
        core, warm = _ensure_loaded()
        if core is not None and warm is not None:
            set_memory(core, warm, segmento or memory.segmento or "default")


def extract_and_persist_learning(
    memory: LeadMemory,
    incoming_message: str,
    intent_str: str,
    reply: str,
    next_stage: str,
) -> None:
    """Extrai aprendizagem do turno e persiste em Warm.

    Promove entries de Warm -> Core quando confianca >= 0.9 e uso >= 5.

    Args:
        memory: LeadMemory.
        incoming_message: msg do lead.
        intent_str: intent classificado (string).
        reply: resposta do Franz.
        next_stage: stage decidido.
    """
    core, warm = _ensure_loaded()
    if core is None or warm is None:
        return

    segmento = memory.segmento or "default"

    # 1. Persistir Warm entry com insight sobre o nicho
    try:
        insight = _build_insight(memory, incoming_message, intent_str, next_stage)
        if insight:
            warm.adicionar(
                tipo="lead_pattern",
                agente="franz",
                nicho=segmento,
                conteudo=insight,
                confianca=0.7,
                fonte=f"turn:{memory.turn_count}",
            )
    except Exception as e:
        logger.warning(f"[memory_hook] persist_warm falhou: {e}")

    # 2. Promover entries maduras pro Core
    try:
        core, warm = _ensure_loaded()  # recarrega
        if core and warm:
            promoted = warm.promover_para_core(core)
            if promoted:
                logger.info(f"[memory_hook] {len(promoted)} entries promovidas pra Core")
    except Exception as e:
        logger.warning(f"[memory_hook] promote_warm_to_core falhou: {e}")


def _build_insight(memory: LeadMemory, incoming: str, intent: str, stage: str) -> Optional[str]:
    """Constroi uma frase de insight curta baseada no turno."""
    if not incoming or not incoming.strip():
        return None
    snippet = incoming[:80].strip()
    if intent in ("objection", "opt_out"):
        return f"Lead em {memory.segmento or 'nicho'} objecao: {snippet}"
    if intent == "buying_intent":
        return f"Lead em {memory.segmento or 'nicho'} pediu preco/link/compra"
    if intent == "engagement":
        return f"Lead em {memory.segmento or 'nicho'} engajou no stage {stage}: {snippet}"
    return None