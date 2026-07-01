import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


# TESTS MOVED/REMOVED Sprint 14.3:
# - test_vite_react_falls_back_to_openui: DELETED — OpenUI fallback removido do builder_worker.
#   O bloco except + _openui_fallback_allowed() foi eliminado.
#   O engine Vite/React agora NUNCA cai para OpenUI.
# - test_vite_react_fails_closed_without_explicit_openui_fallback: MANTIDO (é o comportamento esperado)
def test_vite_react_fails_closed_without_explicit_openui_fallback(monkeypatch, tmp_path):
    import backend.services.vite_react_renderer as vite_mod
    from backend.services import builder_worker

    monkeypatch.setenv("FRALIB_BUILDER_ENGINE", "vite_react")
    monkeypatch.setenv(
        "FRALIB_BUILDER_SANDBOX_ROOT",
        str(tmp_path / "workspaces").replace("\\", "/"),
    )
    monkeypatch.setenv("FRALIB_BUILDER_MANIFEST_DIR", str(tmp_path / "manifests"))

    def fail_vite(*_args, **_kwargs):
        raise RuntimeError("forced vite failure")

    monkeypatch.setattr(vite_mod, "render_vite_react_site", fail_vite)

    with pytest.raises(RuntimeError, match="forced vite failure"):
        builder_worker.render_site_with_builder(
            {
                "business": {"name": "Fail Closed Smoke", "segmento": "academia"},
                "seo_keywords": ["academia"],
            },
            tenant_id="fail-closed-smoke",
            job_id="vite-no-openui",
        )


def test_vite_react_aplica_defaults_canonicos_do_runtime(monkeypatch, tmp_path):
    import backend.services.vite_react_renderer as vite_mod
    from backend.services import builder_worker

    monkeypatch.delenv("FRALIB_VITE_LLM_POLICY", raising=False)
    monkeypatch.delenv("FRALIB_VITE_CINEMATIC_STUDIO", raising=False)
    monkeypatch.delenv("FRALIB_VITE_DISABLE_STUDIO_FALLBACK", raising=False)
    monkeypatch.delenv("FRALIB_ALLOW_OPENUI_FALLBACK", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.setenv("FRALIB_BUILDER_ENGINE", "vite_react")
    monkeypatch.setenv(
        "FRALIB_BUILDER_SANDBOX_ROOT",
        str(tmp_path / "workspaces").replace("\\", "/"),
    )
    monkeypatch.setenv("FRALIB_BUILDER_MANIFEST_DIR", str(tmp_path / "manifests"))

    captured = {}

    def fake_vite(*_args, **_kwargs):
        captured["llm_policy"] = os.getenv("FRALIB_VITE_LLM_POLICY")
        captured["cinematic"] = os.getenv("FRALIB_VITE_CINEMATIC_STUDIO")
        captured["studio_fallback"] = os.getenv("FRALIB_VITE_DISABLE_STUDIO_FALLBACK")
        captured["openui_fallback"] = os.getenv("FRALIB_ALLOW_OPENUI_FALLBACK")
        captured["builder_force_env"] = os.getenv("FRALIB_BUILDER_FORCE_ENV_ANTHROPIC")
        captured["anthropic_base_url"] = os.getenv("ANTHROPIC_BASE_URL")
        return SimpleNamespace(
            html="<!doctype html><html><head><title>React OK</title></head><body>" + ("x" * 300) + "</body></html>",
            model="studio-copy-only",
            attempts=[{"model": "studio-template", "status": "studio_copy_only_success"}],
            elapsed_ms=11,
            source_files=[],
        )

    monkeypatch.setattr(vite_mod, "render_vite_react_site", fake_vite)

    result = builder_worker.render_site_with_builder(
        {
            "business": {"name": "Canonical Runtime", "segmento": "nutricionista"},
            "seo_keywords": ["nutricionista esportivo"],
            "og_image": "https://example.com/og.jpg",
        },
        tenant_id="canonical-runtime",
        job_id="vite-defaults",
    )

    assert result["engine"] == "vite_react"
    assert captured == {
        "llm_policy": "creative_plan",
        "cinematic": "1",
        "studio_fallback": "1",
        "openui_fallback": "0",
        "builder_force_env": "1",
        "anthropic_base_url": "https://api.kpalabz.com/v1",
    }


def test_builder_sandbox_cleanup_remove_apenas_jobs_antigos(tmp_path, monkeypatch):
    from backend.services import builder_worker

    root = tmp_path / "fralib_builder"
    old_job = root / "tenant-2" / "job-old"
    fresh_job = root / "tenant-2" / "job-fresh"
    outside_name = root / "tenant-2" / "not-a-job"
    for path in (old_job, fresh_job, outside_name):
        path.mkdir(parents=True)
        (path / "marker.txt").write_text("ok", encoding="utf-8")

    old_ts = time.time() - 48 * 3600
    fresh_ts = time.time()
    for path in (old_job, old_job / "marker.txt"):
        os.utime(path, (old_ts, old_ts))
    for path in (fresh_job, fresh_job / "marker.txt", outside_name, outside_name / "marker.txt"):
        os.utime(path, (fresh_ts, fresh_ts))

    monkeypatch.setenv("FRALIB_BUILDER_SANDBOX_MAX_AGE_HOURS", "12")
    builder_worker._cleanup_builder_sandbox(str(root))

    assert not old_job.exists()
    assert fresh_job.exists()
    assert outside_name.exists()


def test_publicacao_canonica_bloqueia_openui_em_producao(tmp_path, monkeypatch):
    from backend.services import builder_worker

    monkeypatch.setenv("FRALIB_ENV", "prod")
    monkeypatch.setenv("FRALIB_BUILDER_ENGINE", "openui")

    with pytest.raises(RuntimeError, match="publicacao bloqueada"):
        builder_worker.render_site_with_builder(
            {
                "business": {"name": "Locked Smoke", "segmento": "academia"},
                "seo_keywords": ["academia"],
            },
            tenant_id="locked-smoke",
            job_id="openui-prod",
        )


def test_assert_canonical_builder_publication_rejeita_meta_nao_canonica(tmp_path, monkeypatch):
    from backend.services import builder_worker

    output_dir = tmp_path / "dist"
    output_dir.mkdir()
    (output_dir / "builder-render.json").write_text(
        json.dumps({"engine": "openui", "model": "fake", "attempts": []}),
        encoding="utf-8",
    )

    monkeypatch.setenv("FRALIB_STRICT_CANONICAL_PUBLISH", "1")

    with pytest.raises(RuntimeError, match="artefato nao canonico"):
        builder_worker.assert_canonical_builder_publication_allowed(
            output_dir,
            html='<!doctype html><html data-renderer="builder" data-builder-engine="openui"><head></head><body></body></html>',
        )


def test_ensure_builder_renderer_marker_normaliza_engine_divergente():
    from backend.services.builder_worker import _ensure_builder_renderer_marker

    html = '<!doctype html><html lang="pt-BR" data-renderer="builder" data-builder-engine="openui"><head></head><body></body></html>'
    updated = _ensure_builder_renderer_marker(html, engine="vite_react")

    assert 'data-builder-engine="vite_react"' in updated
    assert 'data-builder-engine="openui"' not in updated


def test_publication_head_keeps_og_and_json_ld_image_aligned():
    from backend.services.builder_worker import _ensure_builder_publication_head

    html = """<!doctype html><html><head>
<meta property="og:image" content="https://old.example/old.jpg">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness","name":"Academia","image":"https://old.example/schema.jpg"}</script>
</head><body></body></html>"""
    updated = _ensure_builder_publication_head(
        html,
        {
            "publication": {"og_image": "https://cdn.example/new.jpg"},
            "business": {"name": "Academia"},
        },
    )

    assert 'property="og:image" content="https://cdn.example/new.jpg"' in updated
    assert '"image":"https://cdn.example/new.jpg"' in updated
    assert "schema.jpg" not in updated
