"""Testes canônicos de ausência de OpenUI no caminho de produção."""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


class TestCanonicalBuilderEngine(unittest.TestCase):
    """OpenUI não deve mais ser um caminho importável na suíte canônica."""

    def test_openui_renderer_is_absent(self):
        self.assertIsNone(importlib.util.find_spec("backend.services.openui_renderer"))
        self.assertIsNone(importlib.util.find_spec("services.openui_renderer"))

    def test_builder_worker_accepts_only_vite_react(self):
        content = (ROOT / "backend/services/builder_worker.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('os.getenv("FRALIB_BUILDER_ENGINE", "vite_react")', content)
        self.assertIn('if engine != "vite_react":', content)
        self.assertIn("Use 'vite_react'.", content)
        self.assertNotIn("render_openui_site(", content)
        self.assertNotIn("from backend.services.openui_renderer", content)
        self.assertNotIn("from services.openui_renderer", content)

    def test_builder_worker_no_openui_renderer_callsite(self):
        content = (ROOT / "backend/services/builder_worker.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("render_openui_site(", content)
        self.assertNotIn("from backend.services.openui_renderer", content)
        self.assertNotIn("from services.openui_renderer", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
