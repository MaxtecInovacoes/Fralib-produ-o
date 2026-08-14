"""
Builder Agent — OpenUI HTTP Client.

Receives a DesignerPRD and calls the OpenUI service (port 7878 - wandb/openui)
to generate the complete HTML site via single-shot LLM generation.
"""
import os
import json
import time
import re
import requests
from urllib.parse import quote_plus
from backend.agents.design_guidelines import TAILWIND_FIRST_RULES, ANIMATION_PRINCIPLES

try:
    from loguru import logger as _builder_logger
except ImportError:
    _builder_logger = None

try:
    from backend.agents.artifact_store import write_html_artifact
except Exception:
    write_html_artifact = None

OPENUI_URL = os.environ.get("OPENUI_URL") or os.environ.get("OPENUI_SERVICE_URL", "http://localhost:7878")
GENERATE_ENDPOINT = f"{OPENUI_URL}/generate"
OPENUI_CHECK_URL = f"{OPENUI_URL}/generate"

_BLOCOS_HTML = [
    ["hero"],
    ["interesse", "sobre", "trust_bar"],
    ["servicos", "desejo", "depoimentos", "prova-social"],
    ["seo-geo", "localizacao", "faq"],
    ["acao", "contato", "lgpd", "footer"],
]

_SECTION_BLOCKS = [
    ["hero"],
    ["interesse"],
    ["sobre"],
    ["servicos"],
    ["desejo"],
    ["depoimentos"],
    ["seo-geo"],
    ["faq"],
    ["localizacao"],
    ["acao"],
    ["contato"],
    ["lgpd"],
    ["footer"],
]

class BuildResult:
    """Result of a site build."""
    def __init__(self, html: str, model: str = "", success: bool = True, error: str = ""):
        self.html = html
        self.model = model
        self.success = success
        self.error = error


_VISIBLE_TAG_RE = re.compile(
    r"<(?:main|section|header|nav|article|aside|footer|div|h1|h2|h3|p|a|button|form|img|ul|ol|li)\b",
    flags=re.IGNORECASE,
)


def _strip_non_content_blocks(html: str) -> str:
    html = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", html or "")
    html = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<noscript\b[^>]*>.*?</noscript>", " ", html)
    return html


def _looks_like_valid_body_fragment(html: str) -> tuple[bool, str]:
    """Reject style/script-heavy fragments before they poison the final page."""
    if not html or len(html.strip()) < 200:
        return False, "fragmento muito curto"

    style_opens = len(re.findall(r"(?i)<style\b", html))
    style_closes = len(re.findall(r"(?i)</style>", html))
    if style_opens != style_closes:
        return False, "tags <style> desbalanceadas"

    script_opens = len(re.findall(r"(?i)<script\b", html))
    script_closes = len(re.findall(r"(?i)</script>", html))
    if script_opens != script_closes:
        return False, "tags <script> desbalanceadas"

    content_only = _strip_non_content_blocks(html)
    visible_tags = len(_VISIBLE_TAG_RE.findall(content_only))
    visible_text = re.sub(r"(?is)<[^>]+>", " ", content_only)
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    lower = content_only.lower()
    main_count = lower.count("<main")
    section_count = lower.count("<section")
    h1_count = lower.count("<h1")

    if visible_tags == 0:
        return False, "sem tags estruturais visiveis"
    if len(visible_text) < 80:
        return False, "texto visivel insuficiente"
    if main_count == 0:
        return False, "sem tag <main>"
    if section_count < 3:
        return False, f"poucas secoes ({section_count})"
    if h1_count == 0:
        return False, "sem tag <h1>"
    if "<script" in lower or "<style" in lower:
        return False, "bloco ainda contem style/script apos limpeza"

    return True, ""


def _looks_like_valid_section_fragment(html: str) -> tuple[bool, str]:
    """Aceita fragmentos de seção e também documentos completos com corpo útil."""
    if not html or len(html.strip()) < 120:
        return False, "fragmento de secao muito curto"

    body_only = _extract_body_only(html)
    if not body_only or len(body_only.strip()) < 120:
        return False, "corpo do fragmento muito curto"

    style_opens = len(re.findall(r"(?i)<style\b", body_only))
    style_closes = len(re.findall(r"(?i)</style>", body_only))
    if style_opens != style_closes:
        return False, "tags <style> desbalanceadas"

    script_opens = len(re.findall(r"(?i)<script\b", body_only))
    script_closes = len(re.findall(r"(?i)</script>", body_only))
    if script_opens != script_closes:
        return False, "tags <script> desbalanceadas"

    content_only = _strip_non_content_blocks(body_only)
    visible_tags = len(_VISIBLE_TAG_RE.findall(content_only))
    visible_text = re.sub(r"(?is)<[^>]+>", " ", content_only)
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    lower = content_only.lower()
    section_count = lower.count("<section")
    main_count = lower.count("<main")
    header_count = lower.count("<header")
    article_count = lower.count("<article")
    div_count = lower.count("<div")
    h1_count = lower.count("<h1")

    if visible_tags == 0:
        return False, "sem tags estruturais visiveis"
    if len(visible_text) < 60:
        return False, "texto visivel insuficiente"
    if section_count == 0 and main_count == 0 and header_count == 0 and article_count == 0 and div_count == 0:
        return False, "sem bloco estrutural renderizavel"
    if h1_count == 0 and section_count == 0 and main_count == 0:
        return False, "fragmento sem heading principal"
    if "<script" in lower or "<style" in lower:
        return False, "fragmento ainda contem style/script apos limpeza"

    return True, ""


def _first_non_empty(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _coerce_section_content(section) -> str:
    if not section:
        return ""
    copy_data = getattr(section, "copy_data", None) or {}
    if not isinstance(copy_data, dict):
        copy_data = {}

    pieces: list[str] = []
    title = _first_non_empty(
        getattr(section, "title", None),
        getattr(section, "h1", None),
        getattr(section, "h2", None),
        getattr(section, "headline", None),
        copy_data.get("h1"),
        copy_data.get("h2"),
        copy_data.get("headline"),
        copy_data.get("title"),
    )
    if title:
        pieces.append(title)

    subtitle = _first_non_empty(
        getattr(section, "subheadline", None),
        copy_data.get("subtitle"),
        copy_data.get("subheadline"),
        copy_data.get("eyebrow"),
    )
    if subtitle:
        pieces.append(subtitle)

    body = _first_non_empty(
        getattr(section, "content", None),
        copy_data.get("body"),
        copy_data.get("description"),
        copy_data.get("text"),
    )
    if body:
        pieces.append(body)

    items = copy_data.get("items")
    if isinstance(items, list) and items:
        pieces.extend(str(item).strip() for item in items if str(item).strip())

    for key in ("cta_primary", "cta_secondary", "cta", "cta_text"):
        value = copy_data.get(key)
        if isinstance(value, str) and value.strip():
            pieces.append(value.strip())

    return "\n".join(piece for piece in pieces if piece)


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
        section_payload = {
            "name": getattr(s, "name", "") or getattr(s, "id", ""),
            "title": _first_non_empty(
                getattr(s, "title", None),
                getattr(s, "h1", None),
                getattr(s, "h2", None),
                getattr(s, "headline", None),
                (getattr(s, "copy_data", None) or {}).get("h1") if isinstance(getattr(s, "copy_data", None), dict) else None,
                (getattr(s, "copy_data", None) or {}).get("h2") if isinstance(getattr(s, "copy_data", None), dict) else None,
            ) or (getattr(s, "name", "") or "section"),
            "content": _coerce_section_content(s),
            "layout_type": getattr(s, "layout_type", None),
            "components": getattr(s, "components", None) or [],
            "copy_data": getattr(s, "copy_data", None) or {},
            "items": getattr(s, "items", None) or [],
            "cta": getattr(s, "cta", None),
            "objective": getattr(s, "objective", None),
            "media_role": getattr(s, "media_role", None),
            "schema_org": getattr(s, "schema_org", None),
        }
        sections.append(section_payload)

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
        hero_section = sections[0]
        hero_copy = hero_section.get("copy_data") if isinstance(hero_section.get("copy_data"), dict) else {}
        hero = {
            "headline": _first_non_empty(
                prd.business_name,
                hero_copy.get("h1") if isinstance(hero_copy, dict) else "",
                hero_section.get("title"),
            ),
            "subheadline": _first_non_empty(
                hero_copy.get("subtitle") if isinstance(hero_copy, dict) else "",
                hero_copy.get("body") if isinstance(hero_copy, dict) else "",
                getattr(prd, "value_props", [""])[0] if getattr(prd, "value_props", []) else "",
            ),
            "cta_text": _first_non_empty(
                hero_copy.get("cta_primary") if isinstance(hero_copy, dict) else "",
                hero_copy.get("cta") if isinstance(hero_copy, dict) else "",
                "Fale Conosco",
            ),
        }

    # Build ctas from value_props
    ctas = []
    for section in sections:
        copy_data = section.get("copy_data") if isinstance(section.get("copy_data"), dict) else {}
        for key in ("cta_primary", "cta_secondary"):
            value = copy_data.get(key)
            if isinstance(value, str) and value.strip():
                ctas.append({"text": value.strip()[:60], "href": "#contato"})
    if not ctas:
        for vp in (getattr(prd, "value_props", []) or [])[:3]:
            ctas.append({"text": str(vp)[:60], "href": "#contato"})

    creative_direction = getattr(prd, "creative_direction", {}) or {}
    variation_blueprint = getattr(prd, "variation_blueprint", {}) or {}
    media_plan = getattr(prd, "media_plan", []) or []
    photos = getattr(prd, "photos", None) or []
    geo = getattr(prd, "geo", None)
    if isinstance(geo, dict) and not any(geo.values()):
        geo = None

    # Build motion_directives from creative direction and animations
    motion_soft = (creative_direction.get("soft_constraints") or {}).get("motion", {}) if isinstance(creative_direction, dict) else {}
    motion_directives = {
        "profile": motion_soft or {},
        "animations": animations,
        "parallax": bool(motion_soft.get("usa_parallax", True)) if isinstance(motion_soft, dict) else True,
        "scroll_reveal": str((motion_soft or {}).get("efeito_principal", "")).lower() not in ("none", "sem motion"),
        "hover_effects": True,
    }

    # Build builder_directive
    builder_directive = f"Landing page para {prd.business_name} ({getattr(prd, 'segmento', '')}) em {getattr(prd, 'cidade', '')}. "
    builder_directive += getattr(prd, "instrucao_criativa_para_dev", "") or ""
    builder_directive += (
        "\n\nDIRETRIZES OBRIGATÓRIAS DE HTML/CSS:\n"
        f"{TAILWIND_FIRST_RULES.strip()}\n\n"
        "REGRAS DE ESTRUTURA:\n"
        "- Retorne HTML completo e válido.\n"
        "- Use apenas 1 <main> raiz no documento.\n"
        "- Use apenas 1 <h1> principal no hero.\n"
        "- Seções subsequentes devem usar <section> e headings <h2>/<h3>.\n"
        "- Não crie overlays absolutos sem wrapper relativo.\n\n"
        "REGRAS DE ANIMAÇÃO:\n"
        f"{ANIMATION_PRINCIPLES.strip()}\n"
    )

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
        "photos": photos,
        "media_plan": media_plan,
        "videos": getattr(prd, "videos", []),
        "value_props": getattr(prd, "value_props", []) or [],
        "geo": geo,
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
        "niche_brief": getattr(prd, "niche_brief", {}) or {},
        "creative_direction": creative_direction,
        "variation_blueprint": variation_blueprint,
    }
    spec["openui_payload"] = {
        "business_context": {
            "business_name": spec["business_name"],
            "cidade": spec["cidade"],
            "segmento": spec["segmento"],
            "address": spec["address"],
            "phone": spec["phone"],
            "reviews_rating": spec["reviews_rating"],
            "reviews_count": spec["reviews_count"],
        },
        "creative_direction": creative_direction,
        "visual_dna": spec["visual_dna"],
        "variation_blueprint": variation_blueprint,
        "site_plan": spec["site_build_plan"],
        "media_plan": media_plan,
        "content": {
            "sections": sections,
            "faqs": spec["faqs"],
            "seo_keywords": spec["seo_keywords"],
            "reviews_list": spec["reviews_list"],
            "value_props": spec["value_props"],
        },
        "technical_requirements": {
            "html": "static Tailwind HTML",
            "hard_constraints": (creative_direction or {}).get("hard_constraints", {}),
            "anti_patterns": spec["anti_patterns"],
            "narrative_framework": (variation_blueprint or {}).get("narrative_framework", "AIDA"),
            "required_sections": (variation_blueprint or {}).get(
                "required_sections",
                ["hero", "interesse", "desejo", "acao", "faq", "lgpd", "footer"],
            ),
        },
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


def _extract_response_html(payload: dict) -> str:
    """Normalize common OpenUI response formats to a single HTML string."""
    if not isinstance(payload, dict):
        return ""
    html = (payload.get("html") or "").strip()
    if html:
        return html
    for key in ("body_html", "body", "content", "markup"):
        value = (payload.get(key) or "").strip()
        if value:
            return value
    return ""


def _extract_body_only(html: str) -> str:
    match = re.search(r"<body[^>]*>(.*?)</body>", html or "", flags=re.DOTALL | re.IGNORECASE)
    fragment = match.group(1) if match else (html or "")
    fragment = re.sub(r"(?is)<!DOCTYPE[^>]*>", "", fragment)
    fragment = re.sub(r"(?is)</?html[^>]*>", "", fragment)
    fragment = re.sub(r"(?is)</?head\b[^>]*>.*?(?=(</body>|$))", "", fragment)
    fragment = re.sub(r"(?is)</?body[^>]*>", "", fragment)
    return fragment.strip()


def _concat_html(partials: list) -> str:
    """Concatenate partial HTML documents/fragments into one valid document."""
    if not partials:
        return ""

    def _strip_document_scaffold(fragment: str) -> str:
        fragment = re.sub(r"<!DOCTYPE[^>]*>\s*", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"<head\b[^>]*>.*?</head>", "", fragment, flags=re.DOTALL | re.IGNORECASE)
        fragment = re.sub(r"<title[^>]*>.*?</title>", "", fragment, flags=re.DOTALL | re.IGNORECASE)
        fragment = re.sub(r"<meta\b[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"<link\b[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"</?head\b[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"</?title[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"</?html[^>]*>", "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"</?body[^>]*>", "", fragment, flags=re.IGNORECASE)
        return fragment.strip()

    def _extract_head(html: str) -> str:
        match = re.search(r"<head\b[^>]*>(.*?)</head>", html, flags=re.DOTALL | re.IGNORECASE)
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
        fragment = _strip_document_scaffold(fragment)
        fragment = re.sub(r"(?is)<style\b[^>]*>.*?</style>", "", fragment)
        fragment = re.sub(r"(?is)<script\b[^>]*>.*?</script>", "", fragment)
        return fragment.strip()

    head = _extract_head(partials[0])
    body = "\n".join(_extract_body(partial) for partial in partials if partial).strip()
    return f"<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n"


def _inject_sections_into_shell(shell_html: str, section_fragments: list[str]) -> str:
    if not shell_html:
        return ""
    shell_html = shell_html.strip()
    body_content = "\n".join(fragment.strip() for fragment in section_fragments if fragment and fragment.strip()).strip()
    if not body_content:
        return shell_html
    if "<main" in shell_html.lower():
        return re.sub(
            r"(?is)(<main\b[^>]*>)(.*?)(</main>)",
            lambda m: f"{m.group(1)}\n{body_content}\n{m.group(3)}",
            shell_html,
            count=1,
        )
    if "</body>" in shell_html.lower():
        return re.sub(r"(?is)</body>", f"{body_content}\n</body>", shell_html, count=1)
    return shell_html + "\n" + body_content


def _google_fonts_href(typography: dict) -> str:
    heading = _normalize_web_font_family(str((typography or {}).get("heading") or "Inter").strip(), "Inter")
    body = _normalize_web_font_family(str((typography or {}).get("body") or "Inter").strip(), "Inter")
    families: list[str] = []
    for family in (heading, body):
        if not family or family.lower() in {"system-ui", "sans-serif", "serif", "monospace"}:
            continue
        encoded = quote_plus(family)
        if encoded.lower() == "inter":
            encoded = "Inter:wght@400;500;600;700;800;900"
        families.append(f"family={encoded}")
    if not families:
        families.append("family=Inter:wght@400;500;600;700;800;900")
    return "https://fonts.googleapis.com/css2?" + "&".join(dict.fromkeys(families)) + "&display=swap"


_FONT_FAMILY_ALIASES = {
    "ubermove": "Archivo Black",
    "ubermovetext": "Inter",
    "uber move": "Archivo Black",
    "uber move text": "Inter",
    "nouvelr": "Oswald",
}


def _normalize_web_font_family(family: str, fallback: str) -> str:
    raw = str(family or "").strip()
    if not raw:
        return fallback
    normalized = re.sub(r"[^a-z0-9]+", "", raw.lower())
    return _FONT_FAMILY_ALIASES.get(normalized, raw)


def _ensure_shell_fonts(html: str, spec: dict) -> str:
    if not html:
        return html
    href = _google_fonts_href(spec.get("typography") or {})
    font_links = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="{href}" rel="stylesheet">'
    )
    cleaned = re.sub(
        r'(?is)<link\b[^>]*href=["\']https://fonts\.googleapis\.com/[^"\']+["\'][^>]*>\s*',
        "",
        html,
    )
    return re.sub(r"(?is)</head>", font_links + "\n</head>", cleaned, count=1)


def _render_block(block_spec: dict, design_tokens: dict) -> tuple[str, str]:
    """Render one block via OpenUI with 6 retries. Returns (html, model) tuple or ("", "") on failure."""
    max_retries = 6
    retry_delays = [60, 120, 180, 300, 300, 600]
    labels = block_spec.get("_bloco_labels", [])
    label_str = ", ".join(labels)
    block_spec = dict(block_spec)
    render_hint = block_spec.get("_render_hint") or "body_only"
    block_spec["_render_hint"] = render_hint

    last_error = ""
    for attempt in range(max_retries):
        try:
            if last_error:
                block_spec["_repair_feedback"] = (
                    f"Tentativa anterior inválida para [{label_str}]: {last_error}. "
                    "Regere somente a seção solicitada, começando com <section e terminando com </section>, "
                    "com heading e texto visível suficientes."
                )
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
                if render_hint == "section_fragment":
                    html = _extract_body_only(html)
                    valid_html = len(html.strip()) >= 200 and "<section" in html.lower()
                    reason = "" if valid_html else "resposta 200 sem section utilizavel"
                else:
                    valid_html, reason = _looks_like_valid_body_fragment(html)
                if (
                    not valid_html
                    and render_hint == "section_fragment"
                    and len(html or "") >= 1200
                ):
                    fallback_body = _extract_body_only(html)
                    fallback_lower = fallback_body.lower()
                    if (
                        len(fallback_body.strip()) >= 400
                        and any(tag in fallback_lower for tag in ("<section", "<div", "<article", "<main"))
                        and any(tag in fallback_lower for tag in ("<h1", "<h2", "<h3", "<p", "<a", "<button"))
                    ):
                        valid_html = True
                        reason = ""
                if valid_html:
                    try:
                        if write_html_artifact:
                            labels_slug = "-".join(labels) if labels else render_hint
                            write_html_artifact(
                                run_id=str(block_spec.get("_run_id") or "no-run"),
                                lead_id=str(block_spec.get("_lead_id") or "no-lead"),
                                lead_name=str(block_spec.get("_lead_name") or ""),
                                filename=f"02-openui-{render_hint}-{labels_slug}.html",
                                html=html,
                                metadata={
                                    "step": "openui_block",
                                    "render_hint": render_hint,
                                    "labels": labels,
                                    "model": model,
                                },
                            )
                    except Exception as exc:
                        print(f"[builder] artifact openui bloco falhou: {exc}")
                    print(f"[builder] Bloco [{label_str}] OK ({len(html)} chars)")
                    return html, model
                last_error = f"HTML invalido: {reason} ({len(html)} chars)"
                print(
                    f"[builder] Bloco [{label_str}] rejeitado "
                    f"render_hint={render_hint} tentativa={attempt + 1}/{max_retries}: {last_error}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
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


def _render_shell_document(spec: dict) -> tuple[str, str, str]:
    request_spec = dict(spec)
    request_spec["_render_hint"] = "shell_document"
    try:
        resp = requests.post(
            GENERATE_ENDPOINT,
            json={"designerPRD": request_spec},
            headers={"Content-Type": "application/json"},
            timeout=600,
        )
        if resp.status_code != 200:
            return "", "", f"OpenUI HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        html = _extract_response_html(data)
        if not html:
            return "", "", "shell vazio"
        html = _ensure_shell_fonts(html, spec)
        lower = html.lower()
        if "<html" not in lower or "<body" not in lower or "<main" not in lower:
            return "", data.get("model", ""), "shell sem html/body/main"
        try:
            if write_html_artifact:
                write_html_artifact(
                    run_id=str(spec.get("_run_id") or "no-run"),
                    lead_id=str(spec.get("_lead_id") or "no-lead"),
                    lead_name=str(spec.get("_lead_name") or ""),
                    filename="02-openui-shell_document.html",
                    html=html,
                    metadata={
                        "step": "openui_shell",
                        "render_hint": "shell_document",
                        "model": data.get("model", ""),
                    },
                )
        except Exception as exc:
            print(f"[builder] artifact openui shell falhou: {exc}")
        return html, data.get("model", ""), ""
    except Exception as exc:
        return "", "", f"shell error: {exc}"


def _render_section_blocks(spec: dict) -> tuple[list[str], str, str]:
    partials: list[str] = []
    last_model = ""
    for group in _SECTION_BLOCKS:
        section_map = {str(s.get("name", "")).lower(): s for s in spec.get("sections", []) if isinstance(s, dict)}
        selected = [section_map[name] for name in group if name in section_map]
        if not selected:
            continue
        block_spec = dict(spec)
        block_spec["sections"] = selected
        block_spec["_bloco_labels"] = group
        block_spec["_render_hint"] = "section_fragment"
        html, model = _render_block(block_spec, spec.get("design_tokens", {}))
        if not html:
            return [], last_model, f"Falha ao gerar bloco [{', '.join(group)}]"
        partials.append(html)
        last_model = model or last_model
    if not partials:
        return [], last_model, "nenhum fragmento gerado"
    return partials, last_model, ""


def _render_full_site(spec: dict) -> tuple[str, str, str]:
    """Controlled multi-call flow: shell first, then short section fragments."""
    shell_html, shell_model, shell_error = _render_shell_document(spec)
    if not shell_html:
        return "", shell_model, shell_error or "falha no shell"

    partials, last_model, partial_error = _render_section_blocks(spec)
    if not partials:
        return "", last_model or shell_model, partial_error or "falha nos fragmentos"

    final_html = _inject_sections_into_shell(shell_html, partials)
    valid_html, reason = _looks_like_valid_body_fragment(final_html)
    if not valid_html:
        return "", last_model or shell_model, f"HTML final invalido: {reason} ({len(final_html)} chars)"
    print(f"[builder] Multi-call OpenUI OK ({len(final_html)} chars)")
    return final_html, last_model or shell_model, ""


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
    spec["_run_id"] = getattr(prd, "_run_id", "") or ""
    spec["_lead_id"] = getattr(prd, "_lead_id", "") or ""
    _lead_data = getattr(prd, "_lead_data", None) or {}
    spec["_lead_name"] = _lead_data.get("nome", "") if isinstance(_lead_data, dict) else ""

    final_html, final_model, error = _render_full_site(spec)
    if not final_html:
        return BuildResult(
            html="",
            model=final_model,
            success=False,
            error=error or "Falha ao gerar HTML single-shot no OpenUI",
        )

    try:
        from backend.agents.llm_direct import _registrar_uso_completo
        _registrar_uso_completo(
            model_id=final_model or "openui-unknown",
            input_tokens=0,
            output_tokens=len(final_html) // 4,
            agent_name="builder_openui_single_shot",
            provider="openui",
        )
    except Exception as e:
        print(f"[builder] tracking falhou single-shot: {e}")

    return BuildResult(html=final_html, model=final_model, success=True)
