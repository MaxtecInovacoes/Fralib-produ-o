"""Testes anti-regressao Sprint 6 (v1.9) - Sub-agentes por estetica."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


class TestSubAgents(unittest.TestCase):
    """Sprint 6 - 6 sub-agentes especializados por estetica."""

    def test_sub_agents_module_exists(self):
        from backend.agents import sub_agents
        assert hasattr(sub_agents, "SUB_AGENT_DISPATCH")

    def test_6_sub_agents_registered(self):
        from backend.agents.sub_agents import SUB_AGENT_DISPATCH
        assert len(SUB_AGENT_DISPATCH) == 7  # 6 esteticas + default
        for est in ["BOLD_ENERGY", "EDITORIAL", "MINIMAL", "KINETIC", "SCROLL", "IMMERSIVE_3D"]:
            assert est in SUB_AGENT_DISPATCH, f"Falta sub-agente: {est}"

    def test_router_dispatches_to_correct_agent(self):
        from backend.agents.sub_agent_router import route_to_sub_agent
        html = route_to_sub_agent("BOLD_ENERGY", {}, {"business_name": "Test", "tagline": "T"})
        assert "Test" in html
        assert "<html" in html

    def test_default_agent_fallback(self):
        from backend.agents.sub_agent_router import route_to_sub_agent
        html = route_to_sub_agent("UNKNOWN_ESTETICA", {}, {"business_name": "X"})
        assert "<html" in html
        assert "X" in html

    def test_bold_agent_returns_html(self):
        from backend.agents.sub_agents import bold_agent
        html = bold_agent({}, {"business_name": "Acad", "tagline": "Force"})
        assert "<html" in html
        assert "Acad" in html
        assert "data-reveal" in html

    def test_editorial_agent_returns_html(self):
        from backend.agents.sub_agents import editorial_agent
        html = editorial_agent({}, {"business_name": "Adv", "tagline": "Justica"})
        assert "<html" in html
        assert "marquee" in html
        assert "bento" in html

    def test_router_handles_invalid_estetica(self):
        from backend.agents.sub_agent_router import route_to_sub_agent, is_valid_estetica
        assert not is_valid_estetica("INVALID")
        # Mas retorna html via default
        html = route_to_sub_agent("INVALID", {}, {"business_name": "X"})
        assert "<html" in html

    def test_nicho_to_estetica_mapping(self):
        from backend.agents.sub_agent_router import get_sub_agent_for_nicho
        assert get_sub_agent_for_nicho("academia_crossfit") == "BOLD_ENERGY"
        assert get_sub_agent_for_nicho("barbearia_premium") == "EDITORIAL"
        assert get_sub_agent_for_nicho("unknown") == "default"


if __name__ == "__main__":
    unittest.main(verbosity=2)
