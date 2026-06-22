#!/usr/bin/env python3
"""Teste isolado do Builder 100% LLM apos remover os 12 templates FraLib Studio.

Fato mockado: Academia ficticia em Campo Grande. Roda render_vite_react_site,
mede tempo, valida que o site sai (LLM puro ou Studio fallback) e lista os
arquivos gerados para inspecao visual.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env")
except Exception:
    pass

# Mock: academia Crossfit ficticia
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
        "photos": [
            "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1200",
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1200",
            "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=1200",
            "https://images.unsplash.com/photo-1554284126-aa88f22d8b74?w=1200",
        ],
        "reviews": [
            {"autor": "Lucas M.", "texto": "Treino pesado, ambiente motivador, coaches atenciosos. Voltarei sempre.", "rating": 5},
            {"autor": "Ana P.", "texto": "Melhor box de CG. WOD varia todo dia, nunca fica chato.", "rating": 5},
            {"autor": "Roberto S.", "texto": "Open box flexivel, da pra treinar em qualquer horario. Preco justo.", "rating": 4},
        ],
    },
    "cidade": "Campo Grande",
    "segmento": "academia",
    "media": {
        "photos": [
            "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1200",
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1200",
        ],
    },
    "design_system": "crossfit-box",
}

# Prompt minimo: o _compose_vite_user_prompt do vite_react_renderer monta o prompt real
# com base nos facts + design system + DESIGN.md
builder_prompt = """Gere um site de academia Crossfit premium em Campo Grande, MS.

Estilo: dark/moody, vermelho/preto, tipografia bold (Oswald/Montserrat), motion
agressivo, GSAP ScrollTrigger, parallax no hero, contadores animados para
"alunos ativos" e "WODs realizados". Hero com video background ou imagem
full-bleed de atleta fazendo snatch. Secoes: Navbar (logo + CTA Matricule-se
+ WhatsApp), Hero (titulo agressivo + subtitulo + CTA), About (manifesto da
box, valores, metodologia), Services (CrossFit, Open Box, Personal, Assessoria),
Gallery (grid de fotos), Lifestyle (depoimentos visuais), Reviews (3-5 cards
com rating), Location (mapa + endereco + horarios), ContactCTA (WhatsApp
destaque + form simples), Footer (links + LGPD). LGPD banner obrigatorio.

Use React 19 + Vite 7 + Tailwind v4. Motion: framer-motion. Stack:
- React + Vite + TypeScript
- Tailwind v4 (com @import "tailwindcss"; no TOPO do index.css, antes de qualquer @import de fonts)
- framer-motion
- lucide-react (icones)

IMPORTANTE: cada componente deve ser um arquivo .tsx separado em src/components/.
Todos esses arquivos devem estar presentes no output:
- src/components/Navbar.tsx
- src/components/HeroSection.tsx
- src/components/AboutSection.tsx
- src/components/GallerySection.tsx
- src/components/ServicesSection.tsx
- src/components/LifestyleSection.tsx
- src/components/ReviewsSection.tsx
- src/components/LocationSection.tsx
- src/components/ContactCTA.tsx
- src/components/Footer.tsx
- src/components/LgpdBanner.tsx

Use os dados de facts para preencher. Nome: Crossfit Campo Grande. WhatsApp:
67999887766. Cidade: Campo Grande, MS. Endereco: Rua Bahia, 1500 - Centro.
Horarios: Seg-Sex 6h-22h / Sab 8h-14h. Rating: 4.8. 3 reviews reais.
"""


def main() -> int:
    workspace = ROOT / ".tmp" / "test-builder-llm-only"
    workspace.mkdir(parents=True, exist_ok=True)
    # limpa build anterior
    for stale in ("dist", "src", "node_modules", "package.json", "vite.config.ts"):
        target = workspace / stale
        if target.is_dir():
            import shutil

            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    print("=" * 60)
    print("Builder 100% LLM — teste isolado (sem templates FraLib Studio)")
    print("=" * 60)
    print(f"workspace: {workspace}")
    print(f"design system: {facts.get('design_system')}")
    print(f"lead: {facts['business']['name']} ({facts['business']['city']})")
    print()
    print("Iniciando render_vite_react_site...")
    started = time.time()
    try:
        from services.vite_react_renderer import render_vite_react_site

        result = render_vite_react_site(
            builder_prompt,
            workspace_dir=workspace,
            facts=facts,
        )
    except Exception as exc:
        elapsed = time.time() - started
        print(f"\nFAIL: Builder crashou em {elapsed:.1f}s")
        print(f"Erro: {exc}")
        return 1

    elapsed = time.time() - started
    print()
    print("=" * 60)
    print(f"OK: {elapsed:.1f}s")
    print("=" * 60)
    print()
    print(f"engine: {result.model}")
    print(f"index_path: {result.index_path}")
    print(f"html_chars: {len(result.html)}")
    print(f"source_files: {len(result.source_files)}")
    print()
    print("attempts:")
    for a in result.attempts:
        elapsed_ms = a.get("elapsed_ms", 0)
        print(f"  - model={a.get('model')} status={a.get('status')} elapsed_ms={elapsed_ms}")
        if a.get("error"):
            print(f"    error: {a['error'][:300]}")
    print()
    print("source files (alphabetical):")
    for path in sorted(result.source_files.keys()):
        content = result.source_files[path]
        print(f"  {path} ({len(content)} chars)")

    # Verifica completude
    expected_components = [
        "src/components/Navbar.tsx",
        "src/components/HeroSection.tsx",
        "src/components/AboutSection.tsx",
        "src/components/GallerySection.tsx",
        "src/components/ServicesSection.tsx",
        "src/components/LifestyleSection.tsx",
        "src/components/ReviewsSection.tsx",
        "src/components/LocationSection.tsx",
        "src/components/ContactCTA.tsx",
        "src/components/Footer.tsx",
        "src/components/LgpdBanner.tsx",
    ]
    print()
    print("completude dos 11 componentes:")
    missing = []
    for c in expected_components:
        if c in result.source_files:
            content = result.source_files[c]
            print(f"  OK   {c} ({len(content)} chars)")
        else:
            print(f"  MISS {c}")
            missing.append(c)
    if missing:
        print(f"\n{len(missing)}/{len(expected_components)} componentes faltando!")
        print("LLM provavelmente omitiu. Resultado pode ser Studio fallback.")
    else:
        print(f"\nTodos os {len(expected_components)} componentes presentes!")

    # Persiste resultado
    out = {
        "elapsed_seconds": round(elapsed, 1),
        "engine": result.model,
        "html_chars": len(result.html),
        "source_files_count": len(result.source_files),
        "attempts": result.attempts,
        "missing_components": missing,
        "index_path": result.index_path,
    }
    report = workspace / "test-report.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nrelatorio salvo em {report}")
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
