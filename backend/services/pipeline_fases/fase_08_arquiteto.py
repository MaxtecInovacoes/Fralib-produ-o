"""
Fase 8: Arquiteto Mestre (PRD Builder)
Extraída do pipeline_orchestrator_service.py para manter SRP.
"""

import hashlib
import logging
import os
import random
from typing import Any, Callable, Optional

from sqlalchemy import text

from backend.services.pipeline_prd_builder import (
    build_prompt_agent_prd as _build_prompt_agent_prd,
    build_skill_fast_prd as _build_skill_fast_prd,
    ensure_prd_contracts as _ensure_prd_contracts,
    ensure_prd_design_reference as _ensure_prd_design_reference,
    ensure_prd_publication_identity as _ensure_prd_publication_identity,
)
from backend.services.pipeline_cache_control import temporary_prd_cache_disabled
from backend.agents.arquiteto_mestre import gerar_arquiteto_mestre_prd
from backend.pipeline_ledger import FaseStatus, Ledger

logger = logging.getLogger("uvicron")


def executar_fase_8(
    state: Any,
    config: dict,
    tenant_id: int,
    engine: Any,
    ledger: Optional[Ledger],
    get_dados_agente: Callable,
    salvar_checkpoint: Callable,
    tentar: Callable,
    log_func: Callable,
    progress_func: Callable,
    iniciar_span: Optional[Callable] = None,
    finalizar_span: Optional[Callable] = None,
    trace: bool = False,
    prompt_agent_flow: bool = False,
    builder_fast_path: bool = False,
    arquiteto_agent: bool = False,
) -> dict:
    """
    Executa Fase 8: Arquiteto Mestre (PRD Builder).

    Args:
        state: FraLibState com dados das fases anteriores
        config: Configuração do pipeline
        tenant_id: ID do tenant
        engine: Engine de banco de dados
        ledger: Ledger para registro de fases
        get_dados_agente: Função para obter dados em cache
        salvar_checkpoint: Função para salvar checkpoint
        tentar: Função de retry
        log_func: Função de log
        progress_func: Função de progresso SSE
        iniciar_span: Função para iniciar span de observabilidade
        finalizar_span: Função para finalizar span
        trace: Se True, habilita tracing
        prompt_agent_flow: Se True, usa fluxo de prompt agent
        builder_fast_path: Se True, usa PRD factual compacto
        arquiteto_agent: Se True, usa _gerar_prd_agent

    Returns:
        dict com state atualizado (prd_arquiteto)
    """
    # Progresso e logging
    progress_func(8, "Arquitetando site...")
    log_func("FASE 8: ARQUITETO MESTRE", "info")

    # Finalizar fase 7 e iniciar fase 8 no ledger
    if ledger:
        ledger.registrar_fim_fase(7, FaseStatus.CONCLUIDA)
        ledger.registrar_inicio_fase(8, "arquiteto_mestre", modelo="sonnet")

    # Span de observabilidade
    span = None
    if trace and iniciar_span:
        span = iniciar_span("arquiteto_mestre", agente="arquiteto_mestre", modelo="sonnet")

    # Verificar cache do PRD
    arq_cached = (
        None
        if config.get("_forcar_renovacao") or config.get("_cold_run")
        else get_dados_agente(state.pipeline_id, "arquiteto_mestre")
    )

    # Fluxos alternativos
    if prompt_agent_flow:
        state.prd_arquiteto = _build_prompt_agent_prd(state, tenant_id)
        arq_cached = {"prd_json": True}
        log_func(
            f"  Prompt: {len(state.prd_arquiteto.builder_prompt):,} chars para o Builder",
            "success",
        )
    elif builder_fast_path:
        state.prd_arquiteto = _build_skill_fast_prd(state)
        arq_cached = {"prd_json": True}
        log_func("  PRD: fast-path factual compacto (sem LLM)", "success")
    elif arq_cached and arq_cached.get("prd_json"):
        # Retomar PRD do checkpoint
        from designer_prd import DesignerPRD as PRDOutput

        try:
            state.prd_arquiteto = PRDOutput(**arq_cached["prd_json"])
            log_func(
                f"  PRD: retomado do checkpoint ({len(state.prd_arquiteto.sections)} secoes)",
                "success",
            )
        except Exception as prd_err:
            log_func(f"  Checkpoint PRD invalido, regenerando: {prd_err}", "warning")
            arq_cached = None

    # Gerar PRD se não tiver cache
    if (
        not builder_fast_path
        and (not arq_cached or not arq_cached.get("prd_json"))
    ):
        # Setup de seed para reprodutibilidade
        seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        pool = [
            "mask-reveal", "counter-animation", "parallax-scroll", "stagger-fade",
            "reveal-on-scroll", "text-split", "floating-cards", "elastic-scale",
            "wave-animation", "spotlight-hover", "tilt-3d", "fade-up",
            "slide-in", "zoom-reveal",
        ]
        random.sample(pool, 6)

        seg = state.segmento or state.lead_obj.lead.segmento or "negocio local"
        cid = state.lead_obj.lead.cidade or state.cidade or ""
        prd_fn = gerar_arquiteto_mestre_prd

        with temporary_prd_cache_disabled(
            bool(config.get("_forcar_renovacao") or config.get("_cold_run"))
        ):
            state.prd_arquiteto = tentar(
                lambda: prd_fn(
                    dados_hunter=state.lead_raw_data,
                    cidade=cid,
                    segmento=seg,
                    jina_insights=state.jina_insights,
                    briefing_theo=state.briefing_theo,
                    caio_tier=(
                        state.qualificacao_caio.tier
                        if state.qualificacao_caio
                        else "STANDARD"
                    ),
                    caio_score=(
                        state.qualificacao_caio.score
                        if state.qualificacao_caio
                        else 0
                    ),
                    caio_motivo=(
                        state.qualificacao_caio.motivo
                        if state.qualificacao_caio
                        else ""
                    ),
                    dark_mode=(state.segmento or "").lower()
                    in ("academia", "crossfit", "churrascaria", "barbearia"),
                    keyword_research=getattr(state, "keyword_research", ""),
                    inteligencia=getattr(state, "inteligencia", {}),
                    nicho_briefing=getattr(state, "nicho_briefing", None),
                    variacao=getattr(state, "variacao_estrutural", None),
                ),
                fase="arquiteto_mestre",
                max_attempts=3,
                base_delay=2.0,
                log_fn=log_func,
            )

        log_func(f"  PRD: {len(state.prd_arquiteto.sections)} secoes", "success")

        # Salvar checkpoint do PRD
        _salvar_checkpoint_prd(state, ledger, get_dados_agente, salvar_checkpoint, log_func)

    # White-label: verificar plano PRO
    _aplicar_white_label(state, engine, tenant_id, log_func)

    # Contracts e design reference
    if prompt_agent_flow:
        log_func("  Contracts antigos: desativados no fluxo Agente de Prompt", "info")
    else:
        # Forçar google_maps_embed curado no PRD
        state.prd_arquiteto.google_maps_embed = state.lead_raw_data.get(
            "google_maps_embed", ""
        )
        _aplicar_contracts_e_design(
            state, ledger, get_dados_agente, salvar_checkpoint, log_func
        )

    # Salvar PRD no trace para auditoria
    _salvar_trace_prd(state, log_func)

    # Finalizar fase 8
    if ledger:
        ledger.registrar_fim_fase(8, FaseStatus.CONCLUIDA, resultado="PRD gerado")

    if span and finalizar_span:
        finalizar_span("success")

    return {"state": state}


# ─── HELPERS INTERNOS ─────────────────────────────────────────────────────────


def _salvar_checkpoint_prd(
    state: Any,
    ledger: Optional[Ledger],
    get_dados_agente: Callable,
    salvar_checkpoint: Callable,
    log_func: Callable,
) -> None:
    """Salva checkpoint do PRD após geração."""
    def validar_output(output: Any, min_chars: int = 50) -> bool:
        text = output if isinstance(output, str) else str(output)
        return len(text) >= min_chars

    try:
        prd_dict = (
            state.prd_arquiteto.model_dump()
            if hasattr(state.prd_arquiteto, "model_dump")
            else state.prd_arquiteto.__dict__
        )
        if validar_output(str(prd_dict), min_chars=200):
            salvar_checkpoint(
                state.pipeline_id, "arquiteto_mestre", {"prd_json": prd_dict}
            )
        else:
            log_func("  PRD output truncado - nao salvou checkpoint", "warning")
    except Exception as ckpt_e:
        print(f"[Checkpoint] PRD save skip: {ckpt_e}")


def _aplicar_white_label(
    state: Any, engine: Any, tenant_id: int, log_func: Callable
) -> None:
    """Verifica se tenant tem plano PRO (remove branding FraLib do footer)."""
    try:
        with engine.connect() as wl_conn:
            wl_row = wl_conn.execute(
                text("SELECT plano FROM users WHERE id=:uid"), {"uid": tenant_id}
            ).fetchone()
            if wl_row and wl_row[0] in ("pro", "enterprise"):
                state.prd_arquiteto.white_label = True
    except Exception:
        pass


def _aplicar_contracts_e_design(
    state: Any,
    ledger: Optional[Ledger],
    get_dados_agente: Callable,
    salvar_checkpoint: Callable,
    log_func: Callable,
) -> None:
    """Aplica contracts de design e publication identity."""
    try:
        pack_id = _ensure_prd_design_reference(state.prd_arquiteto, state)
        if pack_id:
            log_func(f"  Design reference pack: {pack_id}", "success")
        _ensure_prd_contracts(state.prd_arquiteto, state)
        # publication_identity pode precisar de tenant_id, pular aqui
        log_func("  Contracts: requirements + visual OK", "info")
    except Exception as pack_err:
        logger.warning(f"[Pipeline] Design reference pack skip: {pack_err}")


def _salvar_trace_prd(state: Any, log_func: Callable) -> None:
    """Salva PRD no trace para auditoria."""
    try:
        import json

        trace_dir = os.getenv("PIPELINE_TRACE_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            "logs",
            "pipeline_trace",
        )
        os.makedirs(trace_dir, exist_ok=True)
        prd_dict = (
            state.prd_arquiteto.model_dump()
            if hasattr(state.prd_arquiteto, "model_dump")
            else state.prd_arquiteto.__dict__
        )
        with open(f"{trace_dir}/designer_prd.json", "w", encoding="utf-8") as pf:
            json.dump(prd_dict, pf, ensure_ascii=False, indent=2, default=str)
    except Exception as pe:
        print(f"[Pipeline] PRD trace skip: {pe}")
