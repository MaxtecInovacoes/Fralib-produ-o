"""Sub-agentes especializados por estetica (Sprint 6 - v1.9).

Cada estetica tem um agente dedicado que retorna HTML otimizado para
o estilo visual. Sao registrados via SUB_AGENT_DISPATCH e chamados
via route_to_sub_agent() do router.

Custo: $0 (nao chama LLM - usa templates via variation system).
Tracing: opt-in via FRALIB_TRACING (zero overhead se desabilitado).
"""
from __future__ import annotations

import os
from typing import Callable

# Tracing opt-in
try:
    from backend.services.tracing import trace_run
    _HAS_TRACING = True
except ImportError:
    _HAS_TRACING = False
    from contextlib import contextmanager
    @contextmanager
    def trace_run(*args, **kwargs):
        yield None


def bold_agent(prd: dict, facts: dict) -> str:
    """BOLD_ENERGY: dark, neon, motion cinematic, 3D shaders."""
    business = facts.get("business_name", "Marca")
    tagline = facts.get("tagline", "Performance real")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{business}</title>
<style>body{{background:#0a0a0a;color:#fff;font-family:Inter,sans-serif;}}</style>
</head>
<body>
<section class="hero" data-reveal>
  <h1>{business}</h1>
  <p>{tagline}</p>
  <button class="cta">COMECAR AGORA</button>
</section>
<section class="features" data-parallax>
  <h2>Performance sem limites</h2>
  <div class="grid">{"".join(f"<div class='card'>{k}: {v}</div>" for k,v in facts.items() if k not in ['business_name','tagline'])}</div>
</section>
</body></html>"""


def editorial_agent(prd: dict, facts: dict) -> str:
    """EDITORIAL: serif elegante, marquee, bento grid premium."""
    business = facts.get("business_name", "Marca")
    tagline = facts.get("tagline", "Excelencia")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{business}</title>
<style>body{{background:#faf8f5;color:#1a1a1a;font-family:'Playfair Display',serif;}}</style>
</head>
<body>
<header class="marquee"><span>{business.upper()} - {tagline.upper()}</span></header>
<section class="bento">
  <div class="cell large"><h1>{business}</h1><p>{tagline}</p></div>
  <div class="cell"><h3>Historia</h3><p>Tradicão e excelencia</p></div>
  <div class="cell"><h3>Visao</h3><p>Futuro premium</p></div>
  <div class="cell"><h3>Equipe</h3><p>Especialistas</p></div>
</section>
</body></html>"""


def minimal_agent(prd: dict, facts: dict) -> str:
    """MINIMAL: zen, whitespace, sans-serif clean, motion subtle."""
    business = facts.get("business_name", "Marca")
    tagline = facts.get("tagline", "Simplicidade")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{business}</title>
<style>body{{background:#fff;color:#222;font-family:'IBM Plex Sans',sans-serif;padding:80px;}}</style>
</head>
<body>
<main class="zen">
  <h1>{business}</h1>
  <p class="lead">{tagline}</p>
  <nav class="quiet">
    <a href="#about">Sobre</a> <a href="#contact">Contato</a>
  </nav>
  <section id="about">
    <p>Foco no essencial. Cada elemento tem proposito.</p>
  </section>
</main>
</body></html>"""


def kinetic_agent(prd: dict, facts: dict) -> str:
    """KINETIC: vibrant, text-animate, shimmer, motion editorial."""
    business = facts.get("business_name", "Marca")
    tagline = facts.get("tagline", "Energia")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{business}</title>
<style>body{{background:linear-gradient(135deg,#ff6b6b,#feca57);color:#fff;font-family:Inter;}}</style>
</head>
<body>
<section class="hero" data-shimmer>
  <h1 data-text-animate>{business}</h1>
  <p data-text-animate>{tagline}</p>
  <button class="cta-bold">EXPERIMENTE</button>
</section>
<section class="menu-grid">
  <div class="item">Item 1</div><div class="item">Item 2</div>
  <div class="item">Item 3</div><div class="item">Item 4</div>
</section>
</body></html>"""


def scroll_agent(prd: dict, facts: dict) -> str:
    """SCROLL: storytelling, GSAP ScrollTrigger, Lenis smooth."""
    business = facts.get("business_name", "Marca")
    tagline = facts.get("tagline", "Jornada")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{business}</title>
<style>body{{background:#f5f5f0;color:#1a1a1a;}}</style>
<script src="https://unpkg.com/lenis@1.1.13/dist/lenis.min.js"></script>
</head>
<body data-scroll-container>
<section class="hero" data-scroll-section>
  <h1>{business}</h1>
  <p>{tagline}</p>
</section>
<section class="story" data-scroll-section>
  <h2>Nossa Historia</h2>
  <p>Cada capitulo construido com proposito.</p>
</section>
</body></html>"""


def immersive_3d_agent(prd: dict, facts: dict) -> str:
    """IMMERSIVE_3D: R3F scene no hero, dark + cinematic."""
    business = facts.get("business_name", "Marca")
    tagline = facts.get("tagline", "Viva a experiencia")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{business}</title>
<style>body{{background:#000;color:#fff;font-family:'Space Grotesk',sans-serif;overflow:hidden;}}</style>
</head>
<body>
<canvas id="hero-3d"></canvas>
<div class="overlay">
  <h1>{business}</h1>
  <p>{tagline}</p>
</div>
<script>
// Stub R3F/Drei - em prod carrega via importmap
console.log("3D scene placeholder");
</script>
</body></html>"""


def default_agent(prd: dict, facts: dict) -> str:
    """Fallback quando estetica desconhecida."""
    business = facts.get("business_name", "Marca")
    return f"""<!DOCTYPE html>
<html><head><title>{business}</title></head>
<body><h1>{business}</h1><p>Site generico.</p></body></html>"""


# Registry
SUB_AGENT_DISPATCH: dict[str, Callable[[dict, dict], str]] = {
    "BOLD_ENERGY": bold_agent,
    "EDITORIAL": editorial_agent,
    "MINIMAL": minimal_agent,
    "KINETIC": kinetic_agent,
    "SCROLL": scroll_agent,
    "IMMERSIVE_3D": immersive_3d_agent,
    "default": default_agent,
}


def list_sub_agents() -> list[str]:
    """Lista nomes dos sub-agentes registrados."""
    return list(SUB_AGENT_DISPATCH.keys())


def sub_agent(name: str):
    """Decorator que mapeia nome → handler. Uso: @sub_agent('BOLD_ENERGY')"""
    def decorator(func: Callable[[dict, dict], str]) -> Callable[[dict, dict], str]:
        SUB_AGENT_DISPATCH[name] = func
        return func
    return decorator
