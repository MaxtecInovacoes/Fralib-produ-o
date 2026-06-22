#!/usr/bin/env python3
"""Teste do OpenUI renderer restaurado (HTML estatico, sem Vite/node_modules)."""

from __future__ import annotations

import json
import os
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

facts = {
    "business": {
        "name": "Crossfit Campo Grande",
        "whatsapp": "67999887766",
        "phone": "67999887766",
        "city": "Campo Grande",
        "segment": "academia",
        "rating": "4.8",
        "hours": "Seg-Sex 6h-22h / Sab 8h-14h",
        "address": "Rua Bahia, 1500 - Centro, Campo Grande/MS",
    },
    "cidade": "Campo Grande",
    "segmento": "academia",
    "design_system": "crossfit-box",
}

builder_prompt = """Gere uma landing page premium para Crossfit Campo Grande, box de CrossFit localizado no Centro de Campo Grande/MS.

Estilo: dark/moody (preto #0a0a0a, vermelho sangue #dc2626), tipografia display bold (Oswald), motion agressivo, hero full-bleed com imagem de CrossFit. Secoes: Navbar (logo + WhatsApp CTA), Hero (titulo "TREINE COMO UM ATLETA" + CTA matricule-se), About (manifesto da box), Services (CrossFit, Open Box, Personal), Gallery (grid de fotos), Reviews (3 depoimentos), Location (Rua Bahia, 1500, Centro, CG/MS + horarios), ContactCTA (WhatsApp 67999887766), Footer (LGPD).

Nome: Crossfit Campo Grande. Cidade: Campo Grande, MS. Rating 4.8. WhatsApp 67999887766.
"""


def main() -> int:
    print("=" * 60)
    print("OpenUI renderer — teste isolado (HTML estatico, sem Vite)")
    print("=" * 60)
    print(f"lead: {facts['business']['name']} ({facts['business']['city']})")
    print()
    print("Iniciando render_openui_site...")

    from services.openui_renderer import render_openui_site

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
        print(f"\nFAIL: OpenUI crashou em {elapsed:.1f}s")
        print(f"Erro: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    elapsed = time.time() - started
    print()
    print("=" * 60)
    print(f"OK: {elapsed:.1f}s")
    print("=" * 60)
    print()
    print(f"model: {result.model}")
    print(f"html_chars: {len(result.html)}")
    print(f"body_html_chars: {len(result.body_html)}")
    print()
    print("attempts:")
    for a in result.attempts:
        print(f"  - model={a.get('model')} status={a.get('status')} elapsed_ms={a.get('elapsed_ms')}")
        if a.get("error"):
            print(f"    error: {a['error'][:200]}")
    print()
    print("HTML preview (primeiros 800 chars):")
    print("-" * 60)
    print(result.html[:800])
    print("-" * 60)

    # Salva o HTML completo
    out_dir = ROOT / ".tmp" / "test-openui"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / "index.html"
    out_html.write_text(result.html, encoding="utf-8")
    print(f"\nHTML salvo em {out_html}")
    print(f"Tamanho: {len(result.html)} chars ({len(result.html.encode('utf-8'))} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
