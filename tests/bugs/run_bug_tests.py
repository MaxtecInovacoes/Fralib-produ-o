"""
run_bug_tests.py
=================
Runner de testes para os 2 bugs corrigidos.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


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


def test_bug_enqueue_caio():
    r = TestRunner()
    r.section("BUG #1: _enqueue_caio import")

    # 1. Funcao existe em inventory
    from backend.services.lead_supply_inventory import _enqueue_caio as real_fn
    r.assert_(callable(real_fn), "_enqueue_caio existe em lead_supply_inventory")

    # 2. Funcao e re-exportada em storage (compat)
    from backend.services.lead_supply_storage import _enqueue_caio as compat_fn
    r.assert_(callable(compat_fn), "_enqueue_caio re-exportada de lead_supply_storage")

    # 3. Sao a mesma funcao (re-export)
    r.assert_(real_fn is compat_fn, "Funcao original == funcao re-exportada")

    # 4. Hunter.py importa de inventory (correto)
    hunter_path = PROJECT_ROOT / "backend" / "services" / "lead_supply_providers" / "hunter.py"
    hunter_content = hunter_path.read_text(encoding="utf-8")
    r.assert_("from backend.services.lead_supply_inventory import" in hunter_content,
              "hunter.py importa de lead_supply_inventory")

    # 5. Nenhum import de _enqueue_caio de lead_supply_storage
    suspicious = []
    for py_file in (PROJECT_ROOT / "backend").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if "from backend.services.lead_supply_storage import" in content and "_enqueue_caio" in content:
            # Verifica se eh a re-exportacao (OK) ou import direto (bug)
            if "_enqueue_caio as _real_fn" not in content:
                suspicious.append(str(py_file.relative_to(PROJECT_ROOT)))
    r.assert_(len(suspicious) == 0,
              f"Nenhum import direto problematico ({len(suspicious)} encontrados)")

    return r


def test_bug_lead_qualificado():
    r = TestRunner()
    r.section("BUG #2: LeadQualificado validation")

    from backend.utils.agente1_hunter_v2 import LeadQualificado, LeadRaw
    from backend.utils.safe_lead_qualificado import safe_qualificar

    # 1. safe_qualificar aceita LeadRaw
    lr = LeadRaw(nome="OK", cidade="SP", segmento="academia")
    lq = safe_qualificar(lr, {"nome": "OK"})
    r.assert_(lq.lead.nome == "OK", "safe_qualificar aceita LeadRaw")

    # 2. safe_qualificar aceita dict
    lq2 = safe_qualificar(None, {"nome": "Test", "cidade": "RJ"})
    r.assert_(lq2.lead.nome == "Test", "safe_qualificar aceita dict quando lead_raw=None")

    # 3. safe_qualificar recupera quando lead_raw e string
    lq3 = safe_qualificar("string_invalida", {"nome": "Bug", "cidade": "MG"})
    r.assert_(lq3.lead.nome == "Bug", "safe_qualificar recupera de string")

    # 4. safe_qualificar funciona com lead_dict completo
    lq4 = safe_qualificar(None, {
        "nome": "Lead Dict", "cidade": "BA", "segmento": "restaurante",
        "telefone": "71999999999", "website": "https://x.com"
    })
    r.assert_(lq4.lead.cidade == "BA", "safe_qualificar usa todos campos do dict")

    # 5. safe_qualificar funciona com lead_dict vazio
    lq5 = safe_qualificar(None, {})
    r.assert_(lq5.lead.nome == "desconhecido", "safe_qualificar tem defaults")

    # 6. safe_qualificar NUNCA quebra (sempre retorna LeadQualificado)
    lq6 = safe_qualificar(None, None)
    r.assert_(lq6 is not None, "safe_qualificar nunca retorna None")

    # 7. lead_obj no orchestrator foi substituido
    orch_path = PROJECT_ROOT / "backend" / "endpoints" / "pipeline_orchestrator_service.py"
    orch_content = orch_path.read_text(encoding="utf-8")
    r.assert_("safe_qualificar(_lead_raw_r, _ld, log_fn=_log)" in orch_content,
              "orchestrator usa safe_qualificar (linha 494)")

    # 8. lead_obj no reprocess foi substituido
    reproc_path = PROJECT_ROOT / "backend" / "endpoints" / "pipeline_lead_flow_helpers.py"
    reproc_content = reproc_path.read_text(encoding="utf-8")
    r.assert_("safe_qualificar(lead_raw, lead_dict)" in reproc_content,
              "reprocess usa safe_qualificar (linha 288)")

    return r


def test_regression_tenant_failures():
    r = TestRunner()
    r.section("REGRESSAO: 2 bugs nao voltam")

    # 1. safe_qualificar existe e funciona
    from backend.utils.safe_lead_qualificado import safe_qualificar
    r.assert_(safe_qualificar is not None, "safe_qualificar existe")

    # 2. lead_supply_storage re-exporta _enqueue_caio
    from backend.services.lead_supply_storage import _enqueue_caio
    r.assert_(callable(_enqueue_caio), "lead_supply_storage expoe _enqueue_caio")

    # 3. Nenhum arquivo de backend cria LeadQualificado() fora do safe_lead_qualificado
    bad_uses = []
    for py_file in (PROJECT_ROOT / "backend").rglob("*.py"):
        if "__pycache__" in str(py_file) or "safe_lead_qualificado.py" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'LeadQualificado\s*\(\s*lead\s*=', content):
            bad_uses.append(str(py_file.relative_to(PROJECT_ROOT)))
    r.assert_(len(bad_uses) == 0,
              f"Todos usam safe_qualificar ({len(bad_uses)} usos diretos restantes)")

    # 4. Sistema de diagnostico classifica os 2 bugs
    from backend.services.error_diagnostics import diagnosticar
    d1 = diagnosticar("cannot import _enqueue_caio")
    r.assert_(d1["categoria"] == "code_bug", "_enqueue_caio -> code_bug")

    d2 = diagnosticar("LeadQualificado Input should be a valid dictionary")
    r.assert_(d2["categoria"] == "data_quality", "LeadQualificado validation -> data_quality")

    # 5. Auto-fix categoriza corretamente
    from backend.services.auto_fix import tentar_auto_fix
    fix1 = tentar_auto_fix("ImportError cannot import _enqueue_caio")
    r.assert_(fix1.categoria == "code_bug", "auto-fix identifica code_bug")

    # 6. Arquivos criticos existem
    files_exist = [
        "backend/utils/safe_lead_qualificado.py",
        "backend/services/error_diagnostics.py",
        "backend/services/auto_fix.py",
        "backend/services/alerting.py",
    ]
    for f in files_exist:
        full = PROJECT_ROOT / f
        r.assert_(full.exists(), f"{f} existe")

    return r


def main():
    print("=" * 60)
    print(" ECC LOOP - TESTES BUG FIXES (2 bugs corrigidos)")
    print("=" * 60)

    r1 = test_bug_enqueue_caio()
    r2 = test_bug_lead_qualificado()
    r3 = test_regression_tenant_failures()

    total = r1.passed + r1.failed + r2.passed + r2.failed + r3.passed + r3.failed
    passed = r1.passed + r2.passed + r3.passed
    failed = total - passed

    print("\n" + "=" * 60)
    print(f" RESULTADO: {passed}/{total} PASS")
    print("=" * 60)

    if failed == 0:
        print("\n[SUCESSO] Bugs corrigidos! Sistema validado.")
    else:
        print(f"\n[FALHA] {failed} testes falharam - revisar implementacao")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())