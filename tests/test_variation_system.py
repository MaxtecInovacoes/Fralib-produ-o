"""test_variation_system.py — Suite standalone do sistema 4-eixos (Sprint 4A.3).

6 testes:
    1. test_select_estetica_deterministic
    2. test_select_theme_matches_estetica_coherence
    3. test_select_motion_matches_estetica_coherence
    4. test_generate_variation_returns_all_4_axes
    5. test_two_different_leads_may_get_different_look
    6. test_same_lead_id_always_same_variation

Standalone runner: nao usa pytest/cov. Executar:
    PYTHONIOENCODING=utf-8 python tests/test_variation_system.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def _import_system():
    from backend.templates._system import (
        select_estetica,
        select_theme,
        select_typography,
        select_layout,
        select_motion,
        generate_variation,
    )
    from backend.templates._system.variation import (
        ESTETICAS,
        THEMES,
        TYPOGRAPHIES,
        LAYOUTS,
        MOTIONS,
        COHERENCE,
    )
    return {
        "select_estetica": select_estetica,
        "select_theme": select_theme,
        "select_typography": select_typography,
        "select_layout": select_layout,
        "select_motion": select_motion,
        "generate_variation": generate_variation,
        "ESTETICAS": ESTETICAS,
        "THEMES": THEMES,
        "TYPOGRAPHIES": TYPOGRAPHIES,
        "LAYOUTS": LAYOUTS,
        "MOTIONS": MOTIONS,
        "COHERENCE": COHERENCE,
    }


class TestVariationSystem:
    """Suite do sistema 4-eixos (6 testes)."""

    @staticmethod
    def test_select_estetica_deterministic():
        """select_estetica(lead_id, segmento) sempre retorna o mesmo valor."""
        sys_mod = _import_system()
        select_estetica = sys_mod["select_estetica"]
        ESTETICAS = sys_mod["ESTETICAS"]

        # Mesmo input -> mesmo output (chama 5x)
        for _ in range(5):
            r = select_estetica(lead_id=42, segmento="clinica_estetica")
            assert r in ESTETICAS, f"Estetica invalida: {r}"

        # 100 chamadas identicas produzem 100 resultados identicos
        results = {select_estetica(42, "clinica_estetica") for _ in range(100)}
        assert len(results) == 1, f"Determinismo quebrado: {results}"

    @staticmethod
    def test_select_theme_matches_estetica_coherence():
        """select_theme SEMPRE retorna tema coerente com a estetica."""
        sys_mod = _import_system()
        select_estetica = sys_mod["select_estetica"]
        select_theme = sys_mod["select_theme"]
        COHERENCE = sys_mod["COHERENCE"]

        # Amostra 50 leads em segmentos variados
        seen_pairs = set()
        for lead_id in range(1, 51):
            segmento = f"segmento_{lead_id % 7}"
            estetica = select_estetica(lead_id, segmento)
            theme = select_theme(lead_id, estetica)
            valid_themes = COHERENCE[estetica]["themes"]

            assert theme in valid_themes, (
                f"Tema '{theme}' invalido para estetica '{estetica}'. "
                f"Esperado um de: {valid_themes}"
            )
            seen_pairs.add((estetica, theme))

        # Sanity: pelo menos 3 pares (estetica, theme) distintos foram cobertos
        assert len(seen_pairs) >= 3, f"Pouca variacao observada: {seen_pairs}"

    @staticmethod
    def test_select_motion_matches_estetica_coherence():
        """select_motion SEMPRE retorna motion coerente com a estetica."""
        sys_mod = _import_system()
        select_estetica = sys_mod["select_estetica"]
        select_motion = sys_mod["select_motion"]
        COHERENCE = sys_mod["COHERENCE"]

        for lead_id in range(1, 51):
            segmento = f"segmento_{lead_id % 11}"
            estetica = select_estetica(lead_id, segmento)
            motion = select_motion(lead_id, estetica)
            valid_motions = COHERENCE[estetica]["motions"]

            assert motion in valid_motions, (
                f"Motion '{motion}' invalida para estetica '{estetica}'. "
                f"Esperado um de: {valid_motions}"
            )

    @staticmethod
    def test_generate_variation_returns_all_4_axes():
        """generate_variation retorna dict com TODOS os 4+1 eixos."""
        sys_mod = _import_system()
        generate_variation = sys_mod["generate_variation"]
        ESTETICAS = sys_mod["ESTETICAS"]
        THEMES = sys_mod["THEMES"]
        TYPOGRAPHIES = sys_mod["TYPOGRAPHIES"]
        LAYOUTS = sys_mod["LAYOUTS"]
        MOTIONS = sys_mod["MOTIONS"]

        v = generate_variation(lead_id=99, segmento="barbearia_premium")

        required_keys = {
            "estetica", "theme", "typography", "layout", "motion",
            "template_path", "css_vars_inline",
        }
        assert set(v.keys()) == required_keys, (
            f"Chaves esperadas: {required_keys}. Obtido: {set(v.keys())}"
        )
        assert v["estetica"] in ESTETICAS
        assert v["theme"] in THEMES
        assert v["typography"] in TYPOGRAPHIES
        assert v["layout"] in LAYOUTS
        assert v["motion"] in MOTIONS
        assert v["template_path"].endswith("index.html"), \
            f"template_path nao eh HTML: {v['template_path']}"
        assert "<style" in v["css_vars_inline"], \
            f"css_vars_inline nao contem <style>: {v['css_vars_inline']}"
        assert "--motion-duration" in v["css_vars_inline"]
        assert "--layout-container-max" in v["css_vars_inline"]

    @staticmethod
    def test_two_different_leads_may_get_different_look():
        """Dois leads diferentes podem (e geralmente devem) receber looks diferentes.

        Nao eh garantido que TODOS os leads recebam tudo diferente (o pool
        tem overlap), mas se gerarmos 50 leads esperamos ver pelo menos
        3 esteticas distintas e 3 temas distintos.
        """
        sys_mod = _import_system()
        generate_variation = sys_mod["generate_variation"]

        esteticas = set()
        temas = set()
        layouts = set()
        for lead_id in range(1, 51):
            v = generate_variation(lead_id, f"seg_{lead_id}")
            esteticas.add(v["estetica"])
            temas.add(v["theme"])
            layouts.add(v["layout"])

        assert len(esteticas) >= 3, f"Poucas esteticas em 50 leads: {esteticas}"
        assert len(temas) >= 3, f"Poucos temas em 50 leads: {temas}"
        assert len(layouts) >= 2, f"Poucos layouts em 50 leads: {layouts}"

    @staticmethod
    def test_same_lead_id_always_same_variation():
        """Mesmo (lead_id, segmento) -> MESMA variation sempre."""
        sys_mod = _import_system()
        generate_variation = sys_mod["generate_variation"]

        v1 = generate_variation(lead_id=7, segmento="academia_crossfit")
        v2 = generate_variation(lead_id=7, segmento="academia_crossfit")
        v3 = generate_variation(lead_id=7, segmento="academia_crossfit")

        assert v1 == v2 == v3, (
            f"Determinismo global quebrado:\n"
            f"  v1={v1}\n  v2={v2}\n  v3={v3}"
        )

        # Bonus: segmento diferente, mesmo lead -> pode (e deve) ser diferente
        v4 = generate_variation(lead_id=7, segmento="pet_shop")
        # Pelo menos UM eixo deve diferir (na pratica varios diferem)
        diffs = sum(1 for k in v1 if v1[k] != v4[k])
        assert diffs >= 1, (
            f"Segmento diferente nao mudou NENHUM eixo: v1={v1} v4={v4}"
        )


def _run_all() -> int:
    suite = TestVariationSystem()
    passed = failed = 0
    failures: list[str] = []

    for name in dir(suite):
        if not name.startswith("test_"):
            continue
        fn = getattr(suite, name)
        try:
            fn()
            print(f"OK   {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            failures.append(name)
        except Exception as e:
            print(f"ERR  {name}: {type(e).__name__}: {e}")
            failed += 1
            failures.append(name)

    print(f"\n{'=' * 60}")
    print(f"Variation System (4-Axis): {passed}/{passed + failed} passados")
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())