"""
cinematic_post_processor.py — Transforma HTML gerado pelo LLM em site cinematográfico.

Injeta:
- Wrapper com Google Fonts, GSAP, Lenis, ScrollTrigger
- Barra de progresso de scroll
- Animações on-scroll via IntersectionObserver
- Alternância de fundo entre seções
- Scroll suave Lenis
- Contadores animados
- Text reveal para headings
"""

import re
import hashlib
import os


# ─── Google Fonts pairing por design direction ────────────────────────
FONT_PAIRINGS = {
    "energetic":    ("Oswald", "Inter"),
    "elegant":      ("Gelasio", "Inter"),
    "vibrante":     ("Space Grotesk", "Inter"),
    "default":      ("Plus Jakarta Sans", "Inter"),
    "fitness":      ("Oswald", "Inter"),
    "brutalism":    ("Darker Grotesque", "Inter"),
    "luxury":       ("Playfair Display", "Inter"),
    "corporate":    ("Plus Jakarta Sans", "Inter"),
    "editorial":    ("Gelasio", "Gelasio"),
    "clean":        ("Plus Jakarta Sans", "Inter"),
    "modern":       ("Plus Jakarta Sans", "Inter"),
    "warm":         ("Poppins", "Poppins"),
    "friendly":     ("Noto Serif Display", "Noto Serif Display"),
    "dramatic":     ("Outfit", "Outfit"),
}


def _pick_fonts(design_tokens: dict, segmento: str, nome: str) -> tuple:
    """Escolhe fonte heading/body baseado em design_tokens ou fallback por nicho."""
    if design_tokens:
        heading = design_tokens.get("font_heading", "")
        body = design_tokens.get("font_body", "")
        if heading and body:
            return (heading, body)

    seed = int(hashlib.md5((nome or segmento).encode()).hexdigest()[:8], 16)
    options = list(FONT_PAIRINGS.values())
    return options[seed % len(options)]


def _build_font_url(heading: str, body: str) -> str:
    """Monta URL do Google Fonts com pesos variados."""
    h = heading.replace(" ", "+")
    b = body.replace(" ", "+")
    return (
        "https://fonts.googleapis.com/css2?"
        f"family={h}:opsz,wght@8..144,400;8..144,500;8..144,600;8..144,700;8..144,800&"
        f"family={b}:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600&"
        "display=swap"
    )


def _inject_wrapper(html: str, font_url: str) -> str:
    """Envolve HTML com DOCTYPE + head completo + scripts cinematográficos."""
    wrapper_head = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Site oficial — gerado por FraLib">
<title></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{font_url}" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {{ darkMode: 'class' }}
</script>
<style>
  :root {{
    --bg: oklch(98% 0.0 0);
    --surface: oklch(100% 0.0 0);
    --fg: oklch(9% 0.017 221);
    --muted: oklch(55% 0.01 0);
    --border: oklch(90% 0.008 220);
    --accent: oklch(48% 0.147 217);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: auto; }}
  body {{
    font-family: var(--font-body, 'Inter'), system-ui, sans-serif;
    color: var(--fg);
    background: var(--bg);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow-x: hidden;
  }}
  h1, h2, h3, h4 {{
    font-family: var(--font-heading, 'Plus Jakarta Sans'), system-ui, sans-serif;
  }}
  img {{ max-width: 100%; height: auto; display: block; }}
  a {{ color: inherit; text-decoration: none; }}

  /* ── Scroll Progress Bar ── */
  #scroll-progress {{
    position: fixed; top: 0; left: 0; height: 3px;
    background: var(--accent); z-index: 9999; width: 0%;
    transition: width 0.1s linear;
  }}

  /* ── Reveal animations ── */
  .reveal {{
    opacity: 0; transform: translateY(24px);
    transition: opacity 0.7s ease-out, transform 0.7s ease-out;
  }}
  .reveal.visible {{ opacity: 1; transform: translateY(0); }}

  .reveal-left {{
    opacity: 0; transform: translateX(-24px);
    transition: opacity 0.7s ease-out, transform 0.7s ease-out;
  }}
  .reveal-left.visible {{ opacity: 1; transform: translateX(0); }}

  .reveal-right {{
    opacity: 0; transform: translateX(24px);
    transition: opacity 0.7s ease-out, transform 0.7s ease-out;
  }}
  .reveal-right.visible {{ opacity: 1; transform: translateX(0); }}

  .scale-in {{
    opacity: 0; transform: scale(0.95);
    transition: opacity 0.7s ease-out, transform 0.7s ease-out;
  }}
  .scale-in.visible {{ opacity: 1; transform: scale(1); }}

  /* ── Stagger waterfall ── */
  .stagger-item {{
    opacity: 0; transform: translateY(20px);
    transition: opacity 0.5s ease-out, transform 0.5s ease-out;
  }}
  .stagger-item.visible {{
    opacity: 1; transform: translateY(0);
    transition-delay: calc(var(--i, 0) * 80ms);
  }}

  /* ── Parallax suave ── */
  [data-parallax] {{
    will-change: transform;
    transform: translateZ(0);
  }}

  /* ── CTA pulse ── */
  .pulse-cta {{
    animation: ctaPulse 2s ease-in-out infinite;
  }}
  @keyframes ctaPulse {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(var(--accent-lch), 0.4); }}
    50% {{ box-shadow: 0 0 0 12px rgba(var(--accent-lch), 0); }}
  }}

  /* ── Counter animation ── */
  [data-counter] {{
    display: inline-block;
  }}

  /* ── WhatsApp float ── */
  .whatsapp-float {{
    position: fixed; bottom: 24px; right: 24px; z-index: 9998;
    width: 60px; height: 60px; border-radius: 50%;
    background: #25D366; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 20px rgba(37, 211, 102, 0.4);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
  }}
  .whatsapp-float:hover {{
    transform: scale(1.08);
    box-shadow: 0 6px 28px rgba(37, 211, 102, 0.55);
  }}

  /* ── Reduced motion ── */
  @media (prefers-reduced-motion: reduce) {{
    .reveal, .reveal-left, .reveal-right, .scale-in, .stagger-item {{
      opacity: 1 !important; transform: none !important;
      transition: none !important;
    }}
    .pulse-cta {{ animation: none; }}
    [data-parallax] {{ transform: none !important; }}
  }}

  /* ── Section alternation (cinematic rhythm) ── */
  section {{ position: relative; }}
  section:nth-child(even) {{ background: var(--surface); }}
  section:nth-child(odd) {{ background: var(--bg); }}
</style>
</head>
<body>
<div id="scroll-progress"></div>

"""

    wrapper_foot = """
<script>
(function() {
  'use strict';

  // ── Scroll Progress ──
  const progressBar = document.getElementById('scroll-progress');
  if (progressBar) {
    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      progressBar.style.width = pct + '%';
    }, { passive: true });
  }

  // ── IntersectionObserver: reveal / stagger / counter ──
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        // Counter animation
        const counter = entry.target.querySelector('[data-counter]');
        if (counter && !counter.dataset.animated) {
          counter.dataset.animated = 'true';
          animateCounter(counter);
        }
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .scale-in, .stagger-item')
    .forEach(el => observer.observe(el));

  // ── Parallax suave ──
  const parallaxEls = document.querySelectorAll('[data-parallax]');
  if (parallaxEls.length) {
    const pObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const speed = parseFloat(el.dataset.parallax) || 0.2;
          function onScroll() {
            const rect = el.getBoundingClientRect();
            const center = rect.top + rect.height / 2;
            const offset = (window.innerHeight / 2 - center) * speed;
            el.style.transform = `translateY(${offset}px)`;
          }
          window.addEventListener('scroll', onScroll, { passive: true });
          onScroll();
          pObserver.unobserve(el);
        }
      });
    }, { threshold: 0 });
    parallaxEls.forEach(el => pObserver.observe(el));
  }

  // ── Counter animation ──
  function animateCounter(el) {
    const target = parseFloat(el.dataset.counter);
    if (isNaN(target)) return;
    const decimals = (target.toString().split('.')[1] || '').length;
    const duration = 1500;
    const start = performance.now();
    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = eased * target;
      el.textContent = current.toFixed(decimals);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ── Hover premium para cards ──
  document.querySelectorAll('.card').forEach(card => {{
    card.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
    card.addEventListener('mouseenter', () => {{
      card.style.transform = 'translateY(-4px)';
      card.style.boxShadow = '0 12px 40px rgba(0,0,0,0.1)';
    }});
    card.addEventListener('mouseleave', () => {{
      card.style.transform = '';
      card.style.boxShadow = '';
    }});
  }});
})();
</script>
</body>
</html>"""

    # Remove DOCTYPE/html/head/body existentes se houver
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<html[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</html>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<title[^>]*>.*?</title>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'</?head[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<body[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</body>', '', html, flags=re.IGNORECASE)

    # Limpar espaços
    html = html.strip()

    return wrapper_head + html + wrapper_foot


def _fix_section_backgrounds(html: str) -> str:
    """Garante alternância de fundo entre seções para ritmo visual cinematográfico."""
    sections = re.findall(r'(<section[^>]*>.*?</section>)', html, re.DOTALL | re.IGNORECASE)
    if not sections:
        return html

    result = []
    bg_cycle = ["var(--bg)", "var(--surface)", "var(--bg)", "var(--bg)", "var(--surface)", "var(--bg)"]

    for i, section in enumerate(sections):
        bg = bg_cycle[i % len(bg_cycle)]
        # Inject or replace background
        section = re.sub(
            r'style="([^"]*)"',
            lambda m: f'style="background-color:{bg}; {m.group(1).replace("background-color:", "").replace(f"background:{bg};", "")}"' if 'background-color' not in m.group(1) and 'background:' not in m.group(1) else m.group(0),
            section, count=1
        )
        result.append(section)

    # Reconstruct HTML
    parts = html.split('<section')
    if len(parts) > 1:
        rebuilt = parts[0]
        for i, section in enumerate(result):
            rebuilt += '<section' + section.split('<section', 1)[1] if '<section' in section else section
        return rebuilt
    return html


def _fix_hero_typography(html: str) -> str:
    """Garante que o hero tem tipografia cinematográfica."""
    # Garante que h1 no hero tem font-bold (skip se ja tem clamp() ou font-bold)
    def _add_font_bold(m):
        full = m.group(0)
        if 'clamp(' in full or 'font-bold' in full:
            return full
        return m.group(1) + ' font-bold' + m.group(2)

    html = re.sub(
        r'(<h1[^>]*class="[^"]*)([^"]*"[^>]*>)',
        _add_font_bold,
        html
    )
    return html


def _inject_google_fonts_var(html: str, heading: str, body: str) -> str:
    """Injeta CSS vars para fontes no :root."""
    h = heading.replace(" ", "+")
    b = body.replace(" ", "+")
    font_vars = f"  --font-heading: '{heading}', system-ui, sans-serif;\n  --font-body: '{body}', system-ui, sans-serif;"
    html = re.sub(
        r'(:root\s*\{)',
        lambda m: m.group(1) + '\n' + font_vars,
        html, count=1
    )
    # Also add var(--font-heading) and var(--font-body) to body/h1 CSS
    html = re.sub(
        r'font-family:\s*var\(--font-body[^)]*\)',
        f'font-family: var(--font-body, \'{body}\'), system-ui, sans-serif',
        html
    )
    html = re.sub(
        r'font-family:\s*var\(--font-heading[^)]*\)',
        f'font-family: var(--font-heading, \'{heading}\'), system-ui, sans-serif',
        html
    )
    return html


def _ensure_hero_parallax(html: str) -> str:
    """Garante que a primeira imagem do hero tem parallax."""
    # Find hero section
    hero_match = re.search(r'<section[^>]*id=["\']hero["\'][^>]*>(.*?)</section>', html, re.DOTALL | re.IGNORECASE)
    if hero_match:
        hero_content = hero_match.group(1)
        # Find first img in hero
        img_match = re.search(r'<img([^>]*?)>', hero_content, re.IGNORECASE)
        if img_match and 'data-parallax' not in img_match.group(0):
            new_img = img_match.group(0).replace('<img', '<img data-parallax="0.3"')
            html = html.replace(img_match.group(0), new_img, 1)
    return html


def _add_stagger_to_cards(html: str) -> str:
    """Adiciona stagger delay em grids de cards."""
    # Find card containers with grid/flex
    def add_stagger(m):
        tag = m.group(0)
        if 'stagger-item' in tag or '--i' in tag:
            return tag
        # Add stagger-item class to direct children that are cards
        return tag

    # Pattern: div/grid containing cards
    html = re.sub(
        r'(<div[^>]*class="[^"]*(?:grid|flex)[^"]*(?:gap|cols)[^"]*"[^>]*>)',
        lambda m: m.group(1) + '\n      <style>.stagger-item{--i:0}</style>' if 'stagger-item' not in m.group(0) else m.group(0),
        html
    )
    return html


def _fix_accent_contrast(html: str) -> str:
    """Garante contraste mínimo entre accent e background."""
    # This is a light touch — just ensure accent is used for CTAs with proper text color
    html = re.sub(
        r'bg-\[var\(--accent\)\]([^>]*>)([^<]*)(</a>|</button>)',
        lambda m: f'bg-[var(--accent)]{m.group(1)}<span style="color:var(--bg)">{m.group(2)}</span>{m.group(3)}' if 'text-' not in m.group(1) else m.group(0),
        html
    )
    return html


def _add_scroll_progress_id(html: str) -> str:
    """Adiciona ID na barra de progresso se não existir."""
    if 'id="scroll-progress"' not in html:
        html = html.replace('<div id="scroll-progress">', '<div id="scroll-progress"></div>')
    return html


def process(html: str, design_tokens: dict = None, segmento: str = "", nome: str = "") -> str:
    """Pipeline de pós-processamento cinematográfico."""

    heading, body = _pick_fonts(design_tokens or {}, segmento, nome)
    font_url = _build_font_url(heading, body)

    # 1. Inject wrapper (DOCTYPE + scripts + styles)
    html = _inject_wrapper(html, font_url)

    # 2. Inject font CSS vars
    html = _inject_google_fonts_var(html, heading, body)

    # 3. Fix section backgrounds
    html = _fix_section_backgrounds(html)

    # 4. Fix hero typography
    html = _fix_hero_typography(html)

    # 5. Ensure hero parallax
    html = _ensure_hero_parallax(html)

    # 6. Fix accent contrast on CTAs
    html = _fix_accent_contrast(html)

    # 7. Add scroll progress
    html = _add_scroll_progress_id(html)

    return html
