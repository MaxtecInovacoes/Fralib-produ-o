"""Vite/React system prompts and user prompt composers."""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Main instruction set for the LLM
# ═══════════════════════════════════════════════════════════════════

VITE_REACT_SYSTEM_PROMPT_HEAD = """You are a senior React/Vite/Tailwind landing-page engineer with AI Studio-level visual taste.

Build a complete, premium, responsive local-business website as a Vite React
TypeScript project. Return one strict JSON object only, no markdown:

{
  "files": {
    "package.json": "...",
    "index.html": "...",
    "vite.config.ts": "...",
    "tsconfig.json": "...",
    "src/main.tsx": "...",
    "src/App.tsx": "...",
    "src/index.css": "...",
    "src/types.ts": "...",
    "src/pages/Index.tsx": "...",
    "src/components/Navbar.tsx": "...",
    "src/components/HeroSection.tsx": "...",
    "src/components/<Section2>.tsx": "...",


# Few-shot + negative examples (#4, #7) - injetados em runtime
try:
    from backend.agents.few_shot_examples import build_few_shot_block
    VITE_REACT_SYSTEM_PROMPT_FOOT = build_few_shot_block()
except Exception:
    VITE_REACT_SYSTEM_PROMPT_FOOT = ""

VITE_REACT_SYSTEM_PROMPT = VITE_REACT_SYSTEM_PROMPT_HEAD + VITE_REACT_SYSTEM_PROMPT_FOOT
    "src/components/<Section3>.tsx": "...",
    "src/components/<Section4>.tsx": "...",
    "src/components/<Section5>.tsx": "...",
    "src/components/<Section6>.tsx": "...",
    "src/components/<Section7>.tsx": "...",
    "src/components/ContactCTA.tsx": "...",
    "src/components/Footer.tsx": "...",
    "src/components/Testimonials.tsx": "...",
    "src/components/Pricing.tsx": "...",
    "src/components/Faq.tsx": "..."
  }
}

LANGUAGE (CRITICAL):
- All user-facing text, aria-labels, alt text, meta description, title, button
  labels, and content MUST be in Brazilian Portuguese (pt-BR).
- Comments in code may be in English.
- Component names and props stay in English (React convention).

ACCESSIBILITY (MANDATORY):
- Use semantic HTML: <main>, <nav>, <section>, <article>, <header>, <footer>, <h1>–<h6>.
- Every image MUST have descriptive alt attribute in pt-BR.
- Icon-only buttons MUST have aria-label in pt-BR.
- Form inputs MUST have associated <label> elements.
- Color contrast ratio must be >= 4.5:1 (WCAG AA).
- Include "Pular para o conteúdo" skip link.
- Ensure single H1 per page.

SEO (MANDATORY):
- Include <title> and <meta name="description"> in pt-BR.
- Include Open Graph tags: og:title, og:description, og:image, og:url, og:type.
- Include <link rel="canonical"> placeholder.
- Use proper heading hierarchy (single H1, then H2/H3 in order).
- Include Twitter Card meta tags.
- Include JSON-LD structured data (LocalBusiness schema).

LGPD COMPLIANCE (MANDATORY):
- Include cookie consent banner placeholder (data-lgpd-banner).
- Include accept button placeholder (data-lgpd-accept).
- Include privacy policy link in footer.

MOTION (REQUIRED):
- Implement scroll-triggered animations with GSAP 3.12.5 + ScrollTrigger.
- Use Lenis 1.1.20 for smooth scroll.
- Add data-parallax attribute on parallax images.
- Add data-magnetic to magnetic CTAs.
- Add data-text-scramble for text reveal effects.
- Add data-letter-reveal for letter-by-letter title animations.
- Add fralib-grain texture overlay (subtle noise).
- Add fralib-cursor custom cursor for premium feel.
- Include fralib-card-interactive for hover effects on cards.
- Include fralib-reading-progress bar at top of page.

COMPONENTS (include when relevant):
- Testimonials: cards with avatar, name, role, stars (5), real-looking quote.
- Pricing: table with 3 plans (Basic, Pro, Premium) with feature lists.
- FAQ: accordion with 4-6 questions and answers in pt-BR.

Rules:
- Use React + TypeScript + Tailwind v4 through @tailwindcss/vite, motion/react
  and lucide-react. Componentize the page in src/components and compose it from
  src/pages/Index.tsx.
- If the user asks for a file batch, return only the requested paths in the
  same strict JSON `files` object. Do not wrap it in status/metadata.
- If the brief lists exact files to create/edit, generate those exact files and
  wire them into the page. Do not collapse requested sections into one generic
  component.
- Vite will build the project to dist. Do not output Next.js app router,
  server routes, auth, database code, Supabase, CRM, dashboards or admin code.
- Preserve confirmed business facts exactly.
- Do not invent operational facts, fake services, fake links, fake Instagram
  URLs, awards, prices, years in business or guarantees.
- Use lucide-react icons when useful.
- src/index.css must include @import "tailwindcss"; and a real design system:
  font imports or fallbacks, tokens, selection, reduced motion and body/base
  styles. Do not depend on remote CSS frameworks or CDN scripts.
- Source must be rich enough for a production site, not a thin demo.
- Choose section names and component structure that match THIS specific business.
  Do NOT reuse the same generic section pattern for every site. Examples:"""


VITE_REACT_BATCH_SYSTEM_PROMPT = """You are generating file batch "{batch_name}" for a Vite React landing page.

Return ONLY a JSON object with the requested files:
{{
  "files": {{
    "path/to/file1.tsx": "file content...",
    "path/to/file2.tsx": "file content..."
  }}
}}

Rules:
- Include complete, production-ready code
- Use TypeScript with proper types
- Use Tailwind CSS v4
- Import from lucide-react for icons
- Do NOT use: Next.js, Supabase, Firebase, auth, database code
- Match the business facts exactly (name, address, phone, services)"""


# ═══════════════════════════════════════════════════════════════════
# USER PROMPT COMPOSERS
# ═══════════════════════════════════════════════════════════════════

def _compose_vite_user_prompt(
    facts: dict[str, Any],
    segment: str,
    template: str = "default",
) -> str:
    """Compose the main user prompt with business facts."""
    business = facts.get("business", {})
    city = facts.get("city", "")
    phone = facts.get("phone", "")
    address = facts.get("address", "")
    services = facts.get("services", [])
    niche = facts.get("niche", segment)

    # Build services section
    services_section = ""
    if services:
        services_list = "\n".join(f"  - {s}" for s in services[:8])
        services_section = f"\nServices:\n{services_list}"

    # Build prompt
    prompt = f"""Generate a premium Vite React landing page for:

Business: {business.get('name', 'Business Name')}
Niche: {niche}
City: {city}
Phone: {phone}
Address: {address}{services_section}

Requirements:
- Modern, premium design with Tailwind CSS v4
- Responsive for mobile and desktop
- Fast loading with optimized images
- Professional typography
- Clear call-to-action sections
- Include realistic content (no lorem ipsum)

Generate complete TypeScript React components with proper types."""

    return prompt


def _compose_vite_file_batch_prompt(
    batch_name: str,
    batch_files: list[str],
    facts: dict[str, Any],
    facts_summary: str,
) -> str:
    """Compose prompt for a specific batch of files."""
    business = facts.get("business", {})
    city = facts.get("city", "")
    segment = facts.get("segment", "")

    prompt = f"""Generate the following files for a Vite React landing page:

Business: {business.get('name', 'Business Name')}
Segment: {segment}
City: {city}

Files to generate:
{chr(10).join(f'- {f}' for f in batch_files)}

{facts_summary}

Return ONLY a JSON object with "files" key containing the file paths and contents."""

    return prompt


def _summarize_builder_facts(facts: dict[str, Any]) -> str:
    """Create a compact summary of business facts for prompts."""
    business = facts.get("business", {})
    cidade = facts.get("city", "")
    segmento = facts.get("segment", "")
    telefone = facts.get("phone", "")
    endereco = facts.get("address", "")
    servicos = facts.get("services", [])
    palavras_poder = facts.get("palavras_poder", [])
    horarios = facts.get("horarios", "")

    parts = [
        f"Business: {business.get('name', 'N/A')}",
        f"Segment: {segmento}",
        f"City: {cidade}",
    ]

    if telefone:
        parts.append(f"Phone: {telefone}")
    if endereco:
        parts.append(f"Address: {endereco}")
    if servicos:
        parts.append(f"Services: {', '.join(servicos[:5])}")
    if palavras_poder:
        parts.append(f"Keywords: {', '.join(palavras_poder[:5])}")
    if horarios:
        parts.append(f"Hours: {horarios}")

    return "\n".join(parts)


def _segment_contamination_guard(facts: dict[str, Any]) -> str:
    """Create prompt injection to prevent cross-segment contamination."""
    business = facts.get("business", {})
    business_name = business.get("name", "")

    guard = f"""
IMPORTANT: Do not copy style, layout, colors, or content from any competitor.
This site is ONLY for: {business_name}
If the generated code resembles another business, rewrite it completely.
"""
    return guard


def _safe_project_path(path: str) -> str:
    """Sanitize project path for safety."""
    import re

    # Remove any path traversal attempts
    safe = re.sub(r"[^a-zA-Z0-9_\-./]", "_", path)
    safe = re.sub(r"\.{2,}", ".", safe)
    return safe


def _meta_escape(value: Any) -> str:
    """Escape HTML entities for meta tags."""
    if not isinstance(value, str):
        value = str(value)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
