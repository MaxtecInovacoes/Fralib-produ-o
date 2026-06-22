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
    print("Etapa 1: chamar LLM direto (sem validador) para ver o que gera...")
    from services.vite_react_renderer import (
        _call_vite_react_llm,
        _compose_vite_user_prompt,
        extract_vite_project_files,
        prepare_vite_project_files,
        _select_vite_react_models_for_run,
    )
    from backend.core.proxy_models import PROXY_BUILDER_MODEL, PROXY_LIGHT_MODEL

    cascade = _select_vite_react_models_for_run(PROXY_BUILDER_MODEL, PROXY_LIGHT_MODEL)
    print(f"cascade: {cascade}")
    print()

    raw = ""
    used_model = ""
    last_err = ""
    for model in cascade:
        try:
            print(f"tentando {model}...")
            started_m = time.time()
            prompt = _compose_vite_user_prompt(builder_prompt, facts=facts)
            raw = _call_vite_react_llm(prompt, model=model, max_tokens=16000, temperature=0.55)
            used_model = model
            print(f"  OK {model} em {time.time()-started_m:.1f}s ({len(raw)} chars)")
            break
        except Exception as e:
            last_err = str(e)[:200]
            print(f"  FAIL {model}: {last_err}")

    if not raw:
        print(f"FATAL: nenhum modelo retornou. Ultimo erro: {last_err}")
        return 1

    files = prepare_vite_project_files(extract_vite_project_files(raw), facts=facts)

    print()
    print("=" * 60)
    print(f"LLM ({used_model}) gerou {len(files)} arquivos:")
    print("=" * 60)
    for path in sorted(files.keys()):
        print(f"  {path} ({len(files[path])} chars)")

    # Componentes esperados
    expected = [
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
    print("completude:")
    for c in expected:
        marker = "OK  " if c in files else "MISS"
        sz = len(files[c]) if c in files else 0
        print(f"  {marker} {c} ({sz} chars)")

    # Persiste o source cru para inspecao
    raw_dump = workspace / "llm_raw_output.txt"
    raw_dump.write_text(raw, encoding="utf-8")
    print(f"\nLLM raw output: {raw_dump} ({len(raw)} chars)")

    # Persiste report
    report = {
        "used_model": used_model,
        "cascade": cascade,
        "elapsed_seconds_total": round(time.time() - started, 1) if 'started' in dir() else 0,
        "raw_chars": len(raw),
        "files_count": len(files),
        "missing_components": [c for c in expected if c not in files],
    }
    (workspace / "test-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
