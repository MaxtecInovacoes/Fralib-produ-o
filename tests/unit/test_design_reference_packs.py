import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from core.design_reference_packs import (
    REFERENCE_ROLES,
    build_design_reference_pack,
    format_design_reference_pack_prompt,
)
from core.design_system_router import build_design_dna


def test_reference_pack_is_curated_and_actionable():
    pack = build_design_reference_pack(
        segmento="academia",
        business_name="High Fitness Academia",
        lead_id="lead-123",
        tier="PREMIUM",
    )

    assert pack["source"] == "opendesign_curated_reference_pack"
    assert pack["archetype"] == "BOLD_ENERGY"
    assert set(REFERENCE_ROLES).issubset(pack["references"].keys())
    assert pack["dna_combo"]["structure_ref"] == pack["references"]["structure"]["slug"]
    assert pack["tokens"]["--bg"]
    assert pack["typography"]["heading"]
    assert "full-bleed" in pack["constraints"]["hero"] or "poster" in pack["constraints"]["hero"]


def test_reference_pack_is_deterministic_per_lead_seed():
    first = build_design_reference_pack("nutricionista", "Priscila Botelho", "lead-abc")
    second = build_design_reference_pack("nutricionista", "Priscila Botelho", "lead-abc")
    other = build_design_reference_pack("nutricionista", "Priscila Botelho", "lead-other")

    assert first["id"] == second["id"]
    assert first["dna_combo"] == second["dna_combo"]
    assert first["id"] != other["id"]


def test_design_dna_exposes_reference_pack_to_renderers():
    dna = build_design_dna(
        segmento="odontologia",
        business_name="Odontologia Jardim Paulista",
        lead_id="lead-odonto",
    )

    pack = dna["design_reference_pack"]
    assert pack["id"]
    assert pack["archetype"] == "TRUST_ELITE"
    assert dna["dna_combo"] == pack["dna_combo"]
    assert dna["style_mix_instruction"] == pack["instruction"]
    assert dna["tokens"] == pack["tokens"]


def test_pizzaria_does_not_match_ia_inside_word():
    pack = build_design_reference_pack(
        segmento="restaurante",
        business_name="Duetto Café Restaurante e Pizzaria",
        lead_id="lead-duetto",
    )

    assert pack["archetype"] == "LUXURY_ELITE"
    assert "MODERN_TECH" not in pack["id"]


def test_reference_pack_prompt_stays_compact():
    pack = build_design_reference_pack("academia", "High Fitness Academia", "lead-123")
    prompt = format_design_reference_pack_prompt(pack)

    assert "DESIGN REFERENCE PACK CURADO" in prompt
    assert "structure:" in prompt
    assert "Proibido:" in prompt
    assert len(prompt) < 2500
