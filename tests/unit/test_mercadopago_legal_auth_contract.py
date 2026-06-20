import hashlib
import hmac
import asyncio
import os
import sys
from pathlib import Path


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@example.com")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "core"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "endpoints"))

from endpoints.auth_endpoints import (  # noqa: E402
    PRIVACY_VERSION,
    TERMS_VERSION,
    RegisterRequest,
    _totp_code,
    _verify_totp_code,
)
from endpoints.credits_endpoints import (  # noqa: E402
    PLANOS,
    _criar_checkout_mercadopago,
    _criar_recarga_mercadopago,
    _credit_package_for_value,
    _mercadopago_signature_valid,
    _mercadopago_payload_matches_user,
    _payment_provider,
    get_pricing,
)


ROOT = Path(__file__).resolve().parents[2]


def test_mercadopago_webhook_signature_contract():
    secret = "mp-webhook-secret"
    data_id = "123456789"
    request_id = "req-abc"
    ts = "1710000000"
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    assert _mercadopago_signature_valid(data_id, request_id, f"ts={ts},v1={signature}", secret)
    assert not _mercadopago_signature_valid(data_id, request_id, f"ts={ts},v1=bad", secret)


def test_mercadopago_subscription_preapproval_payload(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "pre_123", "init_point": "https://www.mercadopago.com.br/subscriptions/checkout?preapproval_id=pre_123"}

    def fake_post(url, headers, json, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "APP_USR_TEST")
    monkeypatch.setenv("APP_URL", "https://fralib.example.com")
    monkeypatch.setattr("endpoints.credits_endpoints.requests.post", fake_post)

    result = _criar_checkout_mercadopago("starter", {"id": 42, "email": "cliente@example.com"})

    assert result["provider"] == "mercadopago"
    assert result["checkout_type"] == "subscription"
    assert result["checkout_url"].startswith("https://www.mercadopago.com.br/")
    assert calls["url"].endswith("/preapproval")
    assert calls["headers"]["Authorization"] == "Bearer APP_USR_TEST"
    assert calls["json"]["auto_recurring"] == {
        "frequency": 1,
        "frequency_type": "months",
        "transaction_amount": 97.0,
        "currency_id": "BRL",
    }
    assert calls["json"]["external_reference"].startswith("fralib:42:starter:")
    assert calls["json"]["status"] == "pending"
    assert calls["json"]["notification_url"] == "https://fralib.example.com/api/credits/webhook/mercadopago?source_news=webhooks"


def test_mercadopago_agency_subscription_contract(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "pre_agency", "init_point": "https://www.mercadopago.com.br/subscriptions/checkout?preapproval_id=pre_agency"}

    def fake_post(url, headers, json, timeout):
        calls["url"] = url
        calls["json"] = json
        return FakeResponse()

    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "APP_USR_TEST")
    monkeypatch.setenv("APP_URL", "https://fralib.example.com")
    monkeypatch.setattr("endpoints.credits_endpoints.requests.post", fake_post)

    result = _criar_checkout_mercadopago("agency", {"id": 42, "email": "agency@example.com"})

    assert PLANOS["agency"]["valor"] == 497.0
    assert result["checkout_type"] == "subscription"
    assert result["plano"] == "agency"
    assert calls["url"].endswith("/preapproval")
    assert calls["json"]["auto_recurring"]["transaction_amount"] == 497.0
    assert calls["json"]["external_reference"].startswith("fralib:42:agency:")
    assert calls["json"]["notification_url"] == "https://fralib.example.com/api/credits/webhook/mercadopago?source_news=webhooks"


def test_mercadopago_recharge_preference_payload_supports_pix_and_card(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "pref_123", "init_point": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=pref_123"}

    def fake_post(url, headers, json, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "APP_USR_TEST")
    monkeypatch.setenv("APP_URL", "https://fralib.example.com")
    monkeypatch.setattr("endpoints.credits_endpoints.requests.post", fake_post)

    result = _criar_recarga_mercadopago(50, {"id": 42, "email": "cliente@example.com"})

    assert result["provider"] == "mercadopago"
    assert result["checkout_type"] == "recharge"
    assert result["creditos"] == 18
    assert calls["url"].endswith("/checkout/preferences")
    assert calls["json"]["items"][0]["currency_id"] == "BRL"
    assert calls["json"]["metadata"]["plano"] == "recarga"
    assert calls["json"]["metadata"]["creditos"] == "18"
    assert calls["json"]["payment_methods"] == {"installments": 12}
    assert "excluded_payment_types" not in calls["json"]["payment_methods"]
    assert calls["json"]["notification_url"].endswith("/api/credits/webhook/mercadopago?source_news=webhooks")


def test_mercadopago_is_the_only_payment_provider_contract():
    assert _payment_provider() == "mercadopago"
    assert _credit_package_for_value(100)["creditos_totais"] == 40
    assert _credit_package_for_value(37)["creditos_totais"] >= 9
    pricing = asyncio.run(get_pricing())
    assert pricing["payment_methods"] == ["pix", "credit_card", "debit_card"]
    assert any(p["plano"] == "agency" and p["valor"] == 497.0 for p in pricing["plans"])


def test_mercadopago_return_sync_is_user_scoped():
    usuario = {"id": 42, "email": "cliente@example.com"}

    assert _mercadopago_payload_matches_user({"metadata": {"user_id": "42"}}, usuario)
    assert not _mercadopago_payload_matches_user({"metadata": {"user_id": "7"}}, usuario)
    assert _mercadopago_payload_matches_user({"external_reference": "fralib:42:recarga:abc"}, usuario)
    assert not _mercadopago_payload_matches_user({"external_reference": "fralib:7:recarga:abc"}, usuario)
    assert _mercadopago_payload_matches_user({"payer": {"email": "cliente@example.com"}}, usuario)


def test_billing_runtime_uses_only_mercadopago():
    checked_files = [
        ROOT / "backend" / "endpoints" / "credits_endpoints.py",
        ROOT / "backend" / "requirements.txt",
        ROOT / ".env.example",
    ]
    for path in checked_files:
        source = path.read_text(encoding="utf-8").lower()
        assert "stripe" not in source, f"{path} should not contain stripe references"


def test_register_request_requires_legal_acceptance_by_default():
    payload = RegisterRequest(email="novo@example.com", password="SenhaForte123")

    assert payload.accept_terms is False
    assert payload.accept_privacy is False
    assert payload.terms_version == TERMS_VERSION
    assert payload.privacy_version == PRIVACY_VERSION


def test_totp_verification_contract():
    secret = "JBSWY3DPEHPK3PXP"
    now = 1_710_000_000
    counter = now // 30
    code = _totp_code(secret, counter)

    assert _verify_totp_code(secret, code, now=now)
    assert not _verify_totp_code(secret, "000000", now=now)


def test_public_legal_pages_and_signup_contract_are_versioned():
    termos = (ROOT / "frontend" / "termos.html").read_text(encoding="utf-8")
    privacidade = (ROOT / "frontend" / "privacidade.html").read_text(encoding="utf-8")
    login = (ROOT / "frontend" / "login.html").read_text(encoding="utf-8")

    assert TERMS_VERSION in termos
    assert PRIVACY_VERSION in privacidade
    assert 'id="acceptLegal"' in login
    public_terms = (ROOT / "frontend" / "docs" / "termos.html").read_text(encoding="utf-8")
    public_privacy = (ROOT / "frontend" / "docs" / "privacidade.html").read_text(encoding="utf-8")
    assert TERMS_VERSION in public_terms
    assert PRIVACY_VERSION in public_privacy
    assert 'href="/docs/termos.html"' in login
    assert 'href="/docs/privacidade.html"' in login
    assert "accept_terms:true" in login
    assert "accept_privacy:true" in login
    assert "localStorage.setItem('fralib_token'" not in login


def test_launch_sales_copy_matches_trial_guarantee_and_franz_brand():
    checked = [
        ROOT / "frontend" / "partials" / "landing" / "_head.html",
        ROOT / "frontend" / "partials" / "landing" / "_hero.html",
        ROOT / "frontend" / "partials" / "landing" / "_produto.html",
        ROOT / "frontend" / "partials" / "landing" / "_planos.html",
        ROOT / "frontend" / "partials" / "landing" / "_faq.html",
        ROOT / "frontend" / "planos.html",
        ROOT / "frontend" / "docs" / "index.html",
        ROOT / "frontend" / "blog" / "index.html",
        ROOT / "frontend" / "js" / "pixel-office.js",
    ]
    forbidden = [
        "7 DIAS GRÁTIS",
        "7 DIAS GRATIS",
        "Teste por 7 dias",
        "SDR Bryan",
        "Sou o Bryan",
        "Bryan completo",
        "Bryan com retries",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)

    for token in forbidden:
        assert token not in combined
    assert "7 DIAS DE GARANTIA" in combined
    assert "SDR Franz" in combined
    assert "R$497" in combined
    assert "Sem disparo SDR" in combined


def test_prod_payment_runtime_scripts_keep_secrets_out_of_git_flow():
    apply_script = (ROOT / "scripts" / "vps_apply_prod_runtime.py").read_text(encoding="utf-8")
    validate_script = (ROOT / "scripts" / "vps_validate_prod_launch.py").read_text(encoding="utf-8")
    redis_script = (ROOT / "scripts" / "vps_prepare_redis.sh").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "MERCADO_PAGO_SEGURANCA_PLANO.md").read_text(encoding="utf-8")

    assert "getpass.getpass" in apply_script
    assert "/root/fralib-env-backups" in apply_script
    assert '"FRALIB_ENV": "prod"' in apply_script
    assert '"FRALIB_COOKIE_SECURE": "1"' in apply_script
    assert "APP_USR" in apply_script
    assert "redis-cli" in redis_script
    assert "LIBERADO TECNICAMENTE PARA COBRANCA REAL" in validate_script
    assert "Nao cole token Mercado Pago no chat" in docs
    assert "vps_validate_prod_launch.py --smoke" in docs


def test_payment_ui_exposes_recharge_renewal_return_sync_and_tour():
    dashboard_header_path = ROOT / "frontend" / "partials" / "dashboard" / "_header.html"
    dashboard_header = (
        dashboard_header_path
        if dashboard_header_path.exists()
        else ROOT / "frontend" / "partials" / "admin" / "_main-header.html"
    ).read_text(encoding="utf-8")
    admin_header = (ROOT / "frontend" / "partials" / "admin" / "_main-header.html").read_text(encoding="utf-8")
    dashboard_scripts_path = ROOT / "frontend" / "partials" / "dashboard" / "_scripts.html"
    dashboard_scripts = (
        dashboard_scripts_path
        if dashboard_scripts_path.exists()
        else ROOT / "frontend" / "partials" / "admin" / "_scripts.html"
    ).read_text(encoding="utf-8")
    admin_scripts = (ROOT / "frontend" / "partials" / "admin" / "_scripts.html").read_text(encoding="utf-8")
    credits_api = (ROOT / "backend" / "endpoints" / "credits_endpoints.py").read_text(encoding="utf-8")
    reconcile_script = (ROOT / "scripts" / "vps_reconcile_mercadopago_payments.py").read_text(encoding="utf-8")

    for source in (dashboard_header, admin_header):
        assert 'id="billing-control-strip"' in source
        assert "Comprar créditos" in source
        assert "Planos e renovação" in source
        assert "iniciarTourFraLib(true)" in source

    for source in (dashboard_scripts, admin_scripts):
        assert "fralib_mp_pending" in source
        assert "/api/credits/sync-mercadopago" in source
        assert "Pagamentos e créditos" in source or "PAGAMENTOS E CRÉDITOS" in source
        assert "fralib_onboarding_done_v2" in source

    assert '@router.post("/sync-mercadopago")' in credits_api
    assert "pagamento ja processado" in credits_api
    assert "_processar_evento_mercadopago(payment)" in reconcile_script
