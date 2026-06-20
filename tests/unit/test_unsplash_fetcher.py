import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from agents.unsplash_fetcher import _build_query, _infer_query_key


@pytest.mark.unit
def test_aquatic_academia_uses_swimming_query():
    assert _infer_query_key("Academia", "Aquaflex Jardim Paulista") == "natacao"

    query = _build_query("Academia", "Campina Grande do Sul", "Aquaflex Jardim Paulista")

    assert "swimming pool" in query
    assert "gym fitness" not in query
