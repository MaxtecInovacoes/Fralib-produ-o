"""Verify that generated frontend HTML matches its canonical partials."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

GENERATED = {
    "admin.html": [
        "_head.html",
        "_sidebar.html",
        "_main-header.html",
        "_view-overview.html",
        "_view-crm.html",
        "_view-uti.html",
        "_view-config.html",
        "_view-perfil.html",
        "_modals.html",
        "../shared/_modal-editor-site.html",
        "_scripts.html",
    ],
    "landing.html": [
        "_head.html",
        "_nav.html",
        "_hero.html",
        "_social-proof.html",
        "_problema.html",
        "_como-funciona.html",
        "_produto.html",
        "_funcionalidades.html",
        "_para-quem.html",
        "_planos.html",
        "_faq.html",
        "_beta-form.html",
        "_footer.html",
        "_scripts.html",
    ],
}

NONCANONICAL_TOP_LEVEL_HTML = ("landing2.html", "landing_backup.html")


def render_from_partials(name: str, partials: list[str]) -> str:
    parts_dir = FRONTEND / "partials" / Path(name).stem
    separator = "" if name == "admin.html" else "\n"
    return separator.join((parts_dir / partial).read_text(encoding="utf-8") for partial in partials)


def main() -> int:
    problems = []
    for name, partials in GENERATED.items():
        expected = render_from_partials(name, partials)
        actual = (FRONTEND / name).read_text(encoding="utf-8")
        if actual != expected:
            problems.append(
                f"{name} diverge dos partials canonicos; rode os builds frontend"
            )

    for name in NONCANONICAL_TOP_LEVEL_HTML:
        if (FRONTEND / name).exists():
            problems.append(f"HTML nao canonico presente: frontend/{name}")

    if problems:
        print("Frontend canonical contract failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("frontend canonical contract ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
