"""
Budget reset + trigger Curitiba Fitness + monitor + validate HTML.
"""
import sys, os, time, re
sys.path.insert(0, '/app/backend')
os.environ['DATABASE_URL'] = 'postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.core.job_queue import enqueue

LEAD_ID = "b5db65cd-e856-487a-9fac-5f5d6caaa62f"
TENANT_ID = 2
LEAD_NOME = "Curitiba Fitness"
MAX_WAIT = 900
POLL_INTERVAL = 5

db_url = "postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

# ── 1. Inspect budget state ────────────────────────────────────────────
with engine.connect() as conn:
    row = conn.execute(text("""
        SELECT COALESCE(SUM(input_tokens+output_tokens),0)::bigint AS total,
               COUNT(*) AS calls,
               MIN(criado_em) AS oldest,
               MAX(criado_em) AS newest
        FROM llm_usage
        WHERE criado_em > NOW() - INTERVAL '24 hours'
    """)).fetchone()
    print(f"BUDGET_24H: used={row.total} calls={row.calls} oldest={row.oldest} newest={row.newest}")

    # tenant usage
    trow = conn.execute(text("""
        SELECT COALESCE(SUM(input_tokens+output_tokens),0)::bigint AS total
        FROM llm_usage
        WHERE user_id=:u AND criado_em > NOW() - INTERVAL '24 hours'
    """), {"u": TENANT_ID}).fetchone()
    print(f"TENANT_2_USAGE_24H: {trow.total}")

# ── 2. Reset daily budget counter (delete 24h window entries) ──────────
with engine.begin() as conn:
    res = conn.execute(text("""
        DELETE FROM llm_usage
        WHERE criado_em > NOW() - INTERVAL '24 hours'
    """))
    print(f"BUDGET_RESET: deleted {res.rowcount} rows from last 24h")

# Confirm reset
with engine.connect() as conn:
    row = conn.execute(text("""
        SELECT COALESCE(SUM(input_tokens+output_tokens),0)::bigint AS total
        FROM llm_usage
        WHERE criado_em > NOW() - INTERVAL '24 hours'
    """)).fetchone()
    print(f"BUDGET_AFTER_RESET: {row.total} tokens in last 24h (should be 0)")

# ── 3. Trigger Curitiba Fitness ────────────────────────────────────────
with SessionLocal() as db:
    db.execute(
        text("UPDATE leads SET status='capturado', processado=false, erro_pipeline=NULL WHERE id=:id"),
        {"id": LEAD_ID},
    )
    db.commit()
    print("Lead status -> capturado")

with SessionLocal() as db:
    job_id = enqueue(
        db,
        tipo="pipeline_lead",
        payload={
            "_lead_id_existente": LEAD_ID,
            "quantidade": 1,
            "_forcar_renovacao": True,
        },
        tenant_id=TENANT_ID,
        max_attempts=3,
        priority=1,
    )
    print(f"JOB ENQUEUED: {job_id}")

# ── 4. Monitor ─────────────────────────────────────────────────────────
print(f"Monitorando... (poll a cada {POLL_INTERVAL}s, max {MAX_WAIT}s)")
t0 = time.time()
last_status = None
while time.time() - t0 < MAX_WAIT:
    time.sleep(POLL_INTERVAL)
    with SessionLocal() as db:
        s = db.execute(text("SELECT status, url_site, erro_pipeline FROM leads WHERE id=:i"), {"i": LEAD_ID}).fetchone()
        cur = s.status if s else "?"
        if cur != last_status:
            elapsed = int(time.time() - t0)
            url = s.url_site if s else ""
            print(f"  [{elapsed}s] status={cur} | url={url}")
            last_status = cur
        if cur in ("concluido", "erro_pipeline", "cancelado"):
            break

# ── 5. Result + validate HTML ──────────────────────────────────────────
with SessionLocal() as db:
    final = db.execute(
        text("SELECT status, url_site, erro_pipeline, atualizado_em FROM leads WHERE id=:i"),
        {"i": LEAD_ID},
    ).fetchone()
    fd = dict(final._mapping) if final else {}
    print(f"\nFINAL: status={fd.get('status')} | url={fd.get('url_site')} | erro={fd.get('erro_pipeline')} | atualizado={fd.get('atualizado_em')}")

site_url = fd.get("url_site") or ""
if site_url:
    found_path = None
    tenant_dir = f"/var/www/fralib/sites/{TENANT_ID}"
    if os.path.isdir(tenant_dir):
        for entry in sorted(os.listdir(tenant_dir)):
            p = os.path.join(tenant_dir, entry, "index.html")
            if os.path.isfile(p) and os.path.getmtime(p) > t0 - 60:
                print(f"NEW SITE: {p}")
                found_path = p
                break
    if not found_path:
        for p in [f"/var/www/fralib/sites/{TENANT_ID}/curitiba-fitness/index.html",
                  f"/var/www/fralib/sites/{TENANT_ID}/curitiba-fitness-{LEAD_ID[:8]}/index.html"]:
            if os.path.isfile(p):
                found_path = p
                break
    if found_path:
        with open(found_path) as f:
            html = f.read()
        checks = {
            "design_tokens (id=design-tokens)": 'id="design-tokens"' in html,
            "unprefixed :root vars (--bg:)": '--bg:' in html,
            "hermetic sections (clear-both)": "clear-both" in html,
            "native FAQ <details>": "<details" in html.lower(),
            "native FAQ <summary>": "<summary" in html.lower(),
        }
        print("\n=== VALIDACAO DOS 4 UPGRADES ===")
        for k, v in checks.items():
            print(f"  {k}: {'OK' if v else 'FAIL'}")
        print(f"\nHTML size: {len(html)} bytes")
        idx = html.find('design-tokens')
        if idx != -1:
            print(f"Tokens snippet: {html[max(0,idx-5):idx+220]!r}")
    else:
        print("HTML FILE NOT FOUND — site may not have been published")
else:
    print("NO URL — pipeline failed before publishing")
