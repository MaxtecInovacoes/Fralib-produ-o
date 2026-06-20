from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from whatsapp.sdr_reply_service import (
    build_history,
    get_outgoing_formatter,
    is_duplicate_reply,
    map_next_stage,
    normalize_followup_date,
    sanitize_reply,
)


def test_build_history_maps_directions_to_roles():
    rows = [("bot-1", "saida"), ("lead-1", "entrada")]

    history = build_history(rows)

    assert history == [
        {"role": "user", "content": "lead-1"},
        {"role": "assistant", "content": "bot-1"},
    ]


def test_sanitize_reply_extracts_embedded_resposta_field():
    raw = '{"resposta":"Oi, tudo bem?","novo_stage":"intro"}'

    assert sanitize_reply(raw) == "Oi, tudo bem?"


def test_sanitize_reply_uses_retry_extractor_when_needed():
    raw = '{"foo":"bar"}'

    fixed = sanitize_reply(raw, retry_extractor=lambda reply: "Texto limpo")

    assert fixed == "Texto limpo"


def test_get_outgoing_formatter_falls_back_to_single_part():
    formatter = get_outgoing_formatter(None)

    assert formatter("teste") == ["teste"]


def test_is_duplicate_reply_detects_repeat_against_last_assistant_message():
    history = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": "Mensagem anterior completa"},
    ]

    assert is_duplicate_reply(history, "Mensagem anterior") is True
    assert is_duplicate_reply(history, "Mensagem nova") is False


def test_map_next_stage_uses_mapping_and_default_hook():
    raw_stage, stage = map_next_stage("", "", {"hook": "intro", "lost": "perdidos"})
    assert raw_stage == "hook"
    assert stage == "intro"

    raw_stage, stage = map_next_stage("lost", "intro", {"hook": "intro", "lost": "perdidos"})
    assert raw_stage == "lost"
    assert stage == "perdidos"


def test_normalize_followup_date_keeps_future_date():
    normalized, status = normalize_followup_date("2099-12-31")

    assert normalized == "2099-12-31"
    assert status == "ok"


def test_normalize_followup_date_fixes_past_date():
    normalized, status = normalize_followup_date("2020-01-01")

    assert status == "past"
    assert len(normalized) == 10


def test_normalize_followup_date_fixes_invalid_date():
    normalized, status = normalize_followup_date("amanha")

    assert status == "invalid"
    assert len(normalized) == 10
