from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_deploy_contract_requires_llms_static_publish():
    source = _read("scripts/check_deploy_contract.py")
    hook = _read("scripts/post-receive")

    assert "frontend/llms.txt" in source
    assert "$WEB_DIR/llms.txt" in source
    assert "frontend/llms.txt" in hook
    assert "$WEB_DIR/llms.txt" in hook


def test_rate_limiter_can_use_distributed_storage():
    source = _read("backend/core/rate_limiter.py")

    assert "FRALIB_RATE_LIMIT_STORAGE_URI" in source
    assert "REDIS_URL" in source
    assert "storage_uri=_uri" in source
    assert "in_memory_fallback_enabled=True" in source
    assert "headers_enabled" in source


def test_docker_runtime_runs_app_as_non_root():
    dockerfile = _read("Dockerfile")
    compose = _read("docker-compose.yml")

    assert "useradd --system" in dockerfile
    assert "chown -R fralib:fralib /app /var/www/fralib /tmp/fralib_builder" in dockerfile
    assert "USER fralib" in dockerfile
    assert "healthcheck:" in compose
    assert "http://127.0.0.1:8000/health" in compose


def test_public_metrics_do_not_expose_global_tenant_data():
    source = _read("backend/endpoints/metrics_endpoints.py")
    public_block = source.split('@router.get("/public")', 1)[1].split('@router.get("/db-pool")', 1)[0]

    assert "_get_leads_stats()" not in public_block
    assert "_get_pipeline_stats()" not in public_block
    assert "require_metrics_admin" in source
    assert "Depends(require_metrics_admin)" in source


def test_provider_base_urls_are_allowlisted_before_persist_or_runtime_use():
    endpoints = _read("backend/endpoints/provider_keys_endpoints.py")
    manager = _read("backend/services/ia_manager.py")
    config = _read("backend/core/config.py")

    assert "api.aibee.cloud" in config
    assert "ia.namehost.com.br" in config
    assert "def _validate_base_url" in endpoints
    assert "is_allowed_llm_url(base_url)" in endpoints
    assert "base_url_not_allowed" in manager
    assert "is_allowed_llm_url(base_url)" in manager


def test_sse_frontend_uses_short_lived_ticket_instead_of_jwt_query():
    endpoint = _read("backend/endpoints/sse_endpoints.py")
    frontend_files = [
        "frontend/partials/admin/_scripts.html",
        "frontend/admin.html",
    ]

    assert '@router.post("/stream-token")' in endpoint
    assert "SSE_STREAM_PURPOSE" in endpoint
    assert "require_stream_ticket=True" in endpoint
    assert "require_stream_ticket=False" in endpoint

    for relative in frontend_files:
        source = _read(relative)
        assert "/api/logs/stream-token" in source
        assert "/api/logs/stream?ticket=" in source
        assert "/api/logs/stream?token=" not in source


def test_builder_publish_contract_excludes_internal_render_metadata():
    source = _read("backend/services/builder_worker.py")

    assert "_INTERNAL_BUILDER_ARTIFACTS" in source
    assert "builder-render.json" in source
    assert "vite-render.json" in source
    assert "_ignore_internal_builder_artifacts" in source
    assert 'path.suffix == ".map"' in source
