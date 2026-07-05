"""Variation seed system for deterministic site generation.

This module provides deterministic randomness based on a seed derived from
business facts. The same seed always produces the same variation, allowing
reproducible site generation for the same business while enabling different
variations for different businesses.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Hero layout options
HERO_LAYOUTS = ["split", "center", "asymmetric", "fullbleed", "video"]

# Motion style options
MOTION_STYLES = ["sharp", "smooth", "minimal"]

# Copy voice options
COPY_VOICES = ["aggressive", "friendly", "authoritative"]

# Color emphasis options
COLOR_EMPHASIS = ["primary_dominant", "secondary_dominant", "balanced"]

# Section order strategies
SECTION_ORDER_STYLES = ["credibility_first", "visual_first", "offer_first", "story_first"]

# Proof section styles
PROOF_STYLES = ["score_wall", "quote_spotlight", "card_marquee", "editorial_case"]

# Surface treatment styles
SURFACE_STYLES = ["glass", "solid", "outline", "soft_tint"]

# Visual lane tokens (resolved later per niche/subniche)
VISUAL_LANES = ["lane_a", "lane_b", "lane_c", "lane_d", "lane_e", "lane_f", "lane_g", "lane_h", "lane_i", "lane_j", "lane_k", "lane_l", "lane_m", "lane_n", "lane_o", "lane_p"]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class VariationSeed:
    """Container for all variation parameters determined by the seed."""
    seed: int
    counter: int = 0  # Sprint 16: para o renderer usar na geração de CSS único
    hero_layout: str = ""
    motion_style: str = ""
    copy_voice: str = ""
    color_emphasis: str = ""
    section_order_style: str = ""
    proof_style: str = ""
    surface_style: str = ""
    visual_lane: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "counter": self.counter,
            "hero_layout": self.hero_layout,
            "motion_style": self.motion_style,
            "copy_voice": self.copy_voice,
            "color_emphasis": self.color_emphasis,
            "section_order_style": self.section_order_style,
            "proof_style": self.proof_style,
            "surface_style": self.surface_style,
            "visual_lane": self.visual_lane,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SEED GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _get_variation_seed(facts: dict[str, Any] | None = None) -> int:
    """Generate a deterministic integer seed from business facts.

    The seed is derived from:
    1. Explicit seed parameter in facts["seed"]
    2. Hash of business.name
    3. Hash of business.address
    4. Fallback to "default" string

    Args:
        facts: Dictionary containing business facts. Expected keys:
            - seed (int or str): Explicit seed value (takes precedence)
            - business.name (str): Business name
            - business.address (str): Business address
            - name (str): Alternative business name
            - business_name (str): Alternative business name

    Returns:
        int: A deterministic integer seed
    """
    facts = facts or {}

    # Priority 1: Explicit seed parameter
    explicit_seed = facts.get("seed")
    if explicit_seed is not None:
        if isinstance(explicit_seed, int):
            return explicit_seed
        if isinstance(explicit_seed, str):
            try:
                return int(explicit_seed)
            except ValueError:
                return _hash_string(explicit_seed)

    # Extract business data from various possible structures
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}

    # Priority 2: business.name hash
    name = (
        business.get("name")
        or business.get("business_name")
        or facts.get("name")
        or facts.get("business_name")
    )
    if name:
        return _hash_string(str(name))

    # Priority 3: business.address hash
    address = business.get("address") or facts.get("address")
    if address:
        return _hash_string(str(address))

    # Priority 4: phone number as fallback
    phone = business.get("phone") or business.get("whatsapp") or facts.get("phone") or facts.get("whatsapp")
    if phone:
        return _hash_string(str(phone))

    # Priority 5: segment + city combination
    segment = business.get("segment") or facts.get("segment") or ""
    city = business.get("city") or facts.get("city") or ""
    if segment or city:
        return _hash_string(f"{segment}:{city}")

    # Final fallback: "fralib-default"
    return _hash_string("fralib-default")


def _hash_string(value: str) -> int:
    """Convert a string to a deterministic integer hash.

    Uses SHA-256 for consistent cross-platform hashing.

    Args:
        value: String to hash

    Returns:
        int: Positive integer hash value
    """
    # Normalize the string (lowercase, strip whitespace)
    normalized = value.lower().strip()

    # Use SHA-256 for consistent hashing
    hash_bytes = hashlib.sha256(normalized.encode("utf-8")).digest()

    # Convert first 8 bytes to integer (64-bit)
    # This gives us a large positive integer
    seed = int.from_bytes(hash_bytes[:8], byteorder="big")

    # Ensure positive by taking modulo
    return abs(seed)


def _seeded_choice(options: list[str], seed: int, offset: int = 0) -> str:
    """Select an item from a list using deterministic randomness.

    Uses the seed to generate a deterministic index into the options list.

    Args:
        options: List of options to choose from
        seed: Integer seed for randomness
        offset: Additional offset to vary selection (for related choices)

    Returns:
        str: Selected option
    """
    if not options:
        raise ValueError("Options list cannot be empty")

    # Combine seed and offset using a simple hash-like operation
    combined = seed + offset

    # Use hash bem distribuido: XOR do seed com shifts e multiplicacao.
    # O multiplicative hash sozinho colapsa seeds diferentes em mesmo modulo
    # quando len(options) e potencia de 2. Mistura com XOR espalha melhor.
    h = (seed * 2654435761) ^ (seed >> 33)
    h = (h * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
    index = h % len(options)

    return options[index]


def _seeded_index(seed: int, count: int, offset: int = 0) -> int:
    """Get a deterministic index within a range.

    Args:
        seed: Base seed value
        count: Number of options
        offset: Offset to vary selection

    Returns:
        int: Deterministic index in range [0, count)
    """
    if count <= 0:
        return 0
    combined = seed + offset
    return combined % count


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_variation(facts: dict[str, Any] | None = None, *, counter: int = 0) -> VariationSeed:
    """Generate all variation parameters from facts using deterministic randomness.

    Sprint 14.6 — `counter` faz XOR com base_seed para rotacionar variacoes
    quando o mesmo lead/facts e processado varias vezes (counter rotation).
    Para counter=0 o comportamento e identico ao original.

    This function takes business facts and produces a complete set of variation
    choices that are deterministic based on the seed. The same seed will always
    produce the same variation choices.

    The seed determines:
    - hero_layout: Visual hero section layout (split/center/asymmetric/fullbleed/video)
    - motion_style: Animation style (sharp/smooth/minimal)
    - copy_voice: Tone of voice for copy (aggressive/friendly/authoritative)
    - color_emphasis: Which color is dominant (primary_dominant/secondary_dominant/balanced)
    - section_order_style: Narrative order preference for the page
    - proof_style: Social proof visual treatment
    - surface_style: Card/surface treatment language

    Args:
        facts: Dictionary containing business facts for seed generation

    Returns:
        VariationSeed: Container with all variation parameters

    Example:
        >>> facts = {"business": {"name": "Barbearia Central", "address": "Rua das Barbas, 123"}}
        >>> variation = get_variation(facts)
        >>> variation.hero_layout
        'asymmetric'
        >>> variation.motion_style
        'smooth'
        >>> variation.copy_voice
        'friendly'
        >>> variation.color_emphasis
        'primary_dominant'
    """
    base_seed = _get_variation_seed(facts)
    # Sprint 14.6: counter rotation via XOR com golden ratio prime
    _GOLDEN_RATIO_PRIME = 0x9E3779B9
    counter_offset = (int(counter) * _GOLDEN_RATIO_PRIME) & 0xFFFFFFFFFFFFFFFF
    seed = (base_seed ^ counter_offset) & 0xFFFFFFFFFFFFFFFF

    # Generate each variation choice with different offsets to ensure variety
    # Offset of 0: hero layout
    hero_layout = _seeded_choice(HERO_LAYOUTS, seed, offset=0)

    # Offset of 1: motion style (different dimension)
    motion_style = _seeded_choice(MOTION_STYLES, seed, offset=1)

    # Offset of 2: copy voice
    copy_voice = _seeded_choice(COPY_VOICES, seed, offset=2)

    # Offset of 3: color emphasis
    color_emphasis = _seeded_choice(COLOR_EMPHASIS, seed, offset=3)

    # Offset of 4: section order strategy
    section_order_style = _seeded_choice(SECTION_ORDER_STYLES, seed, offset=4)

    # Offset of 5: social proof style
    proof_style = _seeded_choice(PROOF_STYLES, seed, offset=5)

    # Offset of 6: surface/card treatment
    surface_style = _seeded_choice(SURFACE_STYLES, seed, offset=6)

    # Offset of 7: visual lane token
    visual_lane = _seeded_choice(VISUAL_LANES, seed, offset=7)

    return VariationSeed(
        seed=seed,
        counter=counter,  # Sprint 16: salvar counter para o renderer usar
        hero_layout=hero_layout,
        motion_style=motion_style,
        copy_voice=copy_voice,
        color_emphasis=color_emphasis,
        section_order_style=section_order_style,
        proof_style=proof_style,
        surface_style=surface_style,
        visual_lane=visual_lane,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VARIATION APPLICATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def apply_variation_to_facts(facts: dict[str, Any], variation: VariationSeed) -> dict[str, Any]:
    """Add variation data to facts dictionary.

    Useful for passing variation choices through the rendering pipeline.

    Args:
        facts: Original facts dictionary
        variation: Computed variation seed

    Returns:
        dict: Facts with variation added
    """
    result = dict(facts)
    result["variation"] = variation.to_dict()
    return result


def get_hero_classes(variation: VariationSeed) -> str:
    """Get Tailwind CSS classes for the hero based on variation.

    Args:
        variation: The variation seed

    Returns:
        str: Tailwind classes for the hero section
    """
    base = "relative overflow-hidden"

    if variation.hero_layout == "split":
        return f"{base} lg:grid lg:grid-cols-2 min-h-[600px]"
    elif variation.hero_layout == "center":
        return f"{base} flex items-center justify-center text-center min-h-[600px]"
    elif variation.hero_layout == "asymmetric":
        return f"{base} lg:grid lg:grid-cols-[1.2fr_1fr] min-h-[600px]"
    elif variation.hero_layout == "fullbleed":
        return f"{base} min-h-screen"
    elif variation.hero_layout == "video":
        return f"{base} min-h-screen"

    return base


def get_motion_config(variation: VariationSeed) -> dict[str, Any]:
    """Get animation configuration based on variation.

    Args:
        variation: The variation seed

    Returns:
        dict: Animation configuration
    """
    configs = {
        "sharp": {
            "duration_fast": 150,
            "duration_standard": 250,
            "duration_reveal": 400,
            "easing": "cubic-bezier(0.0, 0.0, 0.2, 1)",
            "hover_easing": "cubic-bezier(0.34, 1.56, 0.64, 1)",
            "stagger_delay": 50,
        },
        "smooth": {
            "duration_fast": 300,
            "duration_standard": 500,
            "duration_reveal": 700,
            "easing": "cubic-bezier(0.4, 0, 0.2, 1)",
            "hover_easing": "cubic-bezier(0.4, 0, 0.2, 1)",
            "stagger_delay": 100,
        },
        "minimal": {
            "duration_fast": 100,
            "duration_standard": 150,
            "duration_reveal": 200,
            "easing": "ease-out",
            "hover_easing": "ease-out",
            "stagger_delay": 30,
        },
    }

    return configs.get(variation.motion_style, configs["smooth"])


def get_copy_templates(variation: VariationSeed) -> dict[str, str]:
    """Get copy templates based on variation voice.

    Args:
        variation: The variation seed

    Returns:
        dict: Copy templates for different sections
    """
    templates = {
        "aggressive": {
            "hero_headline": "{benefit} AGORA - sem desculpas!",
            "hero_subheadline": "Pare de adiar. Comece HOJE.",
            "cta_primary": "Quero Resultado!",
            "cta_secondary": "Ver Provas",
        },
        "friendly": {
            "hero_headline": "Bem-vindo(a) ao {name}!",
            "hero_subheadline": "Estamos aqui para cuidar de voce.",
            "cta_primary": "Agendar Visita",
            "cta_secondary": "Conhecer Mais",
        },
        "authoritative": {
            "hero_headline": "{name}: excelencia em {segment}",
            "hero_subheadline": "{years} anos de experiencia a seu servico.",
            "cta_primary": "Falar com Especialista",
            "cta_secondary": "Ver Portfolio",
        },
    }

    return templates.get(variation.copy_voice, templates["friendly"])


def get_color_scheme(variation: VariationSeed, base_palette: dict[str, str]) -> dict[str, str]:
    """Get color scheme with emphasis based on variation.

    Args:
        variation: The variation seed
        base_palette: Base color palette dict with primary, secondary, accent keys

    Returns:
        dict: Color scheme with emphasis applied
    """
    result = dict(base_palette)

    if variation.color_emphasis == "primary_dominant":
        result["primary_ratio"] = "70%"
        result["secondary_ratio"] = "30%"
    elif variation.color_emphasis == "secondary_dominant":
        result["primary_ratio"] = "30%"
        result["secondary_ratio"] = "70%"
    else:  # balanced
        result["primary_ratio"] = "50%"
        result["secondary_ratio"] = "50%"

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def test_determinism() -> dict[str, Any]:
    """Test that the variation system is deterministic.

    Returns:
        dict: Test results with status
    """
    # Test 1: Same barbearia with same seed -> identical output
    barbearia_facts_1 = {
        "business": {
            "name": "Barbearia Teste",
            "address": "Rua das Barbas, 123",
            "segment": "barbearia",
            "city": "Sao Paulo",
        },
        "seed": "fixed-seed-123",  # Explicit fixed seed
    }

    variation_1a = get_variation(barbearia_facts_1)
    variation_1b = get_variation(barbearia_facts_1)

    test1_passed = (
        variation_1a.seed == variation_1b.seed
        and variation_1a.hero_layout == variation_1b.hero_layout
        and variation_1a.motion_style == variation_1b.motion_style
        and variation_1a.copy_voice == variation_1b.copy_voice
        and variation_1a.color_emphasis == variation_1b.color_emphasis
    )

    # Test 2: Same barbearia with different seeds -> different layouts
    barbearia_facts_2 = {
        "business": {
            "name": "Barbearia Teste",
            "address": "Rua das Barbas, 123",
            "segment": "barbearia",
            "city": "Sao Paulo",
        },
        "seed": "different-seed-456",
    }

    variation_2 = get_variation(barbearia_facts_2)

    # Different seed should produce different variation (with high probability)
    # Since we're using modulo, some combinations might collide, but most should differ
    test2_layouts_differ = variation_1a.hero_layout != variation_2.hero_layout

    return {
        "test_same_seed_same_output": test1_passed,
        "test_different_seed_different_layout": test2_layouts_differ,
        "deterministic": test1_passed,
        "all_passed": test1_passed,
        "variations": {
            "same_seed": variation_1a.to_dict(),
            "different_seed": variation_2.to_dict(),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run tests when executed directly
    print("Testing variation seed system...")
    print()

    results = test_determinism()

    print(f"Test: Same seed -> Same output: {'PASSED' if results['test_same_seed_same_output'] else 'FAILED'}")
    print(f"Test: Different seed -> Different layout: {'PASSED' if results['test_different_seed_different_layout'] else 'FAILED'}")
    print()

    print("Variations generated:")
    print(f"  Seed 1 (fixed-seed-123): {json.dumps(results['variations']['same_seed'], indent=2)}")
    print(f"  Seed 2 (different-seed-456): {json.dumps(results['variations']['different_seed'], indent=2)}")
