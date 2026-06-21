import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from agents.agente_variacao import SYSTEM_PROMPT as VARIACAO_SYSTEM_PROMPT
from agents.designer_prd import DesignerPRD
from agents.design_system_selector import _load_index
from agents.skill_loader import get_skills_agente


def _minimal_prd(**overrides):
    data = {
        "sections": [{"name": "Hero", "copy": {"h1": "Teste"}}],
        "color_palette": {
            "primary": "#111111",
            "secondary": "#ffffff",
            "accent": "#ff4a00",
            "background": "#ffffff",
            "text": "#111111",
        },
        "typography": {"heading": "Anton", "body": "Inter"},
        "animations": [],
        "business_name": "Lead Visual",
        "reviews_count": 0,
        "reviews_rating": 0,
        "reviews_list": [],
        "address": "Rua Teste, 123",
        "phone": "",
        "hours": {},
        "photos": [],
        "google_maps_embed": "",
        "components_21dev": [],
        "competitor_analysis": "",
        "anti_patterns": [],
        "schema_org_types": ["LocalBusiness"],
    }
    data.update(overrides)
    return DesignerPRD(**data)


def test_designer_prd_preserves_visual_contract_fields():
    prd = _minimal_prd(
        visual_dna={"archetype": "LUXURY_ELITE"},
        design_reference_pack={"id": "luxury-abc", "archetype": "LUXURY_ELITE"},
        layout_blueprint=[{"section": "hero", "variant": "hero-full-bleed"}],
        dna_combo={"structure_ref": "bugatti"},
        visual_seed="abc123",
        minimum_required_media=4,
    )

    dumped = prd.model_dump()

    assert dumped["visual_dna"]["archetype"] == "LUXURY_ELITE"
    assert dumped["design_reference_pack"]["id"] == "luxury-abc"
    assert dumped["layout_blueprint"][0]["variant"] == "hero-full-bleed"
    assert dumped["dna_combo"]["structure_ref"] == "bugatti"
    assert dumped["visual_seed"] == "abc123"
    assert dumped["minimum_required_media"] == 4


def test_visual_skills_are_active_for_arquiteto_and_renderers():
    assert get_skills_agente("arquiteto_mestre") == ["design-with-taste"]
    assert get_skills_agente("builder_renderer") == []


def test_variacao_no_longer_forces_services_section():
    assert "REQUIRED: hero, contato, footer" in VARIACAO_SYSTEM_PROMPT
    assert 'Do not force "servicos" section' in VARIACAO_SYSTEM_PROMPT


def test_design_system_index_loads_with_utf8():
    rows = _load_index()

    assert len(rows) >= 100
    assert any(row.get("slug") == "nike" for row in rows)
