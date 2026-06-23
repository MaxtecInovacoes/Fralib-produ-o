"""Tests anti-regressao v1.3 - Bugs textuais Vite/React removidos dos system prompts.

Protege contra regressao dos 4 bugs:
1. builder_prompt NAO menciona "Vite/React/TypeScript/Tailwind project componentized"
2. builder_prompt NAO menciona "@tailwindcss/vite" / "lucide-react"
3. premium_delivery_contract NAO menciona "motion/react, useState, useEffect"
4. OPENUI_SYSTEM_PROMPT TEM secao FORBIDDEN listando frameworks proibidos

Standalone runner: nao usa pytest/cov.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


class TestV13BugFixes:
    """Sprint 2.7: 4 bugs textuais Vite/React removidos dos system prompts."""

    @staticmethod
    def test_builder_prompt_no_vite_react_phrasing():
        """Bug #71-72: builder_prompt NAO fala mais Vite/React como instrucao POSITIVA.

        A secao FORBIDDEN pode listar libs (negacao). Aqui testamos apenas
        a parte POSITIVA (Output runtime) que diz o que o LLM DEVE gerar.
        """
        src = _read(BACKEND / "agents" / "prompt_agent_builder.py")
        # Frases que NAO podem mais aparecer como instrucao positiva
        forbidden_phrases = [
            "Vite/React/TypeScript/Tailwind project",
            "componentized in Studio mode",
        ]
        for phrase in forbidden_phrases:
            assert phrase not in src, \
                f"builder_prompt ainda referencia '{phrase}' (bug reintroduzido!)"
        # Verificar que secao FORBIDDEN existe (negacao explicita)
        assert "FORBIDDEN" in src, \
            "builder_prompt deveria ter secao FORBIDDEN"
        # A secao Output runtime deve falar HTML self-contained, nao Vite/React
        out_runtime_idx = src.find("Output runtime:")
        if out_runtime_idx >= 0:
            forbidden_idx = src.find("FORBIDDEN", out_runtime_idx)
            if forbidden_idx >= 0:
                # Texto entre Output runtime e FORBIDDEN nao pode ter Vite/React
                region = src[out_runtime_idx:forbidden_idx]
                for bad in ["Vite", "React", "TypeScript", "@tailwindcss/vite", "lucide-react", "tsx"]:
                    assert bad not in region, \
                        f"builder_prompt Output runtime menciona '{bad}' (deveria ser HTML only)"

    @staticmethod
    def test_builder_prompt_mentions_html_only():
        """builder_prompt agora explica que saida e HTML estatico."""
        src = _read(BACKEND / "agents" / "prompt_agent_builder.py")
        # Deve mencionar HTML self-contained + sem build step
        assert "self-contained HTML document" in src, \
            "builder_prompt deveria mencionar HTML self-contained"
        assert "No build step" in src or "no build step" in src.lower(), \
            "builder_prompt deveria explicitar 'no build step'"
        # Deve ter secao FORBIDDEN
        assert "FORBIDDEN" in src, \
            "builder_prompt deveria ter secao FORBIDDEN listando libs proibidas"

    @staticmethod
    def test_premium_delivery_no_react_motion():
        """Bug #73: premium_delivery_contract NAO menciona React/motion."""
        src = _read(BACKEND / "agents" / "prompt_agent_context.py")
        forbidden_phrases = [
            "motion/react",
            "estado React",
            "useState",
            "useEffect",
            "navbar, galeria premium",
        ]
        for phrase in forbidden_phrases:
            assert phrase not in src, \
                f"premium_delivery_contract ainda referencia '{phrase}' (bug reintroduzido!)"

    @staticmethod
    def test_premium_delivery_runtime_output_html():
        """runtime_output agora descreve HTML estatico, nao Vite/React."""
        src = _read(BACKEND / "agents" / "prompt_agent_context.py")
        assert "OpenUI static HTML" in src, \
            "runtime_output deveria descrever OpenUI static HTML"
        assert "Vite React TypeScript Tailwind motion" not in src, \
            "runtime_output ainda fala Vite React (regressao!)"
        # Nao menciona mais componentized React source
        assert "componentized React source" not in src, \
            "runtime_output ainda fala React source (regressao!)"

    @staticmethod
    def test_openui_system_prompt_has_forbidden_section():
        """Bug #74: OPENUI_SYSTEM_PROMPT tem secao FORBIDDEN blindando escopo."""
        src = _read(BACKEND / "services" / "openui_renderer.py")
        assert "FORBIDDEN" in src, \
            "OPENUI_SYSTEM_PROMPT deveria ter secao FORBIDDEN"
        # A secao FORBIDDEN deve listar frameworks proibidos
        assert "React" in src and "Vue" in src and "Svelte" in src, \
            "FORBIDDEN deveria listar React/Vue/Svelte"
        assert "motion/react" in src and "lucide-react" in src, \
            "FORBIDDEN deveria listar pacotes especificos"
        # Tambem deve permitir apenas HTML+Tailwind inline
        assert "ONLY ALLOWED" in src, \
            "FORBIDDEN deveria ter secao ONLY ALLOWED definindo o que pode gerar"

    @staticmethod
    def test_no_legacy_renderers_referenced():
        """Sanity: nenhum system prompt referencia renderer morto."""
        for path in [
            BACKEND / "agents" / "prompt_agent_builder.py",
            BACKEND / "agents" / "prompt_agent_context.py",
            BACKEND / "services" / "openui_renderer.py",
        ]:
            src = _read(path)
            # Vite/React studio morto (FraLib Studio deletado em 393f597)
            for phrase in [
                "Vite React Studio",
                "FraLib Studio mode",
                "vite_facts",
                "vite_modules",
                "vite_templates",
                "vite_validator",
            ]:
                assert phrase not in src, \
                    f"{path.name} ainda referencia '{phrase}' (renderer morto!)"


def _run_all() -> int:
    classes = [TestV13BugFixes()]
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

    print(f"\n{'='*60}")
    print(f"v1.3-baseline-2026-06-23 anti-regression: {passed}/{passed+failed} passados")
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
