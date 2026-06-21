import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "agents"))

from designer_prd import SectionSpec


@pytest.mark.unit
def test_section_spec_preserves_copy_and_layout_contract():
    section = SectionSpec(
        name="hero",
        layout_type="hero-split",
        copy={
            "h1": "Treino forte em Campina Grande do Sul",
            "subtitulo": "Academia com rotina objetiva.",
            "cta": "Chamar no WhatsApp",
        },
        items="musculacao; funcional",
        media_role="hero",
    )

    assert section.name == "hero"
    assert section.layout_type == "hero-split"
    assert section.copy_data["h1"] == "Treino forte em Campina Grande do Sul"
    assert section.items == ["musculacao", "funcional"]
    assert section.media_role == "hero"
    assert section.model_dump(by_alias=True)["copy"]["cta"] == "Chamar no WhatsApp"
