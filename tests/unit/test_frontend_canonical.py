from scripts.verify_frontend_canonical import GENERATED, render_from_partials


def test_generated_frontend_matches_canonical_partials():
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    for name, partials in GENERATED.items():
        assert (frontend / name).read_text(encoding="utf-8") == render_from_partials(
            name, partials
        )


def test_admin_toast_global_contract():
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    toast_js = (frontend / "js" / "toast.js").read_text(encoding="utf-8")
    admin_html = (frontend / "admin.html").read_text(encoding="utf-8")

    assert "window.Toast" in toast_js
    for method in ("success", "error", "warning", "info"):
        assert f"window.Toast.{method}" in toast_js
        assert f"Toast.{method}" in admin_html
