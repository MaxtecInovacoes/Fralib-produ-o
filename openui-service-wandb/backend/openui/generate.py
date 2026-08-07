"""
POST /generate endpoint — wraps LiteLLM chat completions for FraLib Builder agent.

Accepts {"designerPRD": spec} and returns {"html": "...", "model": "..."}.
No auth required — this is a backend-to-backend API.
"""
import json
import os
import logging
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
MAX_TOKENS = int(os.getenv("FRA_GENERATION_MAX_TOKENS", "16000"))
TEMPERATURE = float(os.getenv("FRA_GENERATION_TEMPERATURE", "0.7"))


class GenerateRequest(BaseModel):
    designerPRD: dict[str, Any] = Field(..., description="DesignerPRD spec from FraLib")


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
        f"located in {cidade}."
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
            content = s.get("content", "")
            segments.append(f"\n### {title} ({name})")
            if content:
                segments.append(content[:2000])

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
        for r in reviews[:5]:
            segments.append(f"- {r.get('author', '')}: {r.get('text', '')[:200]}")

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
        segments.append(f"\n## Competitor Analysis\n{comp[:500]}")

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

    # Output contract
    segments.append("""

## Output Contract
Return ONLY a single complete HTML file. No markdown, no code fences, no explanation.
- Single <html> document with embedded <style> and <script>
- Mobile-first responsive (375px to 1440px)
- Use CSS custom properties for the color palette
- Include semantic HTML5 elements
- Inline ALL CSS and JS — no external dependencies except Google Fonts
- Use IntersectionObserver for scroll-reveal animations
- Include proper meta tags for SEO
- Make it visually impressive — this is the final deliverable
""")

    # ── CONTRATOS DO ARQUITETO (injetados em força máxima) ──
    visual_contract = prd.get("visual_contract") or {}
    if visual_contract:
        segments.append("\n## VISUAL CONTRACT — From Arquiteto (obrigatório)")
        segments.append(json.dumps(visual_contract, ensure_ascii=False, indent=2)[:3000])

    requirements_contract = prd.get("requirements_contract") or {}
    if requirements_contract:
        segments.append("\n## REQUIREMENTS CONTRACT — From Arquiteto (obrigatório)")
        segments.append(json.dumps(requirements_contract, ensure_ascii=False, indent=2)[:3000])

    site_build_plan = prd.get("site_build_plan") or {}
    if site_build_plan:
        segments.append("\n## SITE BUILD PLAN — From Arquiteto (obrigatório)")
        segments.append(json.dumps(site_build_plan, ensure_ascii=False, indent=2)[:3000])

    visual_dna = prd.get("visual_dna") or {}
    if visual_dna:
        segments.append("\n## VISUAL DNA — From Arquiteto")
        segments.append(json.dumps(visual_dna, ensure_ascii=False, indent=2)[:2000])

    layout_blueprint = prd.get("layout_blueprint") or []
    if layout_blueprint:
        segments.append("\n## LAYOUT BLUEPRINT — From Arquiteto")
        segments.append(json.dumps(layout_blueprint, ensure_ascii=False, indent=2)[:2000])

    design_reference_pack = prd.get("design_reference_pack") or {}
    if design_reference_pack:
        segments.append("\n## DESIGN REFERENCE PACK — From Arquiteto")
        segments.append(json.dumps(design_reference_pack, ensure_ascii=False, indent=2)[:2000])

    prompt_final = "\n".join(segments)
    if _openui_logger:
        _openui_logger.info(
            "PRD_OPENUI: prompt_inicio=[{preview}]",
            preview=prompt_final[:2000],
        )
    return prompt_final


def _build_user_message(prd: dict) -> str:
    """Build the user message with the full PRD context."""
    return (
        "Generate the complete landing page HTML based on the DesignerPRD "
        "specification. Follow the design system, sections, and creative "
        "directive precisely. Output only the raw HTML file."
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

        if not html or len(html) < 1000:
            raise HTTPException(
                status_code=502,
                detail=f"Generated HTML too short ({len(html)} chars) — model may have failed",
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
