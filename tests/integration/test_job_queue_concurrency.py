import os
import sys
import threading
import pytest
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

os.environ["TESTING"] = "true"
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres@localhost:5433/fralib_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from core import job_queue

assert "fralib_test" in TEST_DATABASE_URL
_parsed_test_db = urlsplit(TEST_DATABASE_URL)
assert (_parsed_test_db.hostname or "localhost") in {"localhost", "127.0.0.1", "::1"}
_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def ensure_jobs_schema():
    original_max_global = job_queue._MAX_PIPELINES_GLOBAL
    original_unlimited_tenants = set(job_queue._UNLIMITED_PIPELINE_TENANTS)
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    tipo VARCHAR(80) NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    tenant_id INTEGER,
                    status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    last_error TEXT,
                    last_phase TEXT,
                    checkpoint_id TEXT,
                    idempotency_key VARCHAR(120) UNIQUE,
                    worker_id VARCHAR(80),
                    worker_heartbeat TIMESTAMP,
                    next_retry_at TIMESTAMP DEFAULT NOW(),
                    criado_em TIMESTAMP DEFAULT NOW(),
                    iniciado_em TIMESTAMP,
                    concluido_em TIMESTAMP,
                    priority INTEGER NOT NULL DEFAULT 2
                )
                """
            )
        )
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_claim ON jobs (status, next_retry_at) WHERE status='pending'"))
        db.execute(text("DELETE FROM jobs"))
        db.commit()
    finally:
        db.close()
    try:
        yield
    finally:
        job_queue._MAX_PIPELINES_GLOBAL = original_max_global
        job_queue._UNLIMITED_PIPELINE_TENANTS = original_unlimited_tenants
        cleanup = SessionLocal()
        try:
            cleanup.execute(text("DELETE FROM jobs"))
            cleanup.commit()
        finally:
            cleanup.close()


@pytest.mark.integration
def test_claim_next_nao_duplica_job_em_workers_concorrentes():
    ids = []
    db = SessionLocal()
    try:
        for i in range(5):
            jid = job_queue.enqueue(db, tipo="franz_outreach", payload={"i": i}, tenant_id=i + 1)
            ids.append(jid)
    finally:
        db.close()

    claimed = []
    lock = threading.Lock()

    def worker(wid):
        local = SessionLocal()
        try:
            item = job_queue.claim_next(local, worker_id=f"w-{wid}")
            if item:
                with lock:
                    claimed.append(item["id"])
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(claimed) == 5
    assert len(set(claimed)) == 5
    assert set(claimed) == set(ids)


@pytest.mark.integration
def test_claim_next_nao_roda_duas_pipelines_do_mesmo_tenant_em_paralelo():
    job_queue._MAX_PIPELINES_GLOBAL = 10
    job_queue._UNLIMITED_PIPELINE_TENANTS = set()
    db = SessionLocal()
    try:
        first = job_queue.enqueue(db, tipo="pipeline_multiplos", payload={"i": 1}, tenant_id=31, priority=1)
        second = job_queue.enqueue(db, tipo="pipeline_lead", payload={"i": 2}, tenant_id=31, priority=1)
        other = job_queue.enqueue(db, tipo="pipeline_lead", payload={"i": 3}, tenant_id=32, priority=1)

        claimed_1 = job_queue.claim_next(db, worker_id="w-1", tipos=["pipeline_lead", "pipeline_multiplos"])
        claimed_2 = job_queue.claim_next(db, worker_id="w-2", tipos=["pipeline_lead", "pipeline_multiplos"])
    finally:
        db.close()

    assert claimed_1["id"] == first
    assert claimed_2["id"] == other
    assert claimed_2["id"] != second


@pytest.mark.integration
def test_claim_next_tenant_ilimitado_nao_roda_pipeline_em_paralelo():
    job_queue._MAX_PIPELINES_GLOBAL = 10
    job_queue._UNLIMITED_PIPELINE_TENANTS = {2}
    db = SessionLocal()
    try:
        first = job_queue.enqueue(db, tipo="pipeline_multiplos", payload={"i": 1}, tenant_id=2, priority=1)
        second = job_queue.enqueue(db, tipo="pipeline_lead", payload={"i": 2}, tenant_id=2, priority=1)

        claimed_1 = job_queue.claim_next(db, worker_id="w-1", tipos=["pipeline_lead", "pipeline_multiplos"])
        claimed_2 = job_queue.claim_next(db, worker_id="w-2", tipos=["pipeline_lead", "pipeline_multiplos"])
    finally:
        db.close()

    assert claimed_1["id"] == first
    assert claimed_2 is None
    assert second != first


@pytest.mark.integration
def test_claim_next_prioriza_pipeline_antes_de_franz():
    job_queue._MAX_PIPELINES_GLOBAL = 10
    db = SessionLocal()
    try:
        franz = job_queue.enqueue(db, tipo="franz_outreach", payload={"i": 1}, tenant_id=2, priority=1)
        pipeline = job_queue.enqueue(db, tipo="pipeline_lead", payload={"i": 2}, tenant_id=31, priority=1)

        claimed = job_queue.claim_next(
            db,
            worker_id="w-1",
            tipos=["pipeline_lead", "pipeline_multiplos", "franz_outreach"],
        )
    finally:
        db.close()

    assert claimed["id"] == pipeline
    assert claimed["id"] != franz


@pytest.mark.integration
def test_claim_next_respeita_limite_global_de_pipelines():
    job_queue._MAX_PIPELINES_GLOBAL = 1
    db = SessionLocal()
    try:
        first = job_queue.enqueue(db, tipo="pipeline_lead", payload={"i": 1}, tenant_id=2, priority=1)
        second = job_queue.enqueue(db, tipo="pipeline_lead", payload={"i": 2}, tenant_id=31, priority=1)

        claimed_1 = job_queue.claim_next(db, worker_id="w-1", tipos=["pipeline_lead"])
        claimed_2 = job_queue.claim_next(db, worker_id="w-2", tipos=["pipeline_lead"])
    finally:
        db.close()

    assert claimed_1["id"] == first
    assert claimed_2 is None
    assert second != first


@pytest.mark.integration
def test_claim_next_nao_reexecuta_job_sem_tentativas_restantes():
    db = SessionLocal()
    try:
        jid = job_queue.enqueue(
            db,
            tipo="pipeline_lead",
            payload={"i": 1},
            tenant_id=2,
            max_attempts=1,
        )
        db.execute(text("UPDATE jobs SET attempts=1 WHERE id=:id"), {"id": jid})
        db.commit()

        claimed = job_queue.claim_next(db, worker_id="w-1", tipos=["pipeline_lead"])
    finally:
        db.close()

    assert claimed is None
