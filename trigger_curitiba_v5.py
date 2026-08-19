"""Trigger: reprocessa 'Curitiba Fitness' diretamente no worker e monitora + valida HTML."""
import sys, os, time, re, json
sys.path.insert(0, '/app/backend')
os.environ['DATABASE_URL'] = 'postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

LEAD_ID = "b5db65cd-e856-487a-9fac-5f5d6caaa62f"
TENANT_ID = 2
LEAD_NOME = "Curitiba Fitness"
MAX_WAIT = 900
POLL_INTERVAL = 5

db_url = "postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

# ── 1. Status do lead ──────────────────────────────────────────────────
with SessionLocal() as db:
    row = db.execute(text("SELECT nome, segmento, cidade, status, url_site FROM leads WHERE id=:i"), {"i": LEAD_ID}).fetchone()
    if not row:
        print("LEAD NOT FOUND"); sys.exit(1)
    rd = dict(row._mapping)
    print(f"LEAD: {rd['nome']} | segmento={rd.get('segmento')} | cidade={rd.get('cidade')} | status={rd['status']}")
    segmento = rd.get("segmento") or ""
    cidade = rd.get("cidade") or ""
    # Marcar capturado e resetar flags
    db.execute(text("UPDATE leads SET status='capturado', processado=false, erro_pipeline=NULL WHERE id=:id"), {"id": LEAD_ID})
    db.commit()
    print("Status -> capturado")

# ── 2. Enfileirar ──────────────────────────────────────────────────────
from backend.core.job_queue import enqueue
with SessionLocal() as db:
    job_id = enqueue(
        db,
        tipo="pipeline_lead",
        payload={
            "_lead_id_existente": LEAD_ID,
            "segmento": segmento,
            "cidade": cidade,
            "quantidade": 1,
            "_forcar_renovacao": True,
        },
        tenant_id=TENANT_ID,
        max_attempts=3,
        priority=1,
    )
print(f"JOB ENQUEUED: {job_id}")

# ── 3. Monitorar ───────────────────────────────────────────────────────
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

# ── 4. Resultado ───────────────────────────────────────────────────────
with SessionLocal() as db:
    final = db.execute(text("SELECT status, url_site, erro_pipeline, atualizado_em FROM leads WHERE id=:i"), {"i": LEAD_ID}).fetchone()
    fd = dict(final._mapping) if final else {}
    print(f"\nFINAL: status={fd.get('status')} | url={fd.get('url_site')} | erro={fd.get('erro_pipeline')} | atualizado={fd.get('atualizado_em')}")

# ── 5. Validar HTML ────────────────────────────────────────────────────
site_url = fd.get("url_site") or ""
if site_url:
    slug = re.sub(r'[^a-z0-9-]+', '-', LEAD_NOME.lower()).strip('-')
    found_path = None
    tenant_dir = f"/var/www/fralib/sites/{TENANT_ID}"
    if os.path.isdir(tenant_dir):
        for entry in sorted(os.listdir(tenant_dir)):
            p = os.path.join(tenant_dir, entry, "index.html")
            if os.path.isfile(p):
                print(f"Found site: {p}")
                found_path = p
                break
    if not found_path:
        for p in [f"/var/www/fralib/sites/{TENANT_ID}/{slug}/index.html", f"/var/www/fralib/sites/{TENANT_ID}/{LEAD_ID}/index.html"]:
            if os.path.isfile(p):
                found_path = p
                print(f"Found site (expected): {p}")
                break
    if found_path:
        with open(found_path) as f:
            html = f.read()
        checks = {
            "design_tokens_present": 'id="design-tokens"' in html,
            "unprefixed :root vars": '--bg:' in html,
            "hermetic sections clear-both": "clear-both" in html,
            "native FAQ <details>": "<details" in html.lower(),
            "native FAQ <summary>": "<summary" in html.lower(),
        }
        for k, v in checks.items():
            print(f"  {k}: {'OK' if v else 'FAIL'}")
        print(f"\nHTML size: {len(html)} bytes")
        idx = html.find('design-tokens')
        if idx != -1:
            print(f"Tokens snippet: {html[max(0,idx-10):idx+220]!r}")
    else:
        print("HTML FILE NOT FOUND — site may not have been published yet")
else:
    print("NO URL — site was not published")
