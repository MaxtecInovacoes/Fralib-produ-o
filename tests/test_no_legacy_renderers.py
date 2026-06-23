"""Test: garantir que engines legados nao voltem para a rota padrao.

Renderers proibidos:
- liam_renderer
- skill_based_renderer

`vite_react_renderer` existe como engine de compatibilidade explicita, acionada
somente por FRALIB_BUILDER_ENGINE=vite_react.
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


def test_no_forbidden_renderers_in_pipeline():
    """Verifica que pipeline_orchestrator e builder_worker NAO importam renderers proibidos."""
    forbidden = ["liam_renderer", "skill_based_renderer"]
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


def test_openui_is_default_and_vite_is_explicit_engine():
    """OpenUI deve existir e Vite/React so pode ser acionado por engine explicita."""
    builder_worker = ROOT / "backend/services/builder_worker.py"
    if not builder_worker.exists():
        return

    content = builder_worker.read_text(encoding="utf-8")
    assert "render_openui_site" in content, "builder_worker deve chamar render_openui_site"
    assert "FRALIB_BUILDER_ENGINE" in content, "engine precisa ser controlada por env explicita"
    assert 'os.getenv("FRALIB_BUILDER_ENGINE", "openui")' in content, "OpenUI deve ser fallback padrao"
    assert 'engine == "vite_react"' in content, "vite_react deve ser branch explicito, nao fallback implicito"


def test_pipeline_phases_dont_call_legacy():
    """Verifica que as fases da pipeline NAO chamam legacy renderers."""
    phases_dir = ROOT / "backend/services/pipeline_fases"
    if not phases_dir.exists():
        return

    for f in phases_dir.glob("*.py"):
        content = f.read_text(encoding="utf-8")
        for forbidden in ["liam_renderer", "skill_based_renderer"]:
            if forbidden in content and not all(
                line.strip().startswith('#') for line in content.split('\n') if forbidden in line
            ):
                assert False, f"{f} referencia renderer legado: {forbidden}"


if __name__ == "__main__":
    # Rodar testes sem pytest
    tests = [
        test_no_forbidden_renderers_in_pipeline,
        test_openui_is_default_and_vite_is_explicit_engine,
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
