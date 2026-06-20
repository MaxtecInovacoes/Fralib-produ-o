from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from whatsapp.sender import (
    send_handoff_notification,
    send_presence_composing,
    send_text_parts,
)


class _FakeResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self.responses:
            return self.responses.pop(0)
        return _FakeResponse()


def test_send_presence_composing_posts_expected_payload():
    client = _FakeClient([_FakeResponse()])

    send_presence_composing(client, "http://localhost:3001", "k", "tenant-1", "5511@s.whatsapp.net")

    call = client.calls[0]
    assert call["url"] == "http://localhost:3001/api/sessions/tenant-1/presence"
    assert call["headers"] == {"X-API-Key": "k"}
    assert call["json"] == {"jid": "5511@s.whatsapp.net", "type": "composing"}


def test_send_text_parts_sends_all_parts_and_calls_hook_between_parts():
    client = _FakeClient([_FakeResponse(), _FakeResponse()])
    hook_calls = []

    ok, last_error = send_text_parts(
        client,
        "http://localhost:3001",
        "k",
        "tenant-1",
        "5511@s.whatsapp.net",
        ["parte 1", "parte 2"],
        before_send=lambda idx, part: hook_calls.append((idx, part)),
    )

    assert ok is True
    assert last_error == ""
    assert len(client.calls) == 2
    assert hook_calls == [(0, "parte 1"), (1, "parte 2")]
    assert client.calls[1]["json"]["text"] == "parte 2"


def test_send_text_parts_stops_on_first_http_error():
    client = _FakeClient([_FakeResponse(500, "boom"), _FakeResponse()])

    ok, last_error = send_text_parts(
        client,
        "http://localhost:3001",
        "k",
        "tenant-1",
        "5511@s.whatsapp.net",
        ["parte 1", "parte 2"],
    )

    assert ok is False
    assert last_error == "boom"
    assert len(client.calls) == 1


def test_send_handoff_notification_targets_closer_jid():
    client = _FakeClient([_FakeResponse()])

    send_handoff_notification(
        client,
        "http://localhost:3001",
        "k",
        "tenant-1",
        "5541999999999",
        "resumo",
    )

    call = client.calls[0]
    assert call["url"] == "http://localhost:3001/api/sessions/tenant-1/send"
    assert call["json"]["jid"] == "5541999999999@s.whatsapp.net"
    assert call["json"]["text"] == "resumo"
