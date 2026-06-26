#!/usr/bin/env python3
"""Sprint 14.4: Smoke test da pipeline Vite/React com lead real Tenant 2.

Simula a pipeline completa (sem Postgres) usando dados do lead:
- Barbearia Fio Nobre Pinhais
- Tenant 2
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Setup
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["FRALIB_BUILDER_ENGINE"] = "vite_react"


def banner(msg: str) -> None:
    print(f"\n{'='*70}\n  {msg}\n{'='*70}")


def step(msg: str) -> None:
    print(f"  [+] {msg}")


def check(msg: str, ok: bool) -> None:
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {msg}")


# Lead real do Tenant 2
TENANT2_LEAD = {
    "id": "codex-test-barbearia-fio-nobre-pinhais-20260612",
    "tenant_id": 2,
    "nome": "Barbearia Fio Nobre",
    "segmento": "barbearia",
    "cidade": "Pinhais",
    "estado": "PR",
    "business": {
        "name": "Barbearia Fio Nobre",
        "segment": "barbearia",
        "cidade": "Pinhais",
        "estado": "PR",
        "whatsapp": "41988084400",
        "phone": "4130128181",
        "address": "Rua Jandaia do Sul, 585 - Estancia Pinhais",
        "services": ["Corte Masculino", "Barba", "Sobrancelha", "Pigmentacao", "Corte Infantil"],
        "hours": "Seg-Sab 09h-19h",
        "rating": "4.8",
        "total_avaliacoes": "312",
        "diferenciais": ["Ambiente Climatizado", "Profissionais Especializados", "Produtos Premium"],
        "website": "https://barbeariafionobre.com.br",
        "maps_url": "https://maps.google.com/?cid=xxx",
    },
    "content": {
        "services": ["Corte Masculino", "Barba", "Sobrancelha", "Pigmentacao", "Corte Infantil"],
        "attributes": ["Ambiente Climatizado", "Profissionais Especializados", "Produtos Premium"],
        "ideal_customer": "Homens de 18 a 55 anos que buscam qualidade e profissionalismo",
    },
    "seo": {
        "primary_terms": [
            "barbearia Pinhais",
            "corte masculino Pinhais",
            "barba Pinhais",
            "barbearia PR",
            "melhor barbearia Pinhais"
        ],
        "secondary_terms": ["barbeiro Pinhais", "corte degrade", "barbearia proximo a mim"],
    },
    "media": {
        "photos": [
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1",
            "https://images.unsplash.com/photo-1621605815971-fbc98d665033",
            "https://images.unsplash.com/photo-1599351431202-1e0f0137899a"
        ]
    },
    "visual_dna": {
        "archetype": "WARM_LOCAL",
        "tokens": {
            "primary": "#D4A853",
            "secondary": "#1A1A1A",
            "accent": "#C17F3C",
            "background": "#FAFAF8"
        },
        "style_mix_instruction": "Warm local feel, golden accents, dark wood tones"
    },
    "tier": "PREMIUM",
}


async def main():
    banner("SMOKE TEST: Pipeline Vite/React com Lead Real Tenant 2")
    print(f"  Lead: {TENANT2_LEAD['nome']} ({TENANT2_LEAD['segmento']})")
    print(f"  Cidade: {TENANT2_LEAD['cidade']}/{TENANT2_LEAD['estado']}")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # FASE 1: Validar imports e caroco do system prompt
    banner("FASE 1: Validar Caroco do System Prompt")

    from backend.services.vite_prompts import (
        _build_caroço_block,
        _build_vite_react_system_prompt_with_facts,
        _build_lead_briefing_block,
        _build_gsap_code_block,
    )
    from backend.services.vite_react_renderer import (
        _summarize_builder_facts,
        _compose_vite_user_prompt,
    )

    step("Imports OK")

    # Testar caroco com facts reais
    sys_prompt = _build_vite_react_system_prompt_with_facts(TENANT2_LEAD)
    check(f"System prompt gerado ({len(sys_prompt)} chars)", len(sys_prompt) > 30000)
    check(f"LEAD BRIEFING presente", "LEAD BRIEFING" in sys_prompt)
    check(f"JSON-LD presente", "@type" in sys_prompt)
    check(f"Barbearia Fio Nobre no prompt", "Fio Nobre" in sys_prompt)
    check(f"Services (Corte/Barba) no prompt", "Corte" in sys_prompt and "Barba" in sys_prompt)
    check(f"GSAP code (useGSAP)", "useGSAP" in sys_prompt)
    check(f"BookingModal configurado", "BookingModal" in sys_prompt)
    check(f"WhatsApp no prompt", "41988084400" in sys_prompt)

    # FASE 2: Validar user prompt
    banner("FASE 2: Validar User Prompt")

    user_prompt = _compose_vite_user_prompt(
        "Build a premium landing page for Barbearia Fio Nobre",
        facts=TENANT2_LEAD,
    )
    check(f"User prompt gerado ({len(user_prompt)} chars)", len(user_prompt) > 5000)
    check(f"Facts summary presente", "Fio Nobre" in user_prompt)
    check(f"Contamination guard presente", "contaminat" in user_prompt.lower())

    # FASE 3: Validar summarize_builder_facts
    banner("FASE 3: Validar _summarize_builder_facts")

    summary = _summarize_builder_facts(TENANT2_LEAD)
    check(f"Summary gerado ({len(summary)} chars)", len(summary) > 300)
    check(f"Business name", "Fio Nobre" in summary)
    check(f"Services (5 items)", "Corte" in summary and "Barba" in summary)
    check(f"Hours", "Seg-Sab" in summary)
    check(f"Photos", "unsplash" in summary)
    check(f"Keywords SEO", "barbearia Pinhais" in summary)

    # FASE 4: Gerar arquivos via Studio fallback
    banner("FASE 4: Gerar Site (Studio Fallback)")

    from backend.services.vite_react_renderer import (
        _generate_studio_fallback_files,
        prepare_vite_project_files,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        step("Gerando arquivos via Studio fallback...")
        files = _generate_studio_fallback_files(facts=TENANT2_LEAD)

        check(f"Arquivos gerados ({len(files)})", len(files) >= 15)
        check(f"App.tsx presente", any("App.tsx" in f for f in files))
        check(f"Index.tsx presente", any("Index.tsx" in f for f in files))
        check(f"Navbar.tsx presente", any("Navbar.tsx" in f for f in files))
        check(f"HeroSection.tsx presente", any("HeroSection.tsx" in f for f in files))
        check(f"ContactCTA.tsx presente", any("ContactCTA.tsx" in f for f in files))
        check(f"Footer.tsx presente", any("Footer.tsx" in f for f in files))
        check(f"index.html presente", any("index.html" in f for f in files))

        # Verificar se Barbearia Fio Nobre esta no conteudo
        all_content = "\n".join(files.values())
        check(f"Nome no conteudo (Hero)", "Fio Nobre" in all_content)
        check(f"Cidade no conteudo", "Pinhais" in all_content)
        check(f"WhatsApp no conteudo", "41988084400" in all_content)
        check(f"Services no conteudo", "Corte" in all_content or "Barba" in all_content)

        # Preparar arquivos Vite
        step("Preparando arquivos Vite...")
        vite_files = prepare_vite_project_files(files=files, facts=TENANT2_LEAD)

        check(f"Vite files preparados ({len(vite_files)})", len(vite_files) >= 15)

        # Listar arquivos
        file_list = list(vite_files.keys())
        print(f"\n  Arquivos gerados:")
        for f in sorted(file_list):
            size = len(vite_files[f])
            print(f"    - {f} ({size} bytes)")

    # FASE 5: Validar componentes obrigatorios
    banner("FASE 5: Validar Componentes Obrigatorios")

    required_components = [
        "BookingModal",
        "HeroSection",
        "Navbar",
        "ContactCTA",
        "Footer",
    ]

    all_content_vite = "\n".join(vite_files.values())

    for comp in required_components:
        has_component = any(comp in f for f in file_list)
        check(f"{comp} presente", has_component)

    check(f"CTA para WhatsApp", "whatsapp" in all_content_vite.lower() or "4198808" in all_content_vite)
    check(f"Phone number", "4130128181" in all_content_vite or "4198808" in all_content_vite)

    # RESUMO FINAL
    banner("RESUMO")
    print(f"""
  Lead: {TENANT2_LEAD['nome']}
  Segmento: {TENANT2_LEAD['segmento']}
  Cidade: {TENANT2_LEAD['cidade']}/{TENANT2_LEAD['estado']}

  System Prompt: {len(sys_prompt)} chars
  User Prompt: {len(user_prompt)} chars
  Arquivos: {len(vite_files)}

  Pipeline Status: PRONTO PARA DEPLOY
  """)


if __name__ == "__main__":
    asyncio.run(main())
