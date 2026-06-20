from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from whatsapp.lead_identity import (
    find_lead_by_phone_or_jid,
    normalize_jid_number,
    phone_variants,
    resolve_lid_number,
    user_id_from_tenant,
)


def test_normalize_jid_number_extracts_digits_before_domain():
    assert normalize_jid_number("5511999999999@s.whatsapp.net") == "5511999999999"
    assert normalize_jid_number("234754607685703@lid") == "234754607685703"
    assert normalize_jid_number("+55 (41) 98513-4105") == "5541985134105"


def test_user_id_from_tenant_accepts_only_fralib_user_pattern():
    assert user_id_from_tenant("fralib_user_2") == 2
    assert user_id_from_tenant("fralib_user_987") == 987
    assert user_id_from_tenant("tenant_2") is None
    assert user_id_from_tenant("") is None


def test_phone_variants_cover_country_code_and_brazil_ninth_digit():
    variants = set(phone_variants("(41) 98513-4105"))

    assert "41985134105" in variants
    assert "5541985134105" in variants
    assert "554185134105" in variants
    assert "4185134105" in variants


def test_phone_variants_add_ninth_digit_when_source_has_eight_digits():
    variants = set(phone_variants("554185134105"))

    assert "554185134105" in variants
    assert "5541985134105" in variants
    assert "4185134105" in variants
    assert "41985134105" in variants


class _FakeRow(tuple):
    pass


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        if params["lid"] == "234754607685703":
            return _FakeResult(("5541985134105",))
        return _FakeResult(None)


class _FakeEngine:
    def connect(self):
        return _FakeConnection()


def test_resolve_lid_number_uses_whatsmeow_map_when_available():
    resolved = resolve_lid_number(
        "234754607685703",
        "postgres://example",
        engine_factory=lambda url: _FakeEngine(),
    )

    assert resolved == "5541985134105"


def test_resolve_lid_number_keeps_lid_when_db_is_unavailable():
    assert resolve_lid_number("234754607685703", "") == "234754607685703"


class _LeadLookupConnection:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.calls.append(params)
        if "variantes" in params:
            assert params["uid"] == 2
            assert "5541985134105" in params["variantes"]
            assert "554185134105" in params["variantes"]
            return _FakeResult(None)
        return _FakeResult(("lead-1", "Lead Teste", "academia", "Curitiba", "intro", "concluido", ""))


class _LeadLookupEngine:
    def __init__(self):
        self.connection = _LeadLookupConnection()

    def connect(self):
        return self.connection


def test_find_lead_by_phone_or_jid_falls_back_to_wpp_jid_with_same_tenant():
    fake_engine = _LeadLookupEngine()

    row = find_lead_by_phone_or_jid("5541985134105", 2, fake_engine)

    assert row[0] == "lead-1"
    assert fake_engine.connection.calls[-1] == {"jid": "5541985134105", "uid": 2}
