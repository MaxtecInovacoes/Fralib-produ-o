import json
import sys
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
