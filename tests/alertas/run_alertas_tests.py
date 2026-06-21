"""
run_alertas_tests.py
=====================
Runner de testes para sistema de alertas (diagnostico + auto_fix + alerting).
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DIAG = PROJECT_ROOT / "backend" / "services" / "error_diagnostics.py"
AUTO = PROJECT_ROOT / "backend" / "services" / "auto_fix.py"
ALERT = PROJECT_ROOT / "backend" / "services" / "alerting.py"
EP = PROJECT_ROOT / "backend" / "endpoints" / "diagnostico_endpoints.py"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def assert_(self, cond, msg):
        if cond:
            self.passed += 1
            print(f"  [OK] {msg}")
        else:
            self.failed += 1
            print(f"  [FAIL] {msg}")

    def section(self, name):
        print(f"\n=== {name} ===")


def test_diagnostics():
    r = TestRunner()
    r.section("ERROR DIAGNOSTICS")

    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

    from backend.services.error_diagnostics import classificar, diagnosticar

    # Categoria
    r.assert_(classificar("SSL SYSCALL error: EOF") == "transient", "SSL -> transient")
    r.assert_(classificar("timeout after 30s") == "transient", "timeout -> transient")
    r.assert_(classificar("HTTP 429 Too Many Requests") == "rate_limit", "429 -> rate_limit")
    r.assert_(classificar("ValidationError: Input should be a valid dict") == "data_quality", "Validation -> data_quality")
    r.assert_(classificar("ImportError: cannot import _enqueue_caio") == "code_bug", "ImportError -> code_bug")
    r.assert_(classificar("502 Bad Gateway") == "external_api", "502 -> external_api")
    r.assert_(classificar("401 Unauthorized") == "auth", "401 -> auth")
    r.assert_(classificar("out of memory") == "resource", "OOM -> resource")
    r.assert_(classificar("xyz random error") == "unknown", "unknown -> unknown")

    # Diagnostico especifico
    d = diagnosticar("SSL SYSCALL error: EOF detected")
    r.assert_("titulo" in d and "banco" in d["titulo"].lower(), "SSL tem titulo didatico")
    r.assert_("causa" in d and len(d["causa"]) > 10, "SSL tem causa")

    d2 = diagnosticar("cannot import name '_enqueue_caio' from module")
    r.assert_("bug" in d2["titulo"].lower() or "modulo" in d2["titulo"].lower(), "_enqueue_caio tem titulo")

    d3 = diagnosticar("LeadQualificado Input should be a valid dictionary")
    r.assert_("lead" in d3["titulo"].lower() or "dados" in d3["titulo"].lower(), "Pydantic tem titulo")

    d4 = diagnosticar("qualquer coisa aleatoria xyz")
    r.assert_(d4["categoria"] == "unknown", "Fallback para unknown")
    r.assert_("acao_automatica" in d4, "Tem acao_automatica mesmo no fallback")

    return r


def test_auto_fix():
    r = TestRunner()
    r.section("AUTO FIX")

    from backend.services.auto_fix import tentar_auto_fix, FixResult

    # Transient: deve retornar retry com delay
    fix = tentar_auto_fix("SSL SYSCALL timeout", tentativas_anteriores=0, max_tentativas_total=3)
    r.assert_(fix.categoria == "transient", "Transient categorizado")
    r.assert_(fix.sucesso, "Transient tem auto-fix")
    r.assert_(fix.proxima_tentativa_em_segundos and fix.proxima_tentativa_em_segundos >= 5, "Delay >= 5s")

    # Code bug: nao tem auto-fix
    fix2 = tentar_auto_fix("ImportError cannot import", tentativas_anteriores=0, max_tentativas_total=3)
    r.assert_(fix2.categoria == "code_bug", "Code bug categorizado")
    r.assert_(not fix2.sucesso, "Code bug nao auto-fixa")

    # Auth: requer intervencao humana
    fix3 = tentar_auto_fix("401 Unauthorized invalid api key", tentativas_anteriores=0, max_tentativas_total=3)
    r.assert_(fix3.categoria == "auth", "Auth categorizado")
    r.assert_(not fix3.sucesso, "Auth nao auto-fixa")

    # Limite de tentativas
    fix4 = tentar_auto_fix("timeout", tentativas_anteriores=3, max_tentativas_total=3)
    r.assert_(not fix4.sucesso, "Limite respeitado")
    r.assert_("Limite" in fix4.mensagem or "atingido" in fix4.mensagem, "Mensagem clara")

    # Rate limit tem espera maior
    fix5 = tentar_auto_fix("429 rate limit exceeded", tentativas_anteriores=0)
    r.assert_(fix5.categoria == "rate_limit", "Rate limit OK")
    r.assert_(fix5.proxima_tentativa_em_segundos == 60, "Rate limit espera 60s")

    return r


def test_alerting():
    r = TestRunner()
    r.section("ALERTING")

    # Verifica que o modulo existe e tem funcoes esperadas
    from backend.services.alerting import send_alert, Alert, AlertLevel
    r.assert_(callable(send_alert), "send_alert existe")
    r.assert_(callable(Alert), "Alert class existe")
    r.assert_(AlertLevel.INFO == "info", "AlertLevel.INFO")
    r.assert_(AlertLevel.WARNING == "warning", "AlertLevel.WARNING")
    r.assert_(AlertLevel.CRITICAL == "critical", "AlertLevel.CRITICAL")

    # Verifica que o modulo tem as funcoes de health check
    from backend.services.alerting import (
        check_db_pool_health,
        check_llm_error_rate,
        check_pipeline_jobs,
        check_redis_health,
        check_llm_budget,
        run_health_checks,
        check_and_alert,
        hook_pos_falha,
    )
    r.assert_(callable(check_db_pool_health), "check_db_pool_health existe")
    r.assert_(callable(check_llm_error_rate), "check_llm_error_rate existe")
    r.assert_(callable(check_pipeline_jobs), "check_pipeline_jobs existe")
    r.assert_(callable(check_redis_health), "check_redis_health existe")
    r.assert_(callable(check_llm_budget), "check_llm_budget existe")
    r.assert_(callable(run_health_checks), "run_health_checks existe")
    r.assert_(callable(check_and_alert), "check_and_alert existe")
    r.assert_(callable(hook_pos_falha), "hook_pos_falha existe")

    # hook_pos_falha retorna dict com auto_fix
    res = hook_pos_falha("SSL SYSCALL error", fase="hunter", tenant_id=2)
    r.assert_("auto_fix" in res, "hook retorna auto_fix")
    r.assert_("alerta" in res, "hook retorna alerta")

    return r


def test_endpoint_file():
    r = TestRunner()
    r.section("ENDPOINT ARQUIVO")

    r.assert_(EP.exists(), f"{EP.name} existe")
    content = EP.read_text(encoding="utf-8")
    r.assert_("diagnostico" in content.lower(), "Endpoint tem 'diagnostico'")
    r.assert_("router" in content, "Tem APIRouter")
    r.assert_("diagnostic" in content or "diagnostico" in content, "Endpoint importa modulo")

    return r


def main():
    print("=" * 60)
    print(" ECC LOOP - TESTES ALERTAS DIDATICOS")
    print("=" * 60)

    results = []
    for fn in [test_diagnostics, test_auto_fix, test_alerting, test_endpoint_file]:
        r = fn()
        results.extend([(s, m) for s, m in zip(["PASS"] * r.passed + ["FAIL"] * r.failed,
                                                  [None] * (r.passed + r.failed))])

    total = sum(r.passed + r.failed for r in [test_diagnostics(), test_auto_fix(), test_alerting(), test_endpoint_file()])
    passed = sum(r.passed for r in [test_diagnostics(), test_auto_fix(), test_alerting(), test_endpoint_file()])
    failed = total - passed

    print("\n" + "=" * 60)
    print(f" RESULTADO: {passed}/{total} PASS")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    # Calcular totais corretamente
    r1 = test_diagnostics()
    r2 = test_auto_fix()
    r3 = test_alerting()
    r4 = test_endpoint_file()
    total = r1.passed + r1.failed + r2.passed + r2.failed + r3.passed + r3.failed + r4.passed + r4.failed
    passed = r1.passed + r2.passed + r3.passed + r4.passed
    print("\n" + "=" * 60)
    print(f" RESULTADO: {passed}/{total} PASS")
    print("=" * 60)
    sys.exit(0 if passed == total else 1)