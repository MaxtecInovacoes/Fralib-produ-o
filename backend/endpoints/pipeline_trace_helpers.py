"""
Helpers de trace para o pipeline.

Fornece funções para criar e finalizar spans de trace com persistência no DB.
"""
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class TraceSpan:
    """Wrapper para span do trace com dados de tokens."""
    span: Any
    fase_num: int
    fase_nome: str
    agente: str


class SpanManager:
    """
    Gerencia spans de trace com persistência no DB.

    Mantém estado interno do span atual para facilitar chamadas
    de iniciar/finalizar sem precisar passar o span manualmente.
    """

    def __init__(
        self,
        trace=None,
        salvar_span=None,
        finalizar_span=None,
        state=None,
        tenant_id: int = 0,
        atualizar_heartbeat_span=None,
    ):
        self.trace = trace
        self.salvar_span = salvar_span
        self.finalizar_span = finalizar_span
        self.state = state
        self.tenant_id = tenant_id
        self.atualizar_heartbeat_span = atualizar_heartbeat_span
        self._span_counter = [0]
        self._current_span = None
        self._token_tracker = None

    def set_token_tracker(self, token_tracker):
        """Define o tracker de tokens para coleta de métricas."""
        self._token_tracker = token_tracker

    def iniciar_span_com_db(self, nome, agente, modelo="", fase_num=0):
        """Helper: cria span no trace + persiste no DB simultaneamente."""
        _span = (
            self.trace.iniciar_span(nome, agente=agente, modelo=modelo)
            if self.trace else None
        )
        if self.salvar_span and getattr(self.state, "pipeline_id", None):
            _fn = fase_num or self._span_counter[0] + 1
            self._span_counter[0] = _fn
            self.salvar_span(
                run_id=self.state.run_id,
                fase_num=_fn,
                fase_nome=nome,
                agente=agente,
                modelo=modelo,
                tenant_id=self.tenant_id,
                lead_id=getattr(self.state, "lead_id", None),
                trace_id=self.trace.trace_id if self.trace else None,
            )
        self._current_span = _span
        return _span

    def finalizar_span_com_db(
        self,
        status,
        erro=None,
        duracao_ms=None,
        input_t=0,
        output_t=0,
        cache_r=0,
        cache_c=0,
        custo=0.0,
    ):
        """Helper: finaliza span no trace + persiste no DB simultaneamente."""
        _span = self._current_span
        if _span:
            _span.finalizar(status, erro=erro)
            if self._token_tracker and _span.agente:
                try:
                    _agent_data = self._token_tracker.resumo()["por_agente"].get(
                        _span.agente
                    )
                    if _agent_data:
                        input_t = input_t or _agent_data.get("input", 0)
                        output_t = output_t or _agent_data.get("output", 0)
                        cache_r = cache_r or _agent_data.get("cache_hit", 0)
                        custo = custo or _agent_data.get("custo", 0.0)
                except Exception:
                    pass
        if self.finalizar_span and getattr(self.state, "pipeline_id", None):
            self.finalizar_span(
                run_id=self.state.run_id,
                fase_num=self._span_counter[0],
                status=status,
                duracao_ms=duracao_ms or (_span.duracao_ms if _span else None),
                input_tokens=input_t or (_span.input_tokens if _span else 0),
                output_tokens=output_t or (_span.output_tokens if _span else 0),
                cache_read_tokens=cache_r or (_span.cache_hit_tokens if _span else 0),
                custo_usd=custo or (_span.custo_usd if _span else 0.0),
                erro=erro,
            )


# Funções stand-alone para backward compatibility
def iniciar_span_com_db(
    nome,
    agente,
    modelo="",
    fase_num=0,
    trace=None,
    salvar_span=None,
    state=None,
    tenant_id: int = 0,
    span_counter=None,
):
    """
    Helper: cria span no trace + persiste no DB simultaneamente.

    Args:
        nome: Nome da fase/agente
        agente: Nome do agente
        modelo: Modelo LLM utilizado
        fase_num: Número da fase (opcional, auto-incrementa se não informado)
        trace: Instância do Trace
        salvar_span: Função para salvar span no DB
        state: Estado FraLibState
        tenant_id: ID do tenant
        span_counter: Lista com contador de fase [int]

    Returns:
        Span criado ou None
    """
    _span = (
        trace.iniciar_span(nome, agente=agente, modelo=modelo)
        if trace else None
    )
    if salvar_span and getattr(state, "pipeline_id", None):
        if span_counter is None:
            span_counter = [0]
        _fn = fase_num or span_counter[0] + 1
        span_counter[0] = _fn
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
    status,
    erro=None,
    duracao_ms=None,
    input_t=0,
    output_t=0,
    cache_r=0,
    cache_c=0,
    custo=0.0,
    span=None,
    token_tracker=None,
    finalizar_span=None,
    state=None,
    span_counter=None,
):
    """
    Helper: finaliza span no trace + persiste no DB simultaneamente.

    Args:
        status: Status do span ('success', 'skipped', 'error')
        erro: Mensagem de erro (opcional)
        duracao_ms: Duração em ms (opcional)
        input_t: Input tokens (opcional)
        output_t: Output tokens (opcional)
        cache_r: Cache read tokens (opcional)
        cache_c: Cache create tokens (opcional)
        custo: Custo USD (opcional)
        span: Span a finalizar
        token_tracker: TokenTracker para coleta de métricas
        finalizar_span: Função para finalizar span no DB
        state: Estado FraLibState
        span_counter: Lista com contador de fase [int]
    """
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
        if span_counter is None:
            span_counter = [0]
        finalizar_span(
            run_id=state.run_id,
            fase_num=span_counter[0],
            status=status,
            duracao_ms=duracao_ms or (span.duracao_ms if span else None),
            input_tokens=input_t or (span.input_tokens if span else 0),
            output_tokens=output_t or (span.output_tokens if span else 0),
            cache_read_tokens=cache_r or (span.cache_hit_tokens if span else 0),
            custo_usd=custo or (span.custo_usd if span else 0.0),
            erro=erro,
        )
