"""Curated design reference packs for FraLib visual generation.

The extracted design-system library gives us many raw systems. Runtime should not load all
of them. This module turns the library into compact, deterministic packs that
Arquiteto/Builder can actually obey.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

# Bloqueia caracteres CJK (chinês/japonês/coreano) de vazarem pros prompts
# do LLM e, em última instância, pro HTML do site gerado.
_CJK_PATTERN = re.compile(r"[一-鿿㐀-䶿豈-﫿぀-ヿ゠-ヿ]")


def _strip_cjk(value: Any) -> Any:
    """Remove caracteres CJK de strings. Não recursivo para preservar estrutura."""
    if not isinstance(value, str):
        return value
    return _CJK_PATTERN.sub("", value).strip()

try:
    from agents.design_context import DIRECOES_VISUAIS
except Exception:  # pragma: no cover - local import variant
    from design_context import DIRECOES_VISUAIS

try:
    from core.archetypes import select_archetype
except Exception:  # pragma: no cover - local import variant
    from archetypes import select_archetype


REFERENCE_ROLES = ("structure", "typography", "color", "motion", "spacing")


CURATED_REFERENCES: dict[str, dict[str, list[str]]] = {
    "BOLD_ENERGY": {
        "structure": ["nike", "bmw_m", "spacex", "theverge", "uber", "bold"],
        "typography": ["nike", "theverge", "spacex", "bold", "uber"],
        "color": ["bmw_m", "spotify", "vodafone", "sanity", "bold"],
        "motion": ["nike", "spotify", "theverge", "energetic", "vibrant"],
        "spacing": ["nike", "spacex", "bmw_m", "dramatic", "bold"],
    },
    "TRUST_ELITE": {
        "structure": ["apple", "linear", "wise", "webflow", "corporate", "bmw"],
        "typography": ["apple", "linear", "bmw", "refined", "webflow"],
        "color": ["coinbase", "wise", "bmw", "webex", "corporate"],
        "motion": ["apple", "linear", "webflow", "elegant", "refined"],
        "spacing": ["apple", "spacious", "linear", "corporate", "minimal"],
    },
    "ZEN_PURE": {
        "structure": ["airbnb", "apple", "clay", "clean", "spacious", "starbucks"],
        "typography": ["airbnb", "apple", "clean", "refined", "clay"],
        "color": ["starbucks", "airbnb", "clay", "clean", "claude"],
        "motion": ["airbnb", "clay", "elegant", "warm_editorial", "clean"],
        "spacing": ["spacious", "apple", "airbnb", "clean", "minimal"],
    },
    "MODERN_TECH": {
        "structure": ["linear", "vercel", "linear", "cursor", "supabase", "webflow"],
        "typography": ["vercel", "linear", "cursor", "supabase", "webflow"],
        "color": ["linear", "supabase", "cursor", "canva", "webflow"],
        "motion": ["linear", "vercel", "canva", "vibrant", "linear"],
        "spacing": ["vercel", "linear", "linear", "webflow", "spacious"],
    },
    "LUXURY_ELITE": {
        "structure": ["bugatti", "runwayml", "bmw", "refined", "luxury", "premium"],
        "typography": ["bugatti", "refined", "bmw", "luxury", "warm_editorial"],
        "color": ["bugatti", "runwayml", "bmw", "resend", "premium"],
        "motion": ["bugatti", "runwayml", "elegant", "refined", "luxury"],
        "spacing": ["bugatti", "spacious", "runwayml", "refined", "minimal"],
    },
}


ARCHETYPE_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "BOLD_ENERGY": {
        "theme": "dark_cinematic",
        "hero": "full-bleed or poster-like, dominant image/texture, red action line, stat slabs",
        "spacing": "dense hero, generous section breaks, hard crops, no airy institutional stacking",
        "motion": "fast mask reveal, parallax crop, short stagger, strong scroll progress",
        "ban": ["pastel wellness", "beige institutional", "white card grid", "soft SaaS radius"],
    },
    "TRUST_ELITE": {
        "theme": "structured_confidence",
        "hero": "clear authority, restrained asymmetry, proof and contact visible early",
        "spacing": "precise grid, broad margins, calm section rhythm",
        "motion": "subtle reveal, no theatrical motion on legal/clinical content",
        "ban": ["neon", "chaotic collage", "fake awards", "over-aggressive claims"],
    },
    "ZEN_PURE": {
        "theme": "mineral_wellness_editorial",
        "hero": "asymmetric care editorial, mineral/eucalyptus surface, human proof and one dominant media/depth layer",
        "spacing": "breathing room with commercial density; no empty kilometer of blank page",
        "motion": "slow parallax, soft mask reveal, proof stagger, no bounce",
        "ban": ["cream/sand/beige default", "hospital gray cards", "cold corporate blue", "crowded white cards", "gray-on-white low contrast"],
    },
    "MODERN_TECH": {
        "theme": "technical_clarity",
        "hero": "system/product energy, precise grid, one strong visual mechanism",
        "spacing": "sharp modular blocks, responsive bento only when it carries information",
        "motion": "snappy reveal, interface-like transitions, no decorative glass by default",
        "ban": ["purple SaaS cliché", "generic dashboard cards", "fake integrations"],
    },
    "LUXURY_ELITE": {
        "theme": "editorial_luxury",
        "hero": "monumental image or type, sparse copy, premium restraint",
        "spacing": "extreme negative space, full-bleed media, very few cards",
        "motion": "slow cinematic reveal, image mask, no playful bounce",
        "ban": ["cheap gold gradients", "busy icon grids", "discount language"],
    },
}


def build_visual_seed(lead_id: str = "", business_name: str = "", segmento: str = "") -> str:
    raw = f"{lead_id}|{business_name}|{segmento}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_design_reference_pack(
    segmento: str,
    business_name: str = "",
    lead_id: str = "",
    tier: str = "STANDARD",
    base_design: dict[str, Any] | None = None,
    dados_lead: dict | None = None,
) -> dict[str, Any]:
    """Return a compact, deterministic reference pack from extracted data."""
    archetype = select_archetype(segmento, business_name, dados_lead)
    archetype_id = str(archetype.get("archetype") or "TRUST_ELITE")
    visual_seed = build_visual_seed(lead_id, business_name, segmento)
    rng = random.Random(int(visual_seed[:12], 16))
    role_pools = CURATED_REFERENCES.get(archetype_id, CURATED_REFERENCES["TRUST_ELITE"])
    index = _load_design_system_index()

    references: dict[str, dict[str, Any]] = {}
    for role in REFERENCE_ROLES:
        slug = _pick_available(role_pools.get(role, []), rng)
        references[role] = _reference_summary(slug, role, index)

    color_ref = references["color"]["slug"]
    typography_ref = references["typography"]["slug"]
    color_tokens = deepcopy(_tokens_for(color_ref))
    base_tokens = deepcopy((base_design or {}).get("tokens") or {})
    tokens = color_tokens or base_tokens
    if base_tokens:
        tokens["--accent"] = base_tokens.get("--accent", tokens.get("--accent"))

    typography_source = DIRECOES_VISUAIS.get(typography_ref, {})
    typography = {
        "heading": typography_source.get("font_heading")
        or (base_design or {}).get("font_heading")
        or "Outfit",
        "body": typography_source.get("font_body")
        or (base_design or {}).get("font_body")
        or "Outfit",
    }

    combo = {f"{role}_ref": references[role]["slug"] for role in REFERENCE_ROLES}
    constraints = ARCHETYPE_CONSTRAINTS.get(archetype_id, ARCHETYPE_CONSTRAINTS["TRUST_ELITE"])
    instruction = (
        f"Use estrutura {combo['structure_ref']}, tipografia {combo['typography_ref']}, "
        f"paleta {combo['color_ref']}, motion {combo['motion_ref']} e spacing {combo['spacing_ref']}. "
        f"Regra do arquétipo {archetype_id}: {constraints['hero']}."
    )
    return {
        "id": f"{archetype_id.lower()}-{visual_seed[:8]}",
        "source": "opendesign_curated_reference_pack",
        "archetype": archetype_id,
        "visual_seed": visual_seed,
        "tier": tier,
        "references": references,
        "dna_combo": combo,
        "tokens": tokens,
        "typography": typography,
        "constraints": constraints,
        "instruction": instruction,
    }


def format_design_reference_pack_prompt(pack: dict[str, Any]) -> str:
    """Small prompt block for Arquiteto/Builder. Never include raw DESIGN.md."""
    if not isinstance(pack, dict) or not pack:
        return ""
    refs = pack.get("references") or {}
    lines = [
        "=== DESIGN REFERENCE PACK CURADO ===",
        f"ID: {pack.get('id')} | Fonte: {pack.get('source')}",
        f"Arquétipo: {pack.get('archetype')} | Seed: {pack.get('visual_seed')}",
        f"Instrução: {pack.get('instruction')}",
    ]
    for role in REFERENCE_ROLES:
        ref = refs.get(role) or {}
        if ref:
            lines.append(
                f"- {role}: {ref.get('slug')} | {ref.get('vibe')} | aplicar: {ref.get('use_for')}"
            )
    constraints = pack.get("constraints") or {}
    if constraints:
        lines.append(f"Hero: {constraints.get('hero')}")
        lines.append(f"Spacing: {constraints.get('spacing')}")
        lines.append(f"Motion: {constraints.get('motion')}")
        ban = ", ".join(constraints.get("ban") or [])
        if ban:
            lines.append(f"Proibido: {ban}")
    lines.append("=== FIM DESIGN REFERENCE PACK ===")
    return "\n".join(lines)


def _pick_available(pool: list[str], rng: random.Random) -> str:
    available = [_normalize_slug(slug) for slug in pool if _normalize_slug(slug) in DIRECOES_VISUAIS]
    if not available:
        available = ["clean"] if "clean" in DIRECOES_VISUAIS else list(DIRECOES_VISUAIS.keys())
    return rng.choice(available)


def _reference_summary(slug: str, role: str, index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    data = DIRECOES_VISUAIS.get(slug, {})
    idx = index.get(_denormalize_slug(slug), {}) or index.get(slug, {})
    return {
        "slug": slug,
        "role": role,
        "category": idx.get("category") or "",
        "name": data.get("nome") or idx.get("slug") or slug,
        "vibe": _strip_cjk(data.get("vibe") or idx.get("atmosphere") or ""),
        "font_heading": data.get("font_heading") or idx.get("font_primary") or "",
        "font_body": data.get("font_body") or "",
        "tokens": deepcopy(data.get("tokens") or {}),
        "use_for": _role_use(role),
    }


def _role_use(role: str) -> str:
    return {
        "structure": "grid, seção hero, ritmo e composição",
        "typography": "escala, contraste de peso e voz tipográfica",
        "color": "paleta base, contraste e acento",
        "motion": "cadência, reveal, parallax e microinterações",
        "spacing": "densidade, respiro e proporção entre blocos",
    }.get(role, "referência visual")


def _tokens_for(slug: str) -> dict[str, str]:
    return deepcopy((DIRECOES_VISUAIS.get(slug) or {}).get("tokens") or {})


def _normalize_slug(slug: str) -> str:
    slug = (slug or "").strip().lower().replace("-", "_")
    if slug == "linear_app":
        return "linear"
    if slug == "bmw_motorsport":
        return "bmw_m"
    return slug


def _denormalize_slug(slug: str) -> str:
    return (slug or "").replace("_", "-")


def _load_design_system_index() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / "agents" / "design_system_index.json"
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(rows, list):
        return {}
    return {str(row.get("slug") or ""): row for row in rows if isinstance(row, dict)}
