"""Testes anti-regressao Sprint 6 (v1.9) - ausencia de sub-agentes legados."""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


class TestLegacySubAgentsRemoved(unittest.TestCase):
    """Valida que os sub-agentes antigos nao fazem parte do fluxo canônico."""

    def test_legacy_modules_are_not_importable(self):
        self.assertIsNone(importlib.util.find_spec("backend.agents.sub_agents"))
        self.assertIsNone(
            importlib.util.find_spec("backend.agents.sub_agent_router")
        )

        with self.assertRaises(ModuleNotFoundError):
            __import__("backend.agents.sub_agents", fromlist=["*"])

        with self.assertRaises(ModuleNotFoundError):
            __import__("backend.agents.sub_agent_router", fromlist=["*"])

    def test_backend_agents_package_does_not_export_legacy_modules(self):
        from backend import agents

        exported = set(getattr(agents, "__all__", []))
        self.assertNotIn("sub_agents", exported)
        self.assertNotIn("sub_agent_router", exported)


if __name__ == "__main__":
    unittest.main(verbosity=2)
