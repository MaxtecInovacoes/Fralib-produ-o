"""Check budget and trigger a fresh lead."""
import sys, os, time
sys.path.insert(0, '/app/backend')
os.environ['DATABASE_URL'] = 'postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.core.job_queue import enqueue

LEAD_ID = "b5db65cd-e856-487a-9fac-5f5d6caaa62f"
TENANT_ID = 2
MAX_WAIT = 900
POLL_INTERVAL = 5

db_url = "postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

# 1. Check credits and daily usage
with SessionLocal() as db:
    # Try creditos_llm table
    try:
        cred = db.execute(text("SELECT creditos_diarios, creditos_usados, ultimo_reset FROM creditos_llm WHERE tenant_id=:t"), {"t": TENANT_ID}).fetchone()
        if cred:
            print(f"CREDITOS: {dict(cred._mapping)}")
        else:
            print("NO CREDITOS_LLM ROW")
    except Exception as e:
        print(f"creditos_llm error: {e}")

    # Daily token sum
    try:
        usage = db.execute(text("SELECT SUM(input_tokens + output_tokens) as total, COUNT(*) as calls FROM llm_usage WHERE criado_em >= CURRENT_DATE")).fetchone()
        print(f"DAILY USAGE: {dict(usage._mapping) if usage else 'NONE'}")
    except Exception as e:
        print(f"usage error: {e}")

    # Check validar_permissao_pipeline directly
    try:
        from backend.endpoints.pipeline_endpoints import validar_permissao_pipeline
        perm = validar_permissao_pipeline(db, TENANT_ID)
        print(f"PERMISSAO: {perm}")
    except Exception as e:
        print(f"perm error: {e}")

    # Find fresh lead (status != concluido, erro_pipeline, cancelado)
    try:
        rows = db.execute(
            text("SELECT id, nome, status FROM leads WHERE user_id=:u AND status NOT IN ('concluido','erro_pipeline','cancelado') ORDER BY criado_em DESC LIMIT 5")
        ).fetchall()
        print("=== LEADS EM PROGRESSO ===")
        for r in rows:
            print(dict(r._mapping))
        if not rows:
            print("NENHUM LEAD EM PROGRESSO — usando Curitiba Fitness")
    except Exception as e:
        print(f"lead query error: {e}")

# 2. Try to enqueue Curitiba Fitness anyway (budget may have reset since last attempt)
print("\n=== ENQUEUE ===")
with SessionLocal() as db:
    try:
        from backend.endpoints.pipeline_endpoints import validar_permissao_pipeline
        perm = validar_permissao_pipeline(db, TENANT_ID)
        if not perm.get("allowed"):
            print(f"BLOQUEADO: {perm}")
            sys.exit(0)
        print(f"Permissao OK: {perm.get('message', '')}")
    except Exception as e:
        print(f"perm check failed: {e}")

    # Reset lead
    db.execute(text("UPDATE leads SET status='capturado', processado=false, erro_pipeline=NULL WHERE id=:id"), {"id": LEAD_ID})
    db.commit()
    print("Lead -> capturado")

    job_id = enqueue(
        db,
        tipo="pipeline_lead",
        payload={"_lead_id_existente": LEAD_ID, "quantidade": 1, "_forcar_renovacao": True},
        tenant_id=TENANT_ID,
        max_attempts=1,
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
        s = db.execute(text("SELECT status FROM leads WHERE id=:i"), {"i": LEAD_ID}).fetchone()
        cur = (s.status if s else "?")
        if cur != last_status:
            elapsed = int(time.time() - t0)
            print(f"  [{elapsed}s] status={cur}")
            last_status = cur
        if cur in ("concluido", "erro_pipeline", "cancelado"):
            break

# 4. Result
with SessionLocal() as db:
    final = db.execute(text("SELECT status, url_site, erro_pipeline FROM leads WHERE id=:i"), {"i": LEAD_ID}).fetchone()
    fd = dict(final._mapping) if final else {}
    print(f"\nFINAL: status={fd.get('status')} | url={fd.get('url_site')} | erro={fd.get('erro_pipeline')}")

# 5. Validate HTML
site_url = fd.get("url_site") or ""
if site_url:
    slug = "curitiba-fitness"
    found_path = None
    tenant_dir = f"/var/www/fralib/sites/{TENANT_ID}"
    if os.path.isdir(tenant_dir):
        for entry in sorted(os.listdir(tenant_dir)):
            p = os.path.join(tenant_dir, entry, "index.html")
            if os.path.isfile(p):
                mtime = os.path.getmtime(p)
                if mtime > t0:
                    print(f"NEW SITE: {p} (mtime={time.ctime(mtime)})")
                    found_path = p
                    break
    if not found_path:
        for p in [f"/var/www/fralib/sites/{TENANT_ID}/{slug}/index.html"]:
            if os.path.isfile(p):
                found_path = p
                break
    if found_path:
        with open(found_path) as f:
            html = f.read()
        checks = {
            "design_tokens (id=design-tokens)": 'id="design-tokens"' in html,
            "unprefixed :root vars": '--bg:' in html,
            "hermetic sections clear-both": "clear-both" in html,
            "native FAQ details": "<details" in html.lower(),
            "native FAQ summary": "<summary" in html.lower(),
        }
        for k, v in checks.items():
            print(f"  {k}: {'OK' if v else 'FAIL'}")
        print(f"HTML size: {len(html)} bytes")
        idx = html.find('design-tokens')
        if idx != -1:
            print(f"Tokens: {html[max(0,idx-5):idx+200]!r}")
    else:
        print("HTML FILE NOT FOUND")
else:
    print("NO URL — pipeline failed before publishing")
