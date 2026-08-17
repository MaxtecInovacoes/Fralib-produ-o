"""Tests para jina_research.py — geo-fallback, intent keywords, bulletproof fallback."""
import json
import sys
import types
from unittest.mock import patch, MagicMock

import pytest

from backend.agents.jina_research import (
    pesquisar_referencias_jina,
    INTENT_QUERIES,
    QUERIES_DESIGN_NICHO,
    GEO_FALLBACK_MAP,
)


def _mock_response(text: str, status: int = 200):
    m = MagicMock()
    m.status_code = status
    m.text = text
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    return m


def test_geo_expansion_usa_capital_quando_cidade_pequena_sem_resultado():
    fake_llm = types.ModuleType("llm_direct")
    fake_llm.call_claude = MagicMock(return_value=json.dumps({
        "faq_questions": ["Q1", "Q2"],
        "seo_keywords": ["k1", "k2"],
        "value_props": ["v1"],
    }))
    sys.modules["llm_direct"] = fake_llm
    try:
        call_log = []

        def fake_get(url, headers=None, timeout=20):
            call_log.append(url)
            url_lower = url.lower()
            if any(token in url_lower for token in ["quatro+barras", "quatro%20barras"]):
                return _mock_response("nenhum resultado aqui", 200)
            if "curitiba" in url_lower:
                return _mock_response("http://academia-x.com\nhttp://academia-y.com\nhttp://academia-z.com", 200)
            if any(dom in url_lower for dom in ["academia-x.com", "academia-y.com", "academia-z.com"]):
                return _mock_response("<html>Conteudo</html>", 200)
            return _mock_response("", 404)

        with patch("os.path.exists", return_value=False):
            with patch("backend.agents.jina_research.requests.get", side_effect=fake_get):
                result = pesquisar_referencias_jina("academia", "Quatro Barras")

        # Geo-expansion deve fazer 2 chamadas: 1a para cidade original, 2a para capital
        assert len(call_log) >= 2, f"Esperado >=2 chamadas Jina, obtido {len(call_log)}: {call_log}"
        # Saida mantem a cidade original do lead (nao a capital usada na busca)
        assert "QUATRO BARRAS" in result
        # Mas os sites encontrados sao da capital (geo-expansion funcionou)
        assert "academia-x.com" in result
    finally:
        sys.modules.pop("llm_direct", None)


def test_intent_fallback_quando_design_e_geo_retornam_vazio():
    def fake_get(url, headers=None, timeout=20):
        return _mock_response("nenhum resultado", 200)

    with patch("os.path.exists", return_value=False):
        with patch("backend.agents.jina_research.requests.get", side_effect=fake_get):
            result = pesquisar_referencias_jina("academia", "Quatro Barras")

    parsed = json.loads(result)
    assert "intelgencia_de_mercado" in parsed
    mkt = parsed["intelgencia_de_mercado"]
    assert mkt["nicho"] == "academia"
    assert mkt["cidade"] == "Quatro Barras"
    assert len(mkt["faq_questions"]) == 6
    assert len(mkt["seo_keywords"]) >= 5
    assert any("preco" in kw for kw in mkt["seo_keywords"])


def test_intent_keywords_possuem_intencao_compra():
    design_terms = set()
    for q in QUERIES_DESIGN_NICHO.values():
        design_terms.update(q.lower().split())
    commercial_signals = ["preco", "plano", "consulta", "corte", "tratamento", "menu", "reserva", "aluguel", "matricula", "cafe"]
    for nicho, intent in INTENT_QUERIES.items():
        assert nicho in QUERIES_DESIGN_NICHO, f"{nicho} sem query de design"
        overlap = set(intent.lower().split()) & design_terms
        assert len(overlap) < len(intent.split()), (
            f"Intent query de '{nicho}' parece copia da design: {intent}"
        )
        assert any(t in intent for t in commercial_signals), (
            f"Intent query de '{nicho}' sem sinal de intencao comercial: {intent}"
        )


def test_geo_fallback_tem_capitais_para_cidades_pequenas():
    assert GEO_FALLBACK_MAP["quatro barras"] == "curitiba"
    assert GEO_FALLBACK_MAP["campinas"] == "sao paulo"
    assert GEO_FALLBACK_MAP["contagem"] == "belo horizonte"
    assert GEO_FALLBACK_MAP["niteroi"] == "rio de janeiro"


def test_retorno_sempre_valido_mesmo_com_jina_offline():
    def fake_get(url, headers=None, timeout=20):
        raise ConnectionError("Jina indisponivel")

    with patch("backend.agents.jina_research.requests.get", side_effect=fake_get):
        result = pesquisar_referencias_jina("psicologia", "Niteroi")

    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "intelgencia_de_mercado" in parsed
    mkt = parsed["intelgencia_de_mercado"]
    assert mkt["nicho"] == "psicologia"
    assert mkt["cidade"] == "Niteroi"
    assert len(mkt["faq_questions"]) == 6


def test_bulletproof_fallback_quando_search_vazio_sem_exception():
    def fake_get(url, headers=None, timeout=20):
        return _mock_response("nenhum resultado", 200)

    with patch("backend.agents.jina_research.requests.get", side_effect=fake_get):
        result = pesquisar_referencias_jina("fotografia", "Campinas")

    parsed = json.loads(result)
    assert "intelgencia_de_mercado" in parsed
    assert len(parsed["intelgencia_de_mercado"]["seo_keywords"]) >= 5
