"""Comparacao Template vs LLM (simulado).

Gera 1 site via rota TEMPLATE (render_with_template) e 1 site via stub
"estilo LLM" com 7 secoes + data-attributes de motion. Mede:

  - chars
  - hints de animacao (transition, animation, transform, keyframes,
    data-*, IntersectionObserver, etc.)
  - contagem de elementos com data-animate / data-reveal / data-parallax
  - contagem de secoes distintas (h1/h2)

Sem chamar API LLM real: o stub "estilo LLM" eh deterministico mas
simula a estrutura que o Sonnet geraria (7 secoes, Tailwind, data-* attrs).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.openui_renderer import (  # noqa: E402
    render_with_template,
    build_openui_document,
)


FACTS = {
    "lead_id": 9999,
    "business": {
        "name": "Codex Barbearia",
        "tagline": "Estilo e atitude em cada corte",
        "city": "Sao Paulo",
        "address": "Rua Augusta, 1000",
        "phone": "+55 11 99999-0000",
        "whatsapp": "5511999990000",
        "email": "contato@codexbarbearia.com.br",
        "instagram": "codexbarbearia",
        "lead_id": 9999,
        "segmento": "barbearia",
    },
    "description": "Barbearia premium com cortes modernos, barba desenhada e ambiente acolhedor.",
    "sections": {
        "services": [
            {"title": "Corte Masculino", "description": "Corte sob medida com finalizacao."},
            {"title": "Barba", "description": "Barba desenhada com toalha quente."},
            {"title": "Combo", "description": "Corte + barba com desconto."},
        ],
    },
    "faq": [
        {"answer": "Sim, atendemos com e sem agendamento."},
        {"answer": "Cartao, pix e dinheiro."},
        {"answer": "Sim, temos estacionamento proprio."},
        {"answer": "Ate as 21h de segunda a sabado."},
    ],
    "testimonials": [
        {"name": "Joao Silva", "quote": "Melhor barbeiro da regiao.", "role": "Cliente"},
        {"name": "Maria Souza", "quote": "Ambiente incrivel e atendimento top.", "role": "Cliente"},
    ],
}


# ---------------------------------------------------------------------------
# Stub "estilo LLM" — simula HTML OpenUI/Tailwind que o Sonnet produziria
# Estrutura: 7 secoes, data-attributes para motion runtime, sem <script>
# ---------------------------------------------------------------------------

def _stub_llm_html(facts: dict) -> str:
    """HTML estatico que simula output tipico do Sonnet via OpenUI.

    Foco: 7 secoes canonicas + varios data-* attributes (parallax, reveal,
    marquee) para o motion runtime pegar. Mesmo escopo, sem JS inline.
    """
    b = facts.get("business", {})
    name = b.get("name", "Franquia")
    city = b.get("city", "")
    address = b.get("address", "")
    phone = b.get("phone", "")
    wa = b.get("whatsapp", "")
    ig = b.get("instagram", "")
    desc = facts.get("description", "")
    services = (facts.get("sections") or {}).get("services", [])
    faqs = facts.get("faq", [])
    testimonials = facts.get("testimonials", [])

    sections = []

    # 1) HERO
    sections.append(f"""
<section class="relative overflow-hidden" data-reveal="fade-up" data-parallax="0.15">
  <div class="max-w-6xl mx-auto px-6 py-24 text-center">
    <p class="uppercase tracking-widest text-sm opacity-70" data-marquee="true">Codex Barbearia | {city}</p>
    <h1 class="text-5xl md:text-7xl font-bold mt-4" data-reveal="fade-up" data-reveal-delay="120">
      {name}
    </h1>
    <p class="mt-6 text-lg md:text-xl opacity-80" data-reveal="fade-up" data-reveal-delay="240">
      {desc}
    </p>
    <div class="mt-10 flex flex-col sm:flex-row gap-4 justify-center" data-reveal="fade-up" data-reveal-delay="360">
      <a class="px-8 py-4 rounded-full bg-black text-white text-lg font-semibold hover:scale-105 transition-transform"
         href="https://wa.me/{wa}" data-card-stagger="0">Agendar agora</a>
      <a class="px-8 py-4 rounded-full border border-black/20 text-lg font-semibold hover:bg-black/5 transition-colors"
         href="#servicos">Ver servicos</a>
    </div>
  </div>
</section>
""")

    # 2) SOBRE
    sections.append(f"""
<section class="py-20" data-reveal="fade-up">
  <div class="max-w-4xl mx-auto px-6">
    <h2 class="text-3xl md:text-4xl font-bold" data-reveal="fade-up">Sobre nos</h2>
    <p class="mt-6 text-lg leading-relaxed opacity-80" data-reveal="fade-up" data-reveal-delay="120">
      {desc}
    </p>
  </div>
</section>
""")

    # 3) SERVICOS
    svc_cards = "\n".join(
        f"""
        <div class="p-6 rounded-2xl bg-white/5 border border-white/10" data-card-stagger="{i}" data-reveal="fade-up">
          <h3 class="text-xl font-semibold">{s.get('title', f'Servico {i+1}')}</h3>
          <p class="mt-2 opacity-70">{s.get('description', '')}</p>
        </div>
"""
        for i, s in enumerate(services)
    )
    sections.append(f"""
<section id="servicos" class="py-20" data-reveal="fade-up">
  <div class="max-w-6xl mx-auto px-6">
    <h2 class="text-3xl md:text-4xl font-bold text-center" data-reveal="fade-up">Servicos</h2>
    <div class="mt-12 grid md:grid-cols-3 gap-6">
{svc_cards}
    </div>
  </div>
</section>
""")

    # 4) DEPOIMENTOS
    t_cards = "\n".join(
        f"""
        <blockquote class="p-6 rounded-2xl bg-white/5" data-card-stagger="{i}">
          <p class="text-lg">&ldquo;{t.get('quote','')}&rdquo;</p>
          <footer class="mt-3 opacity-70">&mdash; {t.get('name','')}, {t.get('role','')}</footer>
        </blockquote>
"""
        for i, t in enumerate(testimonials)
    )
    sections.append(f"""
<section class="py-20" data-reveal="fade-up">
  <div class="max-w-6xl mx-auto px-6">
    <h2 class="text-3xl md:text-4xl font-bold text-center" data-reveal="fade-up">Quem nos escolhe</h2>
    <div class="mt-12 grid md:grid-cols-2 gap-6">
{t_cards}
    </div>
  </div>
</section>
""")

    # 5) FAQ
    faq_items = "\n".join(
        f"""
        <details class="py-4 border-b border-white/10" data-reveal="fade-up" data-reveal-delay="{i*80}">
          <summary class="cursor-pointer font-semibold">Pergunta {i+1}</summary>
          <p class="mt-2 opacity-80">{f.get('answer','')}</p>
        </details>
"""
        for i, f in enumerate(faqs)
    )
    sections.append(f"""
<section class="py-20" data-reveal="fade-up">
  <div class="max-w-3xl mx-auto px-6">
    <h2 class="text-3xl md:text-4xl font-bold" data-reveal="fade-up">FAQ</h2>
    <div class="mt-8">
{faq_items}
    </div>
  </div>
</section>
""")

    # 6) CONTATO
    sections.append(f"""
<section class="py-20" data-reveal="fade-up" data-parallax="0.1">
  <div class="max-w-3xl mx-auto px-6 text-center">
    <h2 class="text-3xl md:text-4xl font-bold" data-reveal="fade-up">Contato</h2>
    <p class="mt-4 opacity-80" data-reveal="fade-up" data-reveal-delay="120">{address} - {city}</p>
    <p class="opacity-80" data-reveal="fade-up" data-reveal-delay="160">{phone}</p>
    <a class="inline-block mt-8 px-8 py-4 rounded-full bg-black text-white font-semibold hover:scale-105 transition-transform"
       href="https://wa.me/{wa}" data-reveal="fade-up" data-reveal-delay="240">Falar no WhatsApp</a>
  </div>
</section>
""")

    # 7) FOOTER
    sections.append(f"""
<footer class="py-12 border-t border-white/10" data-reveal="fade-up">
  <div class="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between gap-6">
    <p class="opacity-70">&copy; 2026 {name}. Todos os direitos reservados.</p>
    <p class="opacity-70">
      <a href="https://wa.me/{wa}" class="underline">WhatsApp</a> &middot;
      <a href="https://instagram.com/{ig}" class="underline">Instagram</a> &middot;
      {address}
    </p>
  </div>
</footer>
""")

    body = "\n".join(sections)

    css = """
<style>
  html { scroll-behavior: smooth; }
  body { font-family: 'Inter', system-ui, sans-serif; background: #0a0a0a; color: #fafafa; }
  section { transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
  [data-reveal] { opacity: 0; transform: translateY(24px); }
  [data-reveal].is-revealed { opacity: 1; transform: none; }
  .card-stagger { transition-delay: calc(var(--i, 0) * 80ms); }
  @keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
  [data-marquee] { animation: marquee 30s linear infinite; }
  @media (prefers-reduced-motion: reduce) { [data-reveal] { opacity: 1; transform: none; } }
</style>
"""
    # Note: zero <script> tags. Motion runtime FraLib pega via data-*.
    return f'<!doctype html><html lang="pt-BR" data-renderer="openui_llm_simulated"><head><meta charset="utf-8"><title>{name}</title>{css}</head><body>{body}</body></html>'


ANIM_HINTS = (
    "data-reveal",
    "data-parallax",
    "data-marquee",
    "data-card-stagger",
    "data-mask-reveal",
    "data-fralib-animate",
    "fralib-motion-runtime",
    "@keyframes",
    "transition:",
    "animation:",
    "transform:",
    "transform ",
    "hover:scale",
    "hover:translate",
    "cubic-bezier",
)


def count_animation(html: str) -> dict:
    low = html.lower()
    counts = {h: low.count(h) for h in ANIM_HINTS if h in low}
    data_attrs = len(re.findall(r'data-[a-z][a-z0-9-]+=', low))
    headings = len(re.findall(r"<h[12][^>]*>", low))
    sections = len(re.findall(r"<section\b", low))
    keyframes = len(re.findall(r"@keyframes", low))
    transitions = len(re.findall(r"transition\s*:\s*[^;}]+", low))
    animations = len(re.findall(r"animation\s*:\s*[^;}]+", low))
    transforms = len(re.findall(r"transform\s*:\s*[^;}]+", low))
    return {
        "by_hint": counts,
        "data_attrs_total": data_attrs,
        "h1_h2": headings,
        "section_tags": sections,
        "keyframes": keyframes,
        "css_transitions": transitions,
        "css_animations": animations,
        "css_transforms": transforms,
        "score": sum(counts.values()) + data_attrs + 2 * sections + 3 * keyframes,
    }


def main() -> int:
    print("=" * 72)
    print("COMPARACAO TEMPLATE vs LLM (simulado)")
    print("=" * 72)

    # --- TEMPLATE ---
    t0 = time.perf_counter()
    template_result = render_with_template(builder_prompt="(unused)", facts=FACTS)
    template_ms = (time.perf_counter() - t0) * 1000.0
    template_html = template_result.html

    # --- LLM STUB ---
    t1 = time.perf_counter()
    llm_body = _stub_llm_html(FACTS)
    llm_doc = build_openui_document(llm_body, facts=FACTS)
    llm_ms = (time.perf_counter() - t1) * 1000.0

    # Metricas
    t_anim = count_animation(template_html)
    l_anim = count_animation(llm_doc)

    print()
    print(f"  TEMPLATE: chars={len(template_html)}  build={template_ms:.1f}ms  estetica sorteada={template_result.attempts[0].get('estetica')}")
    print(f"  LLM stub: chars={len(llm_doc)}       build={llm_ms:.1f}ms  (stub deterministico, sem API)")

    print()
    print("-" * 72)
    print("ANIMACAO (numero de elementos animados)")
    print("-" * 72)
    print(f"  {'metrica':<28}  template   llm-stub   vencedor")
    rows = [
        ("data-* attrs total",      t_anim["data_attrs_total"], l_anim["data_attrs_total"]),
        ("section tags",            t_anim["section_tags"],     l_anim["section_tags"]),
        ("@keyframes",              t_anim["keyframes"],        l_anim["keyframes"]),
        ("css transitions",         t_anim["css_transitions"],  l_anim["css_transitions"]),
        ("css animations",          t_anim["css_animations"],   l_anim["css_animations"]),
        ("css transforms",          t_anim["css_transforms"],   l_anim["css_transforms"]),
        ("h1/h2 headings",          t_anim["h1_h2"],            l_anim["h1_h2"]),
    ]
    t_score = 0
    l_score = 0
    for label, tv, lv in rows:
        winner = "TEMPLATE" if tv > lv else ("LLM" if lv > tv else "EMPATE")
        t_score += tv
        l_score += lv
        print(f"  {label:<28}  {tv:>6}    {lv:>6}     {winner}")
    print()
    print(f"  {'SCORE TOTAL':<28}  {t_score:>6}    {l_score:>6}     {'TEMPLATE' if t_score > l_score else 'LLM'}")
    print(f"  score_template_animation (full): {t_anim['score']}")
    print(f"  score_llm_animation (full):      {l_anim['score']}")

    print()
    print("-" * 72)
    print("HINTS ESPECIFICOS (data-* + keywords)")
    print("-" * 72)
    all_keys = sorted(set(t_anim["by_hint"].keys()) | set(l_anim["by_hint"].keys()))
    if not all_keys:
        print("  (nenhum hint detectado em um dos lados)")
    for k in all_keys:
        tv = t_anim["by_hint"].get(k, 0)
        lv = l_anim["by_hint"].get(k, 0)
        print(f"  {k:<28}  template={tv:>3}   llm={lv:>3}")

    # Veredito
    print()
    print("-" * 72)
    print("VEREDITO")
    print("-" * 72)
    if t_anim["score"] > l_anim["score"]:
        winner = "TEMPLATE (mais elementos de animacao no canonico)"
    elif l_anim["score"] > t_anim["score"]:
        winner = "LLM stub (mais elementos de animacao declarados)"
    else:
        winner = "EMPATE"
    print(f"  variacao visual: {winner}")

    # Persistir
    out = ROOT / "tests" / "_compare_template_vs_llm.json"
    out.write_text(
        json.dumps(
            {
                "template": {
                    "chars": len(template_html),
                    "ms": template_ms,
                    "anim": t_anim,
                    "attempts": template_result.attempts,
                },
                "llm_stub": {
                    "chars": len(llm_doc),
                    "ms": llm_ms,
                    "anim": l_anim,
                },
                "veredito": winner,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"  relatorio salvo em: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
