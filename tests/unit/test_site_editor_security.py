import os
import sys
import base64

import pytest
from fastapi import HTTPException


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "unit-test-secret-value-with-32-bytes")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "endpoints")
)

from endpoints.site_editor_endpoints import (
    _decodificar_asset,
    _detectar_asset,
    _rejeitar_html_ativo,
    _sanitizar_html,
)


def test_site_editor_rejects_active_html_even_if_old_html_had_iframe():
    html_antigo = "<html><body><iframe src='https://maps.example'></iframe></body></html>"
    html_novo = "<html><body><iframe src='https://evil.example'></iframe></body></html>"

    with pytest.raises(HTTPException, match="iframe"):
        _sanitizar_html(html_novo, html_antigo)


@pytest.mark.parametrize(
    "html_novo, expected",
    [
        ("<html><body><script>alert(1)</script></body></html>", "script"),
        ("<html><body><a href='javascript:alert(1)'>x</a></body></html>", "URL ativa"),
        ("<html><body><button onclick='alert(1)'>x</button></body></html>", "event handler"),
        ("<html><head><meta http-equiv='refresh' content='0;url=https://x'></head></html>", "meta refresh"),
    ],
)
def test_site_editor_rejects_script_handlers_and_active_urls(html_novo, expected):
    with pytest.raises(HTTPException, match=expected):
        _sanitizar_html(html_novo, "<html><body>ok</body></html>")


def test_site_editor_rejects_current_tailwind_cdn_wrapper_script():
    html = (
        "<html><head><script src='https://cdn.tailwindcss.com'></script></head>"
        "<body><main>ok</main></body></html>"
    )

    with pytest.raises(HTTPException, match="script"):
        _sanitizar_html(html, "<html><body>ok</body></html>")


@pytest.mark.parametrize(
    "fragment, expected",
    [
        ("<div onclick='alert(1)'>x</div>", "event handler"),
        ("<a href='javascript:alert(1)'>x</a>", "URL ativa"),
        ("<script>alert(1)</script>", "script"),
    ],
)
def test_studio_ai_html_guard_rejects_active_fragment(fragment, expected):
    with pytest.raises(HTTPException, match=expected):
        _rejeitar_html_ativo(fragment)


def test_site_editor_upload_accepts_png_data_url():
    payload = b"\x89PNG\r\n\x1a\nfake-png"
    data_url = "data:image/png;base64," + base64.b64encode(payload).decode("ascii")

    decoded = _decodificar_asset(data_url)

    assert decoded == payload
    assert _detectar_asset(decoded) == ("image/png", ".png")


def test_site_editor_upload_rejects_svg_payload():
    with pytest.raises(HTTPException, match="Imagem invalida"):
        _detectar_asset(b"<svg><script>alert(1)</script></svg>")


def test_site_editor_upload_rejects_invalid_base64():
    with pytest.raises(HTTPException, match="Base64 invalido"):
        _decodificar_asset("data:image/png;base64,nao-e-base64")
