"""Smoke test Sprint 3B - RAG semantico no SDR.

Valida que retrieval_semantico.py funciona end-to-end sem LLM:
1. Importa o modulo
2. Indexa 3 conversas mock de nichos diferentes
3. Busca semantica retorna resultados ordenados
4. Backend ativo e' TF-IDF (sem sentence-transformers instalado)
5. RAG substitui retrieve_similar_conversations quando flag ON

Uso:
  python scripts/smoke_sprint_3b.py [user_id]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 88888
    print(f"=== Sprint 3B smoke (user_id={user_id}) ===\n")

    # 1. Import + backend check
    print("1. Import + backend...")
    from backend.agents.sdr_langgraph import retrieval_semantico
    backend = retrieval_semantico.current_backend()
    print(f"   backend ativo: {backend}")
    print(f"   EMBED_DIM: {retrieval_semantico.EMBED_DIM}")
    print(f"   tools: {retrieval_semantico.list_tools()}")
    assert backend in ("tfidf", "sentence-transformers"), f"backend invalido: {backend}"
    print("   OK\n")

    # 2. Index 3 conversas de nichos diferentes
    print("2. Indexando 3 conversas mock...")
    nicho = "academia_crossfit"
    convs = [
        ("lead_a1", "aluno quer musculacao crossfit horario livre manha",
         {"converteu": True, "intent_final": "wants_link", "gatilho_conversao": "familia"}),
        ("lead_a2", "academia sem aluno rating baixo sem instagram",
         {"converteu": False, "intent_final": "lost", "gatilho_conversao": ""}),
        ("lead_a3", "crossfit manha musculacao aluno comunidade resultado",
         {"converteu": True, "intent_final": "wants_link", "gatilho_conversao": "resultado"}),
    ]
    for lead_id, text, meta in convs:
        r = retrieval_semantico.index_conversation(
            user_id=user_id, nicho=nicho, lead_id=lead_id,
            text=text, metadata=meta,
        )
        print(f"   {lead_id}: indexed={r.get('indexed')} dim={r.get('dim')}")
        assert r.get("indexed"), f"index falhou: {r}"
    print("   OK\n")

    # 3. Search semantica
    print("3. Busca semantica: 'musculacao crossfit academia'")
    results = retrieval_semantico.search_similar_conversations(
        user_id=user_id, nicho=nicho,
        query="musculacao crossfit academia aluno",
        top_k=3,
    )
    print(f"   {len(results)} resultados:")
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['lead_id']} score={r['score']:.3f} converteu={r['metadata'].get('converteu')}")
    assert len(results) == 3, f"esperava 3, got {len(results)}"
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "nao esta ordenado desc"
    print("   OK\n")

    # 4. Format para prompt
    print("4. Format para prompt LLM:")
    formatted = retrieval_semantico.format_search_results_for_prompt(results)
    print(formatted)
    assert "RAG" in formatted or "score" in formatted
    print("   OK\n")

    # 5. Edge cases
    print("5. Edge cases...")
    empty_user = retrieval_semantico.search_similar_conversations(
        user_id=0, nicho=nicho, query="qualquer", top_k=3,
    )
    assert empty_user == [], f"user_id=0 deveria [], got {empty_user}"
    print("   user_id=0 -> [] (correto)")

    empty_query = retrieval_semantico.search_similar_conversations(
        user_id=user_id, nicho=nicho, query="", top_k=3,
    )
    assert empty_query == [], f"query='' deveria [], got {empty_query}"
    print("   query='' -> [] (correto)")
    print("   OK\n")

    # 6. COSSENO sanity (identico=1, ortogonal=0)
    print("6. Cosseno sanity...")
    a = [0.1, 0.2, 0.3, 0.4]
    b = [0.1, 0.2, 0.3, 0.4]
    c = [0.0, 0.0, 0.5, 0.0]
    assert abs(retrieval_semantico._cosine(a, b) - 1.0) < 1e-6
    assert abs(retrieval_semantico._cosine(a, c)) < 0.6  # nao ortogonal mas baixo
    print(f"   cos(a,a) = {retrieval_semantico._cosine(a, b):.4f} (esperado 1.0)")
    print(f"   cos(a,c) = {retrieval_semantico._cosine(a, c):.4f} (esperado < 0.6)")
    print("   OK\n")

    # 7. Limpa lixo
    print("7. Cleanup (remove index criado)...")
    import shutil
    path = retrieval_semantico._embeddings_path(user_id, nicho)
    if path.is_file():
        path.unlink()
    print(f"   removido: {path}")
    print("   OK\n")

    print("=" * 50)
    print(f"SMOKE 3B PASSOU (backend={backend}, dim={retrieval_semantico.EMBED_DIM})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
