"""Regression tests for the Vite/React liquid site contract.

These tests keep the cheap LLM `creative_plan` path honest: the LLM may choose
JSON tokens, but the Studio must materialize those tokens into the final
blockPlan and SEO data.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.services.vite_react_renderer import (
    ViteReactRenderError,
    _compose_vite_user_prompt,
    _extract_export_const_json,
    _facts_local_keywords,
    _generate_cinematic_studio_files,
    _merge_copy_only_content,
    _sanitize_creative_plan,
    _validate_creative_plan_response,
    validate_vite_project_files,
)


def _facts(segment: str, seed: int = 1) -> dict:
    return {
        "business": {
            "name": f"Teste {segment}",
            "segment": segment,
            "city": "Curitiba",
            "address": "Rua Teste, 123 - Centro, Curitiba - PR",
            "phone": "(41) 99999-0000",
            "rating": "4.8",
            "reviews_count": "99",
            "services": ["Servico principal", "Atendimento", "Acompanhamento"],
        },
        "media": {
            "photos": [
                "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1400&auto=format&fit=crop",
            ],
        },
        "variation": {"seed": seed},
    }


def test_creative_plan_materializes_liquid_tokens():
    raw = {
        "creative_plan": {
            "visual_lane": "lane_c",
            "aesthetic_mode": "impact",
            "layout_mode": "asymmetric",
            "spacing_density": "compressed",
            "typography_scale": "heroic",
            "motion_intensity": "cinematic",
            "motion_mix": ["mask_reveal", "stagger_cards"],
            "section_order": [
                "hero",
                "about",
                "services",
                "gallery",
                "reviews",
                "faq",
                "location",
                "contact-cta",
            ],
            "hero_variant": "fullbleed",
            "services_variant": "stacked_cards",
            "reviews_variant": "score_wall",
            "surface_style": "solid",
            "prompt_priority": "visual_drama",
        }
    }
    clean = _sanitize_creative_plan(raw)
    merged = _merge_copy_only_content(_facts("academia"), {"creative_plan": clean})
    files = _generate_cinematic_studio_files(merged)
    validate_vite_project_files(files, merged)
    block_plan = _extract_export_const_json(
        files["src/components/siteData.ts"], "blockPlan"
    )

    assert block_plan["aesthetic_mode"] == "impact"
    assert block_plan["spacing_density"] == "compressed"
    assert block_plan["typography_scale"] == "heroic"
    assert block_plan["motion_intensity"] == "cinematic"
    assert block_plan["hero_variant"] == "fullbleed"
    assert block_plan["services_variant"] == "stacked_cards"
    assert block_plan["reviews_variant"] == "score_wall"
    assert block_plan["surface_style"] == "solid"
    assert "mask_reveal" in block_plan["motion_mix"]


def test_creative_plan_policy_rejects_incomplete_llm_direction():
    raw = {
        "creative_plan": {
            "hero_layout": "split",
            "layout_mode": "asymmetric",
            "aesthetic_mode": "impact",
        }
    }
    clean = _sanitize_creative_plan(raw)
    try:
        _validate_creative_plan_response({"creative_plan": clean})
    except ViteReactRenderError as exc:
        assert "creative_plan incompleto" in str(exc)
    else:
        raise AssertionError("creative_plan incompleto nao foi bloqueado")


def test_creative_plan_policy_rejects_weak_premium_floor():
    raw = {
        "creative_plan": {
            "visual_lane": "lane_a",
            "hero_layout": "center",
            "layout_mode": "organic",
            "aesthetic_mode": "minimal",
            "spacing_density": "spacious",
            "typography_scale": "soft",
            "motion_intensity": "minimal",
            "services_variant": "stacked_cards",
            "reviews_variant": "score_wall",
            "surface_style": "soft_tint",
            "motion_mix": ["subtle_fade", "stagger_cards"],
            "section_order": ["hero", "about", "services", "gallery", "reviews", "faq"],
        }
    }
    clean = _sanitize_creative_plan(raw)
    try:
        _validate_creative_plan_response({"creative_plan": clean})
    except ViteReactRenderError as exc:
        assert "piso premium" in str(exc) or "fraco bloqueado" in str(exc)
    else:
        raise AssertionError("creative_plan fraco nao foi bloqueado")


def test_all_core_segments_resolve_distinct_liquid_signatures_and_intent_keywords():
    segments = [
        "academia",
        "advogado",
        "barbearia",
        "clinica",
        "dentista",
        "energia_solar",
        "estetica",
        "imobiliaria",
        "nutricionista",
        "oficina",
        "pet_shop",
        "restaurante",
        "salao",
    ]
    seen = set()
    for seed, segment in enumerate(segments, 1):
        facts = _facts(segment, seed)
        files = _generate_cinematic_studio_files(facts)
        validate_vite_project_files(files, facts)
        block_plan = _extract_export_const_json(
            files["src/components/siteData.ts"], "blockPlan"
        )
        signature = (
            block_plan.get("visual_lane"),
            block_plan.get("hero_variant"),
            block_plan.get("about_variant"),
            block_plan.get("services_variant"),
            block_plan.get("reviews_variant"),
            block_plan.get("gallery_density"),
            block_plan.get("cta_style"),
            block_plan.get("surface_style"),
            block_plan.get("motion_intensity"),
        )
        assert signature not in seen, (
            f"duplicate visual signature for {segment}: {signature}"
        )
        seen.add(signature)

        keywords = _facts_local_keywords(facts)
        assert len(keywords) >= 10
        assert any(
            intent in keyword.lower()
            for keyword in keywords
            for intent in ("whatsapp", "perto de mim", "preco", "preço", "agendar")
        )


def test_root_design_contract_is_injected_into_vite_prompt():
    prompt = _compose_vite_user_prompt(
        "Builder prompt",
        facts={
            "business": {"name": "Teste", "segment": "academia", "city": "Curitiba"}
        },
    )
    assert "ROOT DESIGN CONTRACT" in prompt
    assert "FraLib Visual System" in prompt
    assert "Footer" in prompt
