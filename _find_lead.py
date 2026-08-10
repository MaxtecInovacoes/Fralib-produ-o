import sys
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/backend/core')
from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Find leads not in pipeline_traces (by nome)
    r = conn.execute(text("""
        SELECT l.id, l.nome, l.segmento, l.cidade, l.rating, l.score, l.tier, l.whatsapp
        FROM leads l
        WHERE l.nome NOT IN (SELECT DISTINCT lead_nome FROM pipeline_traces WHERE lead_nome IS NOT NULL)
        ORDER BY l.rating DESC NULLS LAST
        LIMIT 15
    """))
    rows = r.fetchall()
    print("Leads SEM pipeline_traces (%d):" % len(rows))
    for row in rows:
        print("  id=%s nome=%s seg=%s cid=%s rat=%s score=%s tier=%s wa=%s" % tuple(str(x) for x in row))

    # Also check: what pipeline_traces exist with cost > 0
    r2 = conn.execute(text("SELECT trace_id, run_id, lead_nome, status, total_chamadas_llm, custo_total_usd FROM pipeline_traces WHERE custo_total_usd > 0 ORDER BY created_at DESC LIMIT 5"))
    print("\npipeline_traces COM custo:")
    for row in r2.fetchall():
        print("  trace=%s run=%s nome=%s status=%s calls=%s cost=%s" % tuple(str(x) for x in row))
