"""Trigger pipeline real e monitorar tracking — via manager.run_pipeline direto."""
import sys, os

_BACKEND_ROOT = '/app/backend'
sys.path.insert(0, _BACKEND_ROOT)
sys.path.insert(0, os.path.join(_BACKEND_ROOT, 'core'))
sys.path.insert(0, os.path.join(_BACKEND_ROOT, 'endpoints'))
sys.path.insert(0, os.path.join(_BACKEND_ROOT, 'services'))
sys.path.insert(0, os.path.join(_BACKEND_ROOT, 'agents'))
sys.path.insert(0, os.path.join(_BACKEND_ROOT, 'utils'))

from backend.core.database import inicializar_database, engine
from sqlalchemy import text
from backend.agents.token_tracker import TokenTracker, set_tracker, log_tracking, salvar_tracking, _calcular_custo
from backend.observability import Trace, salvar_trace
from backend.agents.manager.agent import run_pipeline, PipelineState
from backend.agents.llm_tracking import set_tracking_context

print("=== TRIGGER PIPELINE REAL (via run_pipeline) ===\n")
inicializar_database()

# Config do teste — usando lead REAL que passa no Caio, sem pipeline rodada
segmento = "academia"
cidade = "Campina Grande do Sul"
tenant_id = 2
run_id = f"smoke-{os.getpid()}"
lead_id = "ca313405-1ecb-4ffd-a38a-6333d25f0d07"  # Academia Iron Gym — capturado, sem pipeline

# Lead data — dados REAIS do lead
lead_data = {
    "nome": "Academia Iron Gym",
    "cidade": cidade,
    "telefone": "5541999946923",
    "segmento": segmento,
    "rating": 0.0,
    "reviews_count": 0,
    "fotos": [],
    "website": "",
    "whatsapp": "5541999946923",
    "endereco": "",
    "market_intelligence": None,
    "descricao": "",
}

print(f"[SETUP] Segmento: {segmento} | Cidade: {cidade}")
print(f"[SETUP] run_id: {run_id}\n")

# Token tracker
_token_tracker = TokenTracker(
    run_id=run_id,
    lead_nome=lead_data.get("nome", "unknown")[:100],
    nicho=segmento,
)
set_tracker(_token_tracker)
set_tracking_context(tenant_id=tenant_id, run_id=run_id, job_id="smoke-test")

# Trace
trace = Trace(run_id=run_id, lead_nome=lead_data.get("nome", "unknown")[:100], nicho=segmento)
trace.iniciar_span("pipeline_total", "worker", "")

# Build state
state = PipelineState(
    tenant_id=tenant_id,
    run_id=run_id,
    lead_id=lead_id,
    job_id="smoke-test",
    segmento=segmento,
    cidade=cidade,
    lead_data=lead_data,
)

t0 = __import__('time').monotonic()
print("[RUN] Executando run_pipeline()...\n")

try:
    final = run_pipeline(state, trace=trace)
    trace.span_atual().finalizar("ok" if final.current_state == "done" else "error")
    trace.duracao_total_ms = int((__import__('time').monotonic() - t0) * 1000)
    trace.status = "success" if final.current_state == "done" else "failed"
    trace.complexidade = final.current_state

    # Agregar tracking nos spans
    for call in _token_tracker.chamadas:
        model = call.get("model", "unknown")
        usage = {
            "input_tokens": call.get("input_tokens", 0),
            "output_tokens": call.get("output_tokens", 0),
            "cache_creation": call.get("cache_creation", 0),
            "cache_read": call.get("cache_read", 0),
        }
        span = trace.iniciar_span(f"llm_{call['agente']}", call['agente'], model)
        span.input_tokens = usage["input_tokens"]
        span.output_tokens = usage["output_tokens"]
        span.cache_hit_tokens = usage["cache_read"]
        span.custo_usd = _calcular_custo(model, usage)
        span.finalizar("success")
    trace._agregar_metricas()
    trace.total_chamadas_llm = len(_token_tracker.chamadas)

    salvar_trace(trace)
    log_tracking(_token_tracker.resumo())

    print(f"\n[RESULT] Estado final: {final.current_state}")
    print(f"[RESULT] Erro: {final.error or 'none'}")
    print(f"[RESULT] Tracking: {len(_token_tracker.chamadas)} chamadas LLM registradas")
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback as tb
    tb.print_exc()
    trace.span_atual().finalizar("error")
    trace.duracao_total_ms = int((__import__('time').monotonic() - t0) * 1000)
    trace.status = "failed"
    salvar_trace(trace)

# ── MEDIR TUDO ──
print("\n" + "=" * 60)
print("MEDIÇÃO COMPLETA DO TRACKING")
print("=" * 60)

# 1. pipeline_traces (resumo do run)
with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT run_id, status, total_chamadas_llm,
               total_input_tokens, total_output_tokens,
               total_cache_hit, custo_total_usd, duracao_total_ms
        FROM pipeline_traces
        WHERE run_id = :run_id
    """), {"run_id": run_id})
    rows = r.fetchall()
    if rows:
        row = rows[0]
        print(f"\npipeline_traces (run_id={run_id}):")
        print(f"  status:              {row.status}")
        print(f"  total_chamadas_llm:  {row.total_chamadas_llm}")
        print(f"  total_input_tokens:  {row.total_input_tokens or 0}")
        print(f"  total_output_tokens: {row.total_output_tokens or 0}")
        print(f"  total_cache_hit:     {row.total_cache_hit or 0}")
        print(f"  custo_total_usd:     ${row.custo_total_usd or 0:.4f}")
        print(f"  duracao_total_ms:    {row.duracao_total_ms}ms")
    else:
        print(f"\npipeline_traces: (vazio — nenhum registro para run_id={run_id})")

# 2. llm_budget_ledger (detalhe por agente/modelo)
with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT agent, provider, model, COUNT(*) as chamadas,
               SUM(input_tokens) as input_tokens,
               SUM(output_tokens) as output_tokens,
               SUM(cache_read_tokens) as cache_read,
               SUM(cache_created_tokens) as cache_creation,
               SUM(cost_usd) as custo
        FROM llm_budget_ledger
        WHERE run_id = :run_id
        GROUP BY agent, provider, model
        ORDER BY chamadas DESC
    """), {"run_id": run_id})
    rows = r.fetchall()
    print(f"\nllm_budget_ledger (run_id={run_id}):")
    if rows:
        print(f"  {'Agente':<22s} {'Provider':<10s} {'Model':<28s} {'#':>4s} {'in':>8s} {'out':>8s} {'cache_r':>8s} {'cache_c':>8s} {'$':>8s}")
        for row in rows:
            print(f"  {row[0]:<22s} {row[1]:<10s} {row[2] or '':<28s} {row[3]:>4d} {row[4] or 0:>8d} {row[5] or 0:>8d} {row[6] or 0:>8d} {row[7] or 0:>8d} {row[8] or 0:>8.4f}")
    else:
        print("  (vazio — nenhuma chamada registrada)")

# 3. TokenTracker in-memory
print(f"\nTokenTracker in-memory: {len(_token_tracker.chamadas)} chamadas")
for c in _token_tracker.chamadas:
    print(f"  {c.get('agente','?'):<22s} model={c.get('model','?')} in={c.get('input_tokens',0)} out={c.get('output_tokens',0)}")

print("\n=== DONE ===")
