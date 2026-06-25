"""Vite/React system prompts and user prompt composers."""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════
# SHADCN/UI - Sprint 11
# ═══════════════════════════════════════════════════════════════════

def _build_shadcn_block() -> str:
    """Bloco shadcn/ui injetado no system prompt para o LLM preferir componentes prontos.

    Returns:
        String formatada com catálogo de componentes, regra de uso e imports.
    """
    try:
        from backend.services.vite_templates import (
            get_shadcn_component_list,
            get_shadcn_imports,
        )
    except Exception:
        return ""

    component_list = get_shadcn_component_list()
    example_imports = get_shadcn_imports(["Button", "Card", "Input", "Badge"])
    imports_block = "\n".join(example_imports)

    return f"""

SHADCN/UI COMPONENTS (Sprint 11 — use these instead of inventing custom HTML):
A library of pre-installed, accessible, premium-quality components is already
available. Prefer these over hand-rolled <button>, <input> or card divs.

Available components:
{component_list}

Import examples (these components are already in package.json, no extra install):
```
{imports_block}
```

Usage rules:
- For CTAs (hero, contact, pricing): use <Button variant="default" size="lg">.
- For form fields: use <Input type="..." placeholder="..." /> wrapped in <label>.
- For service/pricing/testimonial cards: use <Card> with CardHeader/CardContent.
- For category tags or "Novo"/"Popular" badges: use <Badge variant="secondary">.
- Always import the component at the top of the file. Never re-define a Button.
- Fall back to plain HTML only when the section truly needs custom markup.
"""


# ═══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT - Main instruction set for the LLM
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
"""


# Few-shot + negative examples (#4, #7) - injetados em runtime
def _build_few_shot_prompt() -> str:
    # Lazy load few-shot examples. Falha silenciosa se modulo nao existir.
    try:
        from backend.agents.few_shot_examples import build_few_shot_block
        return build_few_shot_block()
    except Exception:
        return ""


def _build_premium_contract_block() -> str:
    """Sprint 11.5: injeta o premium_delivery_contract (AIDA/PAS, archetypes,
    motion hooks, anti-patterns 2023) no VITE_REACT_SYSTEM_PROMPT.

    Antes da Sprint 11.5, este contrato so chegava ao OpenUI renderer.
    Ver backend/agents/prompt_agent_context.py:205-303 (fonte canonica).
    """
    try:
        from backend.agents.prompt_agent_context import _premium_delivery_contract
        # contexto minimo: secao vazia + business vazio; LLM ja recebeu facts
        # no user prompt, entao este bloco so ativa as REGRAS, nao duplica dados.
        context = {
            "business": {},
            "content": {},
            "design": {},
            "seo": {},
            "visual_contract": {},
            "site_build_plan": {},
        }
        contract = _premium_delivery_contract(context)
        return f"""

PREMIUM VISUAL + COPY CONTRACT (Sprint 11.5 — Vite/React parity with OpenUI):
{contract}
"""
    except Exception:
        return ""


def _build_visual_direction_block() -> str:
    """Sprint 11.5: injeta archetype/scene/color_strategy/heroes no
    VITE_REACT_SYSTEM_PROMPT. Antes so chegava ao OpenUI.
    """
    return """

VISUAL DIRECTION (REQUIRED — drive the entire page from one archetype):
The page must feel like a single coherent campaign, not a template with text swapped.
Choose ONE archetype per build and commit hard:

- BOLD_ENERGY (academia, fitness, crossfit, musculacao, eventos esportivos):
  base preta/carvao + vermelho eletrico + branco quente. Tipografia display condensada.
  Cortes diagonais, stats em slab perto da dobra. Manifesto forte apos hero.
  Azul corporativo REPROVA.

- ZEN_PURE (clinica estetica, nutricao, yoga, spa, bem-estar):
  respiro, superficies leves, fotografia editorial, motion suave. Evite SaaS frio.

- LUXURY_ELITE (restaurante premium, gastronomia, moda, eventos):
  imagem full-bleed, contraste sofisticado, escala tipografica, poucas palavras fortes.

- MODERN_TECH (energia solar, infraestrutura, eletrica, tecnologia):
  luz, grade, feixes, contraste tecnico, prova economica, engeharia confiavel.

- WARM_LOCAL (barbearia, salao, petshop, servicos pessoais):
  cores quentes, comunidade, prova local, fotos reais, hero humanizado.

Always include:
- AIDA (Attention-Interest-Desire-Action) when the value prop needs quick desire
  OR PAS (Problem-Agitate-Solution) when pain/objection drives the decision.
- Single H1, H2/H3 hierarchy, local SEO terms distributed naturally.
- One dominant hero idea, not a generic centered brochure.
"""


def _build_mobile_first_block() -> str:
    """Sprint 11.5: mobile-first, clamp(), 44px touch targets, responsividade."""
    return """

MOBILE-FIRST RESPONSIVENESS (MANDATORY):
- Design mobile-first. Default styles target mobile (>=375px). Use sm:/md:/lg: to enhance.
- All headings MUST use clamp() for fluid typography: text-[clamp(1.75rem,5vw,3rem)].
- Touch targets MUST be >= 44px height for buttons/links (min-h-[44px] py-3 px-6).
- No horizontal overflow on any viewport (overflow-x-hidden on body).
- Navbar MUST NOT cover hero content (sticky top with z-50 + hero has pt-16).
- Body text always legible: min text-base (16px) on mobile, leading-relaxed.
- Images: object-cover + sizes attribute + srcset when possible.
- Modal/Dialog: full-screen on mobile (sm:max-w-md for tablet+).
- Test at 375px (iPhone SE), 768px (iPad), 1280px (desktop) before delivery.
"""


def _build_motion_pack_block() -> str:
    """Sprint 11.5: lista COMPLETA de hooks Awwwards — alinhada com
    motion_runtime.js (openui_contracts.MOTION_CONTRACT) e vite_modules.

    Hooks implementados em runtime (ver motion_runtime.js):
    data-reveal, data-parallax, data-marquee, data-magnetic, data-3d-tilt,
    data-text-scramble, data-stagger, data-horizontal-scroll, data-counter,
    data-fralib-scroll-velocity, data-auto-animate, data-swup.
    """
    return """

ANIMATION LIBRARY (FraLib Awwwards Pack — use data-attributes, runtime picks up):
The deploy step injects `motion_runtime.js` (id="fralib-motion-runtime") which
auto-binds these data-attributes. You just add them to JSX; the runtime does the rest.

Available hooks (12 sistemas — IMPLEMENT THEM, do not invent custom JS):
- data-reveal="up|down|left|right|scale|fade" — fade-in on scroll (default: up)
- data-parallax="0.3" — image parallax (0.0=no movement, 1.0=full speed)
- data-marquee="left|right" — infinite horizontal scroll for chips/text
- data-magnetic — CTA buttons that follow the cursor (subtle, premium feel)
- data-3d-tilt="10" — 3D tilt effect on hover (degrees)
- data-text-scramble — letter scramble on scroll into view (h1, h2)
- data-stagger — children appear in sequence (cards, list items)
- data-horizontal-scroll — section that scrolls horizontally
- data-counter="200" — animated number counter (reviews count, anos, etc)
- data-fralib-scroll-velocity — text speed changes with scroll velocity
- data-auto-animate — list/container auto-animates on add (FLIP animation)
- [data-swup] — page transition wrapper (if used)

MOTION RULES:
- Use GSAP 3.12.5 + ScrollTrigger for any animation you write yourself.
- Use Lenis 1.1.20 for smooth scroll (already in package.json).
- NEVER write custom scroll handlers. Use hooks above.
- Animate ONLY opacity + transform (GPU-accelerated).
- Respect prefers-reduced-motion: motion runtime auto-detects and disables.
- Include at least 3 distinct hooks per page (e.g. parallax hero + stagger cards + counter stats).
- Hero MUST use at least one motion attribute (data-parallax or data-reveal="scale").
"""


VITE_REACT_SYSTEM_PROMPT_FOOT = (
    _build_few_shot_prompt()
    + _build_shadcn_block()
    + _build_premium_contract_block()
    + _build_visual_direction_block()
    + _build_motion_pack_block()
    + _build_mobile_first_block()
)

VITE_REACT_SYSTEM_PROMPT_TAIL = """

LANGUAGE (CRITICAL):
- All user-facing text, aria-labels, alt text, meta description, title, button
  labels, and content MUST be in Brazilian Portuguese (pt-BR).
- Comments in code may be in English.
- Component names and props stay in English (React convention).

CODE QUALITY (MANDATORY — Sprint 11.6):
- NEVER use `logger` as an identifier. Logger functions are NOT available.
  For console output use `console.log(...)` directly (already globally available).
- For utility helpers, define inline functions or use the imported `cn()` from @/lib/utils.
- All custom hooks must be defined inside the component file or imported from @/hooks/use-*.
- Do NOT import from non-existent paths. If you need a helper, inline it.

ACCESSIBILITY (MANDATORY):
- Use semantic HTML: <main>, <nav>, <section>, <article>, <header>, <footer>, <h1>-<h6>.
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
  Do NOT reuse the same generic section pattern for every site.
"""

VITE_REACT_SYSTEM_PROMPT = VITE_REACT_SYSTEM_PROMPT_HEAD + VITE_REACT_SYSTEM_PROMPT_FOOT + VITE_REACT_SYSTEM_PROMPT_TAIL


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

    # Injeta Design System Awwwards-grade (#25 Plano Mestre SDR)
    try:
        from backend.agents.design_system_injector import inject_design_system_into_prompt
        prompt = inject_design_system_into_prompt(prompt, facts)
    except Exception:
        pass

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
