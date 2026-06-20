import os
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def test_pipeline_orchestrator_uses_split_support_modules():
    source = (ROOT / "backend" / "endpoints" / "pipeline_orchestrator_service.py").read_text(encoding="utf-8")

    # Accept both relative and absolute imports
    has_prd_builder_import = (
        "from backend.services.pipeline_prd_builder import" in source
        or "from services.pipeline_prd_builder import" in source
    )
    has_renderer_support_import = (
        "from backend.services.pipeline_renderer_support import" in source
        or "from services.pipeline_renderer_support import" in source
    )
    has_cache_control_import = (
        "from backend.services.pipeline_cache_control import" in source
        or "from services.pipeline_cache_control import" in source
    )
    has_flow_config_import = (
        "from backend.services.pipeline_flow_config import" in source
        or "from services.pipeline_flow_config import" in source
    )

    assert has_prd_builder_import, "pipeline_prd_builder import not found"
    assert has_renderer_support_import, "pipeline_renderer_support import not found"
    assert has_cache_control_import, "pipeline_cache_control import not found"
    assert has_flow_config_import, "pipeline_flow_config import not found"
    assert "def _build_skill_fast_prd" not in source
    assert "def _build_prompt_agent_prd" not in source
    assert "def _persist_failed_renderer_html" not in source
    assert "class _temporary_prd_cache_disabled" not in source


def test_pipeline_flow_flags_keep_existing_defaults(monkeypatch):
    from backend.services.pipeline_flow_config import (
        is_builder_fast_path,
        is_prompt_agent_flow,
        skip_html_quality_gate,
    )

    monkeypatch.delenv("FRALIB_PROMPT_AGENT_FLOW", raising=False)
    monkeypatch.delenv("FRALIB_BUILDER_FAST_PATH", raising=False)

    assert is_prompt_agent_flow({}) is True
    assert is_builder_fast_path({}) is True
    assert skip_html_quality_gate({}) is False
    assert is_prompt_agent_flow({"_disable_prompt_agent_flow": True}) is False
    assert is_builder_fast_path({"_disable_builder_fast_path": True}) is False


def test_pipeline_renderer_support_classifies_publication_errors():
    from backend.services.pipeline_renderer_support import (
        builder_job_id_for_state,
        is_renderer_or_publication_error,
    )

    assert is_renderer_or_publication_error(RuntimeError("HtmlQualityGate falhou")) is True
    assert is_renderer_or_publication_error(RuntimeError("lead sem telefone")) is False

    state = SimpleNamespace(pipeline_id="pipe 1", run_id="run 123")
    assert builder_job_id_for_state(state, {}) == "pipe-1"
    assert "run-run-123" in builder_job_id_for_state(state, {"_cold_run": True})


def test_pipeline_prd_builder_small_helpers():
    from backend.services.pipeline_prd_builder import (
        clean_public_text,
        ensure_prd_publication_identity,
        extract_media_urls,
        object_to_dict,
        review_highlights_from_reviews,
    )
    from unittest.mock import patch

    assert clean_public_text("A  ·  B") == "A B"
    # extract_media_urls only accepts URLs from supported hosts (unsplash, pexels, ctfassets)
    # Mock the reachability check for testing - patch where function is defined
    with patch("backend.services.pipeline_media.editorial_image_reachable", return_value=True), \
         patch("backend.services.pipeline_media.is_supported_editorial_image_url", return_value=True), \
         patch("backend.services.pipeline_media.normalize_editorial_image_url", side_effect=lambda x: x):
        result = extract_media_urls([
            {"url": "https://images.unsplash.com/photo-1"},
            {"src": "https://images.unsplash.com/photo-2"},
            "invalid",
        ])
        assert result == ["https://images.unsplash.com/photo-1", "https://images.unsplash.com/photo-2"]
    assert object_to_dict(SimpleNamespace(a=1)) == {"a": 1}
    assert review_highlights_from_reviews([{"text": "Atenciosa e acompanha dúvidas"}])

    prd = SimpleNamespace()
    state = SimpleNamespace(lead_slug="lead-x")
    ensure_prd_publication_identity(prd, state, tenant_id=2)
    assert prd.site_url == "https://seunegociofralib.site/sites/2/lead-x/"
    assert prd.canonical_url == prd.site_url


def test_temporary_prd_cache_disabled_restores_env(monkeypatch):
    from backend.services.pipeline_cache_control import temporary_prd_cache_disabled

    monkeypatch.setenv("DISABLE_PRD_CACHE", "0")
    with temporary_prd_cache_disabled(True):
        assert os.environ["DISABLE_PRD_CACHE"] == "1"
    assert os.environ["DISABLE_PRD_CACHE"] == "0"
