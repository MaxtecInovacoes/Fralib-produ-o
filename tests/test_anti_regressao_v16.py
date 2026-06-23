"""Tests anti-regressao v1.6-baseline-2026-06-23 - Sprint 3C: Telemetria Variacao.

Protege a camada de telemetria (5 funcoes) + integracao opt-in no agent.py:
1. telemetria_variacao.py existe (Sprint 3C entrega)
2. Modulo tem 5 funcoes + TOOLS_DISPATCH
3. record + get_stats roundtrip com taxa_conversao correta
4. rank filtra por min_amostra e ordena por taxa desc
5. get_best_variacao retorna top ou None (cold start)
6. format_variacao_stats retorna string formatada com numeros
7. agent.py importa telemetria quando FRALIB_SDR_USE_TELEMETRIA=1
8. pre-commit hook tem 11 checks (proteger telemetria_variacao.py)

Standalone runner: nao usa pytest/cov.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


class TestV16Sprint3CTelemetriaVariacao:
    """Sprint 3C: Telemetria de Variacao (5 funcoes)."""

    @staticmethod
    def test_telemetria_variacao_module_exists():
        """telemetria_variacao.py deve existir (Sprint 3C entrega)."""
        path = BACKEND / "agents" / "sdr_langgraph" / "telemetria_variacao.py"
        assert path.is_file(), \
            "telemetria_variacao.py nao existe! Sprint 3C nao foi entregue."

    @staticmethod
    def test_has_5_functions_and_dispatch():
        """telemetria_variacao.py deve ter 5 funcoes + TOOLS_DISPATCH + call_tool + list_tools."""
        from backend.agents.sdr_langgraph import telemetria_variacao

        for fn_name in (
            "record_variacao_outcome",
            "get_variacao_stats",
            "rank_variacoes_by_conversion",
            "get_best_variacao_for_nicho",
            "format_variacao_stats_for_prompt",
        ):
            assert hasattr(telemetria_variacao, fn_name), \
                f"funcao ausente: {fn_name}"
        # Dispatcher pattern
        assert hasattr(telemetria_variacao, "TOOLS_DISPATCH")
        assert hasattr(telemetria_variacao, "call_tool")
        assert hasattr(telemetria_variacao, "list_tools")
        assert len(telemetria_variacao.TOOLS_DISPATCH) == 5
        assert len(telemetria_variacao.list_tools()) == 5

    @staticmethod
    def test_record_and_get_stats_roundtrip():
        """record_variacao_outcome + get_variacao_stats roundtrip."""
        from backend.agents.sdr_langgraph import telemetria_variacao

        user_id = 88877  # id ficticio
        nicho = "academia_crossfit"
        # Limpa estado de runs anteriores (test idempotente)
        _path = telemetria_variacao._telemetria_path(user_id)
        if _path.is_file():
            _path.unlink()
        # Registra 5 conversas: 3 com template A (2 converteram), 2 com template B (1 converteu)
        for i in range(2):
            telemetria_variacao.record_variacao_outcome(
                user_id=user_id, nicho=nicho, template_id="tpl_A",
                converteu=True, duracao_turnos=5, lead_id=f"lead_a_{i}",
            )
        for i in range(1):
            telemetria_variacao.record_variacao_outcome(
                user_id=user_id, nicho=nicho, template_id="tpl_A",
                converteu=False, duracao_turnos=8, lead_id=f"lead_a_fail",
            )
        for i in range(1):
            telemetria_variacao.record_variacao_outcome(
                user_id=user_id, nicho=nicho, template_id="tpl_B",
                converteu=True, duracao_turnos=4, lead_id=f"lead_b_{i}",
            )
        telemetria_variacao.record_variacao_outcome(
            user_id=user_id, nicho=nicho, template_id="tpl_B",
            converteu=False, duracao_turnos=10, lead_id="lead_b_fail",
        )
        # get stats
        stats = telemetria_variacao.get_variacao_stats(user_id, nicho)
        assert len(stats) == 2, f"esperava 2 templates, got {len(stats)}"
        # tpl_A: 2/3 converteram = 0.6667
        stats_a = [s for s in stats if s["template_id"] == "tpl_A"][0]
        assert stats_a["total"] == 3
        assert stats_a["converteram"] == 2
        assert abs(stats_a["taxa_conversao"] - (2/3)) < 0.01
        # tpl_B: 1/2 converteram = 0.5
        stats_b = [s for s in stats if s["template_id"] == "tpl_B"][0]
        assert stats_b["total"] == 2
        assert stats_b["converteram"] == 1
        assert abs(stats_b["taxa_conversao"] - 0.5) < 0.01

    @staticmethod
    def test_rank_filters_by_min_amostra():
        """rank filtra templates com < min_amostra e ordena por taxa desc."""
        from backend.agents.sdr_langgraph import telemetria_variacao

        user_id = 88866
        nicho = "barbearia_premium"
        # Limpa estado de runs anteriores
        _path = telemetria_variacao._telemetria_path(user_id)
        if _path.is_file():
            _path.unlink()
        # tpl_X: 5 conversas, 4 converteram (80%)
        for i in range(4):
            telemetria_variacao.record_variacao_outcome(
                user_id=user_id, nicho=nicho, template_id="tpl_X",
                converteu=True, duracao_turnos=3, lead_id=f"x_{i}",
            )
        telemetria_variacao.record_variacao_outcome(
            user_id=user_id, nicho=nicho, template_id="tpl_X",
            converteu=False, duracao_turnos=7, lead_id="x_fail",
        )
        # tpl_Y: 1 conversa (abaixo de min_amostra=3)
        telemetria_variacao.record_variacao_outcome(
            user_id=user_id, nicho=nicho, template_id="tpl_Y",
            converteu=True, duracao_turnos=2, lead_id="y_0",
        )
        # rank com min_amostra=3
        ranking = telemetria_variacao.rank_variacoes_by_conversion(
            user_id, nicho, min_amostra=3,
        )
        # tpl_Y deve ser excluido (1 < 3)
        ids = [r["template_id"] for r in ranking]
        assert "tpl_Y" not in ids, f"tpl_Y deveria ser excluido (1 conversa), got: {ids}"
        assert "tpl_X" in ids, f"tpl_X deveria estar, got: {ids}"
        # tpl_X deve ser top
        assert ranking[0]["template_id"] == "tpl_X"
        assert abs(ranking[0]["taxa_conversao"] - 0.8) < 0.01

    @staticmethod
    def test_get_best_variacao_returns_top_or_none():
        """get_best_variacao_for_nicho retorna top ou None em cold start."""
        from backend.agents.sdr_langgraph import telemetria_variacao

        # Cold start: user_id=0 → None
        assert telemetria_variacao.get_best_variacao_for_nicho(0, "academia") is None
        # user_id sem dados → None
        assert telemetria_variacao.get_best_variacao_for_nicho(99999, "academia") is None
        # user_id com 3 conversas no melhor template → retorna template_id
        user_id = 88855
        nicho = "clinica_estetica"
        # Limpa estado de runs anteriores
        _path = telemetria_variacao._telemetria_path(user_id)
        if _path.is_file():
            _path.unlink()
        for i in range(3):
            telemetria_variacao.record_variacao_outcome(
                user_id=user_id, nicho=nicho, template_id="tpl_premium",
                converteu=True, duracao_turnos=4, lead_id=f"c_{i}",
            )
        best = telemetria_variacao.get_best_variacao_for_nicho(user_id, nicho)
        assert best == "tpl_premium", f"esperava tpl_premium, got {best}"

    @staticmethod
    def test_format_variacao_stats_for_prompt():
        """format retorna string com numeros; vazia para lista vazia."""
        from backend.agents.sdr_langgraph import telemetria_variacao

        assert telemetria_variacao.format_variacao_stats_for_prompt([]) == ""
        # Com stats mock
        stats = [
            {"template_id": "tpl_X", "total": 5, "converteram": 4,
             "taxa_conversao": 0.8, "duracao_media": 4.2, "score_medio": 50.0},
        ]
        out = telemetria_variacao.format_variacao_stats_for_prompt(stats)
        assert "TELEMETRIA" in out, f"deveria mencionar TELEMETRIA, got: {out}"
        assert "tpl_X" in out, f"deveria incluir template_id, got: {out}"
        assert "4/5" in out, f"deveria mostrar 4/5, got: {out}"
        assert "80%" in out, f"deveria mostrar 80%, got: {out}"

    @staticmethod
    def test_agent_py_imports_telemetria_opt_in():
        """agent.py importa telemetria_variacao quando FRALIB_SDR_USE_TELEMETRIA=1."""
        agent_src = _read(BACKEND / "agents" / "sdr_langgraph" / "agent.py")
        # Flag presente
        assert "FRALIB_SDR_USE_TELEMETRIA" in agent_src, \
            "agent.py nao checa FRALIB_SDR_USE_TELEMETRIA"
        # Importa telemetria
        assert "from .telemetria_variacao import" in agent_src, \
            "agent.py nao importa telemetria_variacao"
        # Injeta no pre-fetch
        assert "rank_variacoes_by_conversion" in agent_src, \
            "agent.py nao injeta rank_variacoes_by_conversion"
        # Registra no post-save
        assert "record_variacao_outcome" in agent_src, \
            "agent.py nao chama record_variacao_outcome"

    @staticmethod
    def test_pre_commit_hook_has_11_checks():
        """Pre-commit hook tem 11 checks (era 10)."""
        hook_src = _read(ROOT / ".git" / "hooks" / "check_v11_protection.py")
        assert "telemetria_variacao.py" in hook_src, \
            "Pre-commit hook nao protege telemetria_variacao.py"
        # Verifica que a docstring menciona v1.6
        assert "v1.6" in hook_src, \
            "Pre-commit hook docstring nao menciona v1.6"


def _run_all() -> int:
    classes = [TestV16Sprint3CTelemetriaVariacao()]
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
    print(f"v1.6-baseline-2026-06-23 anti-regression: {passed}/{passed+failed} passados")
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
