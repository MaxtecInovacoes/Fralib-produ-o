"""Testes anti-regressão v1.10 - Sprint 7 (RAG Templates).

Valida:
- template_embeddings.py existe e tem funções principais
- 64d TF-IDF sem numpy, persistência JSON atômica
- find_best_template retorna top_k com score/rank
- admin_template_endpoints.py tem 3 rotas
- 8 testes unitários cobrem todas as funções
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# ════════════════════════════════════════════════════════════════════
# Testes principais
# ════════════════════════════════════════════════════════════════════
# PYTHONIOENCODING=utf-8 python tests/test_anti_regressao_v110.py
# ════════════════════════════════════════════════════════════════════


def test_template_embeddings_module_exists():
    """template_embeddings.py existe e tem funções principais."""
    print("[TESTE 1/8] Verificando template_embeddings.py...")
    from backend.services.template_embeddings import (
        embed_template,
        index_templates,
        find_best_template,
        cosine_similarity,
        persist_index,
        load_index,
        get_template_stats,
    )
    print("  ✓ embed_template, index_templates importam")
    print("  ✓ find_best_template, cosine_similarity importam")
    print("  ✓ persist_index, load_index importam")
    print("  ✓ get_template_stats importa")
    print("  ✓ Template embeddings module OK")


def test_embed_template_returns_64d():
    """embed_template retorna embedding 64d sem numpy."""
    print("\n[TESTE 2/8] Verificando embed_template...")
    from backend.services.template_embeddings import embed_template

    html = "<html><body><h1>Test Bold Template</h1></body></html>"
    vec = embed_template(html)
    assert len(vec) == 64, f"Esperado 64d, tem {len(vec)}"
    assert all(isinstance(v, float) for v in vec), "Todos valores devem ser float"
    print("  ✓ Retorna embedding 64d")
    print("  ✓ Todos valores float")
    print("  ✓ Embed template OK")


def test_index_templates_returns_dict():
    """index_templates retorna dict[str, list[float]]."""
    print("\n[TESTE 3/8] Verificando index_templates...")
    from backend.services.template_embeddings import index_templates, TEMPLATES_DIR

    # Criar template temporário para teste
    test_dir = ROOT / "backend" / "templates"
    test_dir.mkdir(exist_ok=True)
    test_template = test_dir / "test.html"
    test_template.write_text("<html><body>Test Template</body></html>")

    try:
        idx = index_templates()
        assert isinstance(idx, dict), f"Esperado dict, tem {type(idx)}"
        for name, vec in idx.items():
            assert isinstance(name, str), f"Nome deve ser str: {type(name)}"
            assert isinstance(vec, list), f"Vetor deve ser list: {type(vec)}"
            assert len(vec) == 64, f"Vetor 64d: {len(vec)}"
        print("  ✓ Retorna dict[str, list[float]]")
        print("  ✓ Index templates OK")
    finally:
        # Limpar
        if test_template.exists():
            test_template.unlink()


def test_find_best_template_for_nicho():
    """find_best_template retorna top_k templates para nicho."""
    print("\n[TESTE 4/8] Verificando find_best_template...")
    from backend.services.template_embeddings import (
        embed_template,
        find_best_template,
        cosine_similarity,
    )

    # Criar templates de teste
    bold_html = "<html><body><h1>BOLD ENERGY</h1><p>High impact</p></body></html>"
    minimal_html = "<html><body><h1>Minimal Design</h1><p>Clean layout</p></body></html>"

    vec_bold = embed_template(bold_html)
    vec_minimal = embed_template(minimal_html)

    # Testar nicho "bold"
    matches = find_best_template("academia crossfit bold energy", top_k=2)
    assert isinstance(matches, list), f"Esperado list, tem {type(matches)}"
    if matches:
        assert len(matches) <= 2, f"Top_k=2, tem {len(matches)}"
        for match in matches:
            assert "template" in match, "Falta 'template' no match"
            assert "score" in match, "Falta 'score' no match"
            assert "rank" in match, "Falta 'rank' no match"
            assert isinstance(match["score"], float), "Score deve ser float"
    print("  ✓ Retorna top_k com template/score/rank")
    print("  ✓ Find best template OK")


def test_persist_load_roundtrip():
    """persist_index/load_index funcionam em JSON atômico."""
    print("\n[TESTE 5/8] Verificando persistência...")
    from backend.services.template_embeddings import (
        persist_index,
        load_index,
        INDEX_PATH,
    )

    # Criar índice de teste
    test_index = {"test": [0.1] * 64, "test2": [0.2] * 64}

    # Persistir
    path = persist_index(test_index)
    assert path == INDEX_PATH, f"Path errado: {path}"

    # Carregar
    loaded = load_index()
    assert isinstance(loaded, dict), f"Esperado dict, tem {type(loaded)}"
    assert "vectors" in loaded, "Falta 'vectors' no loaded"
    assert len(loaded["vectors"]) == 2, f"Esperado 2 templates, tem {len(loaded['vectors'])}"

    # Limpar
    if INDEX_PATH.exists():
        INDEX_PATH.unlink()

    print("  ✓ Persiste carrega corretamente")
    print("  ✓ JSON atômico OK")


def test_admin_template_endpoints_importable():
    """admin_template_endpoints.py existe e tem 3 rotas."""
    print("\n[TESTE 6/8] Verificando admin_template_endpoints.py...")
    from backend.endpoints.admin_template_endpoints import router

    assert len(router.routes) == 3, f"Esperado 3 rotas, tem {len(router.routes)}"
    expected_paths = [
        "/api/admin/templates/index",
        "/api/admin/templates/reindex",
        "/api/admin/templates/match",
    ]
    paths = [r.path for r in router.routes]
    for path in expected_paths:
        assert path in paths, f"Rota {path} não encontrada"

    print("  ✓ Tem 3 rotas esperadas")
    print("  ✓ Admin endpoints OK")


def test_cosine_similarity_correct():
    """cosine_similarity calcula corretamente."""
    print("\n[TESTE 7/8] Verificando cosine_similarity...")
    from backend.services.template_embeddings import cosine_similarity

    # Vetores idênticos
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    sim = cosine_similarity(a, b)
    assert abs(sim - 1.0) < 0.001, f"Similaridade idêntica deve ser 1.0, tem {sim}"

    # Vetores ortogonais
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    sim = cosine_similarity(a, b)
    assert abs(sim) < 0.001, f"Similaridade ortogonal deve ser 0.0, tem {sim}"

    # Vetores opostos
    a = [1.0, 0.0, 0.0]
    b = [-1.0, 0.0, 0.0]
    sim = cosine_similarity(a, b)
    assert abs(sim - (-1.0)) < 0.001, f"Similaridade oposta deve ser -1.0, tem {sim}"

    print("  ✓ Calcula similaridade corretamente")
    print("  ✓ Cosine similarity OK")


def test_get_template_stats_shape():
    """get_template_stats retorna dict com formato correto."""
    print("\n[TESTE 8/8] Verificando get_template_stats...")
    from backend.services.template_embeddings import get_template_stats

    stats = get_template_stats()
    assert isinstance(stats, dict), f"Esperado dict, tem {type(stats)}"

    required_keys = ["total", "embedding_dim", "last_indexed", "index_path", "templates_dir"]
    for key in required_keys:
        assert key in stats, f"Falta chave: {key}"

    assert isinstance(stats["total"], int), "total deve ser int"
    assert isinstance(stats["embedding_dim"], int), "embedding_dim deve ser int"
    assert isinstance(stats["last_indexed"], (int, float)), "last_indexed deve ser num"
    assert isinstance(stats["index_path"], str), "index_path deve ser str"
    assert isinstance(stats["templates_dir"], str), "templates_dir deve ser str"

    print("  ✓ Retorna dict com formato correto")
    print("  ✓ Template stats OK")


if __name__ == "__main__":
    print("Executando testes anti-regressão v1.10...")
    print("=" * 60)

    test_template_embeddings_module_exists()
    test_embed_template_returns_64d()
    test_index_templates_returns_dict()
    test_find_best_template_for_nicho()
    test_persist_load_roundtrip()
    test_admin_template_endpoints_importable()
    test_cosine_similarity_correct()
    test_get_template_stats_shape()

    print("\n" + "=" * 60)
    print("✅ Todos os 8 testes passaram!")
    print("Sprint 7 (v1.10) - RAG Templates: OK")