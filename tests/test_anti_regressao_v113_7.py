"""Testes anti-regressao v1.13.7 - Sprint 11.7 (validacao npm registry).

Sprint 11.6 fechou 3 bugs no vite_react_renderer.py.
Sprint 11.7 fecha o BUG MAIS CRITICO: pacotes que retornam 404 no npm registry.

Bug: FIXED_PACKAGE_JSON declarava @radix-ui/react-button e @radix-ui/react-card,
mas esses pacotes NAO EXISTEM no npm registry (curl retorna 404). npm install
falha -> studio fallback gera site -> openui_fallback. Suite anterior so
testava que os pacotes estavam no dict, NAO que existiam no npm.

Fix:
- Remove @radix-ui/react-button (404) e @radix-ui/react-card (404)
- Adiciona @radix-ui/react-slot (200, base do shadcn Button)
- Card shadcn e div pura com classes Tailwind, nao precisa de radix
- Atualiza suites v1.13, v1.13.5, v1.13.6 para refletir a verdade

Valida:
- FIXED_PACKAGE_JSON NAO tem @radix-ui/react-button
- FIXED_PACKAGE_JSON NAO tem @radix-ui/react-card
- FIXED_PACKAGE_JSON tem @radix-ui/react-slot
- TODOS os pacotes do FIXED_PACKAGE_JSON existem no npm registry (200 OK)
"""
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


def _check_npm_exists(pkg_name: str, version: str = "") -> bool:
    """Verifica se pacote existe no npm registry (200) ou retorna 404."""
    url = f"https://registry.npmjs.org/{pkg_name}"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════
# TESTES Sprint 11.7
# ════════════════════════════════════════════════════════════════════

def test_1_removed_packages_not_in_deps():
    """Sprint 11.7: pacotes 404 removidos do FIXED_PACKAGE_JSON."""
    print("[TESTE 1/6] Pacotes 404 removidos...")
    from backend.services import vite_config

    deps = vite_config.FIXED_PACKAGE_JSON["dependencies"]
    removed = ["@radix-ui/react-button", "@radix-ui/react-card"]

    for pkg in removed:
        assert pkg not in deps, f"Pacote 404 {pkg} NAO deveria estar em deps"

    print(f"  OK @radix-ui/react-button removido (404 no npm)")
    print(f"  OK @radix-ui/react-card removido (404 no npm)")


def test_2_replacement_packages_added():
    """Sprint 11.7: @radix-ui/react-slot adicionado (200 OK no npm)."""
    print("\n[TESTE 2/6] @radix-ui/react-slot adicionado...")
    from backend.services import vite_config

    deps = vite_config.FIXED_PACKAGE_JSON["dependencies"]
    assert "@radix-ui/react-slot" in deps, "react-slot deveria estar em deps"

    print("  OK @radix-ui/react-slot adicionado (200 OK no npm)")


def test_3_all_deps_exist_in_npm_registry():
    """Sprint 11.7: TODOS os pacotes do FIXED_PACKAGE_JSON existem no npm.

    Validacao real via HEAD request ao registry.npmjs.org.
    Se algum retornar 404, o teste falha (protege contra regressao).
    Pula com skip se sem internet.
    """
    print("\n[TESTE 3/6] Todos os pacotes existem no npm registry...")
    from backend.services import vite_config

    deps = vite_config.FIXED_PACKAGE_JSON["dependencies"]

    # Verifica cada pacote (skip se sem internet)
    failed = []
    skipped = []
    for pkg, version in deps.items():
        if not _check_npm_exists(pkg):
            # Verifica se eh erro de rede ou 404 real
            try:
                req = urllib.request.Request(
                    f"https://registry.npmjs.org/{pkg}", method="HEAD"
                )
                urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    failed.append((pkg, version, "404 NOT FOUND"))
                else:
                    skipped.append((pkg, version, f"HTTP {e.code}"))
            except Exception as e:
                skipped.append((pkg, version, f"network: {type(e).__name__}"))

    if skipped and not failed:
        print(f"  SKIP {len(skipped)} pacotes (sem internet)")
        return

    if failed:
        msg = "\n".join(f"    {pkg}@{v} -> {status}" for pkg, v, status in failed)
        raise AssertionError(f"Pacotes 404 no npm:\n{msg}")

    print(f"  OK {len(deps)} pacotes todos existem (200 OK no npm registry)")


def test_4_shadcn_templates_no_removed_imports():
    """Sprint 11.7: shadcn Button/Card .tsx nao importam pacotes removidos."""
    print("\n[TESTE 4/6] Templates shadcn nao importam pacotes 404...")
    from pathlib import Path

    templates_dir = ROOT / "backend" / "services" / "vite_templates" / "src" / "components" / "ui"
    if not templates_dir.exists():
        print("  SKIP templates dir nao existe")
        return

    removed = ["@radix-ui/react-button", "@radix-ui/react-card"]
    for tsx in templates_dir.glob("*.tsx"):
        content = tsx.read_text(encoding="utf-8")
        for pkg in removed:
            assert pkg not in content, (
                f"{tsx.name} importa pacote 404 {pkg}"
            )

    print(f"  OK {len(list(templates_dir.glob('*.tsx')))} templates .tsx sem imports 404")


def test_5_vite_prompts_no_removed_imports():
    """Sprint 11.7: vite_prompts nao menciona pacotes 404 nos exemplos."""
    print("\n[TESTE 5/6] vite_prompts sem pacotes 404...")
    from backend.services import vite_prompts

    prompt = vite_prompts.VITE_REACT_SYSTEM_PROMPT

    # Pode ter em DOCS (explicando que NAO existem), mas nao em EXEMPLOS de import
    # Verifica que nao ha `from "@radix-ui/react-button"` no prompt
    assert 'from "@radix-ui/react-button"' not in prompt
    assert 'from "@radix-ui/react-card"' not in prompt

    print("  OK Prompt nao tem `from @radix-ui/react-button`")
    print("  OK Prompt nao tem `from @radix-ui/react-card`")


def test_6_existing_packages_intact():
    """Sprint 11.7: NAO quebrou pacotes que ja existiam."""
    print("\n[TESTE 6/6] Pacotes pre-existentes preservados...")
    from backend.services import vite_config

    deps = vite_config.FIXED_PACKAGE_JSON["dependencies"]
    dev_deps = vite_config.FIXED_PACKAGE_JSON["devDependencies"]

    # Pacotes que existem no npm e devem continuar existindo
    must_exist = {
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
        "@radix-ui/react-dialog": "^1.1.0",
        "@radix-ui/react-tabs": "^1.1.0",
        "class-variance-authority": "^0.7.0",
        "clsx": "^2.1.0",
        "tailwind-merge": "^2.5.0",
        "lucide-react": "^0.468.0",
        "motion": "^11.11.0",
    }

    for pkg, ver in must_exist.items():
        assert pkg in deps, f"{pkg} deveria estar em deps"
        assert deps[pkg] == ver, f"{pkg} deveria ter versao {ver}, tem {deps[pkg]}"

    # Dev deps
    assert "vite" in dev_deps
    assert dev_deps["vite"] == "^6.0.0"

    print(f"  OK {len(must_exist)} pacotes pre-existentes preservados")
    print(f"  OK devDep vite@^6.0.0 preservada")


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TESTES ANTI-REGRESSAO v1.13.7 - Sprint 11.7 (npm registry validation)")
    print("=" * 80)

    test_1_removed_packages_not_in_deps()
    test_2_replacement_packages_added()
    test_3_all_deps_exist_in_npm_registry()
    test_4_shadcn_templates_no_removed_imports()
    test_5_vite_prompts_no_removed_imports()
    test_6_existing_packages_intact()

    print("\n" + "=" * 80)
    print("TODOS OS TESTES PASSARAM (6/6)")
    print("Sprint 11.7 (v1.13.7) - pacotes 404 corrigidos")
    print("@radix-ui/react-slot substitui @radix-ui/react-button (404)")
    print("Card shadcn agora e div pura (sem dep radix inexistente)")
    print("=" * 80)
