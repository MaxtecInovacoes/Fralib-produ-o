"""Check Arena Gym Fitness site status on VPS - final version."""
import sys, os
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/backend/core')

from backend.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Lead
    print("=== LEAD ===")
    r = conn.execute(text("""
        SELECT id, nome, url_site, status, cidade, segmento
        FROM leads WHERE id = '38ffd3fb-c9a0-498c-9abc-c8a4e8f24853'
    """))
    row = r.fetchone()
    if row:
        print(f"  Lead: {row[1]}")
        print(f"  URL do site: {row[2]}")
        print(f"  Status: {row[3]}")
        print(f"  Cidade: {row[4]} | Segmento: {row[5]}")

    # Pipeline executions - use run_id FK
    print("\n=== PIPELINE EXECUTIONS (by run_id) ===")
    r = conn.execute(text("""
        SELECT id, run_id, status, lead_nome, nicho, tier,
               duracao_total_ms, total_input_tokens, total_output_tokens,
               custo_total_usd, erro, started_at, finished_at
        FROM pipeline_executions
        WHERE run_id LIKE '%smoke%' OR run_id LIKE '%arena%'
        ORDER BY id DESC LIMIT 5
    """))
    rows = r.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} run_id={row[1]}")
            print(f"    status={row[2]} nome={row[3]} nicho={row[4]} tier={row[5]}")
            print(f"    duracao={row[6]}ms in={row[7]} out={row[8]} custo=${row[9] or 0:.4f}")
            print(f"    erro={row[10]} started={row[11]} finished={row[12]}")
    else:
        print("  Nenhuma execucao encontrada")

    # Find all tables with "site" or "publish"
    print("\n=== ALL TABLES (site-related) ===")
    r = conn.execute(text("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        AND (tablename LIKE '%site%' OR tablename LIKE '%publish%' OR tablename LIKE '%deploy%' OR tablename LIKE '%html%')
        ORDER BY tablename
    """))
    for row in r.fetchall():
        print(f"  {row[0]}")

    # Full table list
    print("\n=== ALL TABLES ===")
    r = conn.execute(text("""
        SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename
    """))
    for row in r.fetchall():
        print(f"  {row[0]}")

# Check filesystem
print("\n=== FILESYSTEM ===")
for path in ['/opt/fralib/data/sites', '/app/data/sites', '/opt/fralib/output', '/app/output', '/opt/fralib/data']:
    if os.path.exists(path):
        try:
            files = os.listdir(path)
            print(f"  {path}: {len(files)} items")
            for f in files[:10]:
                full = os.path.join(path, f)
                if os.path.isdir(full):
                    sub = os.listdir(full)
                    print(f"    {f}/ ({len(sub)} items)")
                else:
                    print(f"    {f}")
        except Exception as e:
            print(f"  {path}: ERROR - {e}")
    else:
        print(f"  {path}: NOT FOUND")
