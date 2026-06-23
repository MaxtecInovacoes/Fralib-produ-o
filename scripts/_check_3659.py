from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
load_dotenv()
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    print("== lead estado ==")
    r = c.execute(text("SELECT id, status, processado, tentativas, site_url, length(erro_pipeline) as err_len FROM leads WHERE id='sdr-test-1780601069'")).fetchone()
    print(" ", dict(r._mapping))
    print("== job 3659 ==")
    r = c.execute(text("SELECT id, status, attempts, last_phase, last_error, criado_em, iniciado_em, concluido_em FROM jobs WHERE id=3659")).fetchone()
    print(" ", dict(r._mapping))
