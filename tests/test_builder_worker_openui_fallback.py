import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def test_vite_react_falls_back_to_openui(monkeypatch, tmp_path):
    import backend.services.vite_react_renderer as vite_mod
    import services.openui_renderer as openui_mod
    from backend.services import builder_worker

    monkeypatch.setenv("FRALIB_BUILDER_ENGINE", "vite_react")
    monkeypatch.setenv(
        "FRALIB_BUILDER_SANDBOX_ROOT",
        str(tmp_path / "workspaces").replace("\\", "/"),
    )
    monkeypatch.setenv("FRALIB_BUILDER_MANIFEST_DIR", str(tmp_path / "manifests"))

    def fail_vite(*_args, **_kwargs):
        raise RuntimeError("forced vite failure")

    def fake_openui(*_args, **_kwargs):
        html = (
            "<!doctype html><html><head><title>Fallback Smoke</title></head>"
            "<body><main><section><h1>Fallback OpenUI OK</h1><p>"
            + ("conteudo seguro " * 40)
            + "</p></section></main></body></html>"
        )
        return SimpleNamespace(
            html=html,
            model="fake-openui",
            attempts=[{"model": "fake-openui", "status": "success"}],
            elapsed_ms=7,
        )

    seen_publication_engine = {}

    def fake_prepare(html, facts, *, engine=None):
        seen_publication_engine["engine"] = engine
        return html

    monkeypatch.setattr(vite_mod, "render_vite_react_site", fail_vite)
    monkeypatch.setattr(openui_mod, "render_openui_site", fake_openui)
    monkeypatch.setattr(builder_worker, "_prepare_builder_html_for_publication", fake_prepare)

    result = builder_worker.render_site_with_builder(
        {
            "business": {"name": "Fallback Smoke", "segmento": "academia"},
            "seo_keywords": ["academia"],
        },
        tenant_id="fallback-smoke",
        job_id="vite-openui",
    )

    assert result["engine"] == "openui_fallback"
    assert result["model"] == "fake-openui"
    assert seen_publication_engine["engine"] == "openui"
    assert Path(result["index_path"]).exists()
    assert any(item.get("status") == "failed_openui_fallback" for item in result["attempts"])

    meta = json.loads((Path(result["output_dir"]) / "builder-render.json").read_text(encoding="utf-8"))
    assert meta["engine"] == "openui_fallback"
    assert meta["attempts"][0]["status"] == "failed_openui_fallback"


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
