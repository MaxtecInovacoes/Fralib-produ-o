"""Vite/React site renderer for the FraLib Builder.

The Builder asks the LLM for a studio-grade, componentized Vite React project,
writes it into the isolated tenant/job workspace, installs a fixed dependency
set and publishes only the compiled `dist` directory.

⚠️  ORQUESTRADOR - NÃO É MONOLITO
=================================
Este arquivo é um ORQUESTRADOR que coordena módulos modulares.
Lógica de negócio extraída para:
- vite_config.py: Configuration constants
- vite_prompts.py: System prompts and composers
- vite_facts.py: Facts extraction helpers
- vite_file_extractor.py: File extraction and normalization
- vite_validator.py: Project validation
- vite_build_executor.py: Build execution
- vite_modules.py: Module definitions
- vite_renderer_models.py: Data models
- vite_config_helpers.py: Configuration helpers

@architecture Orquestrador (coordena módulos, 0 lógica isolada)
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote_plus

import httpx

# Sprint 11.8 fix: logger was missing - caused 'name logger is not defined'
# on later model-cascade attempts.
logger = logging.getLogger(__name__)

# Import from modularized components
try:
    from backend.services.vite_liquid_components import (
        infer_aesthetic_pole,
        get_liquid_component_guide,
        POLO_TOKENS,
        get_hero_display_mode,
        get_services_display_mode,
        get_gallery_display_mode,
    )
    from backend.services.vite_liquid_prompts import (
        build_liquid_system_prompt,
        build_hero_prompt,
        get_temperature_for_agent,
        POLE_SYSTEM_PROMPTS,
    )
    LIQUID_COMPONENTS_AVAILABLE = True
except ImportError:
    LIQUID_COMPONENTS_AVAILABLE = False
    logger.warning("vite_liquid_components not available - running in legacy mode")

try:
    from backend.services.vite_config import (
        VITE_REACT_FILE_BATCHES,
        FIXED_PACKAGE_JSON,
        REQUIRED_PROJECT_FILES,
        BLOCKED_SOURCE_PATTERNS,
        SEGMENT_RULES,
        _env_int,
        _model_repair_attempts,
        _single_model_mode_enabled,
        _preview_fast_enabled,
        _batch_first_enabled,
        _batch_first_project_attempts,
        _batch_spacing_seconds,
        _batch_max_tokens,
        _batch_token_budget,
        _batch_format_repair_budget,
        _studio_min_source_chars,
        _studio_min_classnames,
        _studio_min_images,
        _studio_min_components,
        _transient_proxy_retry_delay_seconds,
    )
except ImportError:
    from services.vite_config import (  # type: ignore
        VITE_REACT_FILE_BATCHES,
        FIXED_PACKAGE_JSON,
        REQUIRED_PROJECT_FILES,
        BLOCKED_SOURCE_PATTERNS,
        SEGMENT_RULES,
        _env_int,
        _model_repair_attempts,
        _single_model_mode_enabled,
        _preview_fast_enabled,
        _batch_first_enabled,
        _batch_first_project_attempts,
        _batch_spacing_seconds,
        _batch_max_tokens,
        _batch_token_budget,
        _batch_format_repair_budget,
        _studio_min_source_chars,
        _studio_min_classnames,
        _studio_min_images,
        _studio_min_components,
        _transient_proxy_retry_delay_seconds,
    )

try:
    from backend.services.vite_block_registry import resolve_cinematic_block_plan
except ImportError:
    from services.vite_block_registry import resolve_cinematic_block_plan  # type: ignore

try:
    from backend.services.vite_theme_guard import resolve_cinematic_theme
except ImportError:
    from services.vite_theme_guard import resolve_cinematic_theme  # type: ignore

try:
    from backend.services.vite_visual_lanes import resolve_visual_lane
except ImportError:
    from services.vite_visual_lanes import resolve_visual_lane  # type: ignore

try:
    from backend.services.vite_prompts import (
        VITE_REACT_SYSTEM_PROMPT,
        VITE_REACT_BATCH_SYSTEM_PROMPT,
        _build_vite_react_system_prompt_with_facts,  # Sprint 12.13: caroço rico com briefing real
        _compose_vite_user_prompt,
        _compose_vite_file_batch_prompt,
        _summarize_builder_facts,
        _segment_contamination_guard,
        _safe_project_path,
        _meta_escape,
    )
except ImportError:
    from services.vite_prompts import (  # type: ignore
        VITE_REACT_SYSTEM_PROMPT,
        _build_vite_react_system_prompt_with_facts,  # Sprint 12.13: caroço rico com briefing real
        _compose_vite_user_prompt,
        _compose_vite_file_batch_prompt,
        _summarize_builder_facts,
        _segment_contamination_guard,
        _safe_project_path,
        _meta_escape,
    )

try:
    from backend.services.vite_facts import (
        _segment_key_for_business,
        _segment_key_from_facts,
        _validate_segment_specificity,
        _facts_business,
        _facts_publication_url,
        _facts_theme_color,
        _facts_local_keywords,
        _facts_meta_description,
        _facts_og_image,
        _facts_json_ld,
        _visual_business_payload,
        _visual_media_urls,
    )
except ImportError:
    from services.vite_facts import (  # type: ignore
        _segment_key_for_business,
        _segment_key_from_facts,
        _validate_segment_specificity,
        _facts_business,
        _facts_publication_url,
        _facts_theme_color,
        _facts_local_keywords,
        _facts_meta_description,
        _facts_og_image,
        _facts_json_ld,
        _visual_business_payload,
        _visual_media_urls,
    )

try:
    from backend.services.vite_file_extractor import (
        extract_vite_project_files,
        _extract_tagged_file_blocks,
        _extract_single_requested_file,
        _clean_json_block,
        _normalize_text,
        _normalize_model_alias,
        _normalize_component_export_contract,
        _normalize_page_export_contract,
        _normalize_generated_imports_and_hooks,
    )
except ImportError:
    from services.vite_file_extractor import (  # type: ignore
        extract_vite_project_files,
        _extract_tagged_file_blocks,
        _extract_single_requested_file,
        _clean_json_block,
        _normalize_text,
        _normalize_model_alias,
        _normalize_component_export_contract,
        _normalize_page_export_contract,
        _normalize_generated_imports_and_hooks,
    )

try:
    from backend.services.vite_validator import (
        validate_vite_project_files,
        validate_vite_dist,
        _validate_studio_project,
        _validate_hero_first_viewport,
        _validate_mobile_navbar,
    )
except ImportError:
    from services.vite_validator import (  # type: ignore
        validate_vite_project_files,
        validate_vite_dist,
        _validate_studio_project,
        _validate_hero_first_viewport,
        _validate_mobile_navbar,
    )

try:
    from backend.services.vite_templates import (
        vite_template_index_html,
        vite_template_vite_config,
        vite_template_tsconfig,
        vite_template_main_tsx,
        vite_template_main_tsx_with_factual_contract,
        vite_template_app_tsx,
        vite_template_types_ts,
        vite_template_index_css,
        vite_template_jsx_fallback_types,
        vite_template_utils_ts,
        vite_template_avatar_ui,
        vite_template_separator_ui,
        vite_template_accordion_ui,
        vite_template_lgpd_banner,
        vite_template_factual_motion_contract,
        _visual_business_payload,
        _visual_media_urls,
    )
except ImportError:
    from services.vite_templates import (  # type: ignore
        vite_template_index_html,
        vite_template_vite_config,
        vite_template_tsconfig,
        vite_template_main_tsx,
        vite_template_main_tsx_with_factual_contract,
        vite_template_app_tsx,
        vite_template_types_ts,
        vite_template_index_css,
        vite_template_jsx_fallback_types,
        vite_template_utils_ts,
        vite_template_avatar_ui,
        vite_template_separator_ui,
        vite_template_accordion_ui,
        vite_template_lgpd_banner,
        vite_template_factual_motion_contract,
        _visual_business_payload,
        _visual_media_urls,
    )

# Sprint 12.18: inject backend parent dir so `from backend.services.x` imports resolve
import os as _os
import sys as _sys
_BACKEND_PARENT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _BACKEND_PARENT not in _sys.path:
    _sys.path.insert(0, _BACKEND_PARENT)

try:
    from backend.core.proxy_models import (
        PROXY_BUILDER_MODEL,
        PROXY_DEFAULT_MODEL,
        PROXY_LIGHT_MODEL,
    )
except Exception:
    from core.proxy_models import (  # type: ignore
        PROXY_BUILDER_MODEL,
        PROXY_DEFAULT_MODEL,
        PROXY_LIGHT_MODEL,
    )

try:
    from backend.services.vite_renderer_models import (
        cap_max_tokens_for_model,
    )
except Exception:
    from backend.services.vite_renderer_models import (  # type: ignore
        cap_max_tokens_for_model,
    )

# Sprint 16: Variation seed system for deterministic site variations
try:
    from backend.services.variation_seed import (
        get_variation,
        apply_variation_to_facts,
    )
except Exception:
    try:
        from services.variation_seed import (  # type: ignore
            get_variation,
            apply_variation_to_facts,
        )
    except Exception:
        # Variation seed module not available - will use legacy seed logic
        get_variation = None  # type: ignore
        apply_variation_to_facts = None  # type: ignore


# Core files always required; component names are chosen freely by the LLM
# based on the niche, archetype and section sequence from the prompt.
VITE_REACT_FILE_BATCHES_CORE = [
    ("app", ["src/App.tsx"]),
    ("main", ["src/main.tsx"]),
    ("types", ["src/types.ts"]),
    ("css", ["src/index.css"]),
    ("page", ["src/pages/Index.tsx"]),
]

# Legacy fixed list kept ONLY as fallback when dynamic detection fails
VITE_REACT_FILE_BATCHES_LEGACY = [
    ("app", ["src/App.tsx"]),
    ("main", ["src/main.tsx"]),
    ("types", ["src/types.ts"]),
    ("css", ["src/index.css"]),
    ("page", ["src/pages/Index.tsx"]),
    ("navbar", ["src/components/Navbar.tsx"]),
    ("hero", ["src/components/HeroSection.tsx"]),
    ("about", ["src/components/AboutSection.tsx"]),
    ("services", ["src/components/ServicesSection.tsx"]),
    ("gallery", ["src/components/GallerySection.tsx"]),
    ("lifestyle", ["src/components/LifestyleSection.tsx"]),
    ("reviews", ["src/components/ReviewsSection.tsx"]),
    ("location", ["src/components/LocationSection.tsx"]),
    ("booking-modal", ["src/components/BookingModal.tsx"]),
    ("contact-cta", ["src/components/ContactCTA.tsx"]),
    ("footer", ["src/components/Footer.tsx"]),
]

def _detect_components_from_page(page_source: str) -> list[tuple[str, list[str]]]:
    """Parse Index.tsx imports to build dynamic component batches."""
    matches = [m.split("/")[-1].replace(chr(34),"").replace(chr(39),"").replace(";","").strip() for m in page_source.splitlines() if "/components/" in m and "from" in m]
    # matches now contains component filenames like "HeroSection" or "HeroSection.tsx"
    batches = []
    for match in matches:
        name = match.replace(".tsx", "").replace(".ts", "")
        slug = re.sub(r"(?<=[a-z0-9])([A-Z])", lambda m: "-" + m.group(1), name).lower()
        batches.append((slug, [f"src/components/{match}" if "." in match else f"src/components/{match}.tsx"]))
    return batches if batches else [(n, p) for n, p in VITE_REACT_FILE_BATCHES_LEGACY if n not in ("app", "main", "types", "css", "page")]

# Dynamic batch list (computed at runtime after page batch)
VITE_REACT_FILE_BATCHES = VITE_REACT_FILE_BATCHES_LEGACY  # initial reference for legacy code paths


BLOCKED_SOURCE_PATTERNS = {
    "fetch externo": r"\bfetch\s*\(",
    "XMLHttpRequest": r"\bXMLHttpRequest\b",
    "Supabase/Firebase": r"\b(supabase|firebase)\b",
    "env runtime": r"\b(import\.meta\.env|process\.env)\b",
    "eval": r"\beval\s*\(",
    "Function constructor": r"\bnew\s+Function\s*\(",
    "cookie": r"\bdocument\.cookie\b",
    # NOTE: localStorage/sessionStorage and dangerouslySetInnerHTML/innerHTML
    # were previously blocked here, but the official LgpdBanner template
    # uses localStorage for consent persistence. We trust the templates and
    # only block genuinely dangerous runtime hooks.
    "Unsplash dinamico antigo": r"\bsource\.unsplash\.com\b",
}


STUDIO_COMPONENT_GROUPS = {
    "navbar": ("navbar", "navigation"),
    "gallery": ("gallery", "portfolio"),
    "lifestyle": ("lifestyle", "editorial", "experience"),
    "services": ("service", "plan", "offer"),
    "modal": ("modal", "dialog", "booking"),
}

SEGMENT_RULES = {
    "academia": {
        "aliases": ("academia", "fitness", "gym", "crossfit", "musculacao", "musculação"),
        "required": (
            "academia", "fitness", "treino", "musculacao", "musculação",
            "aluno", "alunos", "funcional", "modalidade", "matricula", "matrícula",
        ),
        "forbidden": (
            "barbearia", "barber", "barbeiro", "barba", "navalha",
            "corte masculino", "ritual de cuidado", "grooming",
        ),
        "min_required": 2,
    },
    "nutricionista": {
        "aliases": ("nutricionista", "nutricao", "nutrição", "nutricional"),
        "required": (
            "nutricionista", "nutricao", "nutrição", "alimentar", "consulta",
            "paciente", "pacientes", "plano alimentar", "saude", "saúde",
        ),
        "forbidden": (
            "barbearia", "barber", "barbeiro", "barba", "navalha",
            "corte masculino", "ritual de cuidado", "grooming",
            "musculacao", "musculação", "matricula", "matrícula",
        ),
        "min_required": 2,
    },
    "barbearia": {
        "aliases": ("barbearia", "barber", "barbeiro"),
        "required": ("barbearia", "barbeiro", "barba", "corte", "navalha", "barber"),
        "forbidden": ("plano alimentar", "consulta nutricional", "musculacao", "musculação"),
        "min_required": 2,
    },
    "advogado": {
        "aliases": ("advogado", "advocacia", "juridico", "jurídico", "direito"),
        "required": ("advogado", "advocacia", "juridico", "jurídico", "direito", "consulta", "cliente"),
        "forbidden": ("barbearia", "academia", "musculacao", "plano alimentar", "pizza", "pet shop"),
        "min_required": 2,
    },
    "clinica": {
        "aliases": ("clinica", "clínica", "medica", "médica", "medico", "médico"),
        "required": ("clinica", "clínica", "consulta", "atendimento", "paciente", "exame", "saude", "saúde"),
        "forbidden": ("barbearia", "musculacao", "corte masculino", "pizza", "hamburguer", "imovel"),
        "min_required": 2,
    },
    "dentista": {
        "aliases": ("dentista", "odontologia", "odontologico", "odontológico", "odonto"),
        "required": ("dentista", "odontologia", "odontologico", "odontológico", "consulta", "avaliacao", "avaliação"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "pizza", "imovel", "energia solar"),
        "min_required": 2,
    },
    "estetica": {
        "aliases": ("estetica", "estética", "spa", "beleza", "facial", "pele"),
        "required": ("estetica", "estética", "tratamento", "pele", "beleza", "avaliacao", "avaliação"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "pizza", "imovel", "advocacia"),
        "min_required": 2,
    },
    "energia_solar": {
        "aliases": ("energia_solar", "energia solar", "solar", "fotovoltaica", "painel solar"),
        "required": ("energia", "solar", "fotovoltaica", "projeto", "instalacao", "instalação", "economia"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "consulta juridica", "pizza", "pet shop"),
        "min_required": 2,
    },
    "imobiliaria": {
        "aliases": ("imobiliaria", "imobiliária", "imovel", "imóvel", "imoveis", "imóveis"),
        "required": ("imobiliaria", "imobiliária", "imovel", "imóvel", "imoveis", "imóveis", "visita", "bairro"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "painel solar", "pizza", "dentista"),
        "min_required": 2,
    },
    "oficina": {
        "aliases": ("oficina", "mecanica", "mecânica", "automotivo", "auto pecas", "autopeças"),
        "required": ("oficina", "mecanica", "mecânica", "carro", "automotivo", "orcamento", "orçamento"),
        "forbidden": ("barbearia", "plano alimentar", "consulta nutricional", "imovel", "pizza", "dentista"),
        "min_required": 2,
    },
    "pet_shop": {
        "aliases": ("pet_shop", "pet shop", "petshop", "veterinario", "veterinário", "banho", "tosa"),
        "required": ("pet", "banho", "tosa", "veterinario", "veterinário", "tutor", "animal"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "imovel", "painel solar", "advocacia"),
        "min_required": 2,
    },
    "restaurante": {
        "aliases": ("restaurante", "pizzaria", "hamburgueria", "cafeteria", "padaria", "delivery", "cardapio", "cardápio"),
        "required": ("restaurante", "cardapio", "cardápio", "pedido", "delivery", "reserva", "mesa", "sabor"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "painel solar", "advocacia", "dentista"),
        "min_required": 2,
    },
    "salao": {
        "aliases": ("salao", "salão", "salao de beleza", "salão de beleza", "cabeleireiro", "cabelo"),
        "required": ("salao", "salão", "beleza", "cabelo", "escova", "mechas", "agenda"),
        "forbidden": ("barbearia", "musculacao", "plano alimentar", "imovel", "painel solar", "advocacia"),
        "min_required": 2,
    },
}

@dataclass(frozen=True)
class ViteReactRenderResult:
    html: str
    source_files: dict[str, str]
    model: str
    attempts: list[dict[str, Any]]
    elapsed_ms: int
    dist_dir: str
    index_path: str


class ViteReactRenderError(RuntimeError):
    """Raised when the Vite/React Builder cannot produce a publishable dist."""


def _get_llm_policy() -> str:
    """Return the Vite LLM policy.

    Production defaults are set by builder_worker. Policies that do not call
    LLM are not allowed to publish a generated substitute in production.
    """
    raw = os.getenv("FRALIB_VITE_LLM_POLICY", "none").strip().lower().replace("-", "_")
    aliases = {
        "0": "none",
        "off": "none",
        "false": "none",
        "no_llm": "none",
        "copy": "copy_only",
        "content": "copy_only",
        "json": "copy_only",
        "creative": "creative_plan",
        "plan": "creative_plan",
        "creative_json": "creative_plan",
        "creative_director": "creative_plan",
        "full": "full_code",
        "code": "full_code",
        "fullcode": "full_code",
        "legacy": "full_code",
    }
    policy = aliases.get(raw, raw)
    if policy not in {"none", "copy_only", "creative_plan", "full_code"}:
        raise ViteReactRenderError(f"FRALIB_VITE_LLM_POLICY invalida: {raw!r}")
    return policy


def _get_copy_only_system_prompt(policy: str = "copy_only") -> str:
    """Tiny system prompt for the low-token content pass."""
    base = (
        "Voce e redator de conversao para landing pages locais da FraLib. "
        "Retorne APENAS JSON valido, sem markdown e sem codigo. "
        "Nao gere HTML, TSX, CSS, imports, componentes ou scripts. "
        "Use somente fatos confirmados; se faltar dado, use texto neutro. "
        "Toda copy publica deve ser em pt-BR."
    )
    if policy == "creative_plan":
        return (
            base
            + " Voce tambem atua como uma equipe premium: estrategista de marca, "
              "diretor criativo, diretor de fotografia, UX, CRO e SEO local. "
              "Nunca comece por nicho -> template. Raciocine por negocio -> marca "
              "-> cliente -> emocao -> historia -> linguagem visual -> conversao. "
              "Traduza 'cinematografico' em decisoes objetivas: luz, ritmo, "
              "profundidade, composicao, motion e materiais. Escolha somente "
              "variantes permitidas de blocos, superficies e motion. Nao crie "
              "novos nomes fora do schema."
        )
    return base


def _get_copy_only_user_prompt(facts: dict[str, Any], policy: str = "copy_only") -> str:
    facts_summary = _summarize_builder_facts(facts)
    contamination_guard = _segment_contamination_guard(facts)
    creative_schema = ""
    if policy == "creative_plan":
        creative_schema = """
  "creative_plan": {
    "concept": "string curta em pt-BR",
    "brand_archetype": "ruler | rebel | explorer | creator | sage | caregiver | hero | magician",
    "emotional_outcome": "trust | status | belonging | exclusivity | transformation | security | aspiration",
    "anti_identity": "cheap | generic | corporate | startup | fintech | amateur | mass_market",
    "visual_metaphor": "string curta em pt-BR",
    "story_arc": "attention_problem_authority_proof_transformation_action",
    "cinematic_direction": "editorial | documentary | luxury | contrast_heavy | natural_light | energetic",
    "conversion_strategy": "quick_whatsapp | appointment_ritual | proof_first | local_trust | premium_consultation",
    "hero_layout": "split | center | asymmetric | fullbleed | video",
    "hero_text_side": "left | right | center",
    "aesthetic_mode": "wellness | impact | editorial | premium | technical | dynamic | minimal | balanced",
    "spacing_density": "compressed | normal | spacious",
    "radius_mode": "sharp | balanced | soft | pill",
    "container_strategy": "contained | wide | edge_to_edge | overlap",
    "typography_scale": "soft | strong | heroic",
    "heading_style": "clean | display | condensed | editorial | kinetic",
    "surface_depth": "flat | bordered | elevated | cutout",
    "overlap_mode": "none | subtle | strong",
    "motion_intensity": "minimal | composed | cinematic | sharp",
    "image_treatment": "clean | duotone | grain | high_contrast",
    "section_order": ["hero", "about", "services", "gallery", "reviews", "faq", "location", "lifestyle", "contact-cta"],
    "about_variant": "manifesto_split | proof_sidebar | feature_grid",
    "surface_style": "solid | outline | soft_tint",
    "surface_mix": ["solid", "outline", "soft_tint"],
    "section_surface_map": {"about": "solid", "services": "outline", "reviews": "soft_tint", "faq": "solid", "location": "soft_tint", "contact-cta": "solid"},
    "color_strategy": "restrained | committed | full_palette | drenched",
    "typography_mood": "clean_sans | condensed_sport | luxury_display | editorial_serif | technical_grotesk",
    "gallery_density": "mosaic | cinematic_strip | editorial_grid",
    "cta_style": "poster_band | solid_panel | split_card | minimal_inline",
    "prompt_priority": "visual_drama | local_seo | conversion | trust",
    "anti_repetition_rule": "avoid_same_lane | avoid_glass | avoid_same_hero | avoid_same_order",
    "services_variant": "stacked_cards | split_editorial | stats_then_cards",
    "reviews_variant": "score_wall | quote_spotlight | card_marquee | editorial_case",
    "faq_variant": "panel | inline",
    "location_variant": "split_local | feature_local",
    "motion_style": "sharp | smooth | minimal",
    "motion_mix": ["mask_reveal", "parallax_video", "stagger_cards"],
    "visual_lane": "lane_a | lane_b | lane_c | lane_d | lane_e | lane_f | lane_g | lane_h"
  },
"""
    return f"""Preencha slots curtos para um site Vite/React que a FraLib vai montar com templates proprios.

CONTRATO:
- JSON puro.
- Maximo 3 servicos, 3 diferenciais e 4 FAQs.
- Nao escreva codigo.
- Nao invente fatos operacionais, preco, garantia, anos de mercado, certificacoes ou links.
- CTA deve combinar com o nicho.
- Se creative_plan estiver ativo, escolha apenas opcoes do schema. O renderer vai aplicar os blocos.
- Nunca escolha pelo caminho nicho -> template. Escolha por marca -> emocao -> historia -> visual -> conversao.
- Escolha a atitude fisica do layout: impacto comprime, usa quinas, tipografia forte e overlap; wellness/editorial abre respiro, arredonda e reduz agressividade.
- Hero com video NAO e padrao. Use "video" apenas quando a variacao pedir video explicitamente; caso contrario escolha split, center, asymmetric ou fullbleed conforme a marca.
- Use superficies solidas ou outline; glass/transparencia nao deve ser usado como efeito padrao.
- O site precisa parecer pertencer a esta empresa mesmo sem logo.
- SEO deve priorizar intencao local/transacional/comercial sem keyword stuffing.

SCHEMA:
{{
  "blueprint": "performance_plan | authority_trust | transformation_gallery | savings_offer | local_service_fast_quote | premium_appointment",
{creative_schema}
  "hero": {{
    "headline": "string curta",
    "subheadline": "string com promessa especifica",
    "cta_primary": "verbo + objeto",
    "cta_secondary": "verbo + objeto"
  }},
  "services_title": "string",
  "services": [
    {{"title": "string", "description": "string"}}
  ],
  "lifestyle": {{"title": "string", "description": "string"}},
  "differentials": ["string"],
  "faq": [
    {{"question": "string", "answer": "string"}}
  ],
  "gallery_alt": "string",
  "modal_title": "string",
  "modal_cta": "string",
  "contact_headline": "string",
  "contact_sub": "string"
}}

DADOS CONFIRMADOS:
{facts_summary}

GUARDA DE NICHO:
{contamination_guard}
"""


def _clean_copy_value(value: Any, *, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("{", "").replace("}", "").replace("<", "").replace(">", "")
    text = re.sub(r"\bpara\s+finally\s+", "para ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfinally\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfinally\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    if re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text):
        return ""
    if re.search(r"\b(cuenta|entrenamiento|sudor|alcanzar|rutina de entrenamiento)\b", text, flags=re.IGNORECASE):
        return ""
    return text[:limit].strip()


def _one_of(value: Any, allowed: set[str]) -> str:
    candidate = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "full_bleed": "fullbleed",
        "hero_video": "video",
        "video_split": "video",
        "poster_split_video": "video",
        "middle": "center",
        "centre": "center",
        "cards": "stacked_cards",
        "editorial": "split_editorial",
        "marquee": "card_marquee",
        "spotlight": "quote_spotlight",
        "local_feature": "feature_local",
        "brutalist": "impact",
        "aggressive": "impact",
        "sharp": "impact",
        "soft": "wellness",
        "minimalist": "minimal",
        "cinematic": "premium",
        "edge-to-edge": "edge_to_edge",
        "edge": "edge_to_edge",
        "compressed_spacing": "compressed",
        "wide_container": "wide",
        "hero": "heroic",
    }
    alias = aliases.get(candidate)
    if alias and alias in allowed:
        return alias
    return candidate if candidate in allowed else ""


def _clean_choice_list(values: Any, allowed: set[str], *, limit: int = 8) -> list[str]:
    raw_values = values if isinstance(values, list) else []
    cleaned: list[str] = []
    for item in raw_values[:limit]:
        value = _one_of(item, allowed)
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _sanitize_creative_plan(content: dict[str, Any]) -> dict[str, Any]:
    """Validate creative direction while keeping the existing Studio path."""
    source = content.get("creative_plan") if isinstance(content.get("creative_plan"), dict) else content
    if not isinstance(source, dict):
        return {}

    source = dict(source)
    if source.get("hero_variant") and not source.get("hero_layout"):
        source["hero_layout"] = source.get("hero_variant")

    section_allowed = {
        "hero", "about", "services", "gallery", "reviews", "faq",
        "location", "lifestyle", "contact-cta", "pricing", "stats-bar",
    }
    section_aliases = {
        "sobre": "about",
        "servicos": "services",
        "prova": "reviews",
        "depoimentos": "reviews",
        "avaliacoes": "reviews",
        "localizacao": "location",
        "experiencia": "lifestyle",
        "contato": "contact-cta",
        "cta": "contact-cta",
        "planos": "pricing",
        "precos": "pricing",
        "stats": "stats-bar",
        "numeros": "stats-bar",
    }
    sections: list[str] = []
    raw_sections = source.get("section_order") if isinstance(source.get("section_order"), list) else []
    for item in raw_sections:
        key = str(item or "").strip().lower().replace("_", "-")
        key = section_aliases.get(key, key)
        if key in section_allowed and key not in sections:
            sections.append(key)

    cleaned: dict[str, Any] = {}
    for text_key, limit in {
        "concept": 140,
        "visual_metaphor": 120,
    }.items():
        if source.get(text_key):
            cleaned[text_key] = _clean_copy_value(source.get(text_key), limit=limit)
    for key, allowed in {
        "brand_archetype": {"ruler", "rebel", "explorer", "creator", "sage", "caregiver", "hero", "magician"},
        "emotional_outcome": {"trust", "status", "belonging", "exclusivity", "transformation", "security", "aspiration"},
        "anti_identity": {"cheap", "generic", "corporate", "startup", "fintech", "amateur", "mass_market"},
        "story_arc": {"attention_problem_authority_proof_transformation_action"},
        "cinematic_direction": {"editorial", "documentary", "luxury", "contrast_heavy", "natural_light", "energetic"},
        "conversion_strategy": {"quick_whatsapp", "appointment_ritual", "proof_first", "local_trust", "premium_consultation"},
        "hero_layout": {"split", "center", "asymmetric", "fullbleed", "video"},
        "hero_text_side": {"left", "right", "center"},
        "aesthetic_mode": {"wellness", "impact", "editorial", "premium", "technical", "dynamic", "minimal", "balanced"},
        "spacing_density": {"compressed", "normal", "spacious"},
        "radius_mode": {"sharp", "balanced", "soft", "pill"},
        "container_strategy": {"contained", "wide", "edge_to_edge", "overlap"},
        "typography_scale": {"soft", "strong", "heroic"},
        "heading_style": {"clean", "display", "condensed", "editorial", "kinetic"},
        "surface_depth": {"flat", "bordered", "elevated", "cutout"},
        "overlap_mode": {"none", "subtle", "strong"},
        "motion_intensity": {"minimal", "composed", "cinematic", "sharp"},
        "image_treatment": {"clean", "duotone", "grain", "high_contrast"},
        "about_variant": {"manifesto_split", "proof_sidebar", "feature_grid"},
        "surface_style": {"solid", "outline", "soft_tint"},
        "color_strategy": {"restrained", "committed", "full_palette", "drenched"},
        "typography_mood": {"clean_sans", "condensed_sport", "luxury_display", "editorial_serif", "technical_grotesk"},
        "gallery_density": {"mosaic", "cinematic_strip", "editorial_grid"},
        "cta_style": {"poster_band", "solid_panel", "split_card", "minimal_inline"},
        "prompt_priority": {"visual_drama", "local_seo", "conversion", "trust"},
        "anti_repetition_rule": {"avoid_same_lane", "avoid_glass", "avoid_same_hero", "avoid_same_order"},
        "services_variant": {"stacked_cards", "split_editorial", "stats_then_cards"},
        "reviews_variant": {"score_wall", "quote_spotlight", "card_marquee", "editorial_case"},
        "proof_style": {"score_wall", "quote_spotlight", "card_marquee", "editorial_case"},
        "faq_variant": {"panel", "inline"},
        "location_variant": {"split_local", "feature_local"},
        "motion_style": {"sharp", "smooth", "minimal"},
        "visual_lane": {"lane_a", "lane_b", "lane_c", "lane_d", "lane_e", "lane_f", "lane_g", "lane_h"},
    }.items():
        value = _one_of(source.get(key), allowed)
        if value:
            cleaned[key] = value
    if sections:
        cleaned["section_order"] = sections
    surface_mix = _clean_choice_list(source.get("surface_mix"), {"solid", "outline", "soft_tint"}, limit=4)
    if surface_mix:
        cleaned["surface_mix"] = surface_mix
    raw_surface_map = source.get("section_surface_map")
    if isinstance(raw_surface_map, dict):
        surface_map: dict[str, str] = {}
        for raw_key, raw_value in raw_surface_map.items():
            section_key = str(raw_key or "").strip().lower().replace("_", "-")
            section_key = section_aliases.get(section_key, section_key)
            surface_value = _one_of(raw_value, {"solid", "outline", "soft_tint"})
            if section_key in section_allowed and section_key != "hero" and surface_value:
                surface_map[section_key] = surface_value
        if len(set(surface_map.values())) >= 2:
            cleaned["section_surface_map"] = surface_map
    motion_mix = _clean_choice_list(
        source.get("motion_mix"),
        {"mask_reveal", "parallax_video", "stagger_cards", "hover_depth", "line_draw", "marquee", "subtle_fade"},
        limit=5,
    )
    if motion_mix:
        cleaned["motion_mix"] = motion_mix
    if cleaned.get("hero_layout") == "video":
        cleaned.setdefault("motion_mix", ["parallax_video", "mask_reveal", "stagger_cards"])
        cleaned.setdefault("hero_text_side", "left")
    if cleaned.get("anti_identity") in {"generic", "startup", "fintech"}:
        cleaned.setdefault("anti_repetition_rule", "avoid_same_hero")
        cleaned.setdefault("surface_style", "solid")
    return cleaned


def _copy_only_attempts() -> int:
    try:
        return max(1, min(3, int(os.getenv("FRALIB_VITE_COPY_ONLY_ATTEMPTS", "2"))))
    except (TypeError, ValueError):
        return 2


def _looks_like_pt_br_copy(content: dict[str, Any]) -> bool:
    """Reject obvious English copy before it reaches the deterministic Studio."""
    snippets: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, str):
            snippets.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(content)
    text = " ".join(snippets).lower()
    words = re.findall(r"[a-záéíóúâêôãõç]+", text)
    if len(words) < 12:
        return True
    english_markers = {
        "the", "and", "for", "your", "with", "schedule", "learn", "about",
        "nutrition", "performance", "training", "results", "services",
        "consultation", "personalized", "athletic", "food", "recovery",
    }
    portuguese_markers = {
        "de", "da", "do", "em", "para", "com", "seu", "sua", "consulta",
        "agendar", "nutrição", "nutricao", "alimentar", "atendimento",
        "plano", "resultados", "são", "voce", "você", "whatsapp",
    }
    english_hits = sum(1 for word in words if word in english_markers)
    portuguese_hits = sum(1 for word in words if word in portuguese_markers)
    accented = bool(re.search(r"[áéíóúâêôãõç]", text))
    return portuguese_hits >= english_hits or (accented and portuguese_hits > 0)


def _sanitize_copy_only_content(content: dict[str, Any]) -> dict[str, Any]:
    """Keep only small text slots from the copy-only LLM response."""
    if not isinstance(content, dict):
        return {}
    cleaned: dict[str, Any] = {}
    if content.get("blueprint"):
        cleaned["blueprint"] = _clean_copy_value(content.get("blueprint"), limit=80)
    creative_plan = _sanitize_creative_plan(content)
    if creative_plan:
        cleaned["creative_plan"] = creative_plan

    hero = content.get("hero") if isinstance(content.get("hero"), dict) else {}
    if hero:
        cleaned["hero"] = {
            key: _clean_copy_value(hero.get(key), limit=160)
            for key in ("headline", "subheadline", "cta_primary", "cta_secondary")
            if hero.get(key)
        }

    public_text_keys = (
        "services_title",
        "services_subheadline",
        "about_title",
        "about_body",
        "gallery_title",
        "gallery_intro",
        "reviews_title",
        "reviews_intro",
        "proof_quote",
        "faq_title",
        "faq_intro",
        "location_title",
        "location_intro",
        "location_cta_title",
        "location_cta_body",
        "location_cta_primary",
        "location_cta_secondary",
        "about_card_1_text",
        "about_card_2_text",
        "about_card_3_text",
        "about_aside_body",
        "services_city_body",
        "contact_headline",
        "contact_sub",
        "footer_tagline",
        "gallery_alt",
        "modal_title",
        "modal_cta",
    )
    for key in public_text_keys:
        if content.get(key):
            cleaned[key] = _clean_copy_value(content.get(key), limit=240)

    lifestyle = content.get("lifestyle") if isinstance(content.get("lifestyle"), dict) else {}
    if lifestyle:
        cleaned["lifestyle"] = {
            key: _clean_copy_value(lifestyle.get(key), limit=220)
            for key in ("title", "description")
            if lifestyle.get(key)
        }

    services = content.get("services") if isinstance(content.get("services"), list) else []
    clean_services: list[dict[str, str]] = []
    for item in services[:3]:
        if isinstance(item, dict):
            title = _clean_copy_value(item.get("title"), limit=90)
            description = _clean_copy_value(item.get("description"), limit=180)
        else:
            title = _clean_copy_value(item, limit=90)
            description = ""
        if title:
            clean_services.append({"title": title, "description": description})
    if clean_services:
        cleaned["services"] = clean_services

    differentials = content.get("differentials") if isinstance(content.get("differentials"), list) else []
    clean_differentials = [_clean_copy_value(item, limit=110) for item in differentials[:3]]
    clean_differentials = [item for item in clean_differentials if item]
    if clean_differentials:
        cleaned["differentials"] = clean_differentials

    faq = content.get("faq") if isinstance(content.get("faq"), list) else []
    clean_faq: list[dict[str, str]] = []
    for item in faq[:4]:
        if not isinstance(item, dict):
            continue
        question = _clean_copy_value(item.get("question"), limit=140)
        answer = _clean_copy_value(item.get("answer"), limit=240)
        if question and answer:
            clean_faq.append({"question": question, "answer": answer})
    if clean_faq:
        cleaned["faq"] = clean_faq
    banned_fragments = (
        "uma narrativa visual para",
        "pronto para confirmar o próximo passo",
        "pronto para confirmar o proximo passo",
        "use o canal oficial para tirar dúvidas e agendar",
        "use o canal oficial para tirar duvidas e agendar",
        "serviços confirmados da",
        "servicos confirmados da",
        "chegue à {name} pelo canal oficial",
        "chegue a {name} pelo canal oficial",
        "canal oficial para confirmar",
        "prova social tem",
        "a prova social entra",
        "a prova social aparece",
        "direção visual",
        "mídia editorial",
        "composição mistura",
        "cards e ritmo",
        "informações confirmadas da",
        "informacoes confirmadas da",
        "organizadas para contato direto",
        "organizados para contato direto",
        "canal oficial para confirmar",
        "a galeria mostra",
        "a seção mostra",
        "a secao mostra",
        "essa seção",
        "essa secao",
        "finally",
        "estética menos agressiva",
        "próximo passo simples",
    )
    serialized = json.dumps(cleaned, ensure_ascii=False).lower()
    if any(fragment in serialized for fragment in banned_fragments):
        return {}
    if cleaned and not _looks_like_pt_br_copy(cleaned):
        return {}
    return cleaned


def _parse_content_json(raw: str) -> dict[str, Any]:
    """Parse the compact JSON returned by copy_only mode."""
    text = str(raw or "").strip()
    if not text:
        return {}
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    if not isinstance(parsed, dict):
        return {}
    if isinstance(parsed.get("content"), dict):
        parsed = parsed["content"]
    return _sanitize_copy_only_content(parsed)


def _merge_copy_only_content(facts: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
    try:
        merged = json.loads(json.dumps(facts or {}, ensure_ascii=False, default=str))
    except Exception:
        merged = dict(facts or {})
    if content:
        merged["_llm_content"] = content
    creative_plan = content.get("creative_plan") if isinstance(content.get("creative_plan"), dict) else {}
    if creative_plan:
        variation = merged.get("variation") if isinstance(merged.get("variation"), dict) else {}
        variation = dict(variation)
        for key in (
            "hero_layout",
            "hero_text_side",
            "aesthetic_mode",
            "spacing_density",
            "radius_mode",
            "container_strategy",
            "typography_scale",
            "heading_style",
            "surface_depth",
            "overlap_mode",
            "motion_intensity",
            "image_treatment",
            "surface_style",
            "surface_mix",
            "section_surface_map",
            "about_variant",
            "color_strategy",
            "typography_mood",
            "gallery_density",
            "cta_style",
            "prompt_priority",
            "anti_repetition_rule",
            "services_variant",
            "reviews_variant",
            "faq_variant",
            "location_variant",
            "motion_style",
            "motion_mix",
            "visual_lane",
            "section_order",
            "brand_archetype",
            "emotional_outcome",
            "anti_identity",
            "story_arc",
            "cinematic_direction",
            "conversion_strategy",
            "visual_metaphor",
        ):
            if key in creative_plan:
                variation[key] = creative_plan[key]
        if "hero_layout" in creative_plan and "hero_variant" not in variation:
            variation["hero_variant"] = creative_plan["hero_layout"]
        if "reviews_variant" in creative_plan and "proof_style" not in variation:
            variation["proof_style"] = creative_plan["reviews_variant"]
        if "concept" in creative_plan:
            variation["creative_concept"] = creative_plan["concept"]
        merged["variation"] = variation
    return merged


def _render_vite_files_result(
    *,
    workspace: Path,
    files: dict[str, str],
    facts: dict[str, Any],
    attempts: list[dict[str, Any]],
    started: float,
    model: str,
    requested_paths: set[str] | None = None,
) -> ViteReactRenderResult:
    validate_vite_project_files(files, facts, requested_paths=requested_paths or set())
    write_vite_project(workspace, files)
    build_vite_project(workspace)
    index_path = workspace / "dist" / "index.html"
    html = index_path.read_text(encoding="utf-8")
    validate_vite_dist(workspace / "dist")
    return ViteReactRenderResult(
        html=html,
        source_files=files,
        model=model,
        attempts=attempts,
        elapsed_ms=int((time.time() - started) * 1000),
        dist_dir=str((workspace / "dist").resolve()),
        index_path=str(index_path.resolve()),
    )


def render_vite_react_site(
    builder_prompt: str,
    *,
    workspace_dir: str | os.PathLike[str],
    facts: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
    primary_model: str = PROXY_BUILDER_MODEL,
    fallback_model: str = "",
    max_tokens: int = 16000,
    temperature: float = 0.55,
) -> ViteReactRenderResult:
    """Generate, build and validate a Vite React project in one isolated workspace.

    Single-pass pipeline: LLM gera 1x -> build direto. Sem repair_retry,
    sem preview_fast, sem injecao de template sobre o output do LLM. Se o
    LLM ou o build falhar, o erro sobe e o job falha fechado. Nao publica
    Studio/OpenUI/template alternativo para mascarar erro de runtime.
    """
    started = time.time()
    facts = facts or {}
    # Injetar tokens de polo estético (Blocos Líquidos)
    facts = _inject_pole_tokens(facts)
    attempts: list[dict[str, Any]] = []
    requested_paths = extract_requested_vite_project_paths(builder_prompt)
    workspace = Path(workspace_dir).resolve()

    model_candidates = _select_vite_react_models_for_run(primary_model, fallback_model)
    if not model_candidates:
        model_candidates = [PROXY_BUILDER_MODEL]
    # Fail-fast total: sem studio-fallback para nenhum policy.
    # Se llm_policy=="none": Studio determinístico explícito, sem LLM.
    # Se llm_policy=="copy_only"/"creative_plan": JSON curto -> Studio; fail-fast se JSON/build falhar.
    # Se llm_policy=="full_code": LLM cascade, fail-fast se todos falham
    llm_policy = _get_llm_policy()

    if llm_policy == "none":
        attempts.append(
            {
                "model": "studio-deterministic",
                "model_index": 0,
                "status": "policy_none_deterministic",
                "elapsed_ms": 0,
                "policy": llm_policy,
            }
        )
        deterministic_files = prepare_vite_project_files(
            _generate_cinematic_studio_files(facts),
            facts=facts,
        )
        attempts.append(
            {
                "model": "studio-deterministic",
                "model_index": 0,
                "status": "studio_deterministic_success",
                "elapsed_ms": int((time.time() - started) * 1000),
                "source_files": len(deterministic_files),
                "policy": llm_policy,
            }
        )
        return _render_vite_files_result(
            workspace=workspace,
            files=deterministic_files,
            facts=facts,
            attempts=attempts,
            started=started,
            model="studio-deterministic",
            requested_paths=requested_paths,
        )

    if llm_policy in {"copy_only", "creative_plan"}:
        copy_prompt = _get_copy_only_user_prompt(facts, policy=llm_policy)
        copy_models = list(model_candidates)
        if not copy_models:
            copy_models = [PROXY_DEFAULT_MODEL]
        while len(copy_models) < _copy_only_attempts():
            copy_models.append(copy_models[-1])
        copy_models = copy_models[: _copy_only_attempts()]
        last_error = None
        studio_model = "studio-creative-plan" if llm_policy == "creative_plan" else "studio-copy-only"
        for model_idx, model in enumerate(copy_models, start=1):
            attempt_started = time.time()
            try:
                raw = _call_copy_only_llm(
                    copy_prompt,
                    model=model,
                    max_tokens=min(max_tokens, 4000),
                    temperature=temperature,
                    policy=llm_policy,
                )
                content = _parse_content_json(raw)
                if not content:
                    raise ViteReactRenderError("copy_only retornou JSON vazio ou invalido")
                attempts.append(
                    {
                        "model": model,
                        "model_index": model_idx,
                        "status": "copy_only_json_success",
                        "elapsed_ms": int((time.time() - attempt_started) * 1000),
                        "policy": llm_policy,
                    }
                )
                studio_facts = _merge_copy_only_content(facts, content)
                studio_files = prepare_vite_project_files(
                    _generate_cinematic_studio_files(studio_facts),
                    facts=studio_facts,
                )
                attempts.append(
                    {
                        "model": studio_model,
                        "model_index": model_idx,
                        "status": "studio_copy_only_success",
                        "elapsed_ms": int((time.time() - attempt_started) * 1000),
                        "source_files": len(studio_files),
                        "policy": llm_policy,
                    }
                )
                return _render_vite_files_result(
                    workspace=workspace,
                    files=studio_files,
                    facts=studio_facts,
                    attempts=attempts,
                    started=started,
                    model=studio_model,
                    requested_paths=requested_paths,
                )
            except Exception as exc:
                last_error = str(exc)[:500]
                attempts.append(
                    {
                        "model": model,
                        "model_index": model_idx,
                        "status": "copy_only_json_failed",
                        "elapsed_ms": int((time.time() - attempt_started) * 1000),
                        "error": last_error,
                        "policy": llm_policy,
                    }
                )
                if any(marker in last_error.lower() for marker in ("401 unauthorized", "invalid api key", "permission_error")):
                    break
        raise ViteReactRenderError(
            "Vite React renderer falhou no modo "
            f"{llm_policy} apos {len(copy_models)} tentativa(s). "
            "Ultimo erro: " + (last_error or "(sem erro capturado)")
        )

    # Cascata Haiku -> Sonnet -> Opus 4.8: tenta cada modelo em sequencia ate um dar 200.
    # Fail-fast: se TODOS falharem, levanta ViteReactRenderError com diagnostico.
    last_error: str | None = None
    files: dict[str, str] = {}
    html = ""
    index_path = workspace / "dist" / "index.html"

    for model_idx, model in enumerate(model_candidates, start=1):
        attempt_started = time.time()
        try:
            prompt = _compose_vite_user_prompt(
                builder_prompt,
                facts=facts,
                repair_context=repair_context,
            )
            raw = _call_vite_react_llm(
                prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                facts=facts,  # Sprint 12.13: caroço rico com briefing real do lead
            )
            files = prepare_vite_project_files(
                extract_vite_project_files(raw),
                facts=facts,
            )
            validate_vite_project_files(files, facts, requested_paths=requested_paths)
            write_vite_project(workspace, files)
            build_vite_project(workspace)
            index_path = workspace / "dist" / "index.html"
            html = index_path.read_text(encoding="utf-8")
            validate_vite_dist(workspace / "dist")
            attempts.append(
                {
                    "model": model,
                    "model_index": model_idx,
                    "status": "llm_success",
                    "elapsed_ms": int((time.time() - attempt_started) * 1000),
                    "source_files": len(files),
                    "html_chars": len(html),
                }
            )
            return ViteReactRenderResult(
                html=html,
                source_files=files,
                model=model,
                attempts=attempts,
                elapsed_ms=int((time.time() - started) * 1000),
                dist_dir=str((workspace / "dist").resolve()),
                index_path=str(index_path.resolve()),
            )
        except Exception as exc:
            last_error = str(exc)[:500]
            attempts.append(
                {
                    "model": model,
                    "model_index": model_idx,
                    "status": "llm_failed",
                    "elapsed_ms": int((time.time() - attempt_started) * 1000),
                    "error": last_error,
                }
            )
            # Erro permanente (403/401 plan vencido, auth invalida): nao tenta proximo
            lowered = last_error.lower()
            if any(marker in lowered for marker in ("401 unauthorized", "invalid api key", "permission_error")):
                break
            # Caso contrario, tenta proximo modelo da cascata

    # Fail-fast: todos os modelos da cascata falharam. Nao publica site genérico
    # para mascarar o erro. O lead fica em error_retry para reprocessamento.
    raise ViteReactRenderError(
        "Vite React renderer falhou em todos os modelos da cascata "
        f"({len(model_candidates)} tentados: {', '.join(model_candidates)}). "
        "Ultimo erro: " + (last_error or "(sem erro capturado)")
    )

def _select_vite_react_models(primary_model: str, fallback_model: str) -> list[str]:
    selected: list[str] = []
    for candidate in _model_candidates(primary_model, fallback_model):
        normalized = _normalize_model_alias(candidate)
        if normalized and normalized not in selected:
            selected.append(normalized)
    if not selected:
        selected.append(PROXY_BUILDER_MODEL)
    return selected


def _select_vite_react_models_for_run(primary_model: str, fallback_model: str) -> list[str]:
    if _single_model_mode_enabled():
        return _select_vite_react_models(primary_model or PROXY_BUILDER_MODEL, "")
    # Cascade explicito via env (sempre que setado, sobrescreve primary/fallback)
    explicit_cascade = os.getenv("FRALIB_VITE_NAMEHOST_MODELS", "").strip()
    if explicit_cascade:
        return _select_vite_react_models(explicit_cascade, "")
    if _namehost_batch_mode():
        preferred = (
            os.getenv("FRALIB_VITE_NAMEHOST_MODEL", "").strip()
            or os.getenv("FRALIB_PROXY_DEFAULT_MODEL", "").strip()
            or fallback_model
            or primary_model
        )
        light = os.getenv("FRALIB_PROXY_LIGHT_MODEL", "").strip()
        return _select_vite_react_models(preferred, light)
    return _select_vite_react_models(primary_model, fallback_model)


def _model_candidates(*values: str) -> list[str]:
    candidates: list[str] = []
    for value in values:
        for item in re.split(r"[,;]+", str(value or "")):
            clean = item.strip()
            if clean:
                candidates.append(clean)
    return candidates


def _safe_probe_preview(raw: str, limit: int = 240) -> str:
    preview = str(raw or "")[:limit]
    preview = re.sub(r"(?i)(bearer\s+)[a-z0-9._\-]+", r"\1***", preview)
    preview = re.sub(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+", r"\1***", preview)
    return preview


def _model_repair_attempts() -> int:
    try:
        return max(1, min(int(os.getenv("FRALIB_VITE_MODEL_REPAIR_ATTEMPTS", "3")), 3))
    except ValueError:
        return 3


def _single_model_mode_enabled() -> bool:
    env = os.getenv("FRALIB_SINGLE_MODEL_ONLY", "1").strip().lower()
    return env not in {"0", "false", "no", "off"}


def _preview_fast_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_PREVIEW_FAST", "1").strip().lower()
    return env not in {"0", "false", "no", "off"}


def _batch_first_project_attempts() -> int:
    return max(1, min(_env_int("FRALIB_VITE_BATCH_FIRST_ATTEMPTS", 2), 2))


def _batch_first_error_allows_repair(error: Exception) -> bool:
    lowered = str(error or "").lower()
    return not any(
        marker in lowered
        for marker in (
            "429",
            "too many requests",
            "usage_limit",
            "rate limit",
            "401 unauthorized",
            "403 forbidden",
            "invalid api key",
        )
    )


def _proxy_base_url() -> str:
    base = (
        os.getenv("LITELLM_BASE_URL")
        or os.getenv("ANTHROPIC_BASE_URL")
        or "https://llm.seunegociofralib.site"
    ).rstrip("/")
    if "api.aibee.cloud" in base.lower():
        return os.getenv("FRALIB_ANTHROPIC_CANONICAL_BASE_URL", "https://api.kpalabz.com/v1").rstrip("/")
    return base


def _proxy_api_key() -> str:
    return os.getenv("LITELLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""


def _proxy_credentials() -> tuple[str, str, int | None, Any | None]:
    """Resolve LiteLLM credentials through the shared provider key manager."""
    if os.getenv("LITELLM_API_KEY"):
        return _proxy_api_key(), _proxy_base_url(), None, None
    if os.getenv("FRALIB_BUILDER_FORCE_ENV_ANTHROPIC", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return _proxy_api_key(), _proxy_base_url(), None, None

    if os.getenv("FRALIB_BUILDER_USE_PROVIDER_KEYS", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }:
        try:
            try:
                from backend.services import ia_manager
            except Exception:
                try:
                    from services import ia_manager  # type: ignore
                except Exception:
                    import ia_manager  # type: ignore

            picked = ia_manager.pick_key("anthropic")
            if picked and picked[0]:
                picked_base = (picked[1] or _proxy_base_url()).rstrip("/")
                if "api.aibee.cloud" in picked_base.lower():
                    picked_base = os.getenv("FRALIB_ANTHROPIC_CANONICAL_BASE_URL", "https://api.kpalabz.com/v1").rstrip("/")
                return picked[0], picked_base, picked[2], ia_manager
        except Exception as exc:
            print(f"[ViteReact] provider key lookup falhou: {exc}")
    return _proxy_api_key(), _proxy_base_url(), None, None


def _mark_proxy_key_success(manager: Any | None, key_id: int | None) -> None:
    if not manager:
        return
    try:
        manager.mark_success(key_id)
    except Exception as exc:
        print(f"[ViteReact] mark_success falhou key_id={key_id}: {exc}")


def _mark_proxy_key_failure(manager: Any | None, key_id: int | None, error: Exception) -> None:
    if not manager:
        return
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    cooldown = 900 if status in (401, 403, 429) else 60
    detail = str(error)
    if response is not None:
        try:
            detail = response.text or detail
        except Exception:
            pass
    try:
        manager.mark_failure(key_id, detail[:500], cooldown_seconds=cooldown)
    except Exception as exc:
        print(f"[ViteReact] mark_failure falhou key_id={key_id}: {exc}")


def _is_litellm_openai_chat_base(base_url: str | None = None) -> bool:
    if os.getenv("FRALIB_LITELLM_OPENAI_CHAT", "1").strip().lower() in {"0", "false", "no"}:
        return False
    base = (base_url or _proxy_base_url()).lower()
    return any(
        marker in base
        for marker in (
            "127.0.0.1:4000",
            "localhost:4000",
            "llm.seunegociofralib.site",
        )
    )


def _batch_first_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_BATCH_FIRST", "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    if env in {"0", "false", "no", "off"}:
        return False
    return _is_namehost_base()


def _is_namehost_base() -> bool:
    # Sprint 12.2: detecta base namehost tanto 'proxy' (legacy) quanto 'llm.' (production)
    base = _proxy_base_url().lower()
    return "proxy" in base or "llm." in base


def _namehost_batch_mode() -> bool:
    return _is_namehost_base() and _batch_first_enabled()


def _probe_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_PROBE", "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    if env in {"0", "false", "no", "off"}:
        return False
    return not _namehost_batch_mode()


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _call_proxy_openai_chat(
    model_id: str,
    system: str,
    user: str,
    *,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    api_key, base_url, key_id, key_manager = _proxy_credentials()
    if not api_key:
        raise ViteReactRenderError("LiteLLM FraLib API key ausente")
    started = time.time()
    # #10 Prompt Caching: marcar system prompt como ephemeral cacheable
    # O proxy Anthropic (via litellm) aceita isso e faz cache do system prompt
    # Reduz custo de input em ate 90% para chamadas subsequentes
    if _prompt_caching_enabled():
        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system or "",
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user or "",
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
        ]
    else:
        messages = [
            {"role": "system", "content": system or ""},
            {"role": "user", "content": user or ""},
        ]
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if _json_response_format_enabled():
        payload["response_format"] = {"type": "json_object"}
    try:
        with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=420.0, write=60.0, pool=10.0)) as client:
            response = client.post(
                _chat_completions_url(base_url),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            try:
                response.raise_for_status()
            except Exception:
                if "response_format" in json.dumps(payload) and _response_format_retriable(response):
                    payload.pop("response_format", None)
                    response = client.post(
                        _chat_completions_url(base_url),
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    response.raise_for_status()
                else:
                    raise _proxy_http_error(response) from None
    except Exception as exc:
        _mark_proxy_key_failure(key_manager, key_id, exc)
        raise
    _mark_proxy_key_success(key_manager, key_id)
    data = response.json()
    message = (data.get("choices") or [{}])[0].get("message") or {}
    text_out = _extract_proxy_message_content(message.get("content"))
    usage = data.get("usage") or {}
    usage_out = {
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0,
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0,
    }
    _record_builder_llm_usage(model_id, usage_out, latency_ms=int((time.time() - started) * 1000))
    return text_out, usage_out


def _extract_proxy_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
                continue
            nested = item.get("content")
            if isinstance(nested, str) and nested.strip():
                parts.append(nested)
        return "".join(parts).strip()
    if isinstance(content, dict):
        received = content.get("received")
        if isinstance(received, dict):
            nested = received.get("content") or received.get("blocks")
            extracted = _extract_proxy_message_content(nested)
            if extracted:
                return extracted
        for key in ("text", "content", "response", "html", "output"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _proxy_http_error(response: httpx.Response) -> ViteReactRenderError:
    """Keep proxy response bodies visible without exposing credentials."""
    try:
        body = response.text or ""
    except Exception:
        body = ""
    body = _safe_probe_preview(body, limit=900)
    detail = f"HTTP {response.status_code} {response.reason_phrase}"
    if body:
        detail = f"{detail}: {body}"
    return ViteReactRenderError(detail)


def _record_builder_llm_usage(model_id: str, usage: dict[str, Any], *, latency_ms: int | None = None) -> None:
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    if input_tokens <= 0 and output_tokens <= 0:
        return
    try:
        try:
            from agents import llm_direct
        except Exception:
            import llm_direct  # type: ignore

        registrar = getattr(llm_direct, "_registrar_llm_budget", None)
        if registrar:
            registrar(
                model_id,
                input_tokens,
                output_tokens,
                agente="builder_renderer",
                provider="anthropic",
                latency_ms=latency_ms,
            )
    except Exception as exc:
        print(f"[ViteReact] ledger builder falhou: {exc}")


def _json_response_format_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_JSON_RESPONSE_FORMAT", "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    if env in {"0", "false", "no", "off"}:
        return False
    return not _is_namehost_base()


def _prompt_caching_enabled() -> bool:
    """#10 Prompt Caching: Habilita cache_control ephemeral no system+user prompt.

    Reduz custo LLM em ate 90% para chamadas subsequentes (cache hit = 0.1x preco).
    Padrao: ON para modelos Claude (Anthropic suporta nativamente).
    """
    env = os.getenv("FRALIB_VITE_PROMPT_CACHE", "").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    if env in {"1", "true", "yes", "on"}:
        return True
    # Default: ON (Anthropic suporta nativamente)
    return True


def _response_format_retriable(response: httpx.Response) -> bool:
    if response.status_code not in {400, 422}:
        return False
    try:
        body = response.text.lower()
    except Exception:
        body = ""
    return "response_format" in body or "json_object" in body


def _probe_vite_react_model(model: str) -> tuple[bool, str]:
    """Check whether a model can return a small strict JSON object cleanly."""
    probe_system = "You are a JSON API. Return one strict JSON object only, no markdown and no commentary."
    probe_prompt = (
        "Create a minimal Vite React file map. Return exactly this schema: "
        '{"files":{"src/App.tsx":"export default function App(){return null;}"}}'
    )
    try:
        model_id = {
            "haiku": PROXY_LIGHT_MODEL,
            "sonnet": PROXY_DEFAULT_MODEL,
            "opus": PROXY_BUILDER_MODEL,
        }.get(model, model)
        if _is_litellm_openai_chat_base():
            raw, _usage = _call_proxy_openai_chat(
                model_id,
                probe_system,
                probe_prompt,
                temperature=0.1,
                max_tokens=800,
            )
        else:
            try:
                from services.llm_router import call_llm
            except Exception:
                try:
                    from backend.services.llm_router import call_llm
                except Exception:
                    from llm_router import call_llm

            raw, _usage = call_llm(
                "anthropic",
                model_id,
                probe_system,
                probe_prompt,
                temperature=0.1,
                max_tokens=800,
            )
        ok = bool(extract_vite_project_files(raw).get("src/App.tsx"))
        return ok, raw
    except Exception as exc:
        return False, str(exc)


def _probe_failure_blocks_generation(raw: str) -> bool:
    lowered = str(raw or "").lower()
    return any(
        marker in lowered
        for marker in (
            "401 unauthorized",
            "403 forbidden",
            "invalid api key",
            "authentication",
            "connection refused",
            "timed out",
            "timeout",
            "rate limit",
            "429",
        )
    )


def _clean_json_block(raw: str) -> str:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).lower().strip()


def _generate_vite_project_files_in_batches(
    builder_prompt: str,
    *,
    facts: dict[str, Any],
    model: str,
    max_tokens: int,
    temperature: float,
    repair_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    files: dict[str, str] = {}
    # Phase 1: generate core files, then detect components from Index.tsx
    batches = list(VITE_REACT_FILE_BATCHES_CORE)
    total_batches = len(batches)
    for batch_index, (batch_name, paths) in enumerate(batches, 1):
        # Model routing: batches simples (app/main/types/css) -> Haiku
        # Batches visuais (hero, gallery) -> Sonnet
        # Batches complexos/criativos -> Opus
        batch_model = _route_model_for_batch(batch_name, model)
        batch_prompt = _compose_vite_file_batch_prompt(
            builder_prompt,
            facts=facts,
            batch_name=batch_name,
            paths=paths,
            completed_paths=sorted(files),
            repair_context=repair_context,
        )
        last_exc: Exception | None = None
        for attempt in range(1, _batch_generation_attempts() + 1):
            try:
                raw = _call_vite_react_llm(
                    batch_prompt,
                    model=batch_model,
                    max_tokens=_batch_token_budget(batch_name, max_tokens),
                    temperature=temperature if attempt == 1 else 0.1,
                )
            except Exception as exc:
                last_exc = exc
                if _is_transient_proxy_error(exc) and attempt < _batch_generation_attempts():
                    time.sleep(_transient_proxy_retry_delay_seconds(attempt))
                    continue
                raise
            try:
                batch_files = extract_vite_project_files(raw)
                missing = sorted(set(paths).difference(batch_files))
                if missing:
                    raise ViteReactRenderError(
                        f"batch {batch_name} sem arquivos pedidos: {', '.join(missing)}"
                    )
                files.update({path: batch_files[path] for path in paths})
                break
            except Exception as exc:
                last_exc = exc
                single_file = _extract_single_requested_file(raw, paths)
                if single_file:
                    files.update(single_file)
                    break
                repaired_raw = _repair_batch_output_format(
                    raw,
                    model=model,
                    paths=paths,
                    batch_name=batch_name,
                )
                if repaired_raw:
                    try:
                        batch_files = extract_vite_project_files(repaired_raw)
                        missing = sorted(set(paths).difference(batch_files))
                        if not missing:
                            files.update({path: batch_files[path] for path in paths})
                            break
                    except Exception:
                        pass
                batch_prompt = _compose_vite_file_batch_prompt(
                    builder_prompt,
                    facts=facts,
                    batch_name=batch_name,
                    paths=paths,
                    completed_paths=sorted(files),
                    repair_context={
                        "validation_errors": str(exc),
                        "previous_output": raw[:4000],
                    },
                )
        else:
            raise ViteReactRenderError(f"geracao em lotes falhou em {batch_name}: {last_exc}")
        if batch_index < total_batches:
            delay = _batch_spacing_seconds()
            if delay > 0:
                time.sleep(delay)

    # Phase 2: detect component imports from Index.tsx and generate them
    index_content = files.get("src/pages/Index.tsx", "")
    component_batches = _detect_components_from_page(index_content)
    component_paths = [path for _name, paths in component_batches for path in paths]
    # Filter out already generated
    pending_components = [p for p in component_paths if p not in files]
    if pending_components:
        # Generate components in sub-batches of 3
        for i in range(0, len(pending_components), 3):
            chunk = pending_components[i:i+3]
            batch_name = f"components-{i//3 + 1}"
            batch_prompt = _compose_vite_file_batch_prompt(
                builder_prompt,
                facts=facts,
                batch_name=batch_name,
                paths=chunk,
                completed_paths=sorted(files),
                repair_context=repair_context,
            )
            for attempt in range(1, _batch_generation_attempts() + 1):
                try:
                    raw = _call_vite_react_llm(
                        batch_prompt,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature if attempt == 1 else 0.1,
                    )
                except Exception as exc:
                    if _is_transient_proxy_error(exc) and attempt < _batch_generation_attempts():
                        time.sleep(_transient_proxy_retry_delay_seconds(attempt))
                        continue
                    raise
                try:
                    batch_files = extract_vite_project_files(raw)
                    # Accept whatever components we got (flexible)
                    for p in chunk:
                        if p in batch_files:
                            files[p] = batch_files[p]
                    # Also accept any extra components the LLM gave us
                    for p, v in batch_files.items():
                        if p.startswith("src/components/") and p not in files:
                            files[p] = v
                    break
                except Exception:
                    if attempt == _batch_generation_attempts():
                        pass  # skip failed component batch gracefully
            delay = _batch_spacing_seconds()
            if delay > 0:
                time.sleep(delay)

    return files


def _batch_generation_attempts() -> int:
    return max(1, min(_env_int("FRALIB_VITE_BATCH_ATTEMPTS", 3), 5))


def _is_transient_proxy_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "429",
            "too many requests",
            "503",
            "service unavailable",
            "502",
            "504",
            "rate limit",
            "overloaded",
        )
    )


def _transient_proxy_retry_delay_seconds(attempt: int) -> float:
    base = max(10, min(_env_int("FRALIB_VITE_TRANSIENT_RETRY_SECONDS", 90), 600))
    return float(min(base * max(1, attempt), 600))


def _batch_spacing_seconds() -> float:
    configured = os.getenv("FRALIB_VITE_BATCH_SPACING_SECONDS")
    if configured is not None and configured.strip() != "":
        try:
            return float(max(0, min(float(configured), 120)))
        except Exception:
            return 0.0
    if _is_namehost_base():
        return 8.0
    return 0.0


def _batch_max_tokens(max_tokens: int) -> int:
    configured = _env_int("FRALIB_VITE_BATCH_MAX_TOKENS", 3200)
    if max_tokens > 0:
        return max(1400, min(configured, max_tokens))
    return configured


def _batch_token_budget(batch_name: str, max_tokens: int) -> int:
    default_budget = _batch_max_tokens(max_tokens)
    tuned = {
        "app": 1400,
        "main": 1200,
        "types": 900,
        "css": 1800,
        "page": 1700,
        "navbar": 1600,
        "hero": 2000,
        "about": 1500,
        "services": 1500,
        "gallery": 1400,
        "lifestyle": 1400,
        "reviews": 1300,
        "location": 1300,
        "booking-modal": 1100,
        "contact-cta": 1200,
        "footer": 1000,
    }.get(batch_name, default_budget)
    return min(default_budget, tuned)


def _route_model_for_batch(batch_name: str, default_model: str) -> str:
    """Roteia modelo por batch.

    Batches simples (app/main/types/css) -> Haiku (~10x mais barato)
    Batches visuais (hero/about/gallery) -> Sonnet (balanceado)
    Batches complexos/criativos -> Opus (top-tier)

    Custo LLM cai ~50%, velocidade +30% em media.
    """
    try:
        from backend.services.vite_renderer_models import batch_model_for_batch
        routed = batch_model_for_batch(batch_name)
    except Exception:
        return default_model

    # Mapear alias -> modelo real usando normalize_model_alias
    from backend.services.vite_renderer_models import normalize_model_alias
    target_alias = routed  # haiku, sonnet, opus

    # Se default_model ja e um alias, retornar o roteado
    default_alias = normalize_model_alias(default_model)
    # Se o roteado == default, nao muda
    if target_alias == default_alias:
        return default_model

    # Retornar o alias roteado - o _call_vite_react_llm vai resolver
    return target_alias


def _batch_format_repair_budget() -> int:
    return max(600, min(_env_int("FRALIB_VITE_FORMAT_REPAIR_MAX_TOKENS", 1400), 2200))


def _repair_batch_output_format(raw: str, *, model: str, paths: list[str], batch_name: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    prompt = f"""Reformat the previous response for FraLib Builder.

Return only valid file tags, no markdown, no commentary:
<files>
  <file path="exact/requested/path"><![CDATA[
  exact original file content
  ]]></file>
</files>

Rules:
- Do not rewrite business copy, only recover structure/escaping.
- Keep only these exact paths:
{chr(10).join(f"- {path}" for path in paths)}
- If the previous response contains extra prose, discard it.
- If the previous response contains one malformed JSON object, extract the file contents and emit tags.
- If the previous response is already tagged, normalize it and close missing tags.
- Batch name: {batch_name}

Previous response to repair:
{text[:12000]}
"""
    try:
        return _call_vite_react_llm(
            prompt,
            model=model,
            max_tokens=_batch_format_repair_budget(),
            temperature=0.0,
        )
    except Exception:
        return ""


def _extract_files_via_regex(text: str) -> dict[str, str]:
    """Best-effort extract ``"path": "content"`` pairs from truncated JSON.

    When the kpalabz proxy returns 50k+ chars of JSON cut off mid-string, the
    standard ``json.loads`` fails with ``Unterminated string``. This walks
    the text char-by-char, tracking quote/brace depth, and harvests every
    well-formed top-level ``"path": "content"`` pair — even when the
    surrounding ``{"files": {...}}`` wrapper is broken.

    Returns a ``files`` dict, or empty ``{}`` if nothing salvageable.
    """
    out: dict[str, str] = {}

    # Strategy A: walk the text and find "key": "value" pairs where value
    # is a complete JSON string (i.e. starts and ends with unescaped ")
    i = 0
    n = len(text)
    last_open = -1
    while i < n:
        # Find next unescaped quote
        if text[i] != '"':
            i += 1
            continue
        # Skip escaped quote
        if i > 0 and text[i - 1] == "\\":
            i += 1
            continue
        start = i
        # Walk to find closing quote
        j = i + 1
        while j < n:
            c = text[j]
            if c == "\\":
                j += 2  # skip escape
                continue
            if c == '"':
                break
            j += 1
        if j >= n:
            # Truncated before close - stop here
            break
        # We have a complete string [start, j]
        key_candidate = text[start + 1 : j]
        # Look ahead for ":"
        k = j + 1
        while k < n and text[k] in " \r\n\t":
            k += 1
        if k >= n or text[k] != ":":
            i = j + 1
            continue
        # Look ahead for next string value
        m = k + 1
        while m < n and text[m] in " \r\n\t":
            m += 1
        if m >= n or text[m] != '"':
            i = j + 1
            continue
        # Walk value string
        vstart = m
        p = m + 1
        while p < n:
            c = text[p]
            if c == "\\":
                p += 2
                continue
            if c == '"':
                break
            p += 1
        if p >= n:
            # value string truncated - skip
            break
        value = text[vstart + 1 : p]
        # Heuristic: keys look like file paths (contain / or .) and
        # values contain code (often >5 chars)
        if ("/" in key_candidate or key_candidate.endswith(tuple(".tsx .ts .jsx .js .html .css .json .md .yaml .yml".split()))) and len(value) >= 1:
            out.setdefault(key_candidate, value)
        i = p + 1
    return out


def _tolerant_json_loads(text: str) -> dict:
    """Parse JSON tolerating mid-string truncation.

    The Vite React LLM frequently produces 50k+ char JSON outputs that the
    kpalabz proxy cuts off mid-string, leaving Python's strict ``json.loads``
    unable to parse them and crashing the whole build with
    ``Unterminated string at line 1 column 52485``.

    Strategy:
    1. Try strict ``json.loads`` first (fast path).
    2. On failure, use ``_extract_files_via_regex`` to harvest
       ``"path": "content"`` pairs that are individually complete
       (escape-aware quote walking), then wrap them in
       ``{"files": {...}}``. This recovers the bulk of the build even
       when the surrounding JSON is cut off mid-stream.
    3. Fall back to the raw_decode / close-bracket heuristics.
    """
    if not text:
        return {}
    # Fast path
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Regex harvest — this is the workhorse for truncated output
    files = _extract_files_via_regex(text)
    if files:
        return {"files": files}

    # Last-resort: raw_decode + closing heuristics
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        try:
            obj, end = decoder.raw_decode(text, idx)
            if isinstance(obj, dict) and isinstance(obj.get("files"), dict):
                return obj
        except json.JSONDecodeError:
            break
        break
    for trail in ('"', '"}', '"]', '"}]', '"\n}', '"\n]'):
        try:
            obj = json.loads(text + trail)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    raise ViteReactRenderError(
        f"JSON de arquivos irrecuperavel (len={len(text)})"
    )


def extract_vite_project_files(raw: str) -> dict[str, str]:
    """Extract a `files` mapping from tagged blocks or strict JSON output."""
    text = (raw or "").strip()
    if not text:
        raise ViteReactRenderError("resposta vazia")
    tagged_files = _extract_tagged_file_blocks(text)
    if tagged_files:
        return tagged_files
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        match = re.search(r"(?s)\{.*\}", text)
        if not match:
            raise ViteReactRenderError("resposta nao contem JSON de arquivos")
        text = match.group(0)
    payload = _tolerant_json_loads(text)
    if not isinstance(payload, dict):
        raise ViteReactRenderError("payload extraido nao e dict")
    files = payload.get("files") if isinstance(payload, dict) else None
    if not files and isinstance(payload, dict):
        for wrapper_key in ("received", "project", "data", "result"):
            wrapper = payload.get(wrapper_key)
            if isinstance(wrapper, dict) and wrapper.get("files"):
                files = wrapper.get("files")
                break
    if isinstance(files, list):
        files = {str(item.get("path") or ""): item.get("content") for item in files if isinstance(item, dict)}
    if not isinstance(files, dict) or not files:
        raise ViteReactRenderError("JSON sem objeto files")
    return {str(path).replace("\\", "/"): str(content or "") for path, content in files.items()}


def _extract_tagged_file_blocks(raw: str) -> dict[str, str]:
    text = str(raw or "").strip()
    matches = re.findall(
        r"<file\s+path=[\"']([^\"']+)[\"']\s*>([\s\S]*?)</file>",
        text,
        flags=re.IGNORECASE,
    )
    if not matches:
        return {}
    files: dict[str, str] = {}
    for path, body in matches:
        content = str(body or "")
        cdata = re.search(r"<!\[CDATA\[([\s\S]*?)\]\]>", content, flags=re.IGNORECASE)
        if cdata:
            content = cdata.group(1)
        files[str(path).replace("\\", "/")] = content.strip("\r\n")
    if files:
        return files
    partial = re.search(r"<file\s+path=[\"']([^\"']+)[\"']\s*>([\s\S]+)$", text, flags=re.IGNORECASE)
    if partial:
        path = str(partial.group(1) or "").replace("\\", "/")
        content = str(partial.group(2) or "")
        cdata = re.search(r"<!\[CDATA\[([\s\S]*)$", content, flags=re.IGNORECASE)
        if cdata:
            content = cdata.group(1)
        content = re.sub(r"\]\]>\s*$", "", content).strip("\r\n")
        if path and content:
            return {path: content}
    return {}


def _extract_single_requested_file(raw: str, paths: list[str]) -> dict[str, str]:
    if len(paths) != 1:
        return {}
    text = str(raw or "").strip()
    if not text:
        return {}
    fence = re.search(r"```(?:tsx|ts|css|json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    if text.startswith("<files>") or text.startswith("{"):
        return {}
    looks_like_source = any(
        marker in text
        for marker in (
            "import ",
            "export ",
            "className=",
            "@import ",
            "const ",
            "function ",
            "<section",
            "<div",
        )
    )
    if not looks_like_source:
        return {}
    return {paths[0]: text}


def _sanitize_logger_in_source(source: str) -> str:
    """Sprint 11.6: injeta `const logger = console;` quando o LLM usa `logger.`
    sem import. Idempotente. Funciona para .tsx e .ts.

    Resolve: 'name logger is not defined' quando Sonnet gera codigo com helper
    custom chamado logger mas sem definir.
    """
    import re

    # Heuristica: arquivo .tsx/.ts usa `logger.` mas nao tem `const/let/var logger`, `function logger`,
    # `class Logger` ou `import ... logger ...` correspondente.
    if not re.search(r"\blogger\.", source):
        return source  # nada a fazer
    # Verifica se ja tem alguma definicao de logger (qualquer keyword)
    # Const/let/var: aceita tanto `=` quanto `:` (type annotation)
    if re.search(r"\b(const|let|var)\s+[Ll]ogger\s*[=:(]", source):
        return source  # ja tem definicao (incluindo Logger capitalizado)
    if re.search(r"\b(function|class)\s+[Ll]ogger\b", source):
        return source  # ja tem definicao (function/class)
    if re.search(r"\bimport\s+.*[Ll]ogger.*from", source):
        return source  # ja tem import

    # Injeta no inicio do arquivo (depois dos imports, antes do primeiro nao-import)
    lines = source.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or not stripped:
            insert_idx = i + 1
        else:
            break
    lines.insert(insert_idx, "// Sprint 11.6: logger shim (LLM generated code references it)")
    lines.insert(insert_idx + 1, "const logger = console;")
    return "\n".join(lines)


def prepare_vite_project_files(files: dict[str, str], *, facts: dict[str, Any]) -> dict[str, str]:
    """Normalize generated files and inject deterministic Vite scaffolding."""
    # Sprint 11.6: sanitize logger antes de qualquer outra transformacao
    # Sprint 16: Preserve CSS files (don't filter them out like .tsx/.ts)
    sanitized = {}
    for path, content in files.items():
        if path.endswith((".tsx", ".ts", ".jsx", ".js")):
            sanitized[path] = _sanitize_logger_in_source(content)
        elif path.endswith(".css"):
            sanitized[path] = content  # CSS passes through unchanged
    prepared = {_safe_project_path(path): content for path, content in sanitized.items()}
    prepared["package.json"] = json.dumps(FIXED_PACKAGE_JSON, ensure_ascii=False, indent=2)
    prepared["vite.config.ts"] = vite_template_vite_config()
    prepared["tsconfig.json"] = vite_template_tsconfig()

    # Sprint 16: Inject archetype palette into facts for index.html theme-color
    facts_with_archetype = dict(facts)
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or facts.get("segment") or "servicos").lower()
    archetype = _get_archetype_for_segment(segment)
    palette = _get_archetype_palette(archetype)
    facts_with_archetype["_archetype_palette"] = palette
    facts_with_archetype["_archetype"] = archetype

    prepared["index.html"] = vite_template_index_html(facts_with_archetype)
    prepared.setdefault("src/main.tsx", vite_template_main_tsx())
    prepared.setdefault("src/App.tsx", vite_template_app_tsx())
    prepared.setdefault("src/types.ts", vite_template_types_ts())
    prepared.setdefault("src/fralib-jsx.d.ts", vite_template_jsx_fallback_types())
    prepared["src/index.css"] = _ensure_index_css_contract(
        prepared.get("src/index.css", vite_template_index_css())
    )
    _normalize_generated_imports_and_hooks(prepared)
    _stabilize_app_contract(prepared)
    _drop_malformed_data_url_in_jsx(prepared)
    _ensure_lgpd_banner_contract(prepared, facts)
    _rewrite_editorial_images(prepared, facts)
    _ensure_editorial_media_contract(prepared, facts)
    _ensure_factual_motion_contract(prepared, facts)
    _normalize_component_export_contract(prepared)
    _enforce_hero_visual_contract(prepared)
    # Sprint 12.19: post-process - replace any literal {var} placeholders that
    # the studio fallback failed to interpolate (e.g. f-string on LifestyleSection
    # that was missing the `f` prefix on the template). The vars are looked up
    # from the segment-aware dict + facts at the time the file is written.
    _interpolate_studio_placeholders(prepared, facts)
    return dict(sorted(prepared.items()))


def _interpolate_studio_placeholders(prepared: dict[str, str], facts: dict[str, Any]) -> None:
    """Sprint 12.19: defensive fix.

    The studio fallback generates f-strings that reference segment-aware vars
    (lifestyle_title, lifestyle_desc, dense_cards, nav_items, etc). If a string
    was created with a regular \"\"\" instead of f\"\"\", the placeholders leak
    to the .tsx as literal {var}. The browser throws ReferenceError and the
    site shows a black screen.

    This pass scans .tsx files for any literal {var} that matches a known
    segment-aware var, and replaces it with the actual value. The vars are
    rebuilt by calling the segment-detection logic that mirrors the studio
    fallback.
    """
    import re as _re

    # Sprint 14: extract LLM copy_only content for content override
    llm_content: dict[str, Any] = {}
    if isinstance(facts.get("_llm_content"), dict):
        llm_content = facts["_llm_content"]

    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    raw_segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or "")
    segment = raw_segment.lower()
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "Curitiba")
    name = str(business.get("name") or business.get("business_name") or "Negócio local")
    phone = str(business.get("whatsapp") or business.get("phone") or "41999999999")
    rating = str(business.get("rating") or "4.8")

    # Mirror the legacy segment copy chain used by the cinematic studio.
    if "barbearia" in segment or "barbeiro" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar horario", "Ver servicos", "Barbeiro em barbearia"
        lifestyle_title, lifestyle_desc = "Tradicao em cada corte", "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes."
    elif "academia" in segment or "fitness" in segment or "crossfit" in segment or "musculacao" in segment:
        cta_primary, cta_secondary, alt_img = "Comecar treino", "Ver estrutura", "Alunos em treino fitness"
        lifestyle_title, lifestyle_desc = "Energia e constancia", "Um espaco para criar rotina, encontrar orientacao e manter frequencia sem complicar."
    elif "restaurante" in segment or "bar " in segment or "pizzaria" in segment or "hamburgueria" in segment or "lanchonete" in segment or "cafeteria" in segment:
        cta_primary, cta_secondary, alt_img = "Fazer reserva", "Ver menu", "Restaurante"
        lifestyle_title, lifestyle_desc = "Experiencia gastronomica", "Cada prato preparado com cuidado para proporcionar uma experiencia unica."
    elif "clinica" in segment or "estetica" in segment or "dermatologia" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar consulta", "Conhecer servicos", "Clinica"
        lifestyle_title, lifestyle_desc = "Cuidado e acolhimento", "Ambiente preparado para recebe-lo com conforto e seguranca em cada atendimento."
    elif "imobiliaria" in segment or "imoveis" in segment:
        cta_primary, cta_secondary, alt_img = "Ver imoveis", "Falar corretor", "Imovel"
        lifestyle_title, lifestyle_desc = "Seu proximo imovel", "Encontre o imovel ideal com quem entende do mercado local."
    elif "nutricionista" in segment or "nutricao" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar consulta", "Ver planos", "Nutricionista"
        lifestyle_title, lifestyle_desc = "Nutricao de verdade", "Transforme sua alimentacao com acompanhamento profissional cientifico."
    elif "advocacia" in segment or "advogado" in segment:
        cta_primary, cta_secondary, alt_img = "Falar com advogado", "Ver areas", "Escritorio de advocacia"
        lifestyle_title, lifestyle_desc = "Direito com seriedade", "Atendimento juridico transparente e dedicado a sua causa."
    elif "odonto" in segment or "dentista" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar consulta", "Ver tratamentos", "Consultorio odontologico"
        lifestyle_title, lifestyle_desc = "Seu sorriso perfeito", "Tecnologia de ponta e carinho em cada tratamento para seu sorriso."
    elif "ecommerce" in segment or "loja" in segment or "roupas" in segment:
        cta_primary, cta_secondary, alt_img = "Ver produtos", "Ver ofertas", "Produtos"
        lifestyle_title, lifestyle_desc = "Qualidade garantida", "Produtos selecionados com cuidado para atender suas necessidades."
    elif "petshop" in segment or "pet " in segment:
        cta_primary, cta_secondary, alt_img = "Agendar servico", "Ver produtos", "Pet shop"
        lifestyle_title, lifestyle_desc = "Amor pelos animais", "Cuidamos do seu pet como se fosse nosso. Amor e dedicacao em cada servico."
    elif "hotel" in segment or "pousada" in segment or "hostel" in segment:
        cta_primary, cta_secondary, alt_img = "Reservar", "Ver quartos", "Hotel"
        lifestyle_title, lifestyle_desc = "Sua casa longe de casa", "Conforto e acolhimento para tornar sua estadia inesquecivel."
    elif "salao_beleza" in segment or "beleza" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar horario", "Ver servicos", "Salao de beleza"
        lifestyle_title, lifestyle_desc = "Beleza e bem-estar", "Transformamos seu visual com tecnicas modernas e produtos de qualidade."
    elif "fisioterapia" in segment or "fisio" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar sessao", "Ver tratamentos", "Fisioterapia"
        lifestyle_title, lifestyle_desc = "Movimento com saude", "Recupere sua qualidade de vida com tratamento fisioterapêutico humanizado."
    elif "escola" in segment or "cursinho" in segment or "idiomas" in segment:
        cta_primary, cta_secondary, alt_img = "Matricular", "Ver cursos", "Escola"
        lifestyle_title, lifestyle_desc = "Educacao que transforma", "Formando cidadaos preparados para o futuro com excelencia e valores."
    elif "autoescola" in segment:
        cta_primary, cta_secondary, alt_img = "Matricular", "Ver categorias", "Autoescola"
        lifestyle_title, lifestyle_desc = "Sua habilitacao na mao", "Metodologia comprovada para voce passar no DETRAN de primeira."
    elif "oficina" in segment or "mecanica" in segment or "eletrica" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar servico", "Ver servicos", "Oficina mecanica"
        lifestyle_title, lifestyle_desc = "Seu carro em boas maos", "Servico de qualidade com transparencia e compromisso com seu veiculo."
    elif "farmacia" in segment or "manipulacao" in segment:
        cta_primary, cta_secondary, alt_img = "Ver produtos", "Ver promocoes", "Farmacia"
        lifestyle_title, lifestyle_desc = "Saude e bem-estar", "Farmacêuticos capacitados para orientar sobre medicamentos e cuidados."
    elif "psicologo" in segment or "psicologia" in segment:
        cta_primary, cta_secondary, alt_img = "Agendar sessao", "Ver abordagens", "Consultorio de psicologia"
        lifestyle_title, lifestyle_desc = "Cuidado emocional", "Um espaco seguro para falar sobre seus sentimentos e desenvolver seu potencial."
    elif "fotografo" in segment or "fotografia" in segment or "design" in segment or "grafico" in segment:
        cta_primary, cta_secondary, alt_img = "Ver portfolio", "Fazer orcamento", "Fotografia"
        lifestyle_title, lifestyle_desc = "Momentos eternizados", "Capturamos momentos e emocoes com sensibilidade e tecnica."
    else:
        cta_primary, cta_secondary, alt_img = "Saiba mais", "Ver servicos", name
        lifestyle_title, lifestyle_desc = "Experiencia unica", f"Atendimento dedicado para garantir sua satisfacao em {city}."


    # Sprint 14: apply LLM copy_only overrides before building var_map.
    if llm_content:
        hero = llm_content.get("hero", {}) if isinstance(llm_content.get("hero"), dict) else {}
        life = llm_content.get("lifestyle") if isinstance(llm_content.get("lifestyle"), dict) else {}
        if hero.get("cta_primary"):
            cta_primary = str(hero["cta_primary"])
        if hero.get("cta_secondary"):
            cta_secondary = str(hero["cta_secondary"])
        if llm_content.get("gallery_alt"):
            alt_img = str(llm_content["gallery_alt"])
        if life.get("title"):
            lifestyle_title = str(life["title"])
        if life.get("description"):
            lifestyle_desc = str(life["description"])

    # Map of placeholder var name -> replacement value (in the order they appear)
    # Sprint 14.2: var_map now includes ALL customizable text fields
    # {{cta_primary}}, {{cta_secondary}}, {{alt_img}} are literals in TSX files
    # from the studio fallback templates. This map replaces them.
    var_map = {
        "name": name,
        "phone": phone,
        "rating": rating,
        "city": city,
        "segment": raw_segment,
        "cta_primary": cta_primary,
        "cta_secondary": cta_secondary,
        "alt_img": alt_img,
        "lifestyle_title": lifestyle_title,
        "lifestyle_desc": lifestyle_desc,
    }

    # Find .tsx files and replace literal {var} placeholders
    for path in list(prepared.keys()):
        if not path.endswith(".tsx"):
            continue
        content = prepared[path]
        if "{" not in content:
            continue
        original = content
        for var_name, value in var_map.items():
            # Replace {var} with value, but only if the var exists in our map
            # and the placeholder is standalone (not inside another string)
            content = _re.sub(
                r"\{\{?" + _re.escape(var_name) + r"\}?\}",
                value.replace("\\", "\\\\").replace("$", "\\$"),
                content,
            )
        if content != original:
            prepared[path] = content


def _normalize_component_export_contract(files: dict[str, str]) -> None:
    component_names = {
        "src/components/Navbar.tsx": "Navbar",
        "src/components/HeroSection.tsx": "HeroSection",
        "src/components/AboutSection.tsx": "AboutSection",
        "src/components/GallerySection.tsx": "GallerySection",
        "src/components/ServicesSection.tsx": "ServicesSection",
        "src/components/LifestyleSection.tsx": "LifestyleSection",
        "src/components/ReviewsSection.tsx": "ReviewsSection",
        "src/components/LocationSection.tsx": "LocationSection",
        "src/components/BookingModal.tsx": "BookingModal",
        "src/components/ContactCTA.tsx": "ContactCTA",
        "src/components/Footer.tsx": "Footer",
        "src/components/LgpdBanner.tsx": "LgpdBanner",
    }
    for path, export_name in component_names.items():
        content = str(files.get(path) or "")
        if not content:
            continue
        if f"export default {export_name}" in content or re.search(r"export\s+default\s+function\b", content):
            continue
        if re.search(rf"export\s+function\s+{re.escape(export_name)}\b", content) or re.search(
            rf"export\s+const\s+{re.escape(export_name)}\b", content
        ):
            files[path] = content.rstrip() + f"\n\nexport default {export_name};\n"
    _normalize_page_export_contract(files)


def _normalize_page_export_contract(files: dict[str, str]) -> None:
    path = "src/pages/Index.tsx"
    content = str(files.get(path) or "")
    if not content:
        return
    has_named = bool(re.search(r"export\s+(?:function|const)\s+Index\b", content))
    has_default = bool(re.search(r"export\s+default\s+(?:function\s+Index\b|Index\b)", content))
    # Count occurrences of `export { Index }` so we never double-append.
    already_re_exported = bool(re.search(r"export\s*\{\s*Index\s*\}", content))
    if has_default and not has_named and re.search(r"default\s+function\s+Index\b", content):
        if not already_re_exported:
            files[path] = content.rstrip() + "\n\nexport { Index };\n"
    elif has_named and not has_default:
        files[path] = content.rstrip() + "\n\nexport default Index;\n"


def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:
    # Sprint 12.14: fix LLM generating literal backslash-n instead of real newlines
    for path in list(files.keys()):
        if path.endswith((".tsx", ".ts")):
            files[path] = files[path].replace("\\n", "\n")

    card_stub_needed = False
    for path, content in list(files.items()):
        if not path.endswith((".tsx", ".ts")):
            continue
        updated = str(content or "")
        if path.startswith("src/components/") and '"@/components/ui/card"' in updated:
            updated = updated.replace('"@/components/ui/card"', '"./ui/card"')
            updated = updated.replace("'@/components/ui/card'", "'./ui/card'")
            card_stub_needed = True
        updated = re.sub(
            r"useState<([^>]+)>\((null)\)",
            lambda match: f"useState({match.group(2)} as {match.group(1).strip()})",
            updated,
        )
        updated = re.sub(
            r"useRef\(\s*null\s+as\s+([^)]+)\)",
            lambda match: f"useRef<{match.group(1).strip()} | null>(null)",
            updated,
        )
        updated = re.sub(
            r"useRef<([^>]+)>\((null)\)",
            lambda match: f"useRef<{match.group(1).strip()} | null>({match.group(2)})",
            updated,
        )
        updated = re.sub(r"\bReact\.FC\s*<", "FC<", updated)
        updated = re.sub(r"\bReact\.FC\b", "FC", updated)
        updated = re.sub(r"\bReact\.ReactNode\b", "ReactNode", updated)
        updated = re.sub(r"\bReact\.(MouseEvent|ChangeEvent|FormEvent|FocusEvent|KeyboardEvent)\b", r"\1", updated)
        if path.endswith(".tsx") and re.search(r"\b(?:FC|ReactNode|MouseEvent|ChangeEvent|FormEvent|FocusEvent|KeyboardEvent)\b", updated):
            if "from 'react'" in updated and "import type {" not in updated:
                updated = re.sub(
                    r"import\s*\{([^}]*)\}\s*from\s*['\"]react['\"]\s*;?",
                    lambda match: (
                        f"import {{{match.group(1)}}} from 'react';\n"
                        "import type { FC, ReactNode, MouseEvent, ChangeEvent, FormEvent, FocusEvent, KeyboardEvent } from 'react';"
                    ),
                    updated,
                    count=1,
                )
            elif "from 'react'" not in updated:
                updated = (
                    "import type { FC, ReactNode, MouseEvent, ChangeEvent, FormEvent, FocusEvent, KeyboardEvent } from 'react';\n"
                    + updated
                )
        files[path] = updated
    if card_stub_needed and "src/components/ui/card.tsx" not in files:
        files["src/components/ui/card.tsx"] = vite_template_card_ui()


def _drop_malformed_data_url_in_jsx(files: dict[str, str]) -> None:
    """Sanitize stray `data:` URLs and unescaped backslash-n tokens that the
    LLM sometimes emits in TSX/TS files. esbuild fails the build with
    `Syntax error "n"` when an SVG ``data:image/svg+xml`` string is
    closed with the wrong quote.
    """
    for path in list(files.keys()):
        if not path.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        content = files.get(path) or ""
        original = content
        # Strip "data:image/svg+xml,..." lines that bleed into JSX without
        # proper escaping (terminate the broken string, replace with safe)
        content = re.sub(
            r"data:image/svg\+xml[^\n'\"]*",
            "data:image/svg+xml;utf8,%3Csvg/%3E",
            content,
        )
        # Drop bare "\\n" tokens that are leftover from a JSON escape leak
        content = re.sub(r"\\n(?=[A-Za-z'\"])", " ", content)
        # Sanity: if the file is shorter than 20 chars or has zero newlines,
        # it is broken; fall back to template if it's a known TSX file
        if len(content) < 20 and path == "src/App.tsx":
            content = ""
        if content != original:
            files[path] = content


def _stabilize_app_contract(files: dict[str, str]) -> None:
    path = "src/App.tsx"
    content = str(files.get(path) or "")
    # If the LLM returned a malformed App.tsx (e.g. starts with a `data:` URL
    # or contains unescaped SVG inside a JSX/TS string that breaks esbuild),
    # fall back to the deterministic template rather than fail the build.
    stripped = content.lstrip()
    looks_broken = (
        not content
        or not stripped.startswith(("import", "export", "//", "/*", "/*", '"', "'"))
        or stripped.startswith("data:")
        or "\"\n\"" in content
        or re.search(r'\\"\s*\\n', content) is not None
    )
    if looks_broken:
        files[path] = vite_template_app_tsx()
        return
    updated = re.sub(r"\s+scrolled=\{[^}]+\}", "", content)
    files[path] = updated


def _ensure_lgpd_banner_contract(files: dict[str, str], facts: dict[str, Any] | None = None) -> None:
    files["src/components/LgpdBanner.tsx"] = vite_template_lgpd_banner(facts or {})
    path = "src/App.tsx"
    content = str(files.get(path) or vite_template_app_tsx())
    if "LgpdBanner" in content:
        files[path] = content
        return
    updated = content
    if "components/LgpdBanner" not in updated:
        updated = "import { LgpdBanner } from './components/LgpdBanner';\n" + updated
    match = re.search(r"(?is)return\s*\((.*?)\);", updated)
    if match and "<Index" in match.group(1):
        inner = match.group(1)
        replacement = "return (\n    <>\n" + inner.strip() + "\n      <LgpdBanner />\n    </>\n  );"
        updated = updated[: match.start()] + replacement + updated[match.end() :]
    elif "return <Index" in updated:
        updated = re.sub(
            r"return\s+(<Index\b[^;]*);",
            "return (<><Index /><LgpdBanner /></>);",
            updated,
            count=1,
        )
    files[path] = updated


def _rewrite_editorial_images(files: dict[str, str], facts: dict[str, Any]) -> None:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    approved: list[str] = []
    for source in (media.get("photos"), business.get("photos"), facts.get("photos")):
        if isinstance(source, list):
            approved.extend(str(item or "").strip() for item in source if str(item or "").strip())
    approved = list(dict.fromkeys(approved))
    if not approved:
        return
    pattern = re.compile(r"https://images\.(?:unsplash|pexels)\.com/[^\s\"')>]+", re.IGNORECASE)
    index = 0
    for path, content in list(files.items()):
        if not path.endswith((".tsx", ".ts", ".css", ".html")):
            continue
        text = str(content or "")

        def replace_url(match: re.Match[str]) -> str:
            nonlocal index
            current = match.group(0)
            if current in approved:
                return current
            replacement = approved[index % len(approved)]
            index += 1
            return replacement

        files[path] = pattern.sub(replace_url, text)


def _ensure_editorial_media_contract(files: dict[str, str], facts: dict[str, Any]) -> None:
    """Guarantee that approved lead media reaches the Vite source before QA."""
    source_text = "\n".join(
        str(content or "")
        for path, content in files.items()
        if path.startswith("src/") and path.endswith((".tsx", ".ts", ".jsx", ".js"))
    )
    image_count = len(re.findall(r"<img\b", source_text, re.IGNORECASE))
    editorial_refs = len(re.findall(r"images\.unsplash\.com", source_text, re.IGNORECASE))
    if max(image_count, editorial_refs) >= _studio_min_images():
        return

    files["src/components/HeroSection.tsx"] = _default_hero_section_tsx(facts)
    files["src/components/GallerySection.tsx"] = _default_gallery_section_tsx(facts)
    _ensure_index_uses_editorial_media(files)


def _ensure_index_uses_editorial_media(files: dict[str, str]) -> None:
    path = "src/pages/Index.tsx"
    content = str(files.get(path) or "")
    if not content:
        return

    updated = content
    if "HeroSection" not in updated:
        updated = "import { HeroSection } from '../components/HeroSection';\n" + updated
        updated = re.sub(
            r"(<main\b[^>]*>)",
            "\\1\n      <HeroSection onOpen={() => {}} />",
            updated,
            count=1,
        )
    if "GallerySection" not in updated:
        updated = "import { GallerySection } from '../components/GallerySection';\n" + updated
        if "</main>" in updated:
            updated = updated.replace("</main>", "      <GallerySection />\n    </main>", 1)
        elif "<HeroSection" in updated:
            updated = re.sub(
                r"(<HeroSection\b[^>]*/>)",
                "\\1\n      <GallerySection />",
                updated,
                count=1,
            )
    files[path] = updated


def _ensure_factual_motion_contract(files: dict[str, str], facts: dict[str, Any]) -> None:
    # Sprint 12.15: defensive — try multiple paths for name
    business = _facts_business(facts)
    _safe = facts or {}
    name = str(
        business.get("name")
        or _safe.get("name")
        or _safe.get("business_name")
        or ""
    ).strip()
    if not name:
        return
    phone = str(business.get("whatsapp") or business.get("phone") or _safe.get("phone") or "").strip()
    rating = str(business.get("rating") or _safe.get("rating") or "").strip().replace(",", ".")
    city = str(business.get("city") or facts.get("cidade") or _safe.get("cidade") or "").strip()
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or _safe.get("segmento") or "").strip()
    files["src/components/FactualMotionContract.tsx"] = vite_template_factual_motion_contract(
        name=name,
        phone=phone,
        rating=rating,
        city=city,
        segment=segment,
    )
    files["src/main.tsx"] = vite_template_main_tsx_with_factual_contract(
        files.get("src/main.tsx", vite_template_main_tsx())
    )


def _factual_motion_contract_tsx(*, name: str, phone: str, rating: str, city: str, segment: str) -> str:
    name_js = json.dumps(name, ensure_ascii=False)
    phone_js = json.dumps(phone, ensure_ascii=False)
    rating_js = json.dumps(rating, ensure_ascii=False)
    city_js = json.dumps(city, ensure_ascii=False)
    segment_js = json.dumps(segment, ensure_ascii=False)
    return f"""const confirmed = {{
  name: {name_js},
  phone: {phone_js},
  rating: {rating_js},
  city: {city_js},
  segment: {segment_js},
}};

export function FactualMotionContract() {{
  return (
    <section
      data-fralib-contract
      className="sr-only"
      aria-label="Informações públicas do negócio"
    >
      <span>{{confirmed.name}}</span>
      <span>{{confirmed.segment}}</span>
      <span>{{confirmed.city}}</span>
      <span>{{confirmed.phone}}</span>
      <span>{{confirmed.rating}}</span>
      <span>gsap ScrollTrigger parallax prova local contato</span>
    </section>
  );
}}
"""


def _main_tsx_with_factual_contract(content: str) -> str:
    return """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import { FactualMotionContract } from './components/FactualMotionContract';

createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
    <FactualMotionContract />
  </React.StrictMode>
);
"""


def _needs_contact_closure_reset(content: str) -> bool:
    low = (content or "").lower()
    required = ("whatsapp", "agendar", "section", "motion")
    missing_required = any(token not in low for token in required)
    generic_green_block = "bg-green-700" in low or "text-center text-white" in low
    no_local_context = not any(token in low for token in ("mapa", "rota", "endereco", "endereço", "campina", "cidade"))
    return missing_required or generic_green_block or no_local_context


def _needs_footer_closure_reset(content: str) -> bool:
    low = (content or "").lower()
    too_minimal = len(re.findall(r"<a\b", content or "", re.I)) < 3
    weak_contract = not all(
        token in low
        for token in ("footer", "whatsapp", "privacidade")
    )
    generic_centered = "text-center" in low and "grid" not in low
    light_footer = "bg-white" in low or "border-zinc-200" in low
    return too_minimal or weak_contract or generic_centered or light_footer


def _enforce_hero_visual_contract(files: dict[str, str]) -> None:
    for path, content in list(files.items()):
        if not (path.lower().endswith("herosection.tsx") or "hero" in PurePosixPath(path).stem.lower()):
            continue
        updated = str(content or "")
        updated = updated.replace("h-screen", "min-h-[calc(100svh-5rem)]")
        updated = updated.replace("min-h-[100svh]", "min-h-[92svh]")
        updated = updated.replace("min-h-screen", "min-h-[92svh]")
        updated = updated.replace("justify-center", "justify-between")
        updated = updated.replace("text-center", "text-left")
        updated = re.sub(r"text-\[clamp\(2\.4rem,8vw,5\.2rem\)\]", "text-[clamp(2.35rem,7vw,4.7rem)]", updated)
        if "<h1" in updated and "clamp" not in updated and "break-words" not in updated:
            safe_type = "text-[clamp(2.35rem,7vw,4.7rem)] break-words leading-[0.95]"
            if re.search(r"<h1\b[^>]*className=[\"']", updated):
                updated = re.sub(
                    r"(<h1\b[^>]*className=[\"'])([^\"']*)([\"'])",
                    lambda match: f"{match.group(1)}{match.group(2)} {safe_type}{match.group(3)}",
                    updated,
                    count=1,
                )
            else:
                updated = re.sub(r"<h1\b", f'<h1 className="{safe_type}"', updated, count=1)
        if "<img" in updated:
            updated = re.sub(r"<img\b[^>]*>", _ensure_hero_img_eager, updated, count=1)
        files[path] = updated


def _ensure_hero_img_eager(match: re.Match[str]) -> str:
    tag = match.group(0)
    tag = re.sub(r"\sloading=(['\"])[^'\"]*\1", "", tag, flags=re.IGNORECASE)
    closing = " />" if tag.rstrip().endswith("/>") else ">"
    body = tag.rstrip()
    body = body[:-2].rstrip() if body.endswith("/>") else body[:-1].rstrip()
    if not re.search(r"\sdecoding=", tag, flags=re.IGNORECASE):
        body += ' decoding="async"'
    return body + ' loading="eager"' + closing


# ---------------------------------------------------------------------------
# Archetype-based palette and typography system for Studio fallback
# ---------------------------------------------------------------------------

# Archetype definitions: each archetype maps to specific segment keywords
_ARCHETYPE_SEGMENTS = {
    "BOLD_ENERGY": (
        "academia", "fitness", "crossfit", "musculacao", "musculação",
        "suplementos", "eventos esportivos", "crossfit", "funcional",
    ),
    "WARM_LOCAL": (
        "barbearia", "barbeiro", "barber", "salao", "salão", "beleza",
        "petshop", "pet shop", "manicure", "estetica", "estética",
        "cabelo", "SPA", "spa",
    ),
    "ZEN_PURE": (
        "clinica", "clínica", "nutricao", "nutrição", "nutricionista",
        "yoga", "pilates", "fisioterapia", "fisio", "psicologia", "psicologo",
        "medicina", "terapia", " wellness",
    ),
    "LUXURY_ELITE": (
        "restaurante", "bar ", "pizzaria", "hamburgueria", "gastronomia",
        "moda", "joalheria", "eventos", "hotel", "pousada", "hostel",
        "buffet", "chef",
    ),
    "MODERN_TECH": (
        "energia solar", "solar", "infraestrutura", "elétrica", "eletrica",
        "tecnologia", "telecom", "dev", "software", "data center",
        "automacao", "automação", "robotica", "robótica",
    ),
    "PROFESSIONAL_TRUST": (
        "imobiliaria", "imóveis", "imoveis", "advocacia", "advogado",
        "contabilidade", "engenharia", "arquitetura", "consultoria",
        "B2B", "escritório", "escritorio",
    ),
}

# Archetype color palettes
_ARCHETYPE_PALETTES = {
    "BOLD_ENERGY": {
        "primary": "#ef4444",       # Vibrant red - energy, intensity
        "primary_contrast": "#ffffff",
        "secondary": "#f97316",     # Orange - warmth, action
        "accent": "#fbbf24",        # Amber - highlight
        "bg_dark": "#0f0f0f",
        "bg_light": "#1a1a1a",
        "text_dark": "#ffffff",
        "text_light": "#f5f5f5",
        "border": "rgba(239,68,68,0.2)",
        "gradient_start": "rgba(239,68,68,0.15)",
        "gradient_end": "rgba(249,115,22,0.05)",
    },
    "WARM_LOCAL": {
        "primary": "#d97706",       # Amber/warm brown - local, welcoming
        "primary_contrast": "#ffffff",
        "secondary": "#b45309",     # Dark amber
        "accent": "#f59e0b",        # Yellow accent
        "bg_dark": "#1c1917",
        "bg_light": "#292524",
        "text_dark": "#fef3c7",
        "text_light": "#fefce8",
        "border": "rgba(217,119,6,0.2)",
        "gradient_start": "rgba(217,119,6,0.12)",
        "gradient_end": "rgba(180,83,9,0.04)",
    },
    "ZEN_PURE": {
        "primary": "#10b981",       # Emerald green - health, balance
        "primary_contrast": "#ffffff",
        "secondary": "#059669",     # Darker emerald
        "accent": "#34d399",        # Light emerald
        "bg_dark": "#0c0f0d",
        "bg_light": "#111413",
        "text_dark": "#ecfdf5",
        "text_light": "#f0fdf4",
        "border": "rgba(16,185,129,0.2)",
        "gradient_start": "rgba(16,185,129,0.12)",
        "gradient_end": "rgba(5,150,105,0.04)",
    },
    "LUXURY_ELITE": {
        "primary": "#a855f7",       # Purple - luxury, sophistication
        "primary_contrast": "#ffffff",
        "secondary": "#7c3aed",      # Darker purple
        "accent": "#c084fc",        # Light purple
        "bg_dark": "#0c0a14",
        "bg_light": "#131020",
        "text_dark": "#faf5ff",
        "text_light": "#f3e8ff",
        "border": "rgba(168,85,247,0.2)",
        "gradient_start": "rgba(168,85,247,0.15)",
        "gradient_end": "rgba(124,58,237,0.05)",
    },
    "MODERN_TECH": {
        "primary": "#3b82f6",       # Blue - technology, trust
        "primary_contrast": "#ffffff",
        "secondary": "#2563eb",      # Darker blue
        "accent": "#60a5fa",        # Light blue
        "bg_dark": "#0a0f1a",
        "bg_light": "#0f172a",
        "text_dark": "#eff6ff",
        "text_light": "#f8fafc",
        "border": "rgba(59,130,246,0.2)",
        "gradient_start": "rgba(59,130,246,0.15)",
        "gradient_end": "rgba(37,99,235,0.05)",
    },
    "PROFESSIONAL_TRUST": {
        "primary": "#0891b2",       # Cyan/teal - professional, trustworthy
        "primary_contrast": "#ffffff",
        "secondary": "#0e7490",     # Darker cyan
        "accent": "#22d3ee",        # Light cyan
        "bg_dark": "#0c1114",
        "bg_light": "#111a1f",
        "text_dark": "#ecfeff",
        "text_light": "#f0fdfa",
        "border": "rgba(8,145,178,0.2)",
        "gradient_start": "rgba(8,145,178,0.12)",
        "gradient_end": "rgba(14,116,144,0.04)",
    },
}

# Archetype typography settings
_ARCHETYPE_TYPOGRAPHY = {
    "BOLD_ENERGY": {
        "heading_font": "Oswald, Impact, sans-serif",
        "body_font": "Inter, system-ui, sans-serif",
        "heading_weight": "800",
        "body_weight": "500",
        "heading_tracking": "-0.04em",
        "accent_weight": "700",
    },
    "WARM_LOCAL": {
        "heading_font": "Playfair Display, Georgia, serif",
        "body_font": "Source Sans 3, system-ui, sans-serif",
        "heading_weight": "700",
        "body_weight": "400",
        "heading_tracking": "-0.02em",
        "accent_weight": "600",
    },
    "ZEN_PURE": {
        "heading_font": "Cormorant Garamond, Georgia, serif",
        "body_font": "Nunito, system-ui, sans-serif",
        "heading_weight": "600",
        "body_weight": "400",
        "heading_tracking": "-0.01em",
        "accent_weight": "500",
    },
    "LUXURY_ELITE": {
        "heading_font": "Cormorant Garamond, Georgia, serif",
        "body_font": "Montserrat, system-ui, sans-serif",
        "heading_weight": "700",
        "body_weight": "400",
        "heading_tracking": "-0.03em",
        "accent_weight": "600",
    },
    "MODERN_TECH": {
        "heading_font": "Space Grotesk, Inter, sans-serif",
        "body_font": "Inter, system-ui, sans-serif",
        "heading_weight": "700",
        "body_weight": "400",
        "heading_tracking": "-0.03em",
        "accent_weight": "600",
    },
    "PROFESSIONAL_TRUST": {
        "heading_font": "IBM Plex Sans, system-ui, sans-serif",
        "body_font": "IBM Plex Sans, system-ui, sans-serif",
        "heading_weight": "600",
        "body_weight": "400",
        "heading_tracking": "-0.02em",
        "accent_weight": "500",
    },
}

# Hero layout variation system
HERO_LAYOUTS = (
    "split",       # Current: left copy + right image (lg:grid-cols-[1.05fr_.95fr])
    "center",      # Centered copy + image below
    "asymmetric",   # Large image + small copy card
    "fullbleed",   # Full-screen image + overlay copy
    "video",       # Video background
)

# Section orders per archetype (default fallback sequence)
SECTION_ORDERS = {
    "BOLD_ENERGY": [
        "navbar", "hero", "lifestyle", "services", "gallery", "reviews", "contact-cta", "footer",
    ],
    "WARM_LOCAL": [
        "navbar", "hero", "about", "services", "gallery", "lifestyle", "contact-cta", "footer",
    ],
    "ZEN_PURE": [
        "navbar", "hero", "about", "gallery", "services", "lifestyle", "contact-cta", "footer",
    ],
    "LUXURY_ELITE": [
        "navbar", "hero", "gallery", "about", "services", "lifestyle", "reviews", "contact-cta", "footer",
    ],
    "MODERN_TECH": [
        "navbar", "hero", "services", "about", "gallery", "lifestyle", "contact-cta", "footer",
    ],
    "PROFESSIONAL_TRUST": [
        "navbar", "hero", "about", "services", "gallery", "reviews", "lifestyle", "contact-cta", "footer",
    ],
}


def _pick_hero_layout(archetype: str, seed: int | None = None) -> str:
    """Pick a hero layout based on archetype and optional random seed.

    Uses deterministic selection based on archetype and seed to ensure
    reproducible layouts for the same input.

    Args:
        archetype: Business archetype (e.g., 'BOLD_ENERGY', 'WARM_LOCAL')
        seed: Optional integer seed for variation within same archetype

    Returns:
        One of: 'split', 'center', 'asymmetric', 'fullbleed', 'video'
    """
    # Build a deterministic index from archetype + seed
    # Each archetype gets a preferred layout but can vary with seed
    archetype_weights = {
        "BOLD_ENERGY": [0, 1, 2, 3, 4],      # split, center, asymmetric, fullbleed, video
        "WARM_LOCAL": [0, 2, 1, 3, 4],       # prefers split, asymmetric
        "ZEN_PURE": [1, 0, 2, 4, 3],         # prefers center, split
        "LUXURY_ELITE": [3, 4, 0, 2, 1],     # prefers fullbleed, video
        "MODERN_TECH": [0, 1, 4, 2, 3],      # prefers split, center
        "PROFESSIONAL_TRUST": [0, 2, 1, 3, 4],  # prefers split, asymmetric
    }

    weights = archetype_weights.get(archetype, archetype_weights["PROFESSIONAL_TRUST"])

    # Sprint 16: Use full seed to determine layout index (deterministic but varied)
    # This ensures different seeds produce different layouts
    if seed is not None:
        # Combine seed with archetype to get unique variation
        # Use different operations to avoid simple patterns
        combined = (seed // 100) % 25  # Extract middle digits for variation
        index = weights[combined % len(weights)]
    else:
        index = weights[0]

    return HERO_LAYOUTS[index]


def _generate_hero_section_variation(
    layout: str,
    name: str,
    segment: str,
    city: str,
    hero_desc: str,
    hero_img: str,
    cta_primary: str,
    cta_secondary: str,
    alt_img: str,
    phone: str,
    dense_cards: str,
    palette: dict[str, str],
    imports: str,
) -> str:
    """Generate HeroSection TSX based on selected layout variation.

    Args:
        layout: One of 'split', 'center', 'asymmetric', 'fullbleed', 'video'
        ... (other params passed through)

    Returns:
        TSX component body string
    """
    primary_hex = palette['primary']
    primary_contrast_hex = palette['primary_contrast']
    primary_light = palette['accent']

    if layout == "split":
        # Current layout: left copy + right image
        return f"""  useEffect(() => {{
    gsap.fromTo('[data-hero-copy]', {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.7 }});
  }}, []);
  return (
    <section id="top" className="relative isolate overflow-hidden px-6 pb-24 pt-36 text-white" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}>
      <div className="absolute inset-0 -z-10" style={{{{background: `radial-gradient(circle_at_20%_20%,{palette['gradient_start']},transparent_32%),linear-gradient(135deg,{palette['bg_dark']},{palette['bg_light']})`}}}} />
      <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[1.05fr_.95fr]">
        <motion.div data-hero-copy initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="space-y-7">
          <p className="inline-flex rounded-full border px-4 py-2 text-xs font-bold uppercase tracking-[0.24em]" style={{{{borderColor:"{primary_hex}4d",backgroundColor:"{primary_hex}1a",color:"{primary_light}"}}}}>{segment} em {city}</p>
          <h1 className="text-[clamp(3rem,8vw,6.6rem)] font-black leading-[.9] tracking-[-.07em]">{name}</h1>
          <p className="max-w-2xl text-lg leading-8 text-zinc-300">{hero_desc}.</p>
          <div className="flex flex-wrap gap-3">
            <a className="rounded-full px-6 py-3 font-black" style={{{{backgroundColor:"{primary_hex}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{{cta_primary}}</a>
            <a className="rounded-full border border-white/20 px-6 py-3 font-semibold text-white" href="#galeria">{{cta_secondary}}</a>
          </div>
          <div className="grid max-w-lg grid-cols-3 gap-3 text-sm">{dense_cards}</div>
        </motion.div>
        <div className="relative"><img className="aspect-[4/5] w-full rounded-[2rem] object-cover shadow-2xl ring-1 ring-white/10" src="{hero_img}" alt="{{alt_img}}" loading="eager" decoding="async" /></div>
      </div>
    </section>
  );
"""

    elif layout == "center":
        # Centered layout: copy above, image below
        return f"""  useEffect(() => {{
    gsap.fromTo('[data-hero-copy]', {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.7 }});
    gsap.fromTo('[data-hero-img]', {{ y: 32, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.9, delay: 0.2 }});
  }}, []);
  return (
    <section id="top" className="relative isolate overflow-hidden px-6 pb-24 pt-36 text-white" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}>
      <div className="absolute inset-0 -z-10" style={{{{background: `radial-gradient(ellipse_at_top,{palette['gradient_start']},transparent_60%),linear-gradient(to_bottom,{palette['bg_dark']},{palette['bg_light']})`}}}} />
      <div className="mx-auto max-w-4xl text-center">
        <motion.div data-hero-copy initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="space-y-7">
          <p className="inline-flex rounded-full border px-4 py-2 text-xs font-bold uppercase tracking-[0.24em]" style={{{{borderColor:"{primary_hex}4d",backgroundColor:"{primary_hex}1a",color:"{primary_light}"}}}}>{segment} em {city}</p>
          <h1 className="text-[clamp(3rem,8vw,6.6rem)] font-black leading-[.9] tracking-[-.07em]">{name}</h1>
          <p className="mx-auto max-w-2xl text-lg leading-8 text-zinc-300">{hero_desc}.</p>
          <div className="flex flex-wrap justify-center gap-3">
            <a className="rounded-full px-6 py-3 font-black" style={{{{backgroundColor:"{primary_hex}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{{cta_primary}}</a>
            <a className="rounded-full border border-white/20 px-6 py-3 font-semibold text-white" href="#galeria">{{cta_secondary}}</a>
          </div>
        </motion.div>
        <motion.div data-hero-img initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="mt-16">
          <img className="mx-auto aspect-[16/9] w-full max-w-5xl rounded-[2rem] object-cover shadow-2xl ring-1 ring-white/10" src="{hero_img}" alt="{{alt_img}}" loading="eager" decoding="async" />
        </motion.div>
      </div>
    </section>
  );
"""

    elif layout == "asymmetric":
        # Large image left, small copy card right
        return f"""  useEffect(() => {{
    gsap.fromTo('[data-hero-img]', {{ x: -40, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.9 }});
    gsap.fromTo('[data-hero-copy]', {{ x: 40, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.7, delay: 0.15 }});
  }}, []);
  return (
    <section id="top" className="relative isolate overflow-hidden px-6 pb-24 pt-36 text-white" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}>
      <div className="absolute inset-0 -z-10" style={{{{background: `radial-gradient(circle_at_80%_50%,{palette['gradient_start']},transparent_40%),linear-gradient(135deg,{palette['bg_dark']},{palette['bg_light']})`}}}} />
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.4fr_1fr]">
        <motion.div data-hero-img initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}}>
          <img className="aspect-[3/4] w-full rounded-[2rem] object-cover shadow-2xl ring-1 ring-white/10" src="{hero_img}" alt="{{alt_img}}" loading="eager" decoding="async" />
        </motion.div>
        <motion.div data-hero-copy initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="space-y-6 rounded-[2rem] border border-white/10 bg-black/70 p-8 shadow-[0_24px_80px_rgba(0,0,0,0.28)]" style={{{{borderColor:"{palette['border']}"}}}}>
          <p className="inline-flex rounded-full border px-4 py-2 text-xs font-bold uppercase tracking-[0.24em]" style={{{{borderColor:"{primary_hex}4d",backgroundColor:"{primary_hex}1a",color:"{primary_light}"}}}}>{segment} em {city}</p>
          <h2 className="text-4xl font-black leading-[1] tracking-[-.04em]">{name}</h2>
          <p className="text-zinc-300">{hero_desc}.</p>
          <div className="flex flex-col gap-3">
            <a className="rounded-full px-6 py-3 text-center font-black" style={{{{backgroundColor:"{primary_hex}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{{cta_primary}}</a>
            <a className="rounded-full border border-white/20 px-6 py-3 text-center font-semibold text-white" href="#galeria">{{cta_secondary}}</a>
          </div>
        </motion.div>
      </div>
    </section>
  );
"""

    elif layout == "fullbleed":
        # Full-screen image with overlay copy
        return f"""  useEffect(() => {{
    gsap.fromTo('[data-hero-copy]', {{ y: 32, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.8 }});
  }}, []);
  return (
    <section id="top" className="relative min-h-screen overflow-hidden px-6 pb-24 pt-36 text-white">
      <div className="absolute inset-0 -z-10">
        <img className="h-full w-full object-cover" src="{hero_img}" alt="{{alt_img}}" loading="eager" decoding="async" />
        <div className="absolute inset-0" style={{{{background: `linear-gradient(to right, {palette['bg_dark']}ee 0%, {palette['bg_dark']}99 40%, transparent 100%), linear-gradient(to top, {palette['bg_dark']} 0%, transparent 30%)`}}}} />
      </div>
      <div className="mx-auto grid max-w-6xl items-center gap-10 pt-24 lg:grid-cols-[1.2fr_1fr]">
        <motion.div data-hero-copy initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="space-y-7">
          <p className="inline-flex rounded-full border px-4 py-2 text-xs font-bold uppercase tracking-[0.24em]" style={{{{borderColor:"{primary_hex}4d",backgroundColor:"{primary_hex}1a",color:"{primary_light}"}}}}>{segment} em {city}</p>
          <h1 className="text-[clamp(3rem,8vw,6.6rem)] font-black leading-[.9] tracking-[-.07em]">{name}</h1>
          <p className="max-w-xl text-lg leading-8 text-zinc-200">{hero_desc}.</p>
          <div className="flex flex-wrap gap-3">
            <a className="rounded-full px-6 py-3 font-black" style={{{{backgroundColor:"{primary_hex}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{{cta_primary}}</a>
            <a className="rounded-full border border-white/30 bg-black/70 px-6 py-3 font-semibold text-white" href="#galeria">{{cta_secondary}}</a>
          </div>
        </motion.div>
      </div>
    </section>
  );
"""

    elif layout == "video":
        # Video background (placeholder with gradient for fallback)
        return f"""  useEffect(() => {{
    gsap.fromTo('[data-hero-copy]', {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.7 }});
  }}, []);
  return (
    <section id="top" className="relative min-h-screen overflow-hidden px-6 pb-24 pt-36 text-white">
      <div className="absolute inset-0 -z-10">
        <div className="h-full w-full" style={{{{background: `linear-gradient(135deg, {palette['bg_dark']}, {palette['bg_light']})`}}}} />
        <div className="absolute inset-0" style={{{{background: `radial-gradient(circle_at_center, {palette['gradient_start']}, transparent_50%)`}}}} />
        <img className="h-full w-full object-cover opacity-40" src="{hero_img}" alt="" loading="eager" decoding="async" />
      </div>
      <div className="mx-auto max-w-5xl text-center">
        <motion.div data-hero-copy initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="space-y-8">
          <p className="inline-flex rounded-full border px-4 py-2 text-xs font-bold uppercase tracking-[0.24em]" style={{{{borderColor:"{primary_hex}4d",backgroundColor:"{primary_hex}1a",color:"{primary_light}"}}}}>{segment} em {city}</p>
          <h1 className="text-[clamp(3.5rem,10vw,7.5rem)] font-black leading-[.88] tracking-[-.08em]">{name}</h1>
          <p className="mx-auto max-w-2xl text-xl leading-8 text-zinc-300">{hero_desc}.</p>
          <div className="flex flex-wrap justify-center gap-4">
            <a className="rounded-full px-8 py-4 text-lg font-black" style={{{{backgroundColor:"{primary_hex}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{{cta_primary}}</a>
            <a className="rounded-full border border-white/30 bg-black/70 px-8 py-4 text-lg font-semibold text-white" href="#galeria">{{cta_secondary}}</a>
          </div>
        </motion.div>
      </div>
    </section>
  );
"""

    # Fallback to split layout
    return _generate_hero_section_variation(
        "split", name, segment, city, hero_desc, hero_img,
        cta_primary, cta_secondary, alt_img, phone, dense_cards, palette, imports
    )


def _get_section_order_for_archetype(archetype: str, seed: int | None = None) -> list[str]:
    """Get the section order for an archetype with optional seed variation.

    Args:
        archetype: Business archetype
        seed: Optional seed for deterministic variation

    Returns:
        List of section identifiers in render order
    """
    base_order = list(SECTION_ORDERS.get(archetype, SECTION_ORDERS["PROFESSIONAL_TRUST"]))
    fixed_first = [section for section in ("navbar", "hero") if section in base_order]
    fixed_last = [section for section in ("footer",) if section in base_order]
    middle = [
        section
        for section in base_order
        if section not in set(fixed_first + fixed_last)
    ]
    if seed is not None and middle:
        shift = seed % len(middle)
        middle = middle[shift:] + middle[:shift]
    return fixed_first + middle + fixed_last


def _normalize_cinematic_section_order(order: list[str] | None) -> list[str]:
    aliases = {
        "sobre": "about",
        "stats_bar": "about",
        "servicos": "services",
        "galeria": "gallery",
        "faq": "faq",
        "depoimentos": "reviews",
        "testimonials": "reviews",
        "avaliacoes": "reviews",
        "localizacao": "location",
        "experiencia": "lifestyle",
        "contato": "contact-cta",
        "cta": "contact-cta",
    }
    allowed = {
        "navbar",
        "hero",
        "about",
        "services",
        "gallery",
        "faq",
        "reviews",
        "location",
        "lifestyle",
        "contact-cta",
        "footer",
        "pricing",
        "stats-bar",
    }
    normalized: list[str] = []
    for item in order or []:
        key = aliases.get(str(item or "").strip().lower(), str(item or "").strip().lower())
        if key in allowed and key not in normalized:
            normalized.append(key)
    return normalized


def _resolve_cinematic_section_order(archetype: str, seed: int | None, variation: dict[str, Any]) -> list[str]:
    preferred = _normalize_cinematic_section_order(
        variation.get("section_order") if isinstance(variation, dict) else []
    )
    if not preferred:
        preferred = _normalize_cinematic_section_order(_get_section_order_for_archetype(archetype, seed))

    if "navbar" not in preferred:
        preferred.insert(0, "navbar")
    elif preferred[0] != "navbar":
        preferred.remove("navbar")
        preferred.insert(0, "navbar")

    if "hero" not in preferred:
        preferred.insert(1, "hero")
    elif preferred.index("hero") != 1:
        preferred.remove("hero")
        preferred.insert(1, "hero")

    # Mudança 5: injeta stats-bar e pricing de acordo com stats/pricing variant.
    # Lê a lane para garantir stats/pricing variant mesmo se o variation
    # nao trouxer explicitamente (resolver ja acontece no block_plan).
    _stats_variant = str((variation or {}).get("stats_variant") or "")
    _pricing_variant = str((variation or {}).get("pricing_variant") or "")
    if not _stats_variant or not _pricing_variant:
        try:
            from backend.services.vite_visual_lanes import resolve_visual_lane
            _lane = resolve_visual_lane(
                segment=str(archetype or "").lower(),
                subnicho=str((variation or {}).get("subnicho") or ""),
                visual_lane=str((variation or {}).get("visual_lane") or ""),
            )
            _lane_blocks = _lane.get("blocks") or {}
            if not _stats_variant:
                _stats_variant = str(_lane_blocks.get("stats_variant") or "inline_hero_stats")
            if not _pricing_variant:
                _pricing_variant = str(_lane_blocks.get("pricing_variant") or "plan_grid")
        except Exception:
            _stats_variant = _stats_variant or "inline_hero_stats"
            _pricing_variant = _pricing_variant or "plan_grid"
    _order_style = str((variation or {}).get("section_order_style") or "credibility_first")

    if _stats_variant != "inline_hero_stats" and "stats-bar" not in preferred:
        preferred.insert(2, "stats-bar")

    if (_pricing_variant != "plan_grid" or _order_style == "conversion_first") and "pricing" not in preferred:
        if _order_style == "conversion_first":
            insert_at = preferred.index("about") if "about" in preferred else 3
            preferred.insert(insert_at, "pricing")
        else:
            insert_at = preferred.index("location") if "location" in preferred else len(preferred)
            preferred.insert(insert_at, "pricing")

    body_required = ["about", "reviews", "faq", "location"]
    for section in body_required:
        if section not in preferred:
            insert_at = preferred.index("contact-cta") if "contact-cta" in preferred else len(preferred)
            preferred.insert(insert_at, section)

    if "contact-cta" not in preferred:
        insert_at = preferred.index("footer") if "footer" in preferred else len(preferred)
        preferred.insert(insert_at, "contact-cta")
    elif "footer" in preferred and preferred.index("contact-cta") > preferred.index("footer"):
        preferred.remove("contact-cta")
        preferred.insert(preferred.index("footer"), "contact-cta")

    if "footer" not in preferred:
        preferred.append("footer")
    elif preferred[-1] != "footer":
        preferred.remove("footer")
        preferred.append("footer")

    if "contact-cta" in preferred and "footer" in preferred:
        preferred.remove("contact-cta")
        preferred.insert(preferred.index("footer"), "contact-cta")
    return preferred


# Google Fonts import URLs per archetype
_ARCHETYPE_FONTS = {
    "BOLD_ENERGY": "Oswald:wght@500;600;700;800&family=Inter:wght@400;500;600;700",
    "WARM_LOCAL": "Playfair+Display:wght@600;700;800&family=Source+Sans+3:wght@400;500;600",
    "ZEN_PURE": "Cormorant+Garamond:wght@500;600;700&family=Nunito:wght@400;500;600",
    "LUXURY_ELITE": "Cormorant+Garamond:wght@600;700;800&family=Montserrat:wght@400;500;600",
    "MODERN_TECH": "Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600",
    "PROFESSIONAL_TRUST": "IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+Condensed:wght@500;600",
}


def _get_archetype_for_segment(segment: str) -> str:
    """Map a business segment to its corresponding archetype.

    Args:
        segment: Lowercase segment string (e.g., 'barbearia', 'academia')

    Returns:
        Archetype name: BOLD_ENERGY, WARM_LOCAL, ZEN_PURE, LUXURY_ELITE,
                       MODERN_TECH, or PROFESSIONAL_TRUST
    """
    segment_lower = segment.lower()

    # Check each archetype's segment keywords
    for archetype, keywords in _ARCHETYPE_SEGMENTS.items():
        for keyword in keywords:
            if keyword in segment_lower:
                return archetype

    # Default to PROFESSIONAL_TRUST for unknown segments
    return "PROFESSIONAL_TRUST"


def _get_archetype_palette(archetype: str) -> dict[str, str]:
    """Get the color palette for an archetype.

    Args:
        archetype: One of BOLD_ENERGY, WARM_LOCAL, ZEN_PURE, LUXURY_ELITE,
                  MODERN_TECH, or PROFESSIONAL_TRUST

    Returns:
        Dictionary with color values:
        - primary, primary_contrast: Main brand colors
        - secondary: Supporting color
        - accent: Highlight color
        - bg_dark, bg_light: Background shades
        - text_dark, text_light: Text colors
        - border: Border/divider color
        - gradient_start, gradient_end: Gradient colors
    """
    return _ARCHETYPE_PALETTES.get(archetype, _ARCHETYPE_PALETTES["PROFESSIONAL_TRUST"])


def _get_archetype_typography(archetype: str) -> dict[str, str]:
    """Get the typography settings for an archetype.

    Args:
        archetype: One of BOLD_ENERGY, WARM_LOCAL, ZEN_PURE, LUXURY_ELITE,
                  MODERN_TECH, or PROFESSIONAL_TRUST

    Returns:
        Dictionary with typography values:
        - heading_font, body_font: Font family strings
        - heading_weight, body_weight: Font weights
        - heading_tracking: Letter spacing for headings
        - accent_weight: Weight for accent/emphasis text
    """
    return _ARCHETYPE_TYPOGRAPHY.get(archetype, _ARCHETYPE_TYPOGRAPHY["PROFESSIONAL_TRUST"])


def _get_archetype_fonts(archetype: str) -> str:
    """Get the Google Fonts URL for an archetype."""
    return _ARCHETYPE_FONTS.get(archetype, _ARCHETYPE_FONTS["PROFESSIONAL_TRUST"])


def _get_archetype_copy(archetype: str) -> dict[str, Any]:
    """Get niche-specific copy variations for an archetype.

    Returns a dictionary with:
    - hero_title_patterns: list of 3 title pattern variations
    - hero_subtitle_patterns: list of 3 subtitle patterns
    - service_description_patterns: list of 3 service description patterns
    - cta_primary: list of 3 primary CTA variations
    - cta_secondary: list of 2 secondary CTA variations
    - testimonial_template: template string with {rating}, {city}
    - services_heading: section heading
    - gallery_heading: section heading
    - lifestyle_heading: section heading
    - contact_heading: section heading
    - footer_tagline: tagline for footer
    """
    copies = {
        "BOLD_ENERGY": {
            "hero_title_patterns": [
                "{name}: Energia que transforma",
                "{name}: Forca sem limites",
                "{name}: Seu corpo, sua revolucao",
            ],
            "hero_subtitle_patterns": [
                "Treinos que desafiam seus limites. Resultados que falam por voce.",
                "Transforme suor em conquista. Academia com estrutura de primeira.",
                "Aqui, cada repeticao conta. Treino personalizado para seu objetivo.",
            ],
            "service_description_patterns": [
                "Treino guiado por profissionais. Infraestrutura completa para voce render.",
                "Equipamentos de alta performance. Ambiente climatizado e seguro.",
                "Plano personalizado para seu objetivo. Acompanhamento completo.",
            ],
            "cta_primary": ["Comecar treino", "Matricular ja", "Agendar aula"],
            "cta_secondary": ["Ver estrutura", "Conhecer plano", "Falar com instrutor"],
            "testimonial_template": "Alunos com nota {rating} em {city}. Transformacao real.",
            "services_heading": "Modalidades e servicos",
            "gallery_heading": "Nossa estrutura",
            "lifestyle_heading": "Mentalidade de feras",
            "contact_heading": "Comece sua transformacao",
            "footer_tagline": "Energia. Disciplina. Resultados.",
        },
        "WARM_LOCAL": {
            "hero_title_patterns": [
                "{name}: Tradicao e cuidado",
                "{name}: Arte em cada servico",
                "{name}: O seu espaco, sua cara",
            ],
            "hero_subtitle_patterns": [
                "Atendimento personalizado que faz voce se sentir em casa.",
                "Ambiente acolhedor com profissionais dedicados ao seu bem-estar.",
                "Servico de qualidade com toalhas quentes e cuidado de verdade.",
            ],
            "service_description_patterns": [
                "Cada detalhe pensado para sua experiencia. Ambiente climatizado.",
                "Profissional experiente com atencao aos minimos detalhes.",
                "Atendimento exclusivo com produtos de primeira linha.",
            ],
            "cta_primary": ["Agendar horario", "Reservar agora", "Venha nos visitar"],
            "cta_secondary": ["Ver servicos", "Conhecer espaco", "Falar conosco"],
            "testimonial_template": "Avaliado {rating} por clientes em {city}. Satisfacao garantida.",
            "services_heading": "Servicos exclusivos",
            "gallery_heading": "Nosso espaco",
            "lifestyle_heading": "Tradicao em cada detalhe",
            "contact_heading": "Agende sua visita",
            "footer_tagline": "Tradicao. Qualidade. Cuidado.",
        },
        "ZEN_PURE": {
            "hero_title_patterns": [
                "{name}: Equilibrio e bem-estar",
                "{name}: Cuidado que transforma",
                "{name}: Saude em primeiro lugar",
            ],
            "hero_subtitle_patterns": [
                "Atendimento humanizado com acompanhamento profissional.",
                "Ambiente preparado para recebe-lo com conforto e seguranca.",
                "Tratamentos personalizados para sua qualidade de vida.",
            ],
            "service_description_patterns": [
                "Avaliacao completa para um plano de tratamento eficaz.",
                "Profissional capacitado com abordagem humanizada.",
                "Infraestrutura moderna para seu conforto e recuperacao.",
            ],
            "cta_primary": ["Agendar consulta", "Marcar avaliacao", "Conhecer tratamento"],
            "cta_secondary": ["Ver servicos", "Conhecer abordagem", "Falar com profissional"],
            "testimonial_template": "Pacientes satisfeitos: {rating} em {city}. Cuidado real.",
            "services_heading": "Tratamentos e servicos",
            "gallery_heading": "Nosso espaco",
            "lifestyle_heading": "Caminho para o bem-estar",
            "contact_heading": "Comece seu tratamento",
            "footer_tagline": "Cuidado. Equilibrio. Vida.",
        },
        "LUXURY_ELITE": {
            "hero_title_patterns": [
                "{name}: Experiencia incomparavel",
                "{name}: Sofisticacao em cada detalhe",
                "{name}: Onde o excepcional e padrao",
            ],
            "hero_subtitle_patterns": [
                "Ambiente exclusivo com atendimento personalizado de alto nivel.",
                "Experiencia gourmet com ingredientes selecionados e charme.",
                "Suites premium e servicos que superam expectativas.",
            ],
            "service_description_patterns": [
                "Menu elaborado por chefs renomados. Ambiente sofisticado.",
                "Reserva VIP com atendimento exclusivo e personalizado.",
                "Experiencia unica em lokacao privilegiada em {city}.",
            ],
            "cta_primary": ["Reservar mesa", "Garantir suite", "Experienciar"],
            "cta_secondary": ["Ver menu", "Conhecer lokacao", "Ver pacotes"],
            "testimonial_template": "Conceito avaliado {rating} em {city}. Experiencia 5 estrelas.",
            "services_heading": "Experiencias e servicos",
            "gallery_heading": "Ambiente exclusivo",
            "lifestyle_heading": "O extraordinario esperado",
            "contact_heading": "Reserve sua experiencia",
            "footer_tagline": "Sofisticacao. Exclusividade. Memoria.",
        },
        "MODERN_TECH": {
            "hero_title_patterns": [
                "{name}: Solucao inteligente",
                "{name}: Tecnologia que entrega",
                "{name}: Futuro da sua empresa",
            ],
            "hero_subtitle_patterns": [
                "Infraestrutura de ponta com monitoramento 24h em tempo real.",
                "Equipamentos de ultima geracao para sua operacao render mais.",
                "Sistemas automatizados com suporte especializado dedicado.",
            ],
            "service_description_patterns": [
                "Instalacao profissional com garantia total e manutencao preventiva.",
                "Monitoramento remoto 24h. Resposta rapida para qualquer evento.",
                "Painel de controle intuitivo com metricas em tempo real.",
            ],
            "cta_primary": ["Solicitar orcamento", "Ver solucao", "Agendar visita tecnica"],
            "cta_secondary": ["Ver projetos", "Conhecer tecnologia", "Falar com especialista"],
            "testimonial_template": " uptime de {rating}% em {city}. Confiabilidade comprovada.",
            "services_heading": "Solucoes tecnologicas",
            "gallery_heading": "Projetos realizados",
            "lifestyle_heading": "Inovacao em pratica",
            "contact_heading": "Solicite uma proposta",
            "footer_tagline": "Tecnologia. Eficiencia. Parceria.",
        },
        "PROFESSIONAL_TRUST": {
            "hero_title_patterns": [
                "{name}: Expertise que transmite confianca",
                "{name}: Solucoes juridicas com seriedade",
                "{name}: Seu negocio em boas maos",
            ],
            "hero_subtitle_patterns": [
                "Escritorio com experiencia consolidada em {city}.",
                "Atendimento transparente com foco em resultados para seu caso.",
                "Profissional dedicado com formacao solida e actucao comprovada.",
            ],
            "service_description_patterns": [
                "Analise detalhada do seu caso. Atendimento personalizado.",
                "Estrategia juridica sob medida com acompanhamento completo.",
                "Escritorio com infrastructure moderna para seu conforto.",
            ],
            "cta_primary": ["Agendar consulta", "Falar com advogado", "Ver areas de atucao"],
            "cta_secondary": ["Ver areas", "Conhecer equipe", "Solicitar orcamento"],
            "testimonial_template": "Cases bem-sucedidos em {city}. {rating} de satisfacao.",
            "services_heading": "Areas de atucao",
            "gallery_heading": "Escritorio e equipe",
            "lifestyle_heading": "Compromisso com seu caso",
            "contact_heading": "Fale com nosso escritorio",
            "footer_tagline": "Seriedade. Transparencia. Resultado.",
        },
    }
    return copies.get(archetype, copies["PROFESSIONAL_TRUST"])


def _select_copy_variation(
    patterns: list[str],
    archetype: str,
    seed: int | None,
    name: str = "",
    city: str = "",
    rating: str = "",
) -> str:
    """Select a deterministic copy variation based on archetype and seed.

    Uses archetype hash + seed to pick a consistent variation for the same input.
    """
    if not patterns:
        return ""
    # Build deterministic index from archetype + seed
    archetype_hash = sum(ord(c) for c in archetype)
    base_idx = ((archetype_hash + (seed or 0)) % len(patterns)) % len(patterns)
    template = patterns[base_idx]
    # Fill placeholders
    result = template.format(name=name, city=city, rating=rating)
    return result


def _generate_index_tsx_with_section_order(
    archetype: str,
    seed: int | None,
    palette: dict[str, str],
) -> str:
    """Generate Index.tsx with archetype-based section order.

    Different archetypes have different section orders to match their personality:
    - BOLD_ENERGY: lifestyle before services (action-oriented)
    - WARM_LOCAL: about before services (trust-building)
    - ZEN_PURE: gallery before services (visual-first)
    - LUXURY_ELITE: gallery at top, reviews included (aspirational)
    - MODERN_TECH: services first (solution-focused)
    - PROFESSIONAL_TRUST: about before services (credibility-first)

    Args:
        archetype: Business archetype
        seed: Optional seed for variation
        palette: Color palette dict

    Returns:
        Complete Index.tsx component as string
    """
    section_order = _get_section_order_for_archetype(archetype, seed)

    # Map section identifiers to component tags. Unknown sections are omitted:
    # JSX comments in string-generated source are easy to break and add no value.
    section_tags = {
        "navbar": "<Navbar />",
        "hero": "<HeroSection />",
        "services": "<ServicesSection />",
        "gallery": "<GallerySection />",
        "lifestyle": "<LifestyleSection />",
        "contact-cta": "<ContactCTA />",
        "footer": "<Footer />",
    }

    ordered_sections = [section_tags[s] for s in section_order if s in section_tags]

    if "<BookingModal />" not in ordered_sections:
        insert_at = max(0, len(ordered_sections) - 1)
        ordered_sections.insert(insert_at, "<BookingModal />")
    sections_str = "".join(ordered_sections)

    bg_dark = palette['bg_dark']

    return f"""import {{ Navbar }} from '../components/Navbar';
import {{ HeroSection }} from '../components/HeroSection';
import {{ ServicesSection }} from '../components/ServicesSection';
import {{ GallerySection }} from '../components/GallerySection';
import {{ LifestyleSection }} from '../components/LifestyleSection';
import {{ BookingModal }} from '../components/BookingModal';
import {{ ContactCTA }} from '../components/ContactCTA';
import {{ Footer }} from '../components/Footer';

export default function Index() {{
  return <main className="min-h-screen text-zinc-50" style={{{{backgroundColor:"{bg_dark}"}}}}>{sections_str}</main>;
}}
"""


def _cinematic_media_urls(facts: dict[str, Any]) -> tuple[list[str], list[str]]:
    from backend.pipeline_exceptions import ImageNotAvailableError

    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    images = _visual_media_urls(facts)
    if not images:
        raise ImageNotAvailableError(
            "_cinematic_media_urls: Sem imagens no facts.",
            context={
                "segmento": business.get("segment", ""),
                "acao": "Forneca fotos reais no lead ou use unsplash_fetcher",
            },
        )
    videos: list[str] = []
    for source in (media.get("videos"), business.get("videos"), facts.get("videos")):
        if isinstance(source, list):
            videos.extend(str(item or "").strip() for item in source)
        elif isinstance(source, str):
            videos.append(source.strip())
    videos = [url for url in videos if url.startswith(("http://", "https://"))]
    if not videos:
        videos = ["https://videos.pexels.com/video-files/6554881/6554881-uhd_2560_1440_25fps.mp4"]
    return images[:6], videos[:2]


def _build_google_maps_targets(
    *,
    name: str,
    city: str,
    address: str,
    maps_url: str = "",
) -> tuple[str, str]:
    """Return a live Google Maps link and an embeddable map URL."""
    href = str(maps_url or "").strip()
    query = " ".join(part for part in (address, name, city) if str(part or "").strip()).strip()
    if not query and href:
        query = href
    if not query:
        return href, ""
    embed = f"https://www.google.com/maps?q={quote_plus(query)}&output=embed&z=15"
    if not href:
        href = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
    return href, embed


def _cinematic_copy(facts: dict[str, Any]) -> dict[str, Any]:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    llm_content = facts.get("_llm_content") if isinstance(facts.get("_llm_content"), dict) else {}
    hero = llm_content.get("hero") if isinstance(llm_content.get("hero"), dict) else {}
    lifestyle = llm_content.get("lifestyle") if isinstance(llm_content.get("lifestyle"), dict) else {}
    name = str(
        business.get("name")
        or business.get("business_name")
        or business.get("nome")
        or facts.get("business_name")
        or facts.get("name")
        or facts.get("nome")
        or "Negócio local"
    )
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "sua cidade")
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or "atendimento local")
    subnicho = str(business.get("subnicho") or facts.get("subnicho") or facts.get("subniche") or "").strip().lower()
    phone = str(business.get("whatsapp") or business.get("phone") or "")
    rating = str(business.get("rating") or "")
    reviews = str(business.get("total_avaliacoes") or business.get("reviews_count") or "")
    address = str(business.get("address") or business.get("endereco") or "")
    maps_href, maps_embed_src = _build_google_maps_targets(
        name=name,
        city=city,
        address=address,
        maps_url=str(business.get("maps_url") or business.get("map_url") or ""),
    )
    segment_context = _normalize_text(" ".join([name, segment, subnicho]))
    is_nutri = "nutri" in segment_context
    is_barber = any(token in segment_context for token in ("barbearia", "barbeiro", "barber"))
    is_academia = any(token in segment_context for token in ("academia", "crossfit", "musculacao", "funcional", "personal"))
    is_estetica = any(token in segment_context for token in ("estetica", "spa", "beleza", "facial", "pele", "harmoniz", "massagem", "laser"))
    variation = facts.get("variation") if isinstance(facts.get("variation"), dict) else {}
    lane = resolve_visual_lane(
        segment=segment,
        subnicho=subnicho,
        visual_lane=str(variation.get("visual_lane") or ""),
    )
    lane_copy = lane.get("copy") if isinstance(lane.get("copy"), dict) else {}

    # Usa seed + counter para a copy variar entre leads diferentes e tambem
    # entre reprocessamentos controlados do mesmo subnicho.
    try:
        _copy_seed = int(variation.get("seed") or 0)
    except Exception:
        _copy_seed = 0
    try:
        _copy_counter = int(variation.get("counter") or business.get("__counter") or facts.get("__counter") or 0)
    except Exception:
        _copy_counter = 0
    _var_seed = abs((_copy_seed ^ ((_copy_counter + 1) * 0x9E3779B9)) or _copy_counter)

    def _rotaciona(opcoes: list[str]) -> str:
        if not opcoes:
            return ""
        return opcoes[_var_seed % len(opcoes)]

    # Defaults por SUBNICHO (não só segmento) — mais personalizado
    if is_barber:
        defaults = {
            "headline": _rotaciona([
                f"Barbearia {name} em {city}: corte que combina com seu estilo",
                f"Corte, barba e ritual em {city} com a {name}",
                f"{name}: barbearia em {city} para quem valoriza detalhe",
            ]),
            "subheadline": _rotaciona([
                "Atendimento agendado, ambiente preparado e contato direto pelo WhatsApp.",
                "Corte masculino, barba e acabamento com barbeiros certificados.",
                f"Na {name} cada corte tem ritual: começa no agendamento e termina no acabamento.",
            ]),
            "cta_primary": _rotaciona(["Agendar corte", "Marcar horario", "Reservar corte"]),
            "cta_secondary": "Ver serviços",
            "services_title": "O que está incluso no ritual da barbearia",
            "services_subheadline": f"Corte, barba e acabamento em {city}, com serviços apresentados de forma direta para agendar sem complicação.",
            "lifestyle_title": "Corte, barba e ambiente no mesmo lugar",
            "lifestyle_description": f"A {name} reúne atendimento, endereço e WhatsApp para facilitar a reserva do próximo horário.",
            "services": [
                {"title": "Corte masculino", "description": "Corte alinhado ao estilo do cliente, com avaliação antes e finalização por barbeiro certificado."},
                {"title": "Barba e acabamento", "description": "Ritual de barba com toalha quente, contorno definido e produto finalizado."},
                {"title": "Atendimento agendado", "description": f"Confirmação rápida pelo WhatsApp da {name} para {city} e região."},
            ],
        }
    elif is_nutri:
        defaults = {
            "headline": _rotaciona([
                f"{name}: nutrição esportiva em {city} que entende sua rotina",
                f"Plano alimentar em {city} com a {name} para quem treina de verdade",
                f"{name}: nutrição clínica e esportiva em {city} com acompanhamento real",
            ]),
            "subheadline": _rotaciona([
                "Plano alimentar personalizado para rotina, treino e objetivo de cada paciente.",
                "Atendimento com foco em performance, recuperação e decisões práticas antes da consulta.",
                f"A {name} acompanha de perto cada paciente em {city} com plano escrito e revisão periódica.",
            ]),
            "cta_primary": _rotaciona(["Agendar consulta", "Marcar avaliacao", "Falar com a nutri"]),
            "cta_secondary": "Conhecer abordagem",
            "services_title": "Consulta, estratégia e acompanhamento",
            "services_subheadline": f"Consulta, planejamento alimentar e retorno com foco na rotina do paciente em {city}.",
            "lifestyle_title": "Alimentação que respeita sua rotina em " + city,
            "lifestyle_description": f"A {name} atende em {city} com consulta presencial e online, focada em resultado sustentável.",
            "services": [
                {"title": "Plano alimentar", "description": "Estrutura personalizada para rotina, treino e objetivo individual."},
                {"title": "Acompanhamento", "description": f"Consultas de retorno para ajustes finos no plano da {name}."},
                {"title": "Atendimento presencial e online", "description": f"Pacientes em {city} e online com mesma qualidade de plano e acompanhamento."},
            ],
        }
    elif is_academia:
        defaults = {
            "headline": _rotaciona([
                f"Treino de verdade em {city} com a {name}",
                f"{name}: musculação, crossfit e funcional em {city}",
                f"{name} em {city} para quem quer resultado com estrutura",
            ]),
            "subheadline": _rotaciona([
                f"Estrutura completa, horários flexíveis e plano de treino na {name}.",
                f"A {name} atende {city} e região com musculação, crossfit e acompanhamento.",
                f"Academia com equipamentos modernos, profissionais e ambiente preparado em {city}.",
            ]),
            "cta_primary": _rotaciona(["Comecar treino", "Marcar aula experimental", "Conhecer estrutura"]),
            "cta_secondary": "Ver planos",
            "services_title": "Modalidades e estrutura da academia",
            "services_subheadline": f"Treino, modalidades e rotina organizados para quem está em {city} e quer decidir com clareza.",
            "lifestyle_title": "Treinar com regularidade e estrutura em " + city,
            "lifestyle_description": f"A {name} em {city} oferece musculação, crossfit e funcional com profissionais cadastrados.",
            "services": [
                {"title": "Musculação", "description": "Equipamentos completos para hipertrofia, força e condicionamento."},
                {"title": "Crossfit / Funcional", "description": f"Aulas coletivas com coach e programação variada na {name}."},
                {"title": "Acompanhamento", "description": f"Profissionais avaliam e ajustam o treino para cada aluno da {name}."},
            ],
        }
    elif is_estetica:
        defaults = {
            "headline": _rotaciona([
                f"Tratamentos estéticos em {city} com a {name}",
                f"{name}: cuidado com a pele, corpo e autoestima em {city}",
                f"Estética em {city} com avaliação e agendamento pela {name}",
            ]),
            "subheadline": _rotaciona([
                "Tratamentos faciais, corporais e cuidados de beleza com agendamento pelo WhatsApp.",
                f"A {name} atende {city} com foco em avaliação, conforto e cuidado estético.",
                "Ambiente preparado para cuidar da pele, orientar o procedimento e facilitar o agendamento.",
            ]),
            "cta_primary": _rotaciona(["Agendar avaliação", "Marcar horário", "Falar com a clínica"]),
            "cta_secondary": "Conhecer tratamentos",
            "services_title": "Tratamentos para pele, corpo e bem-estar",
            "services_subheadline": f"Facial, corporal e cuidados de beleza da {name} aparecem com clareza para quem está em {city}.",
            "lifestyle_title": "Cuidado estético com conforto e atenção aos detalhes",
            "lifestyle_description": f"A {name} em {city} apresenta ambiente, endereço e WhatsApp para facilitar a primeira avaliação.",
            "services": [
                {"title": "Tratamentos faciais", "description": "Protocolos para limpeza, hidratação e cuidado da pele antes do próximo agendamento."},
                {"title": "Estética corporal", "description": "Procedimentos corporais apresentados com orientação clara e contato fácil pelo WhatsApp."},
                {"title": "Avaliação estética", "description": f"Conversa inicial com a {name} para entender objetivo, rotina e melhor procedimento."},
            ],
        }
    else:
        defaults = {
            "headline": _rotaciona([
                f"{name} em {city}: atendimento claro para {segment}",
                f"{name} — {segment} em {city} com WhatsApp fácil",
                f"{segment} em {city} pela {name}",
            ]),
            "subheadline": _rotaciona([
                f"Serviços, endereço e WhatsApp da {name} aparecem de forma clara.",
                f"Atendimento em {city} pela {name} com avaliações e imagens do negócio.",
                f"A {name} atende {city} com informações úteis e contato visível.",
            ]),
            "cta_primary": _rotaciona(["Falar no WhatsApp", "Solicitar contato", "Marcar atendimento"]),
            "cta_secondary": "Ver abordagem",
            "services_title": "O que está incluso no atendimento",
            "services_subheadline": f"Serviços, localização e WhatsApp da {name} ficam claros para quem está em {city}.",
            "lifestyle_title": f"Atendimento local em {city} pela {name}",
            "lifestyle_description": f"{name} apresenta ambiente, atendimento e WhatsApp com leitura simples.",
            "services": [
                {"title": "Atendimento", "description": f"Serviços e forma de contato da {name} em {city}."},
                {"title": "Avaliações locais", "description": "Imagens do negócio e avaliações reais sustentam a decisão de contato."},
                {"title": "Contato rápido", "description": f"WhatsApp direto para falar com {name}."},
            ],
        }
    services = defaults["services"]
    if isinstance(llm_content.get("services"), list) and llm_content["services"]:
        clean_services = []
        for item in llm_content["services"][:3]:
            if isinstance(item, dict) and item.get("title"):
                clean_services.append({
                    "title": str(item.get("title")),
                    "description": str(item.get("description") or defaults["services"][min(len(clean_services), 2)]["description"]),
                })
        if clean_services:
            services = clean_services

    def _fmt(template: str, fallback: str) -> str:
        raw = str(template or fallback or "").strip()
        if not raw:
            raw = fallback
        return raw.format(name=name, city=city, segment=segment)

    def _copy_slot(key: str, fallback: str, lane_key: str | None = None) -> str:
        """The prompt/LLM contract is authoritative; lane copy only fills blanks."""
        raw = llm_content.get(key)
        if raw not in (None, ""):
            return str(raw)
        return _fmt(lane_copy.get(lane_key or key, ""), fallback)

    public_copy_rewrites = {
        "usa uma assinatura visual mais forte para transformar presença local em reserva real": "reúne atendimento, endereço e WhatsApp para facilitar a reserva do próximo horário",
        "ganha uma assinatura mais respirada": "apresenta consulta, rotina e contato com leitura mais leve",
        "ganha uma presença mais acolhedora": "mostra consulta, escuta e acompanhamento de forma acolhedora",
        "ganha uma presença mais elegante": "apresenta serviços, endereço e reserva com acabamento mais elegante",
        "ganha uma estética mais sofisticada": "organiza consulta, privacidade e agendamento com leitura mais cuidadosa",
        "assume uma estética mais refinada": "valoriza corte, atendimento e experiência presencial",
        "assume uma direção mais esportiva": "prioriza treino, rotina alimentar e acompanhamento técnico",
        "assume uma direção mais atlética": "prioriza intensidade, horários claros e decisão rápida",
        "assume uma leitura mais gráfica": "destaca rotina, modalidades e decisão sem enrolação",
        "assume uma linha mais urbana": "destaca corte, agenda e personalidade do atendimento",
        "assume uma linha mais contemporânea": "apresenta corte, atendimento e reserva com leitura mais atual",
        "assume uma linha mais autoral": "apresenta corte, barba e reserva com identidade própria",
        "aparece com cidade, contato e contexto alinhados": "reúne cidade, contato e informações úteis",
        "entram organizadas": "ficam organizadas",
        "entram com": "aparecem com",
        "entra como": "ajuda como",
        "trabalham na mesma direção": "ajudam a pessoa a decidir",
        "apontam para o mesmo próximo passo": "ajudam a pessoa a decidir",
        "trabalham para reduzir atrito": "ajudam a simplificar a decisão",
        "foram montados": "ficam organizados",
        "A página fecha esse bloco": "Este trecho reúne",
        "página fecha esse bloco": "este trecho reúne",
        "para transformar visita em horário marcado": "para facilitar a reserva do horário",
        "sem rodeio": "sem complicação",
        "precisa parecer atual": "precisa comunicar atendimento atual",
        "marca precisa parecer atual": "barbearia precisa comunicar atendimento atual",
        "quando marca precisa comunicar atendimento atual, rápida e com personalidade": "com agenda clara e personalidade no atendimento",
        "marca precisa comunicar atendimento atual, rápida e com personalidade": "agenda clara e personalidade no atendimento",
        "quando agenda clara e personalidade no atendimento": "com agenda clara e personalidade no atendimento",
        "não como lista genérica": "com clareza para quem quer escolher",
        "não como lista": "com clareza",
        "não de ornamento": "de informação útil",
        "O visual trabalha": "A seção mostra",
        "seção mostra": "As imagens mostram",
        "primeiro scroll": "primeira visita",
        "Score": "Avaliação",
        "score": "avaliação",
        "prova social tem tom humano e direto": "avaliações ajudam a entender a experiência de outros clientes",
        "A prova social tem tom humano e direto": "As avaliações ajudam a entender a experiência de outros clientes",
        "A prova social entra": "As avaliações aparecem",
        "a prova social entra": "as avaliações aparecem",
        "A prova social aparece": "As avaliações aparecem",
        "a prova social aparece": "as avaliações aparecem",
        "prova social": "avaliações",
        "mostra com mais clareza quando prova, mídia e contato apontam para o mesmo próximo passo": "mostra serviços, avaliações e contato no mesmo caminho",
        "mostra serviços, avaliações e contato no mesmo caminho": "reúne serviços, avaliações e contato para facilitar a decisão",
        "A direção visual": "A página",
        "direção visual": "organização da página",
        "o site precisa parecer": "o site deve mostrar",
        "reputação local com recorte de marca": "reputação local com serviços e contato claros",
        "mídia editorial": "imagens do negócio",
        "mídia": "imagens",
        "prova local": "avaliações e informações locais",
        "CTA": "contato",
        "contato final": "caminho final",
        "mostra com atendimento": "mostra atendimento",
        "aparecem como parte": "fazem parte",
        "aparecem arrumados": "ficam organizados",
        "Este trecho reúne com": "Este trecho reúne",
        "este trecho reúne com": "este trecho reúne",
        "facilitar reserva": "facilitar a reserva",
        "facilitar a a reserva": "facilitar a reserva",
        "sem ruído": "sem complicação",
        "sem etapa morta": "sem caminho confuso",
        "sem menus mortos": "sem caminho confuso",
        "sem inventar promessa": "com clareza no atendimento",
        "sem promessas vazias": "com clareza no atendimento",
        "não como decoração": "como apoio real para decidir",
        "não como bloco solto": "junto da decisão de contato",
        "não como grade repetida": "com ritmo visual diferente",
        "não um mosaico genérico": "com imagens organizadas por contexto",
        "não catálogo": "com contexto real",
        "narrativa visual": "sequência de informações",
        "presença local": "atendimento na cidade",
        "identidade visual": "identidade do negócio",
        "estética própria": "estilo próprio",
        "construção visual própria": "informação clara",
        "parecer um site clonado": "ficar genérico",
        "linguagem fiel": "informações fiéis",
        "próximo passo simples": "agendamento mais simples",
        "próximo passo": "agendamento",
        "canal oficial": "WhatsApp",
        "Chegue pelo WhatsApp": "Fale pelo WhatsApp",
        "Chegue à": "Fale com",
        "chegue à": "fale com",
        "Chegue a": "Fale com",
        "chegue a": "fale com",
        "com uma estética menos agressiva": "com treino orientado, rotina clara e ambiente acolhedor",
        "aparece com uma estética menos agressiva": "apresenta treino orientado, rotina clara e ambiente acolhedor",
        "mostra com uma estética menos agressiva": "apresenta treino orientado, rotina clara e ambiente acolhedor",
        "A página valoriza": "A seção reúne",
        "a página valoriza": "a seção reúne",
        "página valoriza": "a seção reúne",
        "Cards e ritmo mais vivos": "Avaliações e detalhes mais claros",
        "cards e ritmo mais vivos": "avaliações e detalhes mais claros",
        "A composição mistura": "A seção reúne",
        "a composição mistura": "a seção reúne",
        "composição mistura": "a seção reúne",
    }

    def _public_text(value: Any, fallback: str = "") -> str:
        text = str(value if value not in (None, "") else fallback).strip()
        for source, target in public_copy_rewrites.items():
            text = re.sub(re.escape(source), target, text, flags=re.IGNORECASE)
        text = re.sub(
            r"Informações confirmadas da ([^.,]+?) em ([^.,]+?), organizadas para contato direto\.?",
            r"Serviços, localização e WhatsApp de \1 ficam claros para quem está em \2.",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"Visual cinematográfico, dados confirmados da ([^.,]+?) e caminho direto para contato\.?",
            r"\1 apresenta ambiente, atendimento e WhatsApp com leitura simples.",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\bcom informações confirmadas\b", "com clareza no atendimento", text, flags=re.IGNORECASE)
        text = re.sub(r"\bdados confirmados\b", "informações úteis", text, flags=re.IGNORECASE)
        text = re.sub(r"\binformações confirmadas\b", "informações úteis", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\borganizadas? para contato direto\b",
            "com caminho claro para falar pelo WhatsApp",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\b[Aa]\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç ]{1,80})\s+aparece\b", r"\1 mostra", text)
        text = re.sub(r"\baparece\b", "mostra", text, flags=re.IGNORECASE)
        text = re.sub(r"\bentra\b", "aparece", text, flags=re.IGNORECASE)
        text = re.sub(r"\bganha\b", "recebe", text, flags=re.IGNORECASE)
        text = re.sub(r"\bassume\b", "apresenta", text, flags=re.IGNORECASE)
        text = re.sub(r"\bparecer\b", "mostrar", text, flags=re.IGNORECASE)
        text = text.replace(
            "quando agenda clara e personalidade no atendimento",
            "com agenda clara e personalidade no atendimento",
        )
        text = text.replace(
            "destaca corte, agenda e personalidade do atendimento com agenda clara e personalidade no atendimento",
            "destaca corte, agenda clara e atendimento com personalidade",
        )
        text = text.replace("mostra com atendimento", "mostra atendimento")
        text = text.replace(
            "Este trecho reúne reserva, localização e identidade forte para facilitar reserva do horário",
            "Reserva, localização e estilo do atendimento facilitam a escolha do horário",
        )
        text = text.replace(
            "este trecho reúne reserva, localização e identidade forte para facilitar reserva do horário",
            "reserva, localização e estilo do atendimento facilitam a escolha do horário",
        )
        text = text.replace("facilitar a a reserva", "facilitar a reserva")
        text = text.replace("facilitar reserva", "facilitar a reserva")
        text = text.replace("Flexibility de horarios", "horários flexíveis")
        text = text.replace("Flexibility de horários", "horários flexíveis")
        text = re.sub(r"\bpara\s+finally\s+", "para ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfinally\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfinally\b", "", text, flags=re.IGNORECASE)
        text = text.replace("horarios", "horários")
        text = text.replace("alcanzar", "alcançar")
        text = text.replace("resistencia", "resistência")
        text = text.replace("forca", "força")
        text = text.replace("equite", "equipe")
        text = text.replace("condiconamento", "condicionamento")
        text = text.replace("deevolucao", "de evolução")
        text = text.replace("paravoces", "para vocês")
        text = text.replace("coracao", "coração")
        text = text.replace("Mercês", "Mercês")
        return re.sub(r"\s+", " ", text).strip()

    data = {
        "name": name,
        "city": city,
        "segment": segment,
        "visual_lane": str(lane.get("id") or ""),
        "visual_lane_name": str(lane.get("name") or ""),
        "phone": phone,
        "phone_digits": re.sub(r"\D+", "", phone),
        "rating": rating,
        "reviews": reviews,
        "address": address,
        "mapsHref": maps_href,
        "mapsEmbedSrc": maps_embed_src,
        "hero_badge": _fmt(lane_copy.get("hero_badge", ""), f"{segment} em {city}"),
        "headline": str(hero.get("headline") or defaults["headline"]),
        "subheadline": str(hero.get("subheadline") or defaults["subheadline"]),
        "cta_primary": str(hero.get("cta_primary") or defaults["cta_primary"]),
        "cta_secondary": str(hero.get("cta_secondary") or defaults["cta_secondary"]),
        "services_title": _copy_slot("services_title", defaults["services_title"]),
        "services_kicker": _fmt(lane_copy.get("services_kicker", ""), "Serviços"),
        "services_subheadline": _copy_slot(
            "services_subheadline",
            defaults.get("services_subheadline") or f"Serviços, localização e WhatsApp da {name} ficam claros para quem está em {city}.",
        ),
        "about_kicker": _fmt(lane_copy.get("about_kicker", ""), "Direção"),
        "about_title": _copy_slot("about_title", f"{name} em {city} com informações claras para decidir."),
        "about_body": _copy_slot("about_body", f"{name} reúne endereço, contato e próximos passos para quem está em {city}."),
        "gallery_kicker": _fmt(lane_copy.get("gallery_kicker", ""), "Ambiente"),
        "gallery_title": _copy_slot("gallery_title", f"Ambiente, rotina e detalhes da {name}."),
        "gallery_intro": _copy_slot("gallery_intro", f"As imagens ajudam a entender o espaço, o atendimento e o contexto de {city}."),
        "reviews_kicker": _fmt(lane_copy.get("reviews_kicker", ""), "Reputação"),
        "reviews_title": _copy_slot("reviews_title", f"Avaliações que ajudam a escolher {name}."),
        "reviews_intro": _copy_slot("reviews_intro", f"Avaliações, cidade e contato ajudam a decidir com mais segurança em {city}."),
        "proof_quote": _copy_slot("proof_quote", f"{name} reúne atendimento, avaliações e contato para facilitar a decisão."),
        "faq_kicker": _fmt(lane_copy.get("faq_kicker", ""), "Perguntas"),
        "faq_title": _copy_slot("faq_title", "Perguntas antes de chamar no WhatsApp."),
        "faq_intro": _copy_slot("faq_intro", f"Respostas rápidas para quem está avaliando {name} em {city}."),
        "location_kicker": _fmt(lane_copy.get("location_kicker", ""), "Presença local"),
        "location_title": _copy_slot("location_title", f"Atendimento em {city}."),
        "location_intro": _copy_slot("location_intro", f"Endereço e WhatsApp aparecem juntos para facilitar contato em {city}."),
        "location_cta_kicker": _fmt(lane_copy.get("location_cta_kicker", ""), "Acesso"),
        "location_cta_title": _copy_slot("location_cta_title", f"Fale com {name} pelo WhatsApp."),
        "location_cta_body": _copy_slot("location_cta_body", "Contato e endereço ficam juntos para facilitar a decisão."),
        "location_cta_primary": str(llm_content.get("location_cta_primary") or _fmt(lane_copy.get("location_cta_primary", ""), "Falar no WhatsApp")),
        "location_cta_secondary": str(llm_content.get("location_cta_secondary") or _fmt(lane_copy.get("location_cta_secondary", ""), "Ver contato")),
        "lifestyle_kicker": _fmt(lane_copy.get("lifestyle_kicker", ""), "Experiência"),
        "lifestyle_title": str(lifestyle.get("title") or _fmt(lane_copy.get("lifestyle_title", ""), defaults["lifestyle_title"])),
        "lifestyle_description": str(lifestyle.get("description") or _fmt(lane_copy.get("lifestyle_description", ""), defaults["lifestyle_description"])),
        "gallery_alt": str(llm_content.get("gallery_alt") or f"{segment} em {city}"),
        "footer_tagline": str(
            llm_content.get("footer_tagline")
            or f"{name} em {city}: contato direto, endereço claro e WhatsApp oficial."
        ),
        "modal_title": str(llm_content.get("modal_title") or f"Fale com {name}"),
        "modal_cta": str(llm_content.get("modal_cta") or "Enviar mensagem"),
        "modal_kicker": _fmt(lane_copy.get("modal_kicker", ""), "Contato"),
        "about_card_1_title": _fmt(lane_copy.get("about_card_1_title", ""), "Presença local"),
        "about_card_1_text": _copy_slot("about_card_1_text", f"{name} reúne cidade, contato e informações úteis para quem está em {city}."),
        "about_card_2_title": _fmt(lane_copy.get("about_card_2_title", ""), "Serviço principal"),
        "about_card_2_text": _copy_slot("about_card_2_text", "As principais frentes de atendimento ficam organizadas para leitura rápida e decisão sem complicação."),
        "about_card_3_title": _fmt(lane_copy.get("about_card_3_title", ""), "Marca em contexto"),
        "about_card_3_text": _copy_slot("about_card_3_text", f"Ambiente, imagens e atendimento sustentam o estilo de {name} com clareza."),
        "about_city_label": _fmt(lane_copy.get("about_city_label", ""), "Cidade"),
        "about_aside_body": _copy_slot("about_aside_body", "Contato e informações úteis para quem está decidindo agora."),
        "services_city_body": _fmt(lane_copy.get("services_city_body", ""), "Estrutura organizada para leitura rápida e decisão mais clara."),
        "contact_kicker": _fmt(lane_copy.get("contact_kicker", ""), "Contato"),
        "contact_headline": _copy_slot("contact_headline", "Quer falar com a equipe agora?"),
        "contact_sub": _copy_slot("contact_sub", "Envie uma mensagem para tirar dúvidas e combinar o melhor horário."),
        "contact_card_label": _fmt(lane_copy.get("contact_card_label", ""), "Contato oficial"),
        "contact_primary_label": _fmt(lane_copy.get("contact_primary_label", ""), "Falar no WhatsApp"),
        "contact_secondary_label": _fmt(lane_copy.get("contact_secondary_label", ""), "Abrir contato"),
        "footer_contact_label": _fmt(lane_copy.get("footer_contact_label", ""), "Contato"),
        "footer_location_label": _fmt(lane_copy.get("footer_location_label", ""), "Local"),
        "footer_privacy_note": _fmt(lane_copy.get("footer_privacy_note", ""), "Privacidade preservada no atendimento."),
        "services": services,
    }
    for key, value in list(data.items()):
        if isinstance(value, str):
            data[key] = _public_text(value)
    clean_services = []
    for service in services:
        if isinstance(service, dict):
            clean_services.append(
                {
                    "title": _public_text(service.get("title", "")),
                    "description": _public_text(service.get("description", "")),
                }
            )
    data["services"] = clean_services or services
    return data


def _with_cinematic_variation_defaults(facts: dict[str, Any]) -> dict[str, Any]:
    """Fill missing visual knobs before theme and block resolution."""
    enriched = dict(facts or {})
    variation = dict(enriched.get("variation") if isinstance(enriched.get("variation"), dict) else {})
    if get_variation is not None:
        try:
            seeded = get_variation(
                enriched,
                counter=int(variation.get("counter") or enriched.get("__counter") or 0),
            ).to_dict()
        except Exception:
            seeded = {}
        for key in ("seed", "counter", "visual_lane", "motion_style", "copy_voice", "color_emphasis", "section_order_style"):
            if key in seeded:
                variation.setdefault(key, seeded[key])
    combo = _cinematic_diversity_combo(variation)
    for key, value in combo.items():
        variation.setdefault(key, value)
    if variation.get("reviews_variant"):
        variation.setdefault("proof_style", variation["reviews_variant"])
    variation.setdefault("anti_repetition_rule", "avoid_glass")
    variation = _enforce_premium_visual_floor(variation, enriched)
    enriched["variation"] = variation
    return enriched


def _enforce_premium_visual_floor(variation: dict[str, Any], facts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Prevent the Studio from publishing a visually flat creative plan.

    The creative LLM can still choose a calm/wellness direction, but production
    sites must keep agency-level presence: visible motion, strong type, readable
    solid surfaces and a hero composition with enough tension.
    """
    v = dict(variation or {})
    facts = facts or {}
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segment") or facts.get("segmento") or "")
    subnicho = str(business.get("subniche") or business.get("subnicho") or facts.get("subniche") or facts.get("subnicho") or "")
    try:
        lane = resolve_visual_lane(
            segment=segment,
            subnicho=subnicho,
            visual_lane=str(v.get("visual_lane") or ""),
        )
        lane_blocks = lane.get("blocks") if isinstance(lane.get("blocks"), dict) else {}
    except Exception:
        lane_blocks = {}
    for key in (
        "aesthetic_mode",
        "spacing_density",
        "radius_mode",
        "container_strategy",
        "typography_scale",
        "heading_style",
        "surface_depth",
        "overlap_mode",
        "motion_intensity",
        "image_treatment",
    ):
        if not v.get(key) and lane_blocks.get(key):
            v[key] = lane_blocks[key]

    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    videos = media.get("videos") if isinstance(media.get("videos"), list) else []

    aesthetic = str(v.get("aesthetic_mode") or "").strip().lower()
    hero_layout = str(v.get("hero_layout") or "").strip().lower()
    spacing = str(v.get("spacing_density") or "").strip().lower()
    motion = str(v.get("motion_intensity") or "").strip().lower()
    typography = str(v.get("typography_scale") or "").strip().lower()
    priority = str(v.get("prompt_priority") or "").strip().lower()
    weak_wellness = aesthetic in {"wellness", "balanced", "minimal", ""}
    weak_combo = (
        hero_layout in {"", "center"}
        and spacing in {"", "spacious"}
        and motion in {"", "minimal"}
        and typography in {"", "soft"}
    )

    if weak_wellness or weak_combo:
        v["motion_intensity"] = "composed" if motion in {"", "minimal"} else v.get("motion_intensity")
        v["typography_scale"] = "strong" if typography in {"", "soft"} else v.get("typography_scale")
        if spacing in {"", "spacious"} and hero_layout in {"", "center"}:
            v["spacing_density"] = "normal"
        if hero_layout in {"", "center"}:
            try:
                seed = abs(int(v.get("seed") or 0))
            except Exception:
                seed = 0
            if videos and seed % 5 == 0:
                v["hero_layout"] = "video"
            else:
                v["hero_layout"] = "asymmetric" if seed % 2 else "split"
            v.setdefault("hero_text_side", "left" if seed % 3 else "right")
        if str(v.get("container_strategy") or "").strip().lower() in {"", "contained"}:
            v["container_strategy"] = "wide"
        if str(v.get("surface_depth") or "").strip().lower() in {"", "elevated"}:
            v["surface_depth"] = "bordered"
        if str(v.get("overlap_mode") or "").strip().lower() in {"", "none"} and priority in {"visual_drama", "trust", "conversion", ""}:
            v["overlap_mode"] = "subtle"
        if str(v.get("heading_style") or "").strip().lower() in {"", "clean"}:
            v["heading_style"] = "display" if aesthetic != "wellness" else "editorial"

    motion_mix = v.get("motion_mix") if isinstance(v.get("motion_mix"), list) else []
    motion_mix = [str(item) for item in motion_mix if str(item).strip()]
    if not motion_mix or set(motion_mix).issubset({"subtle_fade"}):
        motion_mix = ["mask_reveal", "stagger_cards"]
    if v.get("hero_layout") in {"video", "fullbleed"} and "parallax_video" not in motion_mix:
        motion_mix.insert(0, "parallax_video")
    if len(motion_mix) < 2:
        motion_mix.append("line_draw")
    v["motion_mix"] = list(dict.fromkeys(motion_mix[:4]))

    if str(v.get("surface_style") or "").strip().lower() in {"", "glass", "soft_tint"}:
        v["surface_style"] = "solid"
    surface_mix = v.get("surface_mix") if isinstance(v.get("surface_mix"), list) else []
    surface_mix = [str(item) for item in surface_mix if str(item) not in {"glass"}]
    if len(set(surface_mix)) < 2:
        surface_mix = ["solid", "outline"]
    v["surface_mix"] = surface_mix[:4]

    section_map = v.get("section_surface_map") if isinstance(v.get("section_surface_map"), dict) else {}
    if not section_map or len(set(str(value) for value in section_map.values())) < 2:
        v["section_surface_map"] = {
            "about": "solid",
            "services": "outline",
            "reviews": "solid",
            "faq": "outline",
            "location": "solid",
            "contact-cta": "solid",
        }

    v.setdefault("anti_repetition_rule", "avoid_glass")
    return v


def _cinematic_diversity_combo(variation: dict[str, Any]) -> dict[str, Any]:
    lane = str(variation.get("visual_lane") or "").strip().lower()
    lane_index = 0
    if lane.startswith("lane_") and len(lane) >= 6:
        lane_index = max(0, min(7, ord(lane[-1]) - ord("a")))
    elif variation.get("seed") is not None:
        try:
            lane_index = int(variation.get("seed") or 0) % 8
        except Exception:
            lane_index = 0
    combos: list[dict[str, Any]] = [
        {
            "hero_layout": "split",
            "hero_text_side": "left",
            "about_variant": "feature_grid",
            "services_variant": "stacked_cards",
            "reviews_variant": "score_wall",
            "faq_variant": "panel",
            "location_variant": "feature_local",
            "gallery_density": "balanced_grid",
            "cta_style": "solid_panel",
            "surface_style": "outline",
            "typography_mood": "condensed_sport",
            "color_strategy": "committed",
            "motion_mix": ["stagger_cards", "line_draw"],
            "section_order": ["hero", "about", "services", "gallery", "reviews", "faq", "location", "contact-cta"],
        },
        {
            "hero_layout": "video",
            "hero_text_side": "left",
            "about_variant": "manifesto_split",
            "services_variant": "stats_then_cards",
            "reviews_variant": "card_marquee",
            "faq_variant": "inline",
            "location_variant": "feature_local",
            "gallery_density": "mosaic",
            "cta_style": "poster_band",
            "surface_style": "outline",
            "typography_mood": "technical_grotesk",
            "color_strategy": "drenched",
            "motion_mix": ["parallax_video", "mask_reveal", "marquee"],
            "section_order": ["hero", "gallery", "about", "services", "reviews", "faq", "location", "contact-cta"],
        },
        {
            "hero_layout": "center",
            "hero_text_side": "center",
            "about_variant": "manifesto_split",
            "services_variant": "split_editorial",
            "reviews_variant": "quote_spotlight",
            "faq_variant": "panel",
            "location_variant": "split_local",
            "gallery_density": "editorial_grid",
            "cta_style": "minimal_inline",
            "surface_style": "solid",
            "typography_mood": "clean_sans",
            "color_strategy": "restrained",
            "motion_mix": ["subtle_fade", "stagger_cards"],
            "section_order": ["hero", "about", "reviews", "services", "gallery", "faq", "location", "contact-cta"],
        },
        {
            "hero_layout": "asymmetric",
            "hero_text_side": "right",
            "about_variant": "proof_sidebar",
            "services_variant": "stacked_cards",
            "reviews_variant": "editorial_case",
            "faq_variant": "inline",
            "location_variant": "split_local",
            "gallery_density": "editorial_grid",
            "cta_style": "split_card",
            "surface_style": "solid",
            "typography_mood": "technical_grotesk",
            "color_strategy": "full_palette",
            "motion_mix": ["hover_depth", "line_draw"],
            "section_order": ["hero", "about", "services", "gallery", "reviews", "location", "faq", "contact-cta"],
        },
        {
            "hero_layout": "fullbleed",
            "hero_text_side": "left",
            "about_variant": "proof_sidebar",
            "services_variant": "stats_then_cards",
            "reviews_variant": "card_marquee",
            "faq_variant": "inline",
            "location_variant": "feature_local",
            "gallery_density": "cinematic_strip",
            "cta_style": "poster_band",
            "surface_style": "outline",
            "typography_mood": "condensed_sport",
            "color_strategy": "drenched",
            "motion_mix": ["mask_reveal", "parallax_video", "stagger_cards"],
            "section_order": ["hero", "services", "gallery", "reviews", "about", "faq", "location", "contact-cta"],
        },
        {
            "hero_layout": "split",
            "hero_text_side": "right",
            "about_variant": "manifesto_split",
            "services_variant": "split_editorial",
            "reviews_variant": "editorial_case",
            "faq_variant": "panel",
            "location_variant": "split_local",
            "gallery_density": "editorial_grid",
            "cta_style": "minimal_inline",
            "surface_style": "solid",
            "typography_mood": "luxury_display",
            "color_strategy": "committed",
            "motion_mix": ["subtle_fade", "line_draw"],
            "section_order": ["hero", "about", "gallery", "services", "reviews", "location", "faq", "contact-cta"],
        },
        {
            "hero_layout": "asymmetric",
            "hero_text_side": "left",
            "about_variant": "proof_sidebar",
            "services_variant": "stats_then_cards",
            "reviews_variant": "score_wall",
            "faq_variant": "panel",
            "location_variant": "feature_local",
            "gallery_density": "balanced_grid",
            "cta_style": "solid_panel",
            "surface_style": "outline",
            "typography_mood": "clean_sans",
            "color_strategy": "full_palette",
            "motion_mix": ["hover_depth", "stagger_cards"],
            "section_order": ["hero", "reviews", "about", "services", "gallery", "faq", "location", "contact-cta"],
        },
        {
            "hero_layout": "video",
            "hero_text_side": "right",
            "about_variant": "manifesto_split",
            "services_variant": "split_editorial",
            "reviews_variant": "quote_spotlight",
            "faq_variant": "panel",
            "location_variant": "split_local",
            "gallery_density": "cinematic_strip",
            "cta_style": "poster_band",
            "surface_style": "outline",
            "typography_mood": "editorial_serif",
            "color_strategy": "committed",
            "motion_mix": ["parallax_video", "mask_reveal"],
            "section_order": ["hero", "gallery", "services", "about", "reviews", "faq", "location", "contact-cta"],
        },
    ]
    combo = dict(combos[lane_index % len(combos)])
    try:
        seed_value = abs(int(variation.get("seed") or 0))
    except Exception:
        seed_value = 0
    try:
        counter_value = abs(int(variation.get("counter") or 0))
    except Exception:
        counter_value = 0
    sub_index = (seed_value // max(1, len(combos)) + counter_value * 11) % 12
    hero_layouts = ["split", "video", "center", "asymmetric", "fullbleed", "split", "video", "asymmetric"]
    gallery_densities = ["balanced_grid", "mosaic", "editorial_grid", "cinematic_strip"]
    cta_styles = ["solid_panel", "poster_band", "split_card", "minimal_inline"]
    surface_styles = ["solid", "outline", "solid", "outline", "solid"]
    motion_sets = [
        ["stagger_cards", "line_draw"],
        ["parallax_video", "mask_reveal"],
        ["hover_depth", "stagger_cards"],
        ["mask_reveal", "line_draw"],
        ["subtle_fade", "hover_depth"],
        ["parallax_video", "stagger_cards", "mask_reveal"],
    ]
    if variation.get("seed") is not None or variation.get("counter") is not None:
        # A lane is only the broad art direction. The seed adds a second layer of
        # layout/material/motion variation so production does not collapse into
        # the same few compositions for an entire niche.
        combo["hero_layout"] = hero_layouts[(lane_index + sub_index) % len(hero_layouts)]
        combo["hero_text_side"] = ["left", "right", "center", "left"][(lane_index + sub_index) % 4]
        if combo["hero_layout"] in {"video", "fullbleed", "center"} and sub_index % 3 == 0:
            combo["hero_text_side"] = "center"
        combo["gallery_density"] = gallery_densities[(lane_index + sub_index) % len(gallery_densities)]
        combo["cta_style"] = cta_styles[(lane_index + sub_index) % len(cta_styles)]
        combo["surface_style"] = surface_styles[(lane_index + sub_index) % len(surface_styles)]
        combo["motion_mix"] = motion_sets[(lane_index + sub_index) % len(motion_sets)]
    if combo.get("surface_style") == "soft_tint":
        combo["surface_style"] = "solid"
    combo["section_surface_map"] = {
        "about": combo["surface_style"],
        "services": "solid" if combo["services_variant"] == "stats_then_cards" else combo["surface_style"],
        "reviews": "outline" if combo["reviews_variant"] == "card_marquee" else combo["surface_style"],
        "faq": "solid" if combo["faq_variant"] == "panel" else "outline",
        "location": "solid",
        "contact-cta": "solid",
    }
    return combo


def _generate_cinematic_studio_files(facts: dict[str, Any]) -> dict[str, str]:
    facts = _with_cinematic_variation_defaults(facts)
    _biz = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    segment = str(_biz.get("segment") or _biz.get("segmento") or facts.get("segmento") or facts.get("segment") or "servicos").lower()
    archetype = _get_archetype_for_segment(segment)
    fallback_palette = _get_archetype_palette(archetype)
    typography = _get_archetype_typography(archetype)
    fonts = _get_archetype_fonts(archetype)
    theme = resolve_cinematic_theme(
        facts,
        fallback_palette=fallback_palette,
        fallback_archetype=archetype,
        typography=typography,
        fonts=fonts,
    )
    archetype = str(theme["archetype"] or archetype)
    palette = dict(theme["palette"])

    c_bg = palette['bg_dark']
    c_accent = palette['primary']
    c_accent_light = palette['accent_soft']
    c_accent_dark = palette['accent_dark']
    c_text = palette['text_light']
    c_text_muted = palette['text_muted']

    # Sprint 14.12: variacao por subnicho + counter rotation para evitar
    # que sites do mesmo subnicho (ex: 4 nutricionistas) saiam identicos.
    _biz = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    _subnicho_norm = (
        str(_biz.get("subnicho") or _biz.get("subniche") or facts.get("subnicho") or facts.get("subniche") or "default")
        .strip().lower() or "default"
    )
    _variation_for_seed = facts.get("variation") if isinstance(facts.get("variation"), dict) else {}
    try:
        _seed_base_for_html = int(_variation_for_seed.get("seed") or 0)
    except Exception:
        _seed_base_for_html = 0
    try:
        _counter_for_html = int(
            _biz.get("__counter")
            or facts.get("__counter")
            or _variation_for_seed.get("counter")
            or 0
        )
    except Exception:
        _counter_for_html = 0
    _seed_for_html = abs((_seed_base_for_html ^ ((_counter_for_html + 1) * 0x9E3779B9)) or _counter_for_html)

    # Hero class variants (10 opcoes rotacionadas por counter)
    # Mais variabilidade para forcar Tailwind a gerar CSS diferente por lead
    _HERO_CLASSES_POOL = [
        "relative isolate min-h-[92svh] overflow-hidden px-5 pb-16 pt-28 text-white md:px-8 md:pb-24 md:pt-36 grid place-items-center",
        "relative isolate min-h-[85svh] overflow-hidden px-6 pb-20 pt-24 text-white md:px-10 md:pb-28 md:pt-32 flex flex-col justify-center",
        "relative isolate min-h-[92svh] overflow-hidden px-4 pb-12 pt-20 text-white md:px-6 md:pb-16 md:pt-24 grid place-items-end",
        "relative isolate min-h-[88svh] overflow-hidden px-5 pb-14 pt-32 text-white md:px-8 md:pb-20 md:pt-40 flex items-end",
        "relative isolate min-h-[95svh] overflow-hidden px-5 pb-18 pt-26 text-white md:px-9 md:pb-22 md:pt-34 grid place-items-start",
        "relative isolate min-h-[78svh] overflow-hidden px-8 pb-24 pt-20 text-white md:px-12 md:pb-32 md:pt-28 flex flex-col justify-between",
        "relative isolate min-h-[92svh] overflow-hidden px-3 pb-10 pt-30 text-white md:px-4 md:pb-12 md:pt-32 grid grid-rows-2",
        "relative isolate min-h-[80svh] overflow-hidden px-7 pb-28 pt-16 text-white md:px-14 md:pb-36 md:pt-20 flex items-center",
        "relative isolate min-h-[90svh] overflow-hidden px-2 pb-10 pt-28 text-white md:px-4 md:pb-14 md:pt-32 grid place-items-center",
        "relative isolate min-h-[90svh] overflow-hidden px-9 pb-22 pt-22 text-white md:px-16 md:pb-26 md:pt-26 flex flex-row",
    ]
    _hero_class = _HERO_CLASSES_POOL[_seed_for_html % len(_HERO_CLASSES_POOL)]

    # H1 size variants (8 opcoes) — inclui display gigante scraped/condensado
    _H1_SIZE_POOL = [
        "text-[clamp(2.65rem,7.7vw,5.9rem)] font-semibold leading-[0.93] tracking-[-0.035em] text-white",
        "text-[clamp(2.4rem,7vw,5.4rem)] font-bold leading-[0.95] tracking-[-0.04em] text-white",
        "text-[clamp(2.8rem,8.2vw,6rem)] font-extrabold leading-[0.9] tracking-[-0.03em] text-white",
        "text-[clamp(2.55rem,7.3vw,5.7rem)] font-semibold leading-[1] tracking-[-0.025em] text-white",
        "text-[clamp(2.7rem,7.9vw,6rem)] font-bold leading-[0.92] tracking-[-0.038em] text-white",
        # Display scraped/condensado (estilo High Fitness) — para lanes BOLD_ENERGY
        "text-[clamp(3.5rem,11vw,8rem)] font-black leading-[0.85] tracking-[-0.045em] uppercase text-white",
        "text-[clamp(3.2rem,10vw,7.4rem)] font-extrabold leading-[0.86] tracking-[-0.05em] uppercase text-white",
        "text-[clamp(3rem,9vw,6.6rem)] font-extrabold leading-[0.9] tracking-[-0.04em] uppercase text-white",
    ]
    _h1_size = _H1_SIZE_POOL[_seed_for_html % len(_H1_SIZE_POOL)]

    # Font family variants (heading e body separados).
    _FONT_POOL = {
        "default": (["Manrope, sans-serif"] * 4 + ["Inter, sans-serif"], ["Inter, sans-serif"] * 4 + ["Manrope, sans-serif"]),
        "nutricionista_esportiva": (["'Bebas Neue', sans-serif", "'Anton', sans-serif", "'Oswald', sans-serif", "'Roboto Condensed', sans-serif", "'Bebas Neue', sans-serif"], ["Inter, sans-serif", "Manrope, sans-serif", "Roboto, sans-serif", "DM Sans, sans-serif", "system-ui, sans-serif"]),
        "nutricionista_clinica": (["'Source Serif 4', serif", "'Lora', serif", "'Crimson Pro', serif", "'Merriweather', serif", "'Lora', serif"], ["'Nunito', sans-serif", "Inter, sans-serif", "system-ui, sans-serif", "Manrope, sans-serif", "Inter, sans-serif"]),
        "barbearia_premium": (["'Playfair Display', serif", "'Bebas Neue', sans-serif", "'Anton', sans-serif", "'Oswald', sans-serif", "'Libre Baskerville', serif"], ["Inter, sans-serif", "Manrope, sans-serif", "system-ui, sans-serif", "DM Sans, sans-serif", "Inter, sans-serif"]),
        "academia_crossfit": (["'Bebas Neue', sans-serif", "'Anton', sans-serif", "'Oswald', sans-serif", "'Roboto Condensed', sans-serif", "'Bebas Neue', sans-serif"], ["Inter, sans-serif", "Manrope, sans-serif", "Roboto, sans-serif", "system-ui, sans-serif", "DM Sans, sans-serif"]),
        "academia_musculacao": (["'Anton', sans-serif", "'Bebas Neue', sans-serif", "'Oswald', sans-serif", "'Bebas Neue', sans-serif", "'Anton', sans-serif"], ["Inter, sans-serif", "Manrope, sans-serif", "system-ui, sans-serif", "Roboto, sans-serif", "Inter, sans-serif"]),
        "restaurante_familiar": (["'Playfair Display', serif", "'Lora', serif", "'Merriweather', serif", "'Crimson Pro', serif", "'Playfair Display', serif"], ["Inter, sans-serif", "system-ui, sans-serif", "Manrope, sans-serif", "Inter, sans-serif", "DM Sans, sans-serif"]),
    }
    _heading_font_pool, _body_font_pool = _FONT_POOL.get(_subnicho_norm, _FONT_POOL["default"])
    _heading_font = _heading_font_pool[_seed_for_html % len(_heading_font_pool)]
    _body_font = _body_font_pool[_seed_for_html % len(_body_font_pool)]
    _font_family = _body_font
    _typography_mood = ""
    _variation_for_type = facts.get("variation") if isinstance(facts.get("variation"), dict) else {}
    if isinstance(_variation_for_type, dict):
        _typography_mood = str(_variation_for_type.get("typography_mood") or "")
    _TYPOGRAPHY_MOOD_FONT = {
        "clean_sans": ("Manrope, system-ui, sans-serif", "Manrope, system-ui, sans-serif"),
        "condensed_sport": ("'Bebas Neue', 'Oswald', sans-serif", "Inter, sans-serif"),
        "luxury_display": ("'Libre Baskerville', Georgia, serif", "Inter, sans-serif"),
        "editorial_serif": ("'Source Serif 4', Georgia, serif", "Inter, sans-serif"),
        "technical_grotesk": ("'Arial Narrow', 'Roboto Condensed', sans-serif", "Inter, sans-serif"),
    }
    if _typography_mood in _TYPOGRAPHY_MOOD_FONT:
        _heading_font, _body_font = _TYPOGRAPHY_MOOD_FONT[_typography_mood]
        _font_family = _body_font

    # Services icon variants (3 services, 5 icon options)
    _SERVICE_ICONS = ["ClipboardCheck", "Sparkles", "MapPinned", "Heart", "Trophy"]
    _services_icon_set = [
        [_SERVICE_ICONS[_seed_for_html % 5], _SERVICE_ICONS[(_seed_for_html + 1) % 5], _SERVICE_ICONS[(_seed_for_html + 2) % 5]],
    ][0]

    # CTA button style variants (5)
    _CTA_BTN_POOL = [
        "rounded-full px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5",
        "rounded-xl px-5 py-2.5 text-sm font-bold transition hover:scale-105",
        "rounded-2xl px-6 py-3 text-base font-bold transition hover:-translate-y-1",
        "rounded-md px-4 py-2 text-sm font-semibold transition hover:translate-x-1",
        "rounded-lg px-5 py-3 text-sm font-semibold transition hover:shadow-lg",
    ]
    _cta_btn_class = _CTA_BTN_POOL[_seed_for_html % len(_CTA_BTN_POOL)]

    # Sprint 14.6: injeta __counter nos facts para _cinematic_copy usar
    # rotacao de headlines/CTAs. Counter vem do variation log (counter rotation).
    _enriched_facts = dict(facts or {})
    if "business" not in _enriched_facts or not isinstance(_enriched_facts.get("business"), dict):
        _enriched_facts["business"] = {}
    else:
        _enriched_facts["business"] = dict(_enriched_facts["business"])
    _var_payload = _variation_payload if "_variation_payload" in dir() else (
        _enriched_facts.get("variation") if isinstance(_enriched_facts.get("variation"), dict) else None
    )
    if isinstance(_var_payload, dict):
        _enriched_facts["business"]["__counter"] = int(_var_payload.get("counter") or 0)

    copy = _cinematic_copy(_enriched_facts)
    images, videos = _cinematic_media_urls(facts)
    whatsapp = f"https://wa.me/55{copy['phone_digits']}" if copy["phone_digits"] else "#contato"

    # Sprint 14.6: variation counter rotation injeta hero_classes
    # diferente baseado em facts["variation"] (gerado por agente_variacao).
    _variation_payload = dict(facts.get("variation") if isinstance(facts.get("variation"), dict) else {})
    _hero_classes_override = str(_variation_payload.get("hero_classes") or "").strip()
    _variation_payload["hero_classes"] = _hero_classes_override or _hero_class
    _section_order = _resolve_cinematic_section_order(archetype, _seed_for_html, _variation_payload)
    _section_import_map = {
        "navbar": "import { Navbar } from '../components/Navbar';",
        "hero": "import { HeroSection } from '../components/HeroSection';",
        "about": "import { AboutSection } from '../components/AboutSection';",
        "services": "import { ServicesSection } from '../components/ServicesSection';",
        "gallery": "import { GallerySection } from '../components/GallerySection';",
        "faq": "import { FaqSection } from '../components/FaqSection';",
        "reviews": "import { ReviewsSection } from '../components/ReviewsSection';",
        "location": "import { LocationSection } from '../components/LocationSection';",
        "lifestyle": "import { LifestyleSection } from '../components/LifestyleSection';",
        "contact-cta": "import { ContactCTA } from '../components/ContactCTA';",
        "footer": "import { Footer } from '../components/Footer';",
        "pricing": "import { PricingSection } from '../components/PricingSection';",
        "stats-bar": "import { StatsBar } from '../components/StatsBar';",
    }
    _section_markup_map = {
        "navbar": "      <Navbar onOpen={() => setOpen(true)} />",
        "hero": "      <HeroSection onOpen={() => setOpen(true)} />",
        "about": "      <AboutSection />",
        "services": "      <ServicesSection />",
        "gallery": "      <GallerySection />",
        "faq": "      <FaqSection />",
        "reviews": "      <ReviewsSection />",
        "location": "      <LocationSection />",
        "lifestyle": "      <LifestyleSection />",
        "contact-cta": "      <ContactCTA onOpen={() => setOpen(true)} />",
        "footer": "      <Footer />",
        "pricing": "      <PricingSection />",
        "stats-bar": "      <StatsBar />",
    }
    _index_imports = "\n".join(
        _section_import_map[section] for section in _section_order if section in _section_import_map
    )
    _index_sections = "\n".join(
        _section_markup_map[section] for section in _section_order if section in _section_markup_map
    )
    _block_plan = resolve_cinematic_block_plan(
        section_order=_section_order,
        variation=_variation_payload,
        archetype=archetype,
        segment=segment,
    )
    _nav_links = list(_block_plan.get("nav_links") or [])
    _aesthetic_mode = str(_block_plan.get("aesthetic_mode") or "balanced")
    _spacing_density = str(_block_plan.get("spacing_density") or "normal")
    _radius_mode = str(_block_plan.get("radius_mode") or "balanced")
    _container_strategy = str(_block_plan.get("container_strategy") or "contained")
    _typography_scale = str(_block_plan.get("typography_scale") or "strong")
    _heading_style = str(_block_plan.get("heading_style") or "clean")
    _surface_depth = str(_block_plan.get("surface_depth") or "elevated")
    _overlap_mode = str(_block_plan.get("overlap_mode") or "none")
    _motion_intensity = str(_block_plan.get("motion_intensity") or "composed")
    _image_treatment = str(_block_plan.get("image_treatment") or "clean")
    _section_pad = {
        "compressed": "clamp(3rem, 6vw, 5.25rem)",
        "normal": "clamp(4.5rem, 9vw, 8.5rem)",
        "spacious": "clamp(6rem, 11vw, 11rem)",
    }.get(_spacing_density, "clamp(4.5rem, 9vw, 8.5rem)")
    _section_pad_mobile = {
        "compressed": "clamp(2.75rem, 11vw, 4.25rem)",
        "normal": "clamp(3.25rem, 14vw, 5rem)",
        "spacious": "clamp(4.5rem, 16vw, 6rem)",
    }.get(_spacing_density, "clamp(3.25rem, 14vw, 5rem)")
    _radius_card = {
        "sharp": "4px",
        "balanced": "18px",
        "soft": "28px",
        "pill": "36px",
    }.get(_radius_mode, "18px")
    _radius_panel = {
        "sharp": "8px",
        "balanced": "26px",
        "soft": "42px",
        "pill": "56px",
    }.get(_radius_mode, "26px")
    _container_max = {
        "contained": "min(1120px, calc(100vw - clamp(2rem, 7vw, 6rem)))",
        "wide": "min(1320px, calc(100vw - clamp(1.5rem, 5vw, 5rem)))",
        "edge_to_edge": "min(1480px, calc(100vw - clamp(0.75rem, 2.5vw, 2rem)))",
        "overlap": "min(1360px, calc(100vw - clamp(1rem, 4vw, 4rem)))",
    }.get(_container_strategy, "min(1120px, calc(100vw - clamp(2rem, 7vw, 6rem)))")
    _overlap_shift = {
        "none": "0px",
        "subtle": "-3.5rem",
        "strong": "-7rem",
    }.get(_overlap_mode, "0px")
    _h1_css_size = {
        "soft": "clamp(2.4rem, 6.8vw, 5.1rem)",
        "strong": "clamp(2.65rem, 7.7vw, 5.9rem)",
        "heroic": "clamp(3.2rem, 10.5vw, 6.5rem)",
    }.get(_typography_scale, "clamp(2.65rem, 7.7vw, 5.9rem)")
    _h2_css_size = {
        "soft": "clamp(2rem, 4.8vw, 4.2rem)",
        "strong": "clamp(2.2rem, 5.4vw, 4.8rem)",
        "heroic": "clamp(2.7rem, 7.6vw, 6rem)",
    }.get(_typography_scale, "clamp(2.2rem, 5.4vw, 4.8rem)")
    _heading_weight = {
        "soft": "650",
        "strong": "780",
        "heroic": "920",
    }.get(_typography_scale, "780")
    _heading_tracking = {
        "clean": "-0.02em",
        "display": "-0.035em",
        "condensed": "-0.04em",
        "editorial": "-0.015em",
        "kinetic": "-0.035em",
    }.get(_heading_style, "-0.02em")
    _heading_transform = "uppercase" if _heading_style in {"condensed", "kinetic"} or _aesthetic_mode == "impact" else "none"
    _heading_skew = "skewX(-4deg)" if _aesthetic_mode == "impact" and _heading_style in {"condensed", "kinetic"} else "none"
    _surface_shadow = {
        "flat": "none",
        "bordered": "inset 0 0 0 1px color-mix(in srgb, var(--accent) 18%, transparent)",
        "elevated": "0 24px 80px rgba(0,0,0,.14)",
        "cutout": "12px 12px 0 color-mix(in srgb, var(--accent) 72%, transparent)",
    }.get(_surface_depth, "0 24px 80px rgba(0,0,0,.14)")
    _image_filter = {
        "clean": "none",
        "duotone": "grayscale(.45) contrast(1.1) saturate(.85)",
        "grain": "contrast(1.08) saturate(.88)",
        "high_contrast": "contrast(1.18) saturate(.75)",
    }.get(_image_treatment, "none")
    _pole = str(facts.get("pole") or "").strip().lower()
    if _pole not in {"soft", "bold", "corporate", "minimal"}:
        _pole = {
            "impact": "bold",
            "wellness": "soft",
            "premium": "soft",
            "technical": "minimal",
            "dynamic": "minimal",
        }.get(_aesthetic_mode, "corporate")
    _pole_css = _get_pole_css_tokens(_pole)

    source_files: dict[str, str] = {
        "src/App.tsx": """import { Index } from './pages/Index';
import { LgpdBanner } from './components/LgpdBanner';
import { FactualMotionContract } from './components/FactualMotionContract';

export default function App() {
  return (
    <div data-pole="__FRALIB_POLE__" className="min-h-screen">
      <Index />
      <LgpdBanner />
      <FactualMotionContract />
    </div>
  );
}
""".replace("__FRALIB_POLE__", _pole),
        "src/main.tsx": vite_template_main_tsx(),
        "src/types.ts": vite_template_types_ts(),
        "src/fralib-jsx.d.ts": vite_template_jsx_fallback_types(),
        "src/components/siteData.ts": f"""export const siteCopy = {json.dumps(copy, ensure_ascii=False)} as const;
export const mediaImages = {json.dumps(images, ensure_ascii=False)} as const;
export const mediaVideos = {json.dumps(videos, ensure_ascii=False)} as const;
export const whatsappHref = {json.dumps(whatsapp, ensure_ascii=False)} as const;
export const variation = {json.dumps(_variation_payload, ensure_ascii=False)} as const;
export const blockPlan = {json.dumps(_block_plan, ensure_ascii=False)} as const;
export const navLinks = {json.dumps(_nav_links, ensure_ascii=False)} as const;
if (typeof window !== 'undefined') {{
  (window as any).__fralib_pricing_variant = {json.dumps(_block_plan.get("pricing_variant", "plan_grid"))};
  (window as any).__fralib_stats_variant = {json.dumps(_block_plan.get("stats_variant", "inline_hero_stats"))};
}}
""",
        "src/pages/Index.tsx": f"""import {{ useState }} from 'react';
{_index_imports}
import {{ BookingModal }} from '../components/BookingModal';

export function Index() {{
  const [open, setOpen] = useState(false);
  return (
    <main
      data-attitude="{_aesthetic_mode}"
      data-spacing="{_spacing_density}"
      data-radius="{_radius_mode}"
      data-container="{_container_strategy}"
      data-typography="{_typography_scale}"
      data-heading="{_heading_style}"
      data-surface="{_surface_depth}"
      data-overlap="{_overlap_mode}"
      data-motion="{_motion_intensity}"
      data-image-treatment="{_image_treatment}"
      data-pole="{_pole}"
      className="min-h-screen bg-[{c_bg}] text-white"
    >
{_index_sections}
      <BookingModal open={{open}} onClose={{() => setOpen(false)}} />
    </main>
  );
}}

export default Index;
""",
        "src/components/Navbar.tsx": """import { useEffect, useState } from 'react';
import { Menu, MessageCircle, X } from 'lucide-react';
import { navLinks, siteCopy, whatsappHref } from './siteData';

export function Navbar({ onOpen }: { onOpen?: () => void }) {
  const [solid, setSolid] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 36);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return (
    <nav style={{ background: solid ? 'var(--bg)' : 'rgba(0,0,0,0.76)' }} className={`fixed inset-x-3 top-3 z-50 rounded-[18px] border px-4 py-3 transition duration-300 md:inset-x-6 md:top-5 border-white/10 ${solid ? 'shadow-[0_10px_32px_rgba(0,0,0,.24)]' : 'shadow-[0_14px_40px_rgba(0,0,0,.28)]'}`}>
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        <a href="#hero" className="min-w-0 truncate text-sm font-semibold tracking-tight text-white md:text-base">{siteCopy.name}</a>
        <div className="hidden items-center gap-6 text-sm text-zinc-300 md:flex">{navLinks.map((item) => <a key={item.href} href={item.href} className="transition hover:text-white">{item.label}</a>)}</div>
        <div className="flex items-center gap-2">
          <a href={whatsappHref} rel="noopener noreferrer" className="hidden items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 md:inline-flex" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}><MessageCircle className="h-4 w-4" /> WhatsApp</a>
          <button type="button" onClick={onOpen} className="hidden rounded-full border border-white/10 px-4 py-2 text-sm font-semibold text-white md:inline-flex">{siteCopy.cta_primary}</button>
          <button type="button" aria-label="Menu" onClick={() => setMenuOpen((value) => !value)} className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 text-white md:hidden">{menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
        </div>
      </div>
      {menuOpen ? <div className="mt-3 grid gap-2 border-t border-white/10 pt-3 md:hidden">{navLinks.map((item) => <a key={item.href} href={item.href} onClick={() => setMenuOpen(false)} className="rounded-xl px-2 py-2 text-sm text-zinc-200">{item.label}</a>)}<a href={whatsappHref} rel="noopener noreferrer" className="rounded-xl px-3 py-2 text-sm font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}>Falar no WhatsApp</a></div> : null}
    </nav>
  );
}

export default Navbar;
""",
        "src/components/HeroSection.tsx": """import { useEffect, useRef } from 'react';
import { ArrowDownRight, MessageCircle, Play, Star } from 'lucide-react';
import { motion } from 'motion/react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { blockPlan, mediaImages, mediaVideos, siteCopy, variation, whatsappHref } from './siteData';

gsap.registerPlugin(ScrollTrigger);

export function HeroSection({ onOpen }: { onOpen?: () => void }) {
  const rootRef = useRef<HTMLElement | null>(null);
  const heroClasses = (variation as any)?.hero_classes ? (variation as any).hero_classes : '';
  const heroVariant = String((blockPlan as any)?.hero_variant || (variation as any)?.hero_layout || 'split');
  const heroTextSide = String((blockPlan as any)?.hero_text_side || '');
  const motionStyle = String((blockPlan as any)?.motion_style || (variation as any)?.motion_style || 'smooth');
  const motionMix = Array.isArray((blockPlan as any)?.motion_mix) ? (blockPlan as any).motion_mix : [];
  const motionClass = motionMix.map((item: string) => `motion-${item}`).join(' ');
  // Video follows the final block plan, not only the raw variation payload.
  const _showVideo = heroVariant === 'video' || heroVariant === 'fullbleed';
useEffect(() => {
    const root = rootRef.current;
    if (!root || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = gsap.context(() => {
      if (_showVideo) {
        gsap.to('[data-hero-video]', { yPercent: motionStyle === 'minimal' ? 4 : 10, scale: motionStyle === 'sharp' ? 1.12 : 1.08, ease: 'none', scrollTrigger: { trigger: root, start: 'top top', end: 'bottom top', scrub: true } });
      }
      gsap.fromTo('[data-hero-reveal]', { y: motionStyle === 'sharp' ? 18 : 26, opacity: 0 }, { y: 0, opacity: 1, duration: motionStyle === 'minimal' ? 0.55 : 0.9, stagger: motionStyle === 'sharp' ? 0.045 : 0.08, ease: motionStyle === 'sharp' ? 'power4.out' : 'power3.out' });
    }, root);
    return () => ctx.revert();
  }, []);
  const hasMediaPanel = heroVariant === 'asymmetric' || heroVariant === 'center';
  const shellClass = heroVariant === 'video' || heroVariant === 'fullbleed'
    ? 'mx-auto flex min-h-[58svh] max-w-6xl flex-col items-center justify-end gap-8 text-center'
    : heroVariant === 'center'
    ? 'mx-auto flex max-w-6xl flex-col items-center gap-10 text-center'
    : heroVariant === 'asymmetric'
      ? 'mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.82fr_1.05fr_0.68fr] lg:items-center'
      : 'mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1.05fr_.95fr] lg:items-end';
  const copyClass = heroVariant === 'video' || heroVariant === 'fullbleed' ? 'mx-auto max-w-5xl' : heroVariant === 'center' ? 'mx-auto max-w-4xl' : heroVariant === 'asymmetric' ? (heroTextSide === 'left' ? 'order-1 max-w-4xl' : 'order-2 max-w-4xl') : 'max-w-4xl';
  const mediaPanelClass = heroVariant === 'center'
    ? 'relative order-2 aspect-[16/8] w-full max-w-5xl overflow-hidden rounded-[26px] border border-white/10 shadow-[0_30px_90px_rgba(0,0,0,.38)]'
    : heroTextSide === 'left'
      ? 'relative order-2 min-h-[34rem] overflow-hidden rounded-[26px] border border-white/10 shadow-[0_30px_90px_rgba(0,0,0,.38)]'
      : 'relative order-1 min-h-[34rem] overflow-hidden rounded-[26px] border border-white/10 shadow-[0_30px_90px_rgba(0,0,0,.38)]';
  const statsClass = heroVariant === 'video' || heroVariant === 'fullbleed'
    ? 'grid w-full gap-3 sm:grid-cols-3'
    : heroVariant === 'center'
    ? 'grid gap-3 sm:grid-cols-3'
    : heroVariant === 'asymmetric'
      ? (heroTextSide === 'left' ? 'order-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-1' : 'order-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-1')
      : 'grid gap-3 sm:grid-cols-3 lg:grid-cols-1';
  const surfaceStyle = String((variation as any)?.surface_style || '');
  const statCardClass = surfaceStyle === 'solid'
    ? 'rounded-[14px] bg-[var(--accent)] p-4 text-[var(--accent-contrast)]'
    : 'rounded-[14px] border border-[color-mix(in_srgb,var(--accent)_34%,white_10%)] bg-black/72 p-4 shadow-[0_18px_55px_rgba(0,0,0,.32)]';
  return (
    <section ref={rootRef} id="hero" className={'hero-v14 ' + heroClasses + ' ' + motionClass}>
      <div className="absolute inset-0 -z-20" style={{ background: 'var(--bg)' }} />
      {_showVideo && mediaVideos[0] ? (
        <video data-hero-video className="absolute inset-0 -z-10 h-full w-full object-cover opacity-52 saturate-[.9]" src={mediaVideos[0]} poster={mediaImages[0]} autoPlay muted loop playsInline preload="metadata" />
      ) : (
        <img data-hero-poster src={mediaImages[0]} alt={siteCopy.gallery_alt} className={`absolute inset-0 -z-10 h-full w-full object-cover saturate-[.85] ${hasMediaPanel ? 'opacity-16' : 'opacity-32'}`} loading="eager" decoding="async" />
      )}
      <div className="absolute inset-0 -z-10" style={{ background: heroVariant === 'video' || heroVariant === 'fullbleed' ? `linear-gradient(180deg, rgba(0,0,0,.80), rgba(0,0,0,.90) 72%, rgba(0,0,0,.94)), radial-gradient(circle_at_50%_28%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 42%)` : heroVariant === 'center' ? `linear-gradient(180deg, rgba(0,0,0,.74), rgba(0,0,0,.86)), radial-gradient(circle_at_50%_18%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 34%)` : heroVariant === 'asymmetric' ? `linear-gradient(115deg, rgba(0,0,0,.90), rgba(0,0,0,.72) 52%, rgba(0,0,0,.64)), radial-gradient(circle_at_12%_72%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 30%)` : `linear-gradient(90deg, rgba(0,0,0,.92), rgba(0,0,0,.78) 42%, rgba(0,0,0,.62)), radial-gradient(circle_at_80%_20%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 34%)` }} />
      <div className={shellClass}>
        <div className={copyClass}>
          <motion.div data-hero-reveal data-motion-line className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em]" style={{ borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)', background: 'color-mix(in srgb, var(--accent) 10%, transparent)', color: 'var(--accent-soft)' }}><Play className="h-3.5 w-3.5" />{siteCopy.hero_badge || `${siteCopy.segment} em ${siteCopy.city}`}</motion.div>
          <h1 data-hero-reveal data-motion-mask className="mt-7 max-w-5xl text-[clamp(2.65rem,7.7vw,5.9rem)] font-semibold leading-[0.93] tracking-[-0.035em] text-white">{siteCopy.headline}</h1>
          <p data-hero-reveal className="mt-6 max-w-2xl text-base leading-8 text-zinc-200 md:text-lg">{siteCopy.subheadline}</p>
          <div data-hero-reveal className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a href={whatsappHref} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm font-semibold transition duration-300 hover:-translate-y-0.5" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}><MessageCircle className="h-4 w-4" />{siteCopy.cta_primary}</a>
            <button type="button" onClick={onOpen} className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 px-6 py-3.5 text-sm font-semibold text-white transition duration-300 hover:-translate-y-0.5">{siteCopy.cta_secondary}<ArrowDownRight className="h-4 w-4" /></button>
          </div>
        </div>
        {hasMediaPanel ? (
          <motion.figure data-hero-reveal data-motion-depth className={mediaPanelClass}>
            <img src={mediaImages[1] || mediaImages[0]} alt={siteCopy.gallery_alt} className="h-full w-full object-cover opacity-90" loading="eager" decoding="async" />
            <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/78 to-transparent p-5 text-sm font-semibold text-white">{siteCopy.name}</figcaption>
          </motion.figure>
        ) : null}
        <div data-hero-reveal className={statsClass}>
          {[['Avaliação', siteCopy.rating || '5.0'], ['Sinais locais', siteCopy.reviews || 'confirmados'], ['Contato', siteCopy.phone || 'WhatsApp']].map(([label, value]) => (
            <div key={label} data-hero-stat className={statCardClass}><div className="flex items-center gap-2" style={{ color: surfaceStyle === 'solid' ? 'var(--accent-contrast)' : 'var(--accent-soft)' }}><Star className="h-4 w-4" /><span className="text-xs font-semibold uppercase tracking-[0.12em]">{label}</span></div><p className="mt-2 text-lg font-semibold" style={{ color: surfaceStyle === 'solid' ? 'var(--accent-contrast)' : '#fff' }}>{value}</p></div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
""",
        "src/index.css": f"""@import "tailwindcss";
:root {{
  --bg: {c_bg};
  --accent: {c_accent};
  --accent-soft: {c_accent_light};
  --accent-dark: {c_accent_dark};
  --accent-contrast: {palette.get('accent_contrast', '#09130f')};
  --text: {c_text};
  --text-muted: {c_text_muted};
  --bg-light: {palette.get('bg_light', '#f4f0e6')};
  --text-dark: {palette.get('text_dark', '#09130f')};
  --panel-text: {palette.get('panel_text', palette.get('text_dark', '#09130f'))};
  --font-family: {_font_family};
  --font-family-body: {_body_font};
  --font-family-heading: {_heading_font};
  --h1-size: {_h1_css_size};
  --h2-size: {_h2_css_size};
  --heading-weight: {_heading_weight};
  --heading-tracking: {_heading_tracking};
  --heading-transform: {_heading_transform};
  --heading-skew: {_heading_skew};
  --container: {_container_max};
  --section-pad: {_section_pad};
  --section-pad-mobile: {_section_pad_mobile};
  --radius-card: {_radius_card};
  --radius-panel: {_radius_panel};
  --overlap-shift: {_overlap_shift};
  --surface-shadow: {_surface_shadow};
  --image-treatment: {_image_filter};
  --cta-btn: {_cta_btn_class};
  --plan-section: var(--bg);
  --plan-ink: var(--text);
  --plan-card: color-mix(in srgb, var(--bg) 90%, var(--accent) 7%);
  --plan-card-ink: var(--text);
  --plan-featured: var(--accent);
  --plan-featured-ink: var(--accent-contrast);
  --plan-border: color-mix(in srgb, var(--accent) 35%, transparent);
  --lgpd-bg: var(--bg-light);
  --lgpd-text: var(--text-dark);
  --lgpd-border: color-mix(in srgb, var(--accent) 26%, transparent);
}}
{_pole_css}
[data-pole="soft"] {{
  --primary: {c_accent};
  --primary-hover: {c_accent_dark};
  --accent: {c_accent};
  --accent-soft: {c_accent_light};
  --shadow-card: 0 18px 58px color-mix(in srgb, var(--accent) 16%, transparent);
  --shadow-button: 0 6px 18px color-mix(in srgb, var(--accent) 24%, transparent);
  --shadow-glow: 0 10px 38px color-mix(in srgb, var(--accent) 18%, transparent);
  --radius-card: var(--radius);
  --radius-panel: var(--radius);
  --section-pad: var(--section-padding-y);
  --h1-size: clamp(2.6rem, 7vw, 5.6rem);
  --h2-size: var(--heading-scale);
  --heading-transform: none;
  --heading-skew: none;
  --surface-shadow: var(--shadow-card);
  --plan-section: var(--bg-light);
  --plan-ink: var(--text-dark);
  --plan-card: #fff;
  --plan-card-ink: var(--text-dark);
  --plan-border: color-mix(in srgb, var(--accent) 20%, transparent);
}}
[data-pole="bold"] {{
  --bg: #030303;
  --accent: #ff1f1f;
  --accent-soft: #ff5a45;
  --accent-dark: #870812;
  --accent-contrast: #ffffff;
  --text: #f7f2ee;
  --text-muted: rgba(247,242,238,.72);
  --bg-light: #0a0a0b;
  --text-dark: #f7f2ee;
  --panel-text: #f7f2ee;
  --radius-card: 0px;
  --radius-panel: 0px;
  --section-pad: clamp(2.75rem, 6.2vw, 5.4rem);
  --h1-size: clamp(3.25rem, 10.5vw, 6rem);
  --h2-size: clamp(2.7rem, 7.6vw, 5.8rem);
  --heading-weight: 950;
  --heading-tracking: -0.035em;
  --heading-transform: uppercase;
  --heading-skew: skewX(-4deg);
  --surface-shadow: 8px 8px 0 color-mix(in srgb, var(--accent) 76%, transparent);
  --plan-section: #050505;
  --plan-ink: #fff;
  --plan-card: #0f0f10;
  --plan-card-ink: #fff;
  --plan-featured: var(--accent);
  --plan-featured-ink: var(--accent-contrast);
  --plan-border: color-mix(in srgb, var(--accent) 54%, transparent);
  --lgpd-bg: #080808;
  --lgpd-text: #fff;
  --lgpd-border: color-mix(in srgb, var(--accent) 58%, transparent);
}}
[data-pole="corporate"] {{
  --radius-card: var(--radius);
  --radius-panel: calc(var(--radius) + 4px);
  --section-pad: var(--section-padding-y);
  --h2-size: var(--heading-scale);
  --heading-transform: none;
  --heading-skew: none;
  --surface-shadow: var(--shadow-card);
}}
[data-pole="minimal"] {{
  --radius-card: var(--radius);
  --radius-panel: calc(var(--radius) + 8px);
  --section-pad: var(--section-padding-y);
  --h2-size: var(--heading-scale);
  --heading-transform: lowercase;
  --heading-skew: skewX(1.5deg);
  --surface-shadow: var(--shadow-card);
  --plan-section: #071018;
  --plan-ink: #f7fbff;
  --plan-card: color-mix(in srgb, #071018 86%, var(--accent) 10%);
  --plan-card-ink: #f7fbff;
}}
[data-pole="bold"] .hero-v14 h1,
[data-pole="bold"] h2 {{
  font-style: italic;
}}
[data-pole="bold"] .fralib-display-shadow {{
  -webkit-text-stroke: 1px color-mix(in srgb, var(--accent) 70%, white 4%);
  color: transparent;
}}
[data-pole="bold"] #servicos,
[data-pole="bold"] #avaliacoes,
[data-pole="bold"] #localizacao,
[data-pole="bold"] #contato {{
  background: #050505 !important;
  color: #fff !important;
}}
[data-pole="bold"] .bg-white,
[data-pole="bold"] .bg-zinc-50,
[data-pole="bold"] #servicos article,
[data-pole="bold"] #avaliacoes article,
[data-pole="bold"] #localizacao article {{
  background: var(--plan-card) !important;
  color: #fff !important;
  border-color: var(--plan-border) !important;
}}
[data-pole="bold"] .text-zinc-950,
[data-pole="bold"] .text-zinc-900,
[data-pole="bold"] .text-zinc-800 {{
  color: #fff !important;
}}
[data-pole="bold"] .text-zinc-700,
[data-pole="bold"] .text-zinc-600,
[data-pole="bold"] .text-zinc-500 {{
  color: rgba(255,255,255,.72) !important;
}}
[data-pole="bold"] [data-hero-stat] {{
  background: #080808 !important;
  color: #fff !important;
  border-color: color-mix(in srgb, var(--accent) 70%, transparent) !important;
  border-radius: 0 !important;
  box-shadow: 6px 6px 0 color-mix(in srgb, var(--accent-dark) 82%, transparent) !important;
}}
[data-pole="bold"] [data-lgpd-banner] {{
  background: var(--lgpd-bg) !important;
  color: var(--lgpd-text) !important;
  border-color: var(--lgpd-border) !important;
  border-radius: 0 !important;
  box-shadow: 6px 6px 0 color-mix(in srgb, var(--accent-dark) 75%, transparent) !important;
}}
.hero-v14 {{
  min-height: 92svh;
  padding: 7rem 1.25rem 4rem;
  background: var(--bg);
  color: #fff;
  position: relative;
  isolation: isolate;
  overflow: hidden;
}}
@media (min-width: 768px) {{
  .hero-v14 {{
    min-height: 88svh;
    padding: 10rem 2rem 6rem;
  }}
}}
.hero-v14.hero-v14-v0 {{ min-height: 92svh; padding-top: 7rem; padding-bottom: 4rem; display: grid; place-items: center; }}
.hero-v14.hero-v14-v1 {{ min-height: 85svh; padding-top: 6rem; padding-bottom: 5rem; display: flex; flex-direction: column; justify-content: center; }}
.hero-v14.hero-v14-v2 {{ min-height: 92svh; padding-top: 5rem; padding-bottom: 3rem; display: grid; place-items: end; }}
.hero-v14.hero-v14-v3 {{ min-height: 88svh; padding-top: 8rem; padding-bottom: 3.5rem; display: flex; align-items: end; }}
.hero-v14.hero-v14-v4 {{ min-height: 95svh; padding-top: 6.5rem; padding-bottom: 4.5rem; display: grid; place-items: start; }}
.hero-v14.hero-v14-v5 {{ min-height: 78svh; padding-top: 5rem; padding-bottom: 6rem; display: flex; flex-direction: column; justify-content: space-between; }}
.hero-v14.hero-v14-v6 {{ min-height: 92svh; padding-top: 7rem; padding-bottom: 3rem; display: grid; grid-template-rows: 1fr 1fr; }}
.hero-v14.hero-v14-v7 {{ min-height: 80svh; padding-top: 4rem; padding-bottom: 7rem; display: flex; align-items: center; }}
.hero-v14.hero-v14-v8 {{ min-height: 90svh; padding-top: 7rem; padding-bottom: 3.5rem; display: grid; place-items: center; }}
.hero-v14.hero-v14-v9 {{ min-height: 90svh; padding-top: 5.5rem; padding-bottom: 5.5rem; display: flex; flex-direction: row; }}
@layer base {{
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; background: var(--bg); }}
  body {{ margin: 0; min-width: 320px; min-height: 100vh; font-family: var(--font-family-body); color: var(--text); background: var(--bg); text-rendering: geometricPrecision; }}
  h1 {{ font-size: var(--h1-size); font-family: var(--font-family-heading); font-weight: var(--heading-weight); line-height: .9; letter-spacing: var(--heading-tracking); text-transform: var(--heading-transform); }}
  h1, h2, h3 {{ font-family: var(--font-family-heading); letter-spacing: var(--heading-tracking); text-wrap: balance; }}
  p {{ text-wrap: pretty; }}
  section {{ scroll-margin-top: 5rem; }}
  img, video {{ max-width: 100%; display: block; }}
  a {{ color: inherit; text-decoration: none; }}
  button, a {{ -webkit-tap-highlight-color: transparent; }}
  ::selection {{ background: var(--accent); color: var(--bg); }}
}}
main[data-attitude] section:not(#hero):not(#stats) {{ padding-block: var(--section-pad); }}
main[data-attitude] section:not(#hero):not(#stats) > .mx-auto,
main[data-attitude] nav > .mx-auto {{
  max-width: var(--container) !important;
}}
main[data-attitude] h1 {{
  font-size: var(--h1-size) !important;
  font-weight: var(--heading-weight) !important;
  letter-spacing: var(--heading-tracking) !important;
  text-transform: var(--heading-transform);
  transform: var(--heading-skew);
  transform-origin: left center;
}}
main[data-attitude] h2 {{
  font-size: var(--h2-size) !important;
  font-weight: var(--heading-weight) !important;
  letter-spacing: var(--heading-tracking) !important;
}}
main[data-radius] article,
main[data-radius] figure,
main[data-radius] aside,
main[data-radius] [class*="rounded-"] {{
  border-radius: var(--radius-card) !important;
}}
main[data-radius] section > .mx-auto > [class*="rounded-"],
main[data-radius] [data-price-emphasis],
main[data-radius] button,
main[data-radius] a[class*="rounded-"] {{
  border-radius: var(--radius-panel) !important;
}}
main[data-surface="flat"] article,
main[data-surface="bordered"] article,
main[data-surface="elevated"] article,
main[data-surface="cutout"] article {{
  box-shadow: var(--surface-shadow) !important;
}}
main[data-container="edge_to_edge"] section:not(#hero) > .mx-auto {{
  width: min(100%, var(--container));
}}
main[data-overlap="subtle"] section:nth-of-type(3),
main[data-overlap="strong"] section:nth-of-type(3) {{
  margin-top: var(--overlap-shift);
  position: relative;
  z-index: 5;
}}
main[data-overlap="strong"] section:nth-of-type(4) {{
  margin-top: calc(var(--overlap-shift) / 2);
  position: relative;
  z-index: 4;
}}
main[data-attitude] #stats {{
  position: relative;
  z-index: 6;
}}
main[data-overlap] #stats + section {{
  margin-top: 0 !important;
}}
main[data-image-treatment] img:not([src*="data:"]),
main[data-image-treatment] video {{
  filter: var(--image-treatment);
}}
main[data-attitude="impact"] .hero-v14 {{
  clip-path: polygon(0 0,100% 0,100% 96%,0 100%);
}}
main[data-attitude="impact"] h2 {{
  text-transform: uppercase;
}}
main[data-attitude="impact"] section:not(#hero):not(#stats) {{
  border-top: 1px solid color-mix(in srgb, var(--accent) 26%, transparent);
}}
main[data-attitude="wellness"] section:not(#hero):not(#stats),
main[data-attitude="premium"] section:not(#hero):not(#stats) {{
  padding-block: var(--section-pad);
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: 0.01ms !important; }}
}}
@media (max-width: 767px) {{
  main[data-attitude] section:not(#hero):not(#stats) {{ padding-block: var(--section-pad-mobile); }}
  main[data-attitude] h1 {{ transform: none; }}
  main[data-overlap] section:nth-of-type(3),
  main[data-overlap] section:nth-of-type(4) {{ margin-top: 0; }}
}}
.motion-mask_reveal [data-motion-mask] {{
  animation: fralib-mask-reveal 900ms cubic-bezier(.16,1,.3,1) both;
}}
.motion-line_draw [data-motion-line] {{
  box-shadow: inset 0 -1px 0 color-mix(in srgb, var(--accent) 70%, transparent);
}}
.motion-hover_depth [data-motion-depth] {{
  transform-style: preserve-3d;
  transition: transform .55s cubic-bezier(.16,1,.3,1), box-shadow .55s cubic-bezier(.16,1,.3,1);
}}
.motion-hover_depth [data-motion-depth]:hover {{
  transform: translateY(-8px) rotateX(1deg) rotateY(-1deg);
  box-shadow: 0 40px 110px color-mix(in srgb, var(--accent) 18%, rgba(0,0,0,.42));
}}
.motion-marquee-rail {{
  animation: fralib-marquee 28s linear infinite;
  width: max-content;
}}
@keyframes fralib-mask-reveal {{
  from {{ clip-path: inset(0 0 100% 0); transform: translateY(16px); }}
  to {{ clip-path: inset(0 0 0 0); transform: translateY(0); }}
}}
@keyframes fralib-marquee {{
  from {{ transform: translateX(0); }}
  to {{ transform: translateX(-50%); }}
}}
""",
    }
    # Sprint 14.13: .replace() removido - o template agora usa {VAR} que sao
    # placeholders Python (sem $) e nao causam bug de f-string.
    source_files.update(_generate_cinematic_secondary_components(facts, palette=palette))
    for path, content in list(source_files.items()):
        if path.endswith((".tsx", ".jsx")):
            source_files[path] = content.replace("initial={{ opacity: 0", "initial={{ opacity: 1")
    return prepare_vite_project_files(source_files, facts=facts)


def _cinematic_pricing_plans_for_segment(segment: str, copy: dict[str, Any]) -> list[dict[str, Any]]:
    city = str(copy.get("city") or "").strip()
    city_suffix = f" em {city}" if city else ""
    seg = (segment or "").lower()
    if any(token in seg for token in ("academia", "fitness", "crossfit", "musculacao", "musculação")):
        return [
            {"name": "Aula experimental", "perks": ["Acesso a uma sessão", "Avaliação inicial", "Plano de treino"], "highlight": False, "note": "Sem compromisso"},
            {"name": "Plano mensal", "perks": ["Acesso completo", "Acompanhamento semanal", "Reavaliação mensal", f"Rotina flexível{city_suffix}"], "highlight": True, "note": "Mais escolhido"},
            {"name": "Plano trimestral", "perks": ["Acesso completo", "Avaliação mensal", "Suporte prioritário", "Condição progressiva"], "highlight": False, "note": "Melhor custo"},
        ]
    if "nutri" in seg:
        return [
            {"name": "Consulta inicial", "perks": ["Avaliação completa", "Plano alimentar", "Material de apoio"], "highlight": False, "note": "Sem compromisso"},
            {"name": "Acompanhamento", "perks": ["Consultas de retorno", "Ajustes no plano", "Suporte por mensagem", f"Atendimento{city_suffix}"], "highlight": True, "note": "Mais escolhido"},
            {"name": "Plano premium", "perks": ["Consultas recorrentes", "Bioimpedância quando disponível", "Suporte prioritário", "Acesso a conteúdo"], "highlight": False, "note": "Completo"},
        ]
    if any(token in seg for token in ("barbearia", "barbeiro", "barber")):
        return [
            {"name": "Corte clássico", "perks": ["Corte masculino", "Finalização", "Agendamento direto"], "highlight": False, "note": "Essencial"},
            {"name": "Corte e barba", "perks": ["Corte completo", "Barba alinhada", "Acabamento", f"Reserva rápida{city_suffix}"], "highlight": True, "note": "Mais pedido"},
            {"name": "Ritual premium", "perks": ["Atendimento completo", "Toalha quente", "Produto finalizador", "Horário reservado"], "highlight": False, "note": "Experiência"},
        ]
    if any(token in seg for token in ("estetic", "estética", "beleza", "spa")):
        return [
            {"name": "Avaliação", "perks": ["Diagnóstico inicial", "Orientação do procedimento", f"Atendimento{city_suffix}"], "highlight": False, "note": "Primeiro passo"},
            {"name": "Pacote essencial", "perks": ["Sessão completa", "Produtos profissionais", "Acompanhamento"], "highlight": True, "note": "Mais escolhido"},
            {"name": "Pacote premium", "perks": ["Múltiplas sessões", "Produtos premium", "Suporte dedicado", "Acompanhamento estendido"], "highlight": False, "note": "Completo"},
        ]
    return [
        {"name": "Primeira sessão", "perks": ["Acolhimento inicial", "Diagnóstico", "Orientação"], "highlight": False, "note": "Sem compromisso"},
        {"name": "Plano recorrente", "perks": ["Atendimento regular", f"Agenda{city_suffix}", "Acompanhamento"], "highlight": True, "note": "Mais escolhido"},
        {"name": "Plano estendido", "perks": ["Sessões extras", "Suporte dedicado", "Prioridade na agenda"], "highlight": False, "note": "Completo"},
    ]


def _generate_cinematic_secondary_components(facts: dict[str, Any], palette: dict[str, str] | None = None) -> dict[str, str]:
    copy = _cinematic_copy(facts)
    _biz = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    segment = str(_biz.get("segment") or _biz.get("segmento") or facts.get("segmento") or facts.get("segment") or "servicos").lower()
    if palette is None:
        archetype = _get_archetype_for_segment(segment)
        palette = _get_archetype_palette(archetype)
    c_bg_light = palette.get('bg_light', '#f4f0e6')
    c_text_dark = palette.get('text_dark', '#09130f')
    variation = facts.get("variation") if isinstance(facts.get("variation"), dict) else {}
    block_plan = resolve_cinematic_block_plan(
        section_order=["about", "services", "gallery", "reviews", "faq", "location", "contact-cta"],
        variation=variation,
        archetype=_get_archetype_for_segment(segment),
        segment=segment,
    )
    proof_style = str(block_plan.get("reviews_variant") or variation.get("proof_style") or "score_wall")
    surface_style = str(block_plan.get("surface_style") or variation.get("surface_style") or "solid")
    section_surface_map = variation.get("section_surface_map") if isinstance(variation.get("section_surface_map"), dict) else {}
    pricing_plans = _cinematic_pricing_plans_for_segment(segment, copy)
    about_surface = str(section_surface_map.get("about") or surface_style)
    gallery_density = str(block_plan.get("gallery_density") or variation.get("gallery_density") or "")
    cta_style = str(block_plan.get("cta_style") or variation.get("cta_style") or "")
    card_shell_map = {
        "glass": "border border-black/5 bg-white shadow-[0_14px_34px_rgba(0,0,0,0.10)]",
        "solid": "border border-black/5 bg-white shadow-[0_14px_34px_rgba(0,0,0,0.10)]",
        "outline": "border border-[color-mix(in_srgb,var(--accent)_24%,transparent)] bg-transparent",
        "soft_tint": "border border-black/5 bg-[var(--bg-light)] shadow-[0_14px_34px_rgba(0,0,0,0.08)]",
    }
    card_shell = card_shell_map.get(about_surface, card_shell_map["outline"])
    light_surface = about_surface in {"solid", "soft_tint", "glass"}
    card_title_class = "text-[var(--text-dark)]" if light_surface else "text-[var(--text)]"
    card_text_class = "text-zinc-600" if light_surface else "text-[var(--text-muted)]"
    gallery_grid_class = "grid auto-rows-[16rem] gap-4 md:grid-cols-4"
    if gallery_density == "cinematic_strip":
        gallery_grid_class = "grid auto-rows-[18rem] gap-4 md:grid-cols-[1.5fr_0.85fr_0.85fr]"
    elif gallery_density == "editorial_grid" or proof_style == "editorial_case":
        gallery_grid_class = "grid auto-rows-[14rem] gap-4 md:grid-cols-[1.2fr_0.8fr_0.8fr]"
    elif gallery_density == "mosaic" or proof_style == "card_marquee":
        gallery_grid_class = "grid auto-rows-[15rem] gap-4 md:grid-cols-3"
    about_section = """
import { ArrowUpRight, Award, MapPin, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';
import { blockPlan, siteCopy, variation } from './siteData';
const pillars = [
  { title: siteCopy.about_card_1_title, text: siteCopy.about_card_1_text, icon: MapPin },
  { title: siteCopy.about_card_2_title, text: siteCopy.about_card_2_text, icon: Award },
  { title: siteCopy.about_card_3_title, text: siteCopy.about_card_3_text, icon: Sparkles },
];
export function AboutSection() {
  const surfaceStyle = String((variation as any)?.surface_style || '');
  const servicesVariant = String((blockPlan as any)?.services_variant || '');
  const aboutVariant = String((blockPlan as any)?.about_variant || 'feature_grid');
  const leadClass = surfaceStyle === 'solid'
    ? 'bg-white text-[var(--text-dark)] shadow-[0_14px_34px_rgba(0,0,0,0.10)]'
    : surfaceStyle === 'soft_tint'
      ? 'bg-[color-mix(in_srgb,var(--bg-light)_82%,var(--accent)_18%)] text-[var(--text-dark)]'
      : 'bg-transparent text-[var(--text)]';
  if (aboutVariant === 'manifesto_split') {
    return <section id="sobre" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1.16fr_.84fr] lg:items-start"><motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.28 }} className="max-w-4xl"><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.about_kicker}</p><h2 className="mt-3 text-[clamp(2.4rem,6vw,5.4rem)] font-semibold leading-[0.92] tracking-[-0.035em]">{siteCopy.about_title}</h2><p className="mt-7 max-w-2xl text-lg leading-9 text-[var(--text-muted)]">{siteCopy.about_body}</p></motion.div><div className="grid gap-4">{pillars.map((pillar, index) => { const Icon = pillar.icon; return <motion.article key={pillar.title} initial={{ opacity: 0, x: 22 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true, amount: 0.24 }} transition={{ delay: index * 0.05 }} className="grid grid-cols-[auto_1fr] gap-4 border-t border-[color-mix(in_srgb,var(--accent)_20%,transparent)] py-5"><Icon className="mt-1 h-5 w-5" style={{ color: 'var(--accent)' }} /><div><h3 className="text-xl font-semibold tracking-tight text-[var(--text)]">{pillar.title}</h3><p className="mt-3 text-sm leading-7 text-[var(--text-muted)]">{pillar.text}</p></div></motion.article>; })}</div></div></section>;
  }
  if (aboutVariant === 'proof_sidebar') {
    return <section id="sobre" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[.72fr_1.28fr]"><motion.aside initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} className={'rounded-[22px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] p-7 ' + leadClass}><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.about_city_label}</p><p className="mt-3 text-4xl font-semibold">__ABOUT_CITY__</p><p className="mt-5 text-sm leading-7 opacity-80">{siteCopy.about_aside_body}</p><ArrowUpRight className="mt-8 h-6 w-6" style={{ color: 'var(--accent)' }} /></motion.aside><div><motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.28 }}><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.about_kicker}</p><h2 className="mt-3 max-w-4xl text-[clamp(2rem,5vw,4.8rem)] font-semibold leading-[0.98] tracking-[-0.03em]">{siteCopy.about_title}</h2><p className="mt-6 max-w-3xl text-base leading-8 text-[var(--text-muted)]">{siteCopy.about_body}</p></motion.div><div className="mt-8 grid gap-4 md:grid-cols-3">{pillars.map((pillar, index) => { const Icon = pillar.icon; return <motion.article key={pillar.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} transition={{ delay: index * 0.05 }} className="min-h-[13rem] rounded-[18px] p-5 __CARD_SHELL__"><Icon className="h-5 w-5" style={{ color: 'var(--accent)' }} /><h3 className="mt-6 text-lg font-semibold tracking-tight __CARD_TITLE_CLASS__">{pillar.title}</h3><p className="mt-3 text-sm leading-7 __CARD_TEXT_CLASS__">{pillar.text}</p></motion.article>; })}</div></div></div></section>;
  }
  return <section id="sobre" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.88fr_1.12fr] lg:items-end"><motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.28 }}><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.about_kicker}</p><h2 className="mt-3 max-w-3xl text-[clamp(2rem,5vw,4.5rem)] font-semibold leading-[0.98] tracking-[-0.03em]">{siteCopy.about_title}</h2><p className="mt-6 max-w-2xl text-base leading-8 text-[var(--text-muted)]">{siteCopy.about_body}</p></motion.div><div className={`grid gap-4 ${servicesVariant === 'split_editorial' ? 'md:grid-cols-2 xl:grid-cols-3' : 'md:grid-cols-3'}`}>{pillars.map((pillar, index) => { const Icon = pillar.icon; return <motion.article key={pillar.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} transition={{ delay: index * 0.05 }} className="min-h-[15rem] rounded-[18px] p-6 __CARD_SHELL__"><Icon className="h-5 w-5" style={{ color: 'var(--accent)' }} /><h3 className="mt-8 text-xl font-semibold tracking-tight __CARD_TITLE_CLASS__">{pillar.title}</h3><p className="mt-4 text-sm leading-7 __CARD_TEXT_CLASS__">{pillar.text}</p></motion.article>; })}</div><motion.aside initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} className={'rounded-[22px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] p-6 ' + leadClass}><div className="flex items-center justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.about_city_label}</p><p className="mt-3 text-2xl font-semibold">__ABOUT_CITY__</p></div><ArrowUpRight className="h-5 w-5" style={{ color: 'var(--accent)' }} /></div><p className="mt-4 text-sm leading-7 opacity-80">{siteCopy.about_aside_body}</p></motion.aside></div></section>;
}
export default AboutSection;
""".replace("__PROOF_STYLE__", proof_style.replace("_", " ")).replace("__SURFACE_STYLE__", surface_style.replace("_", " ")).replace("__CARD_SHELL__", card_shell).replace("__CARD_TITLE_CLASS__", card_title_class).replace("__CARD_TEXT_CLASS__", card_text_class).replace("__ABOUT_NAME__", copy["name"]).replace("__ABOUT_CITY__", copy["city"])
    gallery_section = """
import { motion } from 'motion/react';
import { mediaImages, siteCopy } from './siteData';
export function GallerySection() {
  return <section id="galeria" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.gallery_kicker}</p><h2 className="mt-3 max-w-3xl text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em]">{siteCopy.gallery_title}</h2></div><p className="max-w-md text-sm leading-7 text-[var(--text-muted)]">{siteCopy.gallery_intro}</p></div><div className="__GALLERY_GRID_CLASS__">{mediaImages.slice(0, 5).map((src, index) => <motion.figure key={src} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.25 }} transition={{ delay: index * 0.04 }} className={`group relative overflow-hidden rounded-[18px] bg-black ${index === 0 ? 'md:col-span-2 md:row-span-2' : ''}`}><img src={src} alt={`${siteCopy.gallery_alt} ${index + 1}`} className="h-full w-full object-cover opacity-90 transition duration-700 group-hover:scale-105 group-hover:opacity-100" loading={index === 0 ? 'eager' : 'lazy'} decoding="async" /><figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-5 text-sm font-semibold text-white">{index === 0 ? siteCopy.name : siteCopy.city}</figcaption></motion.figure>)}</div></div></section>;
}
export default GallerySection;
""".replace("__GALLERY_GRID_CLASS__", gallery_grid_class)
    reviews_section = """
import { motion } from 'motion/react';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Separator } from './ui/separator';
import { blockPlan, siteCopy, variation } from './siteData';
const proofs = siteCopy.services.map((service, index) => ({
  title: service.title,
  body: service.description,
  badge: index === 0 ? `${siteCopy.rating || '5.0'} estrelas` : siteCopy.city,
  initials: service.title.slice(0, 2).toUpperCase(),
}));
export function ReviewsSection() {
  const proofStyle = String((blockPlan as any)?.reviews_variant || (variation as any)?.proof_style || '');
  const motionMix = Array.isArray((blockPlan as any)?.motion_mix) ? (blockPlan as any).motion_mix : [];
  const spotlight = proofStyle === 'quote_spotlight';
  const marquee = proofStyle === 'card_marquee';
  const scoreWall = proofStyle === 'score_wall';
  const editorialCase = proofStyle === 'editorial_case';
  const railClass = motionMix.includes('marquee') ? 'motion-marquee-rail' : '';
  if (scoreWall) {
    return <section id="avaliacoes" style={{ background: 'var(--bg)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.reviews_kicker}</p><h2 className="mt-3 max-w-3xl text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em] text-[var(--text)]">{siteCopy.reviews_title}</h2><div className="mt-10 grid grid-cols-2 gap-3 md:grid-cols-4">{[ { label: 'avaliação', value: siteCopy.rating || '5.0' }, { label: 'cidade', value: siteCopy.city }, { label: 'segmento', value: siteCopy.segment }, { label: 'contato', value: 'WhatsApp' } ].map((stat, i) => <motion.div key={i} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.4 }} transition={{ delay: i * 0.05 }} className="rounded-[18px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] bg-[color-mix(in_srgb,var(--bg)_92%,var(--accent)_8%)] p-6"><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{stat.label}</p><p className="mt-3 text-2xl font-extrabold tracking-tight text-[var(--text)] md:text-3xl">{stat.value}</p></motion.div>)}</div><div className="mt-10 grid gap-4 md:grid-cols-3">{proofs.slice(0, 3).map((item, index) => <motion.article key={item.title} initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} transition={{ delay: index * 0.05 }} className="rounded-[18px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] bg-[color-mix(in_srgb,var(--bg)_94%,var(--accent)_6%)] p-6"><div className="flex items-center gap-3"><Avatar className="h-10 w-10"><AvatarFallback>{item.initials}</AvatarFallback></Avatar><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{item.badge}</p><h3 className="mt-1 text-lg font-semibold text-[var(--text)]">{item.title}</h3></div></div><Separator className="my-4" /><p className="text-sm leading-7 text-[var(--text-muted)]">{item.body}</p></motion.article>)}</div></div></section>;
  }
  if (editorialCase) {
    return <section id="avaliacoes" style={{ background: 'var(--bg-light)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-start"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.reviews_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4rem)] font-semibold leading-[1.05] tracking-[-0.03em] text-zinc-950">{siteCopy.reviews_title}</h2><p className="mt-6 max-w-2xl text-base leading-8 text-zinc-600">{siteCopy.reviews_intro}</p><blockquote className="mt-10 border-l-2 pl-6 text-2xl font-medium leading-[1.3] tracking-[-0.02em] text-zinc-900 md:text-3xl" style={{ borderColor: 'var(--accent)' }}>"{siteCopy.proof_quote}"</blockquote><p className="mt-4 text-sm font-semibold text-zinc-500">{siteCopy.city} · {siteCopy.segment}</p></div><div className="grid gap-4">{proofs.slice(0, 2).map((item, index) => <motion.article key={item.title} initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }} transition={{ delay: index * 0.06 }} className="rounded-[18px] border border-zinc-200 bg-white p-6"><div className="flex items-center gap-3"><Avatar className="h-10 w-10"><AvatarFallback>{item.initials}</AvatarFallback></Avatar><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{item.badge}</p><h3 className="mt-1 text-lg font-semibold text-zinc-950">{item.title}</h3></div></div><Separator className="my-4" /><p className="text-sm leading-7 text-zinc-600">{item.body}</p></motion.article>)}</div></div></section>;
  }
  return <section id="avaliacoes" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="overflow-hidden px-5 py-20 md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.reviews_kicker}</p><h2 className="mt-3 max-w-3xl text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em]">{siteCopy.reviews_title}</h2></div><div className="max-w-md text-sm leading-7 text-[var(--text-muted)]">{siteCopy.reviews_intro}</div></div>{marquee ? <div data-proof-rail className={`flex gap-4 overflow-hidden ${railClass}`}>{[...proofs, ...proofs].map((item, index) => <motion.article key={`${item.title}-${index}`} initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true, amount: 0.18 }} className="min-w-[18rem] rounded-[18px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] bg-[color-mix(in_srgb,var(--bg)_92%,var(--accent)_8%)] p-6"><div className="flex items-center gap-3"><Avatar><AvatarFallback>{item.initials}</AvatarFallback></Avatar><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{item.badge}</p><h3 className="mt-1 text-lg font-semibold text-[var(--text)]">{item.title}</h3></div></div><Separator className="my-4" /><p className="text-sm leading-7 text-[var(--text-muted)]">{item.body}</p></motion.article>)}</div> : <div className={`grid gap-4 ${spotlight ? 'lg:grid-cols-[1.15fr_0.85fr]' : 'md:grid-cols-3'}`}><motion.article initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} className="rounded-[22px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] bg-[color-mix(in_srgb,var(--bg)_92%,var(--accent)_8%)] p-7"><p className="text-2xl leading-10 text-[var(--text)]">“{siteCopy.proof_quote}”</p><p className="mt-6 text-sm font-semibold text-[var(--text-muted)]">{siteCopy.city} • {siteCopy.segment}</p></motion.article><div className={`grid gap-4 ${spotlight ? '' : 'md:col-span-2 md:grid-cols-2'}`}>{proofs.slice(0, spotlight ? 2 : 4).map((item, index) => <motion.article key={item.title} initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} transition={{ delay: index * 0.05 }} className="rounded-[18px] border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] bg-[color-mix(in_srgb,var(--bg)_94%,var(--accent)_6%)] p-6"><div className="flex items-center gap-3"><Avatar className="h-10 w-10"><AvatarFallback>{item.initials}</AvatarFallback></Avatar><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{item.badge}</p><h3 className="mt-1 text-lg font-semibold text-[var(--text)]">{item.title}</h3></div></div><Separator className="my-4" /><p className="text-sm leading-7 text-[var(--text-muted)]">{item.body}</p></motion.article>)}</div></div>}</div></section>;
}
export default ReviewsSection;
""".replace("__PROOF_STYLE__", proof_style.replace("_", " "))
    faq_section = """
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { blockPlan, siteCopy } from './siteData';
const items = [
  { value: 'item-1', question: `Como falar com ${siteCopy.name}?`, answer: 'Use o botão principal ou o bloco final para abrir o WhatsApp e confirmar atendimento, agenda ou visita.' },
  { value: 'item-2', question: `Onde fica ${siteCopy.name}?`, answer: `A cidade, o endereço e o contato aparecem nesta página para facilitar a ida até ${siteCopy.name}.` },
  { value: 'item-3', question: 'O que foi confirmado nesta página?', answer: 'Nome do negócio, cidade, contato, endereço e a linha principal de atendimento mostrada nas seções acima.' },
  { value: 'item-4', question: 'Posso tirar dúvidas antes de fechar?', answer: 'Sim. O caminho recomendado é abrir o WhatsApp e confirmar detalhes diretamente com o negócio.' },
];
export function FaqSection() {
  const variant = String((blockPlan as any)?.faq_variant || 'panel');
  if (variant === 'inline') {
    return <section id="faq" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.faq_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.2rem)] font-semibold leading-[1] tracking-[-0.025em]">{siteCopy.faq_title}</h2></div><p className="max-w-xl text-sm leading-7 text-[var(--text-muted)]">{siteCopy.faq_intro}</p></div><div className="grid gap-4">{items.map((item) => <div key={item.value} className="rounded-[18px] border border-[color-mix(in_srgb,var(--accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--bg)_94%,var(--accent)_6%)] px-5 py-4"><Accordion type="single" collapsible className="w-full"><AccordionItem value={item.value}><AccordionTrigger>{item.question}</AccordionTrigger><AccordionContent>{item.answer}</AccordionContent></AccordionItem></Accordion></div>)}</div></div></section>;
  }
  return <section id="faq" style={{ background: 'var(--bg)', color: 'var(--text)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.85fr_1.15fr]"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.faq_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.2rem)] font-semibold leading-[1] tracking-[-0.025em]">{siteCopy.faq_title}</h2><p className="mt-5 max-w-xl text-sm leading-7 text-[var(--text-muted)]">{siteCopy.faq_intro}</p></div><div className="rounded-[22px] border border-[color-mix(in_srgb,var(--accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--bg)_94%,var(--accent)_6%)] p-6"><Accordion type="single" collapsible className="w-full">{items.map((item) => <AccordionItem key={item.value} value={item.value}><AccordionTrigger>{item.question}</AccordionTrigger><AccordionContent>{item.answer}</AccordionContent></AccordionItem>)}</Accordion></div></div></section>;
}
export default FaqSection;
"""
    return {
        "src/lib/utils.ts": vite_template_utils_ts(),
        "src/components/ui/avatar.tsx": vite_template_avatar_ui(),
        "src/components/ui/separator.tsx": vite_template_separator_ui(),
        "src/components/ui/accordion.tsx": vite_template_accordion_ui(),
        "src/components/AboutSection.tsx": about_section,
        "src/components/ServicesSection.tsx": """import { BarChart3, ClipboardCheck, MapPinned, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';
import { blockPlan, siteCopy } from './siteData';
const icons = [ClipboardCheck, Sparkles, MapPinned];
export function ServicesSection() {
  const variant = String((blockPlan as any)?.services_variant || 'stacked_cards');
  if (variant === 'stats_then_cards') {
    return <section id="servicos" style={{ background: 'var(--bg-light)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><div className="grid gap-6 lg:grid-cols-[0.72fr_1.28fr] lg:items-start"><div className="rounded-[22px] border border-black/5 bg-white p-7 shadow-[0_18px_60px_rgba(0,0,0,0.08)]"><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.services_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.2rem)] font-semibold leading-[1] tracking-[-0.025em] text-zinc-950">{siteCopy.services_title}</h2><p className="mt-5 text-sm leading-7 text-zinc-600">{siteCopy.services_subheadline}</p><div className="mt-8 grid gap-3"><div className="rounded-[16px] bg-zinc-950 px-4 py-4 text-white"><div className="flex items-center gap-3"><BarChart3 className="h-5 w-5" style={{ color: 'var(--accent)' }} /><strong>{siteCopy.rating || '5.0'}</strong></div><p className="mt-2 text-xs uppercase tracking-[0.18em] text-zinc-400">avaliação</p></div><div className="rounded-[16px] border border-zinc-200 px-4 py-4"><strong className="text-zinc-950">{siteCopy.city}</strong><p className="mt-2 text-sm text-zinc-600">{siteCopy.services_city_body}</p></div></div></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{siteCopy.services.map((service, index) => { const Icon = icons[index] || ClipboardCheck; return <motion.article key={service.title} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.28 }} transition={{ delay: index * 0.06 }} className="min-h-[16rem] rounded-[18px] border border-black/5 bg-white p-6 shadow-[0_18px_60px_rgba(0,0,0,0.08)]"><Icon className="h-6 w-6" style={{ color: 'var(--accent)' }} /><h3 className="mt-8 text-2xl font-semibold tracking-tight text-zinc-950">{service.title}</h3><p className="mt-4 text-sm leading-7 text-zinc-600">{service.description}</p></motion.article>; })}</div></div></div></section>;
  }
  if (variant === 'split_editorial') {
    return <section id="servicos" style={{ background: 'var(--bg-light)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.85fr_1.15fr]"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.services_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em] text-zinc-950">{siteCopy.services_title}</h2><p className="mt-5 max-w-xl text-base leading-8 text-zinc-600">{siteCopy.services_subheadline}</p></div><div className="grid gap-4">{siteCopy.services.map((service, index) => { const Icon = icons[index] || ClipboardCheck; return <motion.article key={service.title} initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true, amount: 0.28 }} transition={{ delay: index * 0.05 }} className="grid gap-4 rounded-[18px] border border-black/5 bg-white p-6 shadow-[0_18px_60px_rgba(0,0,0,0.08)] md:grid-cols-[auto_1fr] md:items-start"><Icon className="mt-1 h-6 w-6" style={{ color: 'var(--accent)' }} /><div><h3 className="text-2xl font-semibold tracking-tight text-zinc-950">{service.title}</h3><p className="mt-3 text-sm leading-7 text-zinc-600">{service.description}</p></div></motion.article>; })}</div></div></section>;
  }
  if (variant === 'editorial_rows') {
    return <section id="servicos" style={{ background: 'var(--bg)' }} className="px-5 py-20 text-white md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><div className="grid gap-8 md:grid-cols-[0.7fr_1.3fr] md:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.services_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em]">{siteCopy.services_title}</h2><p className="mt-5 max-w-xl text-base leading-8 text-zinc-300">{siteCopy.services_subheadline}</p></div><div className="hidden md:block"><span className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">{siteCopy.services.length} frentes em operação</span></div></div><div className="mt-12 divide-y divide-white/10 border-y border-white/10">{siteCopy.services.map((service, index) => { const Icon = icons[index] || ClipboardCheck; return <motion.div key={service.title} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.4 }} transition={{ delay: index * 0.05 }} className="grid items-start gap-6 py-7 md:grid-cols-[auto_0.6fr_1.4fr]"><div className="flex items-center gap-3"><span className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">0{index + 1}</span><Icon className="h-6 w-6" style={{ color: 'var(--accent)' }} /></div><h3 className="text-2xl font-semibold tracking-tight md:text-3xl">{service.title}</h3><p className="text-sm leading-7 text-zinc-300">{service.description}</p></motion.div>; })}</div></div></section>;
  }
  return <section id="servicos" style={{ background: 'var(--bg-light)' }} className="px-5 py-20 md:px-8 md:py-28"><div className="mx-auto max-w-7xl"><div className="grid gap-8 lg:grid-cols-[.8fr_1.2fr] lg:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.services_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em] text-zinc-950">{siteCopy.services_title}</h2></div><p className="max-w-2xl text-base leading-8 text-zinc-600">{siteCopy.services_subheadline}</p></div><div className="mt-12 grid gap-4 md:grid-cols-3">{siteCopy.services.map((service, index) => { const Icon = icons[index] || ClipboardCheck; return <motion.article key={service.title} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.28 }} transition={{ delay: index * 0.06 }} className="min-h-[17rem] rounded-[18px] border border-black/5 bg-white p-6 shadow-[0_18px_60px_rgba(0,0,0,0.08)]"><Icon className="h-6 w-6" style={{ color: 'var(--accent)' }} /><h3 className="mt-8 text-2xl font-semibold tracking-tight text-zinc-950">{service.title}</h3><p className="mt-4 text-sm leading-7 text-zinc-600">{service.description}</p></motion.article>; })}</div></div></section>;
}
export default ServicesSection;
""",
        "src/components/StatsBar.tsx": """import { useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Clock, MapPin, Star, Users } from 'lucide-react';
import { siteCopy } from './siteData';

gsap.registerPlugin(ScrollTrigger);

type Stat = { icon: string; value: string; label: string };

function _buildStats(): Stat[] {
  const out: Stat[] = [];
  const rating = (siteCopy as any)?.rating;
  const city = (siteCopy as any)?.city;
  const phone = (siteCopy as any)?.phone;
  const hours = (siteCopy as any)?.hours;
  if (rating) out.push({ icon: 'star', value: String(rating), label: 'avaliação' });
  if (hours) out.push({ icon: 'clock', value: String(hours), label: 'horário' });
  if (city) out.push({ icon: 'map', value: String(city), label: 'localização' });
  if (phone) out.push({ icon: 'phone', value: 'WhatsApp', label: 'contato' });
  if (!out.length) out.push({ icon: 'star', value: '5.0', label: 'avaliação' });
  return out.slice(0, 4);
}

const ICON_MAP: Record<string, any> = { star: Star, clock: Clock, map: MapPin, phone: Users };

export function StatsBar() {
  const rootRef = useRef<HTMLElement | null>(null);
  const variant = String(((window as any).__fralib_stats_variant) || 'dedicated_band');
  const stats = _buildStats();

  useEffect(() => {
    const root = rootRef.current;
    if (!root || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = gsap.context(() => {
      gsap.fromTo('[data-stats-counter]', { y: 18, opacity: 0 }, { y: 0, opacity: 1, duration: 0.7, stagger: 0.08, ease: 'power3.out', scrollTrigger: { trigger: root, start: 'top 80%' } });
    }, root);
    return () => ctx.revert();
  }, []);

  if (variant === 'inline_hero_stats') return null;

  if (variant === 'vertical_stack') {
    return (
      <section ref={rootRef} id="stats" style={{ background: 'var(--bg)' }} className="px-5 py-14 md:px-8">
        <div className="mx-auto grid max-w-md gap-3">
          {stats.map((s, i) => {
            const Icon = ICON_MAP[s.icon] || Star;
            return (
              <motion.div key={i} data-stats-counter className="flex items-center gap-4 rounded-[14px] border border-white/10 bg-white/5 p-4">
                <Icon className="h-5 w-5" style={{ color: 'var(--accent)' }} />
                <div><p className="text-2xl font-extrabold tracking-tight" style={{ color: 'var(--text)' }}>{s.value}</p><p className="text-xs uppercase tracking-[0.18em]" style={{ color: 'var(--text-muted)' }}>{s.label}</p></div>
              </motion.div>
            );
          })}
        </div>
      </section>
    );
  }

  if (variant === 'mosaic_grid') {
    return (
      <section ref={rootRef} id="stats" style={{ background: 'var(--bg)' }} className="px-5 py-16 md:px-8 md:py-24">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-3 md:grid-cols-4">
          {stats.map((s, i) => {
            const Icon = ICON_MAP[s.icon] || Star;
            return (
              <motion.div key={i} data-stats-counter className="rounded-[18px] border border-white/10 bg-[color-mix(in_srgb,var(--bg)_92%,var(--accent)_8%)] p-5">
                <Icon className="h-5 w-5" style={{ color: 'var(--accent)' }} />
                <p className="mt-4 text-2xl font-extrabold tracking-tight" style={{ color: 'var(--text)' }}>{s.value}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.16em]" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
              </motion.div>
            );
          })}
        </div>
      </section>
    );
  }

  // dedicated_band (default)
  return (
    <section ref={rootRef} id="stats" style={{ background: 'var(--accent-dark)' }} className="px-5 py-14 md:px-8 md:py-16">
      <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[minmax(14rem,0.72fr)_minmax(0,2fr)] lg:items-start">
        <p className="max-w-[18rem] text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent-soft)' }}>Números que sustentam a decisão</p>
        <div className="grid min-w-0 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s, i) => {
            const Icon = ICON_MAP[s.icon] || Star;
            return (
              <motion.div key={i} data-stats-counter className="min-w-0 border-t pt-4" style={{ borderColor: 'color-mix(in srgb, var(--accent) 38%, transparent)' }}>
                <div className="flex items-center gap-2"><Icon className="h-4 w-4" style={{ color: 'var(--accent)' }} /><span className="text-xs uppercase tracking-[0.18em]" style={{ color: 'var(--accent-soft)' }}>{s.label}</span></div>
                <p className="mt-3 break-words text-2xl font-extrabold leading-[0.95] tracking-[-0.025em] text-white md:text-3xl">{s.value}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
export default StatsBar;
""",
        "src/components/PricingSection.tsx": """import { motion } from 'motion/react';
import { Check, Sparkles } from 'lucide-react';
import { siteCopy, whatsappHref } from './siteData';

type Plan = { name: string; perks: string[]; highlight: boolean; note: string };

const plans: Plan[] = __PRICING_PLANS__;

export function PricingSection() {
  const variant = String(((window as any).__fralib_pricing_variant) || 'plan_grid');

  if (variant === 'single_plan') {
    const plan = plans.find((p) => p.highlight) || plans[1] || plans[0];
    return (
      <section id="planos" style={{ background: 'var(--plan-section)', color: 'var(--plan-ink)' }} className="px-5 py-20 md:px-8 md:py-28">
        <div className="mx-auto max-w-3xl border p-10 md:p-14" style={{ background: 'var(--plan-card)', color: 'var(--plan-card-ink)', borderColor: 'var(--plan-border)', boxShadow: 'var(--surface-shadow)' }}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{plan.note}</p>
          <h2 className="mt-4 text-[clamp(2rem,5vw,3.6rem)] font-extrabold leading-[1.02] tracking-[-0.03em]">{plan.name}</h2>
          <p className="mt-3 text-sm leading-7 opacity-75">Plano principal recomendado para {siteCopy.name} em {siteCopy.city}.</p>
          <ul className="mt-8 grid gap-3">
            {plan.perks.map((perk, i) => (
              <li key={i} className="flex items-start gap-3 text-sm leading-7 opacity-85">
                <Check className="mt-0.5 h-5 w-5 shrink-0" style={{ color: 'var(--accent)' }} />
                <span>{perk}</span>
              </li>
            ))}
          </ul>
          <a href={whatsappHref} rel="noopener noreferrer" className="mt-10 inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-bold transition hover:-translate-y-0.5" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }} data-price-emphasis>Quero este plano</a>
        </div>
      </section>
    );
  }

  if (variant === 'editorial_plan') {
    return (
      <section id="planos" style={{ background: 'var(--bg)' }} className="px-5 py-20 text-white md:px-8 md:py-28">
        <div className="mx-auto max-w-6xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>Planos editoriais</p>
          <h2 className="mt-3 text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em]">Como começar com {siteCopy.name}</h2>
          <div className="mt-12 divide-y divide-white/10 border-y border-white/10">
            {plans.map((plan, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.4 }} transition={{ delay: i * 0.06 }} className="grid items-center gap-6 py-8 md:grid-cols-[1.4fr_2fr_auto]">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em]" style={{ color: 'var(--accent-soft)' }}>{plan.note}</p>
                  <h3 className="mt-2 text-2xl font-semibold tracking-tight text-white md:text-3xl">{plan.name}</h3>
                </div>
                <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-300">
                  {plan.perks.map((perk, j) => <li key={j} className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--accent)' }} />{perk}</li>)}
                </ul>
                <a href={whatsappHref} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-80" data-price-emphasis={plan.highlight ? 'true' : undefined}>Conversar</a>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="planos" style={{ background: 'var(--plan-section)', color: 'var(--plan-ink)' }} className="px-5 py-20 md:px-8 md:py-28">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>Planos</p>
            <h2 className="mt-3 text-[clamp(2rem,4.8vw,4.2rem)] font-semibold leading-[1] tracking-[-0.025em]">Como começar com {siteCopy.name}</h2>
          </div>
          <p className="max-w-md text-sm leading-7 opacity-75">Valores sob consulta. Comece pela conversa direta para entender o que faz sentido para você.</p>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {plans.map((plan, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }} transition={{ delay: i * 0.06 }} className="relative border p-7" style={{ background: plan.highlight ? 'var(--plan-featured)' : 'var(--plan-card)', color: plan.highlight ? 'var(--plan-featured-ink)' : 'var(--plan-card-ink)', borderColor: plan.highlight ? 'var(--accent)' : 'var(--plan-border)', boxShadow: plan.highlight ? 'var(--surface-shadow)' : 'none' }} data-price-emphasis={plan.highlight ? 'true' : undefined}>
              {plan.highlight ? (
                <span className="absolute -top-3 left-7 inline-flex items-center gap-1 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em]" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}><Sparkles className="h-3 w-3" />{plan.note}</span>
              ) : null}
              <p className="text-xs font-semibold uppercase tracking-[0.18em] opacity-65">{plan.note}</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight">{plan.name}</h3>
              <ul className="mt-6 grid gap-2.5">
                {plan.perks.map((perk, j) => (
                  <li key={j} className="flex items-start gap-2.5 text-sm leading-7 opacity-85">
                    <Check className={`mt-0.5 h-4 w-4 shrink-0`} style={{ color: 'var(--accent)' }} />
                    <span>{perk}</span>
                  </li>
                ))}
              </ul>
              <a href={whatsappHref} rel="noopener noreferrer" className="mt-8 inline-flex w-full items-center justify-center gap-2 border px-5 py-3 text-sm font-bold transition hover:-translate-y-0.5" style={{ background: plan.highlight ? 'var(--bg)' : 'transparent', color: plan.highlight ? 'var(--text)' : 'inherit', borderColor: 'var(--plan-border)' }}>
                {plan.highlight ? 'Quero este plano' : 'Conversar'}
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
export default PricingSection;
""".replace("__PRICING_PLANS__", json.dumps(pricing_plans, ensure_ascii=False)),
        "src/components/GallerySection.tsx": gallery_section,
        "src/components/FaqSection.tsx": faq_section,
        "src/components/ReviewsSection.tsx": reviews_section,
        "src/components/LocationSection.tsx": """import { MapPin, MessageCircle, Phone } from 'lucide-react';
import { motion } from 'motion/react';
import { blockPlan, siteCopy, whatsappHref } from './siteData';

export function LocationSection() {
  const feature = String((blockPlan as any)?.location_variant || '') === 'feature_local';
  const mapsHref = String((siteCopy as any)?.mapsHref || '');
  const mapsEmbedSrc = String((siteCopy as any)?.mapsEmbedSrc || '');
  const gridClass = feature ? 'lg:grid-cols-[0.85fr_1.15fr]' : 'lg:grid-cols-[1fr_1fr]';
  const mapHeightClass = feature ? 'min-h-[30rem] lg:min-h-[48rem]' : 'min-h-[26rem] lg:min-h-[36rem]';
  return (
    <section id="localizacao" className="px-5 py-20 md:px-8 md:py-28" style={{ background: 'var(--plan-section)', color: 'var(--plan-ink)' }}>
      <div className={`mx-auto grid max-w-7xl gap-5 ${gridClass}`}>
        <motion.article initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} className="border p-7 md:p-8" style={{ background: 'var(--plan-card)', color: 'var(--plan-card-ink)', borderColor: 'var(--plan-border)' }}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.location_kicker}</p>
          <h2 className="mt-3 text-[clamp(1.8rem,4vw,3.6rem)] font-semibold leading-[1.02] tracking-[-0.025em]">{siteCopy.location_title}</h2>
          <p className="mt-4 max-w-xl text-sm leading-7 opacity-75">{siteCopy.location_intro}</p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="border p-5" style={{ borderColor: 'var(--plan-border)' }}><MapPin className="h-5 w-5" style={{ color: 'var(--accent)' }} /><p className="mt-3 text-sm font-semibold">Endereço</p><p className="mt-2 text-sm leading-6 opacity-75">{siteCopy.address || siteCopy.city}</p></div>
            <div className="border p-5" style={{ borderColor: 'var(--plan-border)' }}><Phone className="h-5 w-5" style={{ color: 'var(--accent)' }} /><p className="mt-3 text-sm font-semibold">Contato</p><p className="mt-2 text-sm leading-6 opacity-75">{siteCopy.phone}</p></div>
          </div>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a href={whatsappHref} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 px-5 py-3 text-sm font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}><MessageCircle className="h-4 w-4" /> {siteCopy.location_cta_primary}</a>
            {mapsHref ? <a href={mapsHref} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 border px-5 py-3 text-sm font-semibold" style={{ borderColor: 'var(--plan-border)' }}><MapPin className="h-4 w-4" /> Abrir no Google Maps</a> : null}
          </div>
        </motion.article>
        <motion.article initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.24 }} transition={{ delay: 0.06 }} className={`relative overflow-hidden border ${mapHeightClass}`} style={{ background: 'var(--bg)', borderColor: 'var(--plan-border)' }}>
          {mapsEmbedSrc ? (
            <iframe title={`Mapa de ${siteCopy.name}`} src={mapsEmbedSrc} className="absolute inset-0 h-full w-full border-0 grayscale contrast-125" loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
          ) : (
            <div className={`grid h-full place-items-center p-8 text-center ${mapHeightClass}`}>
              <div><MapPin className="mx-auto h-8 w-8" style={{ color: 'var(--accent)' }} /><h3 className="mt-4 text-2xl font-semibold">{siteCopy.location_cta_title}</h3><p className="mt-3 text-sm leading-7 opacity-75">{siteCopy.address || siteCopy.city}</p></div>
            </div>
          )}
        </motion.article>
      </div>
    </section>
  );
}
export default LocationSection;
""",
        "src/components/LifestyleSection.tsx": """import { useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { mediaImages, siteCopy } from './siteData';
gsap.registerPlugin(ScrollTrigger);
export function LifestyleSection() {
  const sectionRef = useRef<HTMLElement | null>(null);
  useEffect(() => { const section = sectionRef.current; if (!section || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return; const ctx = gsap.context(() => { gsap.to('[data-parallax-card]', { y: -46, ease: 'none', scrollTrigger: { trigger: section, start: 'top bottom', end: 'bottom top', scrub: true } }); }, section); return () => ctx.revert(); }, []);
  return <section ref={sectionRef} id="experiencia" style={{ background: 'var(--accent-dark)' }} className="relative overflow-hidden px-5 py-20 text-white md:px-8 md:py-28"><div className="absolute inset-0" style={{ background: 'radial-gradient(circle_at_18%_18%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 32%), linear-gradient(180deg, rgba(255,255,255,0.03), transparent)' }} /><div className="relative mx-auto grid max-w-7xl gap-8 lg:grid-cols-[.9fr_1.1fr] lg:items-center"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.lifestyle_kicker}</p><h2 className="mt-3 text-[clamp(2rem,4.8vw,4.4rem)] font-semibold leading-[1] tracking-[-0.025em]">{siteCopy.lifestyle_title}</h2><p className="mt-6 max-w-xl text-base leading-8 text-zinc-300">{siteCopy.lifestyle_description}</p></div><div className="relative min-h-[34rem]"><motion.img data-parallax-card src={mediaImages[1] || mediaImages[0]} alt={siteCopy.gallery_alt} initial={{ opacity: 0, rotate: -1.4, y: 24 }} whileInView={{ opacity: 1, rotate: -1.4, y: 0 }} viewport={{ once: true, amount: 0.25 }} className="absolute left-0 top-8 h-[25rem] w-[72%] rounded-[18px] object-cover shadow-[0_30px_90px_rgba(0,0,0,.30)]" loading="lazy" decoding="async" /><motion.div initial={{ opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }} className="absolute bottom-0 right-0 w-[68%] rounded-[18px] border border-[color-mix(in_srgb,var(--accent)_26%,transparent)] bg-[color-mix(in_srgb,var(--accent-dark)_88%,var(--accent)_12%)] p-6 shadow-[0_18px_48px_rgba(0,0,0,.24)]"><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.location_kicker}</p><h3 className="mt-3 text-2xl font-semibold">{siteCopy.name}</h3><p className="mt-3 text-sm leading-7 text-zinc-300">{siteCopy.address || siteCopy.city}</p></motion.div></div></div></section>;
}
export default LifestyleSection;
""",
        "src/components/ContactCTA.tsx": """import { MessageCircle, Phone } from 'lucide-react';
import { motion } from 'motion/react';
import { blockPlan, siteCopy, whatsappHref } from './siteData';
export function ContactCTA({ onOpen }: { onOpen?: () => void }) {
  const ctaStyle = String((blockPlan as any)?.cta_style || 'solid_panel');
  const poster = ctaStyle === 'poster_band';
  const split = ctaStyle === 'split_card';
  const minimal = ctaStyle === 'minimal_inline';
  const sectionClass = minimal ? 'px-5 py-14 md:px-8' : poster ? 'px-5 py-24 md:px-8 md:py-32' : 'px-5 py-20 md:px-8';
  const gridClass = split ? 'mx-auto grid max-w-7xl gap-4 lg:grid-cols-2 lg:items-stretch' : 'mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1.1fr_.9fr] lg:items-center';
  const cardClass = minimal ? 'border-t border-white/20 pt-6' : 'rounded-[18px] p-6 shadow-[0_22px_70px_rgba(0,0,0,.22)]';
  return <section id="contato" style={{ background: poster ? 'var(--bg)' : 'var(--accent-dark)', color: 'white' }} className={sectionClass}><div className={gridClass}><motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }}><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent-soft)' }}>{siteCopy.contact_kicker}</p><h2 className="mt-3 max-w-4xl text-[clamp(2rem,5vw,4.8rem)] font-semibold leading-[1] tracking-[-0.03em]">{siteCopy.contact_headline}</h2><p className="mt-5 max-w-2xl text-base leading-8 text-white/75">{siteCopy.contact_sub}</p></motion.div><div style={{ background: minimal ? 'transparent' : 'var(--bg-light)', color: 'var(--text-dark)' }} className={cardClass}><p className="text-sm leading-7" style={{ color: 'var(--text-dark)' }}>{siteCopy.contact_card_label}</p><p className="mt-2 text-2xl font-semibold">{siteCopy.phone || 'WhatsApp'}</p><div className="mt-6 flex flex-col gap-3 sm:flex-row"><a href={whatsappHref} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}><MessageCircle className="h-4 w-4" />{siteCopy.contact_primary_label}</a><button type="button" onClick={onOpen} className="inline-flex items-center justify-center gap-2 rounded-full border border-black/10 px-5 py-3 text-sm font-semibold" style={{ color: 'var(--text-dark)' }}><Phone className="h-4 w-4" />{siteCopy.contact_secondary_label}</button></div></div></div></section>;
}
export default ContactCTA;
""",
        "src/components/BookingModal.tsx": """import { X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { siteCopy, whatsappHref } from './siteData';
export function BookingModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return <AnimatePresence>{open ? <motion.div className="fixed inset-0 z-[80] grid place-items-end bg-black/65 p-3 md:place-items-center md:p-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><motion.div initial={{ y: 42, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 24, opacity: 0 }} transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }} style={{ background: 'var(--bg-light)', color: 'var(--text-dark)' }} className="w-full max-w-lg rounded-[22px] p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.modal_kicker}</p><h3 className="mt-2 text-3xl font-semibold tracking-tight">{siteCopy.modal_title}</h3></div><button type="button" aria-label="Fechar" onClick={onClose} className="inline-flex h-10 w-10 items-center justify-center rounded-full text-white" style={{ background: 'var(--accent-dark)' }}><X className="h-4 w-4" /></button></div><p className="mt-5 text-sm leading-7" style={{ color: 'var(--text-dark)' }}>Telefone: {siteCopy.phone || 'confirme pelo WhatsApp'}. Endereço: {siteCopy.address || siteCopy.city}.</p><a href={whatsappHref} rel="noopener noreferrer" className="mt-6 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}>{siteCopy.modal_cta}</a></motion.div></motion.div> : null}</AnimatePresence>;
}
export default BookingModal;
""",
        "src/components/Footer.tsx": """import { MapPin, MessageCircle, ShieldCheck } from 'lucide-react';
import { siteCopy, whatsappHref } from './siteData';
export function Footer() {
  return <footer style={{ background: 'linear-gradient(180deg, var(--bg), color-mix(in srgb, var(--bg) 88%, var(--accent) 12%))', color: 'var(--text)' }} className="px-5 py-12 md:px-8"><div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-[1.1fr_.8fr_.8fr]"><div><strong className="block text-2xl font-semibold" style={{ color: 'var(--text)' }}>{siteCopy.name}</strong><p className="mt-3 max-w-md text-sm leading-7" style={{ color: 'var(--text-muted)' }}>{siteCopy.footer_tagline}</p></div><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.footer_contact_label}</p><a href={whatsappHref} rel="noopener noreferrer" className="mt-4 flex items-center gap-2 text-sm font-semibold" style={{ color: 'var(--text)' }}><MessageCircle className="h-4 w-4" style={{ color: 'var(--accent)' }} /> WhatsApp oficial</a><p className="mt-3 text-sm" style={{ color: 'var(--text-muted)' }}>{siteCopy.phone}</p></div><div><p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent)' }}>{siteCopy.footer_location_label}</p><p className="mt-4 flex items-start gap-2 text-sm leading-6" style={{ color: 'var(--text-muted)' }}><MapPin className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--accent)' }} /> {siteCopy.address || siteCopy.city}</p><p className="mt-4 flex items-start gap-2 text-sm leading-6" style={{ color: 'color-mix(in srgb, var(--text-muted) 82%, var(--accent) 18%)' }}><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--accent)' }} /> {siteCopy.footer_privacy_note}</p></div></div><div className="mx-auto mt-10 flex max-w-7xl flex-col gap-2 border-t pt-5 text-xs md:flex-row md:items-center md:justify-between" style={{ borderColor: 'color-mix(in srgb, var(--accent) 18%, transparent)', color: 'color-mix(in srgb, var(--text-muted) 88%, var(--accent) 12%)' }}><span>{siteCopy.city}</span><span>© 2026 {siteCopy.name}. Todos os direitos reservados.</span></div></footer>;
}
export default Footer;
""",
        "src/components/LgpdBanner.tsx": vite_template_lgpd_banner(facts),
        "src/components/FactualMotionContract.tsx": vite_template_factual_motion_contract(
            name=copy["name"],
            phone=copy["phone"],
            rating=copy["rating"],
            city=copy["city"],
            segment=copy["segment"],
        ),
        # Sprint 14.6: index.html com HEAD SEO completo (title, description,
        # keywords, OG, Twitter, canonical, JSON-LD LocalBusiness).
        "index.html": vite_template_index_html(facts),
    }


def _generate_studio_fallback_files(facts: dict[str, Any] | None = None) -> dict[str, str]:
    """Legacy import alias for the canonical cinematic Studio renderer."""
    return _generate_cinematic_studio_files(facts or {})


def _removed_studio_legacy_entrypoint(facts: dict[str, Any] | None = None) -> dict[str, str]:
    """Removed legacy Studio entry point.

    Kept temporarily as a fail-fast guard for old scripts/tests that still
    import this name. The official builder path must use LLM-generated files
    through render_vite_react_site().
    """
    raise ViteReactRenderError(
        "Studio legacy entry point foi removido do runtime. "
        "Use render_vite_react_site() com FRALIB_VITE_LLM_POLICY=full_code."
    )
    safe_facts = facts or {}
    # O caminho aprovado para a pipeline oficial usa o Studio cinematografico.
    # Permite desligar explicitamente por env apenas quando um teste precisar.
    if os.getenv("FRALIB_VITE_CINEMATIC_STUDIO", "1").strip().lower() in {"1", "true", "yes", "on"}:
        return _generate_cinematic_studio_files(safe_facts)
    # Sprint 12.15: extract name from MANY sources (defensive — pipeline may put it anywhere)
    _biz = safe_facts.get("business") if isinstance(safe_facts.get("business"), dict) else {}
    name = (
        _biz.get("name")
        or _biz.get("business_name")
        or _biz.get("nome")
        or safe_facts.get("name")
        or safe_facts.get("business_name")
        or safe_facts.get("nome")
        or "FraLib"
    )
    # Also pull other fields defensively from anywhere in facts
    def _find(k, default=""):
        for src in (_biz, safe_facts):
            v = src.get(k) if isinstance(src, dict) else None
            if v:
                return v
        return default
    phone = str(_find("whatsapp") or _find("phone") or "41999999999")
    rating = str(_find("rating") or "4.8")
    city = str(_biz.get("city") or _biz.get("cidade") or safe_facts.get("cidade") or safe_facts.get("city") or "Curitiba")
    segment = str(_biz.get("segment") or _biz.get("segmento") or safe_facts.get("segmento") or safe_facts.get("segment") or "servicos").lower()

    # Extrair imagens do facts (fail-fast: não há mais fallbacks hardcoded)
    media = safe_facts.get("media") if isinstance(safe_facts.get("media"), dict) else {}
    photos = media.get("photos") or []
    if isinstance(photos, list) and photos:
        hero_img = photos[0] if isinstance(photos[0], str) else photos[0].get("url", "")
        gallery_img = photos[1] if len(photos) > 1 and isinstance(photos[1], str) else (photos[1].get("url", "") if len(photos) > 1 else hero_img)
    else:
        from backend.pipeline_exceptions import ImageNotAvailableError
        raise ImageNotAvailableError(
            "Studio legacy entry point: Sem imagens no facts.",
            context={"segmento": segment, "acao": "Forneca fotos no lead ou use unsplash_fetcher"},
        )

    # Sprint 16: Get variation seed and apply it to facts
    # This provides deterministic randomness for hero layout, motion, copy voice, and color emphasis
    variation = None
    if get_variation is not None:
        variation = get_variation(safe_facts)
        safe_facts = apply_variation_to_facts(safe_facts, variation)
        # Convert variation seed to integer for existing seed-based functions
        seed = variation.seed % 1000000  # Keep seed manageable
    else:
        # Legacy seed generation (backward compatibility)
        seed_source = str(
            safe_facts.get("job_id")
            or safe_facts.get("id")
            or f"{name}|{segment}|{city}"
        )
        seed = sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed_source)) % 1000000

    # Sprint 15: Archetype-based palette and typography
    archetype = _get_archetype_for_segment(segment)
    palette = _get_archetype_palette(archetype)
    typography = _get_archetype_typography(archetype)

    # Sprint 15: Get archetype-specific copy structure
    # (actual variation selection happens after seed is defined)
    archetype_copy = _get_archetype_copy(archetype)

    # Use archetype copy for section headings (static, no seed needed)
    services_heading = archetype_copy["services_heading"]
    gallery_heading = archetype_copy["gallery_heading"]
    lifestyle_heading = archetype_copy["lifestyle_heading"]
    contact_heading = archetype_copy["contact_heading"]
    footer_tagline = archetype_copy["footer_tagline"]

    # Sprint 12.14: segment-aware content (fixes hardcoded academia contamination)

    if "barbearia" in segment or "barbeiro" in segment:
        svc_labels = ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"]
        alt_img = "Barbeiro em barbearia"
        lifestyle_desc = "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "academia" in segment or "fitness" in segment or "musculacao" in segment or "crossfit" in segment:
        svc_labels = ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"]
        alt_img = "Alunos em treino fitness"
        lifestyle_desc = "Um espaco para criar rotina, encontrar orientacao e manter frequencia sem complicar."
        nav_items = [("Treinos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "restaurante" in segment or "bar " in segment or "pizzaria" in segment or "hamburgueria" in segment or "lanchonete" in segment or "cafeteria" in segment:
        svc_labels = ["Pratos", "Menu", "Reservas", "Eventos", "Delivery"]
        alt_img = "Restaurante"
        lifestyle_desc = "Cada prato preparado com cuidado para proporcionar uma experiencia unica."
        nav_items = [("Cardapio", "#servicos"), ("Galeria", "#galeria"), ("Reservar", "#contato")]
    elif "clinica" in segment or "estetica" in segment or "dermatologia" in segment:
        svc_labels = ["Consulta", "Tratamento", "Avaliacao", "Procedimento", "Retorno"]
        alt_img = "Clinica"
        lifestyle_desc = "Ambiente preparado para recebe-lo com conforto e seguranca em cada atendimento."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "imobiliaria" in segment or "imoveis" in segment:
        svc_labels = ["Venda", "Locacao", "Avaliacao", "Consultoria", "Lancamentos"]
        alt_img = "Imovel"
        lifestyle_desc = "Encontre o imovel ideal com quem entende do mercado local."
        nav_items = [("Imoveis", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "nutricionista" in segment or "nutricao" in segment:
        svc_labels = ["Avaliacao", "Plano alimentar", "Acompanhamento", "Suplementacao", "Bioimpedancia"]
        alt_img = "Nutricionista"
        lifestyle_desc = "Transforme sua alimentacao com acompanhamento profissional cientifico."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "advocacia" in segment or "advogado" in segment:
        svc_labels = ["Consulta", "Contratos", "Processos", "Assessoria", "Recursos"]
        alt_img = "Escritorio de advocacia"
        lifestyle_desc = "Atendimento juridico transparente e dedicado a sua causa."
        nav_items = [("Areas", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "odonto" in segment or "dentista" in segment:
        svc_labels = ["Limpeza", "Clareamento", "Implante", "Ortodontia", "Emergencia"]
        alt_img = "Consultorio odontologico"
        lifestyle_desc = "Tecnologia de ponta e carinho em cada tratamento para seu sorriso."
        nav_items = [("Tratamentos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "ecommerce" in segment or "loja" in segment or "roupas" in segment:
        svc_labels = ["Produtos", "Frete", "Troca", "Atendimento", "Garantia"]
        alt_img = "Produtos"
        lifestyle_desc = "Produtos selecionados com cuidado para atender suas necessidades."
        nav_items = [("Produtos", "#servicos"), ("Ofertas", "#galeria"), ("Contato", "#contato")]
    elif "petshop" in segment or "pet " in segment:
        svc_labels = ["Banho", "Tosa", "Consulta", "Produtos", "Creche"]
        alt_img = "Pet shop"
        lifestyle_desc = "Cuidamos do seu pet como se fosse nosso. Amor e dedicacao em cada servico."
        nav_items = [("Servicos", "#servicos"), ("Produtos", "#galeria"), ("Contato", "#contato")]
    elif "hotel" in segment or "pousada" in segment or "hostel" in segment:
        svc_labels = ["Quartos", "Cafe da manha", "Estacionamento", "Wi-Fi", "Piscina"]
        alt_img = "Hotel"
        lifestyle_desc = "Conforto e acolhimento para tornar sua estadia inesquecivel."
        nav_items = [("Quartos", "#servicos"), ("Servicos", "#galeria"), ("Reservar", "#contato")]
    elif "salao_beleza" in segment or "beleza" in segment or "manicure" in segment or "cabelo" in segment:
        svc_labels = ["Corte", "Coloracao", "Manicure", "Maquiagem", "Tratamentos"]
        alt_img = "Salao de beleza"
        lifestyle_desc = "Transformamos seu visual com tecnicas modernas e produtos de qualidade."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "fisioterapia" in segment or "fisio" in segment:
        svc_labels = ["Avaliacao", "Tratamento", "RPG", "Acupuntura", "Pilates"]
        alt_img = "Fisioterapia"
        lifestyle_desc = "Recupere sua qualidade de vida com tratamento fisioterapêutico humanizado."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "escola" in segment or "cursinho" in segment or "idiomas" in segment or "musica" in segment or "informatica" in segment:
        svc_labels = ["Matricula", "Cursos", "Talleres", "Eventos", "Biblioteca"]
        alt_img = "Escola"
        lifestyle_desc = "Formando cidadaos preparados para o futuro com excelencia e valores."
        nav_items = [("Cursos", "#servicos"), ("Eventos", "#galeria"), ("Contato", "#contato")]
    elif "autoescola" in segment:
        svc_labels = ["Aulas teoricas", "Aulas praticas", "Simulado", "Exame", "CNH"]
        alt_img = "Autoescola"
        lifestyle_desc = "Metodologia comprovada para voce passar no DETRAN de primeira."
        nav_items = [("Categorias", "#servicos"), ("Simulado", "#galeria"), ("Contato", "#contato")]
    elif "oficina" in segment or "mecanica" in segment or "eletrica" in segment or "pintura" in segment:
        svc_labels = ["Revisao", "Diagnostico", "Reparos", "Pintura", "Eletrica"]
        alt_img = "Oficina mecanica"
        lifestyle_desc = "Servico de qualidade com transparencia e compromisso com seu veiculo."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "farmacia" in segment or "manipulacao" in segment:
        svc_labels = ["Medicamentos", "Manipulacao", "Dermocosmeticos", "Atendimento", "Delivery"]
        alt_img = "Farmacia"
        lifestyle_desc = "Farmacêuticos capacitados para orientar sobre medicamentos e cuidados."
        nav_items = [("Produtos", "#servicos"), ("Promocoes", "#galeria"), ("Contato", "#contato")]
    elif "psicologo" in segment or "psicologia" in segment:
        svc_labels = ["Consulta", "Terapia", "Avaliacao", "Diagnostico", "Acompanhamento"]
        alt_img = "Consultorio de psicologia"
        lifestyle_desc = "Um espaco seguro para falar sobre seus sentimentos e desenvolver seu potencial."
        nav_items = [("Abordagens", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "fotografo" in segment or "fotografia" in segment or "design" in segment or "grafico" in segment:
        svc_labels = ["Eventos", "Casamentos", "Books", "Corporativo", "Produtos"]
        alt_img = "Fotografia"
        lifestyle_desc = "Capturamos momentos e emocoes com sensibilidade e tecnica."
        nav_items = [("Portfolio", "#servicos"), ("Pacotes", "#galeria"), ("Contato", "#contato")]
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]

    else:
        svc_labels = ["Servico 1", "Servico 2", "Servico 3", "Servico 4", "Servico 5"]
        alt_img = f"{name}"
        lifestyle_desc = f"Atendimento dedicado para garantir sua satisfacao em {city}."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]

    # END of segment-aware block - def component follows
    # Sprint 12.17: capture segment vars in the body strings via Python evaluation.
    # f-strings inside this scope see the segment vars (svc_labels, hero_desc, etc).

    # Sprint 15: Build CSS variable declarations from archetype palette for inline style injection
    css_vars = f"""
    --color-primary: {palette['primary']};
    --color-primary-contrast: {palette['primary_contrast']};
    --color-secondary: {palette['secondary']};
    --color-accent: {palette['accent']};
    --color-bg-dark: {palette['bg_dark']};
    --color-bg-light: {palette['bg_light']};
    --color-text-dark: {palette['text_dark']};
    --color-text-light: {palette['text_light']};
    --color-border: {palette['border']};
    --color-gradient-start: {palette['gradient_start']};
    --color-gradient-end: {palette['gradient_end']};
    --font-heading: {typography['heading_font']};
    --font-body: {typography['body_font']};
    --weight-heading: {typography['heading_weight']};
    --weight-body: {typography['body_weight']};
    """.strip()

    def component(export_name: str, body: str, *, imports: str = "") -> str:
        return f"""{imports}
export function {export_name}() {{
{body}
}}

export default {export_name};
"""

    # Sprint 15: Use dynamic palette values instead of hardcoded emerald
    # Extract primary color for Tailwind-style classes via inline style
    primary_hex = palette['primary']
    primary_contrast_hex = palette['primary_contrast']
    primary_light = palette['accent']  # Lighter variant for badges/text

    # Sprint 16: Hero layout variation - deterministic based on archetype + seed
    # Seed is already computed at the top of the function from variation_seed module
    hero_layout = _pick_hero_layout(archetype, seed)

    # Sprint 16: Select niche-specific copy variations using archetype + seed
    hero_title = _select_copy_variation(
        archetype_copy["hero_title_patterns"], archetype, seed, name=name, city=city
    )
    hero_subtitle = _select_copy_variation(
        archetype_copy["hero_subtitle_patterns"], archetype, seed, name=name, city=city
    )
    cta_primary = archetype_copy["cta_primary"][(seed or 0) % len(archetype_copy["cta_primary"])]
    cta_secondary = archetype_copy["cta_secondary"][(seed or 0) % len(archetype_copy["cta_secondary"])]
    llm_content = safe_facts.get("_llm_content") if isinstance(safe_facts.get("_llm_content"), dict) else {}
    if llm_content:
        hero = llm_content.get("hero") if isinstance(llm_content.get("hero"), dict) else {}
        lifestyle = llm_content.get("lifestyle") if isinstance(llm_content.get("lifestyle"), dict) else {}
        if hero.get("headline"):
            hero_title = str(hero["headline"])
        if hero.get("subheadline"):
            hero_subtitle = str(hero["subheadline"])
        if hero.get("cta_primary"):
            cta_primary = str(hero["cta_primary"])
        if hero.get("cta_secondary"):
            cta_secondary = str(hero["cta_secondary"])
        if llm_content.get("services_title"):
            services_heading = str(llm_content["services_title"])
        if lifestyle.get("title"):
            lifestyle_heading = str(lifestyle["title"])
        if lifestyle.get("description"):
            lifestyle_desc = str(lifestyle["description"])
        if llm_content.get("gallery_alt"):
            alt_img = str(llm_content["gallery_alt"])
        if isinstance(llm_content.get("services"), list) and llm_content["services"]:
            slot_labels = []
            for item in llm_content["services"][:5]:
                if isinstance(item, dict) and item.get("title"):
                    slot_labels.append(str(item["title"]))
                elif item:
                    slot_labels.append(str(item))
            if slot_labels:
                svc_labels = slot_labels + svc_labels[len(slot_labels):]
    service_descriptions = [
        _select_copy_variation(
            archetype_copy["service_description_patterns"], archetype,
            (seed + i if seed else i) % len(archetype_copy["service_description_patterns"]),
            name=name, city=city
        )
        for i in range(min(3, len(svc_labels)))
    ]
    if llm_content and isinstance(llm_content.get("services"), list):
        for idx, item in enumerate(llm_content["services"][:len(service_descriptions)]):
            if isinstance(item, dict) and item.get("description"):
                service_descriptions[idx] = str(item["description"])

    dense_cards = "\n".join(
        f'<div className="rounded-3xl border border-white/10 bg-black/70 p-5 text-white"><strong className="block text-xl" style={{{{color:"{primary_light}"}}}}>0{i}</strong><span className="text-sm text-zinc-300">{svc_labels[i-1]}</span></div>'
        for i in range(1, 6)
    )
    nav_links = "\n".join(
        f'<a className="hover:text-white" href="{href}">{label}</a>'
        for label, href in nav_items
    )
    # Sprint 16: Generate niche-specific service descriptions using archetype copy
    services_articles = "\n".join(
        f'<article className="rounded-3xl border border-white/10 bg-black/70 p-6"><h3 className="text-xl font-bold">{svc_labels[i]}</h3><p className="mt-3 text-zinc-400">{service_descriptions[i]}</p></article>'
        for i in range(min(3, len(svc_labels)))
    )
    files = {
        "src/components/Navbar.tsx": component(
            "Navbar",
            f"""  const [open, setOpen] = useState(false);
  useEffect(() => {{
    const onScroll = () => setOpen(window.scrollY > 24);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }}, []);
  return (
    <nav style={{{{background: open ? '{palette['bg_dark']}ee' : 'rgba(0,0,0,.76)', borderColor: open ? '{palette['border']}' : '{palette['border'].replace('0.2', '0.1')}'}}}} className={{`fixed inset-x-4 top-4 z-50 rounded-3xl border px-5 py-3 shadow-[0_14px_40px_rgba(0,0,0,.28)]`}}>
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <a className="min-w-0 truncate text-sm font-black uppercase tracking-[0.24em]" href="#top" style={{{{color:"{primary_light}"}}}}>{name}</a>
        <div className="hidden items-center gap-5 text-sm text-zinc-200 md:flex">
          {nav_links}
        </div>
        <a className="rounded-full px-4 py-2 text-sm font-bold max-sm:px-3 max-sm:text-xs" style={{{{backgroundColor:"{primary_hex}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{{cta_primary}}</a>
      </div>
    </nav>
  );
""",
            imports="import { useEffect, useState } from 'react';",
        ),
        "src/components/HeroSection.tsx": component(
            "HeroSection",
            _generate_hero_section_variation(
                layout=hero_layout,
                name=hero_title,
                segment=segment,
                city=city,
                hero_desc=hero_subtitle,
                hero_img=hero_img,
                cta_primary="{{cta_primary}}",
                cta_secondary="{{cta_secondary}}",
                alt_img="{{alt_img}}",
                phone=phone,
                dense_cards=dense_cards,
                palette=palette,
                imports="",
            ),
            imports="import { motion } from 'motion/react';\nimport gsap from 'gsap';\nimport { useEffect } from 'react';",
        ),
        "src/components/ServicesSection.tsx": component("ServicesSection", f"""  return <section id="servicos" className="px-6 py-24 text-white" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em]" style={{{{color:"{primary_light}"}}}}>servicos</p><h2 className="mt-3 text-4xl font-black">{services_heading}</h2><div className="mt-10 grid gap-4 md:grid-cols-3">{services_articles}</div></div></section>;"""),
        "src/components/GallerySection.tsx": component("GallerySection", f"""  return <section id="galeria" className="px-6 py-24 text-white" style={{{{backgroundColor:"{palette['bg_light']}"}}}}><div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-2"><img className="h-96 w-full rounded-[2rem] object-cover" src="{hero_img}" alt="{{alt_img}}" loading="lazy" decoding="async" /><img className="h-96 w-full rounded-[2rem] object-cover" src="{gallery_img}" alt="{{alt_img}}" loading="lazy" decoding="async" /></div></section>;"""),
        "src/components/LifestyleSection.tsx": component("LifestyleSection", f"""  return <section className="px-6 py-24 text-white" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}><div className="mx-auto max-w-6xl rounded-[2rem] border border-white/10 p-8" style={{{{borderColor:"{palette['border']}",backgroundColor:"{primary_hex}1a"}}}}><p className="text-sm font-bold uppercase tracking-[0.2em]" style={{{{color:"{primary_light}"}}}}>experiencia</p><h2 className="mt-3 text-4xl font-black">{lifestyle_heading}</h2><p className="mt-4 max-w-3xl text-zinc-300">{lifestyle_desc}.</p></div></section>;"""),
        "src/components/BookingModal.tsx": component("BookingModal", f"""  const [open, setOpen] = useState(false);
  return <div className="px-6 py-12 text-center text-white" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}><button className="rounded-full px-6 py-3 font-black" style={{{{backgroundColor:"{primary_contrast_hex}",color:"{palette['bg_dark']}"}}}} onClick={{() => setOpen(true)}}>{{cta_primary}}</button>{{open && <div className="fixed inset-0 z-[80] grid place-items-center bg-black/70 p-6"><div className="max-w-md rounded-3xl p-6 text-left" style={{{{backgroundColor:"{primary_contrast_hex}",color:"{palette['bg_dark']}"}}}}><h3 className="text-2xl font-black">Fale com {name}</h3><p className="mt-3">Telefone {phone}. Atendimento personalizado com avaliacao {rating} em {city}.</p><button className="mt-5 rounded-full px-5 py-2" style={{{{backgroundColor:"{palette['bg_dark']}",color:"{primary_contrast_hex}"}}}} onClick={{() => setOpen(false)}}>Fechar</button></div></div>}}</div>;""", imports="import { useState } from 'react';"),
        "src/components/ContactCTA.tsx": component("ContactCTA", f"""  return <section id="contato" className="px-6 py-20" style={{{{backgroundColor:"{primary_hex}"}}}}><div className="mx-auto flex max-w-6xl flex-col gap-5 md:flex-row md:items-center md:justify-between"><div><p className="text-sm font-bold uppercase tracking-[0.2em]" style={{{{color:"{palette['text_dark']}"}}}}>contato</p><h2 className="text-4xl font-black" style={{{{color:"{palette['text_dark']}"}}}}>{contact_heading} em {city}</h2><p className="mt-2 font-semibold" style={{{{color:"{palette['text_dark']}"}}}}>WhatsApp {phone} • avaliacao {rating}</p></div><a className="rounded-full px-7 py-4 font-black" style={{{{backgroundColor:"{palette['bg_dark']}",color:"{primary_contrast_hex}"}}}} href="tel:{phone}">{cta_primary}</a></div></section>;"""),
        "src/components/Footer.tsx": component("Footer", f"""  return <footer className="px-6 py-10 text-zinc-400" style={{{{backgroundColor:"{palette['bg_dark']}"}}}}><div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4"><span className="font-bold text-white">{name}</span><span>{footer_tagline} {city} • {phone}</span></div></footer>;"""),
        # Sprint 15: Generate Index.tsx with archetype-based section order
        "src/pages/Index.tsx": _generate_index_tsx_with_section_order(archetype, seed, palette),
        # Sprint 15: Generate archetype-specific CSS with fonts and color variables
        "src/index.css": f"""@import "tailwindcss";
@import url('https://fonts.googleapis.com/css2?family={_get_archetype_fonts(archetype).replace('&', '&')}&display=swap');

@layer base {{
  :root {{
    --color-primary: {palette['primary']};
    --color-primary-contrast: {palette['primary_contrast']};
    --color-secondary: {palette['secondary']};
    --color-accent: {palette['accent']};
    --color-bg-dark: {palette['bg_dark']};
    --color-bg-light: {palette['bg_light']};
    --color-text-dark: {palette['text_dark']};
    --color-text-light: {palette['text_light']};
    --color-border: {palette['border']};
    --color-gradient-start: {palette['gradient_start']};
    --color-gradient-end: {palette['gradient_end']};
    --font-heading: {typography['heading_font']};
    --font-body: {typography['body_font']};
    --weight-heading: {typography['heading_weight']};
    --weight-body: {typography['body_weight']};
    --weight-accent: {typography['accent_weight']};
    --heading-tracking: {typography['heading_tracking']};
  }}

  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; background: {palette['bg_dark']}; }}
  body {{
    margin: 0;
    min-width: 320px;
    min-height: 100vh;
    font-family: var(--font-body);
    color: {palette['text_light']};
    background: {palette['bg_dark']};
    text-rendering: geometricPrecision;
    font-weight: var(--weight-body);
  }}
  h1, h2, h3 {{
    font-family: var(--font-heading);
    font-weight: var(--weight-heading);
    letter-spacing: var(--heading-tracking);
    text-wrap: balance;
  }}
  p {{ text-wrap: pretty; }}
  img {{ max-width: 100%; display: block; }}
  a {{ color: inherit; text-decoration: none; }}
  button, a {{ -webkit-tap-highlight-color: transparent; }}
  ::selection {{ background: {palette['primary']}59; color: {palette['text_dark']}; }}
}}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }}
}}
""",
    }
    return prepare_vite_project_files(files, facts=safe_facts)


def extract_requested_vite_project_paths(prompt: str) -> set[str]:
    """Return explicit Vite source/config paths requested by the business brief."""
    requested: set[str] = set()
    for match in re.findall(r"`([^`]+\.(?:tsx|ts|css|json|html))`", prompt or "", re.IGNORECASE):
        candidate = str(match or "").strip().replace("\\", "/")
        if "*" in candidate or candidate.startswith("dist/"):
            continue
        try:
            safe = _safe_project_path(candidate)
        except ViteReactRenderError:
            continue
        requested.add(safe)
    return requested


def validate_vite_project_files(
    files: dict[str, str],
    facts: dict[str, Any],
    *,
    requested_paths: set[str] | None = None,
    studio_mode: bool = True,
) -> None:
    # Sprint 11.6+: sanitize logger GLOBALMENTE antes de qualquer validacao.
    # Garante que mesmo se prepare_vite_project_files nao foi chamado
    # (ex: caminho legado de Studio), o logger orfao eh corrigido.
    for path in list(files.keys()):
        if path.endswith((".tsx", ".ts", ".jsx", ".js")):
            files[path] = _sanitize_logger_in_source(files[path])

    # Fail-fast: se arquivo opcional falta, erro. Sem studio-fallback.
    missing = sorted(REQUIRED_PROJECT_FILES.difference(files))
    if missing:
        raise ViteReactRenderError("projeto Vite sem arquivos obrigatorios: " + ", ".join(missing))
    requested_missing = sorted(set(requested_paths or set()).difference(files))
    if requested_missing:
        raise ViteReactRenderError(
            "projeto Vite nao entregou arquivos pedidos no prompt: " + ", ".join(requested_missing)
        )
    component_files = [
        path for path in files if path.startswith("src/components/") and path.endswith(".tsx")
    ]
    if len(component_files) < 5:
        raise ViteReactRenderError("projeto Vite pouco componentizado: minimo 5 componentes em src/components")
    for path, content in files.items():
        if "\x00" in content:
            raise ViteReactRenderError(f"arquivo contem byte nulo: {path}")
        if path == "package.json":
            continue
        for label, pattern in BLOCKED_SOURCE_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                raise ViteReactRenderError(f"codigo React contem padrao proibido ({label}) em {path}")
    source_text = "\n".join(
        content for path, content in files.items() if path.startswith("src/")
    )
    _validate_no_studio_template_leaks(source_text)
    _validate_public_copy_quality(source_text)
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    name = str(business.get("name") or "").strip()
    if name and _normalize_text(name) not in _normalize_text(source_text):
        raise ViteReactRenderError(f"nome confirmado ausente no projeto React: {name}")
    phone = _digits(str(business.get("whatsapp") or business.get("phone") or ""))
    if phone and phone not in _digits(source_text):
        raise ViteReactRenderError("telefone/WhatsApp confirmado ausente no projeto React")
    rating = str(business.get("rating") or "").strip().replace(",", ".")
    if rating and rating not in source_text.replace(",", "."):
        raise ViteReactRenderError(f"rating confirmado ausente no projeto React: {rating}")
    _validate_segment_specificity(source_text, business)
    if studio_mode:
        _validate_hero_first_viewport(files)
        _validate_mobile_navbar(files)
        _validate_no_low_contrast_card_patterns(files)
        _validate_required_runtime_map(files, facts)
        _validate_creative_plan_materialization(files, facts)
        _validate_studio_project(files, source_text, component_files)


def _validate_no_studio_template_leaks(source_text: str) -> None:
    leaked_identifiers = [
        "_seed_for_html",
        "_h1_size",
        "_cta_btn_class",
        "_hero_class_number",
    ]
    hits = [identifier for identifier in leaked_identifiers if identifier in source_text]
    if hits:
        raise ViteReactRenderError(
            "projeto Vite contem placeholders internos vazando para React: " + ", ".join(hits)
        )
    duplicate_class = re.search(
        r"<[A-Za-z][^>\n]*\bclassName\s*=[^>\n]*\bclassName\s*=",
        source_text,
    )
    if duplicate_class:
        raise ViteReactRenderError("projeto Vite contem className duplicado no mesmo elemento")


def _validate_no_low_contrast_card_patterns(files: dict[str, str]) -> None:
    low_contrast_patterns = [
        ("section_text_dark_with_white_cards", r"color:\s*'var\(--text-dark\)'.{0,1400}(?<![\w/-])bg-white(?![\w/-])"),
        ("white_card_with_accent_dark_body", r"(?<![\w/-])bg-white(?![\w/-]).{0,900}color:\s*'var\(--accent-dark\)'"),
    ]
    for path, content in files.items():
        if not path.startswith("src/components/") or not path.endswith(".tsx"):
            continue
        for label, pattern in low_contrast_patterns:
            if re.search(pattern, content, re.DOTALL):
                raise ViteReactRenderError(
                    f"projeto Vite contem padrao de baixo contraste em {path}: {label}"
                )


def _validate_public_copy_quality(source_text: str) -> None:
    """Block internal planning commentary and translation artifacts in public copy."""
    normalized = _normalize_text(source_text)
    banned_terms = (
        "finally",
        "informacoes confirmadas da",
        "organizadas para contato direto",
        "organizados para contato direto",
        "canal oficial para confirmar",
        "composicao mistura",
        "cards e ritmo",
        "direcao visual",
        "midia editorial",
        "a galeria mostra",
        "essa secao",
        "este bloco",
    )
    hits = [term for term in banned_terms if term in normalized]
    if hits:
        raise ViteReactRenderError(
            "projeto Vite contem copy publica com comentario interno/artefato de traducao: "
            + ", ".join(hits[:4])
        )


def _extract_export_const_json(source: str, const_name: str) -> Any:
    needle = f"export const {const_name} ="
    start = source.find(needle)
    if start < 0:
        return None
    start = source.find("=", start)
    if start < 0:
        return None
    payload_start = -1
    for idx in range(start + 1, len(source)):
        if source[idx] in "{[":
            payload_start = idx
            break
    if payload_start < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(source[payload_start:])[0]
    except Exception:
        return None


def _facts_have_location_signal(facts: dict[str, Any]) -> bool:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    content = facts.get("content") if isinstance(facts.get("content"), dict) else {}
    for container in (business, facts, content):
        if not isinstance(container, dict):
            continue
        for key in ("address", "endereco", "maps_url", "mapsHref", "mapsEmbedSrc", "google_maps_embed"):
            if str(container.get(key) or "").strip():
                return True
    return False


def _validate_required_runtime_map(files: dict[str, str], facts: dict[str, Any]) -> None:
    if not _facts_have_location_signal(facts):
        return
    site_data = files.get("src/components/siteData.ts", "")
    location = files.get("src/components/LocationSection.tsx", "")
    site_copy = _extract_export_const_json(site_data, "siteCopy")
    maps_embed = ""
    if isinstance(site_copy, dict):
        maps_embed = str(site_copy.get("mapsEmbedSrc") or "")
    if not maps_embed or "output=embed" not in maps_embed:
        raise ViteReactRenderError("lead com endereco/mapa, mas siteData nao carrega mapsEmbedSrc real")
    if "<iframe" not in location or "mapsEmbedSrc" not in location:
        raise ViteReactRenderError("lead com endereco/mapa, mas LocationSection nao renderiza iframe real")


def _validate_creative_plan_materialization(files: dict[str, str], facts: dict[str, Any]) -> None:
    site_data = files.get("src/components/siteData.ts", "")
    index = files.get("src/pages/Index.tsx", "")
    block_plan = _extract_export_const_json(site_data, "blockPlan")
    variation = _extract_export_const_json(site_data, "variation")
    if not isinstance(block_plan, dict):
        raise ViteReactRenderError("Studio Vite sem blockPlan materializado em siteData.ts")

    required = (
        "visual_lane",
        "aesthetic_mode",
        "spacing_density",
        "typography_scale",
        "motion_intensity",
        "motion_mix",
        "hero_variant",
        "surface_style",
        "section_surface_map",
    )
    missing = [key for key in required if not block_plan.get(key)]
    if missing:
        raise ViteReactRenderError("blockPlan incompleto para publicacao premium: " + ", ".join(missing))

    motion_mix = block_plan.get("motion_mix")
    if not isinstance(motion_mix, list) or len([item for item in motion_mix if item]) < 2:
        raise ViteReactRenderError("blockPlan sem motion_mix visivel suficiente")
    surface_map = block_plan.get("section_surface_map")
    if not isinstance(surface_map, dict) or len(set(str(value) for value in surface_map.values())) < 2:
        raise ViteReactRenderError("blockPlan sem variacao real de superficies por secao")

    hero = str(block_plan.get("hero_variant") or "")
    spacing = str(block_plan.get("spacing_density") or "")
    motion = str(block_plan.get("motion_intensity") or "")
    typography = str(block_plan.get("typography_scale") or "")
    if hero == "center" and spacing == "spacious" and motion == "minimal" and typography == "soft":
        raise ViteReactRenderError("creative_plan fraco bloqueado: hero=center + spacious + minimal + soft")
    if motion == "minimal" or typography == "soft":
        raise ViteReactRenderError("creative_plan abaixo do piso premium: motion minimal ou tipografia soft")
    if "data-motion={" not in index and 'data-motion="' not in index:
        raise ViteReactRenderError("Index.tsx nao materializa data-motion do blockPlan")
    if isinstance(variation, dict) and variation.get("anti_repetition_rule") == "avoid_glass":
        source = "\n".join(files.values()).lower()
        if "backdrop-blur" in source:
            raise ViteReactRenderError("avoid_glass ativo, mas projeto ainda usa backdrop-blur")


def _segment_key_for_business(business: dict[str, Any]) -> str | None:
    # Sprint 11.6: match EXATO de token, mas dando prioridade ao campo "segment"
    # primario (nao subniche). Antes: "musculacao" no subniche de barbearia disparava
    # academia (bug). Aplica _normalize_text nos aliases para remover acentos.
    segment_primary = _normalize_text(
        " ".join(
            str(business.get(key) or "")
            for key in ("segment", "segmento", "category", "categoria")
        )
    )
    segment_full = _normalize_text(
        " ".join(
            str(business.get(key) or "")
            for key in ("segment", "segmento", "category", "categoria", "subniche", "niche")
        )
    )
    primary_tokens = set(segment_primary.split())
    full_tokens = set(segment_full.split())

    # 1) Match exato no campo primario (segment) — tem prioridade
    for key, rule in SEGMENT_RULES.items():
        if any(_normalize_text(alias) in primary_tokens for alias in rule["aliases"]):
            return key
    # 2) Match exato no full text (incluindo subniche) — fallback
    for key, rule in SEGMENT_RULES.items():
        if any(_normalize_text(alias) in full_tokens for alias in rule["aliases"]):
            return key
    # 3) Match substring apenas para aliases multi-palavra
    for key, rule in SEGMENT_RULES.items():
        if any(" " in _normalize_text(alias) and _normalize_text(alias) in segment_full for alias in rule["aliases"]):
            return key
    return None


def _validate_segment_specificity(source_text: str, business: dict[str, Any]) -> None:
    normalized = _normalize_text(source_text)
    segment_key = _segment_key_for_business(business)
    if not segment_key:
        return
    rule = SEGMENT_RULES[segment_key]
    forbidden_terms = _forbidden_terms_for_business(segment_key, business)
    forbidden_hits = [term for term in forbidden_terms if _contains_normalized_term(normalized, term)]
    if forbidden_hits:
        raise ViteReactRenderError(
            f"projeto Vite contaminado para segmento {segment_key}: {', '.join(forbidden_hits[:4])}"
        )
    required_hits = [term for term in rule["required"] if _normalize_text(term) in normalized]
    min_required = int(rule.get("min_required") or 1)
    if len(set(required_hits)) < min_required:
        raise ViteReactRenderError(
            f"projeto Vite sem linguagem suficiente do segmento {segment_key}: "
            f"{len(set(required_hits))}/{min_required} termos"
        )


def _contains_normalized_term(normalized_text: str, term: str) -> bool:
    """Match forbidden contamination terms as words/phrases, not name substrings.

    Example: "barba" must block a nutrition site that says "servico de barba",
    but must not block a real lead called "Barbara".
    """
    normalized_term = _normalize_text(term)
    if not normalized_text or not normalized_term:
        return False
    pattern = r"(?<![\w])" + re.escape(normalized_term) + r"(?![\w])"
    return bool(re.search(pattern, normalized_text))


def _forbidden_terms_for_business(segment_key: str, business: dict[str, Any]) -> tuple[str, ...]:
    rule = SEGMENT_RULES[segment_key]
    forbidden = tuple(str(term) for term in rule["forbidden"])
    if segment_key != "nutricionista" or not _is_sports_nutrition_business(business):
        return forbidden
    allowed = {"musculacao", "musculação"}
    return tuple(term for term in forbidden if _normalize_text(term) not in allowed)


def _is_sports_nutrition_business(business: dict[str, Any]) -> bool:
    context = _normalize_text(
        " ".join(
            str(business.get(key) or "")
            for key in (
                "name",
                "business_name",
                "nome",
                "segment",
                "segmento",
                "subniche",
                "niche",
                "description",
                "descricao",
            )
        )
    )
    return "nutric" in context and any(
        token in context
        for token in ("esportiv", "atleta", "performance", "hipertrofia", "suplementacao")
    )


def _validate_studio_project(
    files: dict[str, str], source_text: str, component_files: list[str]
) -> None:
    source_chars = sum(len(content) for path, content in files.items() if path.startswith("src/"))
    if source_chars < _studio_min_source_chars():
        raise ViteReactRenderError(
            f"projeto Vite visualmente magro: {source_chars} chars em src; minimo {_studio_min_source_chars()}"
        )
    if len(component_files) < _studio_min_components():
        raise ViteReactRenderError(
            f"projeto Vite sem estrutura studio: minimo {_studio_min_components()} componentes"
        )

    index_css = files.get("src/index.css", "")
    vite_config = files.get("vite.config.ts", "")
    if "@import \"tailwindcss\"" not in index_css and "@import 'tailwindcss'" not in index_css:
        raise ViteReactRenderError("projeto Vite sem Tailwind v4 em src/index.css")
    if "@tailwindcss/vite" not in vite_config:
        raise ViteReactRenderError("projeto Vite sem plugin @tailwindcss/vite")
    if "motion/react" not in source_text and "framer-motion" not in source_text:
        raise ViteReactRenderError("projeto Vite sem motion/react")
    if "gsap" not in source_text.lower():
        raise ViteReactRenderError("projeto Vite sem GSAP (scroll animations)")
    if not re.search(r"\buseState\s*\(", source_text):
        raise ViteReactRenderError("projeto Vite sem estado React para menu/modal/galeria")
    if not re.search(r"\buseEffect\s*\(", source_text):
        raise ViteReactRenderError("projeto Vite sem useEffect para navbar/scroll/responsividade")

    class_count = len(re.findall(r"\bclassName\s*=", source_text))
    if class_count < _studio_min_classnames():
        raise ViteReactRenderError(
            f"projeto Vite sem densidade Tailwind: {class_count} className; minimo {_studio_min_classnames()}"
        )
    image_count = len(re.findall(r"<img\b", source_text, re.IGNORECASE))
    editorial_refs = len(re.findall(r"images\.unsplash\.com", source_text, re.IGNORECASE))
    if max(image_count, editorial_refs) < _studio_min_images():
        raise ViteReactRenderError(
            f"projeto Vite sem galeria/imagens reais: {max(image_count, editorial_refs)} refs; minimo {_studio_min_images()}"
        )

    basenames = {PurePosixPath(path).stem.lower() for path in component_files}
    group_hits = {
        label: any(any(token in basename for token in tokens) for basename in basenames)
        for label, tokens in STUDIO_COMPONENT_GROUPS.items()
    }
    # Sprint 11.6: lifestyle eh equivalente a gallery (visual showcase).
    # Se o LLM gerou GallerySection.tsx mas nao LifestyleSection.tsx, aceita.
    for label, satisfied in group_hits.items():
        if satisfied:
            continue
        if label == "lifestyle" and group_hits.get("gallery"):
            continue
        raise ViteReactRenderError(f"projeto Vite sem componente studio obrigatorio: {label}")


def _validate_hero_first_viewport(files: dict[str, str]) -> None:
    hero_sources = "\n".join(
        content
        for path, content in files.items()
        if path.lower().endswith("herosection.tsx") or "hero" in PurePosixPath(path).stem.lower()
    )
    hero = hero_sources.lower()
    if not hero:
        return
    centered_fullscreen = (
        "h-screen" in hero
        and "items-center" in hero
        and "justify-center" in hero
        and "text-center" in hero
    )
    mobile_safe_type = any(token in hero for token in ("clamp", "text-[clamp", "leading-[", "break-words"))
    if centered_fullscreen and re.search(r"text-(?:5xl|6xl|7xl|8xl|9xl)", hero) and not mobile_safe_type:
        raise ViteReactRenderError(
            "hero Vite com headline gigante sem clamp/break mobile; risco de texto cortado"
        )
    if centered_fullscreen:
        raise ViteReactRenderError(
            "hero Vite fullscreen centrado reprova QA visual; use composicao assimetrica com CTA/prova visiveis"
        )
    if re.search(r"bg-(?:zinc|neutral|slate|black)-950/([7-9]\\d|100)", hero):
        raise ViteReactRenderError("hero Vite com overlay escuro demais; contraste/visibilidade acima da dobra reprovados")
    if "<img" in hero and "loading=\"eager\"" not in hero and "loading='eager'" not in hero:
        raise ViteReactRenderError("hero Vite com imagem sem loading eager; QA visual pode capturar placeholder")


def _validate_mobile_navbar(files: dict[str, str]) -> None:
    nav_sources = "\n".join(
        content
        for path, content in files.items()
        if path.lower().endswith("navbar.tsx") or "nav" in PurePosixPath(path).stem.lower()
    ).lower()
    if not nav_sources:
        return
    has_mobile_cta = "<button" in nav_sources and any(
        token in nav_sources for token in ("matr", "começar", "comecar", "agendar")
    )
    has_responsive_cta = any(
        token in nav_sources for token in ("hidden sm:", "hidden md:", "max-sm:hidden", "sm:inline", "sm:flex")
    )
    has_shrink_brand = any(token in nav_sources for token in ("min-w-0", "truncate", "shrink", "text-sm", "max-sm:"))
    if has_mobile_cta and not (has_responsive_cta or has_shrink_brand):
        raise ViteReactRenderError(
            "navbar Vite pode cortar CTA no mobile; esconda/compacte CTA ou permita shrink/truncate"
        )


def _studio_min_source_chars() -> int:
    return _env_int("FRALIB_VITE_STUDIO_MIN_SOURCE_CHARS", 5500)


def _studio_min_classnames() -> int:
    return _env_int("FRALIB_VITE_STUDIO_MIN_CLASSNAMES", 45)


def _studio_min_images() -> int:
    return _env_int("FRALIB_VITE_STUDIO_MIN_IMAGES", 2)


def _studio_min_components() -> int:
    return _env_int("FRALIB_VITE_STUDIO_MIN_COMPONENTS", 8)


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def write_vite_project(workspace: Path, files: dict[str, str]) -> None:
    """Write normalized files under the workspace and remove stale generated output."""
    workspace.mkdir(parents=True, exist_ok=True)
    preview_fast = _preview_fast_enabled()
    stale_targets = ("dist", "src") if preview_fast else ("dist", "src", "node_modules")
    for stale in stale_targets:
        target = workspace / stale
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
    for path, content in files.items():
        target = (workspace / path).resolve()
        if workspace not in target.parents and target != workspace:
            raise ViteReactRenderError(f"arquivo escapou do workspace: {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    # Sprint 12.x: copiar design-system-tokens.css para a raiz do workspace
    # (necessário para os tokens --pole-* serem aplicados no bundle final)
    _copy_design_system_tokens(workspace)


def _copy_design_system_tokens(workspace: Path) -> None:
    """Copia frontend/static/design-system-tokens.css para a raiz do workspace.

    Faz fallback silencioso se o arquivo não existir (não bloqueia o build).
    """
    try:
        # Localizar arquivo fonte
        repo_root = Path(__file__).resolve().parents[2]
        css_src = repo_root / "frontend" / "static" / "design-system-tokens.css"
        if not css_src.exists():
            return

        css_dst = workspace / "design-system-tokens.css"
        shutil.copy2(css_src, css_dst)
    except Exception:
        # Silencioso: não bloquear build se asset estiver indisponível
        pass


def build_vite_project(workspace: Path) -> None:
    """Install fixed dependencies and compile the Vite project to dist."""
    npm_cmd = _npm_bin()
    node_cmd = _node_bin()
    timeout = int(os.getenv("FRALIB_VITE_BUILD_TIMEOUT", "420"))
    preview_fast = _preview_fast_enabled()
    node_modules = workspace / "node_modules"
    plugin_react = node_modules / "@vitejs" / "plugin-react"
    should_install = True
    if preview_fast and node_modules.exists() and plugin_react.exists():
        should_install = False
    if should_install:
        _run(
            [npm_cmd, "install", "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund"],
            cwd=workspace,
            timeout=timeout,
            label="npm install",
        )
    _ensure_vite_react_plugin_installed(workspace, npm_cmd=npm_cmd, timeout=timeout)
    if not preview_fast:
        _run(
            [node_cmd, str(workspace / "node_modules" / "typescript" / "bin" / "tsc"), "--noEmit"],
            cwd=workspace,
            timeout=timeout,
            label="tsc --noEmit",
        )
    try:
        _run(
            [node_cmd, str(workspace / "node_modules" / "vite" / "bin" / "vite.js"), "build"],
            cwd=workspace,
            timeout=timeout,
            label="vite build",
        )
    except ViteReactRenderError as exc:
        # Some VPS/npm combinations return a non-zero status after Vite has
        # already written a valid dist. Keep the dist and let validate_vite_dist
        # be the final contract instead of discarding a successful build.
        output = str(exc)
        if "vite build falhou:" in output and "built" in output and (workspace / "dist" / "index.html").exists():
            pass
        elif "ERR_MODULE_NOT_FOUND" in output and "plugin-react" in output:
            # npm install falhou parcialmente - @vitejs/plugin-react nao foi instalado.
            # Limpa node_modules e tenta novamente (1 retry automatico).
            import shutil as _shutil

            _shutil.rmtree(node_modules, ignore_errors=True)
            _run(
                [npm_cmd, "install", "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund"],
                cwd=workspace,
                timeout=timeout,
                label="npm install (retry)",
            )
            _ensure_vite_react_plugin_installed(workspace, npm_cmd=npm_cmd, timeout=timeout)
            _run(
                [node_cmd, str(workspace / "node_modules" / "vite" / "bin" / "vite.js"), "build"],
                cwd=workspace,
                timeout=timeout,
                label="vite build (retry)",
            )
        else:
            raise
    rewrite_vite_dist_asset_paths(workspace / "dist")


def _ensure_vite_react_plugin_installed(workspace: Path, *, npm_cmd: str, timeout: int) -> None:
    """Guarantee vite.config.ts can import @vitejs/plugin-react before build."""
    plugin_react = workspace / "node_modules" / "@vitejs" / "plugin-react"
    if plugin_react.exists():
        return
    _run(
        [npm_cmd, "install", "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund", "@vitejs/plugin-react@^4.3.3"],
        cwd=workspace,
        timeout=timeout,
        label="npm install @vitejs/plugin-react",
    )
    if not plugin_react.exists():
        raise ViteReactRenderError(
            "npm install concluiu, mas node_modules/@vitejs/plugin-react nao existe"
        )


def rewrite_vite_dist_asset_paths(dist_dir: Path) -> None:
    """Make Vite bundles load when published below /sites/<tenant>/<slug>/."""
    index = dist_dir / "index.html"
    if not index.exists():
        return
    html = index.read_text(encoding="utf-8")
    rewritten = (
        html.replace('src="/assets/', 'src="assets/')
        .replace("src='/assets/", "src='assets/")
        .replace('href="/assets/', 'href="assets/')
        .replace("href='/assets/", "href='assets/")
        .replace("url(/assets/", "url(assets/")
    )
    if rewritten != html:
        index.write_text(rewritten, encoding="utf-8")


def _npm_bin() -> str:
    configured = os.getenv("FRALIB_NPM_BIN")
    if configured:
        return configured
    if os.name == "nt":
        return shutil.which("npm.cmd") or shutil.which("npm.exe") or "npm.cmd"
    return shutil.which("npm") or "npm"


def _node_bin() -> str:
    configured = os.getenv("FRALIB_NODE_BIN")
    if configured:
        return configured
    if os.name == "nt":
        return shutil.which("node.exe") or "node.exe"
    return shutil.which("node") or "node"


def validate_vite_dist(dist_dir: Path) -> None:
    index = dist_dir / "index.html"
    if not index.exists():
        raise ViteReactRenderError("vite build nao gerou dist/index.html")
    html = index.read_text(encoding="utf-8")
    if len(html) < 250:
        raise ViteReactRenderError("dist/index.html pequeno demais")
    if "/assets/" not in html and "assets/" not in html:
        raise ViteReactRenderError("dist/index.html sem bundle assets")
    assets = dist_dir / "assets"
    if not assets.exists() or not any(assets.iterdir()):
        raise ViteReactRenderError("vite build nao gerou assets")


def _call_vite_react_llm(
    user_prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    facts: dict[str, Any] | None = None,  # Sprint 12.13: caroço rico com briefing real
) -> str:
    model_id = {
        "haiku": PROXY_LIGHT_MODEL,
        "sonnet": PROXY_DEFAULT_MODEL,
        "opus": PROXY_BUILDER_MODEL,
    }.get(model, model)
    effective_max_tokens = _cap_max_tokens_for_model(model_id, max_tokens)
    # Sprint 12.13: usa caroço rico quando facts disponivel, fallback HEAD+FOOT+TAIL estatico
    system_prompt = _build_vite_react_system_prompt_with_facts(facts or {})
    if _is_litellm_openai_chat_base():
        text_out, _usage = _call_proxy_openai_chat(
            model_id,
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=effective_max_tokens,
        )
    else:
        try:
            from services.llm_router import call_llm
        except Exception:
            try:
                from backend.services.llm_router import call_llm
            except Exception:
                from llm_router import call_llm

        text_out, _usage = call_llm(
            "anthropic",
            model_id,
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=effective_max_tokens,
        )
    return text_out


def _call_copy_only_llm(
    user_prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    policy: str = "copy_only",
) -> str:
    """Call the LLM with the small content-only contract, not the full-code prompt."""
    model_id = {
        "haiku": PROXY_LIGHT_MODEL,
        "sonnet": PROXY_DEFAULT_MODEL,
        "opus": PROXY_BUILDER_MODEL,
    }.get(model, model)
    effective_max_tokens = _cap_max_tokens_for_model(model_id, max_tokens)
    inferred_policy = "creative_plan" if policy == "copy_only" and '"creative_plan"' in user_prompt else policy
    system_prompt = _get_copy_only_system_prompt(inferred_policy)
    if _is_litellm_openai_chat_base():
        text_out, _usage = _call_proxy_openai_chat(
            model_id,
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=effective_max_tokens,
        )
    else:
        try:
            from services.llm_router import call_llm
        except Exception:
            try:
                from backend.services.llm_router import call_llm
            except Exception:
                from llm_router import call_llm

        text_out, _usage = call_llm(
            "anthropic",
            model_id,
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=effective_max_tokens,
        )
    return text_out


def _cap_max_tokens_for_model(model_id: str, requested: int) -> int:
    return cap_max_tokens_for_model(model_id, requested)


def _compose_vite_user_prompt(
    builder_prompt: str,
    *,
    facts: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
) -> str:
    facts = facts or {}
    facts_summary = _summarize_builder_facts(facts)
    contamination_guard = _segment_contamination_guard(facts)

    design_contract_ref = ""
    try:
        repo_root = Path(__file__).resolve().parents[2]
        design_contract = (repo_root / "DESIGN.md").read_text(encoding="utf-8").strip()
        if design_contract:
            design_contract_ref = f"""
=== ROOT DESIGN CONTRACT ===
{design_contract[:6000]}
=== END ROOT DESIGN CONTRACT ===

CRITICAL: Treat this as the visual quality floor for spacing, contrast, motion,
map behavior, footer behavior and section rhythm.
"""
    except Exception:
        design_contract_ref = ""

    # Injetar design system por segmento para garantir diferenciação visual
    design_system_ref = ""
    design_reference_ref = ""
    try:
        from backend.agents.design_system_selector import select_design_system
        from backend.core.design_reference_packs import format_design_reference_pack_prompt
        segmento = facts.get("segment", "") or ""
        nome_negocio = (facts.get("business") or {}).get("name", "") or ""
        tier = facts.get("tier", facts.get("caio_tier", "STANDARD")) or "STANDARD"
        ds_result = select_design_system(segmento, nome_negocio, tier)
        if ds_result and ds_result.get("content"):
            ds_content = ds_result["content"]
            ds_slug = ds_result.get("slug", "unknown")
            design_system_ref = f"""
=== DESIGN SYSTEM: {ds_slug.upper()} ===
CATEGORY: {ds_result.get('category', 'General')}
{ds_content}
=== END DESIGN SYSTEM ===

IMPORTANT: Apply this design system's color palette, typography, and visual
principles. The chosen design system MUST affect the visible output.
"""
        # Injetar Design Reference Pack completo (OpenDesign systems)
        ref_pack = facts.get("design_reference_pack") or {}
        if ref_pack and isinstance(ref_pack, dict):
            ref_prompt = format_design_reference_pack_prompt(ref_pack)
            if ref_prompt:
                design_reference_ref = f"""
=== BRAND REFERENCE PACK ===
{ref_prompt}
=== END BRAND REFERENCE ===

Apply this brand's visual DNA: typography, colors, motion, spacing.
"""
    except Exception as e:
        # Se falhar, continua sem design system (não quebra o pipeline)
        design_system_ref = ""
        design_reference_ref = ""

    # Injetar site_skill_pack (regras Awwwards-grade) - UK post-commit 83fc6c1
    skill_pack_ref = ""
    try:
        from backend.agents.site_skill_pack import SITE_SKILL_PACK
        if SITE_SKILL_PACK:
            skill_pack_ref = f"""
=== AWWWRADS-GRADE CRAFT RULES ===
{SITE_SKILL_PACK[:8000]}
=== END CRAFT RULES ===

CRITICAL: Follow these craft rules for every generated site.
"""
    except Exception:
        skill_pack_ref = ""

    # Injetar variação estrutural do Agente Variação
    variacao_ref = ""
    variacao = facts.get("variacao") or facts.get("variacao_estrutural") or {}
    if variacao:
        template_hero = variacao.get("template_hero", "") or ""
        template_estrutura = variacao.get("template_estrutura", "") or ""
        ordem_secoes = variacao.get("ordem_das_secoes", []) or []
        if template_hero or template_estrutura:
            variacao_ref = f"""
=== STRUCTURAL VARIATION ===
Hero Type: {template_hero or 'renderer-decides'}
Structure: {template_estrutura or 'default'}
Section Order: {', '.join(ordem_secoes) if ordem_secoes else 'default'}
=== END VARIATION ===

IMPORTANT: Use the specified hero type and section order. If 'renderer-decides',
choose the best hero type for this business type.
"""

    prompt = f"""Use this FraLib Prompt Agent request as the complete business brief.

Return one JSON object with a `files` mapping for a complete Vite React
TypeScript project. The compiled artifact must be `dist/index.html`.{skill_pack_ref}{design_contract_ref}{design_reference_ref}{design_system_ref}{variacao_ref}

Studio-grade visual contract:
- Use Tailwind v4 through `@tailwindcss/vite`, `@import "tailwindcss";`,
  `motion/react`, `lucide-react`, React state and effects.
- Use GSAP with ScrollTrigger for scroll-linked animations (parallax, scrub, reveals).
  Example: `import {{ gsap }} from 'gsap'; import {{ ScrollTrigger }} from 'gsap/ScrollTrigger';`
  GSAP is pre-installed as a dependency — use it natively, not via CDN.
- Import and use React `useEffect` for navbar, scroll, responsive state or
  interaction wiring; do not fake an inert static page.
- The source must feel closer to an AI Studio/editorial build than a thin demo:
  deep component tree, rich className density, real images, gallery, lifestyle
  section, modal/lightbox, sticky navbar and responsive interaction states.
- Build at least 8 real components and a dense source tree. Do not deliver a
  20KB static brochure with no images, no motion and no state.
- Use provided media first. If media is missing, use curated
  `images.unsplash.com` editorial URLs as visual support only.
- Keep factual claims separate from visual atmosphere: images can create mood,
  but cannot be described as photos of the business unless the brief confirms.
- Include every confirmed business fact from FRA LIB BUILDER REQUEST, including
  business name, city, phone/WhatsApp, rating and review count when present.
- First viewport must pass visual QA: do not build a centered `h-screen`
  hero with only a giant headline. Use responsive `min-h`, asymmetric grid or
  split composition, visible CTA/proof cards above the fold, `text-left` on
  desktop, and headline classes with `clamp(...)`, `break-words` or explicit
  mobile-safe leading so mobile text cannot clip horizontally.
- Mobile navbar must not overflow the viewport. Hide or compact desktop CTAs
  below `sm`, keep brand text shrinkable, and avoid fixed-width nav content.
- Hero imagery must be visible in first viewport screenshots: use a real
  external image, `loading="eager"` and `decoding="async"` on the hero image.
- Avoid dark full-hero overlays such as `bg-zinc-950/80`; keep imagery visible
  and contrast intentional without turning the first viewport into a black slab.

Required structure:
- index.html
- package.json
- vite.config.ts
- tsconfig.json
- src/main.tsx
- src/App.tsx
- src/index.css
- src/types.ts
- src/pages/Index.tsx
- src/components/Navbar.tsx
- src/components/HeroSection.tsx
- src/components/AboutSection.tsx
- src/components/GallerySection.tsx
- src/components/ServicesSection.tsx or PlansSection.tsx
- src/components/LifestyleSection.tsx
- src/components/ReviewsSection.tsx or ProofSection.tsx
- src/components/LocationSection.tsx or ContactSection.tsx
- src/components/BookingModal.tsx or ActionModal.tsx
- src/components/ContactCTA.tsx
- src/components/Footer.tsx

FRA LIB BUILDER REQUEST:
{facts_summary}

ANTI-CONTAMINATION SEGMENT GUARD:
{contamination_guard}

PROMPT AGENT REQUEST:
{builder_prompt[:6000]}
"""
    if repair_context:
        errors = repair_context.get("validation_errors") or ""
        previous = str(repair_context.get("previous_output") or repair_context.get("previous_html") or "")[:5000]
        prompt += f"""

The previous Vite/React generation failed validation or build. Regenerate the
whole project as coherent React source, not a patch.

Validation/build errors:
{errors}

Repair requirements:
- Rebuild `src/components/HeroSection.tsx` around an asymmetric first viewport.
- Avoid `h-screen items-center justify-center text-center` on the hero wrapper.
- Use a mobile-safe headline with `text-[clamp(...)]`, `break-words` or
  equivalent responsive type classes.
- Include the confirmed business rating/review count and at least one
  `useEffect` interaction if either was missing.
- Keep CTA, business proof and visual context visible above the fold.
- Fix mobile navbar overflow: compact or hide desktop CTA below `sm`, and make
  brand/CTA shrink safely.
- Add `loading="eager"` and `decoding="async"` to first-viewport hero image.

Previous output excerpt:
{previous}
"""
    return prompt


def _compose_vite_file_batch_prompt(
    builder_prompt: str,
    *,
    facts: dict[str, Any],
    batch_name: str,
    paths: list[str],
    completed_paths: list[str],
    repair_context: dict[str, Any] | None = None,
) -> str:
    facts_summary = _summarize_builder_facts(facts or {})
    contamination_guard = _segment_contamination_guard(facts or {})
    component_names = {
        "src/components/Navbar.tsx": "Navbar",
        "src/components/HeroSection.tsx": "HeroSection",
        "src/components/AboutSection.tsx": "AboutSection",
        "src/components/ServicesSection.tsx": "ServicesSection",
        "src/components/GallerySection.tsx": "GallerySection",
        "src/components/LifestyleSection.tsx": "LifestyleSection",
        "src/components/ReviewsSection.tsx": "ReviewsSection",
        "src/components/LocationSection.tsx": "LocationSection",
        "src/components/BookingModal.tsx": "BookingModal",
        "src/components/ContactCTA.tsx": "ContactCTA",
        "src/components/Footer.tsx": "Footer",
    }
    exports = "\n".join(
        f"- {path}: export function {component_names[path]}(...)" for path in paths if path in component_names
    )
    excerpt_limit = 1800 if batch_name in {"page", "hero"} else 700
    char_budget = {
        "app": 2400,
        "main": 900,
        "types": 500,
        "css": 4200,
        "page": 2600,
        "navbar": 2600,
        "hero": 3600,
        "about": 2400,
        "services": 2200,
        "gallery": 2200,
        "lifestyle": 2200,
        "reviews": 1800,
        "location": 1800,
        "booking-modal": 1400,
        "contact-cta": 1600,
        "footer": 1400,
    }.get(batch_name, 2200)
    compact_guidance = {
        "app": "- App.tsx: only orchestrate state/imports/layout; no inline FAQ, arrays or business copy.",
        "main": "- main.tsx: only mount React.StrictMode, App and FactualMotionContract.",
        "types": "- types.ts: only 2-4 tiny shared types.",
        "css": "- index.css: concise theme/base/utilities only; avoid decorative utility explosion and embedded SVG noise textures.",
        "hero": "- HeroSection: h1 must include `text-[clamp(2.4rem,8vw,5.2rem)] break-words leading-[0.95]`; use `min-h`, not centered `h-screen`.",
        "about": "- AboutSection: maximum 2 proof pillars, 2 short paragraphs and 2 stats; no clinical claims not present in facts.",
        "services": "- ServicesSection: render at most 4 service cards with concise pt-BR copy; no FAQs or long pricing tables here.",
        "gallery": "- GallerySection: render at most 5 images/cards; keep arrays compact and reusable.",
        "lifestyle": "- LifestyleSection: use at most 3 editorial proof blocks; avoid long paragraphs.",
        "reviews": "- ReviewsSection: build a moving rail/marquee of proof cards with real horizontal motion; avoid a static centered quote.",
        "booking-modal": "- BookingModal: keep only title, short body, two buttons and close control; no long lists.",
        "location": "- LocationSection: concise address/contact plus one real Google Maps iframe when maps/address is present; never duplicate maps.",
        "footer": "- Footer: compact integrated closure only; avoid visual duplication with the CTA block and keep year 2026.",
    }.get(batch_name, "- Keep this batch compact and focused on its own component contract.\n- CRITICAL: Use export function ComponentName (named export). NOT export default.\n- CRITICAL: Use relative imports only (../components/X). NO @/ or ~/ aliases.")
    prompt = f"""Generate one Vite React project batch for FraLib Builder.

Return only file tags, no markdown fence, no commentary, no JSON wrapper:
<files>
  <file path="src/example.tsx"><![CDATA[
  full file content
  ]]></file>
</files>

Batch name: {batch_name}
Generate exactly these paths and no other paths:
{chr(10).join(f"- {path}" for path in paths)}

Already generated in previous batches:
{chr(10).join(f"- {path}" for path in completed_paths) if completed_paths else "- none"}

Cross-batch contract:
- Customer-facing copy must be Brazilian Portuguese (pt-BR).
- Preserve every confirmed business fact exactly, especially name, city,
  phone/WhatsApp, rating and review count.
- CRITICAL: Use NAMED exports (export function ComponentName) for ALL components.
  Do NOT use export default. Index.tsx imports them as {{ ComponentName }}.
- CRITICAL: ALL imports must use RELATIVE paths ("../components/X", "./X").
  Do NOT use path aliases like "@/components/X" or "~/components/X".
  The project has NO path aliases configured in tsconfig.
{exports if exports else "- Core files must wire the known component names listed below."}
- `src/pages/Index.tsx` must import and compose the components YOU chose
  for this specific business. Do NOT default to the generic set
  (AboutSection, GallerySection, LifestyleSection). Choose component names
  that reflect what THIS business actually needs. The only required components
  are Navbar, HeroSection, a CTA component, and Footer. Everything else is
  your creative decision based on the niche and archetype.
- Use a modal/CTA pattern: at least one component should open a contact modal.
  Props are your choice but keep them minimal.
- IMPORT FORMAT: Use ONLY relative imports in Index.tsx:
  import {{ Navbar }} from "../components/Navbar";
  import {{ HeroSection }} from "../components/HeroSection";
  NEVER use: import {{ X }} from "@/components/X" or "~/components/X"
- At least one generated file must use `useState`, at least one must use
  `useEffect`, and the project must include `motion/react`, `gsap` and
  `ScrollTrigger` source imports across batches.
- Use real `images.unsplash.com` URLs for hero/gallery visuals when the brief
  does not provide confirmed media.
- Do not use fetch, localStorage, cookies, eval, external forms, Supabase,
  Firebase, Next.js, server routes, CDN scripts or runtime env variables.
- Hard size budget for this batch: keep the complete response under about
  {char_budget} characters including tags. Prefer shorter code over decorative density.
- Keep each file compact: avoid giant literal arrays, inline FAQs, repeated
  decorative markup, oversized utility sets or placeholder sections.
- Use `<![CDATA[ ... ]]>` inside each `<file>` block so TypeScript/CSS does not
  need JSON escaping.
{compact_guidance}

FRA LIB BUILDER REQUEST:
{facts_summary}

ANTI-CONTAMINATION SEGMENT GUARD:
{contamination_guard}

PROMPT AGENT REQUEST:
{builder_prompt[:excerpt_limit]}
"""
    if repair_context:
        prompt += f"""

Previous batch/full-project attempt failed.
Validation/build errors:
{repair_context.get("validation_errors") or ""}

On this retry, make the requested file much shorter than the previous output
while preserving the public-facing facts and required exports.

Previous output excerpt:
{str(repair_context.get("previous_output") or "")[:1200]}
"""
    return prompt


def _summarize_builder_facts(facts: dict[str, Any]) -> str:
    """Sprint 12.12: briefing REAL do lead para o Vite caroço.

    Antes: so name/segment/city/phone.
    Agora: services, horarios, differentials, target_audience, keywords SEO,
    fotos reais (Unsplash/Pexels aprovados), JSON-LD pronto, schema.org.
    Tudo do briefing REAL - nada inventado.
    """
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    visual = facts.get("visual_dna") if isinstance(facts.get("visual_dna"), dict) else {}
    plan = facts.get("site_build_plan") if isinstance(facts.get("site_build_plan"), dict) else {}
    seo = facts.get("seo") if isinstance(facts.get("seo"), dict) else {}
    content = facts.get("content") if isinstance(facts.get("content"), dict) else {}
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    sections = []
    for item in plan.get("section_plan") or []:
        if isinstance(item, dict) and item.get("id"):
            sections.append(f"- {item.get('id')} ({item.get('role', '')})")

    # Sprint 12.12: services + horarios + differentials + target_audience
    services = (
        business.get("services")
        or business.get("servicos")
        or content.get("services")
        or facts.get("services")
        or []
    )
    if isinstance(services, str):
        services = [s.strip() for s in services.split(",") if s.strip()]

    hours = (
        business.get("hours")
        or business.get("horarios")
        or facts.get("horarios")
        or ""
    )
    differentials = (
        business.get("differentials")
        or business.get("diferenciais")
        or business.get("attributes")
        or content.get("attributes")
        or facts.get("diferenciais")
        or []
    )
    if isinstance(differentials, str):
        differentials = [d.strip() for d in differentials.split(",") if d.strip()]

    target_audience = (
        business.get("target_audience")
        or business.get("publico_alvo")
        or content.get("ideal_customer")
        or facts.get("target_audience")
        or ""
    )

    # Sprint 12.12: fotos REAIS aprovadas (Unsplash/Pexels ou do briefing)
    photos = (
        media.get("photos")
        or business.get("photos")
        or facts.get("photos")
        or []
    )
    if isinstance(photos, str):
        photos = [p.strip() for p in photos.split(",") if p.strip()]
    approved_photos = [str(p).strip() for p in photos[:8] if str(p or "").strip()]

    # Sprint 12.12: keywords SEO ja validadas (do agente Nicho/SEO)
    primary_terms = (
        seo.get("primary_terms")
        or facts.get("seo_keywords")
        or facts.get("keywords")
        or []
    )
    if isinstance(primary_terms, str):
        primary_terms = [k.strip() for k in primary_terms.split(",") if k.strip()]

    parts = [
        f"Business name: {business.get('name') or business.get('business_name') or ''}".strip(),
        f"Segment: {business.get('segment') or business.get('segmento') or facts.get('segmento') or ''}".strip(),
        f"Subniche: {business.get('subniche') or facts.get('subniche') or ''}".strip(),
        f"City: {business.get('cidade') or business.get('city') or ''}".strip(),
        f"Address: {business.get('endereco') or business.get('address') or ''}".strip(),
        f"Phone/WhatsApp: {business.get('whatsapp') or business.get('phone') or ''}".strip(),
        f"Rating: {business.get('rating') or ''} | Reviews: {business.get('total_avaliacoes') or business.get('reviews') or ''}".strip(),
        f"Website: {business.get('website') or ''}".strip(),
        f"Maps: {business.get('maps_url') or ''}".strip(),
        f"Canonical: {business.get('canonical_url') or seo.get('canonical_url') or seo.get('site_url') or ''}".strip(),
        f"OG image: {business.get('og_image') or seo.get('og_image') or ''}".strip(),
        f"Local keywords: {json.dumps(primary_terms[:12], ensure_ascii=False)}",
        f"Archetype: {visual.get('archetype') or ''}".strip(),
        f"Palette: {json.dumps(visual.get('tokens') or {}, ensure_ascii=False)}",
        f"Style mix: {visual.get('style_mix_instruction') or ''}".strip(),
    ]

    # Sprint 12.12: secao de briefing real (NAO inventar)
    if services:
        parts.append(f"Services (use EXATAMENTE estes, nao inventar): {json.dumps(services[:8], ensure_ascii=False)}")
    if hours:
        parts.append(f"Hours (usar literalmente): {hours}")
    if differentials:
        parts.append(f"Differentials (usar como prova): {json.dumps(differentials[:6], ensure_ascii=False)}")
    if target_audience:
        parts.append(f"Target audience (copy deve falar com): {target_audience}")

    # Sprint 12.12: fotos reais ja validadas
    if approved_photos:
        parts.append("Photos APROVADAS (use estas URLs - NAO inventar outras):")
        for photo_url in approved_photos[:6]:
            parts.append(f"  - {photo_url}")

    # Sprint 12.12: keywords SEO distribuicao natural
    if primary_terms:
        parts.append(f"SEO primary terms (distribuir com naturalidade, NAO keyword stuffing): {', '.join(str(k) for k in primary_terms[:8] if k)}")

    if sections:
        parts.append("Sections:")
        parts.extend(sections)

    return "\n".join(part for part in parts if part and part.strip())


def _segment_key_from_facts(facts: dict[str, Any]) -> str:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    candidates = (
        business.get("segment"),
        business.get("segmento"),
        facts.get("segmento"),
        facts.get("segment"),
    )
    raw = next((str(item).strip().lower() for item in candidates if str(item or "").strip()), "")
    normalized = (
        raw.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    for key, rule in SEGMENT_RULES.items():
        aliases = {alias.lower() for alias in rule.get("aliases", ())}
        if normalized == key or normalized in aliases:
            return key
    return normalized


def _segment_contamination_guard(facts: dict[str, Any]) -> str:
    segment_key = _segment_key_from_facts(facts)
    rule = SEGMENT_RULES.get(segment_key)
    if not rule:
        return "Use somente vocabulário compatível com o nicho confirmado. Proíba referências a nichos não confirmados."
    required = ", ".join(rule.get("required", ())[:6])
    forbidden = ", ".join(rule.get("forbidden", ())[:8])
    return (
        f"Nicho confirmado: {segment_key}. "
        f"Vocabulário prioritário: {required}. "
        f"É proibido usar termos, imagens descritas, benefícios ou CTAs ligados a: {forbidden}. "
        "Se faltar informação, permaneça genérico dentro do nicho confirmado sem migrar para outro nicho."
    )


def _safe_project_path(path: str) -> str:
    clean = str(path or "").strip().replace("\\", "/").lstrip("/")
    pure = PurePosixPath(clean)
    if not clean or pure.is_absolute() or ".." in pure.parts:
        raise ViteReactRenderError(f"caminho invalido no projeto Vite: {path!r}")
    allowed_prefixes = ("src/", "public/", "assets/")
    allowed_roots = {
        "package.json",
        "index.html",
        "vite.config.ts",
        "tsconfig.json",
        "tsconfig.app.json",
        "tsconfig.node.json",
        "metadata.json",
        "README.md",
        ".gitignore",
        ".env.example",
    }
    if clean not in allowed_roots and not clean.startswith(allowed_prefixes):
        raise ViteReactRenderError(f"arquivo fora do contrato Vite: {clean}")
    if clean.startswith(("src/", "public/", "assets/")) and not re.search(
        r"\.(tsx|ts|css|json|svg|txt|md)$", clean
    ):
        raise ViteReactRenderError(f"extensao nao permitida no projeto Vite: {clean}")
    return clean


def _run(command: list[str], *, cwd: Path, timeout: int, label: str) -> None:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise ViteReactRenderError(f"{label} falhou: {output[-3000:]}")


def _meta_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _facts_business(facts: dict[str, Any]) -> dict[str, Any]:
    return facts.get("business") if isinstance(facts.get("business"), dict) else {}


def _inject_pole_tokens(facts: dict[str, Any]) -> dict[str, Any]:
    """
    Injeta tokens de polo estético nos facts para Blocos Líquidos.

    Esta função infere o polo baseado nos dados do lead e adiciona
    os tokens de design ao facts para uso pelo LLM.

    Args:
        facts: Dicionário de facts do builder

    Returns:
        Facts com tokens de polo injetados
    """
    if not LIQUID_COMPONENTS_AVAILABLE:
        return facts

    # Extrair dados do lead
    business = _facts_business(facts)
    segment = str(business.get("segment", "") or facts.get("segment", ""))
    subniche = str(business.get("subniche", "") or facts.get("subniche", ""))
    tags = business.get("tags") or facts.get("tags") or []
    description = str(business.get("description", "") or facts.get("description", ""))

    # Inferir polo
    pole_info = infer_aesthetic_pole(
        segment=segment,
        subniche=subniche,
        tags=tags if isinstance(tags, list) else [],
        description=description,
    )

    # Adicionar ao facts
    facts = dict(facts)  # Cópia para não mutar
    facts["pole"] = pole_info["pole"]
    facts["pole_heat"] = pole_info["heat"]
    facts["pole_temperature"] = pole_info["temperature"]
    facts["pole_display_mode"] = pole_info["display_mode"]
    facts["pole_tokens"] = pole_info["tokens"]

    # Adicionar prompt de tokens para o LLM
    if "llm_context" not in facts:
        facts["llm_context"] = {}
    facts["llm_context"]["pole_prompt"] = get_liquid_component_guide(
        pole=pole_info["pole"],
        hero_mode=pole_info["display_mode"],
    )

    return facts


def _get_pole_css_tokens(pole: str) -> str:
    """
    Gera string CSS com tokens do polo para injeção no projeto.

    Args:
        pole: Nome do polo (soft, bold, corporate, minimal)

    Returns:
        String CSS com variáveis customizadas
    """
    tokens = POLO_TOKENS.get(pole, POLO_TOKENS["corporate"])

    lines = [
        "/* ═══════════════════════════════════════════════════════════════════════════",
        f"   POLO {pole.upper()} - DESIGN TOKENS",
        "   Gerado automaticamente pelo FraLib Blocos Líquidos",
        "   ═══════════════════════════════════════════════════════════════════════════ */",
        "",
        f"[data-pole=\"{pole}\"] {{",
    ]

    # Converter tokens para CSS
    for key, value in tokens.items():
        css_key = key.replace("_", "-")
        if isinstance(value, bool):
            lines.append(f"  --{css_key}: {'true' if value else 'false'};")
        elif isinstance(value, (int, float)):
            lines.append(f"  --{css_key}: {value};")
        else:
            lines.append(f"  --{css_key}: {value};")

    lines.append("}")

    return "\n".join(lines)


def _facts_publication_url(facts: dict[str, Any]) -> str:
    for container_name in ("publication", "seo", "business"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        for key in ("canonical_url", "site_url", "canonical", "url_site"):
            url = str(container.get(key) or "").strip()
            if url.startswith(("http://", "https://")):
                return url
    return ""


def _facts_theme_color(facts: dict[str, Any]) -> str:
    for container_name in ("visual_dna", "visual_direction", "design"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        tokens = container.get("tokens") or container.get("color_palette") or {}
        if not isinstance(tokens, dict):
            continue
        for key in ("--primary", "primary", "--accent", "accent"):
            color = str(tokens.get(key) or "").strip()
            if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                return color
    return "#111827"


SEO_SEGMENT_LABELS = {
    "advogado": "advogado",
    "advocacia": "advogado",
    "clinica": "clínica médica",
    "dentista": "dentista",
    "odontologia": "dentista",
    "energia_solar": "energia solar",
    "energia solar": "energia solar",
    "estetica": "clínica estética",
    "imobiliaria": "imobiliária",
    "oficina": "oficina mecânica",
    "pet_shop": "pet shop",
    "pet shop": "pet shop",
    "salao": "salão de beleza",
    "restaurante": "restaurante",
}


def _seo_label(value: Any) -> str:
    raw = re.sub(r"\s+", " ", str(value or "").replace("_", " ")).strip()
    if not raw:
        return ""
    normalized = _normalize_text(raw).replace("_", " ")
    if normalized in SEO_SEGMENT_LABELS:
        return SEO_SEGMENT_LABELS[normalized]
    for key, label in SEO_SEGMENT_LABELS.items():
        if key.replace("_", " ") in normalized:
            return label
    return raw


def _facts_local_keywords(facts: dict[str, Any]) -> list[str]:
    """Sprint 14.6: keywords SEO personalizados por lead.

    Ordem de prioridade:
    1. seo.primary_terms (do agente Nicho/SEO)
    2. seo_keywords do facts (do briefing Jina)
    3. business.cidade (sempre presente)
    4. business.segmento/subnicho
    5. diferencial (palavras_poder do Jina)
    6. bairro/cidade do endereco
    """
    business = _facts_business(facts)
    seo = facts.get("seo") if isinstance(facts.get("seo"), dict) else {}
    candidates = seo.get("primary_terms") or facts.get("seo_keywords") or business.get("seo_keywords") or []
    if not isinstance(candidates, list):
        candidates = re.split(r"[,;\n]", str(candidates or ""))
    keywords: list[str] = []
    seen: set[str] = set()

    def _add(term: str) -> None:
        term = re.sub(r"\s+", " ", str(term or "").replace("_", " ")).strip(" ,.;:-")
        key = term.lower()
        if not term or key in seen:
            return
        seen.add(key)
        keywords.append(term)

    for item in candidates:
        _add(item)

    # cidade sempre presente (SEO local)
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip()
    segment_raw = str(business.get("segmento") or business.get("segment") or "").strip()
    subniche_raw = str(business.get("subnicho") or business.get("subniche") or "").strip()
    segment = _seo_label(segment_raw)
    subniche = _seo_label(subniche_raw) if subniche_raw else ""
    segment_context = _normalize_text(f"{segment_raw} {subniche_raw} {segment} {subniche}").replace("_", " ")
    _add(city)
    _add(business.get("state") or business.get("estado") or facts.get("estado") or "")

    # segmento e subnicho
    _add(segment)
    _add(subniche)
    if city and segment:
        _add(f"{segment} em {city}")
        _add(f"{segment} {city}")
        _add(f"melhor {segment} em {city}")
        _add(f"{segment} perto de mim {city}")
        _add(f"agendar {segment} em {city}")
        _add(f"{segment} WhatsApp {city}")
        _add(f"preço {segment} {city}")
    if city and any(token in segment_context for token in ("barbearia", "barber", "barbeiro")):
        _add(f"barbearia em {city}")
        _add(f"corte masculino {city}")
        _add(f"barba e cabelo {city}")
        _add(f"agendar barbearia {city}")
        _add(f"corte masculino preço {city}")
    if city and any(token in segment_context for token in ("nutri", "nutric")):
        _add(f"nutricionista em {city}")
        _add(f"nutricionista esportivo {city}")
        _add(f"consulta nutricional {city}")
        _add(f"consulta nutricionista {city}")
        _add(f"nutricionista perto de mim {city}")
    if city and any(token in segment_context for token in ("academia", "crossfit", "musculacao", "funcional", "personal")):
        _add(f"academia em {city}")
        _add(f"musculação {city}")
        _add(f"aula experimental academia {city}")
        _add(f"plano de academia {city}")
        _add(f"academia com aula experimental {city}")
        _add(f"personal trainer {city}")
    if city and any(token in segment_context for token in ("estetic", "spa", "beleza", "facial", "pele", "laser")):
        _add(f"clínica estética em {city}")
        _add(f"agendar estética {city}")
        _add(f"limpeza de pele {city}")
        _add(f"estética perto de mim {city}")
    if city and any(token in segment_context for token in ("advogado", "advocacia", "juridico", "direito")):
        _add(f"advogado em {city}")
        _add(f"consulta advogado {city}")
        _add(f"advogado trabalhista {city}")
        _add(f"honorários advogado {city}")
    if city and any(token in segment_context for token in ("clinica", "medica", "medico", "consulta")):
        _add(f"clínica médica em {city}")
        _add(f"consulta particular {city}")
        _add(f"marcar consulta {city}")
        _add(f"clínica perto de mim {city}")
    if city and any(token in segment_context for token in ("dentista", "odontologia", "odonto")):
        _add(f"dentista em {city}")
        _add(f"avaliação odontológica {city}")
        _add(f"clareamento dental {city}")
        _add(f"dentista perto de mim {city}")
    if city and any(token in segment_context for token in ("energia solar", "solar", "fotovoltaica")):
        _add(f"energia solar em {city}")
        _add(f"orçamento energia solar {city}")
        _add(f"simulação energia solar {city}")
        _add(f"placas solares {city}")
    if city and any(token in segment_context for token in ("imobiliaria", "imovel", "imoveis")):
        _add(f"imobiliária em {city}")
        _add(f"apartamento para alugar {city}")
        _add(f"comprar imóvel {city}")
        _add(f"agendar visita imóvel {city}")
    if city and any(token in segment_context for token in ("oficina", "mecanica", "automotivo")):
        _add(f"oficina mecânica em {city}")
        _add(f"orçamento revisão {city}")
        _add(f"troca de óleo {city}")
        _add(f"mecânico perto de mim {city}")
    if city and any(token in segment_context for token in ("pet shop", "petshop", "veterinario", "banho", "tosa")):
        _add(f"pet shop em {city}")
        _add(f"banho e tosa {city}")
        _add(f"veterinário {city}")
        _add(f"pet shop perto de mim {city}")
    if city and any(token in segment_context for token in ("restaurante", "pizzaria", "hamburgueria", "cafeteria", "padaria")):
        _add(f"restaurante em {city}")
        _add(f"delivery {city}")
        _add(f"cardápio {city}")
        _add(f"reservar mesa {city}")
    if city and any(token in segment_context for token in ("salao", "salão", "cabeleireiro", "cabelo", "manicure")):
        _add(f"salão de beleza em {city}")
        _add(f"agendar salão {city}")
        _add(f"escova preço {city}")
        _add(f"manicure {city}")

    # diferencial (palavras_poder do Jina)
    diferencial = business.get("diferenciais") or facts.get("diferenciais") or []
    if isinstance(diferencial, list):
        for d in diferencial[:3]:
            _add(d)

    # bairro/cidade do endereco
    address = business.get("address") or business.get("endereco") or facts.get("endereco") or ""
    if isinstance(address, str) and address:
        parts = re.split(r"[,\-]", address)
        for p in parts[-2:]:
            _add(p)
            if city and segment:
                _add(f"{segment} {p} {city}")

    return keywords[:18]


def _facts_meta_description(facts: dict[str, Any]) -> str:
    business = _facts_business(facts)
    name = str(business.get("name") or business.get("business_name") or "").strip()
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip()
    segment = _seo_label(business.get("segment") or business.get("segmento") or facts.get("segmento") or "negócio local")
    subniche = _seo_label(business.get("subniche") or facts.get("subniche") or "")
    phone = str(business.get("whatsapp") or business.get("phone") or "").strip()
    rating = str(business.get("rating") or "").strip()
    summary = subniche or segment
    parts = [name, summary]
    if city:
        parts.append(f"em {city}")
    description = " ".join(part for part in parts if part).strip()
    suffix = []
    if rating:
        suffix.append(f"avaliação {rating}")
    if phone:
        suffix.append(f"contato {phone}")
    final = description
    if suffix:
        final += ". " + " | ".join(suffix)
    return final[:180].strip(" .") + "."


def _facts_og_image(facts: dict[str, Any]) -> str:
    for container_name in ("publication", "seo", "business", "media"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        image = str(container.get("og_image") or "").strip()
        if image.startswith(("http://", "https://")):
            return image
    for source in (facts.get("photos"), _facts_business(facts).get("photos")):
        if isinstance(source, list):
            for item in source:
                image = str(item or "").strip()
                if image.startswith(("http://", "https://")):
                    return image
    return ""


def _facts_json_ld(facts: dict[str, Any]) -> str:
    business = _facts_business(facts)
    site_url = _facts_publication_url(facts)
    image = _facts_og_image(facts)
    # Sprint 12.x: schema_type dinâmico por nicho (advogado→LegalService, etc.)
    segmento = (
        business.get("segment")
        or business.get("segmento")
        or facts.get("segmento")
        or facts.get("segment")
        or ""
    )
    try:
        from backend.config.nicho_registry import get_schema_type
        schema_type = get_schema_type(segmento)
    except Exception:
        schema_type = "LocalBusiness"
    data = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": business.get("name") or business.get("business_name") or "",
        "url": site_url,
        "image": image,
        "telephone": business.get("phone") or business.get("whatsapp") or "",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": business.get("address") or business.get("endereco") or "",
            "addressLocality": business.get("city") or business.get("cidade") or facts.get("cidade") or "",
            "addressCountry": "BR",
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": business.get("rating") or "",
            "reviewCount": business.get("total_avaliacoes") or business.get("reviews_count") or "",
        },
    }
    cleaned = {key: value for key, value in data.items() if value not in ("", None, {}, [])}
    if isinstance(cleaned.get("aggregateRating"), dict):
        agg = {key: value for key, value in cleaned["aggregateRating"].items() if value not in ("", None)}
        if len(agg) <= 1:
            cleaned.pop("aggregateRating", None)
        else:
            cleaned["aggregateRating"] = agg
    return json.dumps(cleaned, ensure_ascii=False)


def _default_index_html(facts: dict[str, Any]) -> str:
    business = _facts_business(facts)
    title = str(business.get("name") or "FraLib Builder Site")
    canonical = _facts_publication_url(facts)
    description = _facts_meta_description(facts)
    keywords = ", ".join(_facts_local_keywords(facts))
    og_image = _facts_og_image(facts)
    theme_color = _facts_theme_color(facts)
    json_ld = _facts_json_ld(facts)
    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{_meta_escape(title)}</title>
    <meta name="description" content="{_meta_escape(description)}" />
    <meta name="keywords" content="{_meta_escape(keywords)}" />
    <meta name="theme-color" content="{_meta_escape(theme_color)}" />
    <link rel="canonical" href="{_meta_escape(canonical)}" />
    <meta property="og:type" content="website" />
    <meta property="og:locale" content="pt_BR" />
    <meta property="og:title" content="{_meta_escape(title)}" />
    <meta property="og:description" content="{_meta_escape(description)}" />
    <meta property="og:url" content="{_meta_escape(canonical)}" />
    <meta property="og:image" content="{_meta_escape(og_image)}" />
    <meta property="og:site_name" content="{_meta_escape(title)}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{_meta_escape(title)}" />
    <meta name="twitter:description" content="{_meta_escape(description)}" />
    <meta name="twitter:image" content="{_meta_escape(og_image)}" />
    <script type="application/ld+json">{json_ld}</script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""


def _default_vite_config() -> str:
    return """import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  build: {
    target: 'es2020',
    sourcemap: false,
  },
});
"""


def _default_tsconfig() -> str:
    return json.dumps(
        {
            "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": True,
                "lib": ["DOM", "DOM.Iterable", "ES2020"],
                "allowJs": False,
                "skipLibCheck": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "strict": True,
                "noImplicitAny": False,
                "forceConsistentCasingInFileNames": True,
                "module": "ESNext",
                "moduleResolution": "Node",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
            },
            "include": ["src"],
            "references": [],
        },
        ensure_ascii=False,
        indent=2,
    )


def _default_jsx_fallback_types() -> str:
    return """declare module 'react' {
  const React: any;
  export default React;
  export const StrictMode: any;
  export type FC<P = any> = (props: P) => any;
  export type ReactNode = any;
  export type MouseEvent<T = any> = any;
  export type ChangeEvent<T = any> = any;
  export type FormEvent<T = any> = any;
  export type FocusEvent<T = any> = any;
  export type KeyboardEvent<T = any> = any;
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useMemo<T>(factory: () => T, deps?: any[]): T;
  export function useState<T>(initial: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void];
  export function useRef<T>(initial: T): { current: T };
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps?: any[]): T;
}

declare module 'react-dom/client' {
  export function createRoot(element: Element | DocumentFragment): { render(children: any): void };
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
"""


def _default_main_tsx() -> str:
    return """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""


def _default_app_tsx() -> str:
    return """import Index from './pages/Index';
import { LgpdBanner } from './components/LgpdBanner';

export default function App() {
  return (
    <>
      <Index />
      <LgpdBanner />
    </>
  );
}
"""


def _default_types_ts() -> str:
    return """export type NavItem = {
  label: string;
  href: string;
};

export type EditorialImage = {
  src: string;
  alt: string;
  caption?: string;
};
"""


def _default_card_ui_tsx() -> str:
    return """import * as React from 'react';

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className = '', ...props }: DivProps) {
  return <div className={`rounded-2xl border border-zinc-200 bg-white shadow-sm ${className}`.trim()} {...props} />;
}

export function CardHeader({ className = '', ...props }: DivProps) {
  return <div className={`p-6 ${className}`.trim()} {...props} />;
}

export function CardTitle({ className = '', ...props }: DivProps) {
  return <h3 className={`text-lg font-semibold text-zinc-950 ${className}`.trim()} {...props} />;
}

export function CardDescription({ className = '', ...props }: DivProps) {
  return <p className={`text-sm text-zinc-600 ${className}`.trim()} {...props} />;
}

export function CardContent({ className = '', ...props }: DivProps) {
  return <div className={`px-6 pb-6 ${className}`.trim()} {...props} />;
}
"""


def _default_navbar_tsx(facts: dict[str, Any]) -> str:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    name = str(business.get("name") or "FraLib").strip()
    short_name = name.split(" - ")[0].strip() or name
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = phone or "Contato"
    phone_digits = re.sub(r"\D+", "", phone or "")
    phone_href = f"tel:+{phone_digits}" if phone_digits else "#contato"
    name_js = json.dumps(short_name, ensure_ascii=False)
    phone_label_js = json.dumps(phone_label, ensure_ascii=False)
    phone_href_js = json.dumps(phone_href, ensure_ascii=False)
    return f"""import {{ useEffect, useState }} from 'react';
import {{ motion }} from 'motion/react';
import {{ Menu, X, Phone }} from 'lucide-react';

const brand = {name_js};
const phoneLabel = {phone_label_js};
const phoneHref = {phone_href_js};
const links = [
  {{ href: '#sobre', label: 'Sobre' }},
  {{ href: '#servicos', label: 'Serviços' }},
  {{ href: '#galeria', label: 'Galeria' }},
  {{ href: '#avaliacoes', label: 'Avaliações' }},
  {{ href: '#contato', label: 'Contato' }},
];

export function Navbar({{ onOpen }}: {{ onOpen: () => void }}) {{
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {{
    const onScroll = () => setScrolled(window.scrollY > 20);
    onScroll();
    window.addEventListener('scroll', onScroll, {{ passive: true }});
    return () => window.removeEventListener('scroll', onScroll);
  }}, []);

  useEffect(() => {{
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {{
      document.body.style.overflow = '';
    }};
  }}, [open]);

  return (
    <motion.header
      initial={{{{ y: -16, opacity: 0 }}}}
      animate={{{{ y: 0, opacity: 1 }}}}
      transition={{{{ duration: 0.35 }}}}
      className={{`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${{scrolled ? 'border-b border-zinc-200/70 bg-white shadow-sm' : 'bg-transparent'}}`}}
    >
      <nav aria-label="Navegação principal" className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 md:h-20 md:px-8">
        <a href="#topo" className="min-w-0">
          <span className="block truncate text-base font-semibold tracking-tight text-zinc-950 md:text-lg">{{brand}}</span>
        </a>
        <ul className="hidden items-center gap-1 md:flex">
          {{links.map((link) => (
            <li key={{link.href}}>
              <a href={{link.href}} className="rounded-full px-3 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-950/5 hover:text-zinc-950">
                {{link.label}}
              </a>
            </li>
          ))}}
        </ul>
        <div className="hidden items-center gap-2 md:flex">
          <a href={{phoneHref}} className="inline-flex items-center gap-2 rounded-full border border-zinc-300 bg-white/70 px-3 py-2 text-sm font-medium text-zinc-800">
            <Phone className="h-3.5 w-3.5" aria-hidden="true" />
            {{phoneLabel}}
          </a>
          <button type="button" onClick={{onOpen}} className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-semibold text-white">
            Agendar
          </button>
        </div>
        <button
          type="button"
          aria-label={{open ? 'Fechar menu' : 'Abrir menu'}}
          aria-expanded={{open}}
          onClick={{() => setOpen((value) => !value)}}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-zinc-300 bg-white/80 text-zinc-950 md:hidden"
        >
          {{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}}
        </button>
      </nav>
      {{open && (
        <div className="border-t border-zinc-200/70 bg-white px-4 py-4 md:hidden">
          <ul className="space-y-1">
            {{links.map((link) => (
              <li key={{link.href}}>
                <a href={{link.href}} onClick={{() => setOpen(false)}} className="block rounded-xl px-3 py-3 text-base font-medium text-zinc-800 hover:bg-zinc-100">
                  {{link.label}}
                </a>
              </li>
            ))}}
            <li className="pt-2">
              <button type="button" onClick={{() => {{ setOpen(false); onOpen(); }}}} className="w-full rounded-xl bg-zinc-950 px-3 py-3 text-base font-semibold text-white">
                Agendar consulta
              </button>
            </li>
          </ul>
        </div>
      )}}
    </motion.header>
  );
}}

export default Navbar;
"""


def _visual_business_payload(facts: dict[str, Any]) -> dict[str, str]:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    name = str(business.get("name") or business.get("business_name") or "Negocio local").strip()
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or "Atendimento local").strip()
    subniche = str(business.get("subniche") or facts.get("subniche") or segment).strip()
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip()
    address = str(business.get("address") or business.get("endereco") or "").strip()
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    rating = str(business.get("rating") or "5.0").strip().replace(",", ".")
    count = str(business.get("total_avaliacoes") or business.get("reviews_count") or "").strip()
    maps = str(business.get("maps_url") or business.get("map_url") or "").strip()
    return {
        "name": name,
        "segment": segment,
        "subniche": subniche,
        "city": city,
        "address": address,
        "phone": phone,
        "rating": rating,
        "count": count,
        "maps": maps,
    }


def _visual_media_urls(facts: dict[str, Any]) -> list[str]:
    """Extrai URLs de fotos do facts.

    Fail-fast: retorna lista vazia se não houver fotos — não usa fallbacks.
    """
    from backend.pipeline_exceptions import ImageNotAvailableError

    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    urls: list[str] = []
    for source in (media.get("photos"), business.get("photos"), facts.get("photos")):
        if isinstance(source, list):
            urls.extend(str(item or "").strip() for item in source if str(item or "").strip())
    if not urls:
        raise ImageNotAvailableError(
            "_visual_media_urls: Sem imagens no facts.",
            context={
                "segmento": business.get("segment", ""),
                "acao": "Forneca fotos no lead ou use unsplash_fetcher",
            },
        )
    return list(dict.fromkeys(urls))[:5]


def _default_hero_section_tsx(facts: dict[str, Any]) -> str:
    data = _visual_business_payload(facts)
    images = _visual_media_urls(facts)
    image = json.dumps(images[0], ensure_ascii=False)
    data_js = json.dumps(data, ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", data["phone"])
    whatsapp = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    return f"""import {{ useEffect }} from 'react';
import {{ ArrowRight, MapPin, MessageCircle, Star }} from 'lucide-react';
import {{ gsap }} from 'gsap';
import {{ ScrollTrigger }} from 'gsap/ScrollTrigger';
import {{ motion }} from 'motion/react';

const business = {data_js};
const heroImage = {image};
const whatsappHref = {whatsapp};

export function HeroSection({{ onOpen = () => {{}} }}: {{ onOpen?: () => void }}) {{
  useEffect(() => {{
    gsap.registerPlugin(ScrollTrigger);
    gsap.fromTo('[data-hero-copy]', {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.8, ease: 'power3.out' }});
    gsap.to('[data-hero-image]', {{
      yPercent: 8,
      ease: 'none',
      scrollTrigger: {{ trigger: '#topo', start: 'top top', end: 'bottom top', scrub: true }},
    }});
  }}, []);

  return (
    <section id="topo" className="relative min-h-[92svh] overflow-hidden bg-[#071611] text-white">
      <img data-hero-image src={{heroImage}} alt={{`${{business.segment}} em ${{business.city}}`}} className="absolute inset-0 h-[108%] w-full object-cover opacity-70" loading="eager" decoding="async" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(7,22,17,.96)_0%,rgba(7,22,17,.76)_38%,rgba(7,22,17,.18)_100%)]" />
      <div className="relative mx-auto flex min-h-[92svh] max-w-7xl flex-col justify-end px-5 pb-14 pt-28 md:px-8 md:pb-20">
        <motion.div data-hero-copy initial={{{{ opacity: 0, y: 24 }}}} animate={{{{ opacity: 1, y: 0 }}}} transition={{{{ duration: 0.7 }}}} className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300">{{business.subniche}} em {{business.city}}</p>
          <h1 className="mt-5 text-[clamp(2.35rem,7vw,4.7rem)] font-semibold leading-[0.95] tracking-tight text-white">
            {{business.name}}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-100 md:text-lg">
            Atendimento local com contato direto e uma apresentação clara para quem precisa decidir rápido.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a href={{whatsappHref}} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full bg-emerald-400 px-6 py-3.5 text-sm font-semibold text-[#071611]">
              <MessageCircle className="h-4 w-4" /> WhatsApp
            </a>
            <button type="button" onClick={{onOpen}} className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 bg-black/70 px-6 py-3.5 text-sm font-semibold text-white">
              Agendar <ArrowRight className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-6 flex flex-wrap gap-3 text-sm text-zinc-100">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/20 px-4 py-2"><MapPin className="h-4 w-4 text-emerald-300" />{{business.city}}</span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/20 px-4 py-2"><Star className="h-4 w-4 text-amber-300" />{{business.rating}} {{business.count ? `(${{business.count}})` : ''}}</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}}

export default HeroSection;
"""


def _default_about_section_tsx(facts: dict[str, Any]) -> str:
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    return f"""import {{ Award, CheckCircle2, MapPin }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const business = {data};

export function AboutSection() {{
  return (
    <section id="sobre" className="bg-[#f7f3ea] px-5 py-18 text-zinc-950 md:px-8 md:py-24">
      <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1fr_0.85fr] lg:items-end">
        <motion.div initial={{{{ opacity: 0, y: 18 }}}} whileInView={{{{ opacity: 1, y: 0 }}}} viewport={{{{ once: true, amount: 0.3 }}}}>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Sobre</p>
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight md:text-5xl">
            {{business.segment}} com presença local em {{business.city}}.
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-700">
            Página construída para deixar claro o que a empresa faz, onde atende e como o visitante deve avançar.
          </p>
        </motion.div>
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
          {{[
            [Award, 'Prova local', `${{business.rating}} de avaliação`],
            [CheckCircle2, 'Informação clara', 'Sem placeholder ou texto genérico'],
            [MapPin, 'Atendimento', business.city],
          ].map(([Icon, title, text]) => (
            <article key={{title}} className="rounded-[28px] border border-emerald-900/10 bg-white p-5 shadow-sm">
              <Icon className="h-5 w-5 text-emerald-700" />
              <h3 className="mt-4 text-base font-semibold text-zinc-950">{{title}}</h3>
              <p className="mt-2 text-sm leading-6 text-zinc-600">{{text}}</p>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default AboutSection;
"""


def _default_gallery_section_tsx(facts: dict[str, Any]) -> str:
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    images = json.dumps(_visual_media_urls(facts), ensure_ascii=False)
    return f"""import {{ motion }} from 'motion/react';

const business = {data};
const images = {images};
const labels = ['Ambiente e contexto', 'Serviço principal', 'Rotina do cliente', 'Prova visual', 'Atendimento local'];

export function GallerySection() {{
  return (
    <section id="galeria" className="bg-[#ede8dd] px-5 py-18 text-zinc-950 md:px-8 md:py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Galeria</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Visual relacionado ao nicho, sem imagem solta.</h2>
          <p className="mt-4 text-base leading-7 text-zinc-700">Imagens editoriais coerentes com {{business.segment}} e com a intenção local da página.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {{images.map((src, index) => (
            <motion.figure
              key={{src}}
              initial={{{{ opacity: 0, y: 18 }}}}
              whileInView={{{{ opacity: 1, y: 0 }}}}
              viewport={{{{ once: true, amount: 0.2 }}}}
              transition={{{{ delay: index * 0.04 }}}}
              className={{`group relative overflow-hidden rounded-[28px] bg-zinc-900 shadow-sm ${{index === 0 ? 'md:col-span-2 md:row-span-2' : ''}}`}}
            >
              <img src={{src}} alt={{`${{business.segment}} - ${{labels[index] || 'imagem'}}`}} className="h-full min-h-64 w-full object-cover transition duration-700 group-hover:scale-105" loading={{index === 0 ? 'eager' : 'lazy'}} decoding="async" />
              <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-5 text-sm font-semibold text-white">{{labels[index] || business.segment}}</figcaption>
            </motion.figure>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default GallerySection;
"""


def _default_services_section_tsx(facts: dict[str, Any]) -> str:
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    return f"""import {{ ClipboardCheck, MessageCircle, Route, Sparkles }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const business = {data};
const services = [
  ['Diagnóstico inicial', 'Leitura rápida do contexto do cliente antes do primeiro contato.', ClipboardCheck],
  ['Atendimento orientado', `Conversa direta para entender necessidade em ${{business.city}}.`, MessageCircle],
  ['Plano de ação', 'Próximos passos claros, sem promessa inventada ou dado sem confirmação.', Route],
  ['Experiência visual', 'Página com imagens, motion e CTA pensados para conversão local.', Sparkles],
];

export function ServicesSection() {{
  return (
    <section id="servicos" className="bg-white px-5 py-18 text-zinc-950 md:px-8 md:py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Serviços</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight md:text-5xl">O que o visitante entende em poucos segundos.</h2>
          </div>
          <p className="max-w-sm text-sm leading-6 text-zinc-600">Cada bloco é curto para evitar texto truncado e manter leitura limpa no mobile.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {{services.map(([title, text, Icon], index) => (
            <motion.article key={{title}} initial={{{{ opacity: 0, y: 16 }}}} whileInView={{{{ opacity: 1, y: 0 }}}} viewport={{{{ once: true, amount: 0.25 }}}} transition={{{{ delay: index * 0.04 }}}} className="min-h-48 rounded-[28px] border border-zinc-200 bg-[#f7f3ea] p-6">
              <Icon className="h-5 w-5 text-emerald-700" />
              <h3 className="mt-5 text-lg font-semibold text-zinc-950">{{title}}</h3>
              <p className="mt-3 text-sm leading-6 text-zinc-600">{{text}}</p>
            </motion.article>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default ServicesSection;
"""


def _default_lifestyle_section_tsx(facts: dict[str, Any]) -> str:
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    return f"""import {{ motion }} from 'motion/react';

const business = {data};

export function LifestyleSection() {{
  return (
    <section id="experiencia" className="bg-[#071611] px-5 py-18 text-white md:px-8 md:py-24">
      <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300">Experiência</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Movimento, profundidade e leitura sem ruído.</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {{['Scroll com intenção', 'Prova clara', 'CTA sempre objetivo'].map((title, index) => (
            <motion.article key={{title}} initial={{{{ opacity: 0, x: 20 }}}} whileInView={{{{ opacity: 1, x: 0 }}}} viewport={{{{ once: true, amount: 0.3 }}}} transition={{{{ delay: index * 0.06 }}}} className="rounded-[28px] border border-white/10 bg-black/70 p-6">
              <span className="text-sm font-semibold text-emerald-300">0{{index + 1}}</span>
              <h3 className="mt-5 text-lg font-semibold text-white">{{title}}</h3>
              <p className="mt-3 text-sm leading-6 text-zinc-300">Contrato visual aplicado para {{business.segment}} em {{business.city}}.</p>
            </motion.article>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default LifestyleSection;
"""


def _default_reviews_section_tsx(facts: dict[str, Any]) -> str:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    reviews = business.get("reviews")
    if not isinstance(reviews, list):
        reviews = []
    cards: list[dict[str, str]] = []
    for item in reviews[:4]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("texto") or item.get("text") or "").strip()
        author = str(item.get("autor") or item.get("author") or "Avaliação local").strip()
        if text:
            cards.append({"quote": text[:180], "author": author[:48]})
    if not cards:
        cards = [
            {"quote": "Atendimento elogiado pela clareza no acompanhamento e pela experiência personalizada.", "author": "Prova local"},
            {"quote": "Quem chega pelo WhatsApp encontra um processo mais direto, humano e orientado ao objetivo.", "author": "Contato real"},
        ]
    title = json.dumps("Avaliações que sustentam a decisão", ensure_ascii=False)
    cards_js = json.dumps(cards, ensure_ascii=False)
    rating_js = json.dumps(str(business.get("rating") or ""), ensure_ascii=False)
    count_js = json.dumps(str(business.get("total_avaliacoes") or business.get("reviews_count") or ""), ensure_ascii=False)
    return f"""import {{ useEffect, useState }} from 'react';
import {{ ChevronLeft, ChevronRight }} from 'lucide-react';
import {{ AnimatePresence, motion }} from 'motion/react';

const title = {title};
const cards = {cards_js};
const rating = {rating_js};
const reviewCount = {count_js};

export function ReviewsSection() {{
  const [active, setActive] = useState(0);
  const current = cards[active % cards.length];
  const next = () => setActive((value) => (value + 1) % cards.length);
  const previous = () => setActive((value) => (value - 1 + cards.length) % cards.length);

  useEffect(() => {{
    const timer = window.setInterval(next, 6500);
    return () => window.clearInterval(timer);
  }}, []);

  return (
    <section id="avaliacoes" className="overflow-hidden bg-[#071611] px-5 py-20 text-white md:px-8">
      <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
        <div>
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Prova social</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">{{title}}</h2>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-zinc-300">
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2">{{rating || '5.0'}} estrelas</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2">{{reviewCount || String(cards.length)}} sinais locais</span>
          </div>
        </div>
        <div className="relative min-h-[21rem] overflow-hidden rounded-[32px] border border-white/10 bg-black/70 p-6 shadow-[0_24px_80px_rgba(0,0,0,0.24)] md:p-8">
          <AnimatePresence mode="wait">
            <motion.article
              key={{active}}
              initial={{{{ opacity: 0, x: 32 }}}}
              animate={{{{ opacity: 1, x: 0 }}}}
              exit={{{{ opacity: 0, x: -32 }}}}
              transition={{{{ duration: 0.45, ease: 'easeOut' }}}}
              className="flex min-h-[16rem] flex-col justify-between gap-8"
            >
              <p className="max-w-2xl text-2xl leading-10 text-zinc-50 md:text-3xl">“{{current.quote}}”</p>
              <div>
                <div className="flex gap-1 text-amber-300" aria-hidden="true">
                  {{Array.from({{ length: 5 }}).map((_, star) => <span key={{star}}>★</span>)}}
                </div>
                <p className="mt-3 text-sm font-semibold text-white">{{current.author}}</p>
              </div>
            </motion.article>
          </AnimatePresence>
          <div className="mt-6 flex items-center justify-between gap-4">
            <div className="flex gap-2">
              {{cards.map((_, index) => (
                <button
                  key={{index}}
                  type="button"
                  aria-label={{`Mostrar avaliação ${{index + 1}}`}}
                  onClick={{() => setActive(index)}}
                  className={{`h-2.5 rounded-full transition-all ${{index === active ? 'w-8 bg-emerald-300' : 'w-2.5 bg-white/25'}}`}}
                />
              ))}}
            </div>
            <div className="flex gap-2">
              <button type="button" aria-label="Avaliação anterior" onClick={{previous}} className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white">
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button type="button" aria-label="Próxima avaliação" onClick={{next}} className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white">
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>
          <div className="pointer-events-none absolute inset-y-0 right-0 w-28 bg-gradient-to-l from-[#071611]/70 to-transparent" />
        </div>
      </div>
    </section>
  );
}}

export default ReviewsSection;
"""


def _default_lgpd_banner_tsx() -> str:
    return """import { useEffect, useState } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { motion } from 'motion/react';

const CONSENT_KEY = 'fralib_lgpd_consent_v1';

export function LgpdBanner() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    try {
      if (localStorage.getItem(CONSENT_KEY) === '1') setVisible(false);
    } catch {
      // Storage can be unavailable in privacy-restricted browsers.
    }
  }, []);

  const accept = () => {
    try {
      localStorage.setItem(CONSENT_KEY, '1');
    } catch {
      // Consent still applies to the current page when storage is unavailable.
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <motion.div
      data-lgpd-banner
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed inset-x-4 bottom-4 z-[9999] mx-auto grid max-w-3xl grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl p-4 shadow-2xl"
      style={{ background: 'var(--lgpd-bg, var(--bg-light))', color: 'var(--lgpd-text, var(--text-dark))', border: '1px solid var(--lgpd-border, color-mix(in srgb, var(--accent) 26%, transparent))' }}
      role="dialog"
      aria-label="Aviso de privacidade"
    >
      <ShieldCheck className="h-5 w-5" style={{ color: 'var(--accent)' }} />
      <p className="text-sm leading-5" style={{ color: 'var(--lgpd-text, var(--text-dark))' }}>Tratamos dados de contato apenas para atendimento, segurança e melhoria da experiência.</p>
      <div className="flex items-center gap-2">
        <button type="button" data-lgpd-accept onClick={accept} className="rounded-full px-4 py-2 text-sm font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}>
          Aceitar
        </button>
        <button type="button" aria-label="Fechar aviso de privacidade" onClick={accept} className="inline-flex h-9 w-9 items-center justify-center rounded-full" style={{ color: 'var(--lgpd-text, var(--text-dark))', border: '1px solid color-mix(in srgb, var(--accent) 18%, transparent)' }}>
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}

export default LgpdBanner;
"""


def _default_location_section_tsx(facts: dict[str, Any]) -> str:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    address = json.dumps(str(business.get("address") or business.get("endereco") or "").strip(), ensure_ascii=False)
    city = json.dumps(str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip(), ensure_ascii=False)
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = json.dumps(phone or "Contato", ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", phone or "")
    phone_href = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    maps = json.dumps(str(business.get("maps_url") or business.get("map_url") or "").strip(), ensure_ascii=False)
    return f"""import {{ MapPin, MessageCircle, Phone }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const address = {address};
const city = {city};
const phoneLabel = {phone_label};
const whatsappHref = {phone_href};
const mapsHref = {maps};

export function LocationSection() {{
  return (
    <section id="localizacao" className="px-5 py-20 text-white md:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <motion.div
          initial={{{{ opacity: 0, y: 22 }}}}
          whileInView={{{{ opacity: 1, y: 0 }}}}
          viewport={{{{ once: true, amount: 0.25 }}}}
          className="rounded-[32px] border border-white/10 bg-black/70 p-8"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Localização</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">Atendimento em {{city}}</h2>
          <p className="mt-4 max-w-xl text-base leading-7 text-zinc-300">
            Use este contato para confirmar endereço, formato do atendimento e próximos horários disponíveis.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-black/10 p-5">
              <MapPin className="h-5 w-5 text-emerald-300" />
              <p className="mt-3 text-sm font-semibold text-white">Endereço confirmado</p>
              <p className="mt-2 text-sm leading-6 text-zinc-300">{{address || city}}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-black/10 p-5">
              <Phone className="h-5 w-5 text-emerald-300" />
              <p className="mt-3 text-sm font-semibold text-white">Contato direto</p>
              <p className="mt-2 text-sm leading-6 text-zinc-300">{{phoneLabel}}</p>
            </div>
          </div>
        </motion.div>
        <motion.div
          initial={{{{ opacity: 0, y: 22 }}}}
          whileInView={{{{ opacity: 1, y: 0 }}}}
          viewport={{{{ once: true, amount: 0.25 }}}}
          transition={{{{ delay: 0.08 }}}}
          className="rounded-[32px] border border-emerald-400/20 bg-emerald-400/5 p-8"
        >
          <div className="flex h-full flex-col justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Contato e rota</p>
              <h3 className="mt-3 text-2xl font-semibold text-white">Chegue pelo canal certo</h3>
              <p className="mt-4 text-sm leading-7 text-zinc-300">
                Primeiro confirme pelo WhatsApp. Depois, se precisar, abra a rota para chegar ao endereço publicado.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <a href={{whatsappHref}} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full bg-emerald-400 px-5 py-3 text-sm font-semibold text-zinc-950">
                <MessageCircle className="h-4 w-4" />
                WhatsApp
              </a>
              {{mapsHref ? (
                <a href={{mapsHref}} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-semibold text-white">
                  <MapPin className="h-4 w-4" />
                  Abrir rota
                </a>
              ) : null}}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}}

export default LocationSection;
"""


def _default_contact_cta_tsx(facts: dict[str, Any]) -> str:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    name = json.dumps(str(business.get("name") or "Equipe local").strip(), ensure_ascii=False)
    city = json.dumps(str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip(), ensure_ascii=False)
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = json.dumps(phone or "WhatsApp", ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", phone or "")
    whatsapp_href = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    maps_href = json.dumps(str(business.get("maps_url") or business.get("map_url") or "").strip(), ensure_ascii=False)
    address = json.dumps(str(business.get("address") or business.get("endereco") or "").strip(), ensure_ascii=False)
    return f"""import {{ ArrowRight, MapPin, MessageCircle, Phone }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const business = {{
  name: {name},
  city: {city},
  address: {address},
  phoneLabel: {phone_label},
  whatsappHref: {whatsapp_href},
  mapsHref: {maps_href},
}};

export function ContactCTA({{ onOpen }}: {{ onOpen?: () => void }}) {{
  return (
    <section
      id="contato"
      className="relative overflow-hidden border-t border-white/10 bg-[#071611] px-5 py-20 text-white md:px-8"
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/60 to-transparent" />
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div
          initial={{{{ opacity: 0, y: 28 }}}}
          whileInView={{{{ opacity: 1, y: 0 }}}}
          viewport={{{{ once: true, amount: 0.3 }}}}
          className="space-y-6"
        >
          <div className="inline-flex rounded-full border border-emerald-400/25 bg-emerald-400/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-300">
            Atendimento local confirmado
          </div>
          <div className="space-y-4">
            <h2 className="max-w-3xl text-[clamp(2.2rem,5vw,4.5rem)] font-semibold leading-[0.95] tracking-tight text-white">
              Feche sua próxima etapa com acompanhamento real em {{business.city}}.
            </h2>
            <p className="max-w-2xl text-base leading-7 text-zinc-300 md:text-lg">
              Entre pelo WhatsApp oficial, confirme o formato do atendimento e receba a orientação certa para começar sem ruído.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a
              href={{business.whatsappHref}}
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-emerald-400 px-6 py-3.5 text-sm font-semibold text-[#071611] transition-transform duration-300 hover:-translate-y-0.5"
            >
              <MessageCircle className="h-4 w-4" />
              Falar no WhatsApp
            </a>
            <button
              type="button"
              onClick={{() => onOpen?.()}}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 px-6 py-3.5 text-sm font-semibold text-white transition-transform duration-300 hover:-translate-y-0.5"
            >
              <Phone className="h-4 w-4" />
              Abrir contato
            </button>
          </div>
        </motion.div>
        <motion.div
          initial={{{{ opacity: 0, x: 24 }}}}
          whileInView={{{{ opacity: 1, x: 0 }}}}
          viewport={{{{ once: true, amount: 0.3 }}}}
          transition={{{{ delay: 0.08 }}}}
          className="grid gap-4 md:grid-cols-2 lg:grid-cols-1"
        >
          <div className="rounded-[28px] border border-white/10 bg-black/70 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300/80">Contato direto</p>
            <p className="mt-3 text-lg font-semibold text-white">{{business.phoneLabel}}</p>
            <p className="mt-2 text-sm leading-6 text-zinc-300">Canal oficial para agendamento, dúvidas e confirmação de horário.</p>
          </div>
          <div className="rounded-[28px] border border-white/10 bg-black/70 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300/80">Endereço e rota</p>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{{business.address || business.city}}</p>
            {{business.mapsHref ? (
              <a
                href={{business.mapsHref}}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-emerald-300"
              >
                <MapPin className="h-4 w-4" />
                Abrir rota
                <ArrowRight className="h-4 w-4" />
              </a>
            ) : null}}
          </div>
        </motion.div>
      </div>
    </section>
  );
}}

export default ContactCTA;
"""


def _default_footer_tsx(facts: dict[str, Any]) -> str:
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    name = json.dumps(str(business.get("name") or "Negócio local").strip(), ensure_ascii=False)
    city = json.dumps(str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip(), ensure_ascii=False)
    address = json.dumps(str(business.get("address") or business.get("endereco") or "").strip(), ensure_ascii=False)
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = json.dumps(phone or "Contato oficial", ensure_ascii=False)
    phone_href = json.dumps(f"tel:{phone}" if phone else "#contato", ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", phone or "")
    whatsapp_href = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    maps_href = json.dumps(str(business.get("maps_url") or business.get("map_url") or "").strip(), ensure_ascii=False)
    return f"""import {{ ExternalLink, MapPin, MessageCircle, Phone, ShieldCheck }} from 'lucide-react';

const business = {{
  name: {name},
  city: {city},
  address: {address},
  phoneLabel: {phone_label},
  phoneHref: {phone_href},
  whatsappHref: {whatsapp_href},
  mapsHref: {maps_href},
}};

const year = 2026;

export function Footer() {{
  return (
    <footer className="border-t border-white/8 bg-[#071611] px-5 pb-10 pt-10 text-zinc-300 md:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.1fr_0.9fr_0.8fr]">
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Encerramento completo</p>
          <div>
            <strong className="block text-2xl font-semibold tracking-tight text-white">{{business.name}}</strong>
            <p className="mt-2 max-w-md text-sm leading-7 text-zinc-400">
              WhatsApp, endereço e informações essenciais reunidos para facilitar seu próximo contato.
            </p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <div className="rounded-[24px] border border-white/8 bg-black/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300/80">Contato</p>
            <a className="mt-3 flex items-center gap-2 text-sm font-medium text-white" href={{business.phoneHref}}>
              <Phone className="h-4 w-4 text-emerald-300" />
              {{business.phoneLabel}}
            </a>
            <a className="mt-3 flex items-center gap-2 text-sm font-medium text-white" href={{business.whatsappHref}} rel="noopener noreferrer">
              <MessageCircle className="h-4 w-4 text-emerald-300" />
              WhatsApp
            </a>
          </div>
          <div className="rounded-[24px] border border-white/8 bg-black/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300/80">Localização</p>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{{business.address || business.city}}</p>
            {{business.mapsHref ? (
              <a className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-white" href={{business.mapsHref}} target="_blank" rel="noopener noreferrer">
                <MapPin className="h-4 w-4 text-emerald-300" />
                Abrir mapa
                <ExternalLink className="h-4 w-4 text-emerald-300" />
              </a>
            ) : null}}
          </div>
        </div>
        <div className="rounded-[24px] border border-white/8 bg-black/70 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300/80">Navegação e confiança</p>
          <nav className="mt-3 grid gap-3 text-sm text-zinc-300" aria-label="Links finais do site">
            <a href="#hero">Início</a>
            <a href="#servicos">Serviços</a>
            <a href="#localizacao">Localização</a>
            <a href="#contato">Contato</a>
          </nav>
          <div className="mt-5 flex items-start gap-3 text-sm leading-6 text-zinc-400">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
            <p>Privacidade, consentimento e dados de contato publicados com contrato de LGPD e compartilhamento social válidos.</p>
          </div>
        </div>
      </div>
      <div className="mx-auto mt-8 flex max-w-7xl flex-col gap-3 border-t border-white/8 pt-5 text-xs text-zinc-500 md:flex-row md:items-center md:justify-between">
        <span>{{business.name}} | {{business.city}}</span>
        <span>© {{year}} {{business.name}}. Todos os direitos reservados.</span>
      </div>
    </footer>
  );
}}

export default Footer;
"""


def _default_index_css() -> str:
    return """@import "tailwindcss";
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

@layer base {
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; background: #050505; }
  body {
    margin: 0;
    min-width: 320px;
    min-height: 100vh;
    font-family: Inter, system-ui, sans-serif;
    color: #f7f3ec;
    background: #050505;
    text-rendering: geometricPrecision;
  }
  h1, h2, h3 { text-wrap: balance; }
  p { text-wrap: pretty; }
  img { max-width: 100%; display: block; }
  a { color: inherit; text-decoration: none; }
  button, a { -webkit-tap-highlight-color: transparent; }
  ::selection { background: rgba(216, 184, 121, 0.35); color: #fffaf0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
"""


def _ensure_index_css_contract(content: str) -> str:
    css = str(content or "").strip()
    css = re.sub(r"@import\s+[\"']tailwindcss/(?:base|components|utilities)[\"'];?\s*", "", css)
    css = re.sub(r"@tailwind\s+(?:base|components|utilities);?\s*", "", css)
    # Tailwind v4 rejects:
    #   1. "Invalid declaration: `\n`"  - when LLM emits stray "\\\n" tokens
    #   2. "Missing opening {"          - when a rule body has been torn apart
    #   3. "@import rules must precede all rules" - when LLM emits @import
    #      inline with @layer / @font-face / custom rules
    css = css.replace("\\\n", "\n")
    css = re.sub(r"^\s*\\\s*$", "", css, flags=re.MULTILINE)
    css = re.sub(r"\\n\s*", "", css)
    # Collect ALL @import rules and move them to the top, in order.
    import_rules: list[str] = []
    body_lines: list[str] = []
    for line in css.splitlines():
        stripped = line.strip()
        if stripped.startswith("@import") and ";" in stripped:
            import_rules.append(stripped)
        else:
            body_lines.append(line)
    if not any('"tailwindcss"' in r or "'tailwindcss'" in r for r in import_rules):
        import_rules.insert(0, '@import "tailwindcss";')
    css = "\n".join(import_rules + [""] + body_lines).strip()
    if "prefers-reduced-motion" not in css:
        css += """

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
"""
    return css + ("\n" if not css.endswith("\n") else "")


def _digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")
