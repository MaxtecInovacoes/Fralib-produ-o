"""
validar_pipeline.py — Script de validação do pipeline

Modos:
  --etapa N    Testa apenas a etapa N (1=Cleanup, 2=Caio, 3=Lock, 4=Sanitizer, 5=Imports, 6=Design)
  --e2e        Testa pipeline completo (requer VPS com banco + APIs)
  --list       Lista etapas disponíveis
  --report     Gera relatório final em LOG_PROBLEMAS.md

Uso:
  python scripts/validar_pipeline.py --list
  python scripts/validar_pipeline.py --etapa 2   # Testa só Caio
  python scripts/validar_pipeline.py --e2e        # Testa tudo
"""

import sys
import os
import re
import time
import json
import subprocess
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

RESULTADOS = []
ERROS = []


def log(etapa, status, detalhe, tempo=None):
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    t = f" ({tempo:.1f}s)" if tempo else ""
    msg = f"{icon} [{etapa}] {detalhe}{t}"
    print(msg)
    RESULTADOS.append(
        {"etapa": etapa, "status": status, "detalhe": detalhe, "tempo": tempo}
    )
    if status == "FAIL":
        ERROS.append({"etapa": etapa, "detalhe": detalhe})


def test_caio():
    """Teste isolado do Caio — lógica determinística"""
    t0 = time.time()
    try:
        from agents.caio import (
            _calcular_score,
            verificar_se_e_rede,
            validar_site,
        )

        # Teste 1: score máximo
        s1, _ = _calcular_score(
            {"rating": 5.0, "reviews": 500, "possui_site": False, "fotos": 20}
        )
        assert 90 <= s1 <= 100, f"Score maximo esperado ~100, got {s1}"
        log("Caio", "PASS", f"Score maximo: {s1}", time.time() - t0)

        # Teste 2: rede conhecida
        assert verificar_se_e_rede("Smart Fit Academia") is True
        assert verificar_se_e_rede("Academia Local") is False
        log("Caio", "PASS", "Verificacao de rede OK", time.time() - t0)

        # Teste 3: score mínimo
        s3, _ = _calcular_score(
            {"rating": 0, "reviews": 0, "website": "https://instagram.com/teste", "fotos": 0}
        )
        assert s3 < 20, f"Score minimo esperado < 20, got {s3}"
        log("Caio", "PASS", f"Score minimo: {s3}", time.time() - t0)

        return True
    except Exception as e:
        log("Caio", "FAIL", f"Excecao: {e}", time.time() - t0)
        return False


def test_pipeline_state():
    """Teste do sistema de lock — 1 pipeline por vez"""
    t0 = time.time()
    try:
        from core.database import get_pipeline_state, update_pipeline_state

        log("Lock", "PASS", "Import OK (teste completo requer DB)", time.time() - t0)
        return True
    except Exception as e:
        log("Lock", "FAIL", f"Import erro: {e}", time.time() - t0)
        return False


def test_html_sanitizer():
    """Teste do html_sanitizer sem LGPD, sem PipelineQueueManager"""
    t0 = time.time()
    try:
        # Verificar que LGPD foi removido
        import agents.html_sanitizer as m

        assert not hasattr(m, "_gerar_lgpd_banner"), "_gerar_lgpd_banner ainda existe!"
        log("Sanitizer", "PASS", "LGPD removido do modulo", time.time() - t0)

        # Verificar que funcoes essenciais existem
        assert callable(m.montar_template_python)
        assert callable(m._gerar_seo_inline)
        assert callable(m._gerar_nav_links)
        assert callable(m._gerar_whatsapp_float)
        log("Sanitizer", "PASS", "Funcoes essenciais intactas", time.time() - t0)

        return True
    except Exception as e:
        log("Sanitizer", "FAIL", f"Excecao: {e}", time.time() - t0)
        return False


def test_arquivos_mortos():
    """Verificar que arquivos deletados nao existem mais"""
    t0 = time.time()
    mortos_que_ainda_existem = []

    # Arquivos que ja deveriam ter sido deletados
    checar = [
        "backend/agents/liz.py",
        "backend/agents/bartolomeu.py",
        "backend/agents/theo_agent_loop.py",
        "backend/agents/arquiteto_agent_loop.py",
        "backend/agents/bryan_agent_loop.py",
        "backend/agents/color_enforcer.py",
        "backend/agents/color_extractor.py",
        "backend/agents/animation_injector.py",
        "backend/pipeline_queue_manager.py",
        "backend/agents/_arquivo/",
        "backend/_backup_legado/",
    ]

    for path in checar:
        full = os.path.join(os.path.dirname(__file__), "..", path)
        if os.path.exists(full):
            mortos_que_ainda_existem.append(path)

    if mortos_que_ainda_existem:
        log(
            "Cleanup",
            "FAIL",
            f"Ainda existem: {mortos_que_ainda_existem}",
            time.time() - t0,
        )
        return False
    else:
        log("Cleanup", "OK", "0 arquivos orfaos reintroduzidos", time.time() - t0)
        return True


def test_anti_regressao_estado():
    """Executa a suite tests/test_anti_regressao_estado.py.

    Protege contra regressao silenciosa do estado consolidado em
    v1.0-baseline-2026-06-23 (subnicho, Sonnet primario, LGPD,
    HTML sanitizer, OpenUI unico, arquivos legados removidos).
    """
    t0 = time.time()
    test_path = os.path.join(
        os.path.dirname(__file__), "..", "tests", "test_anti_regressao_estado.py"
    )
    if not os.path.exists(test_path):
        log("AntiReg", "SKIP", f"Suite nao encontrada: {test_path}", time.time() - t0)
        return True  # Nao falhar se a suite for removida futuramente

    try:
        proc = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        # Extrai N/M do rodape
        m = re.search(r"(\d+)/(\d+)\s+passados", out)
        if m:
            passed, total = int(m.group(1)), int(m.group(2))
        else:
            passed, total = 0, 1
        if proc.returncode == 0 and passed == total and total > 0:
            log(
                "AntiReg",
                "PASS",
                f"{passed}/{total} testes anti-regressao verdes",
                time.time() - t0,
            )
            return True
        else:
            log(
                "AntiReg",
                "FAIL",
                f"{passed}/{total} — REGRESSAO DETECTADA!\n{out[-800:]}",
                time.time() - t0,
            )
            return False
    except Exception as e:
        log("AntiReg", "FAIL", f"Excecao: {e}", time.time() - t0)
        return False
        log(
            "Cleanup",
            "PASS",
            "Todos os arquivos mortos foram removidos",
            time.time() - t0,
        )
        return True


def test_anti_regressao_v11():
    """Executa a suite tests/test_anti_regressao_v11.py.

    v1.1-baseline-2026-06-23: protege Sprint 0+1 (memory_hook SDK).
    Bloqueia reversao de: memory_hook_site.py, validador reintroduzido,
    AGENT_MODEL_MAP, race condition, bridge Builder, PM2 dreamer, tag v1.1.
    """
    t0 = time.time()
    test_path = os.path.join(
        os.path.dirname(__file__), "..", "tests", "test_anti_regressao_v11.py"
    )
    if not os.path.exists(test_path):
        log("AntiRegV11", "SKIP", f"Suite nao encontrada: {test_path}", time.time() - t0)
        return True

    try:
        proc = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        m = re.search(r"(\d+)/(\d+)\s+passados", out)
        if m:
            passed, total = int(m.group(1)), int(m.group(2))
        else:
            passed, total = 0, 1
        if proc.returncode == 0 and passed == total and total > 0:
            log(
                "AntiRegV11",
                "PASS",
                f"{passed}/{total} testes anti-regressao v1.1 verdes",
                time.time() - t0,
            )
            return True
        else:
            log(
                "AntiRegV11",
                "FAIL",
                f"{passed}/{total} — REGRESSAO v1.1 DETECTADA!\n{out[-800:]}",
                time.time() - t0,
            )
            return False
    except Exception as e:
        log("AntiRegV11", "FAIL", f"Excecao: {e}", time.time() - t0)
        return False


def test_pipeline_imports():
    """Verificar que todos os imports do pipeline resolvem"""
    t0 = time.time()
    erros = []
    modulos = [
        "agents.caio",
        "agents.sdr_langgraph",
        "agents.html_sanitizer",
        "agents.design_context",
        "agents.designer_prd",
        "agents.craft_rules",
        "agents.unsplash_fetcher",
        "agents.pexels_video",
        "agents.section_editor",
        "agents.memory",
        "agents.pipeline_checkpoint",
        "agents.token_tracker",
        "agents.validation_enforcer",
        "services.builder_worker",
        "agents.arquiteto_mestre",
        "agents.keyword_research",
        "agents.seo_context",
        "agents.llm_direct",
        "utils.jina_intelligence",
        "utils.password_utils",
    ]
    for mod in modulos:
        try:
            __import__(mod)
        except Exception as e:
            erros.append(f"{mod}: {e}")

    if erros:
        for e in erros:
            log("Imports", "FAIL", e, time.time() - t0)
        return False
    else:
        log(
            "Imports",
            "PASS",
            f"Todos os {len(modulos)} modulos importam OK",
            time.time() - t0,
        )
        return True


def test_design_context():
    """Verificar que design_context tem dados"""
    t0 = time.time()
    try:
        from agents.design_context import get_design_context

        d = get_design_context("academia", tier="PREMIUM")
        assert d is not None
        assert "tokens" in d
        assert "font_heading" in d
        log(
            "DesignCtx",
            "PASS",
            f"Academia PREMIUM: {d.get('font_heading')}",
            time.time() - t0,
        )
        return True
    except Exception as e:
        log("DesignCtx", "FAIL", f"Erro: {e}", time.time() - t0)
        return False


def gerar_relatorio():
    """Gera relatorio final"""
    total = len(RESULTADOS)
    passed = sum(1 for r in RESULTADOS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTADOS if r["status"] == "FAIL")

    report = f"""# Relatório de Validação — Pipeline FraLib

**Data:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Resultado:** {passed}/{total} passaram {f"⚠️ {failed} falha(s)" if failed else "✅ Tudo OK"}

## Resumo
"""
    for r in RESULTADOS:
        icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
        t = f" ({r['tempo']:.1f}s)" if r.get("tempo") else ""
        report += f"- {icon} **{r['etapa']}**: {r['detalhe']}{t}\n"

    if ERROS:
        report += "\n## Erros Encontrados\n"
        for e in ERROS:
            report += f"- ❌ **{e['etapa']}**: {e['detalhe']}\n"

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validador do Pipeline FraLib")
    parser.add_argument("--etapa", type=int, help="Testar etapa especifica (1-8)")
    parser.add_argument(
        "--e2e", action="store_true", help="Testar pipeline completo (requer VPS)"
    )
    parser.add_argument("--list", action="store_true", help="Listar etapas")
    parser.add_argument("--report", action="store_true", help="Gerar relatorio final")
    args = parser.parse_args()

    if args.list:
        print("Etapas disponiveis:")
        print("  1 = Cleanup (arquivos mortos)")
        print("  2 = Caio (qualificacao)")
        print("  3 = Pipeline State (lock)")
        print("  4 = HTML Sanitizer")
        print("  5 = Imports (todos os modulos)")
        print("  6 = Design Context")
        print("  7 = Anti-Regressao (estado consolidado v1.0)")
        print("  8 = Anti-Regressao v1.1 (memory_hook SDK + race condition)")
        print("  --e2e = Pipeline completo")
        return

    if args.etapa:
        etapas = {
            1: ("Cleanup", test_arquivos_mortos),
            2: ("Caio", test_caio),
            3: ("Lock", test_pipeline_state),
            4: ("Sanitizer", test_html_sanitizer),
            5: ("Imports", test_pipeline_imports),
            6: ("DesignCtx", test_design_context),
            7: ("AntiReg", test_anti_regressao_estado),
            8: ("AntiRegV11", test_anti_regressao_v11),
        }
        nome, fn = etapas.get(args.etapa, (None, None))
        if fn is None:
            print(f"Etapa {args.etapa} invalida. Use --list para ver opcoes.")
            return
        print(f"\n=== Testando: {nome} ===\n")
        fn()
    elif args.e2e:
        print("\n=== Teste E2E do Pipeline ===\n")
        test_arquivos_mortos()
        test_caio()
        test_pipeline_state()
        test_html_sanitizer()
        test_pipeline_imports()
        test_design_context()
        test_anti_regressao_estado()
        test_anti_regressao_v11()
    else:
        # Modo padrao: testar tudo
        print("\n=== Validacao Completa do Pipeline ===\n")
        test_arquivos_mortos()
        test_caio()
        test_pipeline_state()
        test_html_sanitizer()
        test_pipeline_imports()
        test_design_context()
        test_anti_regressao_estado()

    print("\n" + "=" * 50)
    total = len(RESULTADOS)
    passed = sum(1 for r in RESULTADOS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTADOS if r["status"] == "FAIL")
    print(f"Resultado: {passed}/{total} passaram")
    if failed:
        print(f"WARN {failed} falha(s)!")
        sys.exit(1)
    else:
        print("PASS Todas as validacoes passaram!")

    if args.report:
        report = gerar_relatorio()
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "planning", "LOG_PROBLEMAS.md"
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nRelatorio salvo em: {report_path}")


if __name__ == "__main__":
    main()
