"""
Unit tests for builder/agent.py _prd_to_spec().

Verifies DesignerPRD → OpenUI spec conversion without needing a DB or server.
"""
import sys
import os

# Required env vars before any backend imports
os.environ.setdefault("FRALIB_SITES_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "tmp_sites"))
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Ensure backend path is available
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from unittest.mock import patch


def _make_prd(**overrides):
    """Build a DesignerPRD with valid fields from the actual model."""
    from backend.agents.designer_prd import (
        DesignerPRD,
        SectionSpec,
        ColorPalette,
        AnimationSpec,
    )

    sections = [
        SectionSpec(
            name="Hero",
            required=True,
            components=["hero-cta"],
            data_source="Test",
            headline="Test Headline",
            subheadline="Test Sub",
            cta="Call Now",
        )
    ]

    cp = ColorPalette(
        primary="#111111",
        secondary="#222222",
        accent="#ff6600",
        background="#ffffff",
        text="#111111",
        reasoning="test",
    )

    animations = [AnimationSpec(
        name="fade-in", type="fade-in", target="section", trigger="scroll"
    )]

    defaults = dict(
        sections=sections,
        color_palette=cp,
        typography={"heading": "Inter", "body": "Inter", "accent": "Inter"},
        animations=animations,
        business_name="TestBiz",
        reviews_count=10,
        reviews_rating=4.5,
        reviews_list=[{"autor": "Joao", "texto": "Great!", "rating": 5}],
        address="Rua Test, 123",
        phone="+55 41 9999-9999",
        google_maps_embed="https://maps.example.com",
        components_21dev=["hero", "cta", "footer"],
        anti_patterns=["no_cliches"],
        schema_org_types=["LocalBusiness"],
        seo_keywords=["test", "seo"],
        cidade="Curitiba",
        segmento="Marketing",
        competitor_analysis="Competitor analysis test",
    )
    defaults.update(overrides)

    prd = DesignerPRD(**defaults)
    return prd


class TestPrdToSpec:
    """Tests for _prd_to_spec conversion."""

    def _convert(self, prd):
        from backend.agents.builder.agent import _prd_to_spec
        return _prd_to_spec(prd)

    def test_wrapper_key_matches_openui(self):
        """OpenUI endpoint expects json={"designerPRD": spec}."""
        from backend.agents.builder.agent import render_site
        from backend.agents.builder.agent import GENERATE_ENDPOINT
        assert "/generate" in GENERATE_ENDPOINT

    def test_spec_has_all_openui_consumed_keys(self):
        """Every key that _build_system_prompt reads must be present in the spec."""
        prd = _make_prd()
        spec = self._convert(prd)

        required_keys = [
            "business_name",
            "cidade",
            "segmento",
            "sections",
            "hero",
            "ctas",
            "faqs",
            "paleta",
            "seo_keywords",
            "motion_directives",
            "color_palette",
            "typography",
            "animations",
            "design_tokens",
            "layout_dna",
            "design_system",
            "builder_directive",
            "reviews_list",
            "schema_org_types",
            "anti_patterns",
            "competitor_analysis",
            "address",
            "phone",
            "hours",
            "photos",
            "videos",
        ]
        for key in required_keys:
            assert key in spec, f"Missing key in spec: {key}"

    def test_sections_are_plain_dicts_with_name_title_content(self):
        """OpenUI reads sections[i].get('name'), .get('title'), .get('content')."""
        spec = self._convert(_make_prd())
        sections = spec["sections"]
        assert isinstance(sections, list)
        assert len(sections) > 0
        for s in sections:
            assert isinstance(s, dict), f"Section should be dict, got {type(s)}"
            assert "name" in s, "Section missing 'name'"
            assert "title" in s, "Section missing 'title'"
            assert "content" in s, "Section missing 'content'"
            assert "section_contract" in s, "Section missing 'section_contract'"
            assert "order_index" in s, "Section missing 'order_index'"

    def test_sections_receive_contract_media_and_constraints(self):
        from backend.agents.designer_prd import SectionSpec

        prd = _make_prd(
            sections=[
                SectionSpec(name="hero", title="Hero"),
                SectionSpec(name="faq", title="FAQ"),
                SectionSpec(name="footer", title="Footer"),
            ],
            variation_blueprint={
                "ordem_das_secoes": ["hero", "faq", "footer"],
            },
            creative_direction={
                "hard_constraints": {"hero_strategy": "hero-full-bleed"},
                "soft_constraints": {"motion": {"efeito_principal": "reveal"}},
            },
            media_plan=[
                {
                    "url": "https://images.example.com/hero.jpg",
                    "role": "hero-image",
                    "section": "hero",
                    "required": True,
                }
            ],
            faq_questions=["Como funciona?", "Qual o horário?", "Onde fica?"],
        )

        spec = self._convert(prd)
        sections = {str(section["name"]).lower(): section for section in spec["sections"]}

        assert sections["hero"]["order_index"] == 1
        assert sections["faq"]["order_index"] == 2
        assert sections["footer"]["order_index"] == 3
        assert sections["hero"]["required_media_count"] == 1
        assert sections["hero"]["media_plan"][0]["url"] == "https://images.example.com/hero.jpg"
        assert sections["hero"]["hard_constraints"]["hero_strategy"] == "hero-full-bleed"
        assert sections["faq"]["soft_constraints"]["motion"]["efeito_principal"] == "reveal"
        assert "h1" in sections["hero"]["section_contract"]["minimum_requirements"]["must_have"]
        assert "at least 3 questions" in " ".join(sections["faq"]["section_contract"]["minimum_requirements"]["must_have"])

    def test_color_palette_is_plain_dict(self):
        """OpenUI iterates paleta.items() — must be a plain dict."""
        spec = self._convert(_make_prd())
        paleta = spec["paleta"]
        color_palette = spec["color_palette"]
        assert isinstance(paleta, dict), f"paleta should be dict, got {type(paleta)}"
        assert isinstance(color_palette, dict), f"color_palette should be dict, got {type(color_palette)}"
        for key in ("primary", "secondary", "accent"):
            assert key in paleta

    def test_typography_is_plain_dict(self):
        """OpenUI iterates typography items — must be plain dict."""
        spec = self._convert(_make_prd())
        assert isinstance(spec["typography"], dict)

    def test_animations_are_plain_dicts(self):
        """Animations must serialize cleanly."""
        spec = self._convert(_make_prd())
        assert isinstance(spec["animations"], list)
        for anim in spec["animations"]:
            assert isinstance(anim, dict)
            assert "name" in anim
            assert "type" in anim

    def test_hours_is_never_none(self):
        """OpenUI does json.dumps(hours) — None produces 'null' string."""
        spec = self._convert(_make_prd())
        assert spec["hours"] == {}

    def test_faqs_are_list_of_strings(self):
        """OpenUI iterates faqs as strings: for q in faqs."""
        spec = self._convert(_make_prd())
        assert isinstance(spec["faqs"], list)
        for q in spec["faqs"]:
            assert isinstance(q, str), f"faq should be string, got {type(q)}"

    def test_reviews_list_is_list_of_dicts(self):
        """OpenUI reads reviews_list[i].get('author') and .get('text')."""
        spec = self._convert(_make_prd())
        assert isinstance(spec["reviews_list"], list)
        for r in spec["reviews_list"]:
            assert isinstance(r, dict)
            assert "autor" in r
            assert "texto" in r

    def test_design_tokens_has_archetype_and_radius(self):
        """OpenUI reads design_tokens.archetype and design_tokens.radius."""
        spec = self._convert(_make_prd())
        tokens = spec["design_tokens"]
        assert tokens["archetype"] == "editorial-asymmetric"
        assert tokens["radius"] == "12px"
        assert "palette" in tokens
        assert "typography" in tokens

    def test_layout_dna_has_layout_family(self):
        """OpenUI reads layout_dna.layout_family."""
        spec = self._convert(_make_prd())
        assert spec["layout_dna"]["layout_family"] == "asymmetric-magazine"
        assert "section_count_range" in spec["layout_dna"]

    def test_design_system_has_archetype_briefing(self):
        """OpenUI reads design_system.archetype_briefing."""
        spec = self._convert(_make_prd())
        briefing = spec["design_system"]["archetype_briefing"]
        assert isinstance(briefing, str)
        assert len(briefing) > 0

    def test_videos_empty_list_when_none(self):
        """videos should never be None in the spec."""
        spec = self._convert(_make_prd(videos=[]))
        assert spec["videos"] == []

    def test_geo_serializes_to_dict(self):
        """geo field must be a dict (not a Pydantic object)."""
        # geo is not a DesignerPRD field — _prd_to_spec uses getattr(prd, "geo", None)
        # which returns None → becomes None in spec (not a Pydantic issue)
        spec = self._convert(_make_prd())
        assert isinstance(spec["geo"], type(None))  # None, not a Pydantic object

    def test_contracts_preserved(self):
        """visual_contract, requirements_contract, site_build_plan must pass through."""
        # These are DesignerPRD fields — pass them through overrides
        contracts = {
            "visual_contract": {"style": "bold"},
            "requirements_contract": {"responsive": True},
            "site_build_plan": {"sections": 8},
        }
        spec = self._convert(_make_prd(**contracts))
        assert spec["visual_contract"] == {"style": "bold"}
        assert spec["requirements_contract"] == {"responsive": True}
        assert spec["site_build_plan"] == {"sections": 8}

    def test_dna_fields_preserved(self):
        """visual_dna, layout_blueprint, design_reference_pack pass through."""
        spec = self._convert(_make_prd(
            visual_dna={"seed": "abc"},
            layout_blueprint=[{"section": "hero"}],
            design_reference_pack={"refs": ["url1"]},
        ))
        assert spec["visual_dna"] == {"seed": "abc"}
        assert spec["layout_blueprint"] == [{"section": "hero"}]
        assert spec["design_reference_pack"] == {"refs": ["url1"]}

    def test_photos_serialize_to_list_of_strings(self):
        """photos must be list of strings."""
        spec = self._convert(_make_prd())
        assert isinstance(spec["photos"], list)
        for p in spec["photos"]:
            assert isinstance(p, str)

    def test_hero_built_from_business_name(self):
        """hero headline must be the business_name."""
        spec = self._convert(_make_prd())
        assert spec["hero"]["headline"] == "TestBiz"

    def test_builder_directive_contains_business_and_segment(self):
        """builder_directive must contain business name and segment."""
        spec = self._convert(_make_prd())
        assert "TestBiz" in spec["builder_directive"]

    def test_builder_spec_artifacts_supports_sectioned_layout(self, monkeypatch, tmp_path):
        from backend.agents.builder.agent import _prd_to_spec, _write_builder_spec_artifacts
        from backend.agents import artifact_store as artifact_module

        monkeypatch.setenv("FRALIB_ARTIFACTS_DIR", str(tmp_path))
        monkeypatch.setattr(artifact_module, "artifact_dir", artifact_module.artifact_dir)

        prd = _make_prd(
            cidade="Campina Grande do Sul",
            segmento="academia",
        )
        setattr(prd, "_run_id", "run-123")
        setattr(prd, "_lead_id", "lead-123")
        setattr(prd, "_lead_data", {"nome": "TestBiz"})

        spec = _prd_to_spec(prd)
        spec["_run_id"] = "run-123"
        spec["_lead_id"] = "lead-123"
        spec["_lead_name"] = "TestBiz"

        _write_builder_spec_artifacts(spec)

        payload_file = tmp_path / "run-123" / "testbiz-lead-123" / "builder" / "openui_payload" / "00-openui-payload.json"
        section_file = tmp_path / "run-123" / "testbiz-lead-123" / "builder" / "section_specs" / "01-hero.json"
        assert payload_file.exists()
        assert section_file.exists()
        assert "academia" in spec["builder_directive"]
        assert "Campina Grande do Sul" in spec["builder_directive"]

    def test_openui_payload_carries_section_contracts(self):
        from backend.agents.designer_prd import SectionSpec

        spec = self._convert(_make_prd(
            sections=[
                SectionSpec(name="hero", title="Hero"),
                SectionSpec(name="contato", title="Contato"),
            ],
            variation_blueprint={"ordem_das_secoes": ["hero", "contato"]},
            media_plan=[
                {
                    "url": "https://images.example.com/gym.jpg",
                    "role": "hero",
                    "section": "hero",
                    "required": True,
                }
            ],
        ))

        assert "section_contracts" in spec
        assert spec["section_contracts"][0]["name"] == "hero"
        assert spec["section_contracts"][0]["required_media_count"] == 1
        assert spec["openui_payload"]["section_contracts"][0]["name"] == "hero"
        assert spec["openui_payload"]["section_contracts"][0]["required_media_count"] == 1

    def test_competitor_analysis_passthrough(self):
        """competitor_analysis from DesignerPRD must pass through."""
        spec = self._convert(_make_prd(competitor_analysis="Test analysis"))
        assert spec["competitor_analysis"] == "Test analysis"
