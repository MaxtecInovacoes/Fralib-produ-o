import json
import os
import re
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from utils.schema_builder import gerar_schema, injetar_schema_no_html, normalizar_horarios


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
