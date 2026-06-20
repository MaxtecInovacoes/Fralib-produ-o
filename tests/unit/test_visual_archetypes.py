from agents.visual_archetypes import select_visual_archetype
from agents.unsplash_fetcher import _build_query


def test_visual_archetype_maps_fitness_and_wellness():
    assert select_visual_archetype("academia")["name"] == "BOLD_ENERGY"
    assert select_visual_archetype("nutricionista")["name"] == "ZEN_PURE"


def test_unsplash_query_inherits_visual_archetype():
    query = _build_query("nutricionista", "Curitiba", "Priscila Botelho", archetype="ZEN_PURE")
    assert "calm natural light" in query
