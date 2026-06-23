"""Tests anti-regressao v1.1-baseline-2026-06-23.

Protege as 7 decisoes criticas do Sprint 0+1 (memory_hook SDK).
Se QUALQUER teste falhar, significa que algo foi revertido sem
atualizar AGENTS.md e AGENT_IMPROVEMENT_AUDIT.md.

Gaps protegidos:
1. memory_hook_site.py existe (Sprint 1)
2. ValidacaoResultado.score field (Sprint 0)
3. AGENT_MODEL_MAP sincronizado (Sprint 0)
4. threading.Lock em CoreMemory (Sprint 0)
5. fcntl.flock (intencao - skip em Windows dev)
6. enable_context=True no _call_openui_llm (Sprint 1)
7. PM2 dreamer app (Sprint 0)
8. scripts/ecosystem.config.js removido (Sprint 0)
9. v1.1-baseline-2026-06-23 em AGENTS.md (Sprint 0)

Standalone runner (nao usa pytest/cov): rapido, sem import side-effects.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
AGENTS_DIR = BACKEND / "agents"
SERVICES_DIR = BACKEND / "services"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


class TestV11MemoryHook:
    """Gap #1: memory_hook_site.py + pipeline orchestrator integration."""

    @staticmethod
    def test_memory_hook_site_exists():
        p = AGENTS_DIR / "memory_hook_site.py"
        assert p.is_file(), "memory_hook_site.py sumiu! Sprint 1 perdido."

    @staticmethod
    def test_memory_hook_site_has_persist_lesson_with_score():
        src = _read(AGENTS_DIR / "memory_hook_site.py")
        assert "persist_lesson_with_score" in src, \
            "persist_lesson_with_score removido! Feedback loop Nicho<->Validador quebrado."
        assert "validador_score" in src, "parametro validador_score removido!"

    @staticmethod
    def test_memory_hook_site_has_inject_memory_for_site():
        src = _read(AGENTS_DIR / "memory_hook_site.py")
        assert "inject_memory_for_site" in src, \
            "inject_memory_for_site removido! Memory hook do site pipeline quebrado."

    @staticmethod
    def test_orchestrator_calls_persist_lesson_with_score():
        src = _read(BACKEND / "endpoints" / "pipeline_orchestrator_service.py")
        assert "persist_lesson_with_score" in src, \
            "Orchestrator nao chama mais persist_lesson_with_score!"


class TestV11ValidadorScore:
    """Gap #2: ValidacaoResultado.score field."""

    @staticmethod
    def test_validacao_resultado_has_score_field():
        from backend.agents.handoff_types import ValidacaoResultado
        assert "score" in ValidacaoResultado.model_fields, \
            "ValidacaoResultado.score field removido! Sprint 0 perdido."
        field = ValidacaoResultado.model_fields["score"]
        assert field.default == 0.0, \
            f"ValidacaoResultado.score default mudou (esperado 0.0, got {field.default})"

    @staticmethod
    def test_validador_returns_score():
        src = _read(AGENTS_DIR / "validador.py")
        assert "_score = float" in src or "_score=float" in src, \
            "validador.py nao calcula mais _score!"
        assert "_score = max(0.0, min(10.0" in src, "Clamp [0,10] do score removido!"

    @staticmethod
    def test_orchestrator_reintroduced_validador():
        src = _read(BACKEND / "endpoints" / "pipeline_orchestrator_service.py")
        assert "from agents.validador import validar" in src, \
            "Orchestrator nao chama mais validador.validar()!"
        assert "_validador_result = validar(" in src, "validar() nao e mais chamado!"


class TestV11ModelMap:
    """Gap #3: llm_config.AGENT_MODEL_MAP sincronizado."""

    @staticmethod
    def test_agent_model_map_sonnet_for_nicho():
        src = _read(AGENTS_DIR / "llm_config.py")
        m = re.search(r'"agente_nicho":\s*"(\w+)"', src)
        assert m, "agente_nicho nao encontrado em AGENT_MODEL_MAP"
        assert m.group(1) == "sonnet", \
            f"agente_nicho voltou para {m.group(1)}! Era para ser sonnet (v1.1)."

    @staticmethod
    def test_agent_model_map_sonnet_for_variacao():
        src = _read(AGENTS_DIR / "llm_config.py")
        m = re.search(r'"agente_variacao":\s*"(\w+)"', src)
        assert m, "agente_variacao nao encontrado em AGENT_MODEL_MAP"
        assert m.group(1) == "sonnet", \
            f"agente_variacao voltou para {m.group(1)}! Era para ser sonnet (v1.1)."

    @staticmethod
    def test_agente_nicho_uses_model_map_not_hardcode():
        src = _read(AGENTS_DIR / "agente_nicho.py")
        assert "AGENT_MODEL_MAP" in src, \
            "agente_nicho.py nao usa AGENT_MODEL_MAP!"
        bad_hardcode = re.search(r'model\s*=\s*"(haiku|sonnet|opus)"\s*[,)]', src)
        assert not bad_hardcode, \
            f"agente_nicho.py tem hardcode model={bad_hardcode.group(1) if bad_hardcode else '?'}"


class TestV11RaceCondition:
    """Gap #4: agent_memory._salvar com threading.Lock + fcntl.flock."""

    @staticmethod
    def test_core_memory_has_intra_process_lock():
        from backend.agent_memory import CoreMemory
        assert hasattr(CoreMemory, "_intra_process_lock"), \
            "_intra_process_lock removido de CoreMemory!"
        import threading
        assert isinstance(CoreMemory._intra_process_lock, type(threading.Lock())), \
            f"_intra_process_lock nao e threading.Lock (got {type(CoreMemory._intra_process_lock)})"

    @staticmethod
    def test_salvar_uses_fcntl_or_lock():
        src = _read(BACKEND / "agent_memory.py")
        assert "fcntl" in src or "threading.Lock" in src, \
            "agent_memory.py nao usa fcntl OU threading.Lock!"

    @staticmethod
    def test_salvar_nicho_uses_fcntl_or_lock():
        src = _read(BACKEND / "agent_memory.py")
        match = re.search(r'def _salvar_nicho.*?(?=\n    def |\nclass )', src, re.DOTALL)
        assert match, "_salvar_nicho nao encontrada em agent_memory.py"
        block = match.group(0)
        assert "fcntl" in block or "_intra_process_lock" in block, \
            "_salvar_nicho nao tem lock!"

    @staticmethod
    def test_threading_import_present():
        src = _read(BACKEND / "agent_memory.py")
        assert "import threading" in src, "agent_memory.py nao importa threading!"


class TestV11BuilderBridge:
    """Sprint 1: Bridge Builder worker->orchestrator (3 mudancas coordenadas)."""

    @staticmethod
    def test_builder_worker_serializes_nicho():
        src = _read(SERVICES_DIR / "builder_worker.py")
        assert "_nicho_serializado" in src, "_nicho_serializado removido!"
        assert "prompt_agent" in src and "context" in src and "nicho" in src, \
            "nicho nao esta sendo injetado no manifest!"

    @staticmethod
    def test_openui_renderer_enable_context_true():
        src = _read(SERVICES_DIR / "openui_renderer.py")
        match = re.search(r"enable_context\s*=\s*(True|False)\s*,\s*(?:#.*)?\n", src)
        assert match, "enable_context nao encontrado em _call_openui_llm"
        assert match.group(1) == "True", \
            f"enable_context voltou para False! Match: {match.group(0)!r}"

    @staticmethod
    def test_openui_renderer_rehydrates_memory():
        src = _read(SERVICES_DIR / "openui_renderer.py")
        assert "memory reidratada" in src or "memory rehydration" in src, \
            "OpenUI nao reidrata mais memory!"


class TestV11PM2AndLegacy:
    """Gap #5: PM2 dreamer + scripts/ecosystem.config.js removido."""

    @staticmethod
    def test_ecosystem_config_js_has_dreamer():
        src = _read(ROOT / "ecosystem.config.js")
        assert "fralib-dreamer" in src, "fralib-dreamer removido do ecosystem.config.js!"

    @staticmethod
    def test_dreamer_daemon_script_exists():
        p = ROOT / "scripts" / "dreamer_daemon.py"
        assert p.is_file(), "scripts/dreamer_daemon.py sumiu!"

    @staticmethod
    def test_legacy_ecosystem_deleted():
        legacy = ROOT / "scripts" / "ecosystem.config.js"
        assert not legacy.exists(), "scripts/ecosystem.config.js voltou!"


class TestV11DocsAndTag:
    """Gap #8: Docs atualizados + tag v1.1 existe."""

    @staticmethod
    def test_agents_md_references_v11():
        src = _read(ROOT / "AGENTS.md")
        assert "v1.1-baseline-2026-06-23" in src, \
            "AGENTS.md nao referencia v1.1-baseline-2026-06-23!"

    @staticmethod
    def test_audit_md_references_v11():
        src = _read(ROOT / "docs" / "AGENT_IMPROVEMENT_AUDIT.md")
        assert "v1.1" in src, "AGENT_IMPROVEMENT_AUDIT.md nao menciona v1.1!"

    @staticmethod
    def test_v11_tag_exists():
        result = subprocess.run(
            ["git", "tag", "-l", "v1.1-baseline-2026-06-23"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        assert "v1.1-baseline-2026-06-23" in result.stdout, \
            "Tag v1.1-baseline-2026-06-23 sumiu!"


def _run_all() -> int:
    """Roda todas as classes e imprime resumo. Retorna exit code (0=ok, 1=falha)."""
    classes = [
        TestV11MemoryHook(),
        TestV11ValidadorScore(),
        TestV11ModelMap(),
        TestV11RaceCondition(),
        TestV11BuilderBridge(),
        TestV11PM2AndLegacy(),
        TestV11DocsAndTag(),
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

    print(f"\n{'='*60}")
    print(f"v1.1-baseline-2026-06-23 anti-regression: {passed}/{passed+failed} passados")
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
