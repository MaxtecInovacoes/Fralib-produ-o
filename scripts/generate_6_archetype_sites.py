#!/usr/bin/env python3
"""Generate 6 archetype sites with proper differentiation - Sprint 16."""

import sys
import os
import subprocess
import json
from pathlib import Path

# Set to use archetype-based generator (not cinematic)
os.environ['FRALIB_VITE_CINEMATIC_STUDIO'] = '0'

sys.path.insert(0, '.')

from backend.services.vite_react_renderer import (
    _generate_studio_fallback_files,
    _get_archetype_for_segment,
    _get_archetype_palette,
)

# 6 test sites with real tenant 2 data patterns
SITES = [
    {
        "segment": "academia",
        "name": "Start Fitness Academia",
        "city": "Curitiba",
        "phone": "41999999999",
        "rating": "4.8",
        "slug": "start-academia",
    },
    {
        "segment": "barbearia",
        "name": "Fio Nobre Barbearia",
        "city": "Pinhais",
        "phone": "41999999999",
        "rating": "4.8",
        "slug": "barbearia-fio-nobre",
    },
    {
        "segment": "clinica",
        "name": "Clinica Vida Plena",
        "city": "São Paulo",
        "phone": "11999999999",
        "rating": "4.9",
        "slug": "clinica-vida",
    },
    {
        "segment": "restaurante",
        "name": "Sabor da Casa",
        "city": "Rio de Janeiro",
        "phone": "21999999999",
        "rating": "4.7",
        "slug": "restaurante-sabor",
    },
    {
        "segment": "energia solar",
        "name": "Solar Tech Brasil",
        "city": "Belo Horizonte",
        "phone": "31999999999",
        "rating": "4.9",
        "slug": "solar-energy",
    },
    {
        "segment": "imobiliaria",
        "name": "Imob Prime",
        "city": "Porto Alegre",
        "phone": "51999999999",
        "rating": "4.6",
        "slug": "imob-prime",
    },
]

def main():
    print("=" * 70)
    print("GENERATING 6 ARCHETYPE SITES WITH PROPER DIFFERENTIATION")
    print("=" * 70)
    print()

    base_dir = Path("C:/fralib/sites")
    results = []

    for i, site in enumerate(SITES, 1):
        segment = site["segment"]
        name = site["name"]
        slug = site["slug"]

        print(f"[{i}/6] Generating: {name} ({segment})")

        # Generate facts
        facts = {
            "business": {
                "name": name,
                "segment": segment,
                "city": site["city"],
                "phone": site["phone"],
                "rating": site["rating"],
            }
        }

        # Get expected archetype
        archetype = _get_archetype_for_segment(segment)
        palette = _get_archetype_palette(archetype)
        expected_color = palette["primary"]

        # Generate files
        files = _generate_studio_fallback_files(facts)

        # Verify colors
        css = files.get("src/index.css", "")
        has_correct_color = expected_color in css
        has_root = ":root" in css

        # Verify fonts
        if segment == "academia":
            has_font = "Oswald" in css
        elif segment == "barbearia":
            has_font = "Playfair" in css
        elif segment == "clinica":
            has_font = "Nunito" in css
        elif segment == "restaurante":
            has_font = "Montserrat" in css
        elif segment == "energia solar":
            has_font = "Space" in css
        else:
            has_font = "IBM" in css

        status = "OK" if (has_correct_color and has_root and has_font) else "FAIL"
        print(f"   -> Archetype: {archetype}")
        print(f"   -> Color: {expected_color} (correct: {has_correct_color})")
        print(f"   -> CSS :root: {has_root}")
        print(f"   -> Font: {has_font}")
        print(f"   -> Status: {status}")
        print()

        # Save to disk
        site_dir = base_dir / f"tenant2-{slug}"
        site_dir.mkdir(parents=True, exist_ok=True)

        for path, content in files.items():
            file_path = site_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        print(f"   -> Saved to: {site_dir}")
        print()

        results.append({
            "slug": slug,
            "segment": segment,
            "archetype": archetype,
            "color": expected_color,
            "status": status,
        })

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for r in results:
        print(f"[{r['status']}] {r['slug']} -> {r['archetype']} ({r['color']})")

    all_ok = all(r["status"] == "OK" for r in results)
    print()
    if all_ok:
        print("ALL 6 SITES GENERATED SUCCESSFULLY WITH DIFFERENT COLORS!")
    else:
        print("SOME SITES FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
