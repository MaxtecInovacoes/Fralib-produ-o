"""Pipeline Orchestrator Service.

⚠️  ORQUESTRADOR - NÃO É MONOLITO
=================================
Este arquivo é um ORQUESTRADOR que coordena ~20 módulos de helpers.
Lógica de negócio extraída para:
- pipeline_execution_core.py: Execução de pipeline
- pipeline_phase_helpers.py: Helpers de fase
- pipeline_lead_flow_helpers.py: Fluxo de leads
- pipeline_lead_persistence.py: Persistência
- pipeline_status_endpoints.py: Status endpoints
- pipeline_trace_helpers.py: Tracing
- pipeline_heartbeat.py: Heartbeat
- pipeline_start_endpoints.py: Start endpoints
- pipeline_run_helpers.py: Run helpers
- pipeline_sse_handler.py: SSE handler
- pipeline_reprocess_endpoints.py: Reprocess endpoints
- pipeline_control_endpoints.py: Control endpoints
- E mais ~12 arquivos de helpers

@architecture Orquestrador (coordena módulos, ~2,500 linhas de orquestração)
"""

import asyncio
import hashlib
import logging
import os
import random
import re
import sys
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from backend.services.pipeline_executors import (
    tentar,
)
from backend.services.pipeline_phases import (
    FraLibState,
    _pipeline_phase_key_impl,
    aplicar_segmento_inferido,
    sincronizar_segmento_state,
    validar_output,
)
from backend.services.pipeline_state import (
    atualizar_pipeline_id_para_lead,
    build_lead_raw_data,
)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

from backend.core.database import (
    Session,
    SessionLocal,
    engine,
    text,
    update_pipeline_state,
)
from backend.endpoints.pipeline_execution_core import execute_pipeline_tail
from backend.endpoints.pipeline_execution_helpers import (
    build_existing_lead_pipeline_config,
    log_legacy_queue_id,
)
from backend.endpoints.pipeline_lead_flow_helpers import (
    build_reprocess_seed_state,
    prepare_lead_intelligence_assets,
)
from backend.endpoints.pipeline_llm_context import set_llm_context_for_pipeline
from backend.endpoints.pipeline_multi_helpers import handle_pipeline_no_leads
from backend.endpoints.pipeline_phase_helpers import (
    build_franz_outreach_payload,
    build_prompt_phase_outputs,
    curate_lead_assets,
    ensure_jina_insights,
    ensure_keyword_research,
    finalize_reprocess_state,
    init_phase_tracking,
    publish_rendered_site,
)
from backend.endpoints.pipeline_run_helpers import maybe_schedule_autorun_next_lead
from backend.endpoints.sse_endpoints import adicionar_log
from backend.utils.agente1_hunter_v2 import buscar_leads_google_maps

# Re-exportar FraLibState do módulo de fases para compatibilidade
# (código existente usa esta definição local)
# A classe FraLibState em services/pipeline_phases.py é usada pelo novo código
# A definição abaixo mantida apenas para compatibilidade com código legado que referencia diretamente

# Usar FraLibState do módulo de fases
FraLibState = FraLibState  # Já importado acima


from backend.agents.caio import LeadInput as CaioInput

# Logs do pipeline chegam ao terminal via adicionar_log() chamado explicitamente
from backend.agents.caio import qualificar_lead
from backend.agents.pexels_video import buscar_videos_pexels
from backend.agents.pipeline_checkpoint import (
    gerar_pipeline_id,
    get_dados_agente,
    limpar_checkpoint,
    resumo_checkpoint,
    salvar_checkpoint,
)
from backend.agents.pipeline_identity import inferir_segmento_por_nome
from backend.agents.unsplash_fetcher import buscar_fotos_unsplash
from backend.endpoints.pipeline_sse_handler import _sse_handler
from backend.services.builder_worker import copy_builder_dist, render_site_with_builder
from backend.services.pipeline_cache_control import (
    invalidar_caches_cold_run as _invalidar_caches_cold_run,
)
from backend.services.pipeline_cache_control import (
    temporary_prd_cache_disabled as _temporary_prd_cache_disabled,
)
from backend.services.pipeline_flow_config import (
    is_builder_fast_path as _is_builder_fast_path,
)
from backend.services.pipeline_flow_config import (
    is_prompt_agent_flow as _is_prompt_agent_flow,
)
from backend.services.pipeline_flow_config import (
    skip_deterministic_gate as _skip_deterministic_gate,
)
from backend.services.pipeline_flow_config import (
    skip_html_quality_gate as _skip_html_quality_gate,
)
from backend.services.pipeline_phase_tracking import (
    pipeline_phase_key as _pipeline_phase_key_impl,
)
from backend.services.pipeline_phase_tracking import (
    set_pipeline_job_phase as _set_pipeline_job_phase_impl,
)
from backend.services.pipeline_prd_builder import (
    build_prompt_agent_prd as _build_prompt_agent_prd,
)
from backend.services.pipeline_prd_builder import (
    build_skill_fast_prd as _build_skill_fast_prd,
)
from backend.services.pipeline_prd_builder import (
    ensure_prd_contracts as _ensure_prd_contracts,
)
from backend.services.pipeline_prd_builder import (
    ensure_prd_design_reference as _ensure_prd_design_reference,
)
from backend.services.pipeline_prd_builder import (
    ensure_prd_publication_identity as _ensure_prd_publication_identity,
)
from backend.services.pipeline_prd_builder import (
    visual_archetype_id as _visual_archetype_id,
)
from backend.services.pipeline_renderer_support import (
    builder_job_id_for_state as _builder_job_id_for_state,
)
from backend.services.pipeline_renderer_support import (
    is_renderer_or_publication_error as _is_renderer_or_publication_error,
)
from backend.services.pipeline_renderer_support import (
    persist_failed_renderer_html as _persist_failed_renderer_html,
)
from backend.services.pipeline_sdr_delivery import (
    tenant_sdr_allowed as _tenant_sdr_allowed_impl,
)

# Renderer unico do pipeline principal.
gerar_html_componentizado = render_site_with_builder

from backend.agents.arquiteto_mestre import gerar_arquiteto_mestre_prd


def _pipeline_phase_key(fase_num: int, label: str = "") -> str:
    return _pipeline_phase_key_impl(fase_num, label)


def _set_pipeline_job_phase(
    config: dict | None, tenant_id: int, fase: str, label: str = ""
) -> None:
    """Persist current pipeline phase so refresh/status can reconstruct progress."""
    try:
        _set_pipeline_job_phase_impl(engine, config, tenant_id, fase, label)
    except Exception:
        pass


_ARQUITETO_AGENT = False
from pipeline_runtime_utils import (
    _COOLDOWN_POR_PLANO,
)
from pipeline_runtime_utils import (
    emitir_erro_pipeline as _emitir_erro_pipeline,
)
from retry_helper import tentar

from backend.services.credits_manager import (
    consumir_credito_diario,
    trial_credit_waits_for_sdr_delivery,
    validar_permissao_pipeline,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])
logger = logging.getLogger("uvicorn")
logger.addHandler(_sse_handler)


def _tenant_sdr_allowed(db: Session, tenant_id: int) -> bool:
    return _tenant_sdr_allowed_impl(db, tenant_id)


@dataclass
class FraLibState:
    segmento: str = ""
    cidade: str = ""
    pipeline_id: str = ""
    run_id: str = ""
    tenant_id: int = 0
    lead_raw_data: dict = field(default_factory=dict)
    lead_obj: Any = None
    lead_id: str = ""
    lead_nome: str = ""
    lead_slug: str = ""
    _inventory_id: str = ""  # Sprint 16: ID do lead_inventory para marcar error_retry
    qualificacao_caio: Any = None
    alex_result: Any = None
    jina_insights: str = ""
    briefing_theo: str = ""
    prd_arquiteto: Any = None
    html_sections: list[str] = field(default_factory=list)
    html_final: str = ""
    builder_output_dir: str = ""
    builder_manifest_path: str = ""
    liz_aprovado: bool = False
    liz_score: int = 0
    site_url: str = ""
    paleta_cores: dict = field(default_factory=dict)  # Sprint 14.x: cores para SDR
    refs_visuais: str = ""  # Sprint 14.x: referências visuais do usuário
    font_preferencia: str = (
        ""  # Sprint 14.x: preferência de fonte (sans-serif, serif, display, monospace)
    )
    keyword_research: str = ""
    direcao_criativa: Any = None  # Output do Design Director (tokens OKLch)


# Funções de sincronização de estado - delegam para módulos de serviços
def _sincronizar_segmento_state(state: FraLibState, segmento: str) -> None:
    """Delega para pipeline_phases para manter compatibilidade."""
    sincronizar_segmento_state(state, segmento)


def _aplicar_segmento_inferido(state: FraLibState, log_func=None) -> None:
    """Delega para pipeline_phases para manter compatibilidade."""
    aplicar_segmento_inferido(state, log_func, inferir_segmento_por_nome)


def _atualizar_pipeline_id_para_lead(
    state: FraLibState, tenant_id: int, queue_id: int = None
) -> None:
    """Delega para pipeline_state para manter compatibilidade."""
    atualizar_pipeline_id_para_lead(state, tenant_id, queue_id, log_legacy_queue_id)


async def executar_pipeline_completo(
    config: dict, tenant_id: int, queue_id: int = None, resume_from_phase: int = 0
):
    # Setar user_id no contexto do LLM pra rastrear consumo por usuario
    _run_id_context = str(config.get("_run_id") or uuid.uuid4().hex[:12])
    config["_run_id"] = _run_id_context
    set_llm_context_for_pipeline(
        tenant_id=tenant_id,
        run_id=_run_id_context,
        job_id=config.get("_job_id"),
    )

    _log = lambda msg, tipo="info", **kwargs: adicionar_log(
        msg, tipo, user_id=tenant_id
    )

    def _progress(fase_num, label):
        _phase_key = _pipeline_phase_key(fase_num, label)
        _set_pipeline_job_phase(config, tenant_id, _phase_key, label)
        adicionar_log(
            {
                "type": "progress",
                "event_kind": "pipeline_phase",
                "fase": fase_num,
                "phase": _phase_key,
                "total": 11,
                "label": label,
                "percent": round(min(fase_num, 11) / 11 * 100),
                "job_id": config.get("_job_id"),
                "run_id": _run_id_context,
            },
            "pipeline",
            user_id=tenant_id,
        )

    _fase_counter = [0]
    _span_manager = None

    def _iniciar_span_com_db(nome, agente, modelo="", fase_num=0):
        """Wrapper para SpanManager.iniciar_span_com_db."""
        if _span_manager:
            return _span_manager.iniciar_span_com_db(nome, agente, modelo, fase_num)
        return None

    def _finalizar_span_com_db(
        status,
        erro=None,
        duracao_ms=None,
        input_t=0,
        output_t=0,
        cache_r=0,
        cache_c=0,
        custo=0.0,
    ):
        """Wrapper para SpanManager.finalizar_span_com_db."""
        if _span_manager:
            _span_manager.finalizar_span_com_db(
                status, erro, duracao_ms, input_t, output_t, cache_r, cache_c, custo
            )

    def _validar_output(output, min_chars=50, must_contain=None):
        """Delega para pipeline_phases para manter compatibilidade."""
        return validar_output(output, min_chars, must_contain)

    state = FraLibState(
        segmento=config.get("segmento", ""),
        cidade=config.get("cidade", ""),
        pipeline_id=gerar_pipeline_id(
            tenant_id, config.get("segmento", ""), config.get("cidade", "")
        ),
        tenant_id=tenant_id,
    )
    state.run_id = _run_id_context
    _score_minimo = int(config.get("score_minimo", 45) or 45)
    # PRD #4: Token Tracker — rastreia custo LLM por run
    try:
        from agents.token_tracker import TokenTracker, set_tracker

        _token_tracker = TokenTracker(
            run_id=state.run_id,
            lead_nome="",  # preenchido após hunter
            nicho=state.segmento,
            tenant_id=tenant_id,
            job_id=config.get("_job_id"),
        )
        set_tracker(_token_tracker)
    except Exception:
        _token_tracker = None

    # PRD #6: Ledger Pattern — documento vivo do pipeline
    try:
        from pipeline_ledger import FaseStatus, Ledger, salvar_ledger

        _ledger = Ledger(run_id=state.run_id)
        _ledger.atualizar_fact("segmento", state.segmento)
        _ledger.atualizar_fact("cidade", state.cidade)
        _ledger.atualizar_fact("nicho", state.segmento)
    except Exception:
        _ledger = None

    # PRD #10: Observability — trace completo do pipeline + spans por fase
    try:
        from observability import (
            Trace,
            atualizar_heartbeat_span,
            finalizar_span,
            formatar_trace_log,
            salvar_span,
            salvar_trace,
        )

        _trace = Trace(run_id=state.run_id, nicho=state.segmento)
    except Exception:
        _trace = None
        salvar_span = None
        finalizar_span = None
        atualizar_heartbeat_span = None

    # Inicializar SpanManager para trace com DB
    from backend.endpoints.pipeline_trace_helpers import SpanManager

    _span_manager = SpanManager(
        trace=_trace,
        salvar_span=salvar_span,
        finalizar_span=finalizar_span,
        state=state,
        tenant_id=tenant_id,
        atualizar_heartbeat_span=atualizar_heartbeat_span,
    )
    if _token_tracker:
        _span_manager.set_token_tracker(_token_tracker)

    # PRD #11: Memory Tiered — agentes aprendem entre gerações
    try:
        from agent_memory import ColdMemory, CoreMemory, WarmMemory

        _memory_core = CoreMemory()
        _memory_warm = WarmMemory()
        _memory_cold = ColdMemory()
    except Exception:
        _memory_core = None
        _memory_warm = None
        _memory_cold = None

    # ─── HEARTBEAT DAEMON: atualiza span + job periodicamente ───
    from backend.endpoints.pipeline_heartbeat import HeartbeatManager

    _heartbeat_manager = HeartbeatManager(
        run_id=state.run_id,
        tenant_id=tenant_id,
        engine=engine,
        fase_counter=_fase_counter,
        atualizar_heartbeat_span=atualizar_heartbeat_span,
    )
    _heartbeat_manager.start()

    def _heartbeat_loop():
        """Wrapper para HeartbeatManager (mantém interface)."""
        # Não usado diretamente

    def _parar_heartbeat():
        """Wrapper para HeartbeatManager.stop()."""
        _heartbeat_manager.stop()

    _log("PIPELINE v2 - FraLibState Orquestrador", "info")
    _log(f"{state.segmento} em {state.cidade}", "info")
    logger.info(f"[Pipeline] Iniciando: {state.segmento} em {state.cidade}")
    # Checkpoint: verificar se existe progresso anterior
    _ckpt_resumo = resumo_checkpoint(state.pipeline_id)
    if "nenhum" not in _ckpt_resumo:
        _log(f"♻️ Retomando pipeline: {_ckpt_resumo}", "info")
        logger.info(f"[Pipeline] Retomando de checkpoint: {_ckpt_resumo}")
    # Limpar traces residuais de execucoes anteriores
    import os as _os

    _trace_dir = os.getenv("PIPELINE_TRACE_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..",
        "logs",
        "pipeline_trace",
    )
    _os.makedirs(_trace_dir, exist_ok=True)
    for _tf in [
        "liz_resultado.json",
        "designer_prd.json",
        "theo_briefing.md",
        "builder_renderer_html.html",
    ]:
        _tp = f"{_trace_dir}/{_tf}"
        if _os.path.exists(_tp):
            _os.remove(_tp)
    print("[Pipeline] Traces residuais limpos")
    try:
        # ─── REPROCESSAMENTO: pular Hunter + Caio se lead já existe ───
        _lead_id_existente = config.get("_lead_id_existente")
        if _lead_id_existente:
            _log("REPROCESSAMENTO — pulando Hunter + Caio", "info")
            import json as _json_reproc

            from agents.caio import CaioOutput
            from utils.agente1_hunter_v2 import LeadRaw
            from utils.safe_lead_qualificado import safe_qualificar

            with engine.connect() as _conn_reproc:
                _row_reproc = _conn_reproc.execute(
                    text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
                    {"id": _lead_id_existente, "uid": tenant_id},
                ).fetchone()
            if not _row_reproc:
                raise Exception(f"Lead {_lead_id_existente} nao encontrado")
            _ld = dict(_row_reproc._mapping)
            _dados_r = _ld.get("dados_completos") or {}
            if isinstance(_dados_r, str):
                try:
                    _dados_r = _json_reproc.loads(_dados_r)
                except _json_reproc.JSONDecodeError:
                    _dados_r = {}
            _reviews_r = _dados_r.get("reviews") or []
            _lead_raw_r = LeadRaw(
                nome=_ld["nome"],
                cidade=_ld["cidade"],
                segmento=_ld.get("segmento") or state.segmento,
                telefone=_ld.get("telefone") or "",
                whatsapp=_ld.get("whatsapp") or "",
                rating=float(_ld.get("rating") or 0),
                total_avaliacoes=int(_ld.get("total_avaliacoes") or len(_reviews_r)),
                reviews=_reviews_r,
                fotos=_dados_r.get("fotos") or [],
                website=_ld.get("website") or _dados_r.get("website") or "",
                endereco=_ld.get("endereco") or _dados_r.get("endereco") or "",
                maps_url=_dados_r.get("maps_url") or "",
                horarios=_dados_r.get("horarios") or [],
                atributos=_dados_r.get("atributos") or [],
                servicos=_dados_r.get("servicos") or [],
            )
            state.lead_obj = safe_qualificar(_lead_raw_r, _ld, log_fn=_log)
            state.lead_nome = _ld["nome"]
            _slug_norm = (
                unicodedata.normalize("NFKD", state.lead_nome)
                .encode("ascii", "ignore")
                .decode("ascii")
            )
            state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm.lower()).strip("-")[
                :50
            ]
            state.lead_id = _lead_id_existente
            state._inventory_id = config.get("_inventory_id", "")
            _aplicar_segmento_inferido(state, _log)
            state.lead_raw_data = build_lead_raw_data(
                _lead_raw_r,
                default_segmento=state.segmento,
            )
            state.lead_raw_data["reviews"] = _reviews_r
            state.lead_raw_data["logo_url"] = _dados_r.get("logo_url")
            state.lead_raw_data["briefing"] = _ld.get(
                "observacoes", ""
            )  # Sprint 14.x: briefing do lead
            state.refs_visuais = _ld.get(
                "refs_visuais", ""
            )  # Sprint 14.x: referências visuais
            state.font_preferencia = _ld.get(
                "font_preferencia", ""
            )  # Sprint 14.x: preferência de fonte
            _aplicar_segmento_inferido(state, _log)
            _atualizar_pipeline_id_para_lead(state, tenant_id, queue_id)
            # Caio: pular — usar qualificação anterior
            state.qualificacao_caio = CaioOutput(
                qualificado=True,
                qualificacao="QUENTE",
                tier=state.lead_obj.tier or "STANDARD",
                score=state.lead_obj.score or 50,
                motivo="Reprocessamento — qualificação anterior mantida",
            )
            state.alex_result = None
            _log(
                f"  Lead: {state.lead_nome} | Caio: PULADO (tier={state.qualificacao_caio.tier})",
                "success",
            )
            # Unsplash — renovar fotos
            try:
                _fotos_u = buscar_fotos_unsplash(
                    state.segmento,
                    quantidade=8,
                    nome=state.lead_nome,
                    cidade=_ld["cidade"],
                    archetype=_visual_archetype_id(
                        state.segmento, state.lead_nome, _dados_r
                    ),
                )
                state.lead_raw_data["fotos"] = _fotos_u
                state.lead_raw_data["logo_url"] = None
                _log(f"  Fotos Unsplash: {len(_fotos_u)}", "success")
            except Exception as _eu:
                logger.warning(f"[Pipeline] Unsplash erro: {_eu}")
            # Forcar renovacao de caches se pedido
            if config.get("_forcar_renovacao"):
                import hashlib as _hl_r

                _cache_key_r = _hl_r.md5(
                    (state.segmento.lower() + _ld["cidade"].lower()).encode()
                ).hexdigest()[:12]
                _jina_file_r = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "agents",
                    "jina_cache",
                    f"jina_{_cache_key_r}.txt",
                )
                if _os.path.exists(_jina_file_r):
                    _os.remove(_jina_file_r)
                    _log("  Cache Jina invalidado", "info")
            # Reprocessamento: usar _executar_pipeline_a_partir_fase2 (mesmos agentes)
            if not getattr(state, "keyword_research", ""):
                try:
                    from agents.keyword_research import pesquisar_keywords_nicho

                    state.keyword_research = pesquisar_keywords_nicho(
                        state.segmento, state.lead_obj.lead.cidade, tenant_id=tenant_id
                    )
                except Exception as e:
                    # FIX CRÍTICO: silent failure - SEO do site pode estar incompleto
                    # sem qualquer alerta. Agora logamos para detectar falhas.
                    logger.error(
                        f"[Pipeline] Keyword research falhou: {e}. "
                        f"SEO do site estará incompleto."
                    )
                    state.keyword_research = ""
            await _executar_pipeline_a_partir_fase2(state, tenant_id, config)
            _parar_heartbeat()
            return {"sucesso": True, "lead": state.lead_nome}
        _progress(1, "Buscando leads...")
        _log("FASE 1: HUNTER + KEYWORD RESEARCH (paralelo)", "info")
        if _ledger:
            _ledger.registrar_inicio_fase(1, "hunter_kw")
        _span = _iniciar_span_com_db("hunter_kw", agente="hunter") if _trace else None
        # Carregar leads não reutilizáveis. Capturados/pendentes entram no pool
        # do Hunter para evitar scraping novo e manter a pipeline andando.
        with engine.connect() as _conn_dedup:
            _res_existentes = _conn_dedup.execute(
                text("""
                SELECT lower(trim(nome)) FROM leads
                WHERE lower(cidade) = lower(:cidade)
                  AND user_id = :user_id
                  AND COALESCE(status, '') IN ('processando','concluido','contatado','deployed','erro')
            """),
                {"cidade": state.cidade, "user_id": tenant_id},
            )
            _leads_existentes = {row[0] for row in _res_existentes.fetchall()}
        if _leads_existentes:
            _log(f"  Dedup: {len(_leads_existentes)} leads ja existem no banco", "info")

        # Keyword research em paralelo com o Hunter (cache 30 dias)
        from concurrent.futures import ThreadPoolExecutor as _KWExec

        from agents.keyword_research import pesquisar_keywords_nicho

        _kw_result = [None]

        def _run_kw():
            try:
                _kw_result[0] = pesquisar_keywords_nicho(
                    state.segmento, state.cidade, tenant_id=tenant_id
                )
                _log("  Keywords: OK", "success")
            except Exception as _e:
                logger.warning(f"[Pipeline] Keyword research erro: {_e}")

        _kw_executor = _KWExec(max_workers=1)
        _kw_future = _kw_executor.submit(_run_kw)

        leads = await buscar_leads_google_maps(
            cidade=state.cidade,
            segmento=state.segmento,
            limite=config.get("_candidate_pool_limit", 10),
            leads_existentes=_leads_existentes,
            force_fresh=config.get("force_fresh", False),
            user_id=tenant_id,
            score_minimo=_score_minimo,
            aprovados_necessarios=1,
        )
        _kw_future.result(timeout=30)  # aguarda keyword research terminar
        _kw_executor.shutdown(wait=False)
        state.keyword_research = _kw_result[0] or ""
        if not leads:
            raise Exception(
                "Nenhum lead novo encontrado para '"
                + state.segmento
                + "' em '"
                + state.cidade
                + "'. Os leads dessa regiao ja estao sendo processados ou nao ha negocios com dados suficientes. Tente outro nicho ou cidade."
            )

        # Salvar leads capturados no banco com status 'capturado'
        # Limitar salvamento pela quantidade solicitada (trial=1, starter=10, etc)
        import json as _json_hunter

        _agora_hunter = datetime.now().isoformat()
        _salvos_hunter = 0
        _max_salvar = config.get("quantidade", 10)
        with engine.connect() as _conn_hunter:
            for _lq in leads:
                if _salvos_hunter >= _max_salvar:
                    break
                _l = _lq.lead
                _nome_norm_h = _l.nome.lower().strip() if _l.nome else ""
                if not _nome_norm_h:
                    continue
                # Checar se já existe (qualquer status)
                _dup_h = _conn_hunter.execute(
                    text("""
                    SELECT id FROM leads
                    WHERE lower(trim(nome)) = lower(trim(:nome))
                      AND lower(cidade) = lower(:cidade)
                      AND user_id = :user_id
                    LIMIT 1
                """),
                    {
                        "nome": _l.nome,
                        "cidade": _l.cidade or state.cidade,
                        "user_id": tenant_id,
                    },
                ).fetchone()
                if _dup_h:
                    continue
                _id_h = str(uuid.uuid4())
                _dados_h = {
                    "endereco": getattr(_l, "endereco", "")
                    or getattr(_l, "address", "")
                    or "",
                    "horarios": getattr(_l, "horarios", []) or [],
                    "maps_url": getattr(_l, "maps_url", None) or "",
                    "atributos": getattr(_l, "atributos", []) or [],
                    "servicos": getattr(_l, "servicos", []) or [],
                    "faixa_preco": getattr(_l, "faixa_preco", None) or "",
                    "website": getattr(_l, "website", "") or "",
                    "total_avaliacoes": getattr(_l, "total_avaliacoes", 0) or 0,
                    "google_maps_embed": getattr(_l, "google_maps_embed", "") or "",
                    "fotos": getattr(_l, "fotos", []) or [],
                    "reviews": [
                        {
                            "autor": r.get("autor", ""),
                            "rating": r.get("rating", 5),
                            "texto": r.get("texto", ""),
                        }
                        for r in (getattr(_l, "reviews", []) or [])
                    ],
                }
                try:
                    _conn_hunter.execute(
                        text("""
                        INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
                        VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
                        ON CONFLICT DO NOTHING
                    """),
                        {
                            "id": _id_h,
                            "nome": _l.nome,
                            "cidade": _l.cidade or state.cidade,
                            "segmento": _l.segmento or state.segmento,
                            "telefone": getattr(_l, "telefone", "") or "",
                            "whatsapp": getattr(_l, "whatsapp", "") or "",
                            "rating": getattr(_l, "rating", 0.0) or 0.0,
                            "score": _lq.score,
                            "tier": _lq.tier,
                            "status": "capturado",
                            "user_id": tenant_id,
                            "criado_em": _agora_hunter,
                            "atualizado_em": _agora_hunter,
                            "processado": False,
                            "tentativas": 0,
                            "dados_completos": _json_hunter.dumps(_dados_h),
                        },
                    )
                    _salvos_hunter += 1
                except Exception as _eh:
                    print(f"[Hunter] Erro ao salvar lead pendente {_l.nome}: {_eh}")
            _conn_hunter.commit()
        if _salvos_hunter:
            print(f"[Hunter] {_salvos_hunter} leads salvos como pendente no banco")

        state.lead_obj = leads[0]
        state.lead_nome = state.lead_obj.lead.nome
        if state.lead_obj.caio_resultado:
            from agents.caio import CaioOutput

            state.qualificacao_caio = CaioOutput(**state.lead_obj.caio_resultado)
        _aplicar_segmento_inferido(state, _log)
        # GUARD: se checkpoint tem dados de outro lead, limpar pra evitar contaminação
        _ckpt_lead_check = get_dados_agente(state.pipeline_id, "arquiteto_mestre")
        if _ckpt_lead_check and _ckpt_lead_check.get("prd_json"):
            _ckpt_bname = _ckpt_lead_check["prd_json"].get("business_name", "")
            if (
                _ckpt_bname
                and _ckpt_bname.lower().strip() != state.lead_nome.lower().strip()
            ):
                print(
                    f"[Pipeline] ⚠️ Checkpoint de outro lead ({_ckpt_bname}) — limpando pra {state.lead_nome}"
                )
                limpar_checkpoint(state.pipeline_id)
        _slug_norm = (
            unicodedata.normalize("NFKD", state.lead_nome)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm.lower()).strip("-")[:50]
        _reviews_raw = list(state.lead_obj.lead.reviews or [])
        state.lead_raw_data = build_lead_raw_data(
            state.lead_obj.lead,
            default_segmento=state.segmento,
        )
        state.lead_raw_data["reviews"] = _reviews_raw
        _log(f"  Lead: {state.lead_nome}", "success")
        state.lead_id = str(uuid.uuid4())
        agora = datetime.now().isoformat()
        with engine.connect() as conn:
            # Checar duplicata por nome+cidade+user_id antes de inserir
            _dup = conn.execute(
                text("""
                SELECT id FROM leads
                WHERE lower(trim(nome)) = lower(trim(:nome))
                  AND lower(cidade) = lower(:cidade)
                  AND user_id = :user_id
                LIMIT 1
            """),
                {
                    "nome": state.lead_nome,
                    "cidade": state.lead_obj.lead.cidade,
                    "user_id": tenant_id,
                },
            ).fetchone()
            if _dup:
                # Se lead existe com status pendente, foi salvo pelo Hunter agora — usar ele
                _status_dup = conn.execute(
                    text("SELECT status FROM leads WHERE id = :id AND user_id = :uid"),
                    {"id": str(_dup[0]), "uid": tenant_id},
                ).fetchone()
                if _status_dup and _status_dup[0] in ("pendente", "capturado"):
                    # Lead pendente salvo pelo Hunter — reutilizar diretamente
                    print(
                        f"[Pipeline] Lead pendente reutilizado: {state.lead_nome} (id: {_dup[0]})"
                    )
                    _log(f"  Lead: {state.lead_nome}", "success")
                    state.lead_id = str(_dup[0])
                    # Atualizar reviews/dados se o lead antigo não tinha
                    _fresh_reviews = [
                        {
                            "autor": r.get("autor", ""),
                            "rating": r.get("rating", 5),
                            "texto": r.get("texto", ""),
                        }
                        for r in (getattr(state.lead_obj.lead, "reviews", []) or [])
                    ]
                    if _fresh_reviews:
                        import json as _json_reutil

                        conn.execute(
                            text("""
                            UPDATE leads SET dados_completos = jsonb_set(
                                COALESCE(CAST(dados_completos AS jsonb), CAST('{}' AS jsonb)),
                                '{reviews}', CAST(:reviews AS jsonb)
                            ) WHERE id = :id AND user_id = :uid AND (CAST(dados_completos AS jsonb)->'reviews' = CAST('[]' AS jsonb) OR CAST(dados_completos AS jsonb)->'reviews' IS NULL)
                        """),
                            {
                                "id": state.lead_id,
                                "uid": tenant_id,
                                "reviews": _json_reutil.dumps(_fresh_reviews),
                            },
                        )
                        conn.commit()
                    _fresh_address = getattr(state.lead_obj.lead, "endereco", "") or ""
                    if _fresh_address:
                        conn.execute(
                            text("""
                            UPDATE leads SET dados_completos = jsonb_set(
                                COALESCE(CAST(dados_completos AS jsonb), CAST('{}' AS jsonb)),
                                '{endereco}', to_jsonb(CAST(:endereco AS text))
                            ) WHERE id = :id AND user_id = :uid
                              AND COALESCE(CAST(dados_completos AS jsonb)->>'endereco', '') = ''
                        """),
                            {
                                "id": state.lead_id,
                                "uid": tenant_id,
                                "endereco": _fresh_address,
                            },
                        )
                        conn.commit()
                else:
                    _log(f"  Lead duplicado ignorado: {state.lead_nome}", "info")
                    print(
                        f"[Pipeline] Lead duplicado ignorado: {state.lead_nome} (id existente: {_dup[0]})"
                    )
                    # Tentar proximo lead da lista em vez de abortar
                    _idx_dup = (
                        leads.index(state.lead_obj) if state.lead_obj in leads else 0
                    )
                    _proximo_valido = None
                    for _lq_dup in leads[_idx_dup + 1 :]:
                        _dup2 = conn.execute(
                            text("""
                            SELECT id FROM leads
                            WHERE lower(trim(nome)) = lower(trim(:nome))
                              AND lower(cidade) = lower(:cidade)
                              AND user_id = :user_id
                              AND status IN ('concluido', 'processando')
                            LIMIT 1
                        """),
                            {
                                "nome": _lq_dup.lead.nome,
                                "cidade": _lq_dup.lead.cidade,
                                "user_id": tenant_id,
                            },
                        ).fetchone()
                        if not _dup2:
                            _proximo_valido = _lq_dup
                            break
                    if not _proximo_valido:
                        _erro_sem_lead = "Todos os leads sao duplicatas"
                        _log(
                            "Todos os leads ja foram processados anteriormente",
                            "warning",
                        )
                        print(
                            "[Pipeline] Todos os leads sao duplicatas — nada a processar"
                        )
                        if _span:
                            _finalizar_span_com_db("skipped", erro=_erro_sem_lead)
                        _parar_heartbeat()
                        return {
                            "sucesso": False,
                            "fase": "hunter",
                            "erro": _erro_sem_lead,
                        }
                    # Redirecionar para o proximo lead valido
                    state.lead_obj = _proximo_valido
                    state.lead_nome = _proximo_valido.lead.nome
                    _slug_norm2 = (
                        unicodedata.normalize("NFKD", state.lead_nome)
                        .encode("ascii", "ignore")
                        .decode("ascii")
                    )
                    state.lead_slug = re.sub(
                        r"[^a-z0-9]+", "-", _slug_norm2.lower()
                    ).strip("-")[:50]
                    _reviews_raw2 = list(_proximo_valido.lead.reviews or [])
                    state.lead_raw_data = build_lead_raw_data(
                        _proximo_valido.lead,
                        default_segmento=state.segmento,
                    )
                    state.lead_raw_data["reviews"] = _reviews_raw2
                    # Buscar ID existente no banco para este lead (salvo pelo Hunter)
                    _id_existente = conn.execute(
                        text("""
                        SELECT id FROM leads
                        WHERE lower(trim(nome)) = lower(trim(:nome))
                          AND lower(cidade) = lower(:cidade)
                          AND user_id = :user_id
                        LIMIT 1
                    """),
                        {
                            "nome": state.lead_nome,
                            "cidade": _proximo_valido.lead.cidade,
                            "user_id": tenant_id,
                        },
                    ).fetchone()
                    state.lead_id = (
                        str(_id_existente[0]) if _id_existente else str(uuid.uuid4())
                    )
                    _log(f"  Redirecionando para: {state.lead_nome}", "info")
                    print(
                        f"[Pipeline] Redirecionando para proximo lead: {state.lead_nome} (id={state.lead_id})"
                    )
            import json as _json

            _dados_extras = {
                "endereco": state.lead_raw_data.get("endereco", ""),
                "horarios": getattr(state.lead_obj.lead, "horarios", []) or [],
                "maps_url": getattr(state.lead_obj.lead, "maps_url", None) or "",
                "atributos": getattr(state.lead_obj.lead, "atributos", []) or [],
                "servicos": getattr(state.lead_obj.lead, "servicos", []) or [],
                "faixa_preco": getattr(state.lead_obj.lead, "faixa_preco", None) or "",
                "website": state.lead_raw_data.get("website", ""),
                "total_avaliacoes": state.lead_raw_data.get("total_avaliacoes", 0),
            }
            conn.execute(
                text("""
                INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
                VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
                ON CONFLICT DO NOTHING
            """),
                {
                    "id": state.lead_id,
                    "nome": state.lead_nome,
                    "cidade": state.lead_obj.lead.cidade,
                    "segmento": state.lead_obj.lead.segmento,
                    "telefone": state.lead_obj.lead.telefone or "",
                    "whatsapp": state.lead_obj.lead.whatsapp or "",
                    "rating": state.lead_obj.lead.rating or 0.0,
                    "score": state.lead_obj.score,
                    "tier": state.lead_obj.tier,
                    "status": "capturado",
                    "user_id": tenant_id,
                    "dados_completos": _json.dumps(_dados_extras),
                    "criado_em": agora,
                    "atualizado_em": agora,
                    "processado": False,
                    "tentativas": 0,
                },
            )
            conn.commit()
        _aplicar_segmento_inferido(state, _log)
        _atualizar_pipeline_id_para_lead(state, tenant_id, queue_id)
        _progress(2, "Qualificando lead...")
        _log("FASE 2: CURADORIA (Caio ja validado no Hunter)", "info")
        if _ledger:
            _ledger.registrar_fim_fase(
                1, FaseStatus.CONCLUIDA, resultado=f"lead={state.lead_nome}"
            )
            _ledger.atualizar_fact("lead_nome", state.lead_nome)
            _ledger.atualizar_fact("lead_telefone", state.lead_obj.lead.telefone or "")
            _ledger.atualizar_fact(
                "lead_endereco", getattr(state.lead_obj.lead, "endereco", "")
            )
            _ledger.atualizar_fact("tem_reviews", bool(state.lead_obj.lead.reviews))
            _ledger.atualizar_fact(
                "qtd_reviews", state.lead_obj.lead.total_avaliacoes or 0
            )
            _ledger.atualizar_fact("tem_site", bool(state.lead_obj.lead.website))
            _ledger.registrar_inicio_fase(2, "caio")
        if _span:
            _finalizar_span_com_db("success")
        if _trace:
            _trace.lead_nome = state.lead_nome
            _span = _iniciar_span_com_db("caio", agente="caio", modelo="haiku")

        # Check rápido: lead já contatado? (evita gastar tokens gerando site pra lead repetido)
        try:
            with engine.connect() as _conn_dup:
                _ja_contatado = _conn_dup.execute(
                    text(
                        "SELECT id FROM leads WHERE lower(trim(nome))=lower(trim(:nome)) AND user_id=:uid AND status IN ('contatado','concluido')"
                    ),
                    {"nome": state.lead_nome, "uid": tenant_id},
                ).fetchone()
            if _ja_contatado:
                _log(
                    f"  {state.lead_nome} já contatado anteriormente — pulando",
                    "warning",
                )
                # Simular rejeição do Caio pra entrar no loop de fallback
                from agents.caio import CaioOutput as _CaioOut

                state.qualificacao_caio = _CaioOut(
                    qualificado=False,
                    tier="REJEITADO",
                    score=0,
                    razoes=["Lead já contatado anteriormente"],
                )
                # Pular direto pro bloco de fallback (não chamar Caio)
                if _span:
                    _finalizar_span_com_db("skipped")
                # Jump handled below by the rejection fallback block
            else:
                raise StopIteration  # flag: não é duplicado, continuar normalmente
        except StopIteration:
            pass
        except Exception as _dup_err:
            print(f"[Pipeline] Check duplicado falhou (ignorando): {_dup_err}")

        # ═══ PARALELIZAÇÃO: Caio + Jina em paralelo ═══
        # Ambos usam apenas dados básicos do lead (nome, cidade, segmento)
        # Agentes seguintes (Nicho) precisam de ambos os resultados
        _jina_cached = (
            None
            if config.get("_forcar_renovacao") or config.get("_cold_run")
            else get_dados_agente(state.pipeline_id, "jina")
        )

        async def _run_caio_async():
            """Executa Caio para qualificar o lead."""
            if state.qualificacao_caio:
                return state.qualificacao_caio
            caio_input = CaioInput(
                nome=state.lead_nome,
                cidade=state.lead_obj.lead.cidade,
                segmento=state.segmento,
                telefone=state.lead_obj.lead.telefone or "",
                whatsapp=state.lead_obj.lead.whatsapp or "",
                rating=state.lead_obj.lead.rating or 0.0,
                reviews_count=state.lead_obj.lead.total_avaliacoes
                or len(state.lead_obj.lead.reviews or [])
                or 0,
                fotos=state.lead_obj.lead.fotos or [],
                website=state.lead_obj.lead.website,
                reprocessamento=True,
            )

            def _run_caio():
                r = qualificar_lead(caio_input)
                logger.info(f"[Pipeline] Caio: {r.qualificacao}")
                return r

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as ex:
                return await loop.run_in_executor(ex, _run_caio)

        async def _run_jina_async():
            """Executa Jina para pesquisa de mercado (paralelo com Caio)."""
            if _jina_cached and _jina_cached.get("insights"):
                return {
                    "insights": _jina_cached["insights"],
                    "intel": _jina_cached.get("intel") or {},
                    "cached": True,
                }
            try:
                from utils.playwright_intel import (
                    formatar_inteligencia_para_arquiteto,
                )
                from utils.playwright_intel_safe import buscar_inteligencia_mercado_safe

                # FASE H5: Playwright Sync API nao roda nem em ThreadPoolExecutor
                # quando ha asyncio loop no parent thread. Usa subprocess Python
                # isolado via utils.playwright_intel_safe para garantir
                # zero interferencia de event loop.
                _safe_result = await asyncio.to_thread(
                    buscar_inteligencia_mercado_safe,
                    nicho=state.segmento,
                    cidade=state.cidade,
                    nome_negocio=state.lead_nome if hasattr(state, "lead_nome") else "",
                    concorrentes_urls=getattr(state, "_concorrentes_urls", None),
                )
                if _safe_result.get("ok"):
                    _intel = _safe_result["intel"]
                else:
                    raise RuntimeError(
                        _safe_result.get("error", "subprocess Playwright falhou")
                    )
                _insights = formatar_inteligencia_para_arquiteto(_intel)
                logger.info(f"[Pipeline] Playwright Intel: OK ({len(_insights)} chars)")
                return {
                    "insights": _insights,
                    "intel": _intel,
                    "cached": False,
                }
            except Exception as e:
                # FAIL-CLOSED: Playwright eh a fonte canonica. Sem fallback.
                logger.warning(f"[Pipeline] Playwright Intel erro: {e}")
                return {
                    "insights": "",
                    "intel": {},
                    "cached": False,
                    "error": str(e),
                }

        # Executar Caio + Jina em PARALELO
        _log("FASE 2+3: CAIO + JINA (paralelo)", "info")
        if _ledger:
            _ledger.registrar_inicio_fase(2, "caio_jina_parallel")

        _caio_result, _jina_result = await asyncio.gather(
            _run_caio_async(),
            _run_jina_async(),
        )

        # Aplicar resultados
        state.qualificacao_caio = _caio_result
        state.alex_result = None

        if _jina_result.get("cached"):
            state.jina_insights = _jina_result["insights"]
            state.jina_intel_dict = _jina_result.get("intel") or {}
            _log(f"  Jina: ♻️ cache hit ({len(state.jina_insights)} chars)", "success")
        elif _jina_result.get("fallback"):
            state.jina_insights = _jina_result["insights"]
            state.jina_intel_dict = {}
            _log(f"  Jina fallback v1: {len(state.jina_insights)} chars", "warning")
        elif _jina_result.get("error"):
            state.jina_insights = ""
            state.jina_intel_dict = {}
            _log("  Jina: erro - continuando sem insights", "warning")
        else:
            state.jina_insights = _jina_result["insights"]
            state.jina_intel_dict = _jina_result.get("intel") or {}
            if _validar_output(state.jina_insights, min_chars=30):
                salvar_checkpoint(
                    state.pipeline_id,
                    "jina",
                    {"insights": state.jina_insights, "intel": state.jina_intel_dict},
                )

        if _ledger:
            _ledger.registrar_fim_fase(
                2,
                FaseStatus.CONCLUIDA,
                resultado=f"caio={state.qualificacao_caio.qualificacao} jina={len(state.jina_insights)}chars",
            )
        if (
            state.qualificacao_caio
            and state.qualificacao_caio.qualificado
            and int(getattr(state.qualificacao_caio, "score", 0) or 0) < _score_minimo
        ):
            state.qualificacao_caio.qualificado = False
            state.qualificacao_caio.tier = "REJEITADO"
            state.qualificacao_caio.motivo = f"Score {getattr(state.qualificacao_caio, 'score', 0)} abaixo do minimo configurado ({_score_minimo})"
        if state.qualificacao_caio and (
            not state.qualificacao_caio.qualificado
            or state.qualificacao_caio.tier == "REJEITADO"
        ):
            _idx_atual = next(
                (i for i, l in enumerate(leads) if l is state.lead_obj), -1
            )
            _encontrou_aprovado = False
            _motivos_rejeicao = [
                {
                    "nome": state.lead_nome,
                    "motivo": getattr(state.qualificacao_caio, "motivo", None)
                    or "Rejeitado pelo Caio",
                }
            ]
            for _try_idx in range(_idx_atual + 1, min(_idx_atual + 16, len(leads))):
                _proximo = leads[_try_idx]
                _log(
                    f"  {state.lead_nome} rejeitado. Tentando: {_proximo.lead.nome}",
                    "info",
                )
                with engine.connect() as _conn_rej:
                    _conn_rej.execute(
                        text(
                            "UPDATE leads SET status='descartado', atualizado_em=:ts WHERE id=:id AND user_id=:uid"
                        ),
                        {
                            "ts": datetime.now().isoformat(),
                            "id": state.lead_id,
                            "uid": state.tenant_id,
                        },
                    )
                    _conn_rej.commit()
                state.lead_obj = _proximo
                state.lead_nome = _proximo.lead.nome
                _slug_norm_caio = (
                    unicodedata.normalize("NFKD", state.lead_nome)
                    .encode("ascii", "ignore")
                    .decode("ascii")
                )
                state.lead_slug = re.sub(
                    r"[^a-z0-9]+", "-", _slug_norm_caio.lower()
                ).strip("-")[:50]
                state.lead_id = None
                _rvs = list(_proximo.lead.reviews or [])
                state.lead_raw_data = {
                    "nome": _proximo.lead.nome,
                    "cidade": _proximo.lead.cidade,
                    "segmento": _proximo.lead.segmento,
                    "telefone": _proximo.lead.telefone or "",
                    "whatsapp": _proximo.lead.whatsapp or "",
                    "rating": _proximo.lead.rating or 0.0,
                    "reviews": _rvs,
                    "total_avaliacoes": getattr(_proximo.lead, "total_avaliacoes", None)
                    or getattr(_proximo.lead, "reviews_count", None)
                    or len(_rvs),
                    "fotos": _proximo.lead.fotos or [],
                    "website": _proximo.lead.website or "",
                    "logo_url": getattr(_proximo.lead, "logo_url", None) or "",
                    "endereco": getattr(_proximo.lead, "endereco", "")
                    or getattr(_proximo.lead, "address", "")
                    or "",
                    "google_maps_embed": getattr(_proximo.lead, "google_maps_embed", "")
                    or "",
                    "lat": getattr(_proximo.lead, "latitude", None),
                    "lng": getattr(_proximo.lead, "longitude", None),
                    "horarios": getattr(_proximo.lead, "horarios", None),
                    "atributos": getattr(_proximo.lead, "atributos", None),
                    "servicos": getattr(_proximo.lead, "servicos", None),
                    "faixa_preco": getattr(_proximo.lead, "faixa_preco", None),
                }
                _aplicar_segmento_inferido(state, _log)
                from agents.caio import (
                    LeadInput as _CaioInput2,
                )
                from agents.caio import (
                    qualificar_lead as _qualificar_caio2,
                )

                _caio_input2 = _CaioInput2(
                    nome=_proximo.lead.nome,
                    cidade=_proximo.lead.cidade,
                    segmento=state.segmento,
                    telefone=_proximo.lead.telefone or "",
                    whatsapp=_proximo.lead.whatsapp or "",
                    rating=_proximo.lead.rating or 0.0,
                    reviews_count=getattr(_proximo.lead, "total_avaliacoes", None)
                    or len(getattr(_proximo.lead, "reviews", None) or [])
                    or 0,
                    fotos=_proximo.lead.fotos or [],
                    website=_proximo.lead.website,
                    reprocessamento=True,
                )
                state.qualificacao_caio = (
                    await asyncio.get_event_loop().run_in_executor(
                        None, _qualificar_caio2, _caio_input2
                    )
                )
                if (
                    state.qualificacao_caio
                    and state.qualificacao_caio.qualificado
                    and int(getattr(state.qualificacao_caio, "score", 0) or 0)
                    < _score_minimo
                ):
                    state.qualificacao_caio.qualificado = False
                    state.qualificacao_caio.tier = "REJEITADO"
                    state.qualificacao_caio.motivo = f"Score {getattr(state.qualificacao_caio, 'score', 0)} abaixo do minimo configurado ({_score_minimo})"
                if (
                    state.qualificacao_caio
                    and state.qualificacao_caio.qualificado
                    and state.qualificacao_caio.tier != "REJEITADO"
                ):
                    _encontrou_aprovado = True
                    _log(
                        f"  Lead aprovado: {state.lead_nome} ({state.qualificacao_caio.tier})",
                        "success",
                    )
                    break
                else:
                    _motivo = (
                        getattr(state.qualificacao_caio, "motivo", None)
                        if state.qualificacao_caio
                        else "Rejeitado"
                    )
                    _motivos_rejeicao.append(
                        {"nome": _proximo.lead.nome, "motivo": _motivo}
                    )
            if not _encontrou_aprovado:
                _detalhes = [
                    f"{m['nome']} — {m['motivo']}" for m in _motivos_rejeicao[:8]
                ]
                _emitir_erro_pipeline(
                    _log,
                    tenant_id,
                    "NO_LEADS",
                    message=f"Todos os negócios encontrados para {state.segmento} em {state.cidade} foram descartados.",
                    detalhes=_detalhes,
                )
                raise Exception(
                    "Nenhum lead qualificado encontrado para '"
                    + state.segmento
                    + "' em '"
                    + state.cidade
                    + "'. "
                    + str(len(_motivos_rejeicao))
                    + " leads avaliados e rejeitados."
                )
            if _encontrou_aprovado:
                state.lead_id = str(uuid.uuid4())
                _agora_sub = datetime.now().isoformat()
                try:
                    import json as _json_sub

                    _dados_extras_sub = {
                        "endereco": getattr(_proximo.lead, "endereco", "")
                        or getattr(_proximo.lead, "address", "")
                        or "",
                        "horarios": getattr(_proximo.lead, "horarios", []) or [],
                        "maps_url": getattr(_proximo.lead, "maps_url", None) or "",
                        "atributos": getattr(_proximo.lead, "atributos", []) or [],
                        "servicos": getattr(_proximo.lead, "servicos", []) or [],
                        "faixa_preco": getattr(_proximo.lead, "faixa_preco", None)
                        or "",
                        "website": state.lead_raw_data.get("website", ""),
                        "total_avaliacoes": state.lead_raw_data.get(
                            "total_avaliacoes", 0
                        ),
                    }
                    with engine.connect() as _conn_sub:
                        _dup_sub = _conn_sub.execute(
                            text(
                                "SELECT id FROM leads WHERE lower(trim(nome)) = lower(trim(:nome)) AND lower(cidade) = lower(:cidade) AND user_id = :user_id LIMIT 1"
                            ),
                            {
                                "nome": state.lead_nome,
                                "cidade": _proximo.lead.cidade,
                                "user_id": tenant_id,
                            },
                        ).fetchone()
                        if _dup_sub:
                            state.lead_id = _dup_sub[0]
                        else:
                            _conn_sub.execute(
                                text(
                                    "INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos) VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos) ON CONFLICT DO NOTHING"
                                ),
                                {
                                    "id": state.lead_id,
                                    "nome": state.lead_nome,
                                    "cidade": _proximo.lead.cidade,
                                    "segmento": state.segmento,
                                    "telefone": _proximo.lead.telefone or "",
                                    "whatsapp": _proximo.lead.whatsapp or "",
                                    "rating": _proximo.lead.rating or 0.0,
                                    "score": state.qualificacao_caio.score,
                                    "tier": state.qualificacao_caio.tier,
                                    "status": "capturado",
                                    "user_id": tenant_id,
                                    "dados_completos": _json_sub.dumps(
                                        _dados_extras_sub
                                    ),
                                    "criado_em": _agora_sub,
                                    "atualizado_em": _agora_sub,
                                    "processado": False,
                                    "tentativas": 0,
                                },
                            )
                            _conn_sub.commit()
                except Exception as _e_sub:
                    pass
                _aplicar_segmento_inferido(state, _log)
                _atualizar_pipeline_id_para_lead(state, tenant_id, queue_id)
        _log(
            f"  Caio: {state.qualificacao_caio.qualificacao} score={state.qualificacao_caio.score}",
            "success",
        )
        logger.info(f"[Pipeline] Caio: {state.qualificacao_caio.qualificacao}")
        logger.info("[Pipeline] Multimidia: OK")
        if _ledger:
            _ledger.registrar_fim_fase(
                2,
                FaseStatus.CONCLUIDA,
                resultado=f"score={state.qualificacao_caio.score} tier={state.qualificacao_caio.tier}",
            )
            _ledger.atualizar_fact("score_qualificacao", state.qualificacao_caio.score)
            _ledger.atualizar_fact("tier", state.qualificacao_caio.tier)
        if _span:
            _finalizar_span_com_db("success")

        # ═══ FASE 2.5: DESIGN DIRECTOR — Decide direção criativa com tokens OKLch ═══
        # Chamado APÓS Caio (lead qualificado) para gerar direção única por lead
        # Design Director internamente chama design_context.get_design_context() primeiro
        _log("FASE 2.5: DESIGN DIRECTOR (tokens OKLch)", "info")
        try:
            from backend.agents.design_director import gerar_direcao_criativa

            # Verificar se já existe checkpoint do Design Director
            _dd_cached = (
                None
                if config.get("_forcar_renovacao") or config.get("_cold_run")
                else get_dados_agente(state.pipeline_id, "design_director")
            )
            if _dd_cached and _dd_cached.get("direcao_criativa"):
                state.direcao_criativa = _dd_cached["direcao_criativa"]
                _log("  Design Director: ♻️ retomado do checkpoint", "success")
            else:
                # Chamar Design Director com dados do lead qualificado
                state.direcao_criativa = gerar_direcao_criativa(
                    nicho=state.segmento
                    or state.lead_obj.lead.segmento
                    or "negocio local",
                    cidade=state.cidade or state.lead_obj.lead.cidade or "",
                    nome_negocio=state.lead_nome,
                    rating=float(state.lead_obj.lead.rating or 0),
                    segment=state.segmento,
                    tier=(
                        state.qualificacao_caio.tier
                        if state.qualificacao_caio
                        else "STANDARD"
                    ),
                    dados_lead=state.lead_raw_data,
                )
                # Salvar checkpoint
                salvar_checkpoint(
                    state.pipeline_id,
                    "design_director",
                    {"direcao_criativa": state.direcao_criativa},
                )
            _dd_dir = state.direcao_criativa.get("direcao_visual", {}).get(
                "estilo", "N/A"
            )
            _dd_tokens = state.direcao_criativa.get("design_tokens", {})
            _dd_source = _dd_tokens.get("source", "N/A") if _dd_tokens else "sem tokens"
            _log(
                f"  Design Director: estilo={_dd_dir} | tokens={_dd_source}",
                "success",
            )
            logger.info(
                f"[Pipeline] Design Director: dir={_dd_dir}, tokens_source={_dd_source}"
            )
        except Exception as _dd_err:
            logger.warning(
                f"[Pipeline] Design Director erro (continuando sem): {_dd_err}"
            )
            state.direcao_criativa = None

        # PRD #7: Agent Router — modelo dinâmico por complexidade
        try:
            from agent_router import AgentRouter, calcular_complexidade_lead, set_router

            _router_facts = {
                "qtd_reviews": state.lead_raw_data.get("total_avaliacoes", 0),
                "nicho": state.segmento,
                "tier": state.qualificacao_caio.tier
                if state.qualificacao_caio
                else "STANDARD",
                "tem_site": bool(state.lead_raw_data.get("website")),
                "servicos": state.lead_raw_data.get("servicos") or [],
            }
            _complexidade = calcular_complexidade_lead(_router_facts)
            _router = AgentRouter(_complexidade)
            set_router(_router)
            print(_router.resumo())
            if _ledger:
                _ledger.atualizar_fact("complexidade", _complexidade)
                _ledger.registrar_decisao(
                    2, f"routing_{_complexidade}", "Modelos ajustados por complexidade"
                )
        except Exception as _router_err:
            print(f"[ROUTER] Erro (fallback medio): {_router_err}")
            _router = None
            _complexidade = "medio"
        # PRD #11: Ativar memória no thread pra call_claude injetar automaticamente
        if _memory_core and _memory_warm:
            try:
                from agent_memory import set_memory

                set_memory(_memory_core, _memory_warm, state.segmento)
            except Exception:
                pass
        # ═══ JINA JÁ EXECUTADO EM PARALELO COM CAIO (acima) ═══
        # Skip old sequential Jina block - jina_insights already populated
        _log("FASE 3: JINA AI (skip - executado em paralelo)", "info")
        if _ledger:
            _ledger.registrar_inicio_fase(3, "jina_parallel")
            if state.jina_insights:
                _ledger.registrar_fim_fase(
                    3,
                    FaseStatus.CONCLUIDA,
                    resultado=f"{len(state.jina_insights)} chars",
                )
            else:
                _ledger.registrar_fim_fase(3, FaseStatus.PULADA, erro="sem resultado")
        _log(f"  Jina: {len(state.jina_insights)} chars", "success")

        # ═══ MÓDULO DE INTELIGÊNCIA + CURADORIA ═══
        _progress(4, "Analisando concorrência...")
        _log("FASE 4: INTELIGÊNCIA DE MERCADO", "info")
        try:
            await prepare_lead_intelligence_assets(
                state=state,
                config=config,
                logger=logger,
                _visual_archetype_id=_visual_archetype_id,
                buscar_fotos_unsplash=buscar_fotos_unsplash,
                buscar_videos_pexels=buscar_videos_pexels,
            )
        except Exception as _intel_err:
            print(f"[Pipeline] Módulo inteligência erro (não-fatal): {_intel_err}")
            state.inteligencia = {}
        _progress(
            6,
            "Preparando prompt..."
            if _is_prompt_agent_flow(config)
            else "Analisando nicho...",
        )
        _prompt_agent_flow = _is_prompt_agent_flow(config)
        _builder_fast_path = _is_builder_fast_path(config) or _prompt_agent_flow
        if _prompt_agent_flow:
            print(
                "[Pipeline] Prompt Agent flow ativo: Hunter -> Caio -> Jina -> Prompt -> Builder -> Deploy"
            )
        elif _builder_fast_path:
            print(
                "[Pipeline] Builder fast-path ativo: pulando agentes de briefing/PRD LLM"
            )

        # ─── FASE 6: AGENTE DE NICHO ─────────────────────────────────
        _progress(
            6, "Preparando prompt..." if _prompt_agent_flow else "Analisando nicho..."
        )
        _log(
            "FASE 6: AGENTE DE PROMPT (NICHO PULADO)"
            if _prompt_agent_flow
            else "FASE 6: AGENTE DE NICHO",
            "info",
        )
        if _ledger:
            _n_fotos = len(state.lead_raw_data.get("fotos", []))
            _ledger.registrar_fim_fase(
                5, FaseStatus.CONCLUIDA, resultado=f"{_n_fotos} fotos"
            )
            _ledger.atualizar_fact("fotos_disponiveis", _n_fotos)
            _ledger.registrar_inicio_fase(6, "agente_nicho", modelo="sonnet")
        if _span:
            _finalizar_span_com_db("success")
        _span = (
            _iniciar_span_com_db("agente_nicho", agente="agente_nicho", modelo="sonnet")
            if _trace
            else None
        )
        _nicho_cached = (
            None
            if config.get("_forcar_renovacao") or config.get("_cold_run")
            else get_dados_agente(state.pipeline_id, "agente_nicho")
        )
        if _builder_fast_path:
            from agents.handoff_types import NichoBriefing

            state.nicho_briefing = NichoBriefing(
                task_id=state.pipeline_id,
                source_agent="pipeline",
                target_agent="builder_renderer",
                nicho=state.segmento or state.lead_obj.lead.segmento or "negocio local",
                cidade=state.cidade or state.lead_obj.lead.cidade or "",
                confianca="media",
                refs_visuais=state.refs_visuais,  # Sprint 14.x: referências visuais
                font_preferencia=state.font_preferencia,  # Sprint 14.x: preferência de fonte
            )
            _log(
                "  Nicho: pulado; dados seguem direto para o Agente de Prompt"
                if _prompt_agent_flow
                else "  Nicho: fast-path deterministico (sem LLM)",
                "success",
            )
        elif _nicho_cached and _nicho_cached.get("briefing_json"):
            try:
                from agents.handoff_types import NichoBriefing

                state.nicho_briefing = NichoBriefing(**_nicho_cached["briefing_json"])
                _log("  Nicho briefing: ♻️ retomado do checkpoint", "success")
            except Exception:
                _nicho_cached = None
        if not _builder_fast_path and (
            not _nicho_cached or not _nicho_cached.get("briefing_json")
        ):
            from agents.agente_nicho import gerar_briefing

            _dados_hunter = state.lead_raw_data or {}
            state.nicho_briefing = gerar_briefing(
                dados_lead=_dados_hunter,
                segmento=state.segmento,
                cidade=state.cidade,
                jina_insights=state.jina_insights or "",
                task_id=state.pipeline_id,
                refs_visuais=state.refs_visuais,  # Sprint 14.x: referências visuais
                font_preferencia=state.font_preferencia,  # Sprint 14.x: preferência de fonte
            )
            _log(
                f"  Nicho: {state.nicho_briefing.nicho} | confianca={state.nicho_briefing.confianca}",
                "success",
            )
            try:
                salvar_checkpoint(
                    state.pipeline_id,
                    "agente_nicho",
                    {"briefing_json": state.nicho_briefing.model_dump()},
                )
            except Exception:
                pass
        if _span:
            _finalizar_span_com_db("success")

        # ─── FASE 7: AGENTE DE VARIAÇÃO ESTRUTURAL ───────────────────
        _progress(
            7,
            "Mantendo Builder livre..."
            if _prompt_agent_flow
            else "Definindo variação estrutural...",
        )
        _log(
            "FASE 7: AGENTE DE PROMPT (VARIAÇÃO PULADA)"
            if _prompt_agent_flow
            else "FASE 7: AGENTE DE VARIAÇÃO",
            "info",
        )
        if _ledger:
            _ledger.registrar_fim_fase(6, FaseStatus.CONCLUIDA)
            _ledger.registrar_inicio_fase(7, "agente_variacao", modelo="haiku")
        _span_var = (
            _iniciar_span_com_db(
                "agente_variacao", agente="agente_variacao", modelo="haiku"
            )
            if _trace
            else None
        )
        _var_cached = (
            None
            if config.get("_forcar_renovacao") or config.get("_cold_run")
            else get_dados_agente(state.pipeline_id, "agente_variacao")
        )
        if _builder_fast_path:
            from agents.handoff_types import VariacaoEstrutural

            state.variacao_estrutural = VariacaoEstrutural(
                task_id=state.pipeline_id,
                source_agent="pipeline",
                target_agent="builder_renderer",
                template_estrutura="skill-fast",
                template_hero="renderer-decides",
                ordem_das_secoes=[
                    "hero",
                    "sobre",
                    "prova-social",
                    "contato",
                    "footer",
                ],
            )
            _log(
                "  Variação: pulada; estrutura sera pedida no prompt final"
                if _prompt_agent_flow
                else "  Variação: fast-path deterministica (sem LLM)",
                "success",
            )
        elif _var_cached and _var_cached.get("variacao_json"):
            try:
                from agents.handoff_types import VariacaoEstrutural

                state.variacao_estrutural = VariacaoEstrutural(
                    **_var_cached["variacao_json"]
                )
                _log("  Variação: ♻️ retomado do checkpoint", "success")
            except Exception:
                _var_cached = None
        if not _builder_fast_path and (
            not _var_cached or not _var_cached.get("variacao_json")
        ):
            from agents.agente_variacao import gerar_variacao

            _conc_raw = state.jina_insights or ""
            state.variacao_estrutural = gerar_variacao(
                nicho_briefing=state.nicho_briefing,
                concorrentes_raw=_conc_raw[:3000],
                task_id=state.pipeline_id,
            )
            _log(
                f"  Variação: {state.variacao_estrutural.template_estrutura}/{state.variacao_estrutural.template_hero}",
                "success",
            )
            try:
                salvar_checkpoint(
                    state.pipeline_id,
                    "agente_variacao",
                    {"variacao_json": state.variacao_estrutural.model_dump()},
                )
            except Exception:
                pass
        if _span_var:
            _span_var.finalizar("success")
        if finalizar_span and getattr(state, "pipeline_id", None):
            finalizar_span(
                run_id=state.run_id,
                fase_num=_fase_counter[0],
                status="success",
                duracao_ms=_span_var.duracao_ms if _span_var else None,
                input_tokens=_span_var.input_tokens if _span_var else 0,
                output_tokens=_span_var.output_tokens if _span_var else 0,
                cache_read_tokens=_span_var.cache_hit_tokens if _span_var else 0,
                custo_usd=_span_var.custo_usd if _span_var else 0.0,
            )

        # ─── FASE 8: ARQUITETO MESTRE ─────────────────────────────────
        _progress(
            8,
            "Montando prompt completo..."
            if _prompt_agent_flow
            else "Arquitetando site...",
        )
        _log(
            "FASE 8: AGENTE DE PROMPT"
            if _prompt_agent_flow
            else "FASE 8: ARQUITETO MESTRE",
            "info",
        )
        if _ledger:
            _ledger.registrar_fim_fase(7, FaseStatus.CONCLUIDA)
            _ledger.registrar_inicio_fase(8, "arquiteto_mestre", modelo="sonnet")
        if _span:
            _finalizar_span_com_db("success")
        _span = (
            _iniciar_span_com_db(
                "arquiteto_mestre", agente="arquiteto_mestre", modelo="sonnet"
            )
            if _trace
            else None
        )
        _arq_cached = (
            None
            if config.get("_forcar_renovacao") or config.get("_cold_run")
            else get_dados_agente(state.pipeline_id, "arquiteto_mestre")
        )
        if _prompt_agent_flow:
            state.prd_arquiteto = _build_prompt_agent_prd(state, tenant_id)
            _arq_cached = {"prd_json": True}
            _log(
                f"  Prompt: {len(state.prd_arquiteto.builder_prompt):,} chars para o Builder",
                "success",
            )
        elif _builder_fast_path:
            state.prd_arquiteto = _build_skill_fast_prd(state)
            _arq_cached = {"prd_json": True}
            _log("  PRD: fast-path factual compacto (sem LLM)", "success")
        elif _arq_cached and _arq_cached.get("prd_json"):
            # Retomar PRD do checkpoint
            from designer_prd import DesignerPRD as PRDOutput

            try:
                state.prd_arquiteto = PRDOutput(**_arq_cached["prd_json"])
                _log(
                    f"  PRD: ♻️ retomado do checkpoint ({len(state.prd_arquiteto.sections)} seções)",
                    "success",
                )
            except Exception as _prd_err:
                _log(f"  ⚠️ Checkpoint PRD inválido, regenerando: {_prd_err}", "warning")
                _arq_cached = None
        if not _builder_fast_path and (
            not _arq_cached or not _arq_cached.get("prd_json")
        ):
            _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
            random.seed(_seed)
            _pool = [
                "mask-reveal",
                "counter-animation",
                "parallax-scroll",
                "stagger-fade",
                "reveal-on-scroll",
                "text-split",
                "floating-cards",
                "elastic-scale",
                "wave-animation",
                "spotlight-hover",
                "tilt-3d",
                "fade-up",
                "slide-in",
                "zoom-reveal",
            ]
            random.sample(_pool, 6)
            _seg = state.segmento or state.lead_obj.lead.segmento or "negocio local"
            _cid = state.lead_obj.lead.cidade or state.cidade or ""
            _prd_fn = gerar_arquiteto_mestre_prd
            with _temporary_prd_cache_disabled(
                bool(config.get("_forcar_renovacao") or config.get("_cold_run"))
            ):
                state.prd_arquiteto = tentar(
                    lambda: _prd_fn(
                        dados_hunter=state.lead_raw_data,
                        cidade=_cid,
                        segmento=_seg,
                        jina_insights=state.jina_insights,
                        briefing_theo=state.briefing_theo,
                        caio_tier=state.qualificacao_caio.tier
                        if state.qualificacao_caio
                        else "STANDARD",
                        caio_score=state.qualificacao_caio.score
                        if state.qualificacao_caio
                        else 0,
                        caio_motivo=state.qualificacao_caio.motivo
                        if state.qualificacao_caio
                        else "",
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
                    log_fn=_log,
                )
            _log(f"  PRD: {len(state.prd_arquiteto.sections)} secoes", "success")
            # Salvar checkpoint do PRD (fase cara em tokens antes do renderer final)
            try:
                _prd_dict = (
                    state.prd_arquiteto.model_dump()
                    if hasattr(state.prd_arquiteto, "model_dump")
                    else state.prd_arquiteto.__dict__
                )
                if _validar_output(str(_prd_dict), min_chars=200):
                    salvar_checkpoint(
                        state.pipeline_id, "arquiteto_mestre", {"prd_json": _prd_dict}
                    )
                else:
                    _log("  ⚠️ PRD output truncado — não salvou checkpoint", "warning")
            except Exception as _ckpt_e:
                print(f"[Checkpoint] PRD save skip: {_ckpt_e}")
        # White-label: verificar se tenant tem plano PRO (remove branding FraLib do footer)
        try:
            with engine.connect() as _wl_conn:
                _wl_row = _wl_conn.execute(
                    text("SELECT plano FROM users WHERE id=:uid"), {"uid": tenant_id}
                ).fetchone()
                if _wl_row and _wl_row[0] in ("pro", "enterprise"):
                    state.prd_arquiteto.white_label = True
        except Exception:
            pass
        try:
            _ensure_prd_publication_identity(state.prd_arquiteto, state, tenant_id)
        except Exception as _pub_err:
            logger.warning(f"[Pipeline] publication identity skip: {_pub_err}")
        if _prompt_agent_flow:
            _log("  Contracts antigos: desativados no fluxo Agente de Prompt", "info")
        else:
            # Forcar google_maps_embed curado no PRD.
            state.prd_arquiteto.google_maps_embed = state.lead_raw_data.get(
                "google_maps_embed", ""
            )
            print(
                f"[Pipeline] Maps embed injetado no PRD: {len(state.prd_arquiteto.google_maps_embed)} chars"
            )
            try:
                _pack_id = _ensure_prd_design_reference(state.prd_arquiteto, state)
                if _pack_id:
                    _log(f"  Design reference pack: {_pack_id}", "success")
                _ensure_prd_contracts(state.prd_arquiteto, state)
                _ensure_prd_publication_identity(state.prd_arquiteto, state, tenant_id)
                _log("  Contracts: requirements + visual OK", "info")
            except Exception as _pack_err:
                logger.warning(f"[Pipeline] Design reference pack skip: {_pack_err}")

        # Sprint 14.x: injetar paleta_cores do nicho_briefing no PRD
        # para o renderer usar cores solicitadas pelo usuário ("cores roxo e branco")
        try:
            if (
                hasattr(state, "nicho_briefing")
                and state.nicho_briefing
                and hasattr(state.nicho_briefing, "paleta_cores")
            ):
                _pc = getattr(state.nicho_briefing, "paleta_cores", None)
                if _pc and isinstance(_pc, dict) and _pc.get("primary"):
                    state.prd_arquiteto.paleta_cores = _pc
                    state.paleta_cores = _pc  # Sprint 14.x: para propagar ao SDR
                    print(f"[Pipeline] paleta_cores injetada no PRD: {_pc}")
        except Exception as _pc_err:
            print(f"[Pipeline] paleta_cores injeção falhou: {_pc_err}")

        # Salvar PRD no trace para auditoria
        try:
            import json as _json

            _trace_dir = os.getenv("PIPELINE_TRACE_DIR") or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "..",
                "logs",
                "pipeline_trace",
            )
            _os.makedirs(_trace_dir, exist_ok=True)
            with open(f"{_trace_dir}/designer_prd.json", "w", encoding="utf-8") as _pf:
                _json.dump(
                    state.prd_arquiteto.model_dump()
                    if hasattr(state.prd_arquiteto, "model_dump")
                    else state.prd_arquiteto.__dict__,
                    _pf,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
        except Exception as _pe:
            print(f"[Pipeline] PRD trace skip: {_pe}")
        _renderer_agent = "builder_renderer"
        _renderer_label = "BUILDER RENDERER"
        _progress(9, "Gerando site no Builder...")
        _log(f"FASE 9: {_renderer_label}", "info")
        if _ledger:
            _ledger.registrar_fim_fase(8, FaseStatus.CONCLUIDA, resultado="PRD gerado")
            _ledger.registrar_inicio_fase(
                9,
                _renderer_agent,
                modelo=os.getenv("FRALIB_BUILDER_MODEL", "sonnet"),
            )
        if _span:
            _finalizar_span_com_db("success")
        _span = (
            _iniciar_span_com_db(
                _renderer_agent,
                agente=_renderer_agent,
                modelo=os.getenv("FRALIB_BUILDER_MODEL", "sonnet"),
            )
            if _trace
            else None
        )
        if not state.prd_arquiteto:
            raise Exception(f"PRD nao disponivel para {_renderer_agent}")
        _renderer_cached = (
            None
            if config.get("_forcar_renovacao") or config.get("_cold_run")
            else get_dados_agente(state.pipeline_id, _renderer_agent)
        )
        if (
            _renderer_cached
            and _renderer_cached.get("html_final")
            and len(_renderer_cached["html_final"]) >= 500
        ):
            state.html_final = _renderer_cached["html_final"]
            _log(
                f"  HTML: ♻️ retomado do checkpoint ({len(state.html_final):,} chars)",
                "success",
            )
        else:
            # Injetar segmento/fotos no PRD para o renderer final
            if (
                not hasattr(state.prd_arquiteto, "segmento")
                or not state.prd_arquiteto.segmento
            ):
                state.prd_arquiteto.segmento = state.segmento
            if (
                hasattr(state.prd_arquiteto, "photos")
                and not state.prd_arquiteto.photos
            ):
                state.prd_arquiteto.photos = state.lead_raw_data.get("fotos") or []
            _log(f"  Gerador: {_renderer_agent}", "info")

            def _gerar_html_renderer(
                _validation_errors: str = "", _previous_html: str = ""
            ):
                _repair_context = None
                _repair_hash = ""
                if _validation_errors or _previous_html:
                    _repair_context = {
                        "validation_errors": _validation_errors,
                        "previous_html": _previous_html,
                    }
                    _repair_hash = hashlib.sha1(
                        f"{_validation_errors}\n{_previous_html[:2000]}".encode(
                            "utf-8", errors="ignore"
                        )
                    ).hexdigest()[:10]
                _job_id = _builder_job_id_for_state(state, config, _repair_hash)
                _result = render_site_with_builder(
                    state.prd_arquiteto,
                    tenant_id=tenant_id,
                    job_id=_job_id,
                    repair_context=_repair_context,
                    publication_url=f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/",
                )
                state.builder_output_dir = _result.get("output_dir", "")
                state.builder_manifest_path = _result.get("manifest_path", "")

                # Sprint 14.6: log da geracao no site_generation_log
                # para o proximo lead do mesmo subnicho pegar variation diferente.
                try:
                    from backend.services.site_generation_counter import (
                        hash_color_palette,
                        log_generation,
                    )

                    _variation_log = (
                        getattr(state.prd_arquiteto, "variation", None) or {}
                    )
                    if isinstance(_variation_log, dict) and _variation_log:
                        log_generation(
                            tenant_id=tenant_id,
                            lead_id=str(getattr(state, "lead_id", "") or _job_id),
                            subnicho=str(
                                getattr(state.prd_arquiteto, "subnicho", None)
                                or getattr(state, "subniche", None)
                                or state.segmento
                                or ""
                            ),
                            segmento=state.segmento or "",
                            layout_variant=str(
                                _variation_log.get("layout_variant") or ""
                            )[:20],
                            motion_variant=str(
                                _variation_log.get("motion_variant") or ""
                            )[:20],
                            copy_variant=str(_variation_log.get("copy_variant") or "")[
                                :20
                            ],
                            color_palette_hash=hash_color_palette(
                                getattr(state.prd_arquiteto, "color_palette", None)
                            ),
                            hero_classes=str(_variation_log.get("hero_classes") or "")[
                                :2000
                            ],
                            section_order=list(
                                _variation_log.get("section_order") or []
                            ),
                        )
                except Exception as _log_err:
                    logger.debug(f"[Sprint 14.6] log_generation falhou: {_log_err}")

                return _result["html"]

            state.html_final = tentar(
                lambda: _gerar_html_renderer(),
                fase=_renderer_agent,
                max_attempts=1,
                base_delay=3.0,
                log_fn=_log,
            )
            if not state.html_final or len(state.html_final) < 500:
                raise Exception(f"{_renderer_agent} retornou HTML vazio")
            try:
                open(
                    os.path.join(_trace_dir, f"{_renderer_agent}_sections.html"),
                    "w",
                    encoding="utf-8",
                ).write(state.html_final)
            except Exception as e:
                # FIX CRÍTICO: escrita de debug em disco pode falhar
                # (permissao, disco cheio, diretorio invalido)
                # Apenas logamos - nao queremos quebrar o pipeline por isso
                logger.warning(f"[Pipeline] Falha ao salvar debug HTML: {e}")

            # ── Gate determinístico: SEMPRE executa, não pode ser pulado ──
            # FRALIB_SKIP_HTML_QUALITY_GATE só pula validador LLM opcional,
            # nunca o gate determinístico (html_quality_gate.py)
            if _skip_deterministic_gate(config):
                _log(
                    f"  {_renderer_label}: gate determinístico DESATIVADO (NUNCA deveria acontecer)",
                    "error",
                )
            try:
                from agents.html_quality_gate import (
                    HtmlQualityGateError,
                    normalize_generated_html_for_publication,
                    sanitize_builder_html_for_publication,
                    validate_generated_html,
                )
            except Exception:
                from html_quality_gate import (
                    HtmlQualityGateError,
                    normalize_generated_html_for_publication,
                    sanitize_builder_html_for_publication,
                    validate_generated_html,
                )

            _max_repair_attempts = 3
            for _repair_attempt in range(1, _max_repair_attempts + 1):
                try:
                    state.html_final = sanitize_builder_html_for_publication(
                        state.html_final, state.prd_arquiteto
                    )
                    validate_generated_html(state.html_final, state.prd_arquiteto)
                    break
                except HtmlQualityGateError as exc:
                    _persist_failed_renderer_html(state, exc, _renderer_agent)
                    if _repair_attempt >= _max_repair_attempts:
                        raise

                    # PATCH-FIRST: tentar resolver problemas com patches diretos antes de rebuild
                    _log(
                        f"  {_renderer_label}: quality gate falhou; tentando patch primeiro",
                        "warning",
                    )
                    _original_html = state.html_final

                    # Aplicar normalização adicional + sanitização novamente
                    try:
                        state.html_final = normalize_generated_html_for_publication(
                            state.html_final, state.prd_arquiteto
                        )
                        state.html_final = sanitize_builder_html_for_publication(
                            state.html_final, state.prd_arquiteto
                        )
                        validate_generated_html(state.html_final, state.prd_arquiteto)
                        _log(
                            f"  {_renderer_label}: patch resolveu problemas!", "success"
                        )
                        break
                    except HtmlQualityGateError:
                        # Patch não funcionou, mas não perdemos o HTML original
                        # Agora sim faz rebuild, mas passa o HTML original como referência
                        _log(
                            f"  {_renderer_label}: patch insuficiente; rebuild com referência",
                            "warning",
                        )
                        state.html_final = _gerar_html_renderer(
                            _validation_errors=str(exc),
                            _previous_html=_original_html,  # Passa o original, não o html já modificado
                        )
            state.html_final = sanitize_builder_html_for_publication(
                state.html_final, state.prd_arquiteto
            )
            try:
                validate_generated_html(state.html_final, state.prd_arquiteto)
            except HtmlQualityGateError as exc:
                _persist_failed_renderer_html(state, exc, _renderer_agent)
                raise

            # FASE G: Quality Guardian → retry com feedback
            # Quando o QG bloqueia (decision=block), o orchestrator volta pro
            # builder passando as correcoes cirurgicas em linguagem natural.
            # Limite: 3 correcoes antes de desistir com erro claro.
            _quality_guardian_bypass = os.getenv(
                "FRALIB_QUALITY_GUARDIAN_BYPASS", ""
            ).strip().lower() in {"1", "true", "yes", "on"}
            try:
                from backend.agents.quality_guardian import (
                    render_correction_prompt,
                    run_quality_guardian,
                )
            except Exception as _qg_import_err:
                if _quality_guardian_bypass:
                    logger.warning(
                        "Quality Guardian indisponivel, mas bypass administrativo ativo; validacao ignorada.",
                        exc_info=True,
                    )
                    run_quality_guardian = None
                    render_correction_prompt = None
                else:
                    logger.critical(
                        "Falha ao carregar Quality Guardian; bloqueando finalizacao do job.",
                        exc_info=True,
                    )
                    raise RuntimeError(
                        "Quality Guardian indisponivel e bypass administrativo ausente"
                    ) from _qg_import_err

            if run_quality_guardian is not None:
                _max_qg_corrections = 3
                _qg_history: list[dict] = []
                for _qg_attempt in range(1, _max_qg_corrections + 1):
                    _qg_verdict = run_quality_guardian(
                        state.html_final,
                        is_fallback=bool(getattr(state, "is_fallback", False)),
                        has_template_fallback=bool(
                            getattr(state, "has_template_fallback", False)
                        ),
                        dados_incompletos=bool(
                            getattr(state, "dados_incompletos", False)
                        ),
                        design_context_failed=bool(
                            getattr(state, "design_context_failed", False)
                        ),
                        palette_overridden=bool(
                            getattr(state, "palette_overridden", False)
                        ),
                    )
                    _qg_history.append(
                        {
                            "attempt": _qg_attempt,
                            "score": _qg_verdict.overall_score,
                            "decision": _qg_verdict.decision,
                            "critical": _qg_verdict.critical_count,
                        }
                    )
                    _log(
                        f"  Quality Guardian #{_qg_attempt}: score={_qg_verdict.overall_score:.1f}/10 "
                        f"decision={_qg_verdict.decision} criticos={_qg_verdict.critical_count}",
                        "success" if _qg_verdict.decision == "deploy" else "warning",
                    )
                    if _qg_verdict.decision != "block":
                        state.qg_verdict = _qg_verdict
                        state.qg_history = _qg_history
                        break

                    if _qg_attempt >= _max_qg_corrections:
                        state.qg_verdict = _qg_verdict
                        state.qg_history = _qg_history
                        raise Exception(
                            f"Quality Guardian bloqueou apos {_qg_attempt} correcoes. "
                            f"Score final {_qg_verdict.overall_score:.1f}/10. "
                            f"Feedback: {_qg_verdict.feedback}"
                        )

                    _log(
                        f"  Quality Guardian bloqueou; pedindo correcao #{_qg_attempt} ao builder",
                        "warning",
                    )
                    _qg_prompt = (
                        render_correction_prompt(_qg_verdict.corrections)
                        if render_correction_prompt
                        else _qg_verdict.feedback
                    )
                    state.html_final = _gerar_html_renderer(
                        _validation_errors=_qg_prompt,
                        _previous_html=state.html_final,
                    )
                    state.html_final = sanitize_builder_html_for_publication(
                        state.html_final, state.prd_arquiteto
                    )

            # ── Validador LLM (Sonnet Haiku fallback) — score 0-10 + aprovado bool ──
            # v1.1-baseline-2026-06-23: reintroduzido no orchestrator para fechar
            # feedback loop Nicho↔Validador (Sprint 0).
            _validador_result = None
            if not _skip_html_quality_gate(config):
                try:
                    from agents.validador import validar

                    _prd_text = (
                        state.prd_arquiteto.model_dump_json()
                        if hasattr(state.prd_arquiteto, "model_dump_json")
                        else str(getattr(state.prd_arquiteto, "__dict__", {}))
                    )
                    _validador_result = validar(
                        html=state.html_final,
                        prd_text=_prd_text,
                        segmento=state.segmento or "",
                        task_id=str(state.pipeline_id),
                    )
                    _log(
                        f"  Validador LLM: score={_validador_result.score:.1f}/10 "
                        f"aprovado={_validador_result.aprovado}",
                        "success" if _validador_result.aprovado else "warning",
                    )
                    state.validador_result = _validador_result
                except Exception as _val_err:
                    _log(
                        f"  Validador LLM falhou (gate determinístico segue): {_val_err}",
                        "warning",
                    )
            else:
                _log(
                    f"  {_renderer_label}: validador LLM ignorado (FRALIB_SKIP_HTML_QUALITY_GATE=1)",
                    "warning",
                )

            # v1.1-baseline-2026-06-23: feedback loop Nicho↔Validador (Sprint 1).
            # Persiste lesson do briefing com score como multiplicador de confianca.
            if _validador_result is not None and getattr(state, "nicho_briefing", None):
                try:
                    from agents.memory_hook_site import persist_lesson_with_score

                    _briefing = state.nicho_briefing
                    _subnicho = (
                        getattr(_briefing, "subnicho", "")
                        or getattr(_briefing, "subnichos", [""])[0]
                        if getattr(_briefing, "subnichos", None)
                        else ""
                    )
                    persist_lesson_with_score(
                        agente="agente_nicho",
                        nicho=state.segmento or "default",
                        conteudo=(
                            f"Briefing subnicho={_subnicho} "
                            f"confianca_original={getattr(_briefing, 'confianca', 'media')} "
                            f"score={_validador_result.score:.1f}"
                        ),
                        validador_score=_validador_result.score,
                    )
                except Exception as _persist_err:
                    logger.warning(
                        f"[Pipeline] persist_lesson_with_score falhou: {_persist_err}"
                    )
            _log(f"  HTML: {len(state.html_final):,} chars", "success")
            logger.info(f"[Pipeline] {_renderer_label}: OK")
            # Validar HTML antes de salvar checkpoint (não salvar truncado)
            _html_valid = (
                len(state.html_final) >= 2000 and "</html>" in state.html_final.lower()
            )
            if _html_valid:
                salvar_checkpoint(
                    state.pipeline_id, _renderer_agent, {"html_final": state.html_final}
                )
            else:
                _log(
                    "  ⚠️ HTML incompleto (sem </html>) — não salvou checkpoint",
                    "warning",
                )
                raise Exception(
                    f"{_renderer_agent} gerou HTML truncado ({len(state.html_final)} chars, sem tag de fechamento)"
                )
        try:
            os.makedirs(
                os.path.join(_BASE, "..", "logs", "pipeline_trace"), exist_ok=True
            )
            with open(
                os.path.join(
                    _BASE,
                    "..",
                    "logs",
                    "pipeline_trace",
                    f"{_renderer_agent}_html.html",
                ),
                "w",
                encoding="utf-8",
            ) as _f:
                _f.write(state.html_final)
            print(f"[Trace] {_renderer_agent}_html.html salvo")
        except Exception:
            pass
        _progress(10, "Publicando site...")
        _log("FASE 10: DEPLOY", "info")
        if _ledger:
            _ledger.registrar_fim_fase(
                9, FaseStatus.CONCLUIDA, resultado=f"{len(state.html_final)} chars HTML"
            )
            _ledger.registrar_inicio_fase(10, "deploy")
        if _span:
            _finalizar_span_com_db("success")
        _span = _iniciar_span_com_db("deploy", agente="deploy") if _trace else None
        # PRD #8: salvar PRD no cache semantico apos renderer final
        if state.prd_arquiteto and not getattr(
            state.prd_arquiteto, "_cache_hit", False
        ):
            try:
                from design_context import get_design_context
                from prd_cache import salvar_prd_cache

                _dc_cache = get_design_context(state.segmento, state.lead_nome)
                _dir_cache = (
                    _dc_cache.get("direction", "default") if _dc_cache else "default"
                )
                _tier_cache = (
                    state.qualificacao_caio.tier
                    if state.qualificacao_caio
                    else "STANDARD"
                )
                _prd_dict = (
                    state.prd_arquiteto.model_dump()
                    if hasattr(state.prd_arquiteto, "model_dump")
                    else state.prd_arquiteto.__dict__
                )
                _sub_nicho_cache = (
                    _prd_dict.get("sub_nicho", {}).get("sub_nicho", "")
                    if isinstance(_prd_dict.get("sub_nicho"), dict)
                    else ""
                )
                salvar_prd_cache(
                    state.segmento,
                    _tier_cache,
                    _dir_cache,
                    _prd_dict,
                    state.lead_raw_data,
                    sub_nicho=_sub_nicho_cache,
                )
            except Exception as _cache_save_err:
                print(f"[CACHE] Erro ao salvar PRD: {_cache_save_err}")
        web_dir = f"/var/www/fralib/sites/{tenant_id}/{state.lead_slug}"
        os.makedirs(web_dir, exist_ok=True)
        try:
            from backend.services.builder_worker import (
                assert_canonical_builder_publication_allowed,
            )
        except Exception:
            from services.builder_worker import (
                assert_canonical_builder_publication_allowed,  # type: ignore
            )
        assert_canonical_builder_publication_allowed(
            state.builder_output_dir or web_dir,
            html=state.html_final,
        )
        if state.builder_output_dir:
            copy_builder_dist(state.builder_output_dir, web_dir)
        with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
            _f.write(state.html_final)
        # ── Gerar sitemap.xml + robots.txt ──
        try:
            from backend.agents.html_quality_gate import _gerar_sitemap_robots

            _gerar_sitemap_robots(
                state.html_final,
                state.prd_arquiteto,
                web_dir,
                f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/",
            )
        except Exception as _sitemap_err:
            print(f"[Pipeline] Erro sitemap/robots (nao-fatal): {_sitemap_err}")
        if state.alex_result and state.alex_result.assets_dir:
            assets_src = os.path.realpath(state.alex_result.assets_dir)
            assets_dst = os.path.realpath(f"{web_dir}/assets")
            if assets_src == assets_dst:
                # Site ja salvo direto no destino correto — nao fazer nada
                print(f"[Pipeline] Assets já no lugar: {assets_dst}")
            elif os.path.exists(assets_src):
                import shutil

                if os.path.exists(assets_dst):
                    shutil.rmtree(assets_dst)
                shutil.copytree(assets_src, assets_dst)
                print(f"[Pipeline] Assets copiados: {assets_src} -> {assets_dst}")
            else:
                print(f"[Pipeline] Assets src não encontrado: {assets_src}")
        import subprocess as _sp

        _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
        _sp.run(["chmod", "-R", "755", web_dir], check=False)
        state.site_url = (
            f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/"
        )
        _log(f"  Deploy: {state.site_url}", "success")
        logger.info(f"[Pipeline] Deploy: {state.site_url}")

        _progress(11, "Enviando contato...")
        _log("FASE 11: FRANZ", "info")
        if _ledger:
            _ledger.registrar_fim_fase(
                10, FaseStatus.CONCLUIDA, resultado=state.site_url
            )
            _ledger.registrar_inicio_fase(11, "franz", modelo="sonnet")
        if _span:
            _finalizar_span_com_db("success")
        _span = (
            _iniciar_span_com_db("franz", agente="franz", modelo="sonnet")
            if _trace
            else None
        )
        # O worker ainda entende bryan_outreach apenas para historico/fila antiga.
        _sdr_stage_final = "pendente_wpp"
        _sdr_allowed = False
        _skip_franz = bool(config.get("_skip_franz_outreach"))
        if _skip_franz:
            _sdr_stage_final = "manual_test_no_wpp"
            _log("  Franz: pulado por teste controlado sem WhatsApp", "info")
        try:
            if not _skip_franz:
                with SessionLocal() as _db_sdr_plan:
                    _sdr_allowed = _tenant_sdr_allowed(_db_sdr_plan, state.tenant_id)
        except Exception as _sdr_plan_err:
            logger.warning(f"[Pipeline] SDR plan gate falhou fechado: {_sdr_plan_err}")
        if not _skip_franz and not _sdr_allowed:
            _sdr_stage_final = "blocked_plan"
            _log("  Franz: bloqueado pelo plano atual", "info")
        try:
            if _skip_franz:
                raise RuntimeError("sdr_manual_test_blocked")
            if not _sdr_allowed:
                raise RuntimeError("sdr_plan_blocked")
            _franz_payload = {
                "nome": state.lead_nome,
                "cidade": state.lead_obj.lead.cidade,
                "segmento": state.segmento,
                "telefone": state.lead_obj.lead.telefone or "",
                "whatsapp": state.lead_obj.lead.whatsapp or "",
                "rating": state.lead_obj.lead.rating or 0.0,
                "site_url": state.site_url,
                "score_caio": state.qualificacao_caio.score
                if state.qualificacao_caio
                else 0,
                "tier": state.qualificacao_caio.tier
                if state.qualificacao_caio
                else "STANDARD",
                "proof": getattr(state.qualificacao_caio, "motivo", None)
                if state.qualificacao_caio
                else None,
                "lead_id": state.lead_id,
                "tenant_id": state.tenant_id,
                "_run_id": state.run_id,
                "_parent_job_id": config.get("_job_id"),
            }
            if config.get("_bryan_test_number"):
                _franz_payload["_bryan_test_number"] = str(
                    config.get("_bryan_test_number")
                )
            import job_queue as _jq_franz

            _db_franz = SessionLocal()
            try:
                _jq_franz.enqueue(
                    _db_franz,
                    tipo="franz_outreach",
                    payload=_franz_payload,
                    tenant_id=state.tenant_id,
                    max_attempts=5,
                    idempotency_key=f"franz-{state.lead_id}",
                    run_id=state.run_id,
                )
                _db_franz.close()
                _log("  Franz: enfileirado como job separado", "info")
                _sdr_stage_final = "pendente_wpp"
            except Exception:
                _db_franz.close()
                raise
        except Exception as e:
            if str(e) not in {"sdr_plan_blocked", "sdr_manual_test_blocked"}:
                logger.warning(f"[Pipeline] Franz enqueue erro (não bloqueia): {e}")
                _log(f"  Franz: falha ao enfileirar ({e}). Site gerado OK.", "warning")
                _sdr_stage_final = "sdr_enqueue_failed"
        with engine.connect() as conn:
            conn.execute(
                text("""
                UPDATE leads SET site_url=:url, url_site=:url, processado=true,
                processado_em=:ts, status='concluido', sdr_stage=:stage,
                paleta_cores=:cores,
                atualizado_em=:ts, erro_pipeline=NULL
                WHERE id=:id AND user_id=:uid
            """),
                {
                    "url": state.site_url,
                    "ts": datetime.now().isoformat(),
                    "id": state.lead_id,
                    "stage": _sdr_stage_final,
                    "uid": state.tenant_id,
                    "cores": json.dumps(state.paleta_cores)
                    if state.paleta_cores
                    else None,
                },
            )
            conn.commit()
        limpar_checkpoint(state.pipeline_id)
        _log("PIPELINE v2 CONCLUIDO - FraLibState OK", "success")
        import json as _json_complete

        adicionar_log(
            _json_complete.dumps(
                {
                    "type": "complete",
                    "url": state.site_url,
                    "lead_nome": state.lead_nome,
                }
            ),
            "PIPELINE_STATUS",
            user_id=tenant_id,
        )
        logger.info("[Pipeline] CONCLUIDO - 7 AGENTES!")

        # PRD #6: Ledger — finalizar e salvar
        if _ledger:
            _ledger.registrar_fim_fase(
                10, FaseStatus.CONCLUIDA, resultado="pipeline_completo"
            )
            print(_ledger.snapshot())
            salvar_ledger(_ledger)

        # PRD #10: Trace — finalizar e salvar
        if _span:
            _finalizar_span_com_db("success")
        if _trace:
            _trace.lead_nome = state.lead_nome
            _trace.tier = (
                state.qualificacao_caio.tier if state.qualificacao_caio else ""
            )
            _trace.complexidade = _complexidade if "_complexidade" in dir() else ""
            _trace.finalizar("success")
            print(formatar_trace_log(_trace))
            salvar_trace(_trace)

        # Parar heartbeat daemon
        _parar_heartbeat()

        # Pipeline learning: pequenas licoes aprovadas entram na memoria dos agentes.
        if _memory_warm:
            try:
                from agents.pipeline_learning import record_pipeline_success

                _visual_dna = getattr(state.prd_arquiteto, "visual_dna", {}) or {}
                _learned_count = record_pipeline_success(
                    _memory_warm,
                    nicho=state.segmento,
                    archetype=_visual_dna.get("archetype", ""),
                    renderer=_renderer_agent
                    if "_renderer_agent" in locals()
                    else "builder_renderer",
                    tier=state.qualificacao_caio.tier
                    if state.qualificacao_caio
                    else "",
                    site_url=state.site_url,
                )
                if _learned_count:
                    _log(f"  Learning: {_learned_count} padroes salvos", "info")
            except Exception as _learn_err:
                print(f"[Learning] sucesso nao registrado: {_learn_err}")

        # PRD #11: Memory — salvar cold + promoção periódica
        if _memory_cold:
            try:
                _memory_cold.salvar_run(
                    state.run_id,
                    {
                        "nicho": state.segmento,
                        "lead": state.lead_nome,
                        "tier": state.qualificacao_caio.tier
                        if state.qualificacao_caio
                        else "",
                        "liz_aprovado": state.liz_aprovado,
                        "site_url": state.site_url,
                    },
                )
            except Exception:
                pass
        if _memory_warm and _memory_core:
            try:
                _memory_warm.promover_para_core(_memory_core)
            except Exception:
                pass

        # PRD #4: Token Tracking — log + salvar no DB
        try:
            if _token_tracker:
                _token_tracker.lead_nome = state.lead_nome or ""
                from agents.token_tracker import (
                    log_tracking,
                    salvar_tracking,
                    set_tracker,
                )

                _resumo = _token_tracker.resumo()
                log_tracking(_resumo)
                salvar_tracking(_resumo)
                set_tracker(None)  # limpar tracker do thread
        except Exception as _track_err:
            print(f"[TRACKING] Erro: {_track_err}")

        # PRD #7: Limpar router do thread
        try:
            from agent_router import set_router

            set_router(None)
        except Exception:
            pass
        # PRD #11: Limpar memória do thread
        try:
            from agent_memory import clear_memory

            clear_memory()
        except Exception:
            pass

        # Descontar 1 crédito diário + marcar ultimo_deploy_at
        try:
            with SessionLocal() as _db_cred:
                if trial_credit_waits_for_sdr_delivery(_db_cred, tenant_id):
                    print(
                        f"[Pipeline] Trial aguardando envio SDR antes de consumir credito (tenant={tenant_id})"
                    )
                    _log("  Credito trial aguardando envio Franz confirmado", "info")
                else:
                    consumir_credito_diario(_db_cred, tenant_id, state.lead_nome)
                    print(f"[Pipeline] Credito diario consumido (tenant={tenant_id})")
        except Exception as _cred_err:
            print(f"[Pipeline] ERRO ao descontar credito: {_cred_err}")

        # Limpar checkpoints expirados (>24h)
        try:
            from agents.pipeline_checkpoint import limpar_checkpoints_expirados

            limpar_checkpoints_expirados(max_age_hours=24)
        except Exception:
            pass

        maybe_schedule_autorun_next_lead(
            db_factory=SessionLocal,
            tenant_id=tenant_id,
            cooldowns_by_plan=_COOLDOWN_POR_PLANO,
            logger=logger,
            log_fn=_log,
            run_next_lead_fn=executar_pipeline_lead_existente,
        )

        # Buscar leads extras em background pra fila de processamento
        _qtd_extra = config.get("quantidade", 1) - 1
        if _qtd_extra > 0:

            async def _buscar_extras():
                try:
                    _existentes_agora = set()
                    with engine.connect() as _c:
                        _r = _c.execute(
                            text(
                                "SELECT lower(trim(nome)) FROM leads WHERE lower(cidade)=lower(:c) AND user_id=:u AND status IN ('concluido', 'deployed', 'processando')"
                            ),
                            {"c": state.cidade, "u": tenant_id},
                        )
                        _existentes_agora = {row[0] for row in _r.fetchall()}
                    _extras = await buscar_leads_google_maps(
                        cidade=state.cidade,
                        segmento=state.segmento,
                        limite=_qtd_extra,
                        leads_existentes=_existentes_agora,
                        user_id=tenant_id,
                    )
                    if _extras:
                        import json as _jx

                        _agora = datetime.now().isoformat()
                        with engine.connect() as _cx:
                            for _lq in _extras:
                                _l = _lq.lead
                                _id = str(uuid.uuid4())
                                _dados = {
                                    "endereco": getattr(_l, "endereco", "")
                                    or getattr(_l, "address", "")
                                    or "",
                                    "reviews": [
                                        {
                                            "autor": r.get("autor", ""),
                                            "rating": r.get("rating", 5),
                                            "texto": r.get("texto", ""),
                                        }
                                        for r in (_l.reviews or [])
                                    ],
                                    "fotos": _l.fotos or [],
                                    "horarios": getattr(_l, "horarios", None),
                                    "servicos": getattr(_l, "servicos", None),
                                    "atributos": getattr(_l, "atributos", None),
                                }
                                _cx.execute(
                                    text(
                                        """INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos) VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,'capturado',:user_id,:criado_em,:atualizado_em,false,0,:dados_completos) ON CONFLICT DO NOTHING"""
                                    ),
                                    {
                                        "id": _id,
                                        "nome": _l.nome,
                                        "cidade": _l.cidade,
                                        "segmento": _l.segmento,
                                        "telefone": _l.telefone or "",
                                        "whatsapp": _l.whatsapp or "",
                                        "rating": _l.rating or 0.0,
                                        "score": _lq.score,
                                        "tier": _lq.tier,
                                        "user_id": tenant_id,
                                        "criado_em": _agora,
                                        "atualizado_em": _agora,
                                        "dados_completos": _jx.dumps(_dados),
                                    },
                                )
                            _cx.commit()
                        print(
                            f"[Pipeline] {len(_extras)} leads extras salvos na fila de processamento"
                        )
                except Exception as _ex:
                    logger.warning(f"[Pipeline] Busca extras erro: {_ex}")

            asyncio.create_task(_buscar_extras())

        # pipeline_queue e legado; conclusao operacional vem de jobs/pipeline_failures/leads.
        # Registrar execução concluída
        try:
            with engine.connect() as _conn_exec:
                _conn_exec.execute(
                    text("""
                    UPDATE pipeline_executions SET finished_at=NOW(), status='completed',
                           lead_id=:lid, lead_nome=:lnome
                    WHERE user_id=:uid AND status='running'
                    AND id = (SELECT id FROM pipeline_executions WHERE user_id=:uid AND status='running' ORDER BY started_at DESC LIMIT 1)
                """),
                    {"uid": tenant_id, "lid": state.lead_id, "lnome": state.lead_nome},
                )
                _conn_exec.commit()
        except Exception:
            pass
        return {"sucesso": True, "site_url": state.site_url, "lead": state.lead_nome}
    except Exception as e:
        # Detectar tipo de erro e emitir SSE tipado
        from llm_direct import RateLimitError

        _fase_erro = None
        if isinstance(e, RateLimitError):
            _reset_min = max(1, e.reset_seconds // 60)
            _emitir_erro_pipeline(
                _log,
                tenant_id,
                "RATE_LIMIT",
                message=f"Servidor de IA ocupado. Retomando em ~{_reset_min}min.",
                detalhes=["O sistema retoma automaticamente quando liberar."],
                eta_seconds=e.reset_seconds,
                auto_retry=True,
            )
            _log(
                f"⚠️ LIMITE DE USO ATINGIDO. Volte daqui {_reset_min} minuto(s).",
                "rate_limit",
            )
        elif (
            "NenhumLead" in type(e).__name__
            or "no leads" in str(e).lower()
            or "nenhum lead" in str(e).lower()
        ):
            _emitir_erro_pipeline(
                _log,
                tenant_id,
                "NO_LEADS",
                message=str(e),
                detalhes=getattr(e, "motivos", [])
                if hasattr(e, "motivos")
                else [str(e)],
            )
            _log(f"⚠️ {e!s}", "warning")
        elif (
            "deploy" in str(e).lower()
            or "nginx" in str(e).lower()
            or "filesystem" in str(e).lower()
        ):
            _fase_erro = "deploy"
            _emitir_erro_pipeline(
                _log,
                tenant_id,
                "DEPLOY_FAIL",
                message="Site gerado mas erro ao publicar no servidor.",
                detalhes=[str(e)[:200]],
            )
            _log(f"❌ Deploy falhou: {e!s}", "error")
        elif (
            "scraper" in str(e).lower()
            or "playwright" in str(e).lower()
            or "google maps" in str(e).lower()
        ):
            _emitir_erro_pipeline(
                _log,
                tenant_id,
                "SCRAPER_FAIL",
                message="Não conseguimos buscar negócios no Google Maps.",
                detalhes=[str(e)[:200]],
            )
            _log(f"❌ Scraper falhou: {e!s}", "error")
        else:
            _emitir_erro_pipeline(
                _log,
                tenant_id,
                "LLM_FAIL",
                message="Erro na geração do site.",
                detalhes=[str(e)[:200]],
            )
            _log(f"ERRO: {e!s}", "error")
        logger.error(f"[Pipeline] Erro: {e}")
        import traceback

        logger.error(traceback.format_exc())
        if "_memory_warm" in locals() and _memory_warm:
            try:
                from agents.pipeline_learning import record_pipeline_error

                record_pipeline_error(
                    _memory_warm,
                    nicho=getattr(state, "segmento", "") or "",
                    fase=_fase_erro
                    or (str(_fase_counter[0]) if "_fase_counter" in locals() else ""),
                    erro=str(e)[:180],
                )
            except Exception as _learn_err:
                print(f"[Learning] erro nao registrado: {_learn_err}")
        # pipeline_queue e legado; falha operacional vem de jobs/pipeline_failures.
        # Salvar lead com status erro se tiver id
        if hasattr(state, "lead_id") and state.lead_id:
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            "UPDATE leads SET status='erro', atualizado_em=:ts WHERE id=:id AND user_id=:uid AND status NOT IN ('concluido','descartado')"
                        ),
                        {
                            "ts": datetime.now().isoformat(),
                            "id": state.lead_id,
                            "uid": state.tenant_id,
                        },
                    )
                    conn.commit()
            except Exception:
                pass
            # Marcar lead_inventory com error_retry para não perder o lead
            try:
                from backend.core.database import SessionLocal
                from backend.services.lead_supply_inventory import (
                    handle_pipeline_job_finished,
                )

                _inv_payload = {"_inventory_id": getattr(state, "_inventory_id", None)}
                _inv_job = {"payload": _inv_payload, "tenant_id": tenant_id}
                with SessionLocal() as _inv_db:
                    handle_pipeline_job_finished(
                        db=_inv_db,
                        job=_inv_job,
                        success=False,
                        job_status="error",
                        fase=_fase_erro,
                        mensagem=str(e)[:200],
                    )
            except Exception as _inv_err:
                print(f"[Pipeline] Erro ao marcar lead_inventory: {_inv_err}")
        # PRD #6: Ledger — salvar com erro
        if _ledger:
            _fase_atual = _ledger.assignments.get("fase_atual", 0)
            if _fase_atual:
                _ledger.registrar_fim_fase(
                    _fase_atual, FaseStatus.FALHOU, erro=str(e)[:200]
                )
                _ledger.registrar_decisao(
                    _fase_atual, "abortar_pipeline", f"Erro fatal: {str(e)[:100]}"
                )
            print(_ledger.snapshot())
            salvar_ledger(_ledger)
        # PRD #10: Trace — salvar com erro + span no DB
        if _trace:
            _cur_span = _trace.span_atual()
            if _cur_span:
                _cur_span.finalizar("error", erro=str(e)[:200])
                if finalizar_span and getattr(state, "pipeline_id", None):
                    finalizar_span(
                        run_id=state.run_id,
                        fase_num=_fase_counter[0],
                        status="error",
                        duracao_ms=_cur_span.duracao_ms,
                        input_tokens=_cur_span.input_tokens,
                        output_tokens=_cur_span.output_tokens,
                        cache_read_tokens=_cur_span.cache_hit_tokens,
                        custo_usd=_cur_span.custo_usd,
                        erro=str(e)[:200],
                    )
            _trace.lead_nome = getattr(state, "lead_nome", "") or ""
            _trace.finalizar("failed")
            salvar_trace(_trace)
        # Parar heartbeat daemon
        _parar_heartbeat()
        # Registrar execução falhada
        try:
            with engine.connect() as _conn_exec:
                _conn_exec.execute(
                    text("""
                    UPDATE pipeline_executions SET finished_at=NOW(), status='failed'
                    WHERE user_id=:uid AND status='running'
                    AND id = (SELECT id FROM pipeline_executions WHERE user_id=:uid AND status='running' ORDER BY started_at DESC LIMIT 1)
                """),
                    {"uid": tenant_id},
                )
                _conn_exec.commit()
        except Exception:
            pass
        _ret = {"sucesso": False, "erro": str(e)}
        if _fase_erro:
            _ret["fase"] = _fase_erro
        return _ret


async def executar_pipeline_multiplos(
    config: dict, tenant_id: int, queue_id: int = None
):
    _log = lambda msg, tipo="info", **kwargs: adicionar_log(
        msg, tipo, user_id=tenant_id
    )
    quantidade_alvo = int(config.get("quantidade", 1))
    concluidos = 0
    tentativas = 0
    max_tentativas = max(quantidade_alvo * 5, 10)
    segmento = config.get("segmento", "")
    cidade = config.get("cidade", "")

    def _fechar_queue(status: str, erro: str = None):
        return None

    def _liberar_pipeline_state():
        try:
            with SessionLocal() as _db_final:
                update_pipeline_state(_db_final, tenant_id, pausado=False)
        except Exception:
            pass

    _log(
        "Pipeline: buscando "
        + str(quantidade_alvo)
        + " lead(s) para "
        + segmento
        + " em "
        + cidade,
        "info",
    )
    while concluidos < quantidade_alvo and tentativas < max_tentativas:
        tentativas += 1
        try:
            with SessionLocal() as _db_perm_loop:
                _perm_loop = validar_permissao_pipeline(_db_perm_loop, tenant_id)
            if not _perm_loop.get("allowed"):
                _reason = _perm_loop.get("reason") or "blocked"
                _message = (
                    _perm_loop.get("message")
                    or "Plano/cooldown bloqueou o próximo lead."
                )
                _log(
                    "Pipeline pausado pelo controle de plano: " + str(_message),
                    "warning",
                )
                if concluidos > 0:
                    break
                _fechar_queue("erro", str(_message)[:1000])
                _liberar_pipeline_state()
                return {"sucesso": False, "fase": _reason, "erro": _message}
            config_unit = dict(config)
            # Cada chamada unitaria entrega 1 site. Hunter varre um pool tecnico e
            # encaminha o primeiro candidato aprovado pelas regras do Caio.
            config_unit["quantidade"] = 1
            config_unit["_candidate_pool_limit"] = min(
                max(quantidade_alvo - concluidos, 10), 30
            )
            _log(
                "Tentativa "
                + str(tentativas)
                + ": buscando pool de "
                + str(config_unit["_candidate_pool_limit"])
                + " candidato(s); o primeiro aprovado segue para o proximo site.",
                "info",
            )
            resultado = await executar_pipeline_completo(
                config_unit, tenant_id, queue_id if tentativas == 1 else None
            )
            if resultado and resultado.get("sucesso"):
                concluidos += 1
                nome_lead = resultado.get("lead", "?")
                _log(
                    "Lead "
                    + str(concluidos)
                    + "/"
                    + str(quantidade_alvo)
                    + " concluido: "
                    + nome_lead,
                    "success",
                )
                if concluidos >= quantidade_alvo:
                    break
            else:
                erro = (resultado.get("erro", "") or "") if resultado else ""
                if _is_renderer_or_publication_error(erro):
                    raise Exception(erro)
                sem_leads = any(
                    x in erro.lower()
                    for x in ["nenhum lead", "todos os leads", "duplicata", "sem leads"]
                )
                if sem_leads:
                    if handle_pipeline_no_leads(
                        config=config,
                        segmento=segmento,
                        cidade=cidade,
                        logger=_log,
                    ):
                        continue
                    break
                _log("Lead nao qualificado, tentando proximo...", "warning")
        except Exception as e:
            err_str = str(e).lower()
            if _is_renderer_or_publication_error(e):
                _log(
                    "Erro de renderer/publicacao no lead aprovado; retry deve retomar o mesmo lead.",
                    "error",
                )
                raise
            if any(
                x in err_str for x in ["nenhum lead", "todos os leads", "sem leads"]
            ):
                if handle_pipeline_no_leads(
                    config=config,
                    segmento=segmento,
                    cidade=cidade,
                    logger=_log,
                ):
                    continue
                break
            _log("Erro tentativa " + str(tentativas) + ": " + str(e)[:80], "warning")
    if concluidos >= quantidade_alvo:
        _log(
            "Concluido: " + str(concluidos) + " lead(s) processado(s) com sucesso!",
            "success",
        )
        _fechar_queue("concluido")
        _liberar_pipeline_state()
        return {"sucesso": True, "concluidos": concluidos}
    elif concluidos > 0:
        _log(
            "Encerrado: "
            + str(concluidos)
            + " de "
            + str(quantidade_alvo)
            + " leads qualificados para "
            + segmento
            + " em "
            + cidade
            + ". Tente outro nicho ou cidade.",
            "warning",
        )
        _fechar_queue("concluido")
        _liberar_pipeline_state()
        return {"sucesso": True, "concluidos": concluidos, "parcial": True}
    else:
        _erro_final = (
            "Nenhum lead qualificado para "
            + segmento
            + " em "
            + cidade
            + ". Tente outro nicho ou uma cidade maior."
        )
        _log(
            _erro_final,
            "error",
        )
        _fechar_queue("erro", _erro_final)
        _liberar_pipeline_state()
        return {"sucesso": False, "fase": "hunter", "erro": _erro_final}


async def executar_pipeline_lead_existente(
    lead_id: str,
    tenant_id: int,
    forcar_renovacao: bool = False,
    queue_id: int = None,
    run_id: str = None,
    job_id: int | str | None = None,
    test_number: str | None = None,
    skip_franz_outreach: bool = False,
):
    """Pipeline de site para lead já existente no banco — pula o hunter."""
    _log = lambda msg, tipo="info", **kwargs: adicionar_log(
        msg, tipo, user_id=tenant_id
    )

    # Verificar permissão (créditos + cooldown) antes de executar
    with SessionLocal() as _db_check:
        _perm = validar_permissao_pipeline(_db_check, tenant_id)
        if not _perm["allowed"]:
            _msg = _perm.get("message", "Bloqueado")
            _log(f"Pipeline bloqueado: {_msg}", "warning")
            logger.info(
                f"[Pipeline] Lead {lead_id} bloqueado — {_perm.get('reason', '?')} (tenant={tenant_id})"
            )
            raise Exception(_msg)

    _log("Iniciando reprocessamento...", "info")
    import json as _json

    from utils.agente1_hunter_v2 import LeadRaw
    from utils.safe_lead_qualificado import safe_qualificar

    # Carregar lead do banco — valida ownership pelo tenant_id
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
            {"id": lead_id, "uid": tenant_id},
        ).fetchone()
        if not row:
            logger.error(
                f"[Pipeline] Lead {lead_id} nao encontrado ou nao pertence ao usuario {tenant_id}"
            )
            raise Exception(f"Lead {lead_id} nao encontrado")
        lead_dict = dict(row._mapping)

    # ─── GUARD CROSS-TENANT: se o mesmo negócio (phone ou place_id) já tem
    # lead ativo em OUTRO tenant, bloqueia para evitar site/WhatsApp duplicado.
    # Cobre o caso de admins com múltiplas contas (dezigpi/maxtec) achando o
    # mesmo negócio físico em tenants separados. ───
    _phone_norm = re.sub(r"\D+", "", str(lead_dict.get("telefone") or ""))
    if _phone_norm.startswith("55") and len(_phone_norm) > 11:
        _phone_norm = _phone_norm[2:]
    with engine.connect() as _guard_conn:
        _dup = _guard_conn.execute(
            text(
                """
                SELECT id, user_id, nome, status, url_site
                FROM leads
                WHERE id <> :id
                  AND REPLACE(REPLACE(REPLACE(COALESCE(telefone,''),' ',''),'-',''),' ','') = :phone
                  AND status IN ('processando','concluido','pronto')
                LIMIT 5
                """
            ),
            {"id": lead_id, "phone": _phone_norm},
        ).fetchall()
        if _dup:
            _other = ", ".join(f"user={r[1]} status={r[3]}" for r in _dup[:3])
            _log(
                f"BLOCKED: mesmo telefone ja tem lead ativo em outro tenant ({_other}). "
                "Reutilize o existente.",
                "warning",
            )
            raise Exception(
                f"Lead {lead_id} bloqueado: telefone duplicado em outro tenant ({_other})"
            )

    nome = lead_dict.get("nome", "")
    cidade = lead_dict.get("cidade", "")
    segmento = lead_dict.get("segmento", "")

    # Guard: inferir segmento pelo nome quando o Hunter salvou o segmento da busca.
    _seg_inferido = inferir_segmento_por_nome(nome, segmento)
    if _seg_inferido and _seg_inferido.lower() != (segmento or "").lower():
        logger.info(
            "[Pipeline] Segmento corrigido pelo nome: '%s' (era '%s')",
            _seg_inferido,
            segmento,
        )
        segmento = _seg_inferido
    dados = lead_dict.get("dados_completos") or {}
    if isinstance(dados, str):
        try:
            dados = _json.loads(dados)
        except (_json.JSONDecodeError, TypeError) as e:
            # FIX CRÍTICO: dados_completos corrompido no banco
            # Fotos, reviews e total de avaliacoes sao perdidos
            # Logamos para detectar banco corrompido
            logger.error(
                f"[Pipeline] dados_completos JSON corrompido (lead_id={lead_id}): {e}. "
                f"Fotos e reviews nao serao exibidos no site."
            )
            dados = {}

    fotos = dados.get("fotos") or []
    reviews = dados.get("reviews") or []
    total_av = dados.get("total_avaliacoes") or len(reviews)

    lead_raw = LeadRaw(
        nome=nome,
        cidade=cidade,
        segmento=segmento,
        telefone=lead_dict.get("telefone") or "",
        whatsapp=lead_dict.get("whatsapp") or "",
        rating=float(lead_dict.get("rating") or 0),
        total_avaliacoes=int(total_av),
        reviews=reviews,
        fotos=fotos,
        website=lead_dict.get("website") or dados.get("website") or "",
        endereco=lead_dict.get("endereco") or dados.get("endereco") or "",
        maps_url=dados.get("maps_url") or "",
        horarios=dados.get("horarios") or [],
        atributos=dados.get("atributos") or [],
        servicos=dados.get("servicos") or [],
    )
    # LeadQualificado criado de forma defensiva (safe_qualificar lida com lead=None/str)
    _lead_qualificado = safe_qualificar(lead_raw, lead_dict, log_fn=_log)
    state = FraLibState(
        segmento=segmento,
        cidade=cidade,
        pipeline_id=gerar_pipeline_id(
            tenant_id, nome, segmento, cidade, lead_id=lead_id
        ),
        run_id=run_id or uuid.uuid4().hex[:12],
        tenant_id=tenant_id,
    )
    state = build_reprocess_seed_state(
        state, lead_dict, dados, lead_raw, segmento, cidade, nome
    )

    config = build_existing_lead_pipeline_config(
        segmento=segmento,
        cidade=cidade,
        queue_id=queue_id,
        forcar_renovacao=forcar_renovacao,
        run_id=run_id or uuid.uuid4().hex[:12],
        job_id=job_id,
        test_number=test_number,
        skip_franz_outreach=skip_franz_outreach,
    )
    state.run_id = config["_run_id"]
    state.lead_id = lead_id
    _log(f"[Reprocessar] Lead: {nome} ({cidade})", "info")

    if forcar_renovacao:
        config["_cold_run"] = True
        _invalidar_caches_cold_run(
            segmento=segmento,
            cidade=cidade,
            nome=nome,
            pipeline_id=state.pipeline_id,
            log_fn=_log,
        )

    # Substituir fotos reais por Unsplash — zero fotos do Google Maps no HTML
    try:
        import asyncio as _asyncio

        from agents.unsplash_fetcher import buscar_fotos_unsplash as _buscar_unsplash

        _loop = _asyncio.get_event_loop()
        _fotos_unsplash = await _loop.run_in_executor(
            None,
            lambda: _buscar_unsplash(
                segmento,
                quantidade=8,
                nome=nome,
                cidade=cidade,
                archetype=_visual_archetype_id(segmento, nome, state.lead_raw_data),
            ),
        )
        state.lead_raw_data["fotos"] = _fotos_unsplash
        state.lead_raw_data["logo_url"] = None
        _log(f"  Fotos Unsplash: {len(_fotos_unsplash)}", "success")
    except Exception as _e:
        logger.warning(f"[Pipeline] Unsplash erro no reprocessar: {_e}")
        state.lead_raw_data["fotos"] = []
        state.lead_raw_data["logo_url"] = None

    # Forcar renovacao: invalidar caches de Jina e keyword_research
    if forcar_renovacao:
        import hashlib
        import os as _os

        _cache_key = hashlib.md5(
            (segmento.lower() + cidade.lower()).encode()
        ).hexdigest()[:12]
        _jina_file = os.path.join(
            _BASE, "agents", "jina_cache", f"jina_{_cache_key}.txt"
        )
        if _os.path.exists(_jina_file):
            _os.remove(_jina_file)
            _log("  Cache Jina invalidado", "info")
        try:
            from core.database import engine as _eng

            with _eng.connect() as _kc:
                _kc.execute(
                    text("DELETE FROM keyword_cache WHERE segmento=:s AND cidade=:c"),
                    {"s": segmento.lower(), "c": cidade.lower()},
                )
                _kc.commit()
            _log("  Cache Keywords invalidado", "info")
        except Exception as _kce:
            logger.warning(f"[Pipeline] Erro ao invalidar keyword cache: {_kce}")

    # Pular FASE 1 (hunter) e ir direto para FASE 2+
    # Reusar executar_pipeline_completo a partir da FASE 2
    # Injetar state no pipeline via config especial
    config["_lead_existente"] = True
    config["_lead_id_existente"] = lead_id
    return await _executar_pipeline_a_partir_fase2(state, tenant_id, config)


async def _executar_pipeline_a_partir_fase2(state, tenant_id, config):
    """Executa o pipeline a partir da FASE 2 com state já populado."""
    import hashlib
    import random

    _log = lambda msg, tipo="info", **kwargs: adicionar_log(
        msg, tipo, user_id=tenant_id
    )

    def _progress(fase_num, label):
        import json as _json_prog

        _phase_key = _pipeline_phase_key(fase_num, label)
        _set_pipeline_job_phase(config, tenant_id, _phase_key, label)
        adicionar_log(
            _json_prog.dumps(
                {
                    "type": "progress",
                    "fase": fase_num,
                    "phase": _phase_key,
                    "total": 11,
                    "label": label,
                    "percent": round(min(fase_num, 11) / 11 * 100),
                }
            ),
            "pipeline",
            user_id=tenant_id,
        )

    from agents.token_tracker import TokenTracker, set_tracker

    _token_tracker = init_phase_tracking(
        state,
        tenant_id,
        config,
        set_llm_context_for_pipeline,
        TokenTracker,
        set_tracker,
    )
    try:
        _db_state = SessionLocal()
        try:
            update_pipeline_state(_db_state, tenant_id, pausado=False, config=config)
        finally:
            _db_state.close()
        _progress(2, "Qualificando lead...")
        _log("FASE 2: CAIO", "info")

        ensure_keyword_research(state, _log)

        # Caio: pular se já qualificado (reprocessamento)
        if not state.qualificacao_caio:
            from agents.caio import CaioOutput

            state.qualificacao_caio = CaioOutput(
                qualificado=True,
                qualificacao="QUENTE",
                tier=state.lead_obj.tier or "STANDARD",
                score=state.lead_obj.score or 50,
                motivo="Reprocessamento — qualificação anterior mantida",
            )
        state.alex_result = None
        _log(
            f"  Caio: {state.qualificacao_caio.qualificacao} (tier={state.qualificacao_caio.tier})",
            "info",
        )

        # Referencias Jina legadas, sem fase estrategista separada
        state.briefing_theo = (
            f"Site para {state.lead_nome} em {state.lead_obj.lead.cidade}."
        )

        _progress(3, "Pesquisa de mercado...")
        _log("FASE 3: JINA (Intelligence v2)", "info")
        # ensure_jina_insights usa Playwright local internamente; fallback_researcher
        # eh legacy e nao eh mais chamado. Passamos None pra nao dar NameError.
        ensure_jina_insights(state, _log, None, logger.warning)

        # Cores: design_context.py e a fonte unica de verdade (tokens OKLch)
        # paleta_nicho removido — ArquitetoMestre usa design_context diretamente

        curate_lead_assets(state, _log)

        # Agente de Prompt / Arquiteto Mestre
        _prompt_agent_flow = _is_prompt_agent_flow(config)
        _progress(
            6,
            "Preparando prompt..."
            if _prompt_agent_flow
            else "Montando direção visual...",
        )
        _log(
            "FASE 6: AGENTE DE PROMPT"
            if _prompt_agent_flow
            else "FASE 6: ARQUITETO MESTRE",
            "info",
        )
        _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
        random.seed(_seed)
        _aplicar_segmento_inferido(state, _log)
        _seg = state.segmento or state.lead_obj.lead.segmento or "negocio local"
        _cid = state.lead_obj.lead.cidade or state.cidade or ""
        _dark_mode = (state.segmento or "").lower() in (
            "academia",
            "crossfit",
            "churrascaria",
            "barbearia",
        )
        _builder_fast_path = _is_builder_fast_path(config) or _prompt_agent_flow
        if _prompt_agent_flow:
            logger.info("[Pipeline] Prompt Agent flow ativo em lead existente")
        elif _builder_fast_path:
            logger.info("[Pipeline] Builder fast-path ativo em lead existente")

        from agents.agente_nicho import gerar_briefing as _gerar_briefing
        from agents.agente_variacao import gerar_variacao as _gerar_variacao

        _prd_fn2 = gerar_arquiteto_mestre_prd
        build_prompt_phase_outputs(
            state=state,
            tenant_id=tenant_id,
            seg=_seg,
            cid=_cid,
            dark_mode=_dark_mode,
            builder_fast_path=_builder_fast_path,
            prompt_agent_flow=_prompt_agent_flow,
            build_prompt_prd=_build_prompt_agent_prd,
            build_skill_prd=_build_skill_fast_prd,
            build_master_prd=_prd_fn2,
            gerar_briefing=_gerar_briefing,
            gerar_variacao=_gerar_variacao,
            log_fn=_log,
            warning_fn=logger.warning,
        )

        _ledger = None
        _span = None
        _trace = None
        _fase_counter = [0]
        return await execute_pipeline_tail(
            state=state,
            tenant_id=tenant_id,
            config=config,
            logger=logger,
            engine=engine,
            SessionLocal=SessionLocal,
            _log=_log,
            _progress=_progress,
            _ledger=_ledger,
            _span=_span,
            _trace=_trace,
            _fase_counter=_fase_counter,
            _set_llm_context_for_pipeline=set_llm_context_for_pipeline,
            update_pipeline_state=update_pipeline_state,
            build_prompt_phase_outputs=build_prompt_phase_outputs,
            build_franz_outreach_payload=build_franz_outreach_payload,
            publish_rendered_site=publish_rendered_site,
            copy_builder_dist=copy_builder_dist,
            _ensure_prd_publication_identity=_ensure_prd_publication_identity,
            _ensure_prd_design_reference=_ensure_prd_design_reference,
            _ensure_prd_contracts=_ensure_prd_contracts,
            _build_prompt_agent_prd=_build_prompt_agent_prd,
            _build_skill_fast_prd=_build_skill_fast_prd,
            _build_master_prd=gerar_arquiteto_mestre_prd,
            _visual_archetype_id=_visual_archetype_id,
            _builder_job_id_for_state=_builder_job_id_for_state,
            render_site_with_builder=render_site_with_builder,
            _persist_failed_renderer_html=_persist_failed_renderer_html,
            _skip_html_quality_gate=_skip_html_quality_gate,
            _skip_deterministic_gate=_skip_deterministic_gate,
            _tenant_sdr_allowed=_tenant_sdr_allowed,
            trial_credit_waits_for_sdr_delivery=trial_credit_waits_for_sdr_delivery,
            consumir_credito_diario=consumir_credito_diario,
            salvar_checkpoint=salvar_checkpoint,
            get_dados_agente=get_dados_agente,
            limpar_checkpoint=limpar_checkpoint,
            maybe_schedule_autorun_next_lead=maybe_schedule_autorun_next_lead,
            _COOLDOWN_POR_PLANO=_COOLDOWN_POR_PLANO,
            executar_pipeline_lead_existente=executar_pipeline_lead_existente,
        )

    except Exception as e:
        import traceback

        logger.error(f"[Pipeline] Reprocessar erro: {e}")
        logger.error(traceback.format_exc())
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE leads SET status='erro', erro_pipeline=:err, atualizado_em=:ts WHERE id=:id AND user_id=:uid AND status NOT IN ('concluido','descartado')"
                ),
                {
                    "err": str(e)[:500],
                    "ts": datetime.now().isoformat(),
                    "id": state.lead_id,
                    "uid": state.tenant_id,
                },
            )
            conn.commit()
        # queue_id legado ignorado; jobs/pipeline_failures registram o erro.
        raise
    finally:
        finalize_reprocess_state(
            state,
            tenant_id,
            _token_tracker,
            set_llm_context_for_pipeline,
            update_pipeline_state,
            SessionLocal,
        )
