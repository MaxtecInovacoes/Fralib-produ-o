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


def _json_for_prompt(value: Any, limit: int = 4000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
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
- Preserve the requested AIDA role: hero=Attention, interesse=Interest, desejo=Desire, acao=Action
- If requested section is faq, lgpd, seo-geo or footer, render that exact functional section; do not replace it with generic cards
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
- Preserve AIDA structure when provided: hero, interesse, desejo, acao, plus faq, lgpd and footer
- Mobile-first responsive (375px to 1440px)
- Use Tailwind CSS utility classes directly in the markup
- Include Tailwind via CDN script in the <head>
- Keep the head minimal and do NOT output a long <style> block
- Hero must show business name, local context, and primary CTA above the fold
- Prioritize completing the full body before visual polish
"""


def _build_system_prompt(prd: dict) -> str:
    """Build the system prompt from DesignerPRD spec."""
    business = prd.get("business_name", "")
    cidade = prd.get("cidade", "")
    segmento = prd.get("segmento", "")
    render_hint = str(prd.get("_render_hint") or "").strip().lower()

    if render_hint == "shell_document":
        return (
            "You generate HTML shells. Return raw HTML only. "
            f"Create the empty shell for {business}, a {segmento} business in {cidade}. "
            "Required exact structure: <!DOCTYPE html><html lang=\"pt-BR\"><head>charset, viewport, title, Google Fonts and Tailwind CDN only</head>"
            "<body><main id=\"app-shell\"></main></body></html>. "
            "The main must be empty. Do not output sections, hero, footer, style blocks, scripts, markdown, or explanations."
        )

    if render_hint == "section_fragment":
        sections = [section for section in prd.get("sections", []) if isinstance(section, dict)]
        section_payload = sections[0] if sections else {}
        repair_feedback = str(prd.get("_repair_feedback") or "").strip()
        palette = prd.get("paleta") or prd.get("color_palette") or {}
        typography = prd.get("typography") or {}
        photos = prd.get("photos") or []
        photo_urls = [
            str(photo.get("url") if isinstance(photo, dict) else photo)
            for photo in photos[:8]
            if photo
        ]
        return (
            "You generate one semantic HTML section fragment. Return raw HTML only. "
            f"Business: {business}. Segment: {segmento}. City: {cidade}. "
            f"Requested section JSON: {_compact_json(section_payload, 1800)}. "
            f"Palette JSON: {_compact_json(palette, 500)}. "
            f"Typography JSON: {_compact_json(typography, 300)}. "
            f"Available editorial image URLs: {_compact_json(photo_urls, 1400)}. "
            "Preserve AIDA: hero captures Attention, interesse builds Interest, desejo creates Desire with offer/proof, acao drives Action. "
            "FAQ, LGPD, SEO/GEO and footer are functional sections, not decorative filler. "
            "Use at least one real <img> with an available URL in hero, about or media sections. "
            "Start the response with <section and finish with </section>. "
            "Include visible heading, useful copy, and CTA/content from the requested section. "
            "Use Tailwind utility classes directly. Do not output html, head, body, main, style, script, markdown, or explanation. "
            "Generate only this requested section and nothing else. "
            + (f"Previous validation error to fix: {repair_feedback}. " if repair_feedback else "")
        )

    segments: list[str] = []

    task_description = "Generate a complete, production-ready landing page HTML"

    segments.append(
        f"You are an expert frontend developer. {task_description} "
        f"for a {segmento} business called '{business}' "
        f"located in {cidade}. "
        "Obey the render mode and output contract exactly. "
        "Use a Tailwind-first approach so the response stays compact."
    )
    protected_payload = prd.get("openui_payload") or {}
    if protected_payload:
        segments.append("\n## PROTECTED GLOBAL CREATIVE PAYLOAD")
        segments.append(
            "This payload contains hard creative decisions. Implement them; do not replace them with a generic template."
        )
        segments.append(_json_for_prompt(protected_payload, 12000))

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
        segments.append("\n## Photos — use these exact editorial URLs")
        for index, photo in enumerate(photos[:8], 1):
            url = photo.get("url") if isinstance(photo, dict) else photo
            if url:
                segments.append(f"Photo {index}: {url}")
    media_plan = prd.get("media_plan") or []
    if media_plan:
        segments.append("\n## MEDIA PLAN — exact URLs, roles and required placement")
        segments.append(_json_for_prompt(media_plan, 5000))
        segments.append("Required media_plan items must appear in the HTML with the exact URL. Do not replace them with placeholders.")
    if videos:
        segments.append(f"\n## Videos: {len(videos)} videos available")

    segments.append(_build_output_contract(prd))

    # ── CONTRATOS DO ARQUITETO (injetados em força máxima) ──
    visual_contract = prd.get("visual_contract") or {}
    if visual_contract:
        segments.append("\n## VISUAL CONTRACT — From Arquiteto (obrigatório)")
        segments.append(_json_for_prompt(visual_contract, 3000))

    requirements_contract = prd.get("requirements_contract") or {}
    if requirements_contract:
        segments.append("\n## REQUIREMENTS CONTRACT — From Arquiteto (obrigatório)")
        segments.append(_json_for_prompt(requirements_contract, 3000))

    site_build_plan = prd.get("site_build_plan") or {}
    if site_build_plan:
        segments.append("\n## SITE BUILD PLAN — From Arquiteto (obrigatório)")
        segments.append(_json_for_prompt(site_build_plan, 5000))

    visual_dna = prd.get("visual_dna") or {}
    if visual_dna:
        segments.append("\n## VISUAL DNA — From Arquiteto")
        segments.append(_json_for_prompt(visual_dna, 3000))

    layout_blueprint = prd.get("layout_blueprint") or []
    if layout_blueprint:
        segments.append("\n## LAYOUT BLUEPRINT — From Arquiteto")
        segments.append(_json_for_prompt(layout_blueprint, 3000))

    design_reference_pack = prd.get("design_reference_pack") or {}
    if design_reference_pack:
        segments.append("\n## DESIGN REFERENCE PACK — From Arquiteto")
        segments.append(_json_for_prompt(design_reference_pack, 3000))

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
    render_hint = str(prd.get("_render_hint") or "").strip().lower()
    context = f" Business: {business_name}. City: {cidade}."
    if render_hint == "shell_document":
        return _build_mode_instructions(prd) + context + (
            " Output only the raw HTML shell. The main element must remain empty."
        )
    if render_hint == "section_fragment":
        return _build_mode_instructions(prd) + context + (
            f" Requested section: {', '.join(section_names)}. "
            "Output only the raw semantic section fragment. "
            "Start with <section and finish with </section>. "
            "Include visible heading, useful text, and CTA/content. "
            "Use Tailwind classes directly and do not include CSS or JavaScript."
        )
    return _build_mode_instructions(prd) + context + (
        f" Required sections: {', '.join(section_names)}. "
        "Output only the raw complete HTML document. "
        "Write the full body structure first and prefer complete content over visual polish."
    )


async def _repair_section_fragment(
    client: AsyncOpenAI,
    model: str,
    html: str,
    prd: dict[str, Any],
) -> tuple[str, str]:
    sections = [section for section in prd.get("sections", []) if isinstance(section, dict)]
    section_payload = sections[0] if sections else {}
    repair_messages = [
        {
            "role": "system",
            "content": (
                "You repair one HTML section fragment. Return raw HTML only. "
                "Start with <section and finish with </section>. "
                "If the draft is too short, empty, only text, or malformed, ignore it and regenerate the requested section from the JSON contract. "
                "The final answer must contain useful visible content, at least one heading, and enough text for a real landing page section. "
                "Remove document wrappers, CSS, JavaScript, markdown, and explanations."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Requested section JSON: {_compact_json(section_payload, 1200)}\n"
                f"Invalid draft to repair:\n{html[:12000]}"
            ),
        },
    ]
    response = await client.chat.completions.create(
        model=model,
        messages=repair_messages,
        max_tokens=min(MAX_TOKENS, 12000),
        temperature=0.1,
    )
    repaired = (response.choices[0].message.content or "").strip()
    if repaired.startswith("```html"):
        repaired = repaired[7:]
    if repaired.startswith("```"):
        repaired = repaired[3:]
    if repaired.endswith("```"):
        repaired = repaired[:-3]
    return repaired.strip(), response.model or model


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
        render_hint = str(prd.get("_render_hint") or "").strip().lower()
        if not valid_html and render_hint == "section_fragment":
            logger.warning(
                "Repairing invalid section_fragment (%s, %d chars)",
                reason,
                len(html),
            )
            html, model_used = await _repair_section_fragment(client, model, html, prd)
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
