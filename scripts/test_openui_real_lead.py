#!/usr/bin/env python3
"""Teste OpenUI com lead real (do banco/JSON) + injecao de contratos.

Mostra:
- system prompt final (base + contratos) - pra voce ver se estao todos
- raw output do LLM
- HTML gerado
- checklist de contratos respeitados
- contagem de tokens
- tempo total
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except: pass

# Carrega lead real
lead_path = ROOT / ".tmp" / "lead-test" / "lead.json"
lead = json.loads(lead_path.read_text(encoding="utf-8"))

# Monta facts (formato que o render_site_with_builder usa)
business = {
    "name": lead["name"],
    "whatsapp": lead["whatsapp"],
    "phone": lead["phone"],
    "city": lead["city"],
    "state": lead["state"],
    "segment": lead["segment"],
    "rating": lead["rating"],
    "reviews_count": lead["reviews_count"],
    "address": lead["address"],
    "site": lead["site"],
    "hours": lead["hours"],
    "description": lead["description"],
    "instagram": lead["instagram"],
    "photos": lead["photos"],
}
facts = {"business": business, "cidade": lead["city"], "segmento": lead["segment"]}

# Builder prompt (mesmo que o render_site_with_builder monta)
builder_prompt = f"""Crie uma landing page premium para:

Nome: {business['name']}
Cidade: {business['city']} - {business['state']}
Segmento: {business['segment']}
WhatsApp: 55{lead['whatsapp']}
Telefone: {lead['phone']}
Endereco: {business['address']}
Rating: {business['rating']}/5 ({lead['reviews_count']} avaliacoes)
Horario: {business['hours']}
Descricao: {business['description']}
Site: {business['site']}
Instagram: {business['instagram']}

FOTOS REAIS DISPONIVEIS (USE ESTAS URLs):
{chr(10).join('- ' + p for p in business['photos'])}

Requisito FraLib: site Awwwards-grade, dark/moody para CrossFit, copy agressivo, motion premium.
"""


def main() -> int:
    print("=" * 70)
    print("OpenUI com contratos unificados - lead REAL (Crossfit CG)")
    print("=" * 70)
    print(f"lead_id: {lead['id']}")
    print(f"nome: {business['name']}")
    print(f"cidade: {business['city']}/{business['state']}")
    print(f"segmento: {business['segment']}")
    print()

    # 1) Mostra o system prompt injetado
    from services.openui_renderer import OPENUI_SYSTEM_PROMPT
    from services.openui_contracts import build_openui_context_block
    context_block = build_openui_context_block(facts)
    final_prompt = OPENUI_SYSTEM_PROMPT + "\n\n" + context_block

    print("-" * 70)
    print(f"SYSTEM PROMPT (base): {len(OPENUI_SYSTEM_PROMPT)} chars")
    print(f"CONTEXT BLOCK: {len(context_block)} chars")
    print(f"SYSTEM PROMPT FINAL: {len(final_prompt)} chars")
    print("-" * 70)
    print()
    print("Contratos no bloco:")
    for block_name in [
        "SEO FRAMEWORK",
        "DESIGN SYSTEM",
        "MOTION CONTRACT",
        "A11Y CONTRACT",
        "FACTUAL CONTRACT",
        "LGPD BANNER",
        "REGRAS DE DEPLOY",
    ]:
        if block_name in context_block:
            print(f"  OK   {block_name}")
        else:
            print(f"  MISS {block_name}")
    print()

    # 2) Roda OpenUI
    from services.openui_renderer import render_openui_site
    print("Iniciando render_openui_site...")
    started = time.time()
    try:
        result = render_openui_site(
            builder_prompt,
            facts=facts,
            primary_model="claude-opus-4-8",
            fallback_model="claude-sonnet-4-6",
            max_tokens=8000,
            temperature=0.35,
        )
    except Exception as exc:
        elapsed = time.time() - started
        print(f"\nFAIL: {elapsed:.1f}s - {exc}")
        import traceback
        traceback.print_exc()
        return 1

    elapsed = time.time() - started
    print()
    print("=" * 70)
    print(f"OK: {elapsed:.1f}s")
    print("=" * 70)
    print(f"model: {result.model}")
    print(f"html_chars: {len(result.html)}")
    print(f"body_html_chars: {len(result.body_html)}")
    print()
    print("attempts:")
    for a in result.attempts:
        print(f"  - {a.get('model')}: {a.get('status')} ({a.get('elapsed_ms')}ms)")
        if a.get("error"):
            print(f"    err: {a['error'][:150]}")
    print()

    # 3) Auditoria de contratos
    print("-" * 70)
    print("CHECKLIST DE CONTRATOS RESPEITADOS")
    print("-" * 70)
    html = result.html
    checks = [
        ("Skip link", r'class="[^"]*sr-only[^"]*focus:not-sr-only[^"]*"', True),
        ("<main id=\"main\"", r'<main[^>]*id="main"', True),
        ("html lang=pt-BR", r'<html[^>]*lang="pt-BR"', True),
        ("JSON-LD schema.org", r'<script[^>]*type="application/ld\+json"', True),
        ("section sr-only factual", r'<section[^>]*data-fralib-contract[^>]*class="[^"]*sr-only', True),
        ("WhatsApp wa.me", r'wa\.me/55', True),
        ("tel: link", r'href="tel:\+?55', True),
        ("Tailwind CDN", r'cdn\.tailwindcss\.com', True),
        ("data-renderer openui", r'data-builder-engine="openui"', True),
        ("Google Font preconnect", r'fonts\.googleapis\.com', False),
        ("NÃO tem bg-green-700", r'bg-green-700', False),
        ("NÃO tem script inline fora LGPD", None, None),  # checagem manual
        ("Animate tailwind", r'animate-(fade|slide|spin|ping)', False),
        ("prefers-reduced-motion", r'prefers-reduced-motion', False),
        ("Meta description", r'<meta[^>]*name="description"', False),
        ("OG title", r'<meta[^>]*property="og:title"', False),
        ("OG description", r'<meta[^>]*property="og:description"', False),
        ("Canonical", r'<link[^>]*rel="canonical"', False),
        ("Title", r'<title>[^<]+</title>', False),
        ("LGPD banner", None, None),  # checagem manual
    ]
    must_have = 0
    must_pass = 0
    nice = 0
    nice_pass = 0
    for name, pattern, required in checks:
        if pattern is None:
            print(f"  --   {name} (checagem manual abaixo)")
            continue
        match = re.search(pattern, html, re.IGNORECASE)
        present = bool(match)
        if required:
            must_have += 1
            if present:
                must_pass += 1
                print(f"  OK   {name}")
            else:
                print(f"  FAIL {name} (REQUERIDO)")
        else:
            nice += 1
            if present:
                nice_pass += 1
                print(f"  OK   {name}")
            else:
                print(f"  --   {name} (opcional)")
    print()
    print(f"Obrigatorios: {must_pass}/{must_have}")
    print(f"Opcionais:   {nice_pass}/{nice}")

    # 4) Estima tokens
    print()
    print("-" * 70)
    print("CONTAGEM DE TOKENS (estimativa chars/4)")
    print("-" * 70)
    system_tokens_est = len(final_prompt) // 4
    user_tokens_est = len(builder_prompt) // 4
    output_tokens_est = len(result.html) // 4
    print(f"  system prompt:   {len(final_prompt):>7} chars ~ {system_tokens_est:>6} tokens")
    print(f"  user prompt:     {len(builder_prompt):>7} chars ~ {user_tokens_est:>6} tokens")
    print(f"  total input:                        ~ {system_tokens_est + user_tokens_est:>6} tokens")
    print(f"  output (HTML):   {len(result.html):>7} chars ~ {output_tokens_est:>6} tokens")

    # 5) Salva artefatos
    out_dir = ROOT / ".tmp" / "test-openui-real"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(result.html, encoding="utf-8")
    (out_dir / "system_prompt.txt").write_text(final_prompt, encoding="utf-8")
    (out_dir / "user_prompt.txt").write_text(builder_prompt, encoding="utf-8")
    (out_dir / "raw_output.txt").write_text(result.body_html, encoding="utf-8")
    report = {
        "elapsed_seconds": round(elapsed, 1),
        "model": result.model,
        "html_chars": len(result.html),
        "system_prompt_chars": len(final_prompt),
        "context_block_chars": len(context_block),
        "user_prompt_chars": len(builder_prompt),
        "tokens_est": {
            "input": (len(final_prompt) + len(builder_prompt)) // 4,
            "output": len(result.html) // 4,
        },
        "contracts": {
            "must_have_pass": must_pass,
            "must_have_total": must_have,
            "nice_pass": nice_pass,
            "nice_total": nice,
        },
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Artefatos salvos em {out_dir}")
    print(f"  - index.html")
    print(f"  - system_prompt.txt (contratos)")
    print(f"  - user_prompt.txt")
    print(f"  - raw_output.txt")
    print(f"  - report.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
