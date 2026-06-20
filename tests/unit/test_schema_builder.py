import json
import os
import re
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from utils.schema_builder import gerar_schema, injetar_schema_no_html, normalizar_horarios, gerar_faq_schema


def _schema_from_html(html):
    match = re.search(
        r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    assert match
    return json.loads(match.group(1).strip())


@pytest.mark.unit
def test_normalizar_horarios_accepts_scraper_list_strings():
    horarios = normalizar_horarios(
        ["segunda-feira\t06:00-10:00", "terça-feira  17:00-22:00"]
    )

    assert horarios == {
        "segunda-feira": "06:00-10:00",
        "terça-feira": "17:00-22:00",
    }


@pytest.mark.unit
def test_gerar_schema_accepts_horarios_list_without_crashing():
    schema_tag = gerar_schema(
        {
            "nome": "Legacy Centro de Treinamento",
            "segmento": "Academia",
            "cidade": "Campina Grande do Sul",
            "telefone": "(41) 99153-3193",
            "horarios": ["quarta-feira\t06:00-10:00", "quarta-feira\t17:00-22:00"],
            "fotos_unsplash": [{"url": "https://example.com/foto.jpg"}],
        },
        "https://seunegociofralib.site/sites/2/legacy-centro-de-treinamento/",
    )

    schema = _schema_from_html(schema_tag)

    assert schema["@context"] == "https://schema.org"
    assert schema["name"] == "Legacy Centro de Treinamento"
    assert schema["telephone"] == "+5541991533193"
    assert schema["image"] == "https://example.com/foto.jpg"
    assert schema["openingHoursSpecification"][0]["dayOfWeek"] == "Wednesday"


@pytest.mark.unit
def test_injetar_schema_falls_back_when_head_is_missing(tmp_path):
    html = "<html><body><main>Site OD</main></body></html>"

    result = injetar_schema_no_html(
        html,
        {"nome": "Alfa Crosstraining", "segmento": "Academia"},
        "https://seunegociofralib.site/sites/2/alfa-crosstraining/",
        tmp_path,
    )

    assert "application/ld+json" in result
    assert (tmp_path / "sitemap.xml").exists()
    assert (tmp_path / "robots.txt").exists()


@pytest.mark.unit
def test_gerar_faq_schema_retorna_faqpage_valido():
    perguntas_respostas = [
        {"pergunta": "Qual o horario de funcionamento?", "resposta": "Seg a Sex das 8h as 18h."},
        {"question": "Aceita cartao?", "answer": "Sim, aceitamos todos os cartoes."},
        {"q": "Tem estacionamento?", "a": "Sim, gratuito para clientes."},
    ]

    faq_tag = gerar_faq_schema(perguntas_respostas, "https://exemplo.com")

    assert '<script type="application/ld+json">' in faq_tag
    assert "FAQPage" in faq_tag
    assert "Qual o horario de funcionamento" in faq_tag
    assert "Seg a Sex das 8h as 18h" in faq_tag


@pytest.mark.unit
def test_gerar_faq_schema_lista_vazia_retorna_string_vazia():
    assert gerar_faq_schema([], "https://exemplo.com") == ""
    assert gerar_faq_schema(None, "https://exemplo.com") == ""


@pytest.mark.unit
def test_gerar_faq_schema_ignora_itens_sem_pergunta_ou_resposta():
    perguntas_respostas = [
        {"pergunta": "Valido?", "resposta": "Sim."},
        {"pergunta": "", "resposta": "Sem pergunta."},
        {"pergunta": "Sem resposta", "resposta": ""},
    ]

    faq_tag = gerar_faq_schema(perguntas_respostas, "https://exemplo.com")

    assert "Valido" in faq_tag
    assert '"name":""' not in faq_tag
    assert '"text":""' not in faq_tag
