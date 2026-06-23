"""Test: garantir que nenhum codigo novo importa renderers legados.

Renderers legados (NAO usar):
- vite_react_renderer
- liam_renderer
- skill_based_renderer

So `openui_renderer` pode ser importado.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


# Arquivos que podem importar renderers legados (apenas imports para compat)
ALLOWED_FILES = {
    "backend/services/openui_renderer.py",  # pode comentar sobre alternativas
}


def test_no_legacy_renderers_in_pipeline():
    """Verifica que pipeline_orchestrator e builder_worker NAO importam legacy renderers."""
    forbidden = ["vite_react_renderer", "liam_renderer", "skill_based_renderer"]
    critical_files = [
        "backend/services/builder_worker.py",
        "backend/endpoints/pipeline_orchestrator_service.py",
        "backend/services/pipeline_executors.py",
        "backend/services/pipeline_phases.py",
        "backend/services/builder.py",
    ]

    for file in critical_files:
        path = ROOT / file
        if not path.exists():
            continue

        content = path.read_text(encoding="utf-8")
        for forbidden_mod in forbidden:
            # Check imports
            import_patterns = [
                f"from {forbidden_mod} import",
                f"import {forbidden_mod}",
            ]
            for pat in import_patterns:
                if pat in content:
                    # Permitido apenas se for em comentario
                    for line in content.split('\n'):
                        if pat in line and not line.strip().startswith('#'):
                            assert False, f"{file} importa {forbidden_mod}: {line.strip()}"


def test_openui_is_only_renderer_called():
    """Verifica que builder_worker chama apenas render_openui_site."""
    builder_worker = ROOT / "backend/services/builder_worker.py"
    if not builder_worker.exists():
        return

    content = builder_worker.read_text(encoding="utf-8")
    # Deve ter render_openui_site
    assert "render_openui_site" in content, "builder_worker deve chamar render_openui_site"

    # NAO deve ter render_vite_react_site (a menos que seja em comentario)
    for line in content.split('\n'):
        if "render_vite_react_site" in line and not line.strip().startswith('#'):
            assert False, f"builder_worker chama render_vite_react_site (legado): {line.strip()}"


def test_pipeline_phases_dont_call_legacy():
    """Verifica que as fases da pipeline NAO chamam legacy renderers."""
    phases_dir = ROOT / "backend/services/pipeline_fases"
    if not phases_dir.exists():
        return

    for f in phases_dir.glob("*.py"):
        content = f.read_text(encoding="utf-8")
        for forbidden in ["vite_react_renderer", "liam_renderer", "skill_based_renderer"]:
            if forbidden in content and not all(
                line.strip().startswith('#') for line in content.split('\n') if forbidden in line
            ):
                assert False, f"{f} referencia renderer legado: {forbidden}"


if __name__ == "__main__":
    # Rodar testes sem pytest
    tests = [
        test_no_legacy_renderers_in_pipeline,
        test_openui_is_only_renderer_called,
        test_pipeline_phases_dont_call_legacy,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"OK {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed+failed} passados")
    if failed > 0:
        sys.exit(1)
