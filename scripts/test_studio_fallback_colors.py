#!/usr/bin/env python3
"""Full studio fallback test - verify 6 sites generate with different designs."""

import sys
import os
import re
import hashlib
sys.path.insert(0, ".")

from backend.services.vite_react_renderer import _generate_studio_fallback_files

# Test cases: (segment, business_name, city)
test_cases = [
    ("academia", "Start Fitness Academia", "Curitiba", "#ef4444"),
    ("barbearia", "Fio Nobre Barbearia", "Pinhais", "#d97706"),
    ("clinica", "Clinica Vida Plena", "Sao Paulo", "#10b981"),
    ("restaurante", "Sabor da Casa", "Rio de Janeiro", "#a855f7"),
    ("energia solar", "Solar Tech Brasil", "Belo Horizonte", "#3b82f6"),
    ("imobiliaria", "Imob Prime", "Porto Alegre", "#0891b2"),
]

print("Testing studio fallback generation for 6 archetypes...\n")
all_colors = []
all_results = []

for segment, business_name, city, expected_primary in test_cases:
    facts = {
        "business": {
            "name": business_name,
            "segment": segment,
            "phone": "41999999999",
            "rating": "4.8",
            "city": city,
        },
    }

    files = _generate_studio_fallback_files(facts)

    # Extract theme-color from index.html
    index_html = files.get("index.html", "")
    match = re.search(r'<meta name="theme-color" content="([^"]+)"', index_html)
    theme_color = match.group(1) if match else "NOT FOUND"

    # Extract CSS colors from index.css
    index_css = files.get("src/index.css", "")
    css_match = re.search(r'--color-primary:\s*([^;]+);', index_css)
    css_primary = css_match.group(1).strip() if css_match else "NOT FOUND"

    # Get a hash of HeroSection to detect structural differences
    hero = files.get("src/components/HeroSection.tsx", "")
    hero_hash = hashlib.md5(hero.encode()).hexdigest()[:8]

    # Count components
    components = [k for k in files.keys() if k.startswith("src/components/")]

    result = {
        "segment": segment,
        "name": business_name,
        "theme_color": theme_color,
        "css_primary": css_primary,
        "hero_hash": hero_hash,
        "component_count": len(components),
        "expected": expected_primary,
    }
    all_results.append(result)
    all_colors.append(theme_color)

    passed = theme_color == expected_primary
    status = "[OK]" if passed else "[FAIL]"

    print(f"{status} {segment.upper()}")
    print(f"   Business: {business_name}")
    print(f"   Theme-color: {theme_color} (expected: {expected_primary})")
    print(f"   CSS primary: {css_primary}")
    print(f"   Hero hash: {hero_hash}")
    print(f"   Components: {len(components)}")
    print()

# Summary
print("=" * 70)

# Check all colors are unique
unique_colors = set(all_colors)
print(f"Total sites: {len(all_colors)}")
print(f"Unique colors: {len(unique_colors)} ({', '.join(sorted(unique_colors))})")
print()

if len(unique_colors) == len(all_colors):
    print("[OK] SUCCESS - All 6 sites have DIFFERENT colors!")
else:
    print("[FAIL] PROBLEM - Some sites share the same color!")
    for r in all_results:
        if r['theme_color'] != r['expected']:
            print(f"   -> {r['segment']} got {r['theme_color']} instead of {r['expected']}")
    sys.exit(1)
