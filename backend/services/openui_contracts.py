"""Unifica todos os contratos FraLib num unico bloco de contexto para OpenUI.

Em vez de duplicar regras de SEO, motion, LGPD, design system, etc em codigo
Vite/React, este modulo produz um bloco de texto injetado no system prompt
do OpenUI renderer. O LLM segue os contratos direto no HTML que gera.

Conecta (sem acoplar):
- SEO Framework por nicho (seo_context.get_seo_context)
- Design System Selector (design_system_selector.select_design_system)
- LGPD personalizado por negocio (lgpd_personalized.build_personalized_lgpd)
- Motion Contract (regras de parallax/reveal/GSAP)
- A11y Contract (skip link, main landmark, prefers-color-scheme)
- Factual Contract (JSON-LD com dados confirmados)
"""

from __future__ import annotations

from typing import Any


# --- Blocos estaticos (regras) ---

MOTION_CONTRACT = """
=== MOTION CONTRACT - SIGA OBRIGATORIAMENTE ===
Adicione data-motion hooks no HTML para que o FraLib Motion Runtime (GSAP+ScrollTrigger+Lenis via CDN) ative:
- data-parallax="0.3" em imagens/secoes de hero (movimento vertical ao scroll)
- data-reveal em secoes internas (fade+slide ao entrar na viewport, stagger 0.05s)
- data-marquee="left|right" data-marquee-speed="30" em trilhas de logos/icones (loop infinito)
- data-parallax="0.1" em textos do hero (movimento sutil, mais devagar que o scroll)
- data-parallax="0.5" em imagens de fundo (movimento mais rapido que o scroll)
Use Tailwind animate-* classes (animate-fade-in, animate-slide-up) e
  transition-* (transition-all duration-300 ease-out)
- group hover effects em cards (group-hover:scale-105, group-hover:shadow-2xl)
- Stagger animations em listas: animation-delay escalonado via inline style
- Imagens: loading="lazy" e motion-safe:animate-fade-in
- NUNCA use animation que bloqueia o usuario (auto-play video, scroll-jacking)
- Use prefers-reduced-motion: prefers-reduced-motion:animate-none
=== FIM MOTION ===
"""

A11Y_CONTRACT = """
=== A11Y CONTRACT - SIGA OBRIGATORIAMENTE ===
- Primeiro elemento focavel do body: <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:bg-white focus:text-black focus:px-4 focus:py-2 focus:z-50 focus:rounded">Pular para o conteudo principal</a>
- Conteudo principal envolto em <main id="main" tabindex="-1">
- <html lang="pt-BR"> obrigatorio
- Contraste minimo AA (4.5:1 texto normal, 3:1 texto grande)
- Cada secao tem <section aria-labelledby="..."> com h2 visivel
- Imagens com alt descritivo (decorativas: alt="")
- Botoes/links com texto claro (sem "clique aqui" generico)
- Form fields com <label for="...">
- Suporte a prefers-color-scheme via classes dark/light
=== FIM A11Y ===
"""

FACTUAL_CONTRACT = """
=== FACTUAL CONTRACT - DADOS CONFIRMADOS ===
Inclua <script type="application/ld+json"> com:
{
  "@context": "https://schema.org",
  "@type": "<SCHEMA>",
  "name": "<NOME>",
  "telephone": "<PHONE>",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "<ENDERECO>",
    "addressLocality": "<CIDADE>"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "<RATING>",
    "reviewCount": "<N_REVIEWS>"
  }
}
Tambem inclua <section data-fralib-contract class="sr-only" aria-label="Dados confirmados">
com <span> para cada campo confirmado. Crawlers usam isso para verificar fatos.
=== FIM FACTUAL ===
"""

DEPLOY_RULES = """
=== REGRAS DE DEPLOY - OPENUI HTML ESTATICO ===
- Tailwind via CDN OK (https://cdn.tailwindcss.com) - deploy converte para build proprio
- Google Fonts OK via <link rel="preconnect"> + <link href="https://fonts.googleapis.com">
- Imagens: use URLs reais do brief (Hunter, Unsplash) ou CSS gradients - NUNCA
  /icons/, data:image quebrado, source.unsplash.com, iframes de mapa
- WhatsApp: <a href="https://wa.me/55<NUMBER>" target="_blank" rel="noopener">
- Telefone: <a href="tel:+55<NUMBER>">
- Email: <a href="mailto:<EMAIL>">
- Sem JavaScript custom, sem event handlers inline, sem forms que postam pra fora
- Mobile-first: classes sm: md: lg: so onde precisar; base = mobile
- NUNCA use bg-green-700, text-center text-white, "Bem-vindo ao nosso site"
  (cliches FraLib proibe)
=== FIM DEPLOY ===
"""


# --- Bloco dinamico (com dados do lead) ---

def _lgpd_block(facts: dict[str, Any]) -> str:
    """Texto LGPD personalizado por negocio/segmento."""
    business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
    nome = business.get("name") or "Este site"
    cidade = business.get("city") or ""
    segment = business.get("segment") or "negocio local"

    servico_map = {
        "restaurante": "pedidos, reservas e entrega de alimentos",
        "pizzaria": "pedidos, reservas e entrega de pizzas",
        "academia": "matriculas e acompanhamento fitness",
        "crossfit": "matriculas e acompanhamento CrossFit",
        "clinica": "agendamento de consultas e atendimento medico",
        "odontologia": "agendamento de consultas odontologicas",
        "barbearia": "agendamento de horarios e servicos de barbearia",
        "estetica": "agendamento de tratamentos esteticos",
        "salao_beleza": "agendamento de servicos de beleza",
        "advocacia": "atendimento juridico consultivo",
        "contabilidade": "atendimento contabil e fiscal",
    }
    servico = servico_map.get(segment, "atendimento e prestacao de servicos")
    cidade_text = (" em " + cidade) if cidade else ""

    return f"""
=== LGPD BANNER (banner fixo no rodape + link na politica) ===
Texto do banner: "Este site{cidade_text} usa cookies e dados para
{servico}. Ao continuar, voce concorda com nossa politica de privacidade.
Saiba mais em /politica-de-privacidade"
Empresa: {nome}
Inclua o banner como ultimo elemento antes de </body>, com
class="fixed bottom-0 left-0 right-0 bg-zinc-900/95 backdrop-blur-sm
text-zinc-100 p-4 z-50 text-sm" e botao "Aceitar" que esconde via JS inline
onclick="this.parentElement.remove()" (permitido, FraLib compacta).
=== FIM LGPD ===
"""


def _design_block(facts: dict[str, Any]) -> str:
    """Design system slug + paleta + tipografia do nicho."""
    try:
        from backend.agents.design_system_selector import select_design_system
    except Exception:
        try:
            from agents.design_system_selector import select_design_system
        except Exception:
            return "\n=== DESIGN SYSTEM ===\nUse tipografia moderna (Inter/Oswald), paleta contrastante, espacamento generoso.\n=== FIM DESIGN ===\n"

    business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
    segmento = business.get("segment") or facts.get("segmento") or "default"
    nome = business.get("name") or ""
    selected = select_design_system(segmento, nome, tier="STANDARD")
    slug = selected.get("slug", "default")
    content = (selected.get("content") or "")[:1500]
    return f"""
=== DESIGN SYSTEM - SIGA OBRIGATORIAMENTE ===
Slug selecionado: {slug}
{content}
=== FIM DESIGN SYSTEM ===
"""


def _seo_block(facts: dict[str, Any]) -> str:
    """SEO framework por nicho (h1, keywords, FAQ, schema.org)."""
    try:
        from backend.agents.seo_context import get_seo_context
    except Exception:
        try:
            from agents.seo_context import get_seo_context
        except Exception:
            return "\n=== SEO ===\nUse h1 com nome e cidade, meta description 150-160 chars, FAQ 4 perguntas.\n=== FIM SEO ===\n"

    business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
    segmento = business.get("segment") or facts.get("segmento") or "default"
    cidade = business.get("city") or facts.get("cidade") or ""
    nome = business.get("name") or ""
    return get_seo_context(segmento, cidade, nome)


def build_openui_context_block(facts: dict[str, Any] | None) -> str:
    """Bloco completo de contratos para injetar no system prompt do OpenUI.

    Combina (na ordem):
    1. SEO Framework (nichos: h1, keywords, FAQ, schema.org)
    2. Design System (paleta, tipografia, motion do nicho)
    3. Motion Contract (parallax, reveal, GSAP rules)
    4. A11y Contract (skip link, main, contraste)
    5. Factual Contract (JSON-LD + section sr-only)
    6. LGPD personalizado (segmento-aware)
    7. Deploy Rules (Tailwind CDN, links wa.me/tel:, sem iframes)
    """
    facts = facts or {}
    return "\n".join([
        _seo_block(facts),
        _design_block(facts),
        MOTION_CONTRACT,
        A11Y_CONTRACT,
        FACTUAL_CONTRACT,
        _lgpd_block(facts),
        DEPLOY_RULES,
    ])
