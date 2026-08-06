"""Test pipeline end-to-end on VPS with real lead data."""
import sys
import os
import time
import json

# Setup
sys.path.insert(0, "/app")
os.chdir("/app")

# Load .env
from dotenv import load_dotenv
load_dotenv("/app/.env", override=False)

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pipeline_test")

# Import pipeline components
from backend.agents.manager.agent import (
    PipelineState, run_pipeline,
    STATE_INIT, STATE_HUNTING, STATE_QUALIFYING,
    STATE_DESIGNING, STATE_BUILDING, STATE_PUBLISHING,
    STATE_OUTREACH, STATE_DONE, STATE_FAILED,
    PIPELINE_STEPS,
)

LEAD_ID = "f07b88e1-66fc-420e-b645-f0a3065e4653"
TENANT_ID = 2

# Fetch lead data from DB
from sqlalchemy import create_engine, text

db_url = os.environ["DATABASE_URL"]
# Inside Docker container: override hostname from localhost to postgres service
if "localhost" in db_url:
    db_url = db_url.replace("localhost", "postgres")
    # Also fix port from 15434 (host-side) to 5432 (container-side)
    db_url = db_url.replace(":15434", ":5432")
engine = create_engine(db_url)

with engine.connect() as conn:
    row = conn.execute(
        text("SELECT nome, cidade, telefone, segmento, rating, dados_completos FROM leads WHERE id=:id"),
        {"id": LEAD_ID}
    ).fetchone()

if not row:
    print(f"ERROR: Lead {LEAD_ID} not found in DB")
    sys.exit(1)

nome, cidade, telefone, segmento, rating, dados_completos = row
dados = json.loads(dados_completos) if dados_completos and isinstance(dados_completos, str) else (dados_completos or {})

print(f"Lead: {nome} | {cidade} | {segmento} | rating={rating}")
print(f"dados_completos keys: {list(dados.keys()) if dados else 'empty'}")
print("=" * 60)

# Build PipelineState
state = PipelineState(
    tenant_id=TENANT_ID,
    run_id=f"test-{LEAD_ID[:8]}",
    lead_id=LEAD_ID,
    segmento=segmento or "",
    cidade=cidade or "",
    lead_data={
        "nome": nome,
        "cidade": cidade,
        "telefone": telefone,
        "segmento": segmento,
        "rating": float(rating) if rating else 0.0,
        "reviews_count": dados.get("reviews_count") or dados.get("total_avaliacoes") or 0,
        "fotos": dados.get("fotos", []),
        "website": dados.get("website", ""),
        "whatsapp": dados.get("whatsapp", telefone),
        "endereco": dados.get("endereco", ""),
        "market_intelligence": dados.get("market_intelligence"),
        "descricao": dados.get("descricao", ""),
    },
)

# Run pipeline step by step
results = []
for step in PIPELINE_STEPS:
    step_name = step.__name__.replace("step_", "")
    print(f"\n>>> STEP: {step_name} (state={state.current_state})")
    t0 = time.monotonic()
    try:
        state = step(state)
        elapsed = time.monotonic() - t0
        results.append({
            "step": step_name,
            "status": "OK" if state.current_state != STATE_FAILED else "FAILED",
            "elapsed_s": round(elapsed, 1),
            "final_state": state.current_state,
            "error": state.error if state.error else "",
            "history_last3": state.history[-3:] if state.history else [],
        })
        print(f"    Result: state={state.current_state} | {elapsed:.1f}s")
        if state.error:
            print(f"    ERROR: {state.error}")
        if state.current_state in (STATE_DONE, STATE_FAILED):
            break
    except Exception as e:
        elapsed = time.monotonic() - t0
        results.append({
            "step": step_name,
            "status": "EXCEPTION",
            "elapsed_s": round(elapsed, 1),
            "final_state": state.current_state,
            "error": str(e),
            "history_last3": state.history[-3:] if state.history else [],
        })
        print(f"    EXCEPTION: {e} ({elapsed:.1f}s)")
        state.error = str(e)
        break

# Summary
print("\n" + "=" * 60)
print("PIPELINE TEST SUMMARY")
print("=" * 60)
for r in results:
    icon = "OK" if r["status"] == "OK" else "FAIL"
    print(f"  [{icon}] {r['step']:15s} | {r['elapsed_s']:6.1f}s | {r['final_state']}")
    if r["error"]:
        print(f"         error: {r['error'][:200]}")

final = results[-1]["status"] if results else "no steps run"
print(f"\nFinal result: {final}")
if state.build_output:
    html_len = len(state.build_output.get("html", ""))
    print(f"HTML generated: {html_len} chars")
if state.deploy_path:
    print(f"Deploy path: {state.deploy_path}")
if state.design_output:
    print(f"Sections: {len(state.design_output.get('sections', []))}")

# Write results to file for retrieval
results_path = "/tmp/pipeline_test_results.json"
with open(results_path, "w") as f:
    json.dump({
        "lead_id": LEAD_ID,
        "lead_nome": nome,
        "results": results,
        "final_state": state.current_state,
        "html_length": len(state.build_output.get("html", "")) if state.build_output else 0,
    }, f, indent=2, default=str)
print(f"\nResults written to {results_path}")
