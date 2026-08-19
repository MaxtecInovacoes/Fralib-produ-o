"""Check Hunter config + active jobs."""
from backend.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

cfg = db.execute(text("SELECT segmentos, cidades, meta_diaria, ativo, hunter_pausado, producao_pausada, provider FROM lead_supply_config WHERE tenant_id = 1")).fetchone()
print("=== CONFIG ===")
if cfg:
    print(f"segmentos={cfg.segmentos}")
    print(f"cidades={cfg.cidades}")
    print(f"meta_diaria={cfg.meta_diaria}")
    print(f"ativo={cfg.ativo} hunter_pausado={cfg.hunter_pausado} producao_pausada={cfg.producao_pausada} provider={cfg.provider}")
else:
    print("NO CONFIG")

jobs = db.execute(
    text("SELECT tipo, total, status, criado_em FROM job_queue WHERE status IN ('pending','running') ORDER BY criado_em DESC LIMIT 10")
).fetchall()
print("\n=== JOBS ATIVOS ===")
if not jobs:
    print("(nenhum)")
for j in jobs:
    print(f"  {j.tipo} | total={j.total} | {j.status} | {j.criado_em}")

events = db.execute(
    text("SELECT source, level, message, created_at FROM lead_supply_events ORDER BY created_at DESC LIMIT 10")
).fetchall()
print("\n=== EVENTOS RECENTES ===")
if not events:
    print("(nenhum)")
for e in events:
    print(f"  [{e.level}] {e.source}: {e.message[:80]} @ {e.created_at}")

db.close()
