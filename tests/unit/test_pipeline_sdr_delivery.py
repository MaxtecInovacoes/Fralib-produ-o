from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.pipeline_sdr_delivery import tenant_sdr_allowed


class _FakeResult:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _FakeDb:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, query, params):
        self.calls.append((str(query), params))
        return _FakeResult(self.row)


def test_tenant_sdr_allowed_reads_current_plan_status():
    db = _FakeDb(("pro", "active", None))

    allowed = tenant_sdr_allowed(db, 2)

    assert allowed
    assert db.calls[0][1] == {"id": 2}


def test_tenant_sdr_allowed_fails_closed_when_user_missing():
    db = _FakeDb(None)

    assert not tenant_sdr_allowed(db, 2)
