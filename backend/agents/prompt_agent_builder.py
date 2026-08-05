"""Prompt Agent builder: public API for building prompt payloads."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.prompt_agent_context import (
    _business_context,
    _content_context,
    _design_context,
    _fmt_visual_direction,
    _media_context,
    _normalize_target,
    _premium_delivery_contract,
    _publication_context,
    _qualification_context,
    _research_context,
    _section_request,
    _seo_context,
    _visual_direction_contract,
)
from backend.agents.prompt_agent_helpers import (
    _allowed_numeric_claims,
    _as_dict,
    _dict,
    _fmt_contract_facts,
    _fmt_list,
    _fmt_missing_contract_fields,
    _fmt_research,
    _fmt_sections,
    _fmt_value,
    _qualification_summary,
)

try:
    from backend.agents.niche_resolver import resolve_niche_context
except Exception:  # pragma: no cover - local import variant
    try:
        from agents.niche_resolver import resolve_niche_context
    except Exception:
        from niche_resolver import resolve_niche_context


def build_prompt_agent_payload(source: Any, *, target: str = "landing-page") -> dict[str, Any]:
    """Build the isolated prompt payload consumed by the Builder Worker."""
    facts = _as_dict(source)
    if facts.get("contract") == "fralib-prompt-agent-v1" and facts.get("builder_prompt"):
        return facts

    normalized_target = _normalize_target(target)
    lead = _dict(facts.get("lead") or facts.get("lead_raw_data")) or facts
    caio = _dict(facts.get("caio") or facts.get("qualificacao_caio"))
    design = _dict(facts.get("design") or facts.get("visual_direction"))
    visual_dna = _dict(facts.get("visual_dna"))
    prompt_context = {
        "target": normalized_target,
        "business": _business_context(lead, facts),
        "qualification": _qualification_context(caio, facts),
        "research": _research_context(facts),
        "seo": _seo_context(facts),
        "content": _content_context(lead, facts),
        "media": _media_context(lead, facts),
        "design": _design_context(design, visual_dna, facts),
        "publication": _publication_context(lead, facts),
        "requirements_contract": _dict(facts.get("requirements_contract")),
        "visual_contract": _dict(facts.get("visual_contract")),
        "site_build_plan": _dict(facts.get("site_build_plan")),
        "sections": _section_request(lead, facts),
    }
    prompt_context["niche_context"] = resolve_niche_context(
        str(prompt_context["business"].get("segment") or ""),
        {**lead, **facts, **prompt_context["business"]},
    )
    prompt_context["allowed_numeric_claims"] = _allowed_numeric_claims(prompt_context["business"])
    prompt_context["visual_direction"] = _visual_direction_contract(prompt_context)
    builder_prompt = render_builder_prompt(prompt_context)
    return {
        "version": 1,
        "contract": "fralib-prompt-agent-v1",
        "target": normalized_target,
        "context": prompt_context,
        "builder_prompt": builder_prompt,
    }


def render_builder_prompt(context: dict[str, Any]) -> str:
    """Render one complete natural-language site request for the Builder."""
    business = context.get("business") or {}
    target = context.get("target") or "landing-page"
    payload = json.dumps(context, ensure_ascii=False, indent=2)
    name = business.get("name") or "Negócio local"
    segment = business.get("segment") or "negócio local"
    city = business.get("city") or ""
    city_part = f" in {city}" if city else ""
    content = context.get("content") or {}
    research = context.get("research") or {}
    seo = context.get("seo") or {}
    media = context.get("media") or {}
    design = context.get("design") or {}
    niche_context = context.get("niche_context") or {}
    sections = context.get("sections") or []
    ideal = content.get("ideal_customer") or {}
    return f"""Build a complete {target} for {name}, {segment}{city_part}.

You are the final Builder. FraLib has researched the business, qualified the lead and
organized the signals below into a briefing. Treat everything as raw material to
freely decide copy, SEO, structure, media, components, interactions,
and implementation.

There is no legacy checklist, no hidden rule from an old renderer, and no blocked
phrase. There is only this construction contract:
- The Builder is free to compose the site, but confirmed facts are immutable.
- Do not alter, round, replace, or invent name, phone, WhatsApp, e-mail,
  address, city, rating, review count, website, social media, or hours
  when they are provided.
- Where data is missing, do not invent operational data. Use neutral commercial
  neutral copy, CTA for contact, visual placeholders, or editorial sections without
  declaring price, menu, hours, delivery, awards, team, years in business,
  guarantee, or technology as fact.
- If products/services are not listed, speak about the niche in terms of category
  and purchase intent, without creating prices or specific items as if they
  were official.
- FAQ may only use responses confirmed in the briefing or neutral responses
  such as "Consulte diretamente pelo contato informado"; do not invent protocols,
  results, deadlines, families served, clients, or numbers.
- Numbers allowed in public copy: {_fmt_list(context.get("allowed_numeric_claims"))}
- If there is no reliable map, use an address card and external link; do not
  generate a map iframe with generic coordinates.
- Ensure that hero, fixed menu, texts, buttons, images, form, and footer do not
  cut off, overlap, or overflow on mobile and desktop.
- Generate every customer-facing headline, paragraph, CTA, FAQ, form label,
  alt text, metadata title/description, and footer text in Brazilian Portuguese
  (pt-BR). Technical file names and code identifiers may remain in English.

Premium visual and publishing contract
{_premium_delivery_contract(context)}

Mandatory visual direction contract
{_fmt_visual_direction(context.get("visual_direction") or {})}

Output runtime: deliver a Vite/React/TypeScript/Tailwind project
componentized in Studio mode. Use `@tailwindcss/vite`, `motion/react`,
`lucide-react`, `src/pages/Index.tsx`, `src/components/*.tsx`, `src/App.tsx`,
`src/main.tsx`, `src/index.css`, `src/types.ts`, `index.html`,
`package.json`, `tsconfig.json` and `vite.config.ts`. The FraLib wrapper runs
the build and publishes only the `dist` folder.

Immutable factual contract
{_fmt_contract_facts(business)}

Missing or unconfirmed data
{_fmt_missing_contract_fields(business, content)}

1. Business information
Business name: {_fmt_value(business.get("name"))}
Phone/WhatsApp: {_fmt_value(business.get("whatsapp") or business.get("phone"))}
E-mail: {_fmt_value(business.get("email"))}
Address: {_fmt_value(business.get("address"))}
City/service region: {_fmt_value(business.get("service_region") or business.get("city"))}
Current website: {_fmt_value(business.get("website"))}
Social media: {_fmt_list(business.get("socials"))}
Provided hours: {_fmt_value(business.get("hours"))}
Provided price range: {_fmt_value(business.get("price_range"))}

2. Services or products offered
{_fmt_list(content.get("services") or content.get("attributes"))}

3. Ideal customer profile
Who you want to attract: {_fmt_value(ideal.get("audience") or research.get("audience_notes"))}
Resolved sub-niche: {_fmt_value(niche_context.get("sub_niche"))}
Priority audiences: {_fmt_list(niche_context.get("audiences"))}
Tone by sub-niche: {_fmt_value(niche_context.get("tone"))}
Recommended hero by sub-niche: {_fmt_value(niche_context.get("hero_pattern"))}
Forbidden copy by sub-niche: {_fmt_list(niche_context.get("forbidden_copy"))}
Relevant age or range: {_fmt_value(ideal.get("age_range"))}
Profession or segment: {_fmt_value(ideal.get("profession_or_segment"))}
Main problems: {_fmt_list(ideal.get("main_problems"))}
Goals they want to achieve: {_fmt_list(ideal.get("goals"))}
What normally drives people to seek this service: {_fmt_value(ideal.get("buying_trigger"))}

4. Research, SEO, and market
{_fmt_research(research, seo)}

5. Content, reputation, and available media
Rating and proof: {_fmt_value(_qualification_summary(context.get("qualification") or {}, business))}
Photos: {_fmt_list(media.get("photos"))}
Videos: {_fmt_list(media.get("videos"))}
Map or location: {_fmt_value(content.get("maps_embed"))}
External map link: {_fmt_value(content.get("maps_url"))}
Additional notes: {_fmt_value(content.get("raw_notes"))}

6. Visual direction — MANDATORY color and typography tokens
⚠️ You MUST use the exact color tokens below as your CSS variables.
Do NOT substitute, replace, or invent different colors. These tokens are the
design system selected specifically for this business and niche.
Deviation from these tokens is a build failure.
Expected feeling: {_fmt_value(design.get("expected_feeling"))}
Palette or tokens: {_fmt_value(design.get("color_tokens"))}
Typography: {_fmt_value(design.get("typography"))}
Style references: {_fmt_value(design.get("design_reference"))}
Composition notes: {_fmt_list(design.get("composition_notes"))}
Above-the-fold direction: {_fmt_value((context.get("visual_direction") or {}).get("hero_storyboard"))}

7. Sections worth considering
{_fmt_sections(sections)}

Full structured context from the Prompt Agent:
{payload}
"""
