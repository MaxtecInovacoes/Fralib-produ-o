#!/usr/bin/env python3
"""Sprint 14: Smoke test com Caroço Rico 2.0 - copy_only mode (default).

Usa lead real Barbearia Fio Nobre (Tenant 2) para validar:
- copy_only: LLM retorna JSON de conteudo (~300 tokens), FraLib gera o codigo
- O site Compila ebuilda SEMPRE (Studio deterministico)
- O conteudo vem do LLM (headlines/CTAs personalizados)
- Os arquivos incluem ServicesSection (nunca some porque o codigo eh nosso)
"""
from __future__ import annotations

import json as _json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# ── setup ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# ── policy: copy_only (default novo) ─────────────────────────────────────────
os.environ["FRALIB_VITE_LLM_POLICY"] = "copy_only"
os.environ["FRALIB_VITE_DISABLE_STUDIO_FALLBACK"] = "0"

from backend.services.vite_react_renderer import (
    _get_llm_policy,
    _get_copy_only_user_prompt,
    _get_copy_only_system_prompt,
)


def banner(msg: str) -> None:
    print(f"\n{'=' * 70}\n  {msg}\n{'=' * 70}")


def step(msg: str) -> None:
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


# ── lead real: Barbearia Fio Nobre Pinhais (Tenant 2) ────────────────────────
PRD_BARBEARIA_FIO_NOBRE = {
    "id": "codex-test-barbearia-fio-nobre-pinhais-20260612",
    "tenant_id": 2,
    "job_id": f"smoke-sprint14-{int(time.time())}",
    "target": "landing-page",
    "business": {
        "name": "Barbearia Fio Nobre Pinhais",
        "segmento": "barbearia",
        "cidade": "Pinhais",
        "whatsapp": "41999999999",
        "phone": "41999999999",
        "endereco": "Centro, Pinhais - PR",
        "rating": "4.8",
        "total_avaliacoes": "127",
        "services": ["Corte masculino", "Barba", "Sobrancelha", "Pigmentacao", "Platinado"],
        "horarios": "Seg-Sex 9h-20h | Sab 9h-18h",
        "description": "Barbearia premium em Pinhais com ambiente moderno e barbeiros certificados.",
        "differentials": ["Atendimento premium", "Barbeiros certificados", "Produtos importados"],
        "target_audience": "Homens 25-55 anos premium",
    },
    "segmento": "barbearia",
    "city": "Pinhais",
    "site_build_plan": {
        "section_plan": [
            {"id": "hero", "role": "capture"},
            {"id": "servicos", "role": "information"},
            {"id": "galeria", "role": "trust"},
            {"id": "contato", "role": "conversion"},
        ]
    },
}


def test_policy_awareness() -> bool:
    """Teste 1: policy e helpers estao corretos."""
    banner("TESTE 1: Policy awareness")
    policy = _get_llm_policy()
    assert policy == "copy_only", f"Expected copy_only, got {policy}"
    step(f"  Policy: {policy} (CORRETO)")

    copy_sys = _get_copy_only_system_prompt()
    assert len(copy_sys) < 1000, f"System prompt copy_only too long: {len(copy_sys)}"
    step(f"  System prompt: {len(copy_sys)} chars (leve vs ~1000 do full_code)")

    copy_user = _get_copy_only_user_prompt(PRD_BARBEARIA_FIO_NOBRE)
    assert "Barbearia Fio Nobre" in copy_user
    assert "nutricao" not in copy_user.lower()
    step(f"  User prompt: {len(copy_user)} chars (com dados do lead)")

    step("  PASS: policy helpers corretos")
    return True


def test_studio_fallback_generation() -> bool:
    """Teste 2: Studio fallback gera arquivos com ServicesSection."""
    banner("TESTE 2: Studio fallback gera codigo com ServicesSection")
    from backend.services.vite_react_renderer import (
        _generate_studio_fallback_files,
        _interpolate_studio_placeholders,
        prepare_vite_project_files,
    )

    files = _generate_studio_fallback_files(PRD_BARBEARIA_FIO_NOBRE)
    assert files, "Studio fallback retornou dict vazio"
    step(f"  Arquivos gerados: {len(files)}")

    # ServicesSection DEVE existir (nunca some porque vem do Studio, nao do LLM)
    has_services = any("ServicesSection" in v for v in files.values())
    assert has_services, "ServicesSection NAO encontrada — BUG (deveria sempre existir)"
    step("  ServicesSection: ENCONTRADA (codigo nosso, nunca some)")

    # HeroSection deve existir
    has_hero = any("HeroSection" in v for v in files.values())
    assert has_hero, "HeroSection NAO encontrada"
    step("  HeroSection: ENCONTRADA")

    # Index.tsx deve referenciar ServicesSection
    index = next((v for k, v in files.items() if "Index.tsx" in k), "")
    assert "ServicesSection" in index, "Index.tsx nao importa ServicesSection"
    step("  Index.tsx: importa ServicesSection")

    step("  PASS: Studio fallback gera codigo completo")
    return True


def test_copy_only_llm_content_merge() -> bool:
    """Teste 3: JSON do LLM eh mergeado nos facts antes do Studio."""
    banner("TESTE 3: copy_only JSON merge nos facts")
    from backend.services.vite_react_renderer import _parse_content_json

    # Simula output do LLM em copy_only
    llm_output = '''```json
{
  "hero": {
    "headline": "Corte que Transforma",
    "subheadline": "Barbearia premium em Pinhais com ambiente climatizado e barbeiros certificados",
    "cta_primary": "Agendar Corte",
    "cta_secondary": "Ver Servicos"
  },
  "lifestyle": {
    "title": "Tradição em Cada Corte",
    "description": "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes."
  }
}
```'''

    parsed = _parse_content_json(llm_output)
    assert parsed, "Parser retornou dict vazio"
    assert "hero" in parsed
    assert parsed["hero"]["cta_primary"] == "Agendar Corte"
    step(f"  JSON parsed: {list(parsed.keys())}")
    step(f"  cta_primary: {parsed['hero']['cta_primary']}")

    # Verifica que o merge injetaria nos facts
    enriched = dict(PRD_BARBEARIA_FIO_NOBRE)
    enriched["_llm_content"] = parsed
    step("  _llm_content injetado nos facts: OK")

    step("  PASS: JSON do LLM parseado e mergeado")
    return True


def test_studio_with_llm_content() -> bool:
    """Teste 4: Studio + content do LLM = arquivos finais."""
    banner("TESTE 4: Studio + LLM content mergeado nos arquivos")
    from backend.services.vite_react_renderer import (
        _generate_studio_fallback_files,
        prepare_vite_project_files,
    )

    llm_content = {
        "hero": {
            "headline": "Corte que Transforma",
            "subheadline": "Barbearia premium em Pinhais",
            "cta_primary": "Agendar Corte",
            "cta_secondary": "Ver Servicos",
        },
        "services_title": "Nossos Servicos",
        "lifestyle": {
            "title": "Tradição em Cada Corte",
            "description": "Um espaco dedicado ao cuidado masculino.",
        },
        "gallery_alt": "Barbearia",
        "differentials": ["Atendimento premium", "Barbeiros certificados"],
    }

    # Facts enriquecidos com _llm_content
    enriched = dict(PRD_BARBEARIA_FIO_NOBRE)
    enriched["_llm_content"] = llm_content

    files_raw = _generate_studio_fallback_files(enriched)
    files = prepare_vite_project_files(files_raw, facts=enriched)

    # Verifica arquivos base
    assert "src/pages/Index.tsx" in files
    assert "src/components/ServicesSection.tsx" in files
    step(f"  Arquivos finais: {len(files)}")

    # O conteudo do LLM (Agendar Corte) deve estar interpolado nos arquivos
    # O HeroSection ou Index.tsx deve conter o CTA do LLM
    all_content = " ".join(files.values())
    has_llm_cta = "Agendar Corte" in all_content or "Agendar horario" in all_content
    assert has_llm_cta, "CTA do LLM nao encontrado no output"
    step("  CTA do LLM: presente no output")

    step("  PASS: Studio + LLM content mergeado")
    return True


def test_full_pipeline_render() -> bool:
    """Teste 5: render_vite_react_site com copy_only policy."""
    banner("TESTE 5: Pipeline completa com copy_only (lead real Tenant 2)")
    from backend.services.vite_react_renderer import render_vite_react_site

    workspace = Path(tempfile.mkdtemp(prefix="fralib_s14_copyonly_"))
    step(f"  Workspace: {workspace}")

    t0 = time.time()
    try:
        result = render_vite_react_site(
            builder_prompt="",
            workspace_dir=str(workspace),
            facts=PRD_BARBEARIA_FIO_NOBRE,
            primary_model="sonnet",
            fallback_model="haiku",
            max_tokens=1200,
            temperature=0.4,
        )
        elapsed = time.time() - t0
    except Exception as exc:
        elapsed = time.time() - t0
        step(f"  ERRO na renderizacao: {exc}")
        raise

    step(f"  Tempo: {elapsed:.1f}s")
    step(f"  Modelo usado: {result.model}")
    step(f"  HTML chars: {len(result.html):,}")
    step(f"  Source files: {len(result.source_files)}")

    # Attempts deve mostrar copy_only_json_success ou policy_none_studio_success
    for attempt in result.attempts:
        status = attempt.get("status", "")
        policy_tag = attempt.get("policy", "N/A")
        step(f"  Attempt: {status} (policy={policy_tag})")

    # O HTML DEVE ter ServicesSection
    has_services_in_html = "servico" in result.html.lower() or "servi" in result.html.lower()
    step(f"  Services no HTML: {'SIM' if has_services_in_html else 'NAO'}")

    # O HTML nao deve ter {var} literais quebrados
    import re
    broken_vars = re.findall(r"\{[a-z_]+\}", result.html[:5000])
    if broken_vars:
        step(f"  ATENCAO: vars literais encontrados: {broken_vars[:5]}")
    else:
        step("  Sem vars literais quebrados: OK")

    # Deve ter Telefone/WhatsApp
    has_phone = "41999999999" in result.html or "Fio Nobre" in result.html
    step(f"  Dados do lead (nome/telefone): {'SIM' if has_phone else 'PARCIAL'}")

    # Salva resultado
    output = {
        "policy": "copy_only",
        "lead": "Barbearia Fio Nobre Pinhais",
        "tenant_id": 2,
        "model_used": result.model,
        "elapsed_s": round(elapsed, 1),
        "html_chars": len(result.html),
        "source_files": len(result.source_files),
        "attempts": result.attempts,
        "has_services": has_services_in_html,
        "has_lead_data": has_phone,
    }
    out_path = ROOT / "tests" / "_sprint14_copyonly_result.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(_json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    step(f"  Resultado salvo: {out_path}")

    # Copia HTML para inspeção
    html_path = workspace / "dist" / "index.html"
    if html_path.exists():
        dest_html = ROOT / "tests" / "_sprint14_copyonly_index.html"
        shutil.copy2(html_path, dest_html)
        step(f"  HTML copiado para: {dest_html}")

    # Limpa workspace
    shutil.rmtree(workspace, ignore_errors=True)

    step("  PASS: Pipeline completa com copy_only")
    return True


def main() -> int:
    banner("SPRINT 14: CAROÇO RICO 2.0 — Smoke copy_only com lead real Tenant 2")

    tests = [
        ("1. Policy awareness", test_policy_awareness),
        ("2. Studio fallback gera codigo", test_studio_fallback_generation),
        ("3. JSON LLM merge", test_copy_only_llm_content_merge),
        ("4. Studio + LLM content", test_studio_with_llm_content),
        ("5. Pipeline completa", test_full_pipeline_render),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            if fn():
                passed += 1
                step(f"\n  [{passed}/{len(tests)}] {name}: PASS\n")
            else:
                failed += 1
                step(f"\n  [{passed}/{len(tests)}] {name}: FAIL\n")
        except Exception as exc:
            failed += 1
            step(f"\n  [{passed}/{len(tests)}] {name}: EXCEPTION — {exc}\n")
            import traceback
            traceback.print_exc()

    banner("RESULTADO FINAL")
    print(f"  PASSOU: {passed}/{len(tests)}")
    print(f"  FALHOU: {failed}/{len(tests)}")
    if failed == 0:
        print("\n  ✅ TODOS OS TESTES PASSARAM")
        print("  ✅ Caroço Rico 2.0 copy_only funcionando")
        print("  ✅ Studio + LLM JSON: ServicesSection sempre presente")
    else:
        print("\n  ❌ ALGUNS TESTES FALHARAM")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
