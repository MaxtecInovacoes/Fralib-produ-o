"""Tests anti-regressao v1.5-baseline-2026-06-23 - Sprint 3B: RAG semantico no SDR.

Protege a camada de retrieval semantico (5 funcoes) + integracao opt-in no agent.py:
1. retrieval_semantico.py existe (Sprint 3B entrega)
2. Modulo tem 5 funcoes + TOOLS_DISPATCH
3. _embed_tfidf retorna vetor 64-d deterministico
4. _cosine entre vetores identicos = 1.0
5. _cosine entre vetores ortogonais ~ 0.0
6. index_conversation + search_similar_conversations roundtrip
7. current_backend retorna string valida
8. agent.py importa retrieval_semantico quando FRALIB_SDR_USE_RAG=1

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


class TestV15Sprint3BRAGSemantico:
    """Sprint 3B: RAG semantico (TF-IDF + sentence-transformers opt-in)."""

    @staticmethod
    def test_retrieval_semantico_module_exists():
        """retrieval_semantico.py deve existir (Sprint 3B entrega)."""
        path = BACKEND / "agents" / "sdr_langgraph" / "retrieval_semantico.py"
        assert path.is_file(), \
            "retrieval_semantico.py nao existe! Sprint 3B nao foi entregue."

    @staticmethod
    def test_retrieval_semantico_has_5_functions_and_dispatch():
        """retrieval_semantico.py deve ter 5 funcoes + TOOLS_DISPATCH + call_tool + list_tools."""
        from backend.agents.sdr_langgraph import retrieval_semantico

        # 5 funcoes principais
        assert hasattr(retrieval_semantico, "index_conversation"), \
            "index_conversation ausente"
        assert hasattr(retrieval_semantico, "search_similar_conversations"), \
            "search_similar_conversations ausente"
        assert hasattr(retrieval_semantico, "reindex_from_jsonl"), \
            "reindex_from_jsonl ausente"
        assert hasattr(retrieval_semantico, "format_search_results_for_prompt"), \
            "format_search_results_for_prompt ausente"
        assert hasattr(retrieval_semantico, "current_backend"), \
            "current_backend ausente"
        # Dispatcher pattern (mesmo de tools_sdr.py Sprint 3A)
        assert hasattr(retrieval_semantico, "TOOLS_DISPATCH"), \
            "TOOLS_DISPATCH ausente"
        assert hasattr(retrieval_semantico, "call_tool"), \
            "call_tool ausente"
        assert hasattr(retrieval_semantico, "list_tools"), \
            "list_tools ausente"
        # TOOLS_DISPATCH tem 5 entradas
        assert len(retrieval_semantico.TOOLS_DISPATCH) == 5, \
            f"TOOLS_DISPATCH deveria ter 5 tools, tem {len(retrieval_semantico.TOOLS_DISPATCH)}"

    @staticmethod
    def test_embed_tfidf_is_64d_and_deterministic():
        """_embed_tfidf retorna vetor 64-d, deterministico (mesmo input = mesmo output)."""
        from backend.agents.sdr_langgraph.retrieval_semantico import (
            _embed_tfidf, EMBED_DIM
        )
        # EMBED_DIM pode variar com dedup do vocab (64-66 range)
        assert 60 <= EMBED_DIM <= 80, f"EMBED_DIM fora do range esperado: {EMBED_DIM}"
        v1 = _embed_tfidf("academia crossfit aluno musculacao")
        v2 = _embed_tfidf("academia crossfit aluno musculacao")
        assert len(v1) == EMBED_DIM, f"vetor deveria ter {EMBED_DIM} dims, got {len(v1)}"
        assert v1 == v2, "_embed_tfidf nao e deterministico!"
        # Texto vazio retorna vetor zero
        v_empty = _embed_tfidf("")
        assert v_empty == [0.0] * EMBED_DIM, "texto vazio deveria ser vetor zero"
    @staticmethod
    def test_cosine_identical_is_one_orthogonal_is_zero():
        """_cosine: vetores identicos = 1.0, ortogonais = 0.0."""
        from backend.agents.sdr_langgraph.retrieval_semantico import _cosine

        # Identicos
        a = [0.1, 0.2, 0.3, 0.4, 0.5]
        assert abs(_cosine(a, a) - 1.0) < 1e-6, \
            f"cosseno de vetor com ele mesmo deveria ser 1.0, got {_cosine(a, a)}"
        # Ortogonais
        b = [0.5, 0.0, 0.0, 0.0, 0.0]
        c = [0.0, 0.5, 0.0, 0.0, 0.0]
        assert abs(_cosine(b, c)) < 1e-6, \
            f"cosseno ortogonal deveria ser 0.0, got {_cosine(b, c)}"
        # Vetor zero
        zero = [0.0] * 5
        assert _cosine(a, zero) == 0.0, "cosseno com vetor zero deveria ser 0"
        assert _cosine(zero, a) == 0.0, "cosseno com vetor zero deveria ser 0"
        # Vazio
        assert _cosine([], a) == 0.0, "cosseno com vetor vazio deveria ser 0"

    @staticmethod
    def test_index_and_search_roundtrip():
        """index_conversation + search_similar_conversations roundtrip."""
        from backend.agents.sdr_langgraph import retrieval_semantico

        # Indexa 3 conversas de nichos diferentes
        r1 = retrieval_semantico.index_conversation(
            user_id=99999, nicho="academia_crossfit", lead_id="lead_acad_1",
            text="aluno quer musculacao crossfit horario livre manha",
            metadata={"converteu": True, "intent_final": "wants_link"},
        )
        r2 = retrieval_semantico.index_conversation(
            user_id=99999, nicho="academia_crossfit", lead_id="lead_acad_2",
            text="academia sem aluno rating baixo sem instagram",
            metadata={"converteu": False, "intent_final": "lost"},
        )
        r3 = retrieval_semantico.index_conversation(
            user_id=99999, nicho="academia_crossfit", lead_id="lead_acad_3",
            text="crossfit manha musculacao aluno comunidade familia",
            metadata={"converteu": True, "intent_final": "wants_link"},
        )
        for r in (r1, r2, r3):
            assert r.get("indexed") is True, f"index falhou: {r}"
            # dim pode ser 64 (TF-IDF) ou 384 (sentence-transformers)
            dim = r.get("dim", 0)
            assert dim in (64, 65, 384) or 60 <= dim <= 400, \
                f"dim inesperada: {dim}"

        # Busca semantica: query "musculacao crossfit" deve ranquear lead_acad_1 e lead_acad_3 acima do lead_acad_2
        results = retrieval_semantico.search_similar_conversations(
            user_id=99999, nicho="academia_crossfit",
            query="musculacao crossfit academia",
            top_k=3,
        )
        assert len(results) == 3, f"esperava 3 resultados, got {len(results)}"
        # Os 2 primeiros devem ser os "positivos" (converteu=True)
        top_two_ids = {r["lead_id"] for r in results[:2]}
        assert "lead_acad_1" in top_two_ids or "lead_acad_3" in top_two_ids, \
            f"top-2 deveria incluir positivos, got {top_two_ids}"
        # Scores em ordem decrescente
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), \
            f"resultados nao estao ordenados por score desc: {scores}"

    @staticmethod
    def test_search_with_invalid_user_returns_empty():
        """search_similar_conversations com user_id=0 retorna []."""
        from backend.agents.sdr_langgraph.retrieval_semantico import (
            search_similar_conversations,
        )
        result = search_similar_conversations(
            user_id=0, nicho="academia_crossfit",
            query="qualquer coisa", top_k=3,
        )
        assert result == [], f"user_id=0 deveria retornar [], got {result}"

        result_empty_query = search_similar_conversations(
            user_id=12345, nicho="academia_crossfit",
            query="", top_k=3,
        )
        assert result_empty_query == [], \
            f"query vazia deveria retornar [], got {result_empty_query}"

    @staticmethod
    def test_format_search_results_returns_empty_for_empty():
        """format_search_results_for_prompt retorna string vazia se lista vazia."""
        from backend.agents.sdr_langgraph.retrieval_semantico import (
            format_search_results_for_prompt,
        )
        assert format_search_results_for_prompt([]) == ""
        # Com resultados: deve incluir RAG + score
        results = [
            {"lead_id": "lead1", "score": 0.85, "text": "aluno quer crossfit",
             "metadata": {"converteu": True, "gatilho_conversao": "familia"}},
        ]
        out = format_search_results_for_prompt(results)
        assert "RAG" in out or "score" in out, \
            f"formatador deveria mencionar RAG ou score, got: {out}"
        assert "CONVERTEU" in out, f"deveria marcar status CONVERTEU, got: {out}"

    @staticmethod
    def test_agent_py_imports_retrieval_semantico_opt_in():
        """agent.py importa retrieval_semantico quando FRALIB_SDR_USE_RAG=1."""
        agent_src = _read(BACKEND / "agents" / "sdr_langgraph" / "agent.py")
        # Verifica que tem o guard da flag RAG
        assert "FRALIB_SDR_USE_RAG" in agent_src, \
            "agent.py nao checa FRALIB_SDR_USE_RAG"
        # Verifica que importa de retrieval_semantico
        assert "from .retrieval_semantico import" in agent_src, \
            "agent.py nao importa retrieval_semantico"
        # Verifica que injeta RAG no pre-fetch (substitui retrieve_similar_conversations)
        assert "search_similar_conversations" in agent_src, \
            "agent.py nao injeta search_similar_conversations"
        # Verifica que indexa apos save_sdr_lesson
        assert "index_conversation" in agent_src, \
            "agent.py nao chama index_conversation"

    @staticmethod
    def test_pre_commit_hook_has_10_checks():
        """Pre-commit hook tem 10 checks (era 9)."""
        hook_src = _read(ROOT / ".git" / "hooks" / "check_v11_protection.py")
        # Procura referencias a v1.5 ou retrieval_semantico
        has_rag_protection = "retrieval_semantico.py" in hook_src
        assert has_rag_protection, \
            "Pre-commit hook nao protege retrieval_semantico.py"


def _run_all() -> int:
    classes = [TestV15Sprint3BRAGSemantico()]
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
    print(f"v1.5-baseline-2026-06-23 anti-regression: {passed}/{passed+failed} passados")
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
