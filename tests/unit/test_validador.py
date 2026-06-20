import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from agents import validador


@pytest.mark.unit
def test_validador_does_not_block_without_concrete_problem(monkeypatch):
    monkeypatch.setattr(
        validador,
        "call_claude",
        lambda **kwargs: '{"status":"changes_required","problemas":[]}',
    )

    result = validador.validar(
        html="<!doctype html><html><head><meta name='viewport'></head><body>"
        "<h1>High Fitness Academia</h1><a href='https://wa.me/5541999990000'>WhatsApp</a>"
        "<script type='application/ld+json'>{}</script></body></html>"
        + ("x" * 700),
        prd_text="Site para academia local.",
        segmento="academia",
        task_id="test",
    )

    assert result.aprovado is True
    assert result.problemas == []


@pytest.mark.unit
def test_validador_keeps_concrete_problem_blocking(monkeypatch):
    monkeypatch.setattr(
        validador,
        "call_claude",
        lambda **kwargs: '{"status":"changes_required","problemas":["CTA ausente"]}',
    )

    result = validador.validar(
        html="<!doctype html><html><body><h1>High Fitness Academia</h1></body></html>"
        + ("x" * 700),
        prd_text="Site para academia local.",
        segmento="academia",
        task_id="test",
    )

    assert result.aprovado is False
    assert result.problemas == ["CTA ausente"]
