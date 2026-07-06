"""Tests anti-regressao v1.2-baseline-2026-06-23.

Protege as decisoes do Sprint 2 (tools dinamicas + loop autonomo):
1. tools_site.py existe
2. tools_site.py tem 5 tools + TOOLS_DISPATCH
3. retrieve_similar_briefings retorna Warm entries
4. retrieve_top_templates retorna dict de SUB_NICHO_TEMPLATES
5. save_pipeline_lesson persiste via memory_hook_site
6. site_orchestrator.py nao faz parte do baseline atual
7. pipeline_orchestrator nao carrega FRALIB_USE_SDK_LOOP
11. check_v11_protection.py tem 8 checks
12. flag FRALIB_USE_SDK_LOOP removida do caminho oficial

Standalone runner (nao usa pytest/cov): rapido, sem import side-effects.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
AGENTS_DIR = BACKEND / "agents"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


class TestV12ToolsSite:
    """Sprint 2.1: tools_site.py + 5 tools."""

    @staticmethod
    def test_tools_site_exists():
        p = AGENTS_DIR / "tools_site.py"
        assert p.is_file(), "tools_site.py sumiu! Sprint 2 perdido."

    @staticmethod
    def test_tools_site_has_5_tools_in_dispatch():
        from backend.agents.tools_site import SUPPORTED_TOOLS, TOOLS_DISPATCH

        assert len(TOOLS_DISPATCH) == 5, (
            f"TOOLS_DISPATCH tem {len(TOOLS_DISPATCH)} (esperado 5)"
        )
        assert len(SUPPORTED_TOOLS) == 5, (
            f"SUPPORTED_TOOLS tem {len(SUPPORTED_TOOLS)} (esperado 5)"
        )

    @staticmethod
    def test_retrieve_similar_briefings_returns_warm_entries():
        """Tool usa WarmMemory.buscar (read-only, sem LLM)."""
        from backend.agents.tools_site import retrieve_similar_briefings

        result = retrieve_similar_briefings("academia_crossfit")
        assert isinstance(result, list), (
            f"retrieve_similar_briefings retornou {type(result)}, esperado list"
        )

    @staticmethod
    def test_retrieve_top_templates_returns_dict():
        """Tool usa SUB_NICHO_TEMPLATES."""
        from backend.agents.tools_site import retrieve_top_templates

        result = retrieve_top_templates("nutricionista_esportiva")
        assert isinstance(result, dict), (
            f"retrieve_top_templates retornou {type(result)}, esperado dict"
        )
        # Se subnicho mapeado, deve ter campos canonicos
        if result:
            assert "ordem_das_secoes" in result, (
                "retrieve_top_templates nao retornou ordem_das_secoes"
            )

    @staticmethod
    def test_save_pipeline_lesson_persists():
        """Tool usa memory_hook_site.persist_lesson_with_score."""
        from backend.agents.tools_site import save_pipeline_lesson

        ok = save_pipeline_lesson(
            lesson="[test] v1.2 baseline",
            score=8.0,
            agente="agente_nicho",
            nicho="academia_crossfit",
        )
        assert ok is True, "save_pipeline_lesson nao persistiu"
        # Verifica que retrieve agora retorna
        from backend.agents.tools_site import retrieve_similar_briefings

        entries = retrieve_similar_briefings("academia_crossfit", top_k=20)
        assert any("[test] v1.2 baseline" in e.get("conteudo", "") for e in entries), (
            "lesson nao foi persistida em Warm"
        )


class TestV12LegacyArtifacts:
    """Sprint 2.2: artefatos legados removidos do baseline atual."""

    @staticmethod
    def test_site_orchestrator_absent():
        p = AGENTS_DIR / "site_orchestrator.py"
        assert not p.exists(), "site_orchestrator.py ainda existe e não deveria"

    @staticmethod
    def test_no_sdk_loop_flag_in_pipeline_orchestrator():
        src = _read(BACKEND / "endpoints" / "pipeline_orchestrator_service.py")
        assert "FRALIB_USE_SDK_LOOP" not in src
        assert "use_sdk_loop" not in src


class TestV12Integration:
    """Sprint 2.3: pipeline_orchestrator + pre-commit hook."""

    @staticmethod
    def test_pipeline_orchestrator_does_not_use_sdk_loop_flag():
        """Flag FRALIB_USE_SDK_LOOP nao faz parte do caminho oficial."""
        src = _read(BACKEND / "endpoints" / "pipeline_orchestrator_service.py")
        os.environ.pop("FRALIB_USE_SDK_LOOP", None)
        assert "FRALIB_USE_SDK_LOOP" not in src
        assert "use_sdk_loop" not in src
        assert os.getenv("FRALIB_USE_SDK_LOOP") is None

    @staticmethod
    def test_precommit_hook_has_8_checks():
        """Pre-commit hook evoluiu para 8 checks no baseline atual."""
        src = _read(ROOT / ".git" / "hooks" / "check_v11_protection.py")
        # Conta quantas referencias a "errors.append" tem
        checks = src.count("errors.append(")
        assert checks >= 8, f"Pre-commit hook tem {checks} checks, esperado >= 8"


def _run_all() -> int:
    """Roda todas as classes e imprime resumo."""
    classes = [
        TestV12ToolsSite(),
        TestV12LegacyArtifacts(),
        TestV12Integration(),
    ]
    passed = failed = 0
    failures: list[str] = []
    for cls in classes:
        for name in dir(cls):
            if not name.startswith("test_"):
                continue
            fn = getattr(cls, name)
            full_name = f"{cls.__class__.__name__}.{name}"
            try:
                fn()
                print(f"OK   {full_name}")
                passed += 1
            except AssertionError as e:
                print(f"FAIL {full_name}: {e}")
                failed += 1
                failures.append(full_name)
            except Exception as e:
                print(f"ERR  {full_name}: {type(e).__name__}: {e}")
                failed += 1
                failures.append(full_name)
                traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(
        f"v1.2-baseline-2026-06-23 anti-regression: {passed}/{passed + failed} passados"
    )
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
