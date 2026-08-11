from sqlalchemy import create_engine, text

engine = create_engine("postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db")
with engine.connect() as conn:
    cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs' AND table_schema = 'public' ORDER BY ordinal_position")).fetchall()
    print("Jobs columns:", [c[0] for c in cols])

    col_names = [c[0] for c in cols]
    r = conn.execute(text("SELECT * FROM jobs WHERE id = 418")).fetchone()
    if r:
        print("Job:", dict(zip(col_names, r)))
    else:
        print("Job 418 not found")

    r = conn.execute(text("SELECT id, status, url_site, site_url, atualizado_em FROM leads WHERE id = :lid"),
                     {"lid": "38ffd3fb-c9a0-498c-9abc-c8a4e8f24853"}).fetchone()
    print("Lead:", r)

engine.dispose()
