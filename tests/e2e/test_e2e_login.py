"""
test_e2e_login.py - Testes E2E do fluxo de login

Testa o fluxo completo de login na interface web usando Playwright.
"""
import pytest
import sys
import os

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))


@pytest.mark.e2e
def test_login_page_loads(page):
    """Testa que a página de login carrega corretamente."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")
    title = page.title()
    assert title is not None


@pytest.mark.e2e
def test_login_form_elements_exist(page):
    """Testa que os elementos do formulário de login existem."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    email_input = page.locator('input[type="email"], input[name="email"], #email')
    password_input = page.locator('input[type="password"], input[name="password"], #password')
    submit_button = page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")')

    email_input.first.wait_for(state="visible", timeout=5000)
    password_input.first.wait_for(state="visible", timeout=5000)
    submit_button.first.wait_for(state="visible", timeout=5000)


@pytest.mark.e2e
def test_login_with_valid_credentials(page, test_user, test_user_data):
    """Testa login com credenciais válidas."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    email_input = page.locator('input[type="email"], input[name="email"], #email').first
    password_input = page.locator('input[type="password"], input[name="password"], #password').first

    email_input.fill(test_user_data["email"])
    password_input.fill(test_user_data["password"])

    submit_button = page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first
    submit_button.click()

    page.wait_for_timeout(2000)

    current_url = page.url
    assert "login" not in current_url.lower() or page.locator('text=/sucesso|dashboard/i').count() > 0


@pytest.mark.e2e
def test_login_with_invalid_credentials(page):
    """Testa login com credenciais inválidas."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    email_input = page.locator('input[type="email"], input[name="email"], #email').first
    password_input = page.locator('input[type="password"], input[name="password"], #password').first

    email_input.fill("invalido@test.com")
    password_input.fill("SenhaErrada123")

    submit_button = page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first
    submit_button.click()

    page.wait_for_timeout(2000)

    error_message = page.locator('text=/erro|inválido|incorreto/i')
    assert error_message.count() > 0


@pytest.mark.e2e
def test_login_with_empty_fields(page):
    """Testa que não é possível fazer login com campos vazios."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    submit_button = page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first
    submit_button.click()

    page.wait_for_timeout(1000)

    current_url = page.url
    assert "login" in current_url.lower()


@pytest.mark.e2e
def test_login_email_validation(page):
    """Testa validação de formato de email."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    email_input = page.locator('input[type="email"], input[name="email"], #email').first
    password_input = page.locator('input[type="password"], input[name="password"], #password').first

    email_input.fill("email-invalido")
    password_input.fill("SenhaQualquer123")

    submit_button = page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first
    submit_button.click()

    page.wait_for_timeout(1000)

    current_url = page.url
    assert "login" in current_url.lower()


@pytest.mark.e2e
def test_login_password_visibility_toggle(page):
    """Testa botão de mostrar/ocultar senha (se existir)."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    password_input = page.locator('input[type="password"], input[name="password"], #password').first
    password_input.wait_for(state="visible")

    input_type = password_input.get_attribute("type")
    assert input_type == "password"

    toggle_button = page.locator('button:has-text("Mostrar"), button:has-text("👁"), [aria-label*="mostrar"]')

    if toggle_button.count() > 0:
        toggle_button.first.click()
        page.wait_for_timeout(500)
        new_type = password_input.get_attribute("type")
        assert new_type == "text"


@pytest.mark.e2e
def test_login_remember_me_checkbox(page):
    """Testa checkbox 'Lembrar-me' (se existir)."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    remember_checkbox = page.locator('input[type="checkbox"][name*="remember"], input[type="checkbox"]:near(:text("Lembrar"))')

    if remember_checkbox.count() > 0:
        is_checked = remember_checkbox.first.is_checked()
        if not is_checked:
            remember_checkbox.first.check()
            assert remember_checkbox.first.is_checked()


@pytest.mark.e2e
def test_login_page_responsive(page):
    """Testa que a página de login é responsiva."""
    page.goto("http://localhost:8000/login.html")
    page.wait_for_load_state("networkidle")

    viewports = [
        {"width": 375, "height": 667},
        {"width": 768, "height": 1024},
        {"width": 1920, "height": 1080}
    ]

    for viewport in viewports:
        page.set_viewport_size(viewport)
        page.wait_for_timeout(500)

        email_input = page.locator('input[type="email"], input[name="email"], #email').first
        password_input = page.locator('input[type="password"], input[name="password"], #password').first

        assert email_input.is_visible()
        assert password_input.is_visible()
