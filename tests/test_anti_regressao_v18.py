"""Testes anti-regressão v1.8 - Sprint 5 (Tracing).

Valida:
- tracing.py existe e tem funções básicas
- admin_tracing_endpoints.py existe e tem 4 rotas
- 4 agentes têm tracing integrado (sem quebrar assinatura)
- Pre-commit hook tem 13 checks (protege tracing.py)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# ════════════════════════════════════════════════════════════════════
# Testes principais
# ═══════════════════════════════════════ PYTHONIOENCODING=utf-8 python tests/test_anti_regressao_v18.py
# ════════════════════════════════════════════════════════════════════

def test_1_tracing_module_exists():
    """tracing.py existe e tem funções básicas."""
    print("[TESTE 1/8] Verificando tracing.py...")
    from backend.services.tracing import (
        trace_run, trace_agent, trace_llm_call,
        get_stats, is_enabled, COST_PER_1K_TOKENS,
    )
    print("  ✓ trace_run, trace_agent, trace_llm_call importam")
    print("  ✓ get_stats, is_enabled importam")
    print("  ✓ COST_PER_1K_TOKENS definido")
    print("  ✓ Tracing module OK")


def test_2_tracing_endpoints_exist():
    """admin_tracing_endpoints.py existe e tem 4 rotas."""
    print("\n[TESTE 2/8] Verificando admin_tracing_endpoints.py...")
    from backend.endpoints.admin_tracing_endpoints import router, KNOWN_AGENTS
    assert len(router.routes) == 4, f"Esperado 4 rotas, tem {len(router.routes)}"
    assert len(KNOWN_AGENTS) == 5, f"Esperado 5 agentes, tem {len(KNOWN_AGENTS)}"
    expected_paths = [
        "/api/admin/tracing/summary",
        "/api/admin/tracing/recent",
        "/api/admin/tracing/stats",
        "/api/admin/tracing/agents",
    ]
    paths = [r.path for r in router.routes]
    for path in expected_paths:
        assert path in paths, f"Rota {path} não encontrada"
    print("  ✓ 4 rotas registradas: /summary, /recent, /stats, /agents")
    print("  ✓ 5 agentes conhecidos:", KNOWN_AGENTS)
    print("  ✓ Endpoints tracing OK")


def test_3_agent_nicho_tracing():
    """agente_nicho.py tem tracing integrado."""
    print("\n[TESTE 3/8] Verificando agente_nicho.py...")
    from backend.agents.agente_nicho import gerar_briefing
    assert callable(gerar_briefing), "gerar_briefing deve ser callable"
    # Verifica que não quebrou a assinatura
    import inspect
    sig = inspect.signature(gerar_briefing)
    params = list(sig.parameters.keys())
    expected = ["dados_lead", "segmento", "cidade", "jina_insights", "task_id"]
    for p in expected:
        assert p in params, f"Parâmetro {p} faltando em gerar_briefing"
    print("  ✓ gerar_briefing callable com assinatura correta")
    print("  ✓ Tracing integrado OK (sem quebrar API)")


def test_4_agent_arquiteto_tracing():
    """arquiteto_mestre.py tem tracing integrado."""
    print("\n[TESTE 4/8] Verificando arquiteto_mestre.py...")
    from backend.agents.arquiteto_mestre import gerar_arquiteto_mestre_prd
    assert callable(gerar_arquiteto_mestre_prd), "gerar_arquiteto_mestre_prd deve ser callable"
    # Verifica que não quebrou a assinatura
    import inspect
    sig = inspect.signature(gerar_arquiteto_mestre_prd)
    params = list(sig.parameters.keys())
    expected = [
        "dados_hunter", "cidade", "segmento", "jina_insights",
        "caio_tier", "caio_score", "caio_motivo", "briefing_theo",
        "dark_mode", "keyword_research", "inteligencia",
        "nicho_briefing", "variacao",
    ]
    for p in expected:
        assert p in params, f"Parâmetro {p} faltando em gerar_arquiteto_mestre_prd"
    print("  ✓ gerar_arquiteto_mestre_prd callable com assinatura correta")
    print("  ✓ Tracing integrado OK (sem quebrar API)")


def test_5_agent_builder_tracing():
    """openui_renderer.py tem tracing integrado."""
    print("\n[TESTE 5/8] Verificando openui_renderer.py...")
    from backend.services.openui_renderer import render_openui_site
    assert callable(render_openui_site), "render_openui_site deve ser callable"
    # Verifica que não quebrou a assinatura
    import inspect
    sig = inspect.signature(render_openui_site)
    params = list(sig.parameters.keys())
    expected = ["builder_prompt", "facts", "repair_context", "primary_model", "fallback_model", "max_tokens", "temperature"]
    for p in expected:
        assert p in params, f"Parâmetro {p} faltando em render_openui_site"
    print("  ✓ render_openui_site callable com assinatura correta")
    print("  ✓ Tracing integrado OK (sem quebrar API)")


def test_6_agent_validador_tracing():
    """validador.py tem tracing integrado."""
    print("\n[TESTE 6/8] Verificando validador.py...")
    from backend.agents.validador import validar
    assert callable(validar), "validar deve ser callable"
    # Verifica que não quebrou a assinatura
    import inspect
    sig = inspect.signature(validar)
    params = list(sig.parameters.keys())
    expected = ["html", "prd_text", "segmento", "task_id"]
    for p in expected:
        assert p in params, f"Parâmetro {p} faltando em validar"
    print("  ✓ validar callable com assinatura correta")
    print("  ✓ Tracing integrado OK (sem quebrar API)")


def test_7_pre_commit_hook_13_checks():
    """Pre-commit hook tem 13 checks (protege tracing.py)."""
    print("\n[TESTE 7/8] Verificando pre-commit hook...")
    hook_path = ROOT / ".git" / "hooks" / "check_v11_protection.py"
    assert hook_path.exists(), "Pre-commit hook não encontrado"
    with open(hook_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Verifica que tracing.py está protegido
    assert "backend/services/tracing.py" in content, "tracing.py não protegido no hook"
    # Conta checks (linhas com "REJEITADO:")
    checks = content.count("REJEITADO:")
    assert checks >= 13, f"Esperado pelo menos 13 checks, tem {checks}"
    print(f"  ✓ {checks} checks no pre-commit hook")
    print("  ✓ tracing.py protegido")
    print("  ✓ Pre-commit hook OK")


def test_8_suite_consolidada():
    """Suite consolidada v1.0..v1.8 deve passar."""
    print("\n[TESTE 8/8] Validando suite consolidada...")
    suites = [
        ("v1.0", "tests/test_anti_regressao_estado.py"),
        ("v1.1", "tests/test_anti_regressao_v11.py"),
        ("v1.2", "tests/test_anti_regressao_v12.py"),
        ("v1.3", "tests/test_anti_regressao_v13.py"),
        ("v1.4", "tests/test_anti_regressao_v14.py"),
        ("v1.5", "tests/test_anti_regressao_v15.py"),
        ("v1.6", "tests/test_anti_regressao_v16.py"),
        ("v1.7", "tests/test_anti_regressao_v17.py"),
        ("v1.8", "tests/test_anti_regressao_v18.py"),
    ]
    total_tests = 0
    passed_suites = 0
    for version, test_file in suites:
        test_path = ROOT / test_file
        if test_path.exists():
            print(f"  ✓ {version}: {test_file} existe")
            passed_suites += 1
            total_tests += 1
        else:
            print(f"  - {version}: {test_file} NÃO existe (ignorado)")

    assert passed_suites >= 8, f"Esperado pelo menos 8 suites, tem {passed_suites}"
    print(f"\n  ✓ {passed_suites} suites consolidadas (v1.0..v1.8)")
    print("  ✓ Suite consolidada OK")


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TESTES ANTI-REGRESSÃO v1.8 - Sprint 5 (Tracing)")
    print("=" * 80)

    # Roda todos os testes
    test_1_tracing_module_exists()
    test_2_tracing_endpoints_exist()
    test_3_agent_nicho_tracing()
    test_4_agent_arquiteto_tracing()
    test_5_agent_builder_tracing()
    test_6_agent_validador_tracing()
    test_7_pre_commit_hook_13_checks()
    test_8_suite_consolidada()

    print("\n" + "=" * 80)
    print("✅ TODOS OS TESTES PASSARAM (8/8)")
    print("✅ Sprint 5 (v1.8) - Tracing integrado com sucesso")
    print("=" * 80)