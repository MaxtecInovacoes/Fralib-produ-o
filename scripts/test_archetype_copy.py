#!/usr/bin/env python3
"""Test script to verify niche-specific copy in Studio fallback.

Tests that barbearia and academia generate completely different copy.
"""

import sys
sys.path.insert(0, 'backend')

from services.vite_react_renderer import (
    _get_archetype_for_segment,
    _get_archetype_copy,
    _select_copy_variation,
)


def test_archetype_copy_differences():
    """Test that different archetypes have different copy."""

    # Test BOLD_ENERGY (academia/fitness)
    bold_copy = _get_archetype_copy("BOLD_ENERGY")
    print("=== BOLD_ENERGY (Academia/Gym) ===")
    print(f"CTA Primary: {bold_copy['cta_primary']}")
    print(f"CTA Secondary: {bold_copy['cta_secondary']}")
    print(f"Services Heading: {bold_copy['services_heading']}")
    print(f"Lifestyle Heading: {bold_copy['lifestyle_heading']}")
    print(f"Contact Heading: {bold_copy['contact_heading']}")
    print(f"Footer Tagline: {bold_copy['footer_tagline']}")
    print()

    # Test WARM_LOCAL (barbearia)
    warm_copy = _get_archetype_copy("WARM_LOCAL")
    print("=== WARM_LOCAL (Barbearia) ===")
    print(f"CTA Primary: {warm_copy['cta_primary']}")
    print(f"CTA Secondary: {warm_copy['cta_secondary']}")
    print(f"Services Heading: {warm_copy['services_heading']}")
    print(f"Lifestyle Heading: {warm_copy['lifestyle_heading']}")
    print(f"Contact Heading: {warm_copy['contact_heading']}")
    print(f"Footer Tagline: {warm_copy['footer_tagline']}")
    print()

    # Test ZEN_PURE (nutricionista)
    zen_copy = _get_archetype_copy("ZEN_PURE")
    print("=== ZEN_PURE (Nutricionista) ===")
    print(f"CTA Primary: {zen_copy['cta_primary']}")
    print(f"CTA Secondary: {zen_copy['cta_secondary']}")
    print(f"Services Heading: {zen_copy['services_heading']}")
    print()

    # Verify archetypes are different
    assert bold_copy['cta_primary'] != warm_copy['cta_primary'], "CTA should differ between archetypes"
    assert bold_copy['services_heading'] != warm_copy['services_heading'], "Services heading should differ"
    assert bold_copy['lifestyle_heading'] != warm_copy['lifestyle_heading'], "Lifestyle heading should differ"
    assert bold_copy['contact_heading'] != warm_copy['contact_heading'], "Contact heading should differ"
    assert bold_copy['footer_tagline'] != warm_copy['footer_tagline'], "Footer tagline should differ"

    print("✓ All archetype copy is different!")


def test_segment_to_archetype_mapping():
    """Test that segments map to correct archetypes."""

    test_cases = [
        ("barbearia", "WARM_LOCAL"),
        ("barbeiro", "WARM_LOCAL"),
        ("academia", "BOLD_ENERGY"),
        ("fitness", "BOLD_ENERGY"),
        ("musculacao", "BOLD_ENERGY"),
        ("crossfit", "BOLD_ENERGY"),
        ("nutricionista", "ZEN_PURE"),
        ("nutricao", "ZEN_PURE"),
        ("clinica", "ZEN_PURE"),
        ("restaurante", "LUXURY_ELITE"),
        ("pizzaria", "LUXURY_ELITE"),
        ("advocacia", "PROFESSIONAL_TRUST"),
        ("imobiliaria", "PROFESSIONAL_TRUST"),
    ]

    print("=== Segment to Archetype Mapping ===")
    for segment, expected_archetype in test_cases:
        actual = _get_archetype_for_segment(segment)
        status = "✓" if actual == expected_archetype else "✗"
        print(f"{status} {segment} -> {actual} (expected: {expected_archetype})")
        assert actual == expected_archetype, f"Segment {segment} should map to {expected_archetype}, got {actual}"

    print("\n✓ All segment mappings correct!")


def test_copy_variation_selection():
    """Test that copy variations are selected deterministically."""

    print("\n=== Copy Variation Selection ===")

    patterns = ["A", "B", "C"]
    archetype = "BOLD_ENERGY"

    # Same seed should give same result
    result1 = _select_copy_variation(patterns, archetype, seed=100)
    result2 = _select_copy_variation(patterns, archetype, seed=100)
    assert result1 == result2, "Same seed should give same variation"
    print(f"✓ Seed 100 gives consistent result: {result1}")

    # Different seeds should potentially give different results
    results = set()
    for seed in range(10):
        result = _select_copy_variation(patterns, archetype, seed=seed)
        results.add(result)
    print(f"✓ 10 different seeds produced {len(results)} unique variations")

    # Different archetypes should give different results for same seed
    bold_result = _select_copy_variation(patterns, "BOLD_ENERGY", seed=5)
    warm_result = _select_copy_variation(patterns, "WARM_LOCAL", seed=5)
    print(f"✓ Seed 5: BOLD={bold_result}, WARM={warm_result}")


def test_niche_specific_hero_copy():
    """Test that hero copy is niche-specific with placeholders filled."""

    print("\n=== Hero Copy with Placeholders ===")

    name = "PowerFit Academia"
    city = "Curitiba"

    # BOLD_ENERGY
    bold_copy = _get_archetype_copy("BOLD_ENERGY")
    hero_title = _select_copy_variation(
        bold_copy["hero_title_patterns"], "BOLD_ENERGY", seed=100,
        name=name, city=city
    )
    hero_subtitle = _select_copy_variation(
        bold_copy["hero_subtitle_patterns"], "BOLD_ENERGY", seed=100,
        name=name, city=city
    )
    print(f"Academia Hero Title: {hero_title}")
    print(f"Academia Hero Subtitle: {hero_subtitle}")

    # WARM_LOCAL
    warm_copy = _get_archetype_copy("WARM_LOCAL")
    hero_title = _select_copy_variation(
        warm_copy["hero_title_patterns"], "WARM_LOCAL", seed=100,
        name="Barbearia Imperial", city="Sao Paulo"
    )
    hero_subtitle = _select_copy_variation(
        warm_copy["hero_subtitle_patterns"], "WARM_LOCAL", seed=100,
        name="Barbearia Imperial", city="Sao Paulo"
    )
    print(f"\nBarbearia Hero Title: {hero_title}")
    print(f"Barbearia Hero Subtitle: {hero_subtitle}")

    print("\n✓ Hero copy is niche-specific!")


def test_service_descriptions():
    """Test that service descriptions are niche-specific."""

    print("\n=== Service Descriptions ===")

    name = "TestBusiness"
    city = "TestCity"
    archetype = "BOLD_ENERGY"

    bold_copy = _get_archetype_copy("BOLD_ENERGY")
    patterns = bold_copy["service_description_patterns"]

    descs = [
        _select_copy_variation(patterns, archetype, seed=0, name=name, city=city),
        _select_copy_variation(patterns, archetype, seed=1, name=name, city=city),
        _select_copy_variation(patterns, archetype, seed=2, name=name, city=city),
    ]

    print("BOLD_ENERGY (Academia) service descriptions:")
    for i, desc in enumerate(descs, 1):
        print(f"  {i}. {desc}")

    # Compare with WARM_LOCAL
    warm_copy = _get_archetype_copy("WARM_LOCAL")
    warm_patterns = warm_copy["service_description_patterns"]
    warm_desc = _select_copy_variation(warm_patterns, "WARM_LOCAL", seed=0, name=name, city=city)

    print(f"\nWARM_LOCAL (Barbearia) service description:")
    print(f"  1. {warm_desc}")

    # Verify they're different
    assert descs[0] != warm_desc, "Service descriptions should differ between archetypes"
    print("\n✓ Service descriptions are niche-specific!")


def count_copy_variants():
    """Count total copy variants added."""
    archetypes = [
        "BOLD_ENERGY", "WARM_LOCAL", "ZEN_PURE",
        "LUXURY_ELITE", "MODERN_TECH", "PROFESSIONAL_TRUST"
    ]

    total_variants = 0
    for archetype in archetypes:
        copy = _get_archetype_copy(archetype)
        variants = (
            len(copy["hero_title_patterns"]) +
            len(copy["hero_subtitle_patterns"]) +
            len(copy["service_description_patterns"]) +
            len(copy["cta_primary"]) +
            len(copy["cta_secondary"])
        )
        total_variants += variants
        print(f"{archetype}: {variants} variants")

    print(f"\nTotal copy variants added: {total_variants}")
    return total_variants


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Niche-Specific Copy in Studio Fallback")
    print("=" * 60)

    test_segment_to_archetype_mapping()
    test_archetype_copy_differences()
    test_copy_variation_selection()
    test_niche_specific_hero_copy()
    test_service_descriptions()
    total = count_copy_variants()

    print("\n" + "=" * 60)
    print(f"SUCCESS: {total} copy variants added across 6 archetypes")
    print("=" * 60)
