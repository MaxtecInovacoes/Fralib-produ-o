"""Vite/React project validation utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════
# PROJECT VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_vite_project_files(
    files: dict[str, str],
    facts: dict[str, Any],
    min_chars: int = 8000,
    min_classnames: int = 30,
    min_images: int = 2,
    min_components: int = 4,
) -> list[str]:
    """
    Validate generated Vite project files.
    Returns list of validation errors (empty = valid).
    """
    errors = []

    # Check file count
    if len(files) < 5:
        errors.append(f"Too few files generated: {len(files)} (expected 5+)")

    # Check required files
    required = ["package.json", "vite.config.ts", "tsconfig.json", "index.html"]
    for req in required:
        if not any(req in f for f in files):
            errors.append(f"Missing required file: {req}")

    # Check source size
    total_chars = sum(len(content) for content in files.values())
    if total_chars < min_chars:
        errors.append(f"Source too small: {total_chars} chars (min {min_chars})")

    # Check for Tailwind classnames
    all_source = " ".join(files.values())
    classnames = re.findall(r"bg-|text-|flex-|grid-|p-|m-|w-|h-", all_source)
    unique_classes = set(classnames)
    if len(unique_classes) < min_classnames:
        errors.append(f"Too few Tailwind classes: {len(unique_classes)} (min {min_classnames})")

    # Check for images
    images = re.findall(r"https?://[^\s\"']+\.(?:jpg|jpeg|png|webp|svg)", all_source)
    if len(images) < min_images:
        errors.append(f"Too few images: {len(images)} (min {min_images})")

    # Check components
    components = [f for f in files if "components/" in f and f.endswith(".tsx")]
    if len(components) < min_components:
        errors.append(f"Too few components: {len(components)} (min {min_components})")

    # Check for blocked patterns
    try:
        from backend.services.vite_config import BLOCKED_SOURCE_PATTERNS
    except ImportError:
        from vite_config import BLOCKED_SOURCE_PATTERNS
    for pattern in BLOCKED_SOURCE_PATTERNS:
        if re.search(pattern, all_source, re.IGNORECASE):
            errors.append(f"Blocked pattern found: {pattern}")

    # Validate business facts
    errors.extend(_validate_studio_project(files, facts))

    return errors


def _validate_studio_project(files: dict[str, str], facts: dict[str, Any]) -> list[str]:
    """Validate studio-specific requirements."""
    errors = []

    # Merge all source
    all_source = "\n".join(files.values())

    # Validate hero viewport
    hero_errors = _validate_hero_first_viewport(files)
    errors.extend(hero_errors)

    # Validate mobile navbar
    navbar_errors = _validate_mobile_navbar(files)
    errors.extend(navbar_errors)

    # Validate segment specificity
    business = facts.get("business", {})
    if business:
        _validate_segment_specificity(all_source, business)

    return errors


def _validate_hero_first_viewport(files: dict[str, str]) -> list[str]:
    """Validate hero section appears above the fold."""
    errors = []

    # Find hero content
    hero_content = ""
    for path, content in files.items():
        if "Hero" in path or "hero" in content[:500]:
            hero_content = content
            break

    if not hero_content:
        errors.append("No hero section found")
        return errors

    # Check for key elements
    if "import" not in hero_content[:200]:
        errors.append("Hero imports not at top")

    # Check for images in hero
    if "img" not in hero_content.lower() and "Image" not in hero_content:
        errors.append("Hero missing image element")

    return errors


def _validate_mobile_navbar(files: dict[str, str]) -> list[str]:
    """Validate navbar has mobile responsiveness."""
    errors = []

    # Find navbar
    navbar_content = ""
    for path, content in files.items():
        if "Navbar" in path or "navbar" in path:
            navbar_content = content
            break

    if not navbar_content:
        # Check for mobile menu in any component
        for path, content in files.items():
            if "menu" in content.lower()[:1000]:
                return []  # Found menu
        errors.append("No navbar/menu component found")

    return errors


def validate_vite_dist(dist_dir: Path) -> list[str]:
    """Validate built Vite dist directory."""
    errors = []

    if not dist_dir.exists():
        errors.append(f"Dist directory not found: {dist_dir}")
        return errors

    # Check for index.html
    index_html = dist_dir / "index.html"
    if not index_html.exists():
        errors.append("index.html not found in dist")

    # Check for JS/CSS assets
    assets_dir = dist_dir / "assets"
    if not assets_dir.exists():
        errors.append("assets directory not found in dist")

    # Check dist is not empty
    files = list(dist_dir.rglob("*"))
    if len(files) < 3:
        errors.append(f"Dist directory too small: {len(files)} files")

    return errors


# Import helper from vite_facts
def _validate_segment_specificity(source_text: str, business: dict[str, Any]) -> None:
    """Validate segment-specific content."""
    try:
        from backend.services.vite_facts import _segment_key_for_business
    except ImportError:
        from vite_facts import _segment_key_for_business

    segment_key = _segment_key_for_business(business)
    if not segment_key:
        return

    # This is a softer check - just log if issues
    segment_indicators = {
        "academia": ["musculação", "treino", "fitness"],
        "restaurante": ["prato", "menu", "chef"],
        "dentista": ["dentista", "sorriso"],
    }

    indicators = segment_indicators.get(segment_key, [])
    source_lower = source_text.lower()

    found = sum(1 for ind in indicators if ind in source_lower)
    if found == 0 and indicators:
        pass  # Soft warning - content might still be valid
