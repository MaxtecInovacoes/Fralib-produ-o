"""
Teste rápido de validação visual dos tokens CSS.
Verifica que os arquivos CSS contêm as definições corretas.
"""

import re
from pathlib import Path


def test_css_file_exists():
    """CSS tokens file deve existir"""
    css_file = Path("frontend/static/design-system-tokens.css")
    assert css_file.exists(), "design-system-tokens.css not found"
    print("[OK] design-system-tokens.css existe")


def test_css_has_all_poles():
    """CSS deve ter definições para todos os 4 polos"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    assert '[data-pole="soft"]' in content, "SOFT pole missing"
    assert '[data-pole="bold"]' in content, "BOLD pole missing"
    assert '[data-pole="corporate"]' in content, "CORPORATE pole missing"
    assert '[data-pole="minimal"]' in content, "MINIMAL pole missing"
    print("[OK] Todos os 4 polos definidos no CSS")


def test_css_soft_radius():
    """CSS SOFT deve ter radius de 40px"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    # Extrair bloco SOFT
    soft_match = re.search(r'\[data-pole="soft"\]\s*\{([^}]+)\}', content, re.DOTALL)
    assert soft_match, "SOFT pole block not found"
    soft_content = soft_match.group(1)

    assert '--pole-radius: 40px' in soft_content, "SOFT radius should be 40px"
    print("[OK] SOFT radius = 40px")


def test_css_bold_radius():
    """CSS BOLD deve ter radius de 0px"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    bold_match = re.search(r'\[data-pole="bold"\]\s*\{([^}]+)\}', content, re.DOTALL)
    assert bold_match, "BOLD pole block not found"
    bold_content = bold_match.group(1)

    assert '--pole-radius: 0px' in bold_content, "BOLD radius should be 0px"
    print("[OK] BOLD radius = 0px")


def test_css_bold_overlap():
    """CSS BOLD deve ter overlap de -80px"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    bold_match = re.search(r'\[data-pole="bold"\]\s*\{([^}]+)\}', content, re.DOTALL)
    bold_content = bold_match.group(1)

    assert '--pole-section-overlap: -80px' in bold_content, "BOLD overlap should be -80px"
    print("[OK] BOLD overlap = -80px")


def test_css_minimal_radius():
    """CSS MINIMAL deve ter radius de 12px"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    minimal_match = re.search(r'\[data-pole="minimal"\]\s*\{([^}]+)\}', content, re.DOTALL)
    assert minimal_match, "MINIMAL pole block not found"
    minimal_content = minimal_match.group(1)

    assert '--pole-radius: 12px' in minimal_content, "MINIMAL radius should be 12px"
    print("[OK] MINIMAL radius = 12px")


def test_css_has_utility_classes():
    """CSS deve ter classes utilitárias (hero-headline, card-pole, etc)"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    assert '.hero-headline' in content, "hero-headline class missing"
    assert '.card-pole' in content, "card-pole class missing"
    assert '.btn-pole' in content, "btn-pole class missing"
    assert '.glass-card' in content, "glass-card class missing"
    assert '.section-pole' in content, "section-pole class missing"
    print("[OK] Classes utilitárias presentes")


def test_css_has_motion_utilities():
    """CSS deve ter utilitários de motion"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    assert '[data-reveal]' in content, "data-reveal attribute missing"
    assert 'data-stagger' in content, "data-stagger attribute missing"
    print("[OK] Utilitários de motion presentes")


def test_css_has_responsive_breakpoints():
    """CSS deve ter breakpoints responsivos"""
    css_file = Path("frontend/static/design-system-tokens.css")
    content = css_file.read_text(encoding="utf-8")

    assert '@media (max-width: 768px)' in content, "Mobile breakpoint missing"
    assert '@media (min-width: 769px)' in content, "Tablet breakpoint missing"
    print("[OK] Breakpoints responsivos presentes")


if __name__ == "__main__":
    print("=" * 60)
    print("VALIDAÇÃO VISUAL - CSS Design System Tokens")
    print("=" * 60)
    print()

    tests = [
        test_css_file_exists,
        test_css_has_all_poles,
        test_css_soft_radius,
        test_css_bold_radius,
        test_css_bold_overlap,
        test_css_minimal_radius,
        test_css_has_utility_classes,
        test_css_has_motion_utilities,
        test_css_has_responsive_breakpoints,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"RESULTADO: {passed} passou, {failed} falhou")
    print("=" * 60)
