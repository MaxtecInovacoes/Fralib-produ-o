"""Quick status check for Curitiba Fitness pipeline."""
import sys, os
sys.path.insert(0, '/app/backend')
os.environ['DATABASE_URL'] = 'postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    row = conn.execute(text("SELECT status, url_site, atualizado_em, erro_pipeline FROM leads WHERE id=:i"), {"i":"b5db65cd-e856-487a-9fac-5f5d6caaa62f"}).fetchone()
    print("LEAD:", dict(row._mapping) if row else "NOT FOUND")
    jobs = conn.execute(text("SELECT id, tipo, status FROM jobs WHERE status IN ('pending','running','queued') ORDER BY criado_em DESC LIMIT 5")).fetchall()
    print("ACTIVE JOBS:", [dict(j._mapping) for j in jobs] if jobs else "NONE")
