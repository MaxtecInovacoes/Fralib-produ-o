"""
Gerenciamento de estado e persistência do pipeline FraLib.
"""

import os
import uuid
import re
import unicodedata
import hashlib
import logging
from typing import Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger("uvicorn")

# ─── HELPER: SLUG ───────────────────────────────────────────────────────────

def gerar_slug_lead(nome: str, max_len: int = 50) -> str:
    """Gera slug URL-friendly a partir do nome do lead."""
    if not nome:
        return ""
    _slug_norm = (
        unicodedata.normalize("NFKD", nome)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", "-", _slug_norm.lower()).strip("-")[:max_len]


def gerar_pipeline_id(
    tenant_id: int,
    nome: str = "",
    segmento: str = "",
    cidade: str = "",
    lead_id: str = "",
) -> str:
    """Gera ID único para o pipeline/run."""
    from agents.pipeline_checkpoint import gerar_pipeline_id as _original
    return _original(tenant_id, nome, segmento, cidade, lead_id=lead_id)


# ─── HEARTBEAT ──────────────────────────────────────────────────────────────

def criar_heartbeat_thread(
    run_id: str,
    tenant_id: int,
    engine,
    fase_counter,
    atualizar_heartbeat_span: Callable = None,
) -> tuple:
    """Cria thread de heartbeat que atualiza worker_heartbeat periodicamente."""
    import threading

    _heartbeat_stop = threading.Event()

    def _heartbeat_loop():
        from sqlalchemy import text as _hb_text
        while not _heartbeat_stop.is_set():
            try:
                with engine.connect() as _hb_conn:
                    _hb_conn.execute(
                        _hb_text("""
                            UPDATE jobs
                            SET worker_heartbeat = NOW()
                            WHERE run_id = :run_id AND tenant_id = :tenant_id
                        """),
                        {"run_id": run_id, "tenant_id": tenant_id},
                    )
                    if fase_counter[0] > 0 and atualizar_heartbeat_span:
                        atualizar_heartbeat_span(run_id, fase_counter[0])
                    _hb_conn.commit()
            except Exception:
                pass
            _heartbeat_stop.wait(15)

    _thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    return _thread, _heartbeat_stop


def parar_heartbeat(thread, stop_event) -> None:
    """Para a thread de heartbeat."""
    stop_event.set()
    thread.join(timeout=3)


# ─── ATUALIZAR PIPELINE ID ─────────────────────────────────────────────────

def atualizar_pipeline_id_para_lead(
    state,
    tenant_id: int,
    queue_id: int = None,
    log_legacy_queue_id: Callable = None,
) -> None:
    """Atualiza pipeline_id baseado no lead selecionado."""
    from agents.pipeline_checkpoint import gerar_pipeline_id

    cidade = (
        getattr(getattr(state.lead_obj, "lead", None), "cidade", None)
        or state.cidade
        or ""
    )
    lead_marker = (
        state.lead_id
        or state.lead_raw_data.get("place_id")
        or getattr(getattr(state.lead_obj, "lead", None), "place_id", "")
    )
    novo = gerar_pipeline_id(
        tenant_id,
        state.lead_nome,
        state.segmento or getattr(getattr(state.lead_obj, "lead", None), "segmento", ""),
        cidade,
        lead_id=lead_marker,
    )
    antigo = state.pipeline_id
    state.pipeline_id = novo
    if antigo != novo:
        logger.info("[Pipeline] Pipeline ID refinado: %s -> %s", antigo, novo)
    if log_legacy_queue_id:
        log_legacy_queue_id(queue_id, logger)


# ─── SPAN/TRACING HELPERS ──────────────────────────────────────────────────

def iniciar_span_com_db(
    trace,
    salvar_span: Callable,
    state,
    nome: str,
    agente: str,
    modelo: str = "",
    fase_num: int = 0,
    fase_counter: list = None,
    tenant_id: int = 0,
) -> Any:
    """Helper: cria span no trace + persiste no DB simultaneamente."""
    _span = trace.iniciar_span(nome, agente=agente, modelo=modelo) if trace else None
    if salvar_span and getattr(state, "pipeline_id", None):
        _fn = fase_num or (fase_counter[0] + 1 if fase_counter else 1)
        if fase_counter is not None:
            fase_counter[0] = _fn
        salvar_span(
            run_id=state.run_id,
            fase_num=_fn,
            fase_nome=nome,
            agente=agente,
            modelo=modelo,
            tenant_id=tenant_id,
            lead_id=getattr(state, "lead_id", None),
            trace_id=trace.trace_id if trace else None,
        )
    return _span


def finalizar_span_com_db(
    span,
    fase_counter,
    state,
    finalizar_span: Callable,
    token_tracker,
    status: str,
    erro: str = None,
    duracao_ms: float = None,
    input_t: int = 0,
    output_t: int = 0,
    cache_r: int = 0,
    cache_c: int = 0,
    custo: float = 0.0,
) -> None:
    """Helper: finaliza span no trace + persiste no DB simultaneamente."""
    if span:
        span.finalizar(status, erro=erro)
        if token_tracker and span.agente:
            try:
                _agent_data = token_tracker.resumo()["por_agente"].get(span.agente)
                if _agent_data:
                    input_t = input_t or _agent_data.get("input", 0)
                    output_t = output_t or _agent_data.get("output", 0)
                    cache_r = cache_r or _agent_data.get("cache_hit", 0)
                    custo = custo or _agent_data.get("custo", 0.0)
            except Exception:
                pass
    if finalizar_span and getattr(state, "pipeline_id", None):
        finalizar_span(
            run_id=state.run_id,
            fase_num=fase_counter[0],
            status=status,
            duracao_ms=duracao_ms or (span.duracao_ms if span else None),
            input_tokens=input_t or (span.input_tokens if span else 0),
            output_tokens=output_t or (span.output_tokens if span else 0),
            cache_read_tokens=cache_r or (span.cache_hit_tokens if span else 0),
            custo_usd=custo or (span.custo_usd if span else 0.0),
            erro=erro,
        )


# ─── CACHE/PERSISTÊNCIA ─────────────────────────────────────────────────────

def limpar_traces_residuais(base_path: str = None) -> None:
    """Limpa arquivos de trace residuais de execuções anteriores."""
    if base_path is None:
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            "logs",
            "pipeline_trace",
        )
    os.makedirs(base_path, exist_ok=True)
    for _tf in [
        "liz_resultado.json",
        "designer_prd.json",
        "theo_briefing.md",
        "builder_renderer_html.html",
    ]:
        _tp = os.path.join(base_path, _tf)
        if os.path.exists(_tp):
            try:
                os.remove(_tp)
            except Exception:
                pass


def salvar_trace_arquivo(trace_data: Any, tipo: str, base_path: str = None) -> None:
    """Salva trace em arquivo JSON para auditoria."""
    import json

    if base_path is None:
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            "logs",
            "pipeline_trace",
        )
    os.makedirs(base_path, exist_ok=True)

    try:
        _data = trace_data.model_dump() if hasattr(trace_data, "model_dump") else trace_data.__dict__
        with open(os.path.join(base_path, f"{tipo}.json"), "w", encoding="utf-8") as _f:
            json.dump(_data, _f, ensure_ascii=False, indent=2, default=str)
    except Exception as _e:
        print(f"[Pipeline] Trace save skip: {_e}")


# ─── LEAD DATA ─────────────────────────────────────────────────────────────

def build_lead_raw_data(lead, default_segmento: str = "") -> dict:
    """Constrói dicionário de dados brutos do lead."""
    from endpoints.pipeline_lead_flow_helpers import build_lead_raw_data as _original
    return _original(lead, default_segmento)


def gerar_lead_id() -> str:
    """Gera UUID para novo lead."""
    return str(uuid.uuid4())


# ─── CHECKPOINT ─────────────────────────────────────────────────────────────

def get_checkpoint_data(pipeline_id: str, agente: str) -> Optional[dict]:
    """Busca dados de checkpoint para um agente."""
    from agents.pipeline_checkpoint import get_dados_agente
    return get_dados_agente(pipeline_id, agente)


def salvar_checkpoint(pipeline_id: str, agente: str, data: dict) -> None:
    """Salva checkpoint para um agente."""
    from agents.pipeline_checkpoint import salvar_checkpoint as _original
    _original(pipeline_id, agente, data)


def limpar_checkpoint(pipeline_id: str) -> None:
    """Limpa checkpoints após conclusão."""
    from agents.pipeline_checkpoint import limpar_checkpoint as _original
    _original(pipeline_id)


def resumir_checkpoint(pipeline_id: str) -> str:
    """Retorna resumo dos checkpoints existentes."""
    from agents.pipeline_checkpoint import resumo_checkpoint as _original
    return _original(pipeline_id)
