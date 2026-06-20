import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "scripts", ROOT / "backend"):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from scripts import repair_provider_key


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_mask_key_does_not_expose_full_secret():
    assert repair_provider_key.mask_key("sk-ant-1234567890") == "sk-a...7890"
    assert repair_provider_key.mask_key("short") == ""


def test_validate_anthropic_key_uses_safe_minimal_payload(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResponse(200)

    monkeypatch.setattr(repair_provider_key.requests, "post", fake_post)

    result = repair_provider_key.validate_provider_key(
        "anthropic",
        "secret-value",
        "https://llm.seunegociofralib.site",
        "gemini-2.5-flash",
    )

    assert result["ok"] is True
    assert captured["url"] == "https://llm.seunegociofralib.site/v1/messages"
    assert captured["json"]["max_tokens"] == 1
    assert captured["json"]["model"] == "gemini-2.5-flash"
    assert captured["headers"]["x-api-key"] == "secret-value"


def test_validate_provider_key_reports_401_without_secret(monkeypatch):
    monkeypatch.setattr(
        repair_provider_key.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(401),
    )

    result = repair_provider_key.validate_provider_key(
        "anthropic",
        "secret-value",
        "https://llm.seunegociofralib.site",
        "gemini-2.5-flash",
    )

    assert result["ok"] is False
    assert result["status"] == 401
    assert result["error"] == "401 key invalida"
    assert "secret-value" not in str(result)
