---
name: emil-design-eng
description: Compact motion and interface engineering principles inspired by high-quality product animation craft.
---

# Emil Design Engineering Runtime Pack

Motion should clarify hierarchy and make the page feel alive without stealing attention.

## Motion Rules

- Animate entrance in layers: background/media first, headline second, supporting copy third, CTA last.
- Use short stagger windows, roughly 80-140ms between related elements.
- Prefer opacity + translate + clip/mask reveals over noisy bouncing effects.
- Use parallax sparingly on dominant media only; never make text hard to read.
- Respect reduced motion and avoid essential information hidden behind animation.

## Engineering Rules

- Stable layout first: fixed aspect ratios for media, predictable section spacing, no layout shift on hover.
- Motion classes should be reusable: `data-reveal`, `data-stagger`, `data-parallax`, `mask-reveal`.
- Do not add heavy libraries unless already part of the renderer contract.
