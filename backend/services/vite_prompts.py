"""Vite/React system prompts and user prompt composers."""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════
# POLE TOKENS BLOCK - Blocos Líquidos
# ═══════════════════════════════════════════════════════════════════

def _build_pole_tokens_block(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.x: injeta tokens de polo estético para Blocos Líquidos.

    Se facts contém 'pole', adiciona um bloco de tokens CSS que o LLM
    deve usar para gerar o design correto.

    Args:
        facts: Facts do builder com pole info

    Returns:
        String com tokens de polo ou string vazia
    """
    if not facts:
        return ""

    pole = facts.get("pole")
    if not pole:
        return ""

    pole_heat = facts.get("pole_heat", 0.5)
    pole_display_mode = facts.get("pole_display_mode", "default")
    pole_tokens = facts.get("pole_tokens", {})

    # Mapear polo para tokens CSS
    css_tokens = []
    for key, value in pole_tokens.items():
        css_key = key.replace("_", "-")
        if isinstance(value, bool):
            css_tokens.append(f"  --{css_key}: {'true' if value else 'false'};")
        elif isinstance(value, (int, float)):
            css_tokens.append(f"  --{css_key}: {value};")
        else:
            css_tokens.append(f"  --{css_key}: {value};")

    css_block = "\n".join(css_tokens) if css_tokens else ""

    # Mapear polo para descrição
    pole_descriptions = {
        "soft": "SOFT (Orgânico/Acolhedor) - Bordas 40px, serifada, motion lento, cores pastéis",
        "bold": "BOLD (Agressivo/Impacto) - Zero radius, UPPERCASE, text-stroke, motion rápido, overlap",
        "corporate": "CORPORATE (Sério/Seguro) - Radius 6px, sans-serif, grid alinhado, motion discreto",
        "minimal": "MINIMAL (Moderno/Limpo) - Radius 12px, geométrica, glassmorphism, neon glow",
    }
    pole_desc = pole_descriptions.get(pole, f"POLO {pole.upper()}")

    return f"""

═══════════════════════════════════════════════════════════════════════════════
LIQUID DESIGN SYSTEM - POLO: {pole.upper()}
═══════════════════════════════════════════════════════════════════════════════

DESIGN HEAT: {pole_heat:.1f} | DISPLAY MODE: {pole_display_mode}

{pole_desc}

CSS TOKENS TO USE (obedeça rigorosamente):
{css_block or "/* Use default tokens */"}

RULES FOR POLO {pole.upper()}:
{_get_pole_rules(pole)}

═══════════════════════════════════════════════════════════════════════════════
"""


def _get_pole_rules(pole: str) -> str:
    """Retorna as regras específicas do polo para o LLM seguir."""
    rules = {
        "soft": """- Border radius: 40px (cards, botões, imagens)
- Font: Playfair Display ou serif elegante
- Text transform: capitalize (primeira letra maiúscula)
- Espaçamento: Generoso (py-32, gap-12, p-8)
- Shadows: Difusas e coloridas (blur alto)
- Motion: Lento e suave (600ms+, ease)
- Cores: Pastéis (roxo, rosa, pêssego)
- NUNCA: radius 0, UPPERCASE, text-stroke, overlap""",
        "bold": """- Border radius: 0px (cortante/agressivo)
- Font: Anton/Impact ou bold condensed
- Text transform: UPPERCASE + ITALIC
- Espaçamento: Apertado (py-4, gap-2, p-4)
- Shadows: Offset brutas (8px 8px 0)
- Motion: Rápido e intenso (150ms, spring)
- Overlap: -80px entre seções
- Text-stroke: -webkit-text-stroke: 2px var(--primary)
- Skew: transform: skewX(-5deg)
- NUNCA: radius > 0, centered layouts, safe designs""",
        "corporate": """- Border radius: 6px (subtle)
- Font: Inter ou sans-serif profissional
- Text transform: capitalize
- Espaçamento: Padrão (py-16, gap-8, p-6)
- Shadows: Sutis e monocromáticas
- Motion: Discreto (300ms, ease)
- Grid: Alinhado e centrado
- Cores: Azul/cinza corporativo
- NUNCA: decoration excessiva, overlap, text-stroke""",
        "minimal": """- Border radius: 12px (geométrico)
- Font: Space Grotesk ou geométrica/mono
- Text transform: lowercase
- Espaçamento: Preciso (py-20, gap-6)
- Shadows: Neon/glow (box-shadow colorido)
- Motion: Baseado em scroll (400ms)
- Efeitos: Glassmorphism (backdrop-blur)
- Grid: Bento grid ou assimétrico
- Slight skew: 2deg
- NUNCA: decorative excess, pill shapes, slow animations""",
    }
    return rules.get(pole, rules["corporate"])


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
    motion_runtime.js e vite_modules.

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


def _build_gsap_code_block() -> str:
    """Sprint 12.12: bloco de código GSAP REAL para o Vite caroço.

    Em vez de só listar data-attributes (que ja existe em _build_motion_pack_block),
    este bloco injeta snippets REAIS de gsap.from(), ScrollTrigger, useGSAP,
    Lenis, data-magnetic com refs React. O LLM sabe COMO escrever, nao so O QUE.
    """
    return """

GSAP + SCROLLTRIGGER + LENIS — CODIGO REAL (Sprint 12.12 — NAO INVENTE OUTRO):
Abaixo estao os snippets reais ja usados no runtime FraLib. Use estes padroes
exatos. NAO invente helper de animacao proprio.

```tsx
// src/hooks/useReveal.ts — padrao para reveals on-scroll
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(ScrollTrigger, useGSAP);

export function useReveal<T extends HTMLElement>(opts?: gsap.TweenVars) {
  const ref = useRef<T>(null);
  useGSAP(() => {
    if (!ref.current) return;
    gsap.from(ref.current, {
      y: 24,
      opacity: 0,
      duration: 0.9,
      ease: 'power3.out',
      ...opts,
      scrollTrigger: { trigger: ref.current, start: 'top 85%', once: true },
    });
  }, []);
  return ref;
}
```

```tsx
// src/components/HeroParallax.tsx — padrao para hero com parallax
import { useRef } from 'react';
import { useGSAP } from '@gsap/react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

export function HeroParallax({ imageUrl, children }: { imageUrl: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    gsap.to(ref.current, {
      yPercent: 30,
      ease: 'none',
      scrollTrigger: { trigger: ref.current, scrub: true, start: 'top top', end: 'bottom top' },
    });
  }, []);
  return (
    <section ref={ref} className="relative min-h-[92svh] overflow-hidden">
      <img src={imageUrl} className="absolute inset-0 w-full h-full object-cover scale-110" alt="" loading="eager" decoding="async" />
      <div className="relative z-10">{children}</div>
    </section>
  );
}
```

```tsx
// src/components/MagneticCTA.tsx — data-magnetic real com React ref
import { useRef, type FC, type ReactNode } from 'react';

export const MagneticCTA: FC<{ children: ReactNode; className?: string }> = ({ children, className }) => {
  const ref = useRef<HTMLButtonElement>(null);
  return (
    <button
      ref={ref}
      data-magnetic
      onMouseMove={(e) => {
        const rect = ref.current?.getBoundingClientRect();
        if (!rect) return;
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        ref.current!.style.transform = `translate(${x * 0.25}px, ${y * 0.25}px)`;
      }}
      onMouseLeave={() => { if (ref.current) ref.current.style.transform = ''; }}
      className={className}
    >
      {children}
    </button>
  );
};
```

REGRAS DE USO (caroço NAO PODE violar):
1. SEMPRE importe de 'gsap', 'gsap/ScrollTrigger', '@gsap/react' e 'lenis' — ja estao em package.json.
2. SEMPRE chame `gsap.registerPlugin(...)` antes de usar ScrollTrigger.
3. Use `useGSAP` (nao `useLayoutEffect`) — limpa animacoes automaticamente em unmount.
4. Para Lenis: `import Lenis from 'lenis'; new Lenis();` no main.tsx.
5. NAO escreva handlers manuais de scroll (window.addEventListener) — use ScrollTrigger.
6. Anime APENAS opacity + transform (GPU). NAO anime width/height/top/left.
7. Se um efeito pode ser feito com `data-reveal` (CSS) ou `motion/react` (sem GSAP), PREFIRA — GSAP e para casos complexos (scrub, timeline, parallax).
"""


def _build_lead_briefing_block(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.12: bloco de briefing REAL do lead para o Vite caroço.

    Injeta no SYSTEM PROMPT:
    - Dados reais do negocio (nome, cidade, telefone, rating)
    - Services confirmados (NAO inventar)
    - Horarios reais
    - Keywords SEO validadas
    - JSON-LD LocalBusiness pronto pra colar em <head>
    - Fotos aprovadas (URLs reais ja validadas)
    """
    if not facts:
        return ""

    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    seo = facts.get("seo") if isinstance(facts.get("seo"), dict) else {}
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}

    name = business.get("name") or business.get("business_name") or ""
    segment = business.get("segment") or business.get("segmento") or ""
    city = business.get("city") or business.get("cidade") or ""
    phone = business.get("phone") or business.get("whatsapp") or ""
    address = business.get("address") or business.get("endereco") or ""
    rating = business.get("rating") or ""
    reviews = business.get("reviews_count") or business.get("total_avaliacoes") or ""

    services = (
        business.get("services") or business.get("servicos")
        or facts.get("services") or []
    )
    if isinstance(services, str):
        services = [s.strip() for s in services.split(",") if s.strip()]

    hours = business.get("hours") or business.get("horarios") or facts.get("horarios") or ""

    primary_terms = (
        seo.get("primary_terms") or facts.get("seo_keywords") or facts.get("keywords") or []
    )
    if isinstance(primary_terms, str):
        primary_terms = [k.strip() for k in primary_terms.split(",") if k.strip()]

    photos = (
        media.get("photos") or business.get("photos") or facts.get("photos") or []
    )
    if isinstance(photos, str):
        photos = [p.strip() for p in photos.split(",") if p.strip()]

    # Se nao tem name, nao ha briefing
    if not name:
        return ""

    services_block = (
        "\n".join(f"  - {s}" for s in services[:8])
        if services else "  (servicos nao confirmados — NAO inventar cards de servicos)"
    )

    photos_block = (
        "\n".join(f"  - {p}" for p in photos[:6] if p)
        if photos else "  (sem fotos aprovadas — usar editorial stock com disclaimer)"
    )

    primary_terms_block = (
        ", ".join(str(k) for k in primary_terms[:8] if k)
        if primary_terms else "(sem keywords validadas)"
    )

    # JSON-LD dinâmico por nicho (advogado→LegalService, restaurante→Restaurant, etc.)
    try:
        from backend.config.nicho_registry import get_schema_type
        schema_type = get_schema_type(segment)
    except Exception:
        schema_type = "LocalBusiness"
    json_ld = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": name,
        "telephone": phone,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": address,
            "addressLocality": city,
        },
    }
    if rating:
        json_ld["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": rating,
            "reviewCount": reviews or 0,
        }

    import json as _json
    json_ld_str = _json.dumps(json_ld, ensure_ascii=False, indent=2)

    # Sprint 14.x: Extrair cores do briefing do usuário
    # Prioridade: paleta_cores (NichoBriefing) > color_palette (DesignerPRD)
    _paleta = None
    if facts:
        _paleta = facts.get("paleta_cores") or facts.get("color_palette") or {}
        # Tentar em sub-chaves
        if not _paleta:
            _nicho = facts.get("nicho_briefing")
            if isinstance(_nicho, dict):
                _paleta = _nicho.get("paleta_cores") or _nicho.get("color_palette") or {}
            elif hasattr(_nicho, "paleta_cores"):
                _paleta = getattr(_nicho, "paleta_cores", {}) or {}

    if _paleta and _paleta.get("primary"):
        colors_block = f"""
CORES SOLICITADAS PELO USUÁRIO (OBRIGATÓRIO USAR ESTAS CORES):
- Primary: {_paleta.get('primary', '')}
- Secondary: {_paleta.get('secondary', '')}
- Accent: {_paleta.get('accent', '')}
- Background: {_paleta.get('background', '')}
- Text: {_paleta.get('text', '')}
ESSAS CORES FORAM SOLICITADAS PELO USUÁRIO NO FORMULÁRIO — RESPEITE-AS.
"""
    else:
        colors_block = ""

    return f"""

LEAD BRIEFING — DADOS REAIS CONFIRMADOS (Sprint 12.12 — NAO INVENTAR):
Use APENAS os dados abaixo. Se um campo estiver vazio, NAO crie ficticios.

Business: {name}
Segmento: {segment or '(nao informado)'}
Cidade: {city or '(nao informada)'}
Telefone/WhatsApp: {phone or '(nao informado)'}
Endereco: {address or '(nao informado)'}
Rating: {rating or '(nao informado)'} | Reviews: {reviews or '(nao informado)'}

{colors_block}

SERVICOS CONFIRMADOS (use EXATAMENTE estes, NAO inventar):
{services_block}

HORARIOS:
{hours or '(nao informado — NAO inventar horarios)'}

KEYWORDS SEO PRIORITARIAS (distribuir com naturalidade):
{primary_terms_block}

FOTOS APROVADAS (use estas URLs - ja validadas pelo briefing):
{photos_block}

JSON-LD PRONTO PARA COLAR EM <script type="application/ld+json">:
```json
{json_ld_str}
```
"""


def _build_caroço_block(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.12: o CAROÇO unificado do Vite.

    Agrega TUDO o que o sistema injeta para o LLM Vite/React, em um unico bloco
    rico. Chamada canonica. Antes era VITE_REACT_SYSTEM_PROMPT_FOOT estatico;
    agora aceita `facts` para receber briefing real do lead.

    Ordem importa:
      1. Few-shot (bons exemplos primeiro)
      2. SHADCN/UI (biblioteca preferida)
      3. Premium contract (regras Awwwards + AIDA/PAS + anti-patterns)
      4. Visual direction (archetype por nicho)
      5. Motion pack (12 hooks data-attributes)
      6. GSAP real code (snippets executaveis)
      7. Mobile-first (clamp, 44px, no overflow)
      8. Lead briefing REAL (dados do briefing + JSON-LD)
      9. Modal obrigatorio por nicho
     10. Blocos pre-fabricados (composicao nao codar tudo)
     11. No cross-segment contamination (musculacao em barbearia reprova)
    """
    return (
        _build_few_shot_prompt()
        + _build_shadcn_block()
        + _build_premium_contract_block()
        + _build_visual_direction_block()
        + _build_pole_tokens_block(facts)  # Blocos Líquidos - Tokens de polo
        + _build_motion_pack_block()
        + _build_gsap_code_block()
        + _build_mobile_first_block()
        + _build_lead_briefing_block(facts)
        + _build_nicho_modal_block(facts)
        + _build_nicho_blocks_block(facts)
        + _build_no_contamination_block(facts)
    )


def _build_vite_react_system_prompt_with_facts(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.12: prompt FINAL com briefing real injetado."""
    caroco = _build_caroço_block(facts)
    return VITE_REACT_SYSTEM_PROMPT_HEAD + caroco + VITE_REACT_SYSTEM_PROMPT_TAIL

# Modal configuration por nicho (Booking/CTA/Orcamento/Agendamento)
# DEPRECATED (Sprint 12.x): esta constante existe apenas como fallback legacy.
# Fonte unica de verdade: backend/config/nicho_registry.py::get_modal_config()
# Este dict NAO e mais usado pelo codigo de producao (_build_nicho_modal_block
# usa nicho_registry), mas mantemos para nao quebrar imports externos.
NICHO_MODAL_CONFIG: dict[str, dict[str, str]] = {
    "barbearia": {
        "title": "Agendar Horario",
        "cta_button": "Agendar pelo WhatsApp",
        "fields": "Nome, Telefone, Servico (Corte/Barba/Sobrancelha), Data, Horario",
        "submit_action": "Enviar para WhatsApp com mensagem pre-formatada",
    },
    "academia": {
        "title": "Matricule-se Agora",
        "cta_button": "Falar com Consultor",
        "fields": "Nome, Email, Telefone, Modalidade (Musculacao/Crossfit/Spinning/Yoga), Horario Preferido",
        "submit_action": "Enviar formulario + redirecionar para WhatsApp",
    },
    "restaurante": {
        "title": "Reservar Mesa",
        "cta_button": "Reservar Mesa",
        "fields": "Nome, Telefone, Data, Horario, Numero de Pessoas, Observacoes",
        "submit_action": "Confirmar reserva via WhatsApp",
    },
    "clinica": {
        "title": "Agendar Consulta",
        "cta_button": "Marcar Consulta",
        "fields": "Nome Completo, Telefone, Especialidade, Convenio (Particular/Unimed/Amil), Periodo Preferido",
        "submit_action": "Confirmar consulta por WhatsApp",
    },
    "imobiliaria": {
        "title": "Tenho Interesse",
        "cta_button": "Quero Visitar",
        "fields": "Nome, Email, Telefone, Tipo do Imovel, Faixa de Valor, Periodo para Mudar",
        "submit_action": "Enviar para WhatsApp com imovel de interesse",
    },
    "default": {
        "title": "Fale Conosco",
        "cta_button": "Enviar Mensagem",
        "fields": "Nome, Email, Telefone, Mensagem",
        "submit_action": "Enviar formulario via WhatsApp ou email",
    },
}


# Helper de compatibilidade: ainda retorna o dict legacy se algum codigo externo
# precisar (leitura, nao escrita). NAO USE EM CODIGO NOVO.
def _get_legacy_modal_config() -> dict[str, dict[str, str]]:
    """DEPRECATED: use backend.config.nicho_registry.get_modal_config() em codigo novo."""
    return NICHO_MODAL_CONFIG


def _build_nicho_modal_block(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.11: injeta regra obrigatória de <Modal> por nicho (booking/CTA).

    Sprint 12.x: migrado para nicho_registry (fonte única de verdade).
    Aceita aliases e sub-nichos automaticamente.

    Args:
        facts: dict com 'business.segment' ou 'segmento' (opcional)

    Returns:
        Bloco de texto que força o LLM a gerar <Dialog> shadcn no projeto Vite/React
    """
    # Sprint 12.x: usar nicho_registry em vez de NICHO_MODAL_CONFIG
    try:
        from backend.config.nicho_registry import get_modal_config, resolve_polo_for_lead
    except ImportError:
        # Fallback para NICHO_MODAL_CONFIG se registry indisponível
        nicho = "default"
        if facts:
            seg = (facts.get("business") or {}).get("segment") or facts.get("segmento") or ""
            seg_lower = str(seg).lower()
            for key in NICHO_MODAL_CONFIG:
                if key in seg_lower:
                    nicho = key
                    break
        config = NICHO_MODAL_CONFIG[nicho]
        return _render_nicho_modal_block(nicho, config)

    # Detectar nicho e subnicho
    segmento = ""
    subnicho = ""
    if facts:
        business = facts.get("business") or {}
        segmento = (
            business.get("segment")
            or facts.get("segmento")
            or facts.get("segment")
            or ""
        )
        subnicho = (
            business.get("subniche")
            or facts.get("subnicho")
            or ""
        )

    # Buscar config do nicho via registry (ModalConfig tem .title, .cta_button, etc)
    modal = get_modal_config(segmento)
    nicho_resolvido = resolve_polo_for_lead(segmento, subnicho)

    # Converter ModalConfig para dict compatível com template
    config = {
        "title": modal.title,
        "cta_button": modal.cta_button,
        "fields": ", ".join(modal.fields),
        "submit_action": modal.submit_action,
    }
    return _render_nicho_modal_block(segmento or "default", config)


def _render_nicho_modal_block(nicho: str, config: dict) -> str:
    """Renderiza o bloco de texto do modal com o template atual."""
    return f"""

MODAL OBRIGATORIO POR NICHO (Sprint 12.11 — NAO PULE):
Todo projeto Vite/React DEVE incluir um componente de conversao no path
'BookingModal' ou 'ContactModal' usando o shadcn <Dialog>.

Configuracao para nicho '{nicho}':
- Title do modal: {config['title']}
- Botao CTA primario: {config['cta_button']}
- Campos do formulario: {config['fields']}
- Acao ao submit: {config['submit_action']}

CODIGO OBRIGATORIO (use este padrao):

```tsx
// src/components/BookingModal.tsx
import {{ useState }} from 'react';
import {{ Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger }} from '@/components/ui/dialog';
import {{ Button }} from '@/components/ui/button';
import {{ Input }} from '@/components/ui/input';
import {{ Textarea }} from '@/components/ui/textarea';

export function BookingModal() {{
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={{open}} onOpenChange={{setOpen}}>
      <DialogTrigger asChild>
        <Button size="lg" className="..." data-magnetic>
          {{config['cta_button']}}
        </Button>
      </DialogTrigger>
      <DialogContent
        className="sm:max-w-[500px] bg-zinc-950"
        style={{{{ borderColor: 'var(--fralib-accent)', borderOpacity: 0.3 }}}}
      >
        <DialogHeader>
          <DialogTitle
            className="text-2xl font-black uppercase tracking-tight"
            style={{{{ color: 'var(--fralib-accent)' }}}}
          >
            {{config['title']}}
          </DialogTitle>
          <DialogDescription style={{{{ color: 'var(--fralib-accent)', opacity: 0.6 }}}}>
            Preencha os dados abaixo e entraremos em contato em ate 2h.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4">
          <Input placeholder="Nome completo" required />
          <Input type="tel" placeholder="Telefone (WhatsApp)" required />
          {{/* outros campos especificos do nicho */}}
          <Textarea placeholder="Observacoes (opcional)" />
          <Button
            type="submit"
            size="lg"
            className="w-full text-zinc-950"
            style={{{{
              backgroundColor: 'var(--fralib-accent)',
              borderColor: 'var(--fralib-accent)',
            }}}}
          >
            {{config['cta_button']}}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}}
```

REGRA: O componente BookingModal DEVE ser:
1. Criado em src/components/BookingModal.tsx
2. Importado em src/pages/Index.tsx
3. Renderizado no minimo 2x na pagina (CTA no hero + CTA no final)
4. **Usar `var(--fralib-accent)` para o CTA primario, titulo e borda** (nao usar cores hardcoded como bg-amber-500, bg-blue-500, etc). A cor acompanha o polo do site.
4. Aberto por botao com data-magnetic no hero

VALIDACAO: o studio falha o build se nao houver BookingModal.tsx no projeto.
"""


def _build_nicho_blocks_block(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.11: instrui LLM a montar via BLOCOS pré-fabricados (não codar tudo).

    Blocos disponíveis:
    - HeroBlock (1 linha de chamada)
    - TrustBar (logos)
    - Services (cards)
    - Gallery (imagens)
    - Testimonials
    - Pricing/Planos
    - Faq (accordion)
    - ContactCTA
    - Footer
    - BookingModal (sprint 12.11)
    """
    return """

BLOCOS PRÉ-FABRICADOS (Sprint 12.11 — USE ESTES, NAO CODIFIQUE TUDO):
NÃO invente cada div, section, button do zero. FraLib oferece BLOCOS
pré-fabricados que você COMPOEM no src/pages/Index.tsx:

```tsx
// src/pages/Index.tsx — exemplo de composicao com blocos
import { Navbar } from '@/components/Navbar';
import { HeroBlock } from '@/components/HeroBlock';
import { TrustBar } from '@/components/TrustBar';
import { ServicesGrid } from '@/components/ServicesGrid';
import { GalleryMosaic } from '@/components/GalleryMosaic';
import { Testimonials } from '@/components/Testimonials';
import { Faq } from '@/components/Faq';
import { BookingModal } from '@/components/BookingModal';
import { ContactCta } from '@/components/ContactCta';
import { Footer } from '@/components/Footer';

export default function Index() {
  return (
    <main>
      <Navbar />
      <HeroBlock />              {/* hero com video ou imagem + CTA + BookingModal */}
      <TrustBar />                {/* logos de clientes/provas sociais */}
      <ServicesGrid />            {/* 3-6 servicos em cards */}
      <GalleryMosaic />           {/* mosaico de fotos reais */}
      <Testimonials />            {/* 3 depoimentos com avatar+nome+5 estrelas */}
      <Faq />                     {/* 4-6 perguntas com <details> */}
      <ContactCta />              {/* CTA final + BookingModal */}
      <Footer />                   {/* LGPD + contato + redes sociais */}
    </main>
  );
}
```

BLOCOS DISPONIVEIS (cada um é 1 arquivo .tsx em src/components/):
- Navbar.tsx        → menu sticky com CTA booking
- HeroBlock.tsx     → 1 viewport de altura, video/imagem, copy, CTA
- TrustBar.tsx      → logos/provas sociais (5-7)
- ServicesGrid.tsx  → 3-6 servicos em Card shadcn com Icon
- GalleryMosaic.tsx → 6-12 fotos com data-reveal stagger
- Testimonials.tsx  → 3 depoimentos reais ficticios (com disclaimer)
- Faq.tsx           → 4-6 <details> com Q&A especificos do nicho
- ContactCta.tsx    → CTA grande + BookingModal
- Footer.tsx        → LGPD banner + contato + redes sociais
- BookingModal.tsx  → Modal obrigatorio (Sprint 12.11)

FOCO NO CONTEUDO, NÃO EM ESTILIZAR CADA ELEMENTO:
- 80% do codigo = importar blocos + passar props
- 20% = ajustar copy/dados do nicho especifico
- OBRIGATORIO: src/index.css com @import tailwindcss e tokens
- OBRIGATORIO: src/App.tsx (router) + src/main.tsx (entry)
- OBRIGATORIO: index.html (entry HTML com <div id="root">)
"""


def _build_no_contamination_block(facts: dict[str, Any] | None = None) -> str:
    """Sprint 12.11: guard contra cross-segment contamination (musculacao em barbearia)."""
    return """

ZERO CROSS-SEGMENT CONTAMINATION (Sprint 12.11 — REGRA RIGIDA):
O LLM NAO pode inventar termos de outro nicho. Exemplos PROIBIDOS:
- Site de barbearia: NAO pode mencionar musculacao, crossfit, spinning, academia, plano alimentar
- Site de academia: NAO pode mencionar corte, barba, platinado, pigmentacao
- Site de restaurante: NAO pode mencionar corte, agendamento, receita
- Site de clinica: NAO pode mencionar prato, menu, reserva
- Site de imobiliária: NAO pode mencionar consulta, procedimento

REGRA: Use APENAS vocabulario, servicos e copywriting do segmento:
- {{business.segment}} ou {{segmento}}
- Se contexto nao fornece, use apenas termos GENERICOS (ex: 'servico', 'cliente', 'equipe', 'profissional')

FALHA: build quebra com 'contaminated' + {{segment_key}} se detectar termos de outro nicho.
"""


VITE_REACT_SYSTEM_PROMPT_FOOT = (
    _build_few_shot_prompt()
    + _build_shadcn_block()
    + _build_premium_contract_block()
    + _build_visual_direction_block()
    + _build_motion_pack_block()
    + _build_mobile_first_block()
    + _build_nicho_modal_block()
    + _build_nicho_blocks_block()
    + _build_no_contamination_block()
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
