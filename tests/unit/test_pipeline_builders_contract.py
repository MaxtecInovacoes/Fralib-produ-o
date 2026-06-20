"""Contract tests for pipeline_builders module functions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class TestBuildSkillFastPrdContract:
    """Contract tests for build_skill_fast_prd function."""

    def test_returns_simple_namespace(self):
        from backend.services.pipeline_builders import build_skill_fast_prd

        state = SimpleNamespace(
            lead_raw_data={},
            lead_obj=SimpleNamespace(lead=SimpleNamespace()),
            lead_nome="Test Business",
            segmento="nutricionista",
            cidade="Curitiba",
            keyword_research="",
        )

        result = build_skill_fast_prd(state)

        assert isinstance(result, SimpleNamespace)

    def test_has_required_attributes(self):
        from backend.services.pipeline_builders import build_skill_fast_prd

        state = SimpleNamespace(
            lead_raw_data={
                "nome": "Nutri Clinic",
                "segmento": "nutricionista",
                "cidade": "Curitiba",
            },
            lead_obj=SimpleNamespace(lead=SimpleNamespace(nome="Nutri Clinic")),
            lead_nome="Nutri Clinic",
            segmento="nutricionista",
            cidade="Curitiba",
            keyword_research="",
        )

        result = build_skill_fast_prd(state)

        required_attrs = [
            "business_name",
            "segmento",
            "cidade",
            "subniche",
            "neighborhood",
            "visual_direction",
            "visual_dna",
            "requirements_contract",
            "visual_contract",
            "site_build_plan",
            "layout_blueprint",
            "seo_keywords",
        ]
        for attr in required_attrs:
            assert hasattr(result, attr), f"Missing attribute: {attr}"

    def test_calls_contract_builders(self):
        from backend.services.pipeline_builders import build_skill_fast_prd

        state = SimpleNamespace(
            lead_raw_data={},
            lead_obj=SimpleNamespace(lead=SimpleNamespace()),
            lead_nome="Test",
            segmento="academia",
            cidade="Sao Paulo",
            keyword_research="",
            qualificacao_caio=SimpleNamespace(tier="STANDARD"),
        )

        with patch(
            "backend.services.pipeline_builders._contract_builders"
        ) as mock_builders:
            mock_builders.return_value = (
                lambda x: {"requirements": x},
                lambda x: {"visual": x},
                lambda x: {"plan": x},
            )
            result = build_skill_fast_prd(state)

            mock_builders.assert_called_once()
            assert hasattr(result, "requirements_contract")
            assert hasattr(result, "visual_contract")
            assert hasattr(result, "site_build_plan")


class TestEnsurePrdDesignReferenceContract:
    """Contract tests for ensure_prd_design_reference function."""

    def test_returns_string(self):
        from backend.services.pipeline_builders import ensure_prd_design_reference

        prd = SimpleNamespace()
        state = SimpleNamespace(lead_raw_data={}, lead_nome="Test")

        with patch("backend.services.pipeline_builders._contract_builders"):
            result = ensure_prd_design_reference(prd, state)

        assert isinstance(result, str)

    def test_sets_visual_dna_attribute(self):
        from backend.services.pipeline_builders import ensure_prd_design_reference

        prd = SimpleNamespace(sections=[])
        state = SimpleNamespace(
            lead_raw_data={},
            lead_nome="Test",
            segmento="clinica",
        )

        with patch("backend.services.pipeline_builders._contract_builders"):
            ensure_prd_design_reference(prd, state)

        assert hasattr(prd, "visual_dna")

    def test_sets_layout_blueprint_attribute(self):
        from backend.services.pipeline_builders import ensure_prd_design_reference

        prd = SimpleNamespace(sections=[])
        state = SimpleNamespace(
            lead_raw_data={},
            lead_nome="Test",
            segmento="academia",
        )

        with patch("backend.services.pipeline_builders._contract_builders"):
            ensure_prd_design_reference(prd, state)

        assert hasattr(prd, "layout_blueprint")


class TestEnsurePrdContractsContract:
    """Contract tests for ensure_prd_contracts function."""

    def test_sets_photos_attribute(self):
        from backend.services.pipeline_builders import ensure_prd_contracts

        prd = SimpleNamespace()
        state = SimpleNamespace(
            lead_raw_data={},
            segmento="nutricionista",
        )

        with patch("backend.services.pipeline_builders._contract_builders") as mock:
            mock.return_value = (
                lambda x: {"req": x},
                lambda x: {"vis": x},
                lambda x: {"plan": x},
            )
            ensure_prd_contracts(prd, state)

        assert hasattr(prd, "photos")

    def test_sets_seo_keywords_attribute(self):
        from backend.services.pipeline_builders import ensure_prd_contracts

        prd = SimpleNamespace()
        state = SimpleNamespace(
            lead_raw_data={},
            segmento="nutricionista",
        )

        with patch("backend.services.pipeline_builders._contract_builders") as mock:
            mock.return_value = (
                lambda x: {"req": x},
                lambda x: {"vis": x},
                lambda x: {"plan": x},
            )
            ensure_prd_contracts(prd, state)

        assert hasattr(prd, "seo_keywords")

    def test_sets_contracts_when_missing(self):
        from backend.services.pipeline_builders import ensure_prd_contracts

        prd = SimpleNamespace()
        state = SimpleNamespace(
            lead_raw_data={},
            segmento="nutricionista",
        )

        with patch("backend.services.pipeline_builders._contract_builders") as mock:
            mock.return_value = (
                lambda x: {"req": "contract"},
                lambda x: {"vis": "contract"},
                lambda x: {"plan": "contract"},
            )
            ensure_prd_contracts(prd, state)

        assert hasattr(prd, "requirements_contract")
        assert hasattr(prd, "visual_contract")
        assert hasattr(prd, "site_build_plan")


class TestEnsurePrdPublicationIdentityContract:
    """Contract tests for ensure_prd_publication_identity function."""

    def test_sets_site_url_on_simple_namespace(self):
        from backend.services.pipeline_builders import ensure_prd_publication_identity

        prd = SimpleNamespace()
        state = SimpleNamespace(lead_slug="test-lead")
        tenant_id = 2

        ensure_prd_publication_identity(prd, state, tenant_id)

        assert hasattr(prd, "site_url")
        assert "test-lead" in prd.site_url

    def test_sets_site_url_on_dict(self):
        from backend.services.pipeline_builders import ensure_prd_publication_identity

        prd = {}
        state = SimpleNamespace(lead_slug="dict-lead")
        tenant_id = 3

        ensure_prd_publication_identity(prd, state, tenant_id)

        assert "site_url" in prd
        assert "dict-lead" in prd["site_url"]

    def test_handles_empty_slug(self):
        from backend.services.pipeline_builders import ensure_prd_publication_identity

        prd = SimpleNamespace()
        state = SimpleNamespace(lead_slug="")
        tenant_id = 2

        original_url = getattr(prd, "site_url", None)
        ensure_prd_publication_identity(prd, state, tenant_id)

        # Should not crash and should not set URL if slug is empty
        if original_url is None:
            assert not hasattr(prd, "site_url") or prd.site_url == ""


class TestContractBuildersFactory:
    """Contract tests for _contract_builders factory function."""

    def test_returns_tuple_of_three_builders(self):
        from backend.services.pipeline_builders import _contract_builders

        result = _contract_builders()

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_builders_are_callable(self):
        from backend.services.pipeline_builders import _contract_builders

        build_req, build_vis, build_plan = _contract_builders()

        assert callable(build_req)
        assert callable(build_vis)
        assert callable(build_plan)
