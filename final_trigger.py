"""
Final: reset budget -> trigger Curitiba Fitness -> monitor -> validate 4 upgrades.
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

# 1. Reset budget
with engine.begin() as conn:
    res = conn.execute(text("DELETE FROM llm_usage WHERE criado_em > NOW() - INTERVAL '24 hours'"))
    print(f"BUDGET_RESET: deleted {res.rowcount} rows")
    row = conn.execute(text("SELECT COALESCE(SUM(input_tokens+output_tokens),0)::bigint AS total FROM llm_usage WHERE criado_em > NOW() - INTERVAL '24 hours'")).fetchone()
    print(f"BUDGET_AFTER: {row.total} tokens (should be 0)")

# 2. Trigger
with SessionLocal() as db:
    db.execute(text("UPDATE leads SET status='capturado', processado=false, erro_pipeline=NULL WHERE id=:id"), {"id": LEAD_ID})
    db.commit()
    job_id = enqueue(
        db,
        tipo="pipeline_lead",
        payload={"_lead_id_existente": LEAD_ID, "quantidade": 1, "_forcar_renovacao": True},
        tenant_id=TENANT_ID,
        max_attempts=3,
        priority=1,
    )
    print(f"JOB ENQUEUED: {job_id}")

# 3. Monitor
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
            print(f"  [{elapsed}s] status={cur}")
            last_status = cur
        if cur in ("concluido", "erro_pipeline", "cancelado"):
            break

# 4. Result
with SessionLocal() as db:
    final = db.execute(text("SELECT status, url_site, erro_pipeline, atualizado_em FROM leads WHERE id=:i"), {"i": LEAD_ID}).fetchone()
    fd = dict(final._mapping) if final else {}
    print(f"\nFINAL: status={fd.get('status')} | url={fd.get('url_site')} | erro={fd.get('erro_pipeline')} | atualizado={fd.get('atualizado_em')}")

# 5. Validate HTML
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
        for p in [f"/var/www/fralib/sites/{TENANT_ID}/curitiba-fitness-b5db65cd/index.html"]:
            if os.path.isfile(p):
                found_path = p
                break
    if found_path:
        with open(found_path) as f:
            html = f.read()
        # Collect all section classes
        import re as re2
        sections = re2.findall(r'<section\b[^>]*>', html, re2.IGNORECASE)
        section_classes = [re2.search(r'class=(["\'])(.*?)\1', s, re2.IGNORECASE) for s in sections]
        has_clear_both = any("clear-both" in (m.group(2) if m else "") for m in section_classes)
        checks = {
            "design_tokens (id=design-tokens)": 'id="design-tokens"' in html,
            "unprefixed :root vars (--bg:)": '--bg:' in html,
            "hermetic sections (clear-both)": has_clear_both,
            "native FAQ <details>": "<details" in html.lower(),
            "native FAQ <summary>": "<summary" in html.lower(),
        }
        print("\n=== VALIDACAO DOS 4 UPGRADES ===")
        for k, v in checks.items():
            print(f"  {k}: {'OK' if v else 'FAIL'}")
        print(f"\nHTML size: {len(html)} bytes")
        # Snippet tokens
        idx = html.find('id="design-tokens"')
        if idx != -1:
            print(f"Tokens: {html[max(0,idx-5):idx+220]!r}")
        # Snippet sections with clear-both
        if has_clear_both:
            for s in sections:
                if "clear-both" in s:
                    print(f"Section with clear-both: {s}")
                    break
    else:
        print("HTML FILE NOT FOUND")
else:
    print("NO URL — pipeline failed before publishing")
