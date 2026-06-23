"""Smoke test: gera 1 site por estetica (6 sites) usando template_loader real.

Nao chama LLM — usa os 6 templates canonicos + sistema de variacao 4-eixos.
Valida:
  - HTML tem CSS variables
  - Sem {{}} nao substituido
  - Chars > 5000

Cronometra o total e reporta chars medios + estetica dominante.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.template_loader import (  # noqa: E402
    load_template,
    render_with_variation,
    validate_template_output,
)
from backend.templates._system.variation import (  # noqa: E402
    ESTETICAS,
    select_theme,
    select_typography,
    select_layout,
    select_motion,
)

ESTETICAS_6 = list(ESTETICAS)

LEAD_FACT = {
    "business": {
        "name": "Codex Barbearia",
        "tagline": "Estilo e atitude em cada corte",
        "city": "Sao Paulo",
        "address": "Rua Augusta, 1000",
        "phone": "+55 11 99999-0000",
        "email": "contato@codexbarbearia.com.br",
        "instagram": "codexbarbearia",
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

ANIMATION_HINTS = (
    "data-fralib-animate",
    "data-animate",
    "data-aos",
    "data-motion=",
    "fralib-motion-runtime",
    "IntersectionObserver",
    "requestAnimationFrame",
    "@keyframes",
    "transition:",
    "animation:",
    "transform: translate3d",
    "transform: scale(",
    "transform: rotate(",
    "scroll-linked",
    "scrollY",
    "parallax",
)


def build_variation_for(estetica: str, lead_id: int) -> dict:
    """Constroi variation dict compativel com render_with_variation()."""
    theme = select_theme(lead_id, estetica)
    typography = select_typography(lead_id, estetica)
    layout = select_layout(lead_id)
    motion = select_motion(lead_id, estetica)
    # Reaproveita o builder de css_vars_inline via generate_variation
    from backend.templates._system.variation import generate_variation
    v = generate_variation(lead_id, segmento=estetica.lower())
    # Garante que a estetica alvo seja a solicitada (forca a chave, nao o seed)
    v["estetica"] = estetica
    v["theme"] = theme
    v["typography"] = typography
    v["layout"] = layout
    v["motion"] = motion
    return v


def count_animated_elements(html: str) -> dict:
    low = html.lower()
    counts = {}
    for hint in ANIMATION_HINTS:
        if hint in low:
            counts[hint] = low.count(hint)
    total_hits = sum(counts.values())
    # Conta elementos com data-* relacionados a animacao
    data_anim = len(re.findall(r'data-(?:fralib-)?animate[="\s]', low))
    transitions = len(re.findall(r'transition\s*:', low))
    animations = len(re.findall(r'(?<!\w)animation\s*:', low))
    transforms = len(re.findall(r'transform\s*:', low))
    keyframes = len(re.findall(r'@keyframes', low))
    return {
        "hints_matched": total_hits,
        "data_anim_attrs": data_anim,
        "css_transitions": transitions,
        "css_animations": animations,
        "css_transforms": transforms,
        "css_keyframes": keyframes,
        "by_hint": counts,
    }


def main() -> int:
    print("=" * 72)
    print("SMOKE 6 SITES — 1 POR ESTETICA (Tenant 2, segmento=codex_barbearia)")
    print("=" * 72)

    started = time.perf_counter()
    results: list[dict] = []
    failed: list[dict] = []

    for idx, estetica in enumerate(ESTETICAS_6):
        lead_id = 2000 + idx  # ids deterministicos por estetica
        t0 = time.perf_counter()
        try:
            template = load_template(estetica)
            variation = build_variation_for(estetica, lead_id)
            html = render_with_variation(template, LEAD_FACT, variation)
            report = validate_template_output(html)
            anim = count_animated_elements(html)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            results.append({
                "estetica": estetica,
                "lead_id": lead_id,
                "theme": variation["theme"],
                "typography": variation["typography"],
                "layout": variation["layout"],
                "motion": variation["motion"],
                "chars": len(html),
                "elapsed_ms": round(elapsed_ms, 2),
                "ok": report["ok"],
                "unresolved": report.get("unresolved_placeholders", []),
                "errors": report.get("errors", []),
                "anim": anim,
            })
        except Exception as exc:  # pragma: no cover
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            failed.append({
                "estetica": estetica,
                "elapsed_ms": round(elapsed_ms, 2),
                "error": repr(exc),
            })

    total_ms = (time.perf_counter() - started) * 1000.0

    print()
    print("-" * 72)
    print(f"RESULTADO — 6 sites em {total_ms:.1f}ms")
    print("-" * 72)
    for r in results:
        flag = "OK" if r["ok"] else "FAIL"
        print(
            f"  [{flag}] {r['estetica']:<13} lead={r['lead_id']} "
            f"chars={r['chars']:>6} t={r['elapsed_ms']:>6.1f}ms "
            f"theme={r['theme']:<18} motion={r['motion']}"
        )
        if not r["ok"]:
            print(f"         errors: {r['errors']}")
            print(f"         unresolved: {r['unresolved']}")
    if failed:
        print()
        print("FALHAS EXCECAO:")
        for f in failed:
            print(f"  {f['estetica']}: {f['error']}")

    # Validacoes
    print()
    print("-" * 72)
    print("VALIDACOES (3 criterios exigidos)")
    print("-" * 72)
    all_ok = all(r["ok"] for r in results)
    print(f"  [1] HTML tem CSS variables:       {'SIM' if all_ok else 'NAO'} (validate_template_output)")
    unresolved_total = sum(len(r["unresolved"]) for r in results)
    print(f"  [2] Sem {{{{}}}} nao substituido:    {'SIM' if unresolved_total == 0 else f'NAO ({unresolved_total} tokens)'} ")
    short = [r for r in results if r["chars"] <= 5000]
    if short:
        print(f"  [3] Chars > 5000:                 NAO — abaixo: {[r['estetica'] for r in short]}")
    else:
        print(f"  [3] Chars > 5000:                 SIM (todos acima)")

    # Agregados
    chars_avg = sum(r["chars"] for r in results) / max(1, len(results))
    chars_min = min(r["chars"] for r in results) if results else 0
    chars_max = max(r["chars"] for r in results) if results else 0
    print()
    print("-" * 72)
    print("AGREGADOS")
    print("-" * 72)
    print(f"  total:        {total_ms:.1f}ms")
    print(f"  chars medios: {chars_avg:.0f}")
    print(f"  chars min:    {chars_min}")
    print(f"  chars max:    {chars_max}")

    # Estetica dominante = maior HTML
    dom = max(results, key=lambda r: r["chars"])
    print(f"  estetica dominante (chars): {dom['estetica']} ({dom['chars']} chars)")

    # Animacao media
    anim_avg = sum(r["anim"]["hints_matched"] for r in results) / max(1, len(results))
    print(f"  anim hints matched (media): {anim_avg:.1f}")
    print()
    print("DETALHE POR ESTETICA (animacao):")
    for r in sorted(results, key=lambda r: r["anim"]["hints_matched"], reverse=True):
        a = r["anim"]
        print(
            f"  {r['estetica']:<13} hints={a['hints_matched']:>4} "
            f"data-anim={a['data_anim_attrs']:>3} "
            f"trans={a['css_transitions']:>3} "
            f"anim={a['css_animations']:>3} "
            f"xform={a['css_transforms']:>3} "
            f"kfs={a['css_keyframes']:>2}"
        )

    # Persistir relatorio
    out = ROOT / "tests" / "_smoke_6_sites_report.json"
    out.write_text(
        json.dumps(
            {
                "total_ms": total_ms,
                "chars_avg": chars_avg,
                "chars_min": chars_min,
                "chars_max": chars_max,
                "dominante_chars": dom["estetica"],
                "results": results,
                "failed": failed,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print()
    print(f"Relatorio salvo em: {out}")

    return 0 if all_ok and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
