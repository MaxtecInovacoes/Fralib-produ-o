#!/usr/bin/env python3
"""Test archetype color differentiation - Sprint 16."""

import sys
sys.path.insert(0, ".")

from backend.services.vite_react_renderer import (
    _get_archetype_for_segment,
    _get_archetype_palette,
    _get_archetype_typography,
)

# Test segments
test_cases = [
    ("academia", "BOLD_ENERGY", "#ef4444"),        # Vermelho
    ("fitness", "BOLD_ENERGY", "#ef4444"),
    ("crossfit", "BOLD_ENERGY", "#ef4444"),
    ("barbearia", "WARM_LOCAL", "#d97706"),        # Ambar/dourado
    ("barbeiro", "WARM_LOCAL", "#d97706"),
    ("salão", "WARM_LOCAL", "#d97706"),
    ("clinica", "ZEN_PURE", "#10b981"),            # Verde esmeralda
    ("nutricao", "ZEN_PURE", "#10b981"),
    ("psicologia", "ZEN_PURE", "#10b981"),
    ("restaurante", "LUXURY_ELITE", "#a855f7"),    # Roxo
    ("hotel", "LUXURY_ELITE", "#a855f7"),
    ("joalheria", "LUXURY_ELITE", "#a855f7"),
    ("energia solar", "MODERN_TECH", "#3b82f6"),   # Azul
    ("tecnologia", "MODERN_TECH", "#3b82f6"),
    ("imobiliaria", "PROFESSIONAL_TRUST", "#0891b2"), # Ciano
    ("advocacia", "PROFESSIONAL_TRUST", "#0891b2"),
]

print("Testing archetype differentiation...\n")
all_passed = True

for segment, expected_archetype, expected_primary in test_cases:
    archetype = _get_archetype_for_segment(segment)
    palette = _get_archetype_palette(archetype)
    typography = _get_archetype_typography(archetype)

    passed = archetype == expected_archetype and palette["primary"] == expected_primary

    status = "[OK]" if passed else "[FAIL]"
    print(f"{status} Segment: '{segment}'")
    print(f"   Archetype: {archetype} (expected: {expected_archetype})")
    print(f"   Primary: {palette['primary']} (expected: {expected_primary})")
    print(f"   Fonts: {typography['heading_font']} / {typography['body_font']}")
    print()

    if not passed:
        all_passed = False

# Summary
print("=" * 50)
if all_passed:
    print("[OK] ALL TESTS PASSED - Archetypes are working correctly!")
else:
    print("[FAIL] SOME TESTS FAILED - Check archetype mapping!")
    sys.exit(1)
