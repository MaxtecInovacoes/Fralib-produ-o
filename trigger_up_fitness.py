"""Find Up Fitness lead_id and optionally trigger the pipeline."""
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL") or "postgresql://fralib:fralib2024@postgres:5432/fralib"
engine = create_engine(db_url)

with engine.connect() as conn:
    # Find Up Fitness
    rows = conn.execute(
        text("SELECT id, nome, user_id, status FROM leads WHERE nome ILIKE :p LIMIT 10"),
        {"p": "%up fitness%"},
    ).fetchall()
    print("=== UP FITNESS LEADS ===")
    found = []
    for r in rows:
        row_dict = dict(r._mapping)
        print(row_dict)
        found.append(row_dict)

    if not found:
        # broader search
        rows2 = conn.execute(
            text("SELECT id, nome, user_id, status FROM leads WHERE nome ILIKE :p LIMIT 10"),
            {"p": "%fitness%"},
        ).fetchall()
        print("=== BROADER FITNESS ===")
        for r in rows2:
            print(dict(r._mapping))
        found = [dict(r._mapping) for r in rows2]

    if found:
        lead_id = str(found[0]["id"])
        print(f"\n=== TARGET LEAD_ID: {lead_id} ===")

        # Check pipeline state
        state_row = conn.execute(
            text("SELECT rodando, pausado FROM pipeline_state WHERE tenant_id=:tid LIMIT 1"),
            {"tid": found[0]["user_id"]},
        ).fetchone()
        print(f"Pipeline state: {dict(state_row._mapping) if state_row else 'NO STATE'}")

        # Trigger reprocessar via REST API
        import requests
        base = os.environ.get("BACKEND_URL", "http://localhost:8000")
        # need a valid token - check env
        token = os.environ.get("PIPELINE_TOKEN", "")
        if not token:
            print("NO TOKEN - need X-Pipeline-Bypass or auth header")
            # try the bypass approach via curl
            import subprocess
            url = f"{base}/api/v1/pipeline/reprocessar/{lead_id}"
            print(f"Would call: POST {url}")
            print("Manual trigger needed with auth")
        else:
            resp = requests.post(
                f"{base}/api/v1/pipeline/reprocessar/{lead_id}",
                headers={"Authorization": f"Bearer {token}", "X-Pipeline-Bypass": "fralib-dev-2026"},
                json={"forcar_renovacao": True},
                timeout=10,
            )
            print(f"Trigger response: {resp.status_code} {resp.text[:300]}")
