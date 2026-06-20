import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "core"))

import job_queue


def test_builder_failure_is_detected_from_wrapped_pipeline_error():
    assert (
        job_queue.normalizar_fase_falha(
            "pipeline", "RuntimeError: builder_renderer falhou com exit_code=1"
        )
        == "builder_renderer"
    )


def test_retry_feedback_explains_automatic_retry_without_raw_error():
    payload = job_queue.formatar_feedback_job(
        job_id=349,
        status="pending",
        fase="pipeline",
        erro_tecnico="RuntimeError: builder_renderer falhou com exit_code=1",
        attempts=1,
        max_attempts=3,
    )

    assert payload["type"] == "pipeline_retry"
    assert payload["fase"] == "builder_renderer"
    assert "nova tentativa foi agendada automaticamente" in payload["message"]
    assert "exit_code" not in payload["message"]


def test_final_feedback_explains_next_actions_without_raw_error():
    payload = job_queue.formatar_feedback_job(
        job_id=349,
        status="failed_permanent",
        fase="pipeline",
        erro_tecnico="RuntimeError: builder_renderer falhou com exit_code=1",
        attempts=3,
        max_attempts=3,
    )

    assert payload["type"] == "pipeline_error"
    assert payload["title"] == "Não foi possível concluir este site"
    assert "Tentar novamente" in payload["message"]
    assert "exit_code" not in payload["message"]


def test_mark_success_aggregates_llm_cost_for_job_id_with_run_fallback():
    engine = create_engine("sqlite:///:memory:")
    raw = engine.raw_connection()
    raw.create_function("NOW", 0, lambda: "2026-06-04T12:00:00")
    raw.close()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY,
                    status TEXT,
                    concluido_em TEXT,
                    last_error TEXT,
                    llm_tokens_used INTEGER DEFAULT 0,
                    llm_cost_estimate NUMERIC DEFAULT 0,
                    run_id TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE llm_budget_ledger (
                    job_id INTEGER,
                    run_id TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    cache_created_tokens INTEGER,
                    cost_usd NUMERIC
                )
                """
            )
        )
        conn.execute(text("INSERT INTO jobs (id,status,run_id) VALUES (10,'running','run-a')"))
        conn.execute(
            text(
                """
                INSERT INTO llm_budget_ledger VALUES
                (10, 'run-a', 100, 50, 10, 0, 0.12),
                (11, 'run-a', 900, 90, 0, 0, 0.99),
                (NULL, 'run-a', 1, 2, 3, 4, 0.03)
                """
            )
        )

    with Session(engine) as db:
        job_queue.mark_success(db, 10)
        row = db.execute(
            text("SELECT status,llm_tokens_used,llm_cost_estimate FROM jobs WHERE id=10")
        ).fetchone()

    assert row[0] == "completed"
    assert row[1] == 170
    assert float(row[2]) == 0.15


def test_reap_dead_workers_restores_attempt_budget_after_worker_death():
    engine = create_engine("sqlite:///:memory:")
    raw = engine.raw_connection()
    raw.create_function("NOW", 0, lambda: "2026-06-04T12:00:00")
    raw.close()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY,
                    status TEXT,
                    attempts INTEGER,
                    max_attempts INTEGER,
                    last_error TEXT,
                    worker_id TEXT,
                    worker_heartbeat TEXT,
                    next_retry_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO jobs (id,status,attempts,max_attempts,last_error,worker_id,worker_heartbeat,next_retry_at)
                VALUES (1,'running',1,1,'builder_renderer timeout','worker-a','2026-06-04T11:50:00','2026-06-04T11:50:00')
                """
            )
        )

    with Session(engine) as db:
        revived = job_queue.reap_dead_workers(db, dead_after_minutes=5)
        row = db.execute(
            text("SELECT status,attempts,last_error,worker_id,worker_heartbeat FROM jobs WHERE id=1")
        ).fetchone()

    assert revived == 1
    assert row[0] == "pending"
    assert row[1] == 0
    assert row[2].endswith("worker_died")
    assert row[3] is None
    assert row[4] is None
