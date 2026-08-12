"""
Builder Agent — OpenUI HTTP Client.

Receives a DesignerPRD and calls the OpenUI service (port 7878 - wandb/openui)
to generate the complete HTML site via single-shot LLM generation.
"""
import os
import json
import time
import requests

try:
    from loguru import logger as _builder_logger
except ImportError:
    _builder_logger = None

OPENUI_URL = os.environ.get("OPENUI_URL") or os.environ.get("OPENUI_SERVICE_URL", "http://localhost:7878")
GENERATE_ENDPOINT = f"{OPENUI_URL}/generate"
OPENUI_CHECK_URL = f"{OPENUI_URL}/generate"

_BLOCOS_HTML = [
    ["hero", "sobre"],
    ["servicos", "depoimentos"],
    ["faq", "localizacao"],
    ["contato"],
]

class BuildResult:
    """Result of a site build."""
    def __init__(self, html: str, model: str = "", success: bool = True, error: str = ""):
        self.html = html
        self.model = model
        self.success = success
        self.error = error


def _wait_for_openui(max_wait: int = 30) -> bool:
    """Wait for OpenUI service to be ready.

    OpenUI wandb doesn't have a health endpoint that returns 200.
    Instead, we try a POST to /generate - if it returns any non-5xx response,
    the service is available (422 means endpoint exists, just missing body).
    """
    for _ in range(max_wait):
        try:
            # POST with empty body - 422 means "service is up, but missing input"
            # 200 would mean health check passed
            # Any non-5xx means service is reachable
            r = requests.post(OPENUI_CHECK_URL, json={"prompt": "test"}, timeout=2)
            if r.status_code < 500:
                return True
        except Exception as e:
            print(f"[builder] OpenUI check tentativa {_ + 1} falhou: {e}")
        time.sleep(1)
    return False


def _prd_to_spec(prd) -> dict:
    """Convert DesignerPRD to JSON spec for OpenUI service."""
    sections = []
    for s in prd.sections:
        sections.append({
            "name": s.name,
            "title": getattr(s, "title", s.name),
            "content": getattr(s, "content", getattr(s, "body", "")),
        })

    color_palette = {}
    if hasattr(prd, "color_palette") and prd.color_palette:
        cp = prd.color_palette
        if hasattr(cp, "model_dump"):
            color_palette = cp.model_dump()
        elif hasattr(cp, "dict"):
            color_palette = cp.dict()
        else:
            color_palette = {k: v for k, v in vars(cp).items() if not k.startswith("_")}

    animations = []
    if hasattr(prd, "animations") and prd.animations:
        for anim in prd.animations:
            if hasattr(anim, "model_dump"):
                animations.append(anim.model_dump())
            elif hasattr(anim, "dict"):
                animations.append(anim.dict())
            else:
                animations.append({k: v for k, v in vars(anim).items() if not k.startswith("_")})

    # Build design_tokens from available PRD fields
    archetype_slug = getattr(prd, "design_system_slug", None) or "editorial-asymmetric"
    design_tokens = {
        "archetype": archetype_slug,
        "palette": color_palette,
        "typography": getattr(prd, "typography", {}),
        "radius": "12px",
    }

    # Build layout_dna from layout_type
    layout_type = getattr(prd, "layout_type", None) or "asymmetric-magazine"
    layout_dna = {
        "layout_family": layout_type,
        "section_count_range": [7, 12],
    }

    # Build design_system from archetype
    design_system = {
        "archetype_briefing": _archetype_briefing(archetype_slug),
    }

    # Build hero from first section
    hero = {}
    if sections:
        hero = {
            "headline": prd.business_name,
            "subheadline": getattr(prd, "value_props", [""])[0] if getattr(prd, "value_props", []) else "",
            "cta_text": "Fale Conosco",
        }

    # Build ctas from value_props
    ctas = []
    for vp in (getattr(prd, "value_props", []) or [])[:3]:
        ctas.append({"text": vp[:60], "href": "#contato"})

    # Build motion_directives from animations
    motion_directives = {
        "parallax": True,
        "scroll_reveal": True,
        "hover_effects": True,
    }

    # Build builder_directive
    builder_directive = f"Landing page para {prd.business_name} ({getattr(prd, 'segmento', '')}) em {getattr(prd, 'cidade', '')}. "
    builder_directive += getattr(prd, "instrucao_criativa_para_dev", "") or ""

    spec = {
        "business_name": prd.business_name,
        "cidade": getattr(prd, "cidade", ""),
        "segmento": getattr(prd, "segmento", ""),
        "sections": sections,
        "hero": hero,
        "ctas": ctas,
        "faqs": getattr(prd, "faq_questions", []) or [],
        "paleta": color_palette,
        "seo_keywords": getattr(prd, "seo_keywords", []) or [],
        "motion_directives": motion_directives,
        "color_palette": color_palette,
        "typography": getattr(prd, "typography", {}),
        "animations": animations,
        "design_tokens": design_tokens,
        "layout_dna": layout_dna,
        "design_system": design_system,
        "builder_directive": builder_directive,
        "reviews_count": getattr(prd, "reviews_count", 0),
        "reviews_rating": getattr(prd, "reviews_rating", 0.0),
        "reviews_list": getattr(prd, "reviews_list", []),
        "address": getattr(prd, "address", ""),
        "phone": getattr(prd, "phone", ""),
        "hours": getattr(prd, "hours", None) or {},
        "photos": getattr(prd, "photos", []),
        "videos": getattr(prd, "videos", []),
        "value_props": getattr(prd, "value_props", []) or [],
        "geo": getattr(prd, "geo", None),
        "dark_mode": getattr(prd, "dark_mode", False),
        "google_maps_embed": getattr(prd, "google_maps_embed", ""),
        "components_21dev": getattr(prd, "components_21dev", []),
        "competitor_analysis": getattr(prd, "competitor_analysis", ""),
        "anti_patterns": getattr(prd, "anti_patterns", []),
        "schema_org_types": getattr(prd, "schema_org_types", []),
        "layout_type": getattr(prd, "layout_type", ""),
        "instrucao_criativa_para_dev": getattr(prd, "instrucao_criativa_para_dev", ""),
        "site_build_plan": getattr(prd, "site_build_plan", {}) or {},
        "requirements_contract": getattr(prd, "requirements_contract", {}) or {},
        "visual_contract": getattr(prd, "visual_contract", {}) or {},
        "visual_dna": getattr(prd, "visual_dna", {}) or {},
        "layout_blueprint": getattr(prd, "layout_blueprint", []) or [],
        "design_reference_pack": getattr(prd, "design_reference_pack", {}) or {},
    }
    # Instrumentação: logar chaves do spec enviado ao OpenUI
    if _builder_logger:
        _builder_logger.info(
            "PRD_BUILDER: spec_keys=[{}]",
            ", ".join(sorted(spec.keys())),
        )
    return spec


def _archetype_briefing(archetype: str) -> str:
    """Return archetype briefing text for OpenUI system prompt."""
    briefings = {
        "industrial-bold": "BOLD. Industrial aesthetic. Massive typography, dark backgrounds, sharp edges. Think brutalist luxury.",
        "dark-futurist": "Futuristic dark mode. Neon accents, glass morphism, smooth gradients. Premium tech feel.",
        "editorial-asymmetric": "Editorial asymmetric layout. Magazine-style grid, bold typography, generous whitespace. Premium content-first.",
        "apple-minimalist": "Minimalist. Clean white space, subtle shadows, restrained palette. Apple-inspired simplicity.",
        "organic-warm": "Warm organic. Earth tones, rounded shapes, natural textures. Approachable and trustworthy.",
        "corporate-trust": "Corporate trust. Professional blue, structured grid, clear hierarchy. Enterprise credibility.",
    }
    return briefings.get(archetype, briefings["editorial-asymmetric"])


def _split_spec_blocks(spec: dict) -> list:
    """Split spec into blocks of sections for partial HTML generation."""
    sections = spec.get("sections", [])
    section_map = {s["name"].lower(): s for s in sections}
    blocos = []
    for grupo in _BLOCOS_HTML:
        relevantes = [section_map[s] for s in grupo if s in section_map]
        if relevantes:
            block_spec = dict(spec)
            block_spec["sections"] = relevantes
            block_spec["_bloco_labels"] = grupo
            blocos.append(block_spec)
    return blocos


def _concat_html(partials: list) -> str:
    """Concatenate partial HTML documents/fragments into one valid document."""
    import re
    if not partials:
        return ""

    def _extract_head(html: str) -> str:
        match = re.search(r"<head[^>]*>(.*?)</head>", html, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return (
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "<title>FraLib Site</title>"
        )

    def _extract_body(html: str) -> str:
        match = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.DOTALL | re.IGNORECASE)
        if match:
            fragment = match.group(1)
        else:
            fragment = html
        fragment = re.sub(r"<!DOCTYPE[^>]*>\s*", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"<head[^>]*>.*?</head>", "", fragment, flags=re.DOTALL | re.IGNORECASE)
        fragment = re.sub(r"</?title[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"</?html[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"</?body[^>]*>", "", fragment, flags=re.IGNORECASE)
        return fragment.strip()

    head = _extract_head(partials[0])
    body = "\n".join(_extract_body(partial) for partial in partials if partial).strip()
    return f"<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n"


def _render_block(block_spec: dict, design_tokens: dict) -> tuple[str, str]:
    """Render one block via OpenUI with 6 retries. Returns (html, model) tuple or ("", "") on failure."""
    max_retries = 6
    retry_delays = [60, 120, 180, 300, 300, 600]
    labels = block_spec.get("_bloco_labels", [])
    label_str = ", ".join(labels)
    block_spec = dict(block_spec)
    block_spec["_render_hint"] = "body_only"

    last_error = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                GENERATE_ENDPOINT,
                json={"designerPRD": block_spec},
                headers={"Content-Type": "application/json"},
                timeout=600,
            )
            if resp.status_code == 200:
                data = resp.json()
                html = data.get("html", "")
                model = data.get("model", "")
                if html and len(html) > 200:
                    print(f"[builder] Bloco [{label_str}] OK ({len(html)} chars)")
                    return html, model
                last_error = f"HTML too short: {len(html)} chars"
            elif resp.status_code in (529, 503) or (
                resp.status_code == 500
                and any(marker in resp.text.lower() for marker in ("529", "overloaded", "sobrecarregado", "503", "provider_error"))
            ):
                last_error = f"OpenUI overloaded attempt {attempt + 1}: HTTP {resp.status_code}"
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
            else:
                last_error = f"OpenUI HTTP {resp.status_code}: {resp.text[:200]}"
                return "", ""
        except requests.exceptions.Timeout:
            last_error = f"OpenUI timeout (600s) attempt {attempt + 1}"
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            return "", ""
        except Exception as e:
            last_error = f"OpenUI error: {str(e)}"
            return "", ""

    print(f"[builder] Bloco [{label_str}] falhou apos {max_retries} tentativas: {last_error}")
    return "", ""


def render_site(prd, usar_llm: bool = True) -> BuildResult:
    """
    Generate HTML site from DesignerPRD via OpenUI block-by-block generation.

    Splits the spec into 4 partial blocks (hero+sobre, servicos+depoimentos,
    faq+localizacao, contato), renders each via separate OpenUI call, then
    concatenates into one final HTML document.

    Args:
        prd: DesignerPRD object with all design specifications.
        usar_llm: If True, use LLM generation. If False, use template fallback.

    Returns:
        BuildResult with html, model, and success status.
    """
    if not usar_llm:
        return BuildResult(html="", model="", success=False, error="Template fallback not implemented")

    # Ensure OpenUI is ready
    if not _wait_for_openui(max_wait=10):
        return BuildResult(html="", model="", success=False, error="OpenUI service not available at " + OPENUI_URL)

    # Convert PRD to spec
    spec = _prd_to_spec(prd)

    # Split into 4 partial blocks and render each separately
    blocos = _split_spec_blocks(spec)
    if not blocos:
        return BuildResult(html="", model="", success=False, error="No sections to render")

    partials = []
    models_used = []

    for bloco in blocos:
        labels = bloco.get("_bloco_labels", [])
        label_str = ", ".join(labels)
        html, model = _render_block(bloco, spec)
        if not html:
            return BuildResult(html="", model="", success=False,
                               error=f"Falha ao gerar bloco [{label_str}]")
        partials.append(html)
        if model:
            models_used.append(model)
        # Registrar tracking por bloco (OpenUI nao retorna usage, estimar)
        try:
            from backend.agents.llm_direct import _registrar_uso_completo
            _registrar_uso_completo(
                model_id=model or "openui-unknown",
                input_tokens=0,
                output_tokens=len(html) // 4,
                agent_name=f"builder_bloco_{label_str.replace(', ', '_')}",
                provider="openui",
            )
        except Exception as e:
            print(f"[builder] tracking falhou bloco [{label_str}]: {e}")

    # Concatenate partial HTMLs into final document
    final_html = _concat_html(partials)
    final_model = models_used[0] if models_used else ""

    return BuildResult(html=final_html, model=final_model, success=True)
