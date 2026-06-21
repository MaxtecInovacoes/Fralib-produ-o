import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_reprocess_endpoint_uses_only_job_queue():
    source = _read("backend/endpoints/pipeline_reprocess_endpoints.py")

    assert "background_tasks.add_task" not in source
    assert "executar_pipeline_lead_existente" not in source
    assert "job_queue_unavailable" in source
    assert "job_queue_rejected" in source


def test_legacy_queue_start_is_disabled():
    source = _read("backend/endpoints/pipeline_start_endpoints.py")

    assert "legacy_queue_disabled" in source
    assert "processar_fila" in source
    assert "INSERT INTO pipeline_queue" not in source
    assert '"queue_id"' not in source


def test_admin_processar_fila_uses_reprocess_route():
    source = _read("frontend/partials/admin/_scripts.html")

    assert "processar_fila: true" not in source
    assert "/api/pipeline/reprocessar/" in source
    assert "var processados = 0" in source
    assert "Nenhum lead capturado na fila." in source


def test_jobs_are_canonical_pipeline_execution_source():
    start = _read("backend/endpoints/pipeline_start_endpoints.py")
    status = _read("backend/endpoints/pipeline_status_endpoints.py")
    metrics = _read("backend/endpoints/metrics_endpoints.py")
    orchestrator = _read("backend/endpoints/pipeline_orchestrator_service.py")
    database = _read("backend/core/database.py")

    assert "FROM jobs" in status
    assert "pipeline_failures" in status
    assert "rodando = bool(current_job" in status
    assert "source\": \"jobs\"" in metrics
    assert "INSERT INTO pipeline_queue" not in start
    assert "UPDATE pipeline_queue" not in orchestrator
    stale_lock_fn = database[database.index("def reset_stale_pipeline_locks") :]
    assert "UPDATE public.pipeline_state" not in stale_lock_fn


def test_one_truth_operational_scripts_are_dry_run_first():
    audit = _read("scripts/audit_one_truth.py")
    reconcile = _read("scripts/reconcile_one_truth.py")

    assert "mode\": \"read_only\"" in audit
    assert "parser.add_argument(\"--apply\"" in reconcile
    assert "apply=args.apply" in reconcile
    assert "reap_stale_inventory_locks" in reconcile


def test_health_route_is_canonical_probe():
    server = _read("server.py")
    health = _read("backend/endpoints/health_endpoints.py")
    compose = _read("docker-compose.yml")
    hermes = _read("backend/services/hermes_watchdog.py")

    assert '@app.get("/health")' in server
    assert "def health_payload" in health
    assert '"worker_queue"' in health
    assert "def _check_meowhats" in health
    assert '"X-API-Key"' in health
    assert '"Authorization"' in health
    assert 'f"{url}/models"' in health
    assert "http://127.0.0.1:8000/health" in compose
    assert "http://127.0.0.1:8000/health" in hermes


def test_llm_cost_dashboards_use_canonical_ledger():
    superadmin = _read("backend/endpoints/superadmin_endpoints.py")
    metrics = _read("backend/endpoints/metrics_endpoints.py")
    alerting = _read("backend/services/alerting.py")

    active_superadmin = superadmin[superadmin.index('@router.get("/dashboard/overview")') :]
    assert "FROM llm_budget_ledger" in active_superadmin
    assert "FROM pipeline_token_usage" not in active_superadmin
    assert "FROM llm_budget_ledger" in metrics
    assert "FROM llm_budget_ledger" in alerting


def test_billing_decisions_do_not_read_compat_plan_column():
    checked_files = [
        "backend/services/credits_manager.py",
        "backend/endpoints/cron_endpoints.py",
        "backend/endpoints/pipeline_orchestrator_service.py",
        "worker.py",
    ]
    for rel in checked_files:
        source = _read(rel)
        assert "COALESCE(plan" not in source
        assert not re.search(r"\bSELECT\s+plan\b", source, flags=re.IGNORECASE)
        assert not re.search(r"\bu\.plan\b", source)


def test_sdr_paths_require_plan_gate():
    worker = _read("worker.py")
    cron = _read("backend/endpoints/cron_endpoints.py")

    assert "blocked_plan" in worker
    assert "plano_tem_sdr" in worker
    assert "plano_tem_sdr(user_plano, user_status, user_trial_expires_at)" in cron
    assert "u.trial_expires_at >= NOW()" not in cron
    assert "lower(COALESCE(u.plano, '')) IN ('trial','pro','beta','agency','ilimitado','admin')" in cron
    assert "lower(COALESCE(u.status, '')) NOT IN ('bloqueado','suspenso','cancelado','inadimplente')" in cron


def test_worker_exceptions_are_marked_as_job_failures():
    worker = _read("worker.py")
    process_block = worker[
        worker.index("async def _process_one") :
        worker.index("async def _main_loop")
    ]

    assert "except asyncio.TimeoutError:" in process_block
    assert "except Exception as exc:" in process_block
    assert 'sucesso, fase, mensagem = False, "worker_exception", str(exc)' in process_block
    assert "job_queue.mark_failure" in process_block


def test_trial_credit_is_consumed_only_after_franz_send_success():
    credits = _read("backend/services/credits_manager.py")
    pipeline = _read("backend/endpoints/pipeline_orchestrator_service.py")
    pipeline_tail = _read("backend/endpoints/pipeline_execution_core.py")
    worker = _read("worker.py")

    assert "trial_delivery_pending" in credits
    assert "pending_sdr_send" in pipeline
    assert "trial_credit_waits_for_sdr_delivery" in pipeline
    assert "consumir_credito_trial_entregue" in worker

    worker_block = worker[
        worker.index("if tipo in SDR_OUTREACH_JOB_TYPES") :
        worker.index('return False, "desconhecido"')
    ]
    send_success_block = worker_block[worker_block.index("if r.status_code == 200:") :]
    assert send_success_block.index("if r.status_code == 200:") < send_success_block.index(
        "consumir_credito_trial_entregue"
    ) < send_success_block.index("Franz: mensagem enviada")

    assert pipeline.index("execute_pipeline_tail") < pipeline.index("trial_credit_waits_for_sdr_delivery")
    enqueue_idx = pipeline_tail.index("Franz: enfileirado como job separado")
    credit_wait_idx = pipeline_tail.index("trial_credit_waits_for_sdr_delivery(", enqueue_idx)
    assert enqueue_idx < credit_wait_idx


def test_existing_lead_pipeline_preserves_franz_test_number():
    worker = _read("worker.py")
    pipeline = _read("backend/endpoints/pipeline_orchestrator_service.py")
    helpers = _read("backend/endpoints/pipeline_phase_helpers.py")

    worker_call = worker[
        worker.index("resultado = await executar_pipeline_lead_existente") :
        worker.index("else:", worker.index("resultado = await executar_pipeline_lead_existente"))
    ]
    assert 'test_number=payload.get("_bryan_test_number")' in worker_call

    reprocess_block = pipeline[pipeline.index("async def executar_pipeline_lead_existente") :]
    assert "test_number: str | None = None" in reprocess_block
    assert "build_existing_lead_pipeline_config" in pipeline
    assert "build_franz_outreach_payload" in pipeline
    assert "build_franz_outreach_payload" in helpers
    assert 'payload["_bryan_test_number"] = str(config.get("_bryan_test_number"))' in helpers


def test_controlled_pipeline_can_skip_franz_outreach():
    worker = _read("worker.py")
    pipeline = _read("backend/endpoints/pipeline_orchestrator_service.py")
    helpers = _read("backend/endpoints/pipeline_execution_helpers.py")

    assert 'skip_franz_outreach=bool(payload.get("_skip_franz_outreach"))' in worker
    assert "skip_franz_outreach: bool = False" in pipeline
    assert "build_existing_lead_pipeline_config" in pipeline
    assert 'if skip_franz_outreach:' in helpers
    assert 'config["_skip_franz_outreach"] = True' in helpers
    assert "manual_test_no_wpp" in pipeline
    assert "sdr_manual_test_blocked" in pipeline


def test_auth_falls_back_when_users_tenant_id_is_missing():
    source = _read("backend/core/auth.py")

    assert "SELECT role, status, tenant_id FROM users" in source
    assert "SELECT role, status, id AS tenant_id FROM users" in source
    assert "ProgrammingError" in source


def test_pipeline_gate_derives_test_database_url_without_losing_credentials():
    from pipeline import _derive_test_database_url

    source = (
        "postgresql://fralib_user"
        + ":pwvalue"
        + "@localhost:5433/fralib_db?sslmode=disable"
    )
    expected = (
        "postgresql://fralib_user"
        + ":pwvalue"
        + "@localhost:5433/fralib_test?sslmode=disable"
    )
    derived = _derive_test_database_url(source)

    assert derived == expected


def test_pipeline_cli_env_includes_repo_root_and_backend(monkeypatch):
    from pipeline import ROOT, _command_env

    monkeypatch.setenv("PYTHONPATH", "")
    env = _command_env()
    parts = env["PYTHONPATH"].split(os.pathsep)

    assert str(ROOT) in parts
    assert str(ROOT / "backend") in parts


def test_pipeline_status_exposes_current_job_phase():
    status = _read("backend/endpoints/pipeline_status_endpoints.py")
    orchestrator = _read("backend/endpoints/pipeline_orchestrator_service.py")

    assert "current_job" in status
    assert "fase_atual" in status
    assert "builder_renderer" in status
    assert "last_phase" in status
    assert "_set_pipeline_job_phase" in orchestrator
    assert '"phase": _phase_key' in orchestrator
    assert '"total": 11' in orchestrator


def test_admin_timeline_maps_builder_renderer_and_status_polling():
    source = _read("frontend/partials/admin/_scripts.html")

    assert "builder_renderer" in source
    assert "etapaTimelinePorFase" in source
    assert "normalizarEtapaTimeline" in source
    assert "atualizarTimelineComStatus" in source
    assert "d.current_job" in source
    assert "data.tipo === 'progress'" in source
    assert "LiteLLM FraLib" in source
