"""Loop autonomo para o pipeline do site (Sprint 2).

Substitui a FSM hardcoded em pipeline_orchestrator_service.py:1557-2068
por decisao baseada em resultado:
- Nicho com confidence < 0.5: retry com feedback (max 2 tentativas)
- Arquiteto com < 7 sections: retry com feedback
- OpenUI HTML < 2KB ou > 100KB: retry OpenUI com feedback
- Validador score < 5: retry OpenUI com feedback de QA
- Validador score >= 7: DEPLOY direto
- attempt_count > 2: DEPLOY com warning (force through)

Padrao reutilizado de sdr_langgraph/orchestrator.py:47-136.

Backward-compat: a FSM padrao continua funcionando quando
FRALIB_USE_SDK_LOOP != '1'. Sprint 2 adiciona apenas um wrapper
opcional run_site_pipeline_with_tools_and_loop().

Reuso:
- state_machine.decide_transition (sdr_langgraph/state_machine.py:155)
- NichoBriefing, VariacaoEstrutural, DesignerPRD, ValidacaoResultado
  (backend/agents/handoff_types.py)
- SUB_NICHO_TEMPLATES (backend/agents/agente_variacao.py)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)


# Constantes de decisao (max retries para evitar loop infinito)
MAX_NICHO_RETRIES = 2
MAX_ARQUITETO_RETRIES = 2
MAX_OPENUI_RETRIES = 2  # Total ciclo OpenUI/Validador
MAX_OPENUI_SIZE_BYTES = 100 * 1024  # 100KB
MIN_OPENUI_SIZE_BYTES = 2_000  # 2KB - HTML incompleto
MIN_SECTIONS_ARQUITETO = 7


AgentName = Literal[
    "nicho", "variacao", "arquiteto", "openui", "validador", "deploy", "retry"
]


@dataclass
class SiteOrchestratorDecision:
    """Decisao completa do orchestrator para um agente do site."""
    next_agent: AgentName
    reasoning: str
    should_retry_with_feedback: bool = False
    feedback_for_retry: Optional[str] = None  # injetado no prompt do retry
    force_through: bool = False  # se True, segue apesar de problemas
    force_through_warning: Optional[str] = None  # msg para logs/UI


@dataclass
class SitePipelineState:
    """Estado acumulado do pipeline do site durante o loop."""
    pipeline_id: str = ""
    tenant_id: int = 0
    segmento: str = ""

    # Resultados de cada agente
    nicho_briefing: Any = None  # NichoBriefing
    nicho_confidence: float = 0.0
    nicho_attempts: int = 0

    variacao_estrutural: Any = None  # VariacaoEstrutural
    variacao_attempts: int = 0

    prd: Any = None  # DesignerPRD
    prd_sections_count: int = 0
    prd_attempts: int = 0

    html: str = ""
    html_size_bytes: int = 0
    openui_attempts: int = 0

    validador_result: Any = None  # ValidacaoResultado
    validador_attempts: int = 0

    # Feedback do ultimo retry
    last_feedback: Optional[str] = None

    # Warning se loop foi forcado
    force_through_warning: Optional[str] = None


def decide_next_site_agent(
    current_agent: str,
    state: SitePipelineState,
) -> SiteOrchestratorDecision:
    """Decide qual agente executar em seguida baseado no resultado atual.

    Args:
        current_agent: nome do agente que acabou de executar.
        state: estado acumulado do pipeline.

    Returns:
        SiteOrchestratorDecision com next_agent + feedback opcional.
    """
    # ──── NICHO ────
    if current_agent == "nicho":
        if state.nicho_confidence < 0.5 and state.nicho_attempts < MAX_NICHO_RETRIES:
            feedback = (
                f"Briefing anterior teve confidence {state.nicho_confidence:.2f} "
                f"(abaixo de 0.5). Refine a analise: extraia mais 3 USPs "
                f"especificos do segmento, identifique 2 objecoes reais "
                f"dos reviews, e justifique a confianca com base em dados."
            )
            return SiteOrchestratorDecision(
                next_agent="retry",
                reasoning=(
                    f"nicho confidence {state.nicho_confidence:.2f} < 0.5 "
                    f"(attempt {state.nicho_attempts}/{MAX_NICHO_RETRIES})"
                ),
                should_retry_with_feedback=True,
                feedback_for_retry=feedback,
            )
        return SiteOrchestratorDecision(
            next_agent="variacao",
            reasoning=(
                f"nicho OK (confidence {state.nicho_confidence:.2f})"
                if state.nicho_briefing else "nicho sem briefing - avancando"
            ),
        )

    # ──── VARIACAO ────
    if current_agent == "variacao":
        return SiteOrchestratorDecision(
            next_agent="arquiteto",
            reasoning="variacao OK (template canonico ou gerado)",
        )

    # ──── ARQUITETO ────
    if current_agent == "arquiteto":
        if (
            state.prd_sections_count < MIN_SECTIONS_ARQUITETO
            and state.prd_attempts < MAX_ARQUITETO_RETRIES
        ):
            feedback = (
                f"PRD anterior teve {state.prd_sections_count} secoes "
                f"(minimo {MIN_SECTIONS_ARQUITETO}). Acrescente: hero, sobre, "
                f"servicos, depoimentos, FAQ, contato, footer. Use a ordem "
                f"de secoes do SUB_NICHO_TEMPLATES quando disponivel."
            )
            return SiteOrchestratorDecision(
                next_agent="retry",
                reasoning=(
                    f"arquiteto sections {state.prd_sections_count} "
                    f"< {MIN_SECTIONS_ARQUITETO} "
                    f"(attempt {state.prd_attempts}/{MAX_ARQUITETO_RETRIES})"
                ),
                should_retry_with_feedback=True,
                feedback_for_retry=feedback,
            )
        return SiteOrchestratorDecision(
            next_agent="openui",
            reasoning=(
                f"arquiteto OK ({state.prd_sections_count} secoes)"
                if state.prd else "arquiteto sem PRD - avancando"
            ),
        )

    # ──── OPENUI ────
    if current_agent == "openui":
        _size = state.html_size_bytes or len(state.html or "")
        if _size > 0 and _size < MIN_OPENUI_SIZE_BYTES:
            if state.openui_attempts < MAX_OPENUI_RETRIES:
                return SiteOrchestratorDecision(
                    next_agent="retry",
                    reasoning=f"openui HTML muito pequeno ({_size} bytes)",
                    should_retry_with_feedback=True,
                    feedback_for_retry=(
                        f"HTML gerado tem apenas {_size} bytes. Provavelmente "
                        f"truncado. Gere o HTML COMPLETO com todas as secoes."
                    ),
                )
        if _size > MAX_OPENUI_SIZE_BYTES:
            return SiteOrchestratorDecision(
                next_agent="deploy",
                reasoning=f"openui HTML grande ({_size} bytes) - prossegue",
                force_through=True,
                force_through_warning=(
                    f"HTML > {MAX_OPENUI_SIZE_BYTES} bytes "
                    f"(gerado: {_size}) - pode ter problemas de performance"
                ),
            )
        return SiteOrchestratorDecision(
            next_agent="validador",
            reasoning=f"openui OK ({_size} bytes)",
        )

    # ──── VALIDADOR ────
    if current_agent == "validador":
        score = getattr(state.validador_result, "score", 0.0) or 0.0
        if score >= 7.0:
            return SiteOrchestratorDecision(
                next_agent="deploy",
                reasoning=f"validador score {score:.1f} >= 7.0 - DEPLOY",
            )
        if score >= 5.0 and state.validador_attempts == 0:
            return SiteOrchestratorDecision(
                next_agent="deploy",
                reasoning=f"validador score {score:.1f} ok (>= 5.0) - DEPLOY",
                force_through=True,
                force_through_warning=(
                    f"Score {score:.1f} abaixo do ideal (>=7), mas >= 5. Prossegue."
                ),
            )
        if state.validador_attempts < MAX_OPENUI_RETRIES:
            problemas = getattr(state.validador_result, "problemas", []) or []
            feedback = (
                f"Validador LLM-as-judge deu score {score:.1f}/10. "
                f"Problemas identificados: {'; '.join(problemas[:5]) or 'nenhum detalhado'}. "
                f"Refine o HTML: corrija problemas criticos, mantenha LGPD visivel, "
                f"garanta 7+ secoes com conteudo, e otimize meta tags."
            )
            return SiteOrchestratorDecision(
                next_agent="retry",
                reasoning=(
                    f"validador score {score:.1f} < 5.0 "
                    f"(attempt {state.validador_attempts}/{MAX_OPENUI_RETRIES})"
                ),
                should_retry_with_feedback=True,
                feedback_for_retry=feedback,
            )
        return SiteOrchestratorDecision(
            next_agent="deploy",
            reasoning=(
                f"validador score {score:.1f} mas max retries atingido - DEPLOY"
            ),
            force_through=True,
            force_through_warning=(
                f"Validador reprovou (score {score:.1f}) mas max retries "
                f"({MAX_OPENUI_RETRIES}) atingido. Forcando deploy."
            ),
        )

    # ──── DEPLOY / RETRY (fallback) ────
    return SiteOrchestratorDecision(
        next_agent="deploy",
        reasoning=f"fallback from {current_agent}",
    )


def run_site_pipeline_with_tools_and_loop(
    state: SitePipelineState,
    run_nicho,
    run_variacao,
    run_arquiteto,
    run_openui,
    run_validador,
    *,
    use_tools: bool = True,
) -> SitePipelineState:
    """Loop autonomo do pipeline do site.

    Cada run_X(state) deve popular state.X_attempts += 1 e o resultado.
    Para hooks de retry, run_X recebe state.last_feedback (setado pelo orchestrator).

    Args:
        state: SitePipelineState (modificado in-place).
        run_nicho: callable(state) -> NichoBriefing
        run_variacao: callable(state) -> VariacaoEstrutural
        run_arquiteto: callable(state) -> DesignerPRD
        run_openui: callable(state) -> str (HTML)
        run_validador: callable(state) -> ValidacaoResultado
        use_tools: se True, chama tools_site antes de cada agente (default).

    Returns:
        state (mesmo objeto, modificado).
    """
    if use_tools:
        try:
            from backend.agents.tools_site import (
                retrieve_similar_briefings,
                get_nicho_history,
                retrieve_top_templates,
            )
            # Pre-fetch: injeta contexto historico no state para uso pelos run_X
            _nicho = state.segmento or "default"
            state.nicho_history = get_nicho_history(_nicho, limit=5)
            state.similar_briefings = retrieve_similar_briefings(_nicho, top_k=5)
            if state.nicho_briefing and getattr(state.nicho_briefing, "subnicho", ""):
                state.top_templates = retrieve_top_templates(state.nicho_briefing.subnicho)
        except Exception as e:
            logger.warning(f"[site_orchestrator] pre-fetch tools falhou: {e}")

    current = "nicho"
    max_steps = 30  # safety: nunca mais que 30 decisoes
    steps = 0

    while current not in ("deploy",) and steps < max_steps:
        steps += 1
        try:
            if current == "nicho":
                state.nicho_attempts += 1
                state.nicho_briefing = run_nicho(state)
                state.nicho_confidence = (
                    float(getattr(state.nicho_briefing, "confianca_num", 0.7))
                    if state.nicho_briefing else 0.0
                )

            elif current == "variacao":
                state.variacao_attempts += 1
                state.variacao_estrutural = run_variacao(state)

            elif current == "arquiteto":
                state.prd_attempts += 1
                state.prd = run_arquiteto(state)
                state.prd_sections_count = (
                    len(getattr(state.prd, "sections", []) or [])
                    if state.prd else 0
                )

            elif current == "openui":
                state.openui_attempts += 1
                state.html = run_openui(state)
                state.html_size_bytes = len(state.html or "")

            elif current == "validador":
                state.validador_attempts += 1
                state.validador_result = run_validador(state)

            elif current == "retry":
                # Retry: o agente ja recebe state.last_feedback via run_X
                _last = getattr(state, "_last_agent", "nicho")
                state.last_feedback = state.last_feedback
                if _last == "nicho":
                    state.nicho_attempts += 1
                    state.nicho_briefing = run_nicho(state)
                    state.nicho_confidence = (
                        float(getattr(state.nicho_briefing, "confianca_num", 0.7))
                        if state.nicho_briefing else 0.0
                    )
                elif _last == "arquiteto":
                    state.prd_attempts += 1
                    state.prd = run_arquiteto(state)
                    state.prd_sections_count = (
                        len(getattr(state.prd, "sections", []) or [])
                        if state.prd else 0
                    )
                elif _last == "openui":
                    state.openui_attempts += 1
                    state.html = run_openui(state)
                    state.html_size_bytes = len(state.html or "")
                _next = "nicho" if _last == "nicho" else ("arquiteto" if _last == "arquiteto" else "validador")
                decision = decide_next_site_agent(_last, state)
                if decision.force_through:
                    state.force_through_warning = decision.force_through_warning
                    current = "deploy"
                else:
                    current = _next  # avancar normalmente
                continue
        except Exception as e:
            logger.exception(f"[site_orchestrator] erro em {current}: {e}")
            state.force_through_warning = f"erro em {current}: {e}"
            current = "deploy"
            continue

        # Decide proximo
        decision = decide_next_site_agent(current, state)
        logger.info(
            f"[site_orchestrator] {current} -> {decision.next_agent} "
            f"({decision.reasoning})"
        )
        if decision.force_through:
            state.force_through_warning = decision.force_through_warning
        if decision.should_retry_with_feedback:
            state.last_feedback = decision.feedback_for_retry
            state._last_agent = current
            current = "retry"
        else:
            current = decision.next_agent

    if current != "deploy":
        logger.warning(
            f"[site_orchestrator] max steps ({max_steps}) atingido sem deploy"
        )
        state.force_through_warning = (
            f"max steps ({max_steps}) atingido - forcado deploy"
        )
        current = "deploy"

    # Persistir lesson final se deploy
    if state.force_through_warning is None and getattr(state, "validador_result", None):
        try:
            from backend.agents.tools_site import save_pipeline_lesson
            save_pipeline_lesson(
                lesson=(
                    f"Site deploy OK: nicho={state.segmento}, "
                    f"html_size={state.html_size_bytes}, "
                    f"validador_score={state.validador_result.score:.1f}"
                ),
                score=float(state.validador_result.score),
                agente="site_pipeline",
                nicho=state.segmento or "default",
            )
        except Exception as e:
            logger.warning(f"[site_orchestrator] save_lesson final falhou: {e}")

    return state
