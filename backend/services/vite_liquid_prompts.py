"""
============================================================================
FRA LIB - VITE LIQUID PROMPTS
============================================================================
Prompts para LLM com blocos líquidos - Sistema de Design Camaleão

Este módulo fornece:
1. TEMPERATURE_CONFIG - Configuração de temperatura por agente
2. build_liquid_system_prompt() - Prompt principal do sistema líquido
3. build_hero_prompt() - Prompt específico para Hero Section
4. build_services_prompt() - Prompt para seção de serviços
5. get_pole_system_prompt() - Prompt base por polo

Temperatura:
- agente_variacao: 0.7-0.8 (alta criatividade)
- arquiteto_mestre: 0.3-0.4 (precisão)
- vite_react_renderer: 0.5-0.6 (equilíbrio)

============================================================================
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE TEMPERATURA POR AGENTE
# ═══════════════════════════════════════════════════════════════════════════

TEMPERATURE_CONFIG: dict[str, dict[str, Any]] = {
    "agente_variacao": {
        "temperature": 0.7,
        "reasoning": "Alta criatividade para misturar variantes de forma inesperada",
        "description": "Para agente de variação - usado quando gerando创意 options",
    },
    "agente_variacao_max": {
        "temperature": 0.8,
        "reasoning": "Criatividade máxima para nichos de alta energia (academia, eventos)",
        "description": "Para agente de variação com polo BOLD - máximo creativity",
    },
    "arquiteto_mestre": {
        "temperature": 0.4,
        "reasoning": "Precisão no JSON/PRD - não pode quebrar sintaxe",
        "description": "Para arquiteto mestre - precisão máxima",
    },
    "vite_react_renderer": {
        "temperature": 0.5,
        "reasoning": "Equilíbrio entre criação e fidelidade ao design system",
        "description": "Para renderer - equilíbrio",
    },
    "vite_react_renderer_bold": {
        "temperature": 0.6,
        "reasoning": "Mais criatividade para sites de alto impacto",
        "description": "Para renderer com polo BOLD - mais ousadia",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PROMPTS BASE POR POLO
# ═══════════════════════════════════════════════════════════════════════════

POLE_SYSTEM_PROMPTS: dict[str, str] = {
    "soft": """
You are generating a SOFT/ORGANIC website design.

DESIGN RULES:
- Border radius: 40px (very rounded)
- Font: Playfair Display (serif), capitalize, elegant
- Spacing: Generous (py-32, gap-12)
- Shadows: Diffuse and colored (purple tints)
- Motion: Slow and smooth (600ms+)
- Colors: Pastel (purple, pink accents)

MUST USE:
- rounded-[40px] or more on cards and buttons
- font-serif for headings
- text-transform: capitalize
- Generous whitespace
- Soft shadows with color tints

NEVER USE:
- Sharp corners (border-radius: 0)
- UPPERCASE text
- Fast animations
- Stark shadows
- High contrast aggressive colors
""",
    "bold": """
You are generating a BOLD/IMPACT website design.

DESIGN RULES:
- Border radius: 0px (sharp, aggressive)
- Font: Anton (impact), UPPERCASE, ITALIC
- Spacing: Tight (py-4, gap-2)
- Shadows: Harsh offset (8px 8px 0)
- Motion: Fast and intense (150ms, spring)
- Colors: Vibrant (red, yellow accents)

MUST USE:
- rounded-none on buttons and cards
- font-bold or Anton for headings
- text-transform: uppercase
- transform: skewX(-5deg) on headlines
- Negative margins for overlap
- Text-stroke: -webkit-text-stroke: 2px
- Fast spring animations

YOU ARE ALLOWED TO:
✅ Create overlapping sections (margin-top: -80px)
✅ Use skew transformations
✅ Use text-stroke for outline text
✅ Use giant fonts (>50vw for hero)
✅ Use offset shadows (8px 8px 0)
✅ Be aggressive and impactful

NEVER USE:
- Rounded corners
- Small fonts
- Safe centered layouts
- Soft colors
- Slow animations
""",
    "corporate": """
You are generating a CORPORATE/PROFESSIONAL website design.

DESIGN RULES:
- Border radius: 6px (subtle)
- Font: Inter (sans-serif), Medium weight
- Spacing: Standard (py-16, gap-8)
- Shadows: Subtle and monochrome
- Motion: Discreet (300ms, ease)
- Colors: Blue/gray corporate palette

MUST USE:
- rounded-md (6px) on elements
- font-medium or font-semibold
- Clean grid alignment
- Professional spacing
- Subtle shadows

NEVER USE:
- Extreme radius (>12px)
- Decorative fonts
- Loud colors
- Overlapping elements
- Aggressive animations
""",
    "minimal": """
You are generating a MINIMAL/TECH website design.

DESIGN RULES:
- Border radius: 12px (geometric)
- Font: Space Grotesk (geometric), lowercase
- Spacing: Precise (py-20, gap-6)
- Shadows: Neon/glow effects
- Motion: Scroll-based (400ms)
- Colors: Tech blue/cyan palette
- Effect: Glassmorphism

MUST USE:
- rounded-xl (12px) on elements
- font-mono or geometric fonts
- lowercase text for headings
- Glass effect (backdrop-blur)
- Neon glow shadows
- Asymmetric bento grids

YOU ARE ALLOWED TO:
✅ Use glassmorphism
✅ Use subtle skew (2deg)
✅ Use overlap (-40px)
✅ Use neon glow effects
✅ Create bento grid layouts

NEVER USE:
- Excessive decoration
- Round-full (pill) shapes
- Serif fonts
- Slow animations
""",
}


# ═══════════════════════════════════════════════════════════════════════════
# PROMPTS DE SEÇÃO
# ═══════════════════════════════════════════════════════════════════════════


def build_hero_prompt(pole: str, business_name: str, tagline: str = "") -> str:
    """
    Gera prompt específico para Hero Section.

    Args:
        pole: Polo estético (soft, bold, corporate, minimal)
        business_name: Nome do negócio
        tagline: Tagline do negócio

    Returns:
        Prompt formatado para hero
    """
    system = POLE_SYSTEM_PROMPTS.get(pole, POLE_SYSTEM_PROMPTS["corporate"])

    hero_templates = {
        "soft": f"""
Create a SOFT Hero Section for: {business_name}
Tagline: {tagline}

Use these exact tokens:
- Layout: centered, generous whitespace
- Font: serif/Playfair Display
- Border radius: 40px+
- Image: rounded-[40px] with soft shadow
- CTA: rounded-full button

Example structure:
```tsx
<section className="flex flex-col items-center justify-center text-center min-h-[70vh] px-8">
  <h1 className="font-serif text-5xl capitalize mb-4">{business_name}</h1>
  <p className="text-gray-600 max-w-xl mb-8">{tagline}</p>
  <button className="rounded-full px-8 py-4 bg-purple-500 text-white">
    CTA
  </button>
</section>
```
""",
        "bold": f"""
Create a BOLD IMPACT Hero Section for: {business_name}
Tagline: {tagline}

Use these exact tokens:
- Layout: fullscreen with image background
- Font: Anton, UPPERCASE, ITALIC
- Transform: skewX(-5deg) on headline
- Text-stroke: -webkit-text-stroke: 2px var(--primary)
- Image: absolute inset-0 opacity-30
- CTA: rounded-none with offset shadow
- Overlap: next section starts at -80px

Example structure:
```tsx
<section className="relative min-h-screen overflow-hidden">
  <img src={{bgImage}} className="absolute inset-0 w-full h-full object-cover opacity-30" />
  <div className="relative z-10 container mx-auto px-8 pt-32">
    <h1
      className="uppercase italic font-bold"
      style={{
        fontSize: 'clamp(4rem, 15vw, 12vw)',
        transform: 'skewX(-5deg)',
        WebkitTextStroke: '2px var(--primary)',
        color: 'transparent'
      }}
    >
      {business_name}
    </h1>
    <button className="mt-8 px-8 py-4 rounded-none shadow-[4px_4px_0px_var(--accent)] hover:translate-x-1 hover:translate-y-1 hover:shadow-none">
      CTA
    </button>
  </div>
</section>
```
""",
        "corporate": f"""
Create a CORPORATE Hero Section for: {business_name}
Tagline: {tagline}

Use these exact tokens:
- Layout: split grid (text/image)
- Font: Inter, clean sans-serif
- Border radius: 6px
- Shadows: subtle/monochrome
- Motion: discreet fade

Example structure:
```tsx
<section className="grid md:grid-cols-2 gap-8 items-center py-16">
  <div>
    <h1 className="text-4xl font-semibold mb-4">{business_name}</h1>
    <p className="text-gray-600 mb-6">{tagline}</p>
    <button className="rounded-md px-6 py-3 bg-blue-800 text-white">
      CTA
    </button>
  </div>
  <img src={{image}} className="rounded-lg" />
</section>
```
""",
        "minimal": f"""
Create a MINIMAL TECH Hero Section for: {business_name}
Tagline: {tagline}

Use these exact tokens:
- Layout: bento grid or glass overlay
- Font: Space Grotesk, lowercase
- Border radius: 12px
- Effect: glassmorphism (backdrop-blur)
- Shadows: neon glow
- Slight skew (2deg)

Example structure:
```tsx
<section className="relative min-h-[80vh] flex items-center">
  <div className="glass-card max-w-2xl p-12">
    <h1 className="text-7xl lowercase font-medium mb-4">{business_name}</h1>
    <p className="text-gray-400 mb-8">{tagline}</p>
    <button className="rounded-xl px-6 py-3 shadow-[0_0_20px_rgba(59,130,246,0.4)]">
      CTA
    </button>
  </div>
</section>
```
""",
    }

    return f"{system}\n\n{hero_templates.get(pole, hero_templates['corporate'])}"


def build_services_prompt(pole: str, services: list[str]) -> str:
    """
    Gera prompt para seção de serviços.

    Args:
        pole: Polo estético
        services: Lista de serviços

    Returns:
        Prompt formatado para serviços
    """
    service_templates = {
        "soft": """
Create a SOFT Services section with these characteristics:
- Cards: rounded-[40px] with soft purple shadow
- Spacing: generous padding (p-8)
- Hover: subtle lift with shadow increase
- Background: white or very light gray
- Icons: rounded-full or soft shapes
""",
        "bold": """
Create a BOLD Services section with these characteristics:
- Cards: rounded-none with offset shadow (8px 8px 0)
- Spacing: tight padding, overlap between cards
- Hover: translate and shadow reduction
- Background: dark or high contrast
- Layout: grid with -ml-4 negative margins for overlap
- Use UPPERCASE for service names
""",
        "corporate": """
Create a CORPORATE Services section with these characteristics:
- Cards: rounded-md with subtle shadow
- Spacing: standard padding (p-6)
- Hover: subtle shadow increase
- Background: white
- Layout: clean grid or flex row
- Use professional icon style
""",
        "minimal": """
Create a MINIMAL TECH Services section with these characteristics:
- Cards: rounded-xl with glass effect or neon shadow
- Spacing: precise padding
- Hover: glow intensity increase
- Background: dark or gradient
- Layout: bento grid or asymmetric
- Use geometric or line icons
""",
    }

    services_list = "\n".join(f"- {s}" for s in services)

    return f"""
{service_templates.get(pole, service_templates['corporate'])}

Services to display:
{services_list}

Return the component code using the pole tokens and CSS variables:
- border-radius: var(--pole-radius)
- box-shadow: var(--pole-shadow-card)
- padding: var(--pole-card-padding)
"""


def build_cta_prompt(pole: str, cta_text: str = "Comece Agora") -> str:
    """
    Gera prompt para seção CTA.

    Args:
        pole: Polo estético
        cta_text: Texto do CTA

    Returns:
        Prompt formatado para CTA
    """
    cta_templates = {
        "soft": f"""
Create a SOFT CTA section:
- Button: rounded-full, soft shadow
- Background: gradient or soft color
- Text: elegant and welcoming tone
- Include subtle decorative elements
""",
        "bold": f"""
Create a BOLD CTA section:
- Button: rounded-none, offset shadow
- Text: UPPERCASE, ITALIC
- Include aggressive messaging
- Use text-stroke or outline effects
- Consider full-width or overlapping layout
""",
        "corporate": f"""
Create a CORPORATE CTA section:
- Button: rounded-md, professional
- Text: clear and direct
- Include trust elements (certifications, etc.)
- Professional layout
""",
        "minimal": f"""
Create a MINIMAL TECH CTA section:
- Button: rounded-xl with glow
- Use glass effect
- Geometric shapes
- Clean, focused layout
""",
    }

    return f"{cta_templates.get(pole, cta_templates['corporate'])}\n\nCTA Text: {cta_text}"


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT PRINCIPAL DO SISTEMA LÍQUIDO
# ═══════════════════════════════════════════════════════════════════════════


def build_liquid_system_prompt(
    pole: str,
    design_heat: float = 0.5,
    include_hero: bool = True,
    include_services: bool = True,
    include_cta: bool = True,
    business_context: str = "",
) -> str:
    """
    Gera prompt principal do sistema de blocos líquidos.

    Args:
        pole: Polo estético (soft, bold, corporate, minimal)
        design_heat: 0.1 (frio) a 1.0 (quente)
        include_hero: Incluir seção hero
        include_services: Incluir seção serviços
        include_cta: Incluir seção CTA
        business_context: Contexto adicional do negócio

    Returns:
        Prompt completo para geração
    """
    system = POLE_SYSTEM_PROMPTS.get(pole, POLE_SYSTEM_PROMPTS["corporate"])
    heat_label = "FRIO" if design_heat < 0.3 else "MÉDIO" if design_heat < 0.7 else "QUENTE"

    sections = []
    if include_hero:
        sections.append("- Hero Section com layout do polo")
    if include_services:
        sections.append("- Services Section com cards do polo")
    if include_cta:
        sections.append("- CTA Section com botão do polo")

    sections_str = "\n".join(sections)

    return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              LIQUID DESIGN SYSTEM - {heat_label} MODE                          ║
║              Design Heat: {design_heat:.1f} | Polo: {pole.upper():<10}                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

{system}

═══════════════════════════════════════════════════════════════════════════════
REQUIRED SECTIONS
═══════════════════════════════════════════════════════════════════════════════
{sections_str}

{business_context}

═══════════════════════════════════════════════════════════════════════════════
CSS VARIABLES TO USE (these are LAWS)
═══════════════════════════════════════════════════════════════════════════════
--pole-radius: border-radius based on pole
--pole-shadow-card: box-shadow based on pole
--pole-heading-font: font-family based on pole
--pole-heading-case: text-transform based on pole
--pole-motion-speed: animation speed based on pole
--pole-motion-ease: easing based on pole
--pole-section-overlap: negative margin based on pole

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════
Return a JSON object:
{{
  "files": {{
    "src/components/HeroSection.tsx": "...",
    "src/components/ServicesSection.tsx": "...",
    "src/components/CTASection.tsx": "...",
    "src/index.css": "/* CSS with pole tokens */"
  }},
  "tokens": {{
    "pole": "{pole}",
    "primary": "#hex",
    "accent": "#hex"
  }}
}}

MAKE IT MEMORABLE. MAKE IT {pole.upper()}.
"""


def get_temperature_for_agent(agent: str, pole: str = "") -> float:
    """
    Retorna a temperatura correta para um agente.

    Args:
        agent: Nome do agente
        pole: Polo estético

    Returns:
        Temperatura (0.0 a 1.0)
    """
    # BOLD pole usa temperaturas mais altas
    if pole == "bold" and agent == "vite_react_renderer":
        return TEMPERATURE_CONFIG["vite_react_renderer_bold"]["temperature"]

    if pole == "bold" and agent == "agente_variacao":
        return TEMPERATURE_CONFIG["agente_variacao_max"]["temperature"]

    if agent in TEMPERATURE_CONFIG:
        return TEMPERATURE_CONFIG[agent]["temperature"]

    # Default
    return 0.5


# ═══════════════════════════════════════════════════════════════════════════
# COMPATIBILITY EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "TEMPERATURE_CONFIG",
    "POLE_SYSTEM_PROMPTS",
    "build_liquid_system_prompt",
    "build_hero_prompt",
    "build_services_prompt",
    "build_cta_prompt",
    "get_temperature_for_agent",
]
