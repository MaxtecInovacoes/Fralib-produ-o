"""Test the archetype system by generating 6 sites (1 per archetype).

Test cases:
1. Barbearia (WARM_LOCAL) - Test 1
2. Academia (BOLD_ENERGY) - Test 2
3. Clinica (ZEN_PURE) - Test 3
4. Restaurante (LUXURY_ELITE) - Test 4
5. Energia Solar (MODERN_TECH) - Test 5
6. Imobiliaria (PROFESSIONAL_TRUST) - Test 6

Note: 'estetica' maps to WARM_LOCAL, 'clinica' maps to ZEN_PURE
"""

import sys
import re
import json
from collections import defaultdict
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.vite_react_renderer import (
    _generate_studio_fallback_files,
    _get_archetype_for_segment,
    _get_archetype_palette,
)


def run_archetype_test():
    """Generate 6 sites using _generate_studio_fallback_files and verify differentiation."""

    # Test cases with correct segment mappings
    test_cases = [
        ("barbearia", "WARM_LOCAL", 1),
        ("academia", "BOLD_ENERGY", 2),
        ("clinica", "ZEN_PURE", 3),
        ("restaurante", "LUXURY_ELITE", 4),
        ("energia solar", "MODERN_TECH", 5),
        ("imobiliaria", "PROFESSIONAL_TRUST", 6),
    ]

    results = {
        "sites_generated": 0,
        "unique_theme_colors": 0,
        "unique_hero_titles": 0,
        "unique_layouts": 0,
        "all_different": False,
        "details": [],
    }

    theme_colors = set()
    hero_titles = set()
    layouts = set()

    for niche, expected_archetype, test_num in test_cases:
        facts = {
            "business": {
                "name": f"Nome do {niche.title()}",
                "segment": niche,
                "city": "Curitiba",
                "whatsapp": "41999999999",
                "rating": "4.8",
            },
            "segmento": niche,
        }

        # Generate the site files
        files = _generate_studio_fallback_files(facts)

        # Get archetype and palette
        actual_archetype = _get_archetype_for_segment(niche)
        palette = _get_archetype_palette(actual_archetype)
        theme_color = palette["primary"]

        # Extract hero title
        hero_content = files.get("src/components/HeroSection.tsx", "")
        h_matches = re.findall(r"<h[12][^>]*>\s*([^<]+?)\s*</h[12]>", hero_content)
        hero_title = h_matches[0].strip() if h_matches else "NOT FOUND"
        hero_titles.add(hero_title)

        # Extract layout
        layout_type = "split"
        if "lg:grid-cols-[1.05fr_.95fr]" in hero_content:
            layout_type = "split"
        elif "max-w-4xl text-center" in hero_content:
            layout_type = "center"
        elif "lg:grid-cols-[1.4fr_1fr]" in hero_content:
            layout_type = "asymmetric"
        elif "min-h-screen" in hero_content and "object-cover" in hero_content:
            layout_type = "fullbleed"
        elif "min-h-screen" in hero_content and "clamp(3.5rem" in hero_content:
            layout_type = "video"
        layouts.add(layout_type)

        # Verify colors in component
        has_theme_color = theme_color.lower() in hero_content.lower()
        has_bg_color = palette["bg_dark"].lower() in hero_content.lower()

        theme_colors.add(theme_color)

        results["details"].append({
            "test": test_num,
            "niche": niche,
            "archetype": actual_archetype,
            "theme_color": theme_color,
            "hero_title": hero_title[:50],
            "layout": layout_type,
            "archetype_match": actual_archetype == expected_archetype,
            "colors_in_component": has_theme_color and has_bg_color,
        })

        results["sites_generated"] += 1

    # Calculate metrics
    results["unique_theme_colors"] = len(theme_colors)
    results["unique_hero_titles"] = len(hero_titles)
    results["unique_layouts"] = len(layouts)
    results["all_different"] = (
        results["unique_theme_colors"] >= 5 and
        results["unique_hero_titles"] >= 5
    )

    return results


if __name__ == "__main__":
    results = run_archetype_test()

    print("TEST RESULTS:")
    print("=" * 60)
    for detail in results["details"]:
        print(f"Test {detail['test']}: {detail['niche']}")
        print(f"  Archetype: {detail['archetype']} (match: {detail['archetype_match']})")
        print(f"  Theme color: {detail['theme_color']}")
        print(f"  Hero: {detail['hero_title'][:40]}...")
        print(f"  Layout: {detail['layout']}")
        print(f"  Colors in component: {detail['colors_in_component']}")
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Sites generated: {results['sites_generated']}")
    print(f"Unique theme colors: {results['unique_theme_colors']}")
    print(f"Unique hero titles: {results['unique_hero_titles']}")
    print(f"Unique layouts: {results['unique_layouts']}")
    print(f"All different: {results['all_different']}")

    print("\nFINAL REPORT:")
    report = {
        "sites_generated": results["sites_generated"],
        "unique_theme_colors": results["unique_theme_colors"],
        "unique_hero_titles": results["unique_hero_titles"],
        "unique_layouts": results["unique_layouts"],
        "all_different": results["all_different"],
    }
    print(json.dumps(report, indent=2))
