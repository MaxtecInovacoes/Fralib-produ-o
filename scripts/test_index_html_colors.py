#!/usr/bin/env python3
"""Full integration test for archetype differentiation - Sprint 16."""

import sys
import os
import re
sys.path.insert(0, ".")

from backend.services.vite_templates import vite_template_index_html

# Test cases: (segment, business_name, expected_theme_color)
test_cases = [
    ("academia", "Start Fitness", "#ef4444", "Vermelho/energia"),
    ("barbearia", "Fio Nobre Barbearia", "#d97706", "Ambar/dourado"),
    ("clinica", "Clinica Vida Plena", "#10b981", "Verde esmeralda"),
    ("restaurante", "Sabor da Casa", "#a855f7", "Roxo/luxo"),
    ("energia solar", "Solar Tech", "#3b82f6", "Azul/tecnologia"),
    ("imobiliaria", "Imob Prime", "#0891b2", "Ciano/profissional"),
]

print("Testing index.html theme-color generation...\n")
all_passed = True

for segment, business_name, expected_color, description in test_cases:
    facts = {
        "business": {
            "name": business_name,
            "segment": segment,
            "phone": "41999999999",
        },
        "_archetype_palette": {
            "primary": expected_color,
        }
    }

    html = vite_template_index_html(facts)

    # Extract theme-color from HTML
    match = re.search(r'<meta name="theme-color" content="([^"]+)"', html)
    actual_color = match.group(1) if match else None

    passed = actual_color == expected_color

    status = "[OK]" if passed else "[FAIL]"
    print(f"{status} Segment: '{segment}' ({description})")
    print(f"   Business: {business_name}")
    print(f"   Theme-color: {actual_color} (expected: {expected_color})")
    print()

    if not passed:
        all_passed = False
        if actual_color:
            print(f"   -> Got wrong color. This means archetype palette was not injected.")
        else:
            print(f"   -> Could not find theme-color meta tag!")

# Summary
print("=" * 60)
if all_passed:
    print("[OK] ALL TESTS PASSED - index.html gets correct theme-color!")
else:
    print("[FAIL] SOME TESTS FAILED!")
    sys.exit(1)
