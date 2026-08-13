"""
POST /generate endpoint — wraps LiteLLM chat completions for FraLib Builder agent.

Accepts {"designerPRD": spec} and returns {"html": "...", "model": "..."}.
No auth required — this is a backend-to-backend API.
"""
import json
import os
import logging
import re
from typing import Any

try:
    from loguru import logger as _openui_logger
except ImportError:
    _openui_logger = None

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .config import LITELLM_API_KEY, LITELLM_BASE_URL

logger = logging.getLogger(__name__)
router = APIRouter()

# Default model for site generation
DEFAULT_GENERATION_MODEL = os.getenv(
    "FRA_GENERATION_MODEL",
    "claude-sonnet-5",
)
MAX_TOKENS = int(os.getenv("FRA_GENERATION_MAX_TOKENS", "64000"))
TEMPERATURE = float(os.getenv("FRA_GENERATION_TEMPERATURE", "0.35"))


class GenerateRequest(BaseModel):
    designerPRD: dict[str, Any] = Field(..., description="DesignerPRD spec from FraLib")


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _compact_json(value: Any, limit: int = 600) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        text = str(value)
    return text[:limit]


def _html_has_minimum_structure(html: str) -> tuple[bool, str]:
    if not html or len(html.strip()) < 1000:
        return False, "html curto"
    lower = html.lower()
    if "<html" not in lower or "<body" not in lower or "<main" not in lower:
        return False, "documento sem html/body/main"
    if lower.count("<section") < 3:
        return False, "menos de 3 sections"
    if "<h1" not in lower:
        return False, "sem h1"
    stripped = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", html)
    stripped = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", stripped)
    visible_text = re.sub(r"(?is)<[^>]+>", " ", stripped)
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    if len(visible_text) < 120:
        return False, "texto visível insuficiente"
    return True, ""


def _fragment_has_minimum_structure(html: str) -> tuple[bool, str]:
    if not html or len(html.strip()) < 200:
        return False, "fragmento curto"
    lower = html.lower()
    section_count = lower.count("<section")
    if section_count < 1:
        return False, "sem section"
    stripped = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", html)
    stripped = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", stripped)
    visible_text = re.sub(r"(?is)<[^>]+>", " ", stripped)
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    if len(visible_text) < 60:
        return False, "texto visível insuficiente"
    return True, ""


def _normalize_generated_html(html: str, prd: dict[str, Any]) -> str:
    render_hint = str(prd.get("_render_hint") or "").strip().lower()
    if render_hint != "section_fragment" or "<section" in html.lower():
        return html

    body_match = re.search(r"(?is)<body\b[^>]*>(.*?)</body>", html)
    fragment = body_match.group(1).strip() if body_match else html.strip()
    fragment = re.sub(r"(?is)<!doctype[^>]*>", "", fragment)
    fragment = re.sub(r"(?is)</?(?:html|head|body|main)\b[^>]*>", "", fragment)
    fragment = re.sub(r"(?is)<title\b[^>]*>.*?</title>", "", fragment)
    fragment = re.sub(r"(?is)<meta\b[^>]*>", "", fragment)
    fragment = re.sub(r"(?is)<link\b[^>]*>", "", fragment)
    fragment = re.sub(r"(?is)<style\b[^>]*>.*?</style>", "", fragment)
    fragment = re.sub(r"(?is)<script\b[^>]*>.*?</script>", "", fragment).strip()

    visible_text = re.sub(r"(?is)<[^>]+>", " ", fragment)
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    if len(fragment) < 200 or len(visible_text) < 60:
        return html

    section_name = "section"
    sections = prd.get("sections") or []
    if sections and isinstance(sections[0], dict):
        section_name = str(sections[0].get("name") or section_name).strip().lower()
        section_name = re.sub(r"[^a-z0-9_-]+", "-", section_name).strip("-") or "section"
    logger.warning(
        "Normalized section_fragment without section wrapper (%d chars, section=%s)",
        len(html),
        section_name,
    )
    return f'<section id="{section_name}">\n{fragment}\n</section>'


def _validate_generated_html(html: str, prd: dict[str, Any]) -> tuple[bool, str]:
    render_hint = str(prd.get("_render_hint") or "").strip().lower()
    if render_hint == "section_fragment":
        return _fragment_has_minimum_structure(html)
    if render_hint == "shell_document":
        if not html or len(html.strip()) < 400:
            return False, "shell curto"
        lower = html.lower()
        if "<html" not in lower or "<body" not in lower or "<main" not in lower:
            return False, "shell sem html/body/main"
        return True, ""
    return _html_has_minimum_structure(html)


def _build_output_contract(prd: dict[str, Any]) -> str:
    render_hint = str(prd.get("_render_hint") or "").strip().lower()
    if render_hint == "shell_document":
        return """
## Output Contract — SHELL DOCUMENT
Return ONLY one complete HTML document. No markdown, code fences, explanation, or text outside the document.
- Required literal structure: <!DOCTYPE html><html><head>...</head><body><main id="app-shell"></main></body></html>
- Include exactly one <html>, one <head>, one <body>, and one empty <main id="app-shell">
- The <main> must be empty: section fragments will be inserted later
- Keep <head> minimal: charset, viewport, title, fonts, and Tailwind CDN only
- Do NOT render hero, sections, cards, footer, long CSS, or large scripts
- Before answering, verify the response contains <html, <body, and <main id="app-shell">
"""
    if render_hint == "section_fragment":
        return """
## Output Contract — SECTION FRAGMENT
Return ONLY the requested semantic <section> block. No markdown, code fences, explanation, or text outside the fragment.
- The first non-whitespace characters must be <section
- The last non-whitespace characters must close the section with </section>
- Include visible heading, text, and CTA/content appropriate to the requested section
- Use Tailwind utility classes directly in the markup
- Do NOT output <!DOCTYPE>, <html>, <head>, <body>, <main>, Tailwind config, <style>, or <script>
- Do NOT render sections that were not requested
- Before answering, verify the response contains at least one opening <section and one closing </section>
"""
    return """
## Output Contract — FULL DOCUMENT
Return ONLY a single complete HTML file. No markdown, code fences, or explanation.
- Single <html> document with exactly one <main> and one visible <h1>
- At least 3 semantic <section> blocks with real visible content
- Mobile-first responsive (375px to 1440px)
- Use Tailwind CSS utility classes directly in the markup
- Include Tailwind via CDN script in the <head>
- Keep the head minimal and do NOT output a long <style> block
- Hero must show business name, local context, and primary CTA above the fold
- Prioritize completing the full body before visual polish
"""


def _build_system_prompt(prd: dict) -> str:
    """Build the system prompt from DesignerPRD spec."""
    segments: list[str] = []

    # Core identity
    business = prd.get("business_name", "")
    cidade = prd.get("cidade", "")
    segmento = prd.get("segmento", "")

    segments.append(
        f"You are an expert frontend developer. Generate a complete, production-ready "
        f"landing page HTML for a {segmento} business called '{business}' "
        f"located in {cidade}. "
        "Use a Tailwind-first approach so the response stays compact and the full body fits in the token budget."
    )

    # Design system
    design_tokens = prd.get("design_tokens", {})
    archetype = design_tokens.get("archetype", "editorial-asymmetric")
    paleta = prd.get("paleta", design_tokens.get("palette", {}))
    radius = design_tokens.get("radius", "12px")

    archetype_briefing = {
        "industrial-bold": "BOLD industrial aesthetic. Massive typography, dark backgrounds, sharp edges. Brutalist luxury.",
        "dark-futurist": "Futuristic dark mode. Neon accents, glass morphism, smooth gradients. Premium tech feel.",
        "editorial-asymmetric": "Editorial asymmetric layout. Magazine-style grid, bold typography, generous whitespace. Premium content-first.",
        "apple-minimalist": "Minimalist. Clean white space, subtle shadows, restrained palette. Apple-inspired simplicity.",
        "organic-warm": "Warm organic. Earth tones, rounded shapes, natural textures. Approachable and trustworthy.",
        "corporate-trust": "Corporate trust. Professional blue, structured grid, clear hierarchy. Enterprise credibility.",
    }
    style_brief = archetype_briefing.get(archetype, archetype_briefing["editorial-asymmetric"])

    segments.append(f"\n## Design System\nStyle: {style_brief}")
    segments.append(f"Archetype: {archetype}\nBorder radius: {radius}")

    # Color palette
    if paleta:
        segments.append("\n### Color Palette (CSS variables)")
        for key, val in paleta.items():
            if key in {"tokens_oklch", "hero_style", "reasoning"}:
                continue
            segments.append(f"  --{key}: {val};")

    # Typography
    typography = prd.get("typography", {})
    if typography:
        segments.append("\n### Typography")
        for key, val in typography.items():
            segments.append(f"  {key}: {val};")

    # Layout DNA
    layout_dna = prd.get("layout_dna", {})
    if layout_dna:
        segments.append(f"\n### Layout\nFamily: {layout_dna.get('layout_family', 'asymmetric-magazine')}")

    # Hero section
    hero = prd.get("hero", {})
    if hero:
        segments.append("\n## Hero Section")
        if hero.get("headline"):
            segments.append(f"Headline: {hero['headline']}")
        if hero.get("subheadline"):
            segments.append(f"Subheadline: {hero['subheadline']}")
        if hero.get("cta_text"):
            segments.append(f"CTA: {hero['cta_text']}")

    # Sections
    sections = prd.get("sections", [])
    if sections:
        segments.append("\n## Page Sections")
        for i, s in enumerate(sections):
            name = s.get("name", f"section_{i}")
            title = s.get("title", name)
            layout_type = s.get("layout_type", "")
            components = s.get("components", [])
            copy_data = s.get("copy_data", {})
            content = s.get("content", "")
            segments.append(f"\n### {title} ({name})")
            if layout_type:
                segments.append(f"Layout type: {layout_type}")
            if components:
                segments.append(f"Components: {_compact_json(components, 220)}")
            if copy_data:
                segments.append(f"Copy data: {_compact_json(copy_data, 500)}")
            if content:
                segments.append(content[:700])

    # CTAs
    ctas = prd.get("ctas", [])
    if ctas:
        segments.append("\n## Call-to-Actions")
        for cta in ctas:
            segments.append(f"- {cta.get('text', '')} -> {cta.get('href', '#')}")

    # FAQs
    faqs = prd.get("faqs", [])
    if faqs:
        segments.append("\n## FAQ Section")
        for q in faqs:
            segments.append(f"Q: {q}")

    # Motion directives
    motion = prd.get("motion_directives", {})
    if motion:
        segments.append("\n## Motion & Animation")
        segments.append(f"Parallax: {motion.get('parallax', False)}")
        segments.append(f"Scroll reveal: {motion.get('scroll_reveal', False)}")
        segments.append(f"Hover effects: {motion.get('hover_effects', False)}")

    # Reviews
    reviews = prd.get("reviews_list", [])
    if reviews:
        segments.append("\n## Reviews")
        for r in reviews[:3]:
            segments.append(f"- {r.get('author', '')}: {r.get('text', '')[:120]}")

    # Schema.org
    schema_types = prd.get("schema_org_types", [])
    if schema_types:
        segments.append(f"\n## Schema.org Types: {', '.join(schema_types)}")

    # Anti-patterns
    anti = prd.get("anti_patterns", [])
    if anti:
        segments.append("\n## Anti-Patterns (AVOID)")
        for a in anti:
            segments.append(f"- {a}")

    # Creative directive
    directive = prd.get("builder_directive", "")
    if directive:
        segments.append(f"\n## Creative Directive\n{directive}")

    # Competitor analysis
    comp = prd.get("competitor_analysis", "")
    if comp:
        segments.append(f"\n## Competitor Analysis\n{comp[:180]}")

    # SEO keywords
    seo = prd.get("seo_keywords", [])
    if seo:
        segments.append(f"\n## SEO Keywords: {', '.join(seo[:10])}")

    # Address / phone
    address = prd.get("address", "")
    phone = prd.get("phone", "")
    hours = prd.get("hours", {})
    if address or phone:
        segments.append("\n## Contact Info")
        if address:
            segments.append(f"Address: {address}")
        if phone:
            segments.append(f"Phone: {phone}")
        if hours:
            segments.append(f"Hours: {json.dumps(hours)}")

    # Photos / videos
    photos = prd.get("photos", [])
    videos = prd.get("videos", [])
    if photos:
        segments.append(f"\n## Photos: {len(photos)} images available")
    if videos:
        segments.append(f"\n## Videos: {len(videos)} videos available")

    segments.append(_build_output_contract(prd))

    # ── CONTRATOS DO ARQUITETO (injetados em força máxima) ──
    visual_contract = prd.get("visual_contract") or {}
    if visual_contract:
        segments.append("\n## VISUAL CONTRACT — From Arquiteto (obrigatório)")
        segments.append(_compact_json(visual_contract, 900))

    requirements_contract = prd.get("requirements_contract") or {}
    if requirements_contract:
        segments.append("\n## REQUIREMENTS CONTRACT — From Arquiteto (obrigatório)")
        segments.append(_compact_json(requirements_contract, 900))

    site_build_plan = prd.get("site_build_plan") or {}
    if site_build_plan:
        segments.append("\n## SITE BUILD PLAN — From Arquiteto (obrigatório)")
        segments.append(_compact_json(site_build_plan, 1000))

    visual_dna = prd.get("visual_dna") or {}
    if visual_dna:
        segments.append("\n## VISUAL DNA — From Arquiteto")
        segments.append(_compact_json(visual_dna, 500))

    layout_blueprint = prd.get("layout_blueprint") or []
    if layout_blueprint:
        segments.append("\n## LAYOUT BLUEPRINT — From Arquiteto")
        segments.append(_compact_json(layout_blueprint, 500))

    design_reference_pack = prd.get("design_reference_pack") or {}
    if design_reference_pack:
        segments.append("\n## DESIGN REFERENCE PACK — From Arquiteto")
        segments.append(_compact_json(design_reference_pack, 500))

    prompt_final = "\n".join(segments)
    if _openui_logger:
        _openui_logger.info(
            "PRD_OPENUI: prompt_inicio=[{preview}]",
            preview=prompt_final[:2000],
        )
    return prompt_final


def _build_mode_instructions(prd: dict) -> str:
    render_hint = str(prd.get("_render_hint") or "").strip().lower()
    if render_hint == "shell_document":
        return (
            "Render mode: shell_document. "
            "Return a complete HTML document with a very short <head>, Tailwind CDN, one <body>, and exactly one empty <main id=\"app-shell\"></main>. "
            "Do not render any hero, section, placeholder, footer, long CSS, or large script."
        )
    if render_hint == "section_fragment":
        return (
            "Render mode: section_fragment. "
            "Return ONLY HTML fragments intended to live inside <main>. "
            "Do not return <!DOCTYPE>, <html>, <head>, <body>, Tailwind config, or large scripts. "
            "Render only the requested sections as semantic <section> blocks with Tailwind classes."
        )
    return (
        "Render mode: full_document. "
        "Return the full HTML document."
    )


def _build_user_message(prd: dict) -> str:
    """Build the user message with the full PRD context."""
    section_names = [s.get("name", "") for s in prd.get("sections", []) if isinstance(s, dict)]
    business_name = prd.get("business_name", "")
    cidade = prd.get("cidade", "")
    return (
        _build_mode_instructions(prd) + " " +
        "Generate the complete landing page HTML based on the DesignerPRD "
        "specification. Follow the design system, sections, and creative "
        "directive precisely. Output only the raw HTML file. "
        f"Business: {business_name}. City: {cidade}. "
        f"Required sections: {', '.join(section_names)}. "
        "Do not output CSS-only layouts, placeholder wrappers, or empty body content. "
        "Use Tailwind utility classes directly on the elements. "
        "Do not emit a long <style> block. "
        "Write the full <body> structure first, including <main>, <section>, headings, text and CTAs. "
        "Keep the <head> very short so the response finishes the complete body. "
        "Prefer complete content over visual polish if you must trade off."
    )


@router.post("/generate", tags=["openui/generate"])
async def generate_site(request: GenerateRequest):
    """Generate HTML site from DesignerPRD spec via LiteLLM proxy."""
    prd = request.designerPRD

    # Validate minimum required fields
    if not prd.get("business_name"):
        raise HTTPException(status_code=400, detail="designerPRD.business_name is required")

    system_prompt = _build_system_prompt(prd)
    user_message = _build_user_message(prd)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Use LiteLLM client (pointing to our DeployFlow proxy)
    client = AsyncOpenAI(
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_BASE_URL,
    )

    model = DEFAULT_GENERATION_MODEL

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )

        html = response.choices[0].message.content or ""
        model_used = response.model or model

        # Clean up markdown fences if the model wraps HTML in them
        html = html.strip()
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()
        html = _normalize_generated_html(html, prd)

        valid_html, reason = _validate_generated_html(html, prd)
        if not valid_html:
            raise HTTPException(
                status_code=502,
                detail=f"Generated HTML invalid ({reason}) ({len(html)} chars) — model may have failed",
            )

        logger.info(
            "Generated %d chars of HTML for %s using %s",
            len(html),
            prd.get("business_name", "unknown"),
            model_used,
        )

        return JSONResponse(content={"html": html, "model": model_used})

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Generation failed: %s", str(e))
        raise HTTPException(status_code=502, detail=f"Generation failed: {str(e)}")
