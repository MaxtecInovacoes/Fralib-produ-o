"""Compact design skill pack for the single-call site renderer.

This file is intentionally small. It distills the design skills FraLib needs
without loading large SKILL.md files on every production run.
"""

SITE_SKILL_PACK = """
# SITE SKILL PACK - FRA LIB

Use this as production craft guidance, not as separate agents.

## 1. Design engineering craft
- Build a complete single-file public website, not a component demo.
- Commit to a clear visual idea per business. Avoid converging every local
  business into the same dark/card/grid template.
- Use semantic sections, real hierarchy, responsive CSS, accessible labels,
  and production-ready spacing.
- Prefer expressive composition over safe stacking: asymmetry, scale shifts,
  editorial rhythm, strong first viewport, and a closing footer that feels
  designed.

## 2. Impeccable visual laws
- Do not use identical card grids as the default answer.
- Do not use emoji. Use inline SVG or pure typography if an icon is needed.
- Do not use glassmorphism, gradient text, or generic hero-metric templates.
- Vary spacing deliberately. Uniform padding everywhere looks generated.
- Pick a theme from the business scene, not from the niche label alone.
- Use OKLCH/CSS variables where useful; avoid raw pure black/white defaults.

## 2A. Curated design system references
- If payload has `design_reference_pack`, it is the active design system contract.
- Use the pack roles literally: structure = composition, typography = type voice,
  color = palette, motion = reveal cadence, spacing = density/rhythm.
- Do not load or imitate all extracted systems at once. The pack is the curated
  slice; everything outside it is reference archive, not runtime instruction.
- The chosen slugs must affect the HTML/CSS visibly through layout, font scale,
  color tokens, media treatment, section spacing, and motion hooks.
- Treat color as a semantic system, not decoration: page background, surface,
  elevated surface, primary text, muted text, border, accent, CTA, glow and
  focus ring must have clear roles.
- Pick a color strategy before colors: restrained, committed, full palette or
  drenched. Brand/campaign pages should usually be committed or full palette;
  do not hedge into beige/gray sameness.
- Use brand-reference packs as mechanics, not imitation: Apple = restraint and
  spacing, Nike = kinetic contrast, BMW = engineered contrast, Spotify =
  saturated confidence, Linear = precise minimalism, Starbucks = organic trust.
- Contrast is non-negotiable. Body text must remain readable on every surface,
  and muted text cannot become gray-on-gray.

## 2B. Awwwards-grade craft mode
- Treat the first viewport as a campaign scene, not a centered brochure block.
  It needs a dominant visual system: oversized type, layered media, strong
  crop, spatial depth, local proof and one unmistakable conversion path.
- Build a brand-specific visual signature per business: palette from the
  business category, typography with display/body contrast, unique rhythm and
  one memorable composition move. Default blue SaaS UI is not acceptable.
- Every color/font/background choice must be defensible from the business
  scene and archetype. Do not let the wrapper, Tailwind defaults or category
  reflex choose black, white, blue, Inter or rounded cards for you.
- Backgrounds should feel like a designed surface: editorial photo crop,
  tinted paper, kinetic light, fine grid, diagonal slab, soft organic field or
  material texture. A flat dark fill plus white cards is not enough.
- Prefer editorial storytelling over generic section labels: manifesto,
  proof, process, objections, location and final CTA should feel connected.
- Use immersive motion hooks without hiding content: scroll progress, reveal
  cadence, parallax on media/depth layers, mask/line reveals and staggered
  proof blocks. Motion must be interruptible, transform/opacity-only and safe
  under reduced motion.
- Do not chase decoration. Premium means hierarchy, art direction, contrast,
  imagery, copy restraint, spacing and a decisive CTA working together.
- For local services, keep conversion practical: phone/WhatsApp/address/proof
  stay visible while the page gets agency-level craft.

## 3. Taste rules
- Make one memorable visual move in the hero.
- At least two sections must break default grid behavior.
- Avoid centered generic hero copy unless the business context strongly asks
  for it.
- Avoid `bg-white rounded-xl/2xl shadow-lg` as a repeated answer. If cards are
  necessary, vary geometry, scale, crop, typography, borders or rhythm.
- Nav and footer must belong to the same visual system as the page; never ship
  a generic white navbar or black footer just because it is safe.
- If data is thin, design with restraint and strong CTA, not fake services.
- Footer is part of the composition: brand, city, phone, address when present,
  hours when present, CTA, and current year.

## 3A. BOLD_ENERGY / academia direction
When visual_dna.archetype is BOLD_ENERGY, the page must feel like a premium
training campaign, not a local directory page:
- Use a black cinematic base, red electric accent, warm white display text,
  charcoal surfaces, and very little gray.
- Hero: full-viewport dark image/texture layer, heavy overlay, giant condensed
  uppercase headline, one red emotional line, primary red CTA, secondary ghost
  CTA, and 3 dark stat slabs near the fold.
- Use outline display text as a background echo behind one headline word.
- Use diagonal/oblique accents, thin red rules, z-index layering, and cropped
  media. Avoid clean centered hero layouts.
- Typography should resemble an athletic poster: condensed, tight, italic or
  skewed on selected words. Body remains readable and short.
- Include an aggressive manifesto section after hero: short stacked lines,
  red emphasis, image on the side, and a clear CTA.
- Cards, when necessary, must be dark editorial panels with image crops and
  numeric labels, not white cards or rounded SaaS cards.
- Motion hooks are mandatory in hero and first three sections: data-reveal,
  data-parallax, mask-reveal, card-stagger, line-draw.
- Never use pastel, wellness, corporate blue, beige, or generic black footer
  for BOLD_ENERGY.

## 4. UX and conversion
- Mobile first. No horizontal scroll. Touch targets at least 44px.
- One primary CTA per viewport area. Secondary links stay visually subordinate.
- Use real contact/address visibly. Local trust beats vague marketing.
- Keep body text readable: 16px+, 1.5 line-height, line length under 75ch.
- Use SVG/icons consistently if used at all.

## 5. Motion
- Motion must serve orientation, reveal, rhythm, or conversion.
- Use data-reveal and data-parallax hooks so FraLib's wrapper can animate.
- Animate transform and opacity only. Never animate width, height, top, left,
  or transition: all.
- Include staggered reveals, scroll progress, one scroll-linked/parallax
  composition and at least one mask/line reveal moment.
- Respect reduced motion. Do not duplicate external GSAP/Lenis scripts; FraLib
  injects the motion runtime.

## 6. Truth policy
- Use only facts in the payload.
- No invented services, equipe, equipamentos, preços, discounts, founding
  history, guarantees, transformation claims, or "premium" claims without proof.
- Reviews can prove sentiment, not operational capabilities.
- If no confirmed service list exists, do not create a standalone services
  section. Merge one short confirmation note into contact/about and keep the
  visual rhythm intact.
"""

